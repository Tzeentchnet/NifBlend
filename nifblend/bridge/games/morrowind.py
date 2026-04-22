"""Morrowind (and pre-Skyrim) classic-material split helpers (Phase 8g).

Phase 6.25 already ships
:func:`nifblend.bridge.material_out.build_classic_material_blocks`, which
emits the ``NiMaterialProperty`` + ``NiTexturingProperty`` +
``NiSourceTexture`` trio at export time. This module is the pure
*validation / dry-run* companion: it answers "what blocks would the
classic path emit for this material?" without building them, so the
operator layer can surface a per-slot preview in the sidebar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nifblend.bridge.material_in import CLASSIC_TEXTURE_SLOT_NAMES, MaterialData

__all__ = [
    "ClassicSplitPreview",
    "preview_classic_split",
]


@dataclass(slots=True)
class ClassicSplitPreview:
    """Summary of the blocks :func:`build_classic_material_blocks` would emit."""

    emit_material_block: bool = True
    emit_texturing_block: bool = False
    populated_slots: list[tuple[str, str]] = field(default_factory=list)
    source_texture_count: int = 0


def preview_classic_split(data: MaterialData) -> ClassicSplitPreview:
    """Return what classic blocks would be emitted for ``data``.

    ``NiMaterialProperty`` is always emitted (holds ambient / diffuse /
    specular / emissive / glossiness). ``NiTexturingProperty`` is only
    emitted when at least one of the 12 classic slots is populated --
    matches the omission behaviour of
    :func:`nifblend.bridge.material_out.build_classic_material_blocks`.
    """
    populated: list[tuple[str, str]] = []
    for slot in CLASSIC_TEXTURE_SLOT_NAMES:
        path = data.textures.get(slot)
        if path:
            populated.append((slot, path))
    return ClassicSplitPreview(
        emit_material_block=True,
        emit_texturing_block=bool(populated),
        populated_slots=populated,
        source_texture_count=len(populated),
    )
