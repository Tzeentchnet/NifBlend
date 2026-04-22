"""Phase 5 step 18 -- KF (animation) file detection and round-trip.

A `.kf` is structurally identical to a `.nif`: the same magic line, the
same header, block table, footer. The only difference is that the
footer's root is a :class:`NiControllerSequence` instead of a
:class:`NiNode`. These tests confirm the existing
:func:`nifblend.io.block_table.read_nif` / ``write_nif`` pipeline
handles a KF root end-to-end and that
:mod:`nifblend.io.kf`'s detection helpers behave correctly.

The synthesised sequences here intentionally use ``num_controlled_blocks
= 0`` so they don't trip the codegen ``#T#`` template gap on
:class:`Key` / :class:`QuatKey` (tracked by ROADMAP step 2f); the goal
of step 18 is reader/writer parity for KF *file* shape, not key-by-key
animation decoding (which is step 19's job).
"""

from __future__ import annotations

import io

import pytest

from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import (
    BSTriShape,
    NiControllerSequence,
    NiNode,
)
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, read_nif, write_nif
from nifblend.io.kf import is_kf_file, iter_controller_sequences, kf_root_sequences

# ---- helpers --------------------------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_table(blocks: list, *, roots: list[int]) -> BlockTable:
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return BlockTable(
        header=h,
        blocks=list(blocks),
        footer=Footer(num_roots=len(roots), roots=list(roots)),
        ctx=ctx,
    )


def _empty_sequence(*, name_index: int = 0xFFFFFFFF) -> NiControllerSequence:
    """Build a NiControllerSequence with no controlled blocks (avoids the
    `#T#` template gap on ``Key`` / ``QuatKey``).

    Every field the writer touches for SSE (version 20.2.0.7,
    bs_version=100) is set explicitly so the round-trip comparison is
    meaningful.
    """
    return NiControllerSequence(
        name=nif_string(index=name_index),
        num_controlled_blocks=0,
        array_grow_by=0,
        controlled_blocks=[],
        weight=1.0,
        text_keys=-1,  # NiTextKeyExtraData ref; -1 = none
        cycle_type=0,  # CYCLE_LOOP
        frequency=1.0,
        start_time=0.0,
        stop_time=2.5,
        manager=-1,
        accum_root_name=nif_string(index=0xFFFFFFFF),
        accum_flags=0,
        # bs_version=100 > 28 so we use anim_note_arrays, not anim_notes:
        num_anim_note_arrays=0,
        anim_note_arrays=[],
    )


# ---- tests ----------------------------------------------------------------


def test_is_kf_file_empty_table_returns_false() -> None:
    table = _sse_table([], roots=[])
    assert is_kf_file(table) is False


def test_is_kf_file_nif_root_returns_false() -> None:
    """A regular `.nif` (NiNode root) must not be detected as a KF file."""
    node = NiNode()
    table = _sse_table([node], roots=[0])
    assert is_kf_file(table) is False


def test_is_kf_file_sequence_root_returns_true() -> None:
    seq = _empty_sequence()
    table = _sse_table([seq], roots=[0])
    assert is_kf_file(table) is True


def test_is_kf_file_out_of_range_root_returns_false() -> None:
    seq = _empty_sequence()
    table = _sse_table([seq], roots=[5])  # 5 is past end of blocks
    assert is_kf_file(table) is False


def test_is_kf_file_negative_root_returns_false() -> None:
    seq = _empty_sequence()
    table = _sse_table([seq], roots=[-1])
    assert is_kf_file(table) is False


def test_is_kf_file_mixed_roots_returns_false() -> None:
    """If any root is not a sequence, it's not a KF file."""
    seq = _empty_sequence()
    node = NiNode()
    table = _sse_table([seq, node], roots=[0, 1])
    assert is_kf_file(table) is False


