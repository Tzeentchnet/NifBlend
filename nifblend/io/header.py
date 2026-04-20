"""NIF file-header parsing and serialisation.

The codegen-emitted :class:`Header` struct in
:mod:`nifblend.format.generated.structs` covers everything in the on-disk
header *except* the leading ASCII "magic" line (a `HeaderString` in the
schema, which the codegen marks ``# CODEGEN-TODO``). This module fills in
that gap and orchestrates the read so :class:`ReadContext` is populated
correctly before any conditional fields are decoded.

We also bypass ``Header.read`` / ``Header.write`` entirely. The codegen
references ``ctx.user_version`` / ``ctx.bs_version`` inside the header's
own field guards (e.g. the BSStreamHeader condition uses
``ctx.user_version >= 3``), but the codegen never updates ``ctx`` from the
matching ``self.*`` reads as it goes -- so ``Header.read`` would, for
example, never read ``bs_header`` for a Skyrim SE file because the cursor
hasn't advanced past ``user_version`` yet from ``ctx``'s point of view.
We hand-roll the field sequence here, mirroring the codegen layout but
threading ``ctx`` updates inline.

Public surface:

- :func:`read_nif_header` -- read magic + Header, return ``(Header, ReadContext)``
- :func:`write_nif_header` -- inverse: write magic + Header from a populated dataclass
- :func:`format_magic` / :func:`parse_magic` -- helpers, exposed for tests
"""

from __future__ import annotations

import re
from typing import IO, Final

from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ByteArray,
    Header,
    SizedString,
)
from nifblend.format.primitives import (
    read_array_u32,
    read_u8,
    read_u16,
    read_u32,
    write_array_u32,
    write_u8,
    write_u16,
    write_u32,
)
from nifblend.format.versions import pack_version, unpack_version

__all__ = [
    "MAX_MAGIC_BYTES",
    "format_magic",
    "parse_magic",
    "read_nif_header",
    "write_nif_header",
]

# Reasonable upper bound on the magic line. Real files are well under 60
# bytes; we cap reads to keep a malformed file from making us scan forever.
MAX_MAGIC_BYTES: Final[int] = 128

# Schema also allows the older 3-component ``X.Y.Z`` form (pre-3.3.0.13).
_MAGIC_RE = re.compile(rb"^(?:NetImmerse|Gamebryo) File Format, Version (\d+\.\d+\.\d+(?:\.\d+)?)$")

# version >= 10.1.0.0 -> "Gamebryo File Format" prefix; older -> "NetImmerse".
_GAMEBRYO_THRESHOLD: Final[int] = pack_version(10, 1, 0, 0)


def parse_magic(line: bytes) -> int:
    """Parse a magic line (without trailing newline) into a packed version int."""
    m = _MAGIC_RE.match(line)
    if not m:
        raise ValueError(f"not a NIF magic line: {line!r}")
    parts = [int(p) for p in m.group(1).split(b".")]
    parts += [0] * (4 - len(parts))
    return pack_version(*parts)


def format_magic(version: int) -> bytes:
    """Inverse of :func:`parse_magic`. Returns the line *without* trailing ``\\n``."""
    prefix = b"Gamebryo" if version >= _GAMEBRYO_THRESHOLD else b"NetImmerse"
    major, minor, patch, sub = unpack_version(version)
    return b"%s File Format, Version %d.%d.%d.%d" % (prefix, major, minor, patch, sub)


def _read_magic_line(stream: IO[bytes]) -> int:
    """Read up to the first ``\\n``; return the parsed packed version.

    Advances the stream cursor to one byte past the newline.
    """
    cur = stream.tell()
    chunk = stream.read(MAX_MAGIC_BYTES)
    nl = chunk.find(b"\n")
    if nl < 0:
        raise ValueError(
            f"NIF magic line not terminated within {MAX_MAGIC_BYTES} bytes of offset {cur}"
        )
    line = chunk[:nl]
    # Tolerate stray CR-LF saved by hand-edited files.
    if line.endswith(b"\r"):
        line = line[:-1]
    version = parse_magic(line)
    stream.seek(cur + nl + 1, 0)
    return version


# ---- BS stream-header guard ------------------------------------------------
#
# Mirrors the schema vercond on `Header.bs_header` exactly, but reads from
# the *header* object we are populating rather than ctx (which the codegen
# does incorrectly).
def _has_bs_header(header: Header) -> bool:
    v = header.version
    uv = header.user_version
    if v == pack_version(10, 0, 1, 2):
        return True
    if v == pack_version(20, 2, 0, 7):
        return uv >= 3
    if v == pack_version(20, 0, 0, 5):
        return uv >= 3
    if pack_version(10, 1, 0, 0) <= v <= pack_version(20, 0, 0, 4) and uv <= 11:
        return uv >= 3
    return False


