"""Unit tests for :mod:`nifblend.io.header` and :mod:`nifblend.io.block_table`.

We exercise three layers:

1. Magic-line parser/formatter (pure string-handling, no header struct).
2. Round-trip of a minimal Skyrim SE-shaped header (empty block list).
3. End-to-end :func:`read_nif` / :func:`write_nif` round-trip with two
   ``BSAnimNotes`` blocks -- chosen because ``BSAnimNotes`` has no nested
   compounds or ``string`` fields, so the test stays free of bridge-layer
   concerns (string-table resolution, ref dereferencing, ...).
"""

from __future__ import annotations

import io

import numpy as np
import pytest

from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import BSAnimNotes
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
    SizedString,
)
from nifblend.format.versions import (
    GameProfile,
    detect_profile,
    pack_version,
)
from nifblend.io import (
    BlockTable,
    read_nif,
    read_nif_header,
    write_nif,
    write_nif_header,
)
from nifblend.io.header import format_magic, parse_magic

# ---- helpers --------------------------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_bs_header() -> BSStreamHeader:
    """A bare BSStreamHeader for SSE (bs_version=100, all strings empty)."""
    return BSStreamHeader(
        bs_version=100,
        author=_empty_export_string(),
        process_script=_empty_export_string(),
        export_script=_empty_export_string(),
    )


def _sse_header(num_blocks: int = 0) -> tuple[Header, ReadContext]:
    """Construct a Skyrim SE shaped header with ``num_blocks`` slots reserved.

    Block-types / sizes / index arrays are left empty -- :func:`write_nif`
    fills them in from the actual block list. Use this when you intend to
    feed the header straight into ``BlockTable`` + ``write_nif``.
    """
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,  # 1 = little-endian (NIF convention)
        user_version=12,
        num_blocks=num_blocks,
        bs_header=_sse_bs_header(),
        num_block_types=0,
        block_types=[],
        block_type_index=[],
        block_size=np.empty(0, dtype=np.uint32),
        num_strings=0,
        max_string_length=0,
        strings=[],
        num_groups=0,
        groups=np.empty(0, dtype=np.uint32),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return h, ctx


# ---- magic-line parser ----------------------------------------------------


@pytest.mark.parametrize(
    ("line", "version"),
    [
        (b"Gamebryo File Format, Version 20.2.0.7", pack_version(20, 2, 0, 7)),
        (b"Gamebryo File Format, Version 10.1.0.0", pack_version(10, 1, 0, 0)),
        (b"NetImmerse File Format, Version 4.0.0.2", pack_version(4, 0, 0, 2)),
        (b"NetImmerse File Format, Version 10.0.1.0", pack_version(10, 0, 1, 0)),
    ],
)
def test_parse_magic_known_lines(line: bytes, version: int) -> None:
    assert parse_magic(line) == version


def test_parse_magic_three_component_pads_with_zero() -> None:
    # The schema allows ``X.Y.Z`` for very old NetImmerse files; we pad the
    # missing sub-component with 0 so packed comparisons still work.
    assert parse_magic(b"NetImmerse File Format, Version 3.3.0") == pack_version(3, 3, 0, 0)


def test_parse_magic_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="not a NIF magic line"):
        parse_magic(b"hello world")


@pytest.mark.parametrize(
    ("version", "expected_prefix"),
    [
        (pack_version(20, 2, 0, 7), b"Gamebryo"),
        (pack_version(10, 1, 0, 0), b"Gamebryo"),
        (pack_version(10, 0, 1, 0), b"NetImmerse"),
        (pack_version(4, 0, 0, 2), b"NetImmerse"),
    ],
)
def test_format_magic_prefix_threshold(version: int, expected_prefix: bytes) -> None:
    assert format_magic(version).startswith(expected_prefix)


def test_format_magic_roundtrips_through_parse() -> None:
    for v in (
        pack_version(20, 2, 0, 7),
        pack_version(20, 0, 0, 5),
        pack_version(10, 0, 1, 0),
        pack_version(4, 0, 0, 2),
    ):
        assert parse_magic(format_magic(v)) == v


# ---- header read/write round-trip ----------------------------------------


def test_sse_header_roundtrip() -> None:
    header, ctx = _sse_header(num_blocks=0)
    sink = io.BytesIO()
    write_nif_header(sink, header, ctx)
    raw = sink.getvalue()

    # Sanity: the magic line is the first thing on the wire.
    assert raw.startswith(b"Gamebryo File Format, Version 20.2.0.7\n")

    src = io.BytesIO(raw)
    parsed, parsed_ctx = read_nif_header(src)
    # Stream cursor sits at end-of-header (no extra payload to read).
    assert src.tell() == len(raw)

    assert parsed.version == header.version
    assert parsed.user_version == header.user_version
    assert parsed.endian_type == header.endian_type
    assert parsed.num_blocks == 0
    assert parsed.bs_header is not None
    assert parsed.bs_header.bs_version == 100
    assert parsed_ctx.bs_version == 100
    assert parsed_ctx.user_version == 12
    assert parsed_ctx.version == pack_version(20, 2, 0, 7)


def test_header_read_rejects_pre_3_1_lineblock() -> None:
    # Synthesise a magic line for a version we explicitly do not parse.
    raw = format_magic(pack_version(3, 0, 0, 0)) + b"\n"
    with pytest.raises(NotImplementedError, match=r"pre-3\.1"):
        read_nif_header(io.BytesIO(raw))


def test_header_read_rejects_unterminated_magic() -> None:
    # 200 bytes of garbage with no newline.
    raw = b"X" * 200
    with pytest.raises(ValueError, match="not terminated"):
        read_nif_header(io.BytesIO(raw))


