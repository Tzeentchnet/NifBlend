"""Emit Python source for whitelisted NIF schema types.

Output structure:

    nifblend/format/generated/
    ├── __init__.py        — re-exports + version banner
    ├── enums.py           — IntEnum/IntFlag for <enum>/<bitflags>
    ├── bitfields.py       — typed dataclass + read/write for <bitfield>
    ├── structs.py         — dataclass + read/write for <struct>
    └── blocks.py          — dataclass + read/write for <niobject>

Inheritance handling: niobject fields are emitted in MRO order (root parent
first). For each field we emit, in this order, guards for `since`/`until`/
`vercond`/`cond`, then the type-dispatched read/write call, optionally
wrapped in a length loop or numpy bulk array call. Fields with `arg=` push
the arg value on `ctx.args` before the nested read and pop after.

Pragmatic gaps (clearly marked with `# CODEGEN-TODO:` in output):

- `Ref` / `Ptr` are read as raw u32 indices; resolution into actual block
  references is the bridge layer's job.
- Inline `string` (pre-v20) vs. header-indexed `string` (post-v20) is read as
  u32 unconditionally — bridge layer resolves later.
- Templated types (`type="Ref" template="NiExtraData"`) ignore the template
  parameter; templates are descriptive metadata, not run-time polymorphism.
- Fields whose type the emitter cannot resolve fall through to a `# CODEGEN-
  TODO: unknown type` marker that does not crash codegen but skips the field.

These shortcuts mean the generated layer is structurally complete (every
whitelisted block has a class, every field has an annotation) but some
fields will read raw scalars where richer semantics will eventually live.
The bridge layer (Phase 2 of the roadmap) builds on this foundation
incrementally.
"""

from __future__ import annotations

import keyword
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from io import StringIO

from .cond_compiler import (
    ExprCompiler,
    FieldResolver,
    compile_version_literal,
    compile_versions_set,
)
from .parser import (
    BitField,
    BitFlags,
    Enum,
    Field,
    NifObject,
    Schema,
    Struct,
)

__all__ = ["EmitResult", "emit_all"]


# ---- naming helpers -------------------------------------------------------


_SAFE_PUNCT_RE = re.compile(r"[^\w\s]")


def _snake(name: str) -> str:
    """Schema field name → Python attribute name.

    `'Num Vertices'` → `'num_vertices'`; `'BS Header\\BS Version'` →
    `'bs_header_bs_version'`. Reserved-word collisions get a trailing
    underscore (e.g. `'Class'` → `'class_'`).
    """
    cleaned = _SAFE_PUNCT_RE.sub(" ", name.replace("\\", " "))
    parts = cleaned.split()
    snake = "_".join(p.lower() for p in parts)
    if not snake:
        raise ValueError(f"empty snake-case for {name!r}")
    if keyword.iskeyword(snake):
        snake += "_"
    return snake


def _class_name(name: str) -> str:
    """Schema type name → Python class name. Schema names are already PascalCase,
    but a handful of Bethesda niobjects use C++-style scoping (`BSSkin::Instance`,
    `BSSkin::BoneData`) which is not a valid Python identifier — collapse `::`
    into nothing so `BSSkin::Instance` → `BSSkinInstance`."""
    return name.replace("::", "").replace(" ", "")


# ---- type dispatch --------------------------------------------------------


@dataclass(slots=True, frozen=True)
class _PrimSpec:
    """How to read/write a `<basic>` primitive."""

    py_type: str
    reader: str  # function name in primitives module, called as reader(stream)
    writer: str  # function name, called as writer(stream, value)
    array_reader: str | None = None  # bulk numpy reader, e.g. 'read_array_u32'
    array_writer: str | None = None
    default: str = "0"