def read_nif_header(stream: IO[bytes]) -> tuple[Header, ReadContext]:
    """Read magic line + Header, returning the populated dataclass + context.

    The returned :class:`ReadContext` has ``version`` / ``user_version`` /
    ``bs_version`` populated from the on-disk values and is ready to drive
    subsequent ``Block.read`` calls.
    """
    ctx = ReadContext()
    ctx.version = _read_magic_line(stream)
    h = Header()

    # Pre-3.1 line-string copyright block is unsupported (out of scope for v0.1
    # and not needed for any post-Morrowind game). Reject explicitly so callers
    # don't get garbled headers.
    if ctx.version <= pack_version(3, 1, 0, 0):
        raise NotImplementedError(
            "pre-3.1 NIF headers (with copyright LineString table) are not "
            "supported; earliest covered game is Morrowind (4.0.0.2)"
        )

    if ctx.version >= pack_version(3, 1, 0, 1):
        h.version = read_u32(stream)
        # Magic-line and in-header version disagree: the on-disk u32 wins
        # (the textual hint is informational only). Mirror back into ctx so
        # later guards stay consistent.
        ctx.version = h.version

    if ctx.version >= pack_version(20, 0, 0, 3):
        h.endian_type = read_u8(stream)

    if ctx.version >= pack_version(10, 0, 1, 8):
        h.user_version = read_u32(stream)
        ctx.user_version = h.user_version

    if ctx.version >= pack_version(3, 1, 0, 1):
        h.num_blocks = read_u32(stream)

    if _has_bs_header(h):
        h.bs_header = BSStreamHeader.read(stream, ctx)
        ctx.bs_version = h.bs_header.bs_version

    if ctx.version >= pack_version(30, 0, 0, 0):
        h.metadata = ByteArray.read(stream, ctx)

    if ctx.version >= pack_version(5, 0, 0, 1):
        h.num_block_types = read_u16(stream)

    if ctx.version >= pack_version(5, 0, 0, 1) and ctx.version != pack_version(20, 3, 1, 2):
        h.block_types = [SizedString.read(stream, ctx) for _ in range(h.num_block_types)]

    if ctx.version == pack_version(20, 3, 1, 2):
        h.block_type_hashes = read_array_u32(stream, h.num_block_types)

    if ctx.version >= pack_version(5, 0, 0, 1):
        h.block_type_index = [read_u16(stream) for _ in range(h.num_blocks)]

    if ctx.version >= pack_version(20, 2, 0, 5):
        h.block_size = read_array_u32(stream, h.num_blocks)

    if ctx.version >= pack_version(20, 1, 0, 1):
        h.num_strings = read_u32(stream)
        h.max_string_length = read_u32(stream)
        h.strings = [SizedString.read(stream, ctx) for _ in range(h.num_strings)]

    if ctx.version >= pack_version(5, 0, 0, 6):
        h.num_groups = read_u32(stream)
        h.groups = read_array_u32(stream, h.num_groups)

    return h, ctx


def write_nif_header(stream: IO[bytes], header: Header, ctx: ReadContext) -> None:
    """Write the magic line + Header to ``stream``.

    ``ctx`` must be consistent with ``header`` (typically by setting
    ``ctx.version = header.version`` etc.) before this call. The writer does
    *not* re-derive count fields from the list lengths -- the caller is
    responsible for keeping ``num_block_types`` / ``num_blocks`` /
    ``num_strings`` / ``num_groups`` aligned with their respective lists.
    """
    if ctx.version <= pack_version(3, 1, 0, 0):
        raise NotImplementedError(
            "pre-3.1 NIF headers (with copyright LineString table) are not supported"
        )

    stream.write(format_magic(ctx.version))
    stream.write(b"\n")

    if ctx.version >= pack_version(3, 1, 0, 1):
        write_u32(stream, header.version)

    if ctx.version >= pack_version(20, 0, 0, 3):
        write_u8(stream, header.endian_type)

    if ctx.version >= pack_version(10, 0, 1, 8):
        write_u32(stream, header.user_version)

    if ctx.version >= pack_version(3, 1, 0, 1):
        write_u32(stream, header.num_blocks)

    if _has_bs_header(header):
        if header.bs_header is None:
            raise ValueError("header.bs_header is required for this version/user combo")
        header.bs_header.write(stream, ctx)

    if ctx.version >= pack_version(30, 0, 0, 0):
        if header.metadata is None:
            raise ValueError("header.metadata is required for version >= 30.0.0.0")
        header.metadata.write(stream, ctx)

    if ctx.version >= pack_version(5, 0, 0, 1):
        write_u16(stream, header.num_block_types)

    if ctx.version >= pack_version(5, 0, 0, 1) and ctx.version != pack_version(20, 3, 1, 2):
        for s in header.block_types:
            if s is None:
                raise ValueError("header.block_types contains None")
            s.write(stream, ctx)

    if ctx.version == pack_version(20, 3, 1, 2):
        write_array_u32(stream, header.block_type_hashes)

    if ctx.version >= pack_version(5, 0, 0, 1):
        for idx in header.block_type_index:
            write_u16(stream, idx)

    if ctx.version >= pack_version(20, 2, 0, 5):
        write_array_u32(stream, header.block_size)

    if ctx.version >= pack_version(20, 1, 0, 1):
        write_u32(stream, header.num_strings)
        write_u32(stream, header.max_string_length)
        for s in header.strings:
            if s is None:
                raise ValueError("header.strings contains None")
            s.write(stream, ctx)

    if ctx.version >= pack_version(5, 0, 0, 6):
        write_u32(stream, header.num_groups)
        write_array_u32(stream, header.groups)
