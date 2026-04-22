"""Phase 6 step 25 — classic Morrowind / Oblivion material tests.

Covers the ``NiMaterialProperty`` + ``NiTexturingProperty`` +
``NiSourceTexture`` triple that pre-Skyrim NIFs attach to a
``NiTriShape``'s property list:

* :func:`niclassic_to_material_data` — pure decoder over hand-built
  codegen blocks (no NIF parsing): default fallbacks, ambient / diffuse
  / specular / emissive colour propagation, glossiness + alpha +
  emissive-mult, ``apply_mode`` / ``texturing_flags`` preservation,
  per-slot ``TexDesc`` resolution against sibling ``NiSourceTexture``
  blocks (legacy inline ``SizedString`` ``file_name`` shape used by
  Morrowind / Oblivion), null-ref / wrong-type / out-of-range defence,
  and ``NiAlphaProperty`` integration.
* :func:`material_data_to_nimaterial` / :func:`material_data_to_nitexturing`
  / :func:`build_ni_source_texture` / :func:`build_classic_material_blocks`
  — round-trip builders.
* End-to-end ``MaterialData → blocks → BlockTable → import →
  MaterialData`` round-trip in a Morrowind-shaped context (NIF
  ``4.0.0.2``, ``user_version=0``, ``bs_version=0``).
"""

from __future__ import annotations

from typing import Any

import pytest