def test_header_read_tolerates_crlf_in_magic() -> None:
    raw = b"Gamebryo File Format, Version 20.2.0.7\r\n"
    # Build the rest of the header using the writer so the suffix is correct.
    header, ctx = _sse_header(num_blocks=0)
    suffix = io.BytesIO()
    write_nif_header(suffix, header, ctx)
    # Replace the writer-generated magic (LF) with our CRLF variant.
    nl = suffix.getvalue().index(b"\n")
    payload = raw + suffix.getvalue()[nl + 1 :]
    parsed, _ = read_nif_header(io.BytesIO(payload))
    assert parsed.version == pack_version(20, 2, 0, 7)


# ---- BlockTable end-to-end -----------------------------------------------


def _ban_block(notes: list[int]) -> BSAnimNotes:
    return BSAnimNotes(num_anim_notes=len(notes), anim_notes=list(notes))


def test_block_table_roundtrip_two_simple_blocks() -> None:
    header, ctx = _sse_header(num_blocks=0)  # write_nif fills num_blocks
    blocks = [_ban_block([1, 2, 3]), _ban_block([42])]
    footer = Footer(num_roots=1, roots=[0])
    table = BlockTable(header=header, blocks=list(blocks), footer=footer, ctx=ctx)

    sink = io.BytesIO()
    write_nif(sink, table)
    raw = sink.getvalue()

    parsed = read_nif(io.BytesIO(raw))
    assert parsed.header.num_blocks == 2
    assert parsed.header.num_block_types == 1  # BSAnimNotes deduplicated
    assert parsed.block_type_name(0) == "BSAnimNotes"
    assert parsed.block_type_name(1) == "BSAnimNotes"
    assert [int(s) for s in parsed.header.block_size] == [
        2 + 4 * 3,  # u16 count + 3*i32
        2 + 4 * 1,  # u16 count + 1*i32
    ]
    assert isinstance(parsed.blocks[0], BSAnimNotes)
    assert parsed.blocks[0].anim_notes == [1, 2, 3]
    assert parsed.blocks[1].anim_notes == [42]
    assert parsed.footer.num_roots == 1
    assert parsed.footer.roots == [0]


def test_block_table_roundtrip_zero_blocks() -> None:
    header, ctx = _sse_header(num_blocks=0)
    table = BlockTable(header=header, blocks=[], footer=Footer(), ctx=ctx)
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))
    assert parsed.header.num_blocks == 0
    assert parsed.blocks == []


def test_block_table_unknown_type_raises() -> None:
    # Construct a header that claims a block of an unknown type, then verify
    # `read_nif` reports it (rather than producing garbage data).
    header, ctx = _sse_header(num_blocks=1)
    header.num_block_types = 1
    header.block_types = [SizedString(length=7, value=list(b"NotReal"))]
    header.block_type_index = [0]
    header.block_size = np.asarray([0], dtype=np.uint32)

    sink = io.BytesIO()
    write_nif_header(sink, header, ctx)
    Footer().write(sink, ctx)

    with pytest.raises(KeyError, match="NotReal"):
        read_nif(io.BytesIO(sink.getvalue()))


def test_block_table_size_mismatch_raises() -> None:
    # Real round-trip first, then corrupt the block_size table and reparse.
    header, ctx = _sse_header(num_blocks=0)
    blocks = [_ban_block([7])]
    table = BlockTable(header=header, blocks=blocks, footer=Footer(), ctx=ctx)
    sink = io.BytesIO()
    write_nif(sink, table)
    raw = bytearray(sink.getvalue())

    # Locate the (single-element) block_size array in the serialised header
    # by reading the file back with a fresh parser, then patch its bytes.
    parsed = read_nif(io.BytesIO(bytes(raw)))
    assert parsed.blocks[0].anim_notes == [7]

    # The block_size u32 sits immediately before the per-string table; rather
    # than computing its offset by hand, scan for the known correct value
    # (6 = 2+4*1) and bump it.
    target = (2 + 4).to_bytes(4, "little")
    pos = raw.find(target)
    assert pos > 0
    raw[pos : pos + 4] = (999).to_bytes(4, "little")

    with pytest.raises(ValueError, match=r"header\.block_size"):
        read_nif(io.BytesIO(bytes(raw)))


# ---- GameProfile ---------------------------------------------------------


@pytest.mark.parametrize(
    ("v", "uv", "bsv", "expected"),
    [
        (pack_version(20, 2, 0, 7), 12, 100, GameProfile.SKYRIM_SE),
        (pack_version(20, 2, 0, 7), 12, 83, GameProfile.SKYRIM_LE),
        (pack_version(20, 2, 0, 7), 12, 130, GameProfile.FALLOUT_4),
        (pack_version(20, 2, 0, 7), 12, 155, GameProfile.FALLOUT_76),
        (pack_version(20, 2, 0, 7), 12, 172, GameProfile.STARFIELD),
        (pack_version(20, 2, 0, 7), 11, 34, GameProfile.FALLOUT_3_NV),
        (pack_version(20, 0, 0, 5), 11, 0, GameProfile.OBLIVION),
        (pack_version(4, 0, 0, 2), 0, 0, GameProfile.MORROWIND),
        (pack_version(99, 0, 0, 0), 0, 0, GameProfile.UNKNOWN),
    ],
)
def test_detect_profile(v: int, uv: int, bsv: int, expected: GameProfile) -> None:
    assert detect_profile(v, uv, bsv) is expected