# Schema basic name → primitive spec. Anything not listed falls back to
# scalar uint32 (Ref/Ptr-style) with a CODEGEN-TODO marker.
_PRIMITIVES: dict[str, _PrimSpec] = {
    "byte": _PrimSpec("int", "read_u8", "write_u8"),
    "char": _PrimSpec("int", "read_u8", "write_u8"),
    "sbyte": _PrimSpec("int", "read_i8", "write_i8"),
    "normbyte": _PrimSpec("int", "read_u8", "write_u8"),
    "ushort": _PrimSpec("int", "read_u16", "write_u16", "read_array_u16", "write_array_u16"),
    "short": _PrimSpec("int", "read_i16", "write_i16"),
    "uint": _PrimSpec("int", "read_u32", "write_u32", "read_array_u32", "write_array_u32"),
    "int": _PrimSpec("int", "read_i32", "write_i32"),
    "ulittle32": _PrimSpec("int", "read_u32", "write_u32", "read_array_u32", "write_array_u32"),
    "uint64": _PrimSpec("int", "read_u64", "write_u64"),
    "int64": _PrimSpec("int", "read_i64", "write_i64"),
    "float": _PrimSpec(
        "float", "read_f32", "write_f32", "read_array_f32", "write_array_f32", default="0.0"
    ),
    "hfloat": _PrimSpec("float", "read_f16", "write_f16", default="0.0"),
    "bool": _PrimSpec("bool", "read_bool", "write_bool", default="False"),
    "BlockTypeIndex": _PrimSpec("int", "read_u16", "write_u16"),
    "FileVersion": _PrimSpec("int", "read_u32", "write_u32"),
    "Ref": _PrimSpec("int", "read_i32", "write_i32"),
    "Ptr": _PrimSpec("int", "read_i32", "write_i32"),
    "StringOffset": _PrimSpec("int", "read_u32", "write_u32"),
    "NiFixedString": _PrimSpec("int", "read_u32", "write_u32"),
}


# ---- closure walker -------------------------------------------------------


def _expand_closure(schema: Schema, seeds: Iterable[str]) -> set[str]:
    """Walk inheritance + field types from `seeds`; return the full set to emit."""
    out: set[str] = set()
    stack: list[str] = list(seeds)
    while stack:
        name = stack.pop()
        if name in out:
            continue
        if name not in (
            schema.niobjects.keys()
            | schema.structs.keys()
            | schema.enums.keys()
            | schema.bitflags.keys()
            | schema.bitfields.keys()
        ):
            # External / primitive — no closure step.
            continue
        out.add(name)
        if name in schema.niobjects:
            n = schema.niobjects[name]
            if n.inherit:
                stack.append(n.inherit)
            for f in n.fields:
                stack.append(f.type)
                if f.template:
                    stack.append(f.template)
        elif name in schema.structs:
            s = schema.structs[name]
            for f in s.fields:
                stack.append(f.type)
                if f.template:
                    stack.append(f.template)
        elif name in schema.bitfields:
            for m in schema.bitfields[name].members:
                if m.type:
                    stack.append(m.type)
    return out


# ---- emit: enums + bitflags + bitfields -----------------------------------


_ENUM_HEADER = '''"""Generated NIF enums and bitflag types.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

__all__ = {all_list!r}
'''


def _enum_member(name: str) -> str:
    """Schema enum option name → Python identifier.

    Schema option names are usually `SHOUTY_SNAKE` already, but a handful
    (e.g. `Environment Map`) contain spaces. Replace non-identifier chars
    with `_`. Leading-digit names get an underscore prefix.
    """
    sanitized = re.sub(r"\W", "_", name).strip("_")
    if not sanitized:
        return "UNNAMED"
    if sanitized[0].isdigit():
        sanitized = "_" + sanitized
    if keyword.iskeyword(sanitized):
        sanitized += "_"
    return sanitized


def _emit_enum(e: Enum) -> str:
    buf = StringIO()
    buf.write(f"\n\nclass {_class_name(e.name)}(IntEnum):\n")
    if e.docstring:
        buf.write(f'    """{e.docstring}"""\n\n')
    if not e.options:
        buf.write("    NONE = 0\n")
        return buf.getvalue()
    seen: set[str] = set()
    for opt in e.options:
        member = _enum_member(opt.name)
        # Disambiguate accidental collisions after sanitization.
        candidate = member
        i = 2
        while candidate in seen:
            candidate = f"{member}_{i}"
            i += 1
        seen.add(candidate)
        buf.write(f"    {candidate} = {opt.value}\n")
    return buf.getvalue()


