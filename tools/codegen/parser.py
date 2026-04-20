"""Parse `nif.xml` into a typed in-memory schema AST.

The XML schema (root `<niftoolsxml>`) defines the NIF binary file format used
by Bethesda games. This parser does *not* interpret any cond/vercond
expressions — those are passed through verbatim as strings and compiled
later by `tools.codegen.cond_compiler`. The job here is purely structural:
walk every supported top-level element and produce dataclasses the emitter
can iterate.

Supported top-level kinds (counts from the vendored 2024-09 snapshot):

- `niobject` (~563): NIF block types with inheritance and ordered fields.
- `struct` (~162): re-usable compound types (no inheritance).
- `enum` (~111): named integer enumerations.
- `bitflags` (~24) / `bitfield` (~14): bit-packed enums (single-bit and
  multi-bit-field variants respectively).
- `basic` (~22): primitives backed by hand-written code in
  `nifblend.format.primitives`.
- `version` (~63): named version literals (e.g. `V20_2_0_7_SSE`).
- `token` (~7): macro substitutions for cond/vercond/etc. attributes.
- `module` (~13): grouping metadata (carried for traceability).
- `verattr` (~3): version-attribute access metadata (currently unused by emit).

Field attribute coverage (from the same snapshot):
`name, type, length, until, since, template, default, vercond, cond, arg,
calc, suffix, binary, excludeT, onlyT, abstract, arg1, arg2, width, range,
recursive`. Of these, the emitter actively uses
`name, type, length, since, until, template, vercond, cond, arg, default,
onlyT, excludeT`. The remainder are preserved on the AST for future use.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Schema",
    "NifObject",
    "Struct",
    "Field",
    "Enum",
    "EnumOption",
    "BitFlags",
    "BitField",
    "BitFieldMember",
    "Basic",
    "VersionDef",
    "Token",
    "TokenEntry",
    "parse_schema",
]


# ---- AST nodes ------------------------------------------------------------


@dataclass(slots=True)
class Field:
    """A single `<field>` element inside a `<niobject>` or `<struct>`.

    The `cond` / `vercond` / `arr1` (length) / `arg` / `calc` strings are
    stored verbatim; the cond compiler turns them into Python expressions
    later. `name` is the raw schema name (with spaces); the emitter
    converts to `snake_case` for attribute generation.
    """

    name: str
    type: str
    template: str | None = None
    length: str | None = None
    cond: str | None = None
    vercond: str | None = None
    since: str | None = None
    until: str | None = None
    arg: str | None = None
    calc: str | None = None
    default: str | None = None
    only_t: str | None = None
    exclude_t: str | None = None
    suffix: str | None = None
    binary: str | None = None
    width: str | None = None
    abstract: str | None = None
    arg1: str | None = None
    arg2: str | None = None
    range: str | None = None
    recursive: str | None = None
    # `<default onlyT="..." value="..." versions="..." />` overrides nested
    # under a `<field>`. Captured but currently unused by the emitter.
    default_overrides: list[dict[str, str]] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class NifObject:
    name: str
    inherit: str | None = None
    abstract: bool = False
    module: str | None = None
    versions: str | None = None  # space-separated version-id list
    fields: list[Field] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class Struct:
    name: str
    module: str | None = None
    generic: bool = False
    fields: list[Field] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class EnumOption:
    name: str
    value: int
    docstring: str = ""


@dataclass(slots=True)
class Enum:
    name: str
    storage: str
    options: list[EnumOption] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class BitFlagsOption:
    name: str
    bit: int
    docstring: str = ""


@dataclass(slots=True)
class BitFlags:
    name: str
    storage: str
    options: list[BitFlagsOption] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class BitFieldMember:
    name: str
    pos: int
    width: int
    type: str | None = None
    mask: int | None = None
    default: str | None = None


@dataclass(slots=True)
class BitField:
    """`<bitfield>` — multi-bit-field packed integer (distinct from `<bitflags>`)."""

    name: str
    storage: str
    members: list[BitFieldMember] = field(default_factory=list)
    docstring: str = ""


@dataclass(slots=True)
class Basic:
    """A `<basic>` primitive (e.g. `uint`, `byte`). Backed by hand-written code."""

    name: str
    integral: bool = False
    countable: bool = False
    size: int | None = None
    docstring: str = ""


@dataclass(slots=True)
class VersionDef:
    id: str
    num: str
    supported: bool = True
    user: str | None = None
    bsver: str | None = None
    docstring: str = ""


@dataclass(slots=True)
class TokenEntry:
    """One substitution rule inside a `<token>` group."""

    token: str
    string: str


@dataclass(slots=True)
class Token:
    """A `<token>` group: rules that apply to attributes in `attrs`.

    `attrs` is a space-separated list of attribute names (from the schema)
    where this token's substitutions apply, e.g. `"cond vercond"`.
    """

    name: str
    attrs: tuple[str, ...]
    entries: list[TokenEntry] = field(default_factory=list)


@dataclass(slots=True)
class Schema:
    schema_version: str
    niobjects: dict[str, NifObject] = field(default_factory=dict)
    structs: dict[str, Struct] = field(default_factory=dict)
    enums: dict[str, Enum] = field(default_factory=dict)
    bitflags: dict[str, BitFlags] = field(default_factory=dict)
    bitfields: dict[str, BitField] = field(default_factory=dict)
    basics: dict[str, Basic] = field(default_factory=dict)
    versions: dict[str, VersionDef] = field(default_factory=dict)
    tokens: list[Token] = field(default_factory=list)

    def all_type_names(self) -> Iterator[str]:
        yield from self.niobjects
        yield from self.structs
        yield from self.enums
        yield from self.bitflags
        yield from self.bitfields
        yield from self.basics


# ---- parser ---------------------------------------------------------------


def _text(elem: ET.Element) -> str:
    """Collect immediate text (excluding child element tails) and trim."""
    return (elem.text or "").strip()


def _bool(s: str | None, *, default: bool = False) -> bool:
    if s is None:
        return default
    return s.strip().lower() in ("1", "true", "yes")


def _parse_int(s: str) -> int:
    s = s.strip()
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s, 10)


def _parse_field(elem: ET.Element) -> Field:
    a = elem.attrib
    f = Field(
        name=a["name"],
        type=a["type"],
        template=a.get("template"),
        length=a.get("length"),
        cond=a.get("cond"),
        vercond=a.get("vercond"),
        since=a.get("since"),
        until=a.get("until"),
        arg=a.get("arg"),
        calc=a.get("calc"),
        default=a.get("default"),
        only_t=a.get("onlyT"),
        exclude_t=a.get("excludeT"),
        suffix=a.get("suffix"),
        binary=a.get("binary"),
        width=a.get("width"),
        abstract=a.get("abstract"),
        arg1=a.get("arg1"),
        arg2=a.get("arg2"),
        range=a.get("range"),
        recursive=a.get("recursive"),
        docstring=_text(elem),
    )
    for child in elem:
        if child.tag == "default":
            f.default_overrides.append(dict(child.attrib))
    return f


def _parse_niobject(elem: ET.Element) -> NifObject:
    a = elem.attrib
    nio = NifObject(
        name=a["name"],
        inherit=a.get("inherit"),
        abstract=_bool(a.get("abstract")),
        module=a.get("module"),
        versions=a.get("versions"),
        docstring=_text(elem),
    )
    for child in elem:
        if child.tag == "field":
            nio.fields.append(_parse_field(child))
    return nio


def _parse_struct(elem: ET.Element) -> Struct:
    a = elem.attrib
    s = Struct(
        name=a["name"],
        module=a.get("module"),
        generic=_bool(a.get("generic")),
        docstring=_text(elem),
    )
    for child in elem:
        if child.tag == "field":
            s.fields.append(_parse_field(child))
    return s


def _parse_enum(elem: ET.Element) -> Enum:
    a = elem.attrib
    e = Enum(name=a["name"], storage=a["storage"], docstring=_text(elem))
    for child in elem:
        if child.tag == "option":
            e.options.append(
                EnumOption(
                    name=child.attrib["name"],
                    value=_parse_int(child.attrib["value"]),
                    docstring=_text(child),
                )
            )
    return e


def _parse_bitflags(elem: ET.Element) -> BitFlags:
    a = elem.attrib
    bf = BitFlags(name=a["name"], storage=a["storage"], docstring=_text(elem))
    for child in elem:
        if child.tag == "option":
            bf.options.append(
                BitFlagsOption(
                    name=child.attrib["name"],
                    bit=_parse_int(child.attrib["bit"]),
                    docstring=_text(child),
                )
            )
    return bf


def _parse_bitfield(elem: ET.Element) -> BitField:
    a = elem.attrib
    bf = BitField(name=a["name"], storage=a["storage"], docstring=_text(elem))
    for child in elem:
        if child.tag == "member":
            ca = child.attrib
            bf.members.append(
                BitFieldMember(
                    name=ca["name"],
                    pos=_parse_int(ca["pos"]),
                    width=_parse_int(ca["width"]),
                    type=ca.get("type"),
                    mask=_parse_int(ca["mask"]) if "mask" in ca else None,
                    default=ca.get("default"),
                )
            )
    return bf


def _parse_basic(elem: ET.Element) -> Basic:
    a = elem.attrib
    return Basic(
        name=a["name"],
        integral=_bool(a.get("integral")),
        countable=_bool(a.get("countable")),
        size=int(a["size"]) if "size" in a else None,
        docstring=_text(elem),
    )


def _parse_version(elem: ET.Element) -> VersionDef:
    a = elem.attrib
    return VersionDef(
        id=a["id"],
        num=a["num"],
        supported=_bool(a.get("supported"), default=True),
        user=a.get("user"),
        bsver=a.get("bsver"),
        docstring=_text(elem),
    )


def _parse_token(elem: ET.Element) -> Token:
    a = elem.attrib
    attrs = tuple(a.get("attrs", "").split())
    tok = Token(name=a["name"], attrs=attrs)
    for child in elem:
        # The child tag varies (verexpr, condexpr, verset, default, range,
        # global, operator) but they all share the (token, string) attribute
        # pair. We don't care about the tag name for substitution purposes.
        ca = child.attrib
        if "token" in ca and "string" in ca:
            tok.entries.append(TokenEntry(token=ca["token"], string=ca["string"]))
    return tok


def parse_schema(path: Path | str) -> Schema:
    """Parse a `nif.xml` file into a `Schema` AST."""
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag != "niftoolsxml":
        raise ValueError(f"unexpected root element {root.tag!r}; want 'niftoolsxml'")

    schema = Schema(schema_version=root.attrib.get("version", "0.0.0"))

    for child in root:
        match child.tag:
            case "niobject":
                obj = _parse_niobject(child)
                schema.niobjects[obj.name] = obj
            case "struct":
                s = _parse_struct(child)
                schema.structs[s.name] = s
            case "enum":
                e = _parse_enum(child)
                schema.enums[e.name] = e
            case "bitflags":
                bf = _parse_bitflags(child)
                schema.bitflags[bf.name] = bf
            case "bitfield":
                bff = _parse_bitfield(child)
                schema.bitfields[bff.name] = bff
            case "basic":
                b = _parse_basic(child)
                schema.basics[b.name] = b
            case "version":
                v = _parse_version(child)
                schema.versions[v.id] = v
            case "token":
                schema.tokens.append(_parse_token(child))
            case "module" | "verattr":
                # Carried by the schema; not consumed by the current emitter.
                continue
            case _:
                # Unknown top-level tag: skip silently. nif.xml is occasionally
                # extended; new tags should not break codegen for existing ones.
                continue

    return schema
