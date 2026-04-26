"""Compile NIF schema cond/vercond/length/arg expressions into Python source.

The schema's expression mini-DSL looks Python-ish after token substitution
(operator tokens like `#GTE#` map straight to `>=`). The pieces this module
handles:

1. **Token substitution** — `Schema.tokens` lists groups of `#NAME#` -> string
   substitutions, each scoped to a set of XML attributes (`cond`, `vercond`,
   `length`, …). We pre-build per-attribute substitution dicts and apply them
   iteratively until no `#...#` markers remain.

2. **Tokenization** — splits the substituted string on a fixed operator set
   (`&& || == != <= >= < > >> << + - * / & | ( ) ,`). Whatever sits between
   operators is either a literal (decimal int, hex int, float, dotted version)
   or an identifier (possibly multi-word like `Num Vertices` or
   path-like `BS Header\\BS Version`).

3. **Re-emit** — produces a valid Python expression. Identifiers are routed
   through a `FieldResolver` callable that the emitter wires up to
   `self.<snake_case>` attribute access for the containing block/struct.
   The three globals (`Version`, `User Version`, `BS Header\\BS Version`) are
   pre-bound to `ctx.version` / `ctx.user_version` / `ctx.bs_version`.

The output is plain Python source (e.g. `(ctx.bs_version >= 100) and
(self.num_vertices > 0)`) — no runtime DSL interpreter, no `eval`.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .parser import Schema, VersionDef

__all__ = [
    "ExprCompiler",
    "FieldResolver",
    "compile_version_literal",
    "compile_versions_set",
]

FieldResolver = Callable[[str], str]
"""Map a raw schema field name (e.g. `'Num Vertices'`) to a Python expression
(e.g. `'self.num_vertices'`). Provided by the emitter for each container."""


# Globals always rewritten to ctx.* attribute access. Inserted as
# Python-identifier markers during substitution so the tokenizer treats them
# as ordinary names.
_GLOBAL_MARKERS: dict[str, str] = {
    "Version": "__CTX_VER__",
    "User Version": "__CTX_USER__",
    "BS Header\\BS Version": "__CTX_BSVER__",
}
_GLOBAL_TO_PY: dict[str, str] = {
    "__CTX_VER__": "ctx.version",
    "__CTX_USER__": "ctx.user_version",
    "__CTX_BSVER__": "ctx.bs_version",
    "__CTX_ARG__": "ctx.arg",
}

# `#ARG#` is not declared in `nif.xml`'s `<token>` table — it is a built-in
# convention referring to the value pushed on `ctx.args` by the calling
# field's `arg=` expression. Codegen wires it up identically to the schema
# globals: per-attribute substitution into an identifier-safe marker, then
# rewritten to `ctx.arg` at emit time.
_BUILTIN_TOKENS: dict[str, str] = {
    "#ARG#": "__CTX_ARG__",
}
_BUILTIN_ATTRS: tuple[str, ...] = ("cond", "vercond", "length", "arg", "calc", "width")

# Operators recognized after token substitution. Order matters: longer
# operators must be tried before their prefixes so `>=` is not split into
# `>` and `=`.
_OPERATORS: tuple[str, ...] = (
    "&&",
    "||",
    "==",
    "!=",
    "<=",
    ">=",
    ">>",
    "<<",
    "<",
    ">",
    "+",
    "-",
    "*",
    "/",
    "&",
    "|",
    "(",
    ")",
    ",",
)
_BOOL_OPS: dict[str, str] = {"&&": " and ", "||": " or "}

_HEX_INT_RE = re.compile(r"^0[xX][0-9A-Fa-f]+$")
_DEC_INT_RE = re.compile(r"^[+-]?\d+$")
# Float: optional leading sign, integer part, optional fractional part, and
# optional exponent (`e`/`E` with optional `+`/`-` sign). Matches forms like
# `1`, `+1.5`, `-3.14`, `1e10`, `+3.402823466e+38`, `-1.0E-7`.
_FLOAT_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")
_VERSION_RE = re.compile(r"^\d+(?:\.\d+){1,3}$")
_TOKEN_MARKER_RE = re.compile(r"#[A-Za-z0-9_]+#")
_IDENT_CHAR_RE = re.compile(r"[A-Za-z0-9_\\ ]+")


# ---- token substitution ---------------------------------------------------


class _SubstTable:
    """Per-attribute substitution table.

    Built once per `Schema` and reused. Substitutions are applied iteratively
    (since `verexpr` macros expand to text containing `#BSVER#`, `#GTE#`,
    etc.). A cycle / overflow guard caps iterations.
    """

    def __init__(self, mapping: dict[str, str]) -> None:
        # Sort by descending key length so longer markers win in the unlikely
        # case one is a prefix of another.
        self._mapping = dict(sorted(mapping.items(), key=lambda kv: -len(kv[0])))

    def apply(self, text: str, *, max_iter: int = 16) -> str:
        for _ in range(max_iter):
            replaced = text
            for marker, value in self._mapping.items():
                if marker in replaced:
                    replaced = replaced.replace(marker, value)
            if replaced == text:
                return replaced
            text = replaced
        if _TOKEN_MARKER_RE.search(text):
            raise ValueError(f"unresolved token markers after {max_iter} iterations: {text!r}")
        return text


def _build_subst_tables(schema: Schema) -> dict[str, _SubstTable]:
    """Build a `_SubstTable` per logical attribute (cond, vercond, length, …).

    Each token group declares which schema attributes its rules apply to via
    `attrs="cond vercond"`. We invert that: for every attribute name seen,
    build a single combined dict from all groups that apply to it, then layer
    in the global-marker rewrites used by `cond` / `vercond` only.
    """
    by_attr: dict[str, dict[str, str]] = {}
    for tok in schema.tokens:
        for attr in tok.attrs:
            slot = by_attr.setdefault(attr, {})
            for entry in tok.entries:
                slot[entry.token] = entry.string

    # Globals are conceptually a fourth substitution pass, but folding them
    # into the table avoids a separate pass. They only apply where the schema
    # said `attrs="cond vercond access"`, which the loop above already
    # captured (we re-route them through identifier-safe markers below).
    for attr, slot in by_attr.items():
        for raw, marker in _GLOBAL_MARKERS.items():
            if raw in slot.values() or attr in ("cond", "vercond", "access"):
                # Replace any literal global expansion with our marker so the
                # later tokenizer treats it as a single identifier.
                for token, expansion in list(slot.items()):
                    if expansion == raw:
                        slot[token] = marker

    # Built-in `#ARG#` token: not declared in nif.xml but used in cond/length/
    # arg/calc/width expressions to refer to ctx.arg.
    for attr in _BUILTIN_ATTRS:
        slot = by_attr.setdefault(attr, {})
        for tok, marker in _BUILTIN_TOKENS.items():
            slot[tok] = marker

    return {attr: _SubstTable(d) for attr, d in by_attr.items()}


# ---- expression compilation -----------------------------------------------


@dataclass(slots=True)
class ExprCompiler:
    """Bound to a `Schema` once; reused per field expression."""

    schema: Schema
    _subst: dict[str, _SubstTable]

    @classmethod
    def for_schema(cls, schema: Schema) -> ExprCompiler:
        return cls(schema=schema, _subst=_build_subst_tables(schema))

    # ---- public entry points ----

    def compile_cond(self, text: str, resolver: FieldResolver) -> str:
        return self._compile(text, "cond", resolver)

    def compile_vercond(self, text: str, resolver: FieldResolver) -> str:
        return self._compile(text, "vercond", resolver)

    def compile_length(self, text: str, resolver: FieldResolver) -> str:
        return self._compile(text, "length", resolver)

    def compile_arg(self, text: str, resolver: FieldResolver) -> str:
        return self._compile(text, "arg", resolver)

    def compile_width(self, text: str, resolver: FieldResolver) -> str:
        return self._compile(text, "width", resolver)

    # ---- core ----

    def _compile(self, text: str, attr: str, resolver: FieldResolver) -> str:
        subst = self._subst.get(attr)
        substituted = subst.apply(text) if subst is not None else text
        tokens = _tokenize(substituted)
        return _emit(tokens, resolver)


# ---- tokenizer + emitter --------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Split on operators; keep operands as single tokens (whitespace-trimmed).

    Float exponents like `3.402823466e+38` contain a `+` that must NOT be
    treated as an operator. We special-case it: when the operand scanner sees
    `[eE][+-]\\d`, it consumes the sign as part of the float.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue

        op = _match_operator(text, i)
        if op is not None:
            out.append(op)
            i += len(op)
            continue

        # Operand: scan up to the next operator or end of string.
        j = i
        while j < n:
            ch = text[j]
            if ch.isspace():
                k = j
                while k < n and text[k].isspace():
                    k += 1
                if k == n or _match_operator(text, k) is not None:
                    break
                j = k
                continue
            # Float-exponent guard: a `+`/`-` immediately following `e` or
            # `E` (in turn preceded by a digit) is part of the number, not
            # an operator. Consume it without breaking the operand.
            if (
                ch in "+-"
                and j > i
                and text[j - 1] in "eE"
                and j - 2 >= i
                and text[j - 2].isdigit()
            ):
                j += 1
                continue
            if _match_operator(text, j) is not None:
                break
            j += 1
        operand = text[i:j].strip()
        if operand:
            out.append(operand)
        i = j
    return out


def _match_operator(text: str, i: int) -> str | None:
    for op in _OPERATORS:
        if text.startswith(op, i):
            return op
    return None


def _emit(tokens: list[str], resolver: FieldResolver) -> str:
    pieces: list[str] = []
    for tok in tokens:
        if tok in _BOOL_OPS:
            pieces.append(_BOOL_OPS[tok])
        elif tok in _OPERATORS:
            # Bracket binary ops with spaces for readability.
            pieces.append(f" {tok} " if tok not in ("(", ")", ",") else tok)
        else:
            pieces.append(_emit_operand(tok, resolver))
    return "".join(pieces).strip()


def _emit_operand(operand: str, resolver: FieldResolver) -> str:
    # Identifier-safe global markers come straight through the table.
    if operand in _GLOBAL_TO_PY:
        return _GLOBAL_TO_PY[operand]
    if _HEX_INT_RE.match(operand):
        return operand
    if _DEC_INT_RE.match(operand):
        return operand
    if _FLOAT_RE.match(operand):
        return operand
    if _VERSION_RE.match(operand):
        return f"pack_version({', '.join(operand.split('.'))})"
    if operand.upper() == "INFINITY":
        return "float('inf')"
    if not _IDENT_CHAR_RE.fullmatch(operand):
        raise ValueError(f"unexpected operand {operand!r}")
    return resolver(operand)


# ---- helpers used by the emitter for since/until/versions -----------------


def compile_version_literal(dotted: str) -> str:
    """Compile a bare dotted version (`'20.2.0.7'`) to a `pack_version(...)` call."""
    if not _VERSION_RE.match(dotted.strip()):
        raise ValueError(f"not a version literal: {dotted!r}")
    return f"pack_version({', '.join(dotted.strip().split('.'))})"


def compile_versions_set(
    versions_attr: str,
    schema: Schema,
    subst: ExprCompiler | None = None,
) -> str:
    """Compile a `versions="#SSE# #FO4# ..."` attribute to a Python `in` test.

    Expands `#...#` verset tokens, then maps each `V20_2_0_7_xxx` id to its
    `(version, user_version, bs_version)` tuple via `Schema.versions`. The
    resulting Python expression evaluates to True when ctx matches one of the
    listed versions.
    """
    sc = subst if subst is not None else ExprCompiler.for_schema(schema)
    table = sc._subst.get("versions")
    expanded = table.apply(versions_attr) if table is not None else versions_attr
    ids = expanded.split()
    triples: list[tuple[int, int, int]] = []
    for vid in ids:
        if vid not in schema.versions:
            # Unknown version id: skip (keeps codegen robust against schema
            # additions). Could also raise if strictness preferred.
            continue
        v: VersionDef = schema.versions[vid]
        triples.append(_version_triple(v))
    if not triples:
        return "False"
    body = ", ".join(f"({a}, {b}, {c})" for (a, b, c) in triples)
    return f"((ctx.version, ctx.user_version, ctx.bs_version) in {{{body}}})"


def _version_triple(v: VersionDef) -> tuple[int, int, int]:
    parts = [int(p) for p in v.num.split(".")]
    parts += [0] * (4 - len(parts))
    packed = (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]
    user = int(v.user) if v.user is not None else 0
    bsver = int(v.bsver) if v.bsver is not None else 0
    return (packed, user, bsver)