def _emit_bitflags(bf: BitFlags) -> str:
    buf = StringIO()
    buf.write(f"\n\nclass {_class_name(bf.name)}(IntFlag):\n")
    if bf.docstring:
        buf.write(f'    """{bf.docstring}"""\n\n')
    if not bf.options:
        buf.write("    NONE = 0\n")
        return buf.getvalue()
    seen: set[str] = set()
    for opt in bf.options:
        member = _enum_member(opt.name)
        candidate = member
        i = 2
        while candidate in seen:
            candidate = f"{member}_{i}"
            i += 1
        seen.add(candidate)
        buf.write(f"    {candidate} = 1 << {opt.bit}\n")
    return buf.getvalue()


_BITFIELD_HEADER = '''"""Generated NIF bitfields (multi-bit packed integers).

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import IO

from nifblend.format.base import Compound, ReadContext
from nifblend.format.primitives import (
    read_u8, read_u16, read_u32, read_u64,
    write_u8, write_u16, write_u32, write_u64,
)

__all__ = {all_list!r}
'''


_BITFIELD_STORAGE_READERS: dict[str, tuple[str, str, int]] = {
    # storage type → (reader, writer, default mask width)
    "byte": ("read_u8", "write_u8", 8),
    "ubyte": ("read_u8", "write_u8", 8),
    "ushort": ("read_u16", "write_u16", 16),
    "uint": ("read_u32", "write_u32", 32),
    "ulittle32": ("read_u32", "write_u32", 32),
    "uint64": ("read_u64", "write_u64", 64),
}


def _emit_bitfield(bf: BitField) -> str:
    storage = _BITFIELD_STORAGE_READERS.get(bf.storage)
    cls = _class_name(bf.name)
    buf = StringIO()
    buf.write("\n\n@dataclass(slots=True)\n")
    buf.write(f"class {cls}(Compound):\n")
    if bf.docstring:
        buf.write(f'    """{bf.docstring}"""\n\n')
    if not bf.members:
        buf.write("    raw: int = 0\n")
        buf.write(_emit_bitfield_rw(cls, storage, bf, simple=True))
        return buf.getvalue()
    for m in bf.members:
        buf.write(f"    {_snake(m.name)}: int = 0\n")
    buf.write(_emit_bitfield_rw(cls, storage, bf, simple=False))
    return buf.getvalue()


def _emit_bitfield_rw(
    cls: str, storage: tuple[str, str, int] | None, bf: BitField, *, simple: bool
) -> str:
    if storage is None:
        return (
            "\n    # CODEGEN-TODO: unknown storage type "
            f"{bf.storage!r}; bitfield read/write unavailable.\n"
        )
    reader, writer, _ = storage
    buf = StringIO()
    buf.write("\n    @classmethod\n")
    buf.write(f"    def read(cls, stream: IO[bytes], ctx: ReadContext) -> {cls}:\n")
    buf.write(f"        raw = {reader}(stream)\n")
    if simple:
        buf.write("        return cls(raw=raw)\n\n")
    else:
        buf.write("        return cls(\n")
        for m in bf.members:
            mask = (1 << m.width) - 1
            buf.write(f"            {_snake(m.name)}=(raw >> {m.pos}) & 0x{mask:X},\n")
        buf.write("        )\n\n")
    buf.write("    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:\n")
    if simple:
        buf.write(f"        {writer}(stream, self.raw)\n")
    else:
        buf.write("        raw = 0\n")
        for m in bf.members:
            mask = (1 << m.width) - 1
            buf.write(
                f"        raw |= (self.{_snake(m.name)} & 0x{mask:X}) << {m.pos}\n"
            )
        buf.write(f"        {writer}(stream, raw)\n")
    return buf.getvalue()


# ---- emit: structs + blocks (read/write with full conditionals) -----------


_STRUCT_HEADER = '''"""Generated NIF compound structs.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.base import Compound, ReadContext
from nifblend.format.primitives import (
    read_u8, read_u16, read_u32, read_u64,
    read_i8, read_i16, read_i32, read_i64,
    read_f32, read_f16, read_bool,
    read_array_u16, read_array_u32, read_array_f32,
    read_vec3_array, read_vec2_array,
    read_sized_string,
    write_u8, write_u16, write_u32, write_u64,
    write_i8, write_i16, write_i32, write_i64,
    write_f32, write_f16, write_bool,
    write_array_u16, write_array_u32, write_array_f32,
    write_vec3_array, write_vec2_array,
    write_sized_string,
)
from nifblend.format.versions import pack_version

__all__ = {all_list!r}
'''


