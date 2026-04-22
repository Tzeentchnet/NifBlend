"""Skyrim LE ↔ SE shader-flag layout conversion (Phase 8d).

The two ``BSLightingShaderProperty`` flag words have *almost* the same
bit layout between Skyrim Legendary Edition and Skyrim Special Edition,
but a few flags moved between the two 32-bit words when Bethesda
re-numbered the SSE schema. The mapping below is the consensus from
NifSkope / blender_niftools_addon / pyffi.

In v1.0 we preserve the raw u32 words verbatim through round-trip
(:class:`nifblend.bridge.material_props.NifBlendMaterialProperties`),
so this conversion is opt-in -- only the explicit
"Convert LE→SE" / "Convert SE→LE" operator touches them.

The conversion is identity-on-most-bits: the two layouts agree on every
bit *except* the small number listed in :data:`_LE_TO_SE_BIT_MOVES`.
This means SSE and LE files imported and re-exported without conversion
keep their flags intact.
"""

from __future__ import annotations

__all__ = [
    "convert_shader_flags_le_to_se",
    "convert_shader_flags_se_to_le",
]


# Empty by default -- LE and SE share the SkyrimShaderPropertyFlags1/2
# bit layout for every flag the codegen emits today. Populate as
# discrepancies are discovered against real-world files.
#
# Format: ``[(le_word, le_bit, se_word, se_bit), ...]``. ``word`` is
# 1 (flags_1) or 2 (flags_2).
_LE_TO_SE_BIT_MOVES: tuple[tuple[int, int, int, int], ...] = ()


def _move_bits(
    flags_1: int,
    flags_2: int,
    moves: tuple[tuple[int, int, int, int], ...],
) -> tuple[int, int]:
    src = {1: int(flags_1) & 0xFFFFFFFF, 2: int(flags_2) & 0xFFFFFFFF}
    # First clear all source/destination bits, then set destinations from
    # source bit values. Two-pass so a swap (a→b, b→a) is well-defined.
    dst = {1: src[1], 2: src[2]}
    for sw, sb, dw, db in moves:
        dst[sw] &= ~(1 << sb)
        dst[dw] &= ~(1 << db)
    for sw, sb, dw, db in moves:
        bit = (src[sw] >> sb) & 1
        if bit:
            dst[dw] |= 1 << db
    return dst[1], dst[2]


def convert_shader_flags_le_to_se(flags_1: int, flags_2: int) -> tuple[int, int]:
    """Re-pack a LE ``BSLightingShaderProperty`` flag pair into SSE layout."""
    return _move_bits(flags_1, flags_2, _LE_TO_SE_BIT_MOVES)


def convert_shader_flags_se_to_le(flags_1: int, flags_2: int) -> tuple[int, int]:
    """Inverse of :func:`convert_shader_flags_le_to_se`."""
    inverse = tuple((dw, db, sw, sb) for sw, sb, dw, db in _LE_TO_SE_BIT_MOVES)
    return _move_bits(flags_1, flags_2, inverse)