from nifblend.bridge.material_in import (
    CLASSIC_TEXTURE_SLOT_NAMES,
    MaterialData,
    niclassic_to_material_data,
)
from nifblend.bridge.material_out import (
    build_classic_material_blocks,
    build_ni_source_texture,
    material_data_to_nimaterial,
    material_data_to_nitexturing,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.bitfields import AlphaFlags
from nifblend.format.generated.blocks import (
    NiAlphaProperty,
    NiMaterialProperty,
    NiSourceTexture,
    NiTexturingProperty,
)
from nifblend.format.generated.structs import (
    Color3,
    FilePath,
    Header,
    SizedString,
    TexDesc,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)
from nifblend.io.block_table import BlockTable

# ---- helpers --------------------------------------------------------------


def _sized(s: str) -> SizedString:
    payload = s.encode("latin-1")
    return SizedString(length=len(payload), value=list(payload))


def _morrowind_table(blocks: list[Any]) -> BlockTable:
    return BlockTable(
        header=Header(),
        blocks=list(blocks),
        # Morrowind: NIF 4.0.0.2 / user 0 / bs 0.
        ctx=ReadContext(version=0x04000002, user_version=0, bs_version=0),
    )


def _make_source(path: str) -> NiSourceTexture:
    src = NiSourceTexture()
    src.use_external = 1
    fp = FilePath()
    fp.string = _sized(path)
    src.file_name = fp
    return src


def _tex_desc(source_ref: int) -> TexDesc:
    td = TexDesc()
    td.source = source_ref
    return td


# ---- decoder --------------------------------------------------------------


def test_classic_decoder_both_blocks_missing_returns_defaults() -> None:
    data = niclassic_to_material_data(None, None, name="empty")
    assert data.name == "empty"
    assert data.origin == "NiMaterialProperty"
    assert data.ambient_color == (1.0, 1.0, 1.0)
    assert data.diffuse_color == (1.0, 1.0, 1.0)
    assert data.textures == {}
    assert data.alpha_blend is False


def test_classic_decoder_material_only_populates_colors_and_alpha() -> None:
    mat = NiMaterialProperty()
    mat.ambient_color = Color3(0.1, 0.2, 0.3)
    mat.diffuse_color = Color3(0.4, 0.5, 0.6)
    mat.specular_color = Color3(0.7, 0.8, 0.9)
    mat.emissive_color = Color3(0.05, 0.06, 0.07)
    mat.glossiness = 12.5
    mat.alpha = 0.5
    mat.emissive_mult = 2.5

    data = niclassic_to_material_data(mat, None, name="m")

    assert data.ambient_color == pytest.approx((0.1, 0.2, 0.3))
    assert data.diffuse_color == pytest.approx((0.4, 0.5, 0.6))
    # diffuse + alpha promoted onto base_color so the Principled-BSDF
    # graph the wrapper builds picks it up natively.
    assert data.base_color == pytest.approx((0.4, 0.5, 0.6, 0.5))
    assert data.specular_color == pytest.approx((0.7, 0.8, 0.9))
    assert data.emissive_color == pytest.approx((0.05, 0.06, 0.07))
    assert data.glossiness == pytest.approx(12.5)
    assert data.alpha == pytest.approx(0.5)
    assert data.emissive_multiple == pytest.approx(2.5)


def test_classic_decoder_texturing_resolves_source_paths() -> None:
    src_diffuse = _make_source("textures/foo/wood_d.dds")
    src_glow = _make_source("textures/foo/wood_g.dds")
    table = _morrowind_table([src_diffuse, src_glow])

    tex = NiTexturingProperty()
    tex.apply_mode = 2
    tex.flags = 0x000F
    tex.texture_count = 7
    tex.has_base_texture = True
    tex.base_texture = _tex_desc(0)
    tex.has_glow_texture = True
    tex.glow_texture = _tex_desc(1)

    data = niclassic_to_material_data(None, tex, table, name="t")

    assert data.textures == {
        "diffuse": "textures/foo/wood_d.dds",
        "glow": "textures/foo/wood_g.dds",
    }
    assert data.texturing_apply_mode == 2
    assert data.texturing_flags == 0x000F
    assert data.texture_count == 7


def test_classic_decoder_skips_null_and_out_of_range_source_refs() -> None:
    src = _make_source("textures/x.dds")
    table = _morrowind_table([src])

    tex = NiTexturingProperty()
    tex.has_base_texture = True
    tex.base_texture = _tex_desc(0)         # valid
    tex.has_dark_texture = True
    tex.dark_texture = _tex_desc(-1)        # null ref
    tex.has_detail_texture = True
    tex.detail_texture = _tex_desc(99)      # out of range
    tex.has_glow_texture = True
    tex.glow_texture = _tex_desc(0xFFFFFFFF)  # NULL_REF

    data = niclassic_to_material_data(None, tex, table)

    assert data.textures == {"diffuse": "textures/x.dds"}


def test_classic_decoder_skips_wrong_typed_source() -> None:
    bogus = NiAlphaProperty()  # not a NiSourceTexture
    table = _morrowind_table([bogus])

    tex = NiTexturingProperty()
    tex.has_base_texture = True
    tex.base_texture = _tex_desc(0)

    data = niclassic_to_material_data(None, tex, table)
    assert data.textures == {}


def test_classic_decoder_resolves_file_name_via_string_table_index() -> None:
    # Modern NiSourceTexture path: file_name carries an index into the
    # header string table instead of an inline SizedString.
    src = NiSourceTexture()
    src.use_external = 1
    fp = FilePath()
    fp.string = None
    fp.index = 1
    src.file_name = fp

    table = _morrowind_table([src])
    table.header.strings = [_sized("ignored"), _sized("textures/abc/d.dds")]
    table.header.num_strings = 2

    tex = NiTexturingProperty()
    tex.has_base_texture = True
    tex.base_texture = _tex_desc(0)

    data = niclassic_to_material_data(None, tex, table)
    assert data.textures == {"diffuse": "textures/abc/d.dds"}


def test_classic_decoder_routes_alpha_property() -> None:
    alpha = NiAlphaProperty()
    alpha.flags = AlphaFlags(alpha_blend=1, alpha_test=1)
    alpha.threshold = 128

    data = niclassic_to_material_data(None, None, alpha=alpha, name="a")
    assert data.alpha_blend is True
    assert data.alpha_test is True
    assert data.alpha_threshold == 128


def test_classic_decoder_resolves_name_from_material_block_via_string_table() -> None:
    mat = NiMaterialProperty()
    mat.name = nif_string(index=1)
    table = _morrowind_table([])
    table.header.strings = [_sized("ignored"), _sized("Wood01")]
    table.header.num_strings = 2

    data = niclassic_to_material_data(mat, None, table)
    assert data.name == "Wood01"


# ---- builders -------------------------------------------------------------


def test_build_ni_source_texture_carries_inline_path() -> None:
    src = build_ni_source_texture("textures/foo/bar_d.dds")
    assert isinstance(src, NiSourceTexture)
    assert src.use_external == 1
    assert src.file_name is not None
    assert bytes(src.file_name.string.value) == b"textures/foo/bar_d.dds"
    # Operator owns wiring up the string-table index for modern NIFs.
    assert src.file_name.index == 0
    # FormatPrefs populated so the writer doesn't trip on a None field.
    assert src.format_prefs is not None


def test_material_data_to_nimaterial_round_trips_colors() -> None:
    data = MaterialData(
        name="m",
        origin="NiMaterialProperty",
        ambient_color=(0.1, 0.2, 0.3),
        diffuse_color=(0.4, 0.5, 0.6),
        specular_color=(0.7, 0.8, 0.9),
        emissive_color=(0.05, 0.06, 0.07),
        glossiness=15.0,
        alpha=0.25,
        emissive_multiple=1.5,
    )

    blk = material_data_to_nimaterial(data)
    assert isinstance(blk, NiMaterialProperty)
    assert blk.ambient_color.r == pytest.approx(0.1)
    assert blk.diffuse_color.g == pytest.approx(0.5)
    assert blk.specular_color.b == pytest.approx(0.9)
    assert blk.emissive_color.r == pytest.approx(0.05)
    assert blk.glossiness == pytest.approx(15.0)
    assert blk.alpha == pytest.approx(0.25)
    assert blk.emissive_mult == pytest.approx(1.5)
    assert blk.controller == -1


def test_material_data_to_nitexturing_wires_source_refs_per_slot() -> None:
    data = MaterialData(
        name="t",
        textures={"diffuse": "a.dds", "glow": "b.dds"},
        texturing_apply_mode=2,
        texturing_flags=0xAB,
        texture_count=7,
    )
    blk = material_data_to_nitexturing(
        data,
        source_refs={"diffuse": 5, "glow": 6},
    )
    assert blk.has_base_texture is True
    assert blk.base_texture.source == 5
    assert blk.has_glow_texture is True
    assert blk.glow_texture.source == 6
    # Slots without a source ref end up as null TexDescs.
    assert blk.has_dark_texture is False
    assert blk.dark_texture is None
    assert blk.apply_mode == 2
    assert blk.flags == 0xAB
    assert blk.texture_count == 7


def test_material_data_to_nitexturing_omits_unmapped_slots() -> None:
    data = MaterialData(name="t", textures={})
    blk = material_data_to_nitexturing(data)
    for has_attr in (
        "has_base_texture",
        "has_dark_texture",
        "has_detail_texture",
        "has_gloss_texture",
        "has_glow_texture",
        "has_bump_map_texture",
        "has_normal_texture",
        "has_parallax_texture",
        "has_decal_0_texture",
        "has_decal_1_texture",
        "has_decal_2_texture",
        "has_decal_3_texture",
    ):
        assert getattr(blk, has_attr) is False


def test_build_classic_material_blocks_emits_sources_in_slot_order() -> None:
    data = MaterialData(
        name="full",
        textures={
            "diffuse": "d.dds",
            "glow": "g.dds",
            "normal": "n.dds",
        },
    )
    mat_blk, tex_blk, sources = build_classic_material_blocks(data)

    assert isinstance(mat_blk, NiMaterialProperty)
    assert isinstance(tex_blk, NiTexturingProperty)
    # Sources emitted in CLASSIC_TEXTURE_SLOT_NAMES order: diffuse, glow, normal.
    paths = [bytes(s.file_name.string.value).decode("latin-1") for s in sources]
    assert paths == ["d.dds", "g.dds", "n.dds"]
    # Texturing block points at sources by their positional index in the list.
    assert tex_blk.base_texture.source == 0
    assert tex_blk.glow_texture.source == 1
    assert tex_blk.normal_texture.source == 2


def test_build_classic_material_blocks_omits_texturing_when_no_textures() -> None:
    data = MaterialData(name="bare", textures={})
    mat_blk, tex_blk, sources = build_classic_material_blocks(data)
    assert mat_blk is not None
    assert tex_blk is None
    assert sources == []


# ---- end-to-end round-trip in a Morrowind context ------------------------


def test_morrowind_round_trip_materialdata_through_blocktable() -> None:
    data = MaterialData(
        name="Wood01",
        origin="NiMaterialProperty",
        ambient_color=(0.2, 0.3, 0.4),
        diffuse_color=(0.5, 0.6, 0.7),
        specular_color=(0.8, 0.9, 1.0),
        emissive_color=(0.01, 0.02, 0.03),
        glossiness=20.0,
        alpha=0.75,
        emissive_multiple=1.25,
        textures={
            "diffuse": "textures/wood/oak_d.dds",
            "normal": "textures/wood/oak_n.dds",
        },
        texturing_apply_mode=2,
        texturing_flags=0x0001,
        texture_count=7,
    )

    mat_blk, tex_blk, sources = build_classic_material_blocks(data)
    assert tex_blk is not None

    # Insert sources first, then the property blocks. The texturing block
    # was built with positional source refs (0, 1) which match the layout.
    blocks: list[Any] = [*sources, mat_blk, tex_blk]
    table = _morrowind_table(blocks)

    decoded = niclassic_to_material_data(mat_blk, tex_blk, table, name="Wood01")
    assert decoded.ambient_color == pytest.approx(data.ambient_color)
    assert decoded.diffuse_color == pytest.approx(data.diffuse_color)
    assert decoded.specular_color == pytest.approx(data.specular_color)
    assert decoded.emissive_color == pytest.approx(data.emissive_color)
    assert decoded.glossiness == pytest.approx(data.glossiness)
    assert decoded.alpha == pytest.approx(data.alpha)
    assert decoded.emissive_multiple == pytest.approx(data.emissive_multiple)
    assert decoded.textures == {
        "diffuse": "textures/wood/oak_d.dds",
        "normal": "textures/wood/oak_n.dds",
    }
    assert decoded.texturing_apply_mode == 2
    assert decoded.texturing_flags == 0x0001
    assert decoded.texture_count == 7


def test_classic_slot_names_includes_classic_only_slots() -> None:
    # Sanity: the classic slot ordering exposes the slots Morrowind /
    # Oblivion can carry that the SSE slot list doesn't (dark / detail
    # / gloss / bump / decal0..3).
    classic_only = set(CLASSIC_TEXTURE_SLOT_NAMES) - {
        "diffuse",
        "normal",
        "glow",
        "height",
    }
    assert classic_only == {
        "dark",
        "detail",
        "gloss",
        "bump",
        "decal0",
        "decal1",
        "decal2",
        "decal3",
    }