_BLOCK_HEADER = '''"""Generated NIF block (niobject) types.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.base import Block, ReadContext
from nifblend.format.primitives import (
    read_u8, read_u16, read_u32, read_u64,
    read_i8, read_i16, read_i32, read_i64,
    read_f32, read_f16, read_bool,
    read_array_u16, read_array_u32, read_array_f32,
    read_vec3_array, read_vec2_array,
    read_sized_string,
    write_u8, write_u16, write_u32, write_u64,
    write_i8, write_i16, write_i32, write_i64,
    write_f32, write_f16, write_bool,
    write_array_u16, write_array_u32, write_array_f32,
    write_vec3_array, write_vec2_array,
    write_sized_string,
)
from nifblend.format.versions import pack_version

__all__ = {all_list!r}
'''


@dataclass(slots=True)
class _EmitContext:
    schema: Schema
    closure: set[str]
    expr: ExprCompiler
    # name -> kind classification ('block', 'struct', 'enum', 'bitflags',
    # 'bitfield', 'basic', or 'unknown'). Cached for fast lookup during emit.
    kinds: dict[str, str] = field(default_factory=dict)

    def kind(self, type_name: str) -> str:
        if type_name in self.kinds:
            return self.kinds[type_name]
        s = self.schema
        if type_name in s.niobjects:
            k = "block"
        elif type_name in s.structs:
            k = "struct"
        elif type_name in s.enums:
            k = "enum"
        elif type_name in s.bitflags:
            k = "bitflags"
        elif type_name in s.bitfields:
            k = "bitfield"
        elif type_name in s.basics:
            k = "basic"
        else:
            k = "unknown"
        self.kinds[type_name] = k
        return k


def _make_resolver(field_names: set[str]) -> FieldResolver:
    """Create a resolver that maps known schema field names to `self.<snake>`.

    Globals (`Version`, `User Version`, etc.) are intercepted upstream by the
    cond compiler; this function only sees the per-container field names.
    Unknown names fall through to a `self.<snake>` access — runtime
    `AttributeError` will surface bugs early during integration.
    """
    snake_map = {n: _snake(n) for n in field_names}

    def resolve(name: str) -> str:
        if name in snake_map:
            return f"self.{snake_map[name]}"
        # Unknown identifier: still emit a self-attribute access. The caller
        # may have a parent-class field; if not, runtime will raise.
        return f"self.{_snake(name)}"

    return resolve


def _flatten_fields(name: str, schema: Schema) -> list[Field]:
    """Walk inheritance chain root-first and return concatenated field list."""
    chain: list[NifObject] = []
    cur: NifObject | None = schema.niobjects.get(name)
    while cur is not None:
        chain.append(cur)
        cur = schema.niobjects.get(cur.inherit) if cur.inherit else None
    chain.reverse()
    out: list[Field] = []
    for nio in chain:
        out.extend(nio.fields)
    return out


def _field_py_default(f: Field, ctx: _EmitContext) -> str:
    if f.length is not None:
        # Arrays: numpy or list, depending on inner type primitiveness.
        kind = ctx.kind(f.type)
        if kind == "basic":
            spec = _PRIMITIVES.get(f.type)
            if spec is not None and spec.array_reader is not None:
                return "field(default_factory=lambda: np.empty(0))"
        return "field(default_factory=list)"
    kind = ctx.kind(f.type)
    if kind == "basic":
        spec = _PRIMITIVES.get(f.type)
        return spec.default if spec is not None else "0"
    if kind in ("enum", "bitflags"):
        return "0"
    if kind == "bitfield":
        return f"field(default_factory={_class_name(f.type)})"
    if kind in ("struct", "block"):
        return "None"
    return "None"


def _field_py_type(f: Field, ctx: _EmitContext) -> str:
    inner = _field_py_inner_type(f, ctx)
    if f.length is not None:
        kind = ctx.kind(f.type)
        if kind == "basic":
            spec = _PRIMITIVES.get(f.type)
            if spec is not None and spec.array_reader is not None:
                return "npt.NDArray[Any]"
        return f"list[{inner}]"
    return inner


