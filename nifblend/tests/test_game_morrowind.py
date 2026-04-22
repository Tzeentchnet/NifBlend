"""Tests for Phase 8g Morrowind classic-split preview helper."""

from __future__ import annotations

from nifblend.bridge.games.morrowind import preview_classic_split
from nifblend.bridge.material_in import MaterialData


def test_preview_empty_material_emits_material_only():
    data = MaterialData(name="mat")
    preview = preview_classic_split(data)
    assert preview.emit_material_block is True
    assert preview.emit_texturing_block is False
    assert preview.populated_slots == []
    assert preview.source_texture_count == 0


def test_preview_populated_slots_emits_texturing():
    data = MaterialData(name="mat")
    data.textures["diffuse"] = "textures/foo_d.dds"
    data.textures["normal"] = "textures/foo_n.dds"
    preview = preview_classic_split(data)
    assert preview.emit_texturing_block is True
    assert preview.source_texture_count == 2
    slot_names = [slot for slot, _ in preview.populated_slots]
    assert "diffuse" in slot_names
    assert "normal" in slot_names


def test_preview_ignores_unknown_classic_slots():
    data = MaterialData(name="mat")
    data.textures["nonsense"] = "textures/foo.dds"
    preview = preview_classic_split(data)
    assert preview.emit_texturing_block is False
    assert preview.source_texture_count == 0


def test_preview_preserves_slot_ordering():
    data = MaterialData(name="mat")
    # Insert in non-canonical order; preview must respect
    # CLASSIC_TEXTURE_SLOT_NAMES order.
    data.textures["glow"] = "g.dds"
    data.textures["diffuse"] = "d.dds"
    preview = preview_classic_split(data)
    order = [slot for slot, _ in preview.populated_slots]
    # diffuse comes before glow in CLASSIC_TEXTURE_SLOT_NAMES
    assert order.index("diffuse") < order.index("glow")
