"""Tests for nifblend.bridge.games.skyrim shader-flag conversion."""

from __future__ import annotations

from nifblend.bridge.games.skyrim import (
    convert_shader_flags_le_to_se,
    convert_shader_flags_se_to_le,
)


def test_round_trip_default_table_is_identity():
    """With no documented bit-moves yet the conversion is identity."""
    f1, f2 = 0xDEADBEEF, 0xCAFEBABE
    assert convert_shader_flags_le_to_se(f1, f2) == (f1, f2)
    assert convert_shader_flags_se_to_le(f1, f2) == (f1, f2)


def test_round_trip_zero():
    assert convert_shader_flags_le_to_se(0, 0) == (0, 0)


def test_le_to_se_to_le_round_trip():
    pairs = [(0, 0), (0xFFFFFFFF, 0xFFFFFFFF), (0x12345678, 0x9ABCDEF0)]
    for f1, f2 in pairs:
        se = convert_shader_flags_le_to_se(f1, f2)
        le = convert_shader_flags_se_to_le(*se)
        assert le == (f1, f2)