def test_kf_root_sequences_returns_only_root_sequences() -> None:
    """`kf_root_sequences` returns exactly the footer-root sequences,
    in declaration order.
    """
    seq_a = _empty_sequence(name_index=0)
    seq_b = _empty_sequence(name_index=1)
    table = _sse_table([seq_a, seq_b], roots=[1, 0])
    roots = kf_root_sequences(table)
    assert roots == [seq_b, seq_a]


def test_kf_root_sequences_rejects_non_kf() -> None:
    table = _sse_table([NiNode()], roots=[0])
    with pytest.raises(ValueError, match="not a KF file"):
        kf_root_sequences(table)


def test_iter_controller_sequences_yields_all_sequences_regardless_of_roots() -> None:
    """`iter_controller_sequences` finds sequences anywhere in the block
    table -- e.g. NiControllerManager-referenced sequences in a regular
    `.nif`.
    """
    seq_a = _empty_sequence(name_index=0)
    seq_b = _empty_sequence(name_index=1)
    node = NiNode()
    table = _sse_table([node, seq_a, seq_b], roots=[0])  # NiNode root, not KF
    assert list(iter_controller_sequences(table)) == [seq_a, seq_b]


def test_kf_round_trip_preserves_sequence_fields() -> None:
    """End-to-end: build a KF-shaped BlockTable, serialise via write_nif,
    deserialise via read_nif, assert the sequence's scalar fields and
    the file's KF detection both survive.
    """
    seq = _empty_sequence()
    seq.weight = 0.75
    seq.frequency = 1.5
    seq.start_time = 0.25
    seq.stop_time = 4.0
    seq.cycle_type = 1  # CYCLE_REVERSE

    table = _sse_table([seq], roots=[0])

    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    assert parsed.header.num_blocks == 1
    assert parsed.block_type_name(0) == "NiControllerSequence"
    assert is_kf_file(parsed) is True

    [rt] = kf_root_sequences(parsed)
    assert isinstance(rt, NiControllerSequence)
    assert rt.num_controlled_blocks == 0
    assert rt.array_grow_by == 0
    assert rt.weight == pytest.approx(0.75)
    assert rt.frequency == pytest.approx(1.5)
    assert rt.start_time == pytest.approx(0.25)
    assert rt.stop_time == pytest.approx(4.0)
    assert rt.cycle_type == 1
    assert rt.text_keys == -1
    assert rt.manager == -1
    # accum_flags is only on disk for version >= 20.3.0.8; SSE (20.2.0.7) skips it.
    assert rt.num_anim_note_arrays == 0
    assert rt.anim_note_arrays == []


def test_multi_sequence_kf_round_trip_preserves_block_order() -> None:
    """Multi-sequence KF: two sequences, both rooted, survive a
    write/read cycle with their order and fields intact.
    """
    seq_a = _empty_sequence()
    seq_a.start_time = 0.0
    seq_a.stop_time = 1.0
    seq_b = _empty_sequence()
    seq_b.start_time = 1.0
    seq_b.stop_time = 3.5

    table = _sse_table([seq_a, seq_b], roots=[0, 1])
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    assert parsed.header.num_blocks == 2
    assert is_kf_file(parsed) is True
    rt_a, rt_b = kf_root_sequences(parsed)
    assert rt_a.start_time == pytest.approx(0.0)
    assert rt_a.stop_time == pytest.approx(1.0)
    assert rt_b.start_time == pytest.approx(1.0)
    assert rt_b.stop_time == pytest.approx(3.5)


def test_iter_controller_sequences_in_mixed_nif_with_other_blocks() -> None:
    """A regular `.nif` carrying a BSTriShape plus an embedded sequence:
    `is_kf_file` is False (NiNode-style root expected by callers), but
    `iter_controller_sequences` still finds the sequence.
    """
    shape = BSTriShape()
    seq = _empty_sequence()
    table = _sse_table([NiNode(), shape, seq], roots=[0])
    assert is_kf_file(table) is False
    assert list(iter_controller_sequences(table)) == [seq]