def _field_py_inner_type(f: Field, ctx: _EmitContext) -> str:
    kind = ctx.kind(f.type)
    if kind == "basic":
        spec = _PRIMITIVES.get(f.type)
        return spec.py_type if spec is not None else "int"
    if kind in ("struct", "block", "bitfield"):
        return f'"{_class_name(f.type)} | None"'
    if kind in ("enum", "bitflags"):
        return "int"
    return "Any"


def _is_pure_comment_block(text: str) -> bool:
    """True if every non-blank line in `text` is a comment (would leave an
    enclosing `if:` body empty in Python)."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return False
    return True


def _emit_field_read(f: Field, ctx: _EmitContext, indent: str) -> str:
    """Emit the read statement(s) for one field, including all guards."""
    buf = StringIO()
    inner_indent = indent
    has_guard, guard_src = _build_guard(f, ctx)
    if has_guard:
        buf.write(f"{indent}if {guard_src}:\n")
        inner_indent = indent + "    "
    body = _emit_field_read_body(f, ctx, inner_indent)
    if not body:
        if has_guard:
            buf.write(f"{inner_indent}pass\n")
        return buf.getvalue() if has_guard else ""
    buf.write(body)
    if has_guard and _is_pure_comment_block(body):
        buf.write(f"{inner_indent}pass\n")
    return buf.getvalue()


def _safe_comment(text: str) -> str:
    """Strip newlines/colons from a string so it can be safely appended to a `# ...`
    inline comment without breaking surrounding Python syntax."""
    return text.replace("\n", " ").replace("\r", " ").replace(":", ";").strip()


def _build_guard(f: Field, ctx: _EmitContext) -> tuple[bool, str]:
    parts: list[str] = []
    resolver = _resolver_for_field(f, ctx)
    if f.since is not None:
        parts.append(f"ctx.version >= {compile_version_literal(f.since)}")
    if f.until is not None:
        parts.append(f"ctx.version <= {compile_version_literal(f.until)}")
    if f.vercond is not None:
        try:
            parts.append(f"({ctx.expr.compile_vercond(f.vercond, resolver)})")
        except Exception as exc:  # noqa: BLE001
            parts.append(f"False  # CODEGEN-TODO vercond {f.vercond!r}; {_safe_comment(str(exc))}")
    if f.cond is not None:
        try:
            parts.append(f"({ctx.expr.compile_cond(f.cond, resolver)})")
        except Exception as exc:  # noqa: BLE001
            parts.append(f"False  # CODEGEN-TODO cond {f.cond!r}; {_safe_comment(str(exc))}")
    if not parts:
        return False, ""
    # If any part is a `False  # ...` fallback, the whole `and` chain still
    # parses cleanly because `# ...` only extends to end of line — but each
    # sub-expression must be on its own physical line for the comment to
    # terminate before the ` and ` joiner. We therefore split with newlines
    # and a continuation indent so generated source remains valid.
    if any("CODEGEN-TODO" in p for p in parts):
        joined = "\n            and ".join(parts)
        return True, f"(\n            {joined}\n        )"
    return True, " and ".join(parts)


def _resolver_for_field(f: Field, ctx: _EmitContext) -> FieldResolver:
    # The resolver only needs to know names visible to expressions on this
    # field. Conservatively expose every field of every container the emitter
    # is currently processing — which we approximate by accepting any name
    # and routing it through `_snake`.
    return _make_resolver(set())


def _emit_field_read_body(f: Field, ctx: _EmitContext, indent: str) -> str:
    attr = f"self.{_snake(f.name)}"
    type_kind = ctx.kind(f.type)

    if f.length is not None:
        return _emit_array_read(f, ctx, indent, attr, type_kind)

    if type_kind == "basic":
        spec = _PRIMITIVES.get(f.type)
        if spec is None:
            return f"{indent}# CODEGEN-TODO: unsupported basic type {f.type!r} for {f.name!r}\n"
        return f"{indent}{attr} = {spec.reader}(stream)\n"

    if type_kind in ("enum", "bitflags"):
        # Storage size determines reader. Look up storage from schema.
        storage_reader = _enum_reader(f.type, ctx)
        return f"{indent}{attr} = {storage_reader}(stream)\n"

    if type_kind in ("struct", "block", "bitfield"):
        cls = _class_name(f.type)
        if f.arg is not None:
            arg_comment = ""
            try:
                arg_expr = ctx.expr.compile_arg(f.arg, _resolver_for_field(f, ctx))
            except Exception as exc:  # noqa: BLE001
                arg_expr = "0"
                arg_comment = (
                    f"{indent}# CODEGEN-TODO arg {f.arg!r}; {_safe_comment(str(exc))}\n"
                )
            return (
                f"{arg_comment}"
                f"{indent}ctx.push_arg({arg_expr})\n"
                f"{indent}try:\n"
                f"{indent}    {attr} = {cls}.read(stream, ctx)\n"
                f"{indent}finally:\n"
                f"{indent}    ctx.pop_arg()\n"
            )
        return f"{indent}{attr} = {cls}.read(stream, ctx)\n"

    return f"{indent}# CODEGEN-TODO: unknown type {f.type!r} for field {f.name!r}\n"


def _emit_array_read(
    f: Field, ctx: _EmitContext, indent: str, attr: str, type_kind: str
) -> str:
    try:
        length_expr = ctx.expr.compile_length(f.length or "0", _resolver_for_field(f, ctx))
    except Exception as exc:  # noqa: BLE001
        return f"{indent}# CODEGEN-TODO length {f.length!r}; {_safe_comment(str(exc))}\n"

    if type_kind == "basic":
        spec = _PRIMITIVES.get(f.type)
        if spec is not None and spec.array_reader is not None:
            return f"{indent}{attr} = {spec.array_reader}(stream, int({length_expr}))\n"
        if spec is not None:
            return (
                f"{indent}{attr} = [{spec.reader}(stream) "
                f"for _ in range(int({length_expr}))]\n"
            )
        return f"{indent}# CODEGEN-TODO: unsupported basic array type {f.type!r}\n"

    if type_kind in ("enum", "bitflags"):
        storage_reader = _enum_reader(f.type, ctx)
        return (
            f"{indent}{attr} = [{storage_reader}(stream) "
            f"for _ in range(int({length_expr}))]\n"
        )

    if type_kind in ("struct", "block", "bitfield"):
        cls = _class_name(f.type)
        return (
            f"{indent}{attr} = [{cls}.read(stream, ctx) "
            f"for _ in range(int({length_expr}))]\n"
        )

    return f"{indent}# CODEGEN-TODO: unknown array element type {f.type!r}\n"


def _enum_reader(type_name: str, ctx: _EmitContext) -> str:
    """Return the primitive reader that matches an enum/bitflags storage type."""
    storage: str | None = None
    if type_name in ctx.schema.enums:
        storage = ctx.schema.enums[type_name].storage
    elif type_name in ctx.schema.bitflags:
        storage = ctx.schema.bitflags[type_name].storage
    if storage is None:
        return "read_u32"
    spec = _PRIMITIVES.get(storage)
    return spec.reader if spec is not None else "read_u32"


def _enum_writer(type_name: str, ctx: _EmitContext) -> str:
    storage: str | None = None
    if type_name in ctx.schema.enums:
        storage = ctx.schema.enums[type_name].storage
    elif type_name in ctx.schema.bitflags:
        storage = ctx.schema.bitflags[type_name].storage
    if storage is None:
        return "write_u32"
    spec = _PRIMITIVES.get(storage)
    return spec.writer if spec is not None else "write_u32"


def _emit_field_write(f: Field, ctx: _EmitContext, indent: str) -> str:
    has_guard, guard_src = _build_guard(f, ctx)
    inner = indent
    buf = StringIO()
    if has_guard:
        buf.write(f"{indent}if {guard_src}:\n")
        inner = indent + "    "
    body = _emit_field_write_body(f, ctx, inner)
    if not body:
        if has_guard:
            buf.write(f"{inner}pass\n")
        return buf.getvalue() if has_guard else ""
    buf.write(body)
    if has_guard and _is_pure_comment_block(body):
        buf.write(f"{inner}pass\n")
    return buf.getvalue()


def _emit_field_write_body(f: Field, ctx: _EmitContext, indent: str) -> str:
    attr = f"self.{_snake(f.name)}"
    type_kind = ctx.kind(f.type)

    if f.length is not None:
        if type_kind == "basic":
            spec = _PRIMITIVES.get(f.type)
            if spec is not None and spec.array_writer is not None:
                return f"{indent}{spec.array_writer}(stream, {attr})\n"
            if spec is not None:
                return (
                    f"{indent}for __v in {attr}:\n"
                    f"{indent}    {spec.writer}(stream, __v)\n"
                )
            return f"{indent}# CODEGEN-TODO: unsupported basic array write {f.type!r}\n"
        if type_kind in ("enum", "bitflags"):
            writer = _enum_writer(f.type, ctx)
            return (
                f"{indent}for __v in {attr}:\n"
                f"{indent}    {writer}(stream, int(__v))\n"
            )
        if type_kind in ("struct", "block", "bitfield"):
            return (
                f"{indent}for __v in {attr}:\n"
                f"{indent}    __v.write(stream, ctx)\n"
            )
        return f"{indent}# CODEGEN-TODO: unknown array elem write {f.type!r}\n"

    if type_kind == "basic":
        spec = _PRIMITIVES.get(f.type)
        if spec is None:
            return f"{indent}# CODEGEN-TODO: unsupported basic write {f.type!r}\n"
        return f"{indent}{spec.writer}(stream, {attr})\n"

    if type_kind in ("enum", "bitflags"):
        writer = _enum_writer(f.type, ctx)
        return f"{indent}{writer}(stream, int({attr}))\n"

    if type_kind in ("struct", "block", "bitfield"):
        if f.arg is not None:
            arg_comment = ""
            try:
                arg_expr = ctx.expr.compile_arg(f.arg, _resolver_for_field(f, ctx))
            except Exception as exc:  # noqa: BLE001
                arg_expr = "0"
                arg_comment = (
                    f"{indent}# CODEGEN-TODO arg {f.arg!r}; {_safe_comment(str(exc))}\n"
                )
            return (
                f"{arg_comment}"
                f"{indent}ctx.push_arg({arg_expr})\n"
                f"{indent}try:\n"
                f"{indent}    {attr}.write(stream, ctx)\n"
                f"{indent}finally:\n"
                f"{indent}    ctx.pop_arg()\n"
            )
        return f"{indent}{attr}.write(stream, ctx)\n"

    return f"{indent}# CODEGEN-TODO: unknown type write {f.type!r}\n"


def _emit_struct(s: Struct, ctx: _EmitContext, *, base: str) -> str:
    cls = _class_name(s.name)
    buf = StringIO()
    buf.write("\n\n@dataclass(slots=True)\n")
    buf.write(f"class {cls}({base}):\n")
    if s.docstring:
        buf.write(f'    """{s.docstring}"""\n\n')
    if not s.fields:
        buf.write("    pass\n")
        return buf.getvalue()
    for f in s.fields:
        buf.write(
            f"    {_snake(f.name)}: {_field_py_type(f, ctx)} = {_field_py_default(f, ctx)}\n"
        )
    buf.write("\n    @classmethod\n")
    buf.write(f"    def read(cls, stream: IO[bytes], ctx: ReadContext) -> {cls}:\n")
    buf.write("        self = cls()\n")
    for f in s.fields:
        body = _emit_field_read(f, ctx, "        ")
        buf.write(body)
    buf.write("        return self\n\n")
    buf.write("    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:\n")
    wrote_any = False
    for f in s.fields:
        body = _emit_field_write(f, ctx, "        ")
        if body:
            buf.write(body)
            wrote_any = True
    if not wrote_any:
        buf.write("        return None\n")
    return buf.getvalue()


def _emit_block(n: NifObject, ctx: _EmitContext) -> str:
    cls = _class_name(n.name)
    fields = _flatten_fields(n.name, ctx.schema)
    buf = StringIO()
    buf.write("\n\n@dataclass(slots=True)\n")
    buf.write(f"class {cls}(Block):\n")
    if n.docstring:
        buf.write(f'    """{n.docstring}"""\n\n')
    if not fields:
        buf.write("    pass\n")
        return buf.getvalue()
    for f in fields:
        buf.write(
            f"    {_snake(f.name)}: {_field_py_type(f, ctx)} = {_field_py_default(f, ctx)}\n"
        )
    buf.write("\n    @classmethod\n")
    buf.write(f"    def read(cls, stream: IO[bytes], ctx: ReadContext) -> {cls}:\n")
    buf.write("        self = cls()\n")
    for f in fields:
        body = _emit_field_read(f, ctx, "        ")
        buf.write(body)
    buf.write("        return self\n\n")
    buf.write("    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:\n")
    wrote_any = False
    for f in fields:
        body = _emit_field_write(f, ctx, "        ")
        if body:
            buf.write(body)
            wrote_any = True
    if not wrote_any:
        buf.write("        return None\n")
    return buf.getvalue()


# ---- top-level emit entry point ------------------------------------------


@dataclass(slots=True)
class EmitResult:
    files: dict[str, str]


def emit_all(schema: Schema, seeds: Iterable[str]) -> EmitResult:
    """Emit four-file generated package as a `{filename: source}` dict."""
    closure = _expand_closure(schema, seeds)
    expr = ExprCompiler.for_schema(schema)
    ctx = _EmitContext(schema=schema, closure=closure, expr=expr)

    enums_to_emit = sorted(n for n in closure if n in schema.enums)
    bitflags_to_emit = sorted(n for n in closure if n in schema.bitflags)
    bitfields_to_emit = sorted(n for n in closure if n in schema.bitfields)
    structs_to_emit = sorted(n for n in closure if n in schema.structs)
    blocks_to_emit = sorted(n for n in closure if n in schema.niobjects)

    enum_all = [_class_name(n) for n in enums_to_emit] + [
        _class_name(n) for n in bitflags_to_emit
    ]
    enums_src = StringIO()
    enums_src.write(_ENUM_HEADER.format(all_list=enum_all))
    for n in enums_to_emit:
        enums_src.write(_emit_enum(schema.enums[n]))
    for n in bitflags_to_emit:
        enums_src.write(_emit_bitflags(schema.bitflags[n]))

    bitfields_src = StringIO()
    bf_all = [_class_name(n) for n in bitfields_to_emit]
    bitfields_src.write(_BITFIELD_HEADER.format(all_list=bf_all))
    for n in bitfields_to_emit:
        bitfields_src.write(_emit_bitfield(schema.bitfields[n]))

    structs_src = StringIO()
    structs_all = [_class_name(n) for n in structs_to_emit]
    structs_src.write(_STRUCT_HEADER.format(all_list=structs_all))
    # Emit referenced bitfield/enum/bitflags imports inline (already in
    # separate modules; cross-import here for type references).
    if bf_all or enum_all:
        if bf_all:
            structs_src.write(f"from .bitfields import {', '.join(bf_all)}  # noqa: F401\n")
        if enum_all:
            structs_src.write(f"from .enums import {', '.join(enum_all)}  # noqa: F401\n")
    for n in structs_to_emit:
        structs_src.write(_emit_struct(schema.structs[n], ctx, base="Compound"))

    blocks_src = StringIO()
    blocks_all = [_class_name(n) for n in blocks_to_emit]
    blocks_src.write(_BLOCK_HEADER.format(all_list=blocks_all))
    if structs_all:
        blocks_src.write(f"from .structs import {', '.join(structs_all)}  # noqa: F401\n")
    if bf_all:
        blocks_src.write(f"from .bitfields import {', '.join(bf_all)}  # noqa: F401\n")
    if enum_all:
        blocks_src.write(f"from .enums import {', '.join(enum_all)}  # noqa: F401\n")
    # Forward-declared self-refs are handled via string annotations elsewhere;
    # blocks reference each other freely. Emit in alphabetical order.
    for n in blocks_to_emit:
        blocks_src.write(_emit_block(schema.niobjects[n], ctx))

    init_src = (
        '"""Generated NIF type tree.\n\n'
        f"Schema version: {schema.schema_version}.\n"
        "DO NOT EDIT — regenerate via `python -m tools.codegen`.\n"
        '"""\n\n'
        "from .blocks import *  # noqa: F401, F403\n"
        "from .bitfields import *  # noqa: F401, F403\n"
        "from .enums import *  # noqa: F401, F403\n"
        "from .structs import *  # noqa: F401, F403\n"
    )

    return EmitResult(
        files={
            "__init__.py": init_src,
            "enums.py": enums_src.getvalue(),
            "bitfields.py": bitfields_src.getvalue(),
            "structs.py": structs_src.getvalue(),
            "blocks.py": blocks_src.getvalue(),
        }
    )
