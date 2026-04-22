"""Phase 6 step 23 — Fallout 3 / NV BSShaderPPLightingProperty tests.

Covers the three layers added for the FO3/NV path:

* :func:`bsshaderpplighting_to_material_data` -- decoder over a hand-built
  :class:`BSShaderPPLightingProperty` block (no NIF parsing): default
  fallbacks, string-table name resolution, FO3 6-slot texture set, the
  refraction / parallax / environment-map / clamp-mode / pp_flags
  scalars, the inline ``emissive_color`` Color4 (with the FO3 quirk that
  the alpha channel doubles as the emissive multiplier), and
  ``NiAlphaProperty`` integration.
* :func:`material_data_to_bsshaderpplighting` + :func:`build_pp_texture_set`
  -- builders that write back into the same shape, plus end-to-end
  block → BlockTable → import → block round-trip.
* :func:`export_material` dispatch on ``origin == "BSShaderPPLightingProperty"``
  via the same fake-bpy material graph the SSE export tests use.

Also pins down :mod:`nifblend.bridge.material_props`'s extension to the
new FO3 fields (``pp_flags``, ``environment_map_scale``,
``texture_clamp_mode``, ``refraction_strength``, ``refraction_fire_period``,
``parallax_max_passes``, ``parallax_scale``).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge.material_in import (
    MaterialData,
    bsshaderpplighting_to_material_data,
    import_material,
    material_data_to_blender,
)
from nifblend.bridge.material_out import (
    build_pp_texture_set,
    export_material,
    material_data_from_blender,
    material_data_to_bsshaderpplighting,
)
from nifblend.bridge.material_props import PROP_ATTR
from nifblend.format.base import ReadContext
from nifblend.format.generated.bitfields import AlphaFlags
from nifblend.format.generated.blocks import (
    BSShaderPPLightingProperty,
    BSShaderTextureSet,
    NiAlphaProperty,
)
from nifblend.format.generated.structs import (
    Color4,
    Header,
    SizedString,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)
from nifblend.io.block_table import BlockTable

# ---- helpers --------------------------------------------------------------


def _sized(s: str) -> SizedString:
    payload = s.encode("latin-1")
    return SizedString(length=len(payload), value=list(payload))


def _texture_set(paths: list[str]) -> BSShaderTextureSet:
    ts = BSShaderTextureSet()
    ts.num_textures = len(paths)
    ts.textures = [_sized(p) for p in paths]
    return ts


def _table_with_blocks(
    blocks: list[Any], names: list[str] | None = None
) -> BlockTable:
    h = Header()
    if names is not None:
        h.strings = [_sized(n) for n in names]
        h.num_strings = len(h.strings)
    return BlockTable(
        header=h,
        blocks=list(blocks),
        # FO3/NV (20.2.0.7 user 11/34, bs_version=34) -- the version
        # context BSShaderPPLightingProperty cares about.
        ctx=ReadContext(version=0x14020007, user_version=11, bs_version=34),
    )


# ---- decoder --------------------------------------------------------------


def test_pplighting_minimal_decode_defaults() -> None:
    blk = BSShaderPPLightingProperty()
    blk.shader_flags = 0xCAFEBABE
    blk.shader_flags_2 = 0xDEADBEEF
    blk.flags = 0x1234
    blk.shader_type = 5
    blk.environment_map_scale = 0.75
    blk.texture_clamp_mode = 3
    blk.refraction_strength = 0.25
    blk.refraction_fire_period = 17
    blk.parallax_max_passes = 4.0
    blk.parallax_scale = 1.5

    data = bsshaderpplighting_to_material_data(blk, name="m")

    assert data.name == "m"
    assert data.origin == "BSShaderPPLightingProperty"
    assert data.shader_type == 5
    assert data.shader_flags_1 == 0xCAFEBABE
    assert data.shader_flags_2 == 0xDEADBEEF
    assert data.pp_flags == 0x1234
    assert data.environment_map_scale == pytest.approx(0.75)
    assert data.texture_clamp_mode == 3
    assert data.refraction_strength == pytest.approx(0.25)
    assert data.refraction_fire_period == 17
    assert data.parallax_max_passes == pytest.approx(4.0)
    assert data.parallax_scale == pytest.approx(1.5)
    assert data.textures == {}


def test_pplighting_resolves_name_via_string_table() -> None:
    blk = BSShaderPPLightingProperty()
    blk.name = nif_string(index=0)
    table = _table_with_blocks([blk], names=["FO3Shader"])
    data = bsshaderpplighting_to_material_data(blk, table)
    assert data.name == "FO3Shader"


def test_pplighting_falls_back_to_class_name_on_null_ref() -> None:
    blk = BSShaderPPLightingProperty()
    blk.name = nif_string(index=0xFFFFFFFF)
    table = _table_with_blocks([blk], names=["irrelevant"])
    data = bsshaderpplighting_to_material_data(blk, table)
    assert data.name == "BSShaderPPLightingProperty"


def test_pplighting_resolves_six_slot_texture_set() -> None:
    paths = [
        "textures/armor/d.dds",   # diffuse
        "textures/armor/n.dds",   # normal
        "",                        # glow
        "textures/armor/p.dds",   # height/parallax
        "textures/cube.dds",      # environment
        "",                        # env_mask
    ]
    ts = _texture_set(paths)
    blk = BSShaderPPLightingProperty()
    blk.texture_set = 1
    table = _table_with_blocks([blk, ts])

    data = bsshaderpplighting_to_material_data(blk, table, name="m")

    assert data.textures == {
        "diffuse": "textures/armor/d.dds",
        "normal": "textures/armor/n.dds",
        "height": "textures/armor/p.dds",
        "environment": "textures/cube.dds",
    }


def test_pplighting_ignores_texture_set_pointing_at_wrong_block_type() -> None:
    blk = BSShaderPPLightingProperty()
    blk.texture_set = 0
    table = _table_with_blocks([BSShaderPPLightingProperty()])
    data = bsshaderpplighting_to_material_data(blk, table, name="m")
    assert data.textures == {}


def test_pplighting_negative_texture_set_treated_as_null() -> None:
    blk = BSShaderPPLightingProperty()
    blk.texture_set = -1
    data = bsshaderpplighting_to_material_data(blk, name="m")
    assert data.textures == {}


def test_pplighting_inline_emissive_color_doubles_as_multiplier() -> None:
    blk = BSShaderPPLightingProperty()
    blk.emissive_color = Color4(r=0.4, g=0.5, b=0.6, a=2.5)
    data = bsshaderpplighting_to_material_data(blk, name="m")
    assert data.emissive_color == pytest.approx((0.4, 0.5, 0.6))
    # FO3 stuffs the multiplier into the alpha channel of the inline
    # color (no separate emissive_multiple field on the block).
    assert data.emissive_multiple == pytest.approx(2.5)


def test_pplighting_alpha_property_routes_through() -> None:
    blk = BSShaderPPLightingProperty()
    alpha = NiAlphaProperty()
    alpha.flags = AlphaFlags(alpha_test=1)
    alpha.threshold = 200
    data = bsshaderpplighting_to_material_data(blk, name="m", alpha=alpha)
    assert data.alpha_test is True
    assert data.alpha_blend is False
    assert data.alpha_threshold == 200


# ---- builder --------------------------------------------------------------


def test_to_pplighting_populates_fo3_fields() -> None:
    data = MaterialData(
        name="m",
        origin="BSShaderPPLightingProperty",
        shader_type=4,
        shader_flags_1=0xFEEDFACE,
        shader_flags_2=0xCAFEBABE,
        pp_flags=0x4321,
        environment_map_scale=0.625,
        texture_clamp_mode=2,
        refraction_strength=0.125,
        refraction_fire_period=9,
        parallax_max_passes=8.0,
        parallax_scale=2.5,
        emissive_color=(0.1, 0.2, 0.3),
        emissive_multiple=1.75,
    )
    blk = material_data_to_bsshaderpplighting(data, name_index=7, texture_set_ref=42)

    assert isinstance(blk, BSShaderPPLightingProperty)
    assert int(blk.name.index) == 7
    assert blk.controller == -1
    assert blk.flags == 0x4321
    assert blk.shader_type == 4
    assert blk.shader_flags == 0xFEEDFACE
    assert blk.shader_flags_2 == 0xCAFEBABE
    assert blk.environment_map_scale == pytest.approx(0.625)
    assert blk.texture_clamp_mode == 2
    assert blk.texture_set == 42
    assert blk.refraction_strength == pytest.approx(0.125)
    assert blk.refraction_fire_period == 9
    assert blk.parallax_max_passes == pytest.approx(8.0)
    assert blk.parallax_scale == pytest.approx(2.5)
    # Emissive Color4: rgb from emissive_color, alpha from emissive_multiple.
    assert blk.emissive_color is not None
    assert (blk.emissive_color.r, blk.emissive_color.g, blk.emissive_color.b) == pytest.approx(
        (0.1, 0.2, 0.3)
    )
    assert blk.emissive_color.a == pytest.approx(1.75)


def test_to_pplighting_defaults_texture_set_ref_to_minus_one() -> None:
    blk = material_data_to_bsshaderpplighting(MaterialData(name="m"))
    assert blk.texture_set == -1


# ---- build_pp_texture_set -------------------------------------------------


def test_build_pp_texture_set_returns_none_for_empty() -> None:
    assert build_pp_texture_set(MaterialData(name="m")) is None


def test_build_pp_texture_set_emits_six_slots_by_default() -> None:
    data = MaterialData(
        name="m",
        textures={
            "diffuse": "d.dds",
            "normal": "n.dds",
            "height": "p.dds",
            # backlight is past the FO3 6-slot window -> dropped.
            "backlight": "b.dds",
        },
    )
    ts = build_pp_texture_set(data)
    assert isinstance(ts, BSShaderTextureSet)
    assert ts.num_textures == 6
    decoded = [bytes(t.value).decode("latin-1") for t in ts.textures]
    assert decoded == ["d.dds", "n.dds", "", "p.dds", "", ""]


def test_build_pp_texture_set_custom_slot_count() -> None:
    data = MaterialData(name="m", textures={"diffuse": "d.dds"})
    ts = build_pp_texture_set(data, num_slots=3)
    assert ts is not None
    assert ts.num_textures == 3
    assert bytes(ts.textures[0].value).decode("latin-1") == "d.dds"


# ---- end-to-end round-trip ------------------------------------------------


def test_pplighting_round_trip_through_block_table() -> None:
    src = MaterialData(
        name="rt",
        origin="BSShaderPPLightingProperty",
        shader_type=2,
        shader_flags_1=0x11223344,
        shader_flags_2=0x55667788,
        pp_flags=0x9999,
        environment_map_scale=0.5,
        texture_clamp_mode=1,
        refraction_strength=0.6,
        refraction_fire_period=12,
        parallax_max_passes=3.0,
        parallax_scale=1.25,
        emissive_color=(0.7, 0.8, 0.9),
        emissive_multiple=1.5,
        textures={
            "diffuse": "textures/rt/d.dds",
            "normal": "textures/rt/n.dds",
            "height": "textures/rt/p.dds",
            "environment": "textures/rt/cube.dds",
        },
    )
    ts = build_pp_texture_set(src)
    assert ts is not None
    shader = material_data_to_bsshaderpplighting(src, name_index=0, texture_set_ref=1)

    h = Header()
    h.strings = [_sized("rt")]
    h.num_strings = 1
    table = BlockTable(
        header=h,
        blocks=[shader, ts],
        ctx=ReadContext(version=0x14020007, user_version=11, bs_version=34),
    )

    decoded = bsshaderpplighting_to_material_data(shader, table)
    assert decoded.name == "rt"
    assert decoded.origin == "BSShaderPPLightingProperty"
    assert decoded.shader_type == 2
    assert decoded.shader_flags_1 == 0x11223344
    assert decoded.shader_flags_2 == 0x55667788
    assert decoded.pp_flags == 0x9999
    assert decoded.environment_map_scale == pytest.approx(0.5)
    assert decoded.texture_clamp_mode == 1
    assert decoded.refraction_strength == pytest.approx(0.6)
    assert decoded.refraction_fire_period == 12
    assert decoded.parallax_max_passes == pytest.approx(3.0)
    assert decoded.parallax_scale == pytest.approx(1.25)
    assert decoded.emissive_color == pytest.approx((0.7, 0.8, 0.9))
    assert decoded.emissive_multiple == pytest.approx(1.5)
    assert decoded.textures == {
        "diffuse": "textures/rt/d.dds",
        "normal": "textures/rt/n.dds",
        "height": "textures/rt/p.dds",
        "environment": "textures/rt/cube.dds",
    }


# ---- import_material dispatch + bpy materialisation ----------------------


class _FakeInput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.default_value: Any = None
        self.linked_from: Any = None


class _FakeOutput:
    def __init__(self, name: str, owner: _FakeNode) -> None:
        self.name = name
        self.owner = owner


class _FakeInputs:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: _FakeInput(n) for n in names}

    def __contains__(self, k: str) -> bool:
        return k in self._items

    def __getitem__(self, k: str) -> _FakeInput:
        return self._items[k]

    def get(self, k: str, default: Any = None) -> Any:
        return self._items.get(k, default)


class _FakeOutputs:
    def __init__(self, names: list[str], owner: _FakeNode) -> None:
        self._items = {n: _FakeOutput(n, owner) for n in names}

    def __getitem__(self, k: str) -> _FakeOutput:
        return self._items[k]


class _FakeNode:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.bl_idname = kind
        self.location: tuple[float, float] = (0.0, 0.0)
        self.image: Any = None
        if kind == "ShaderNodeBsdfPrincipled":
            self.type = "BSDF_PRINCIPLED"
            self.inputs = _FakeInputs(
                [
                    "Base Color",
                    "Alpha",
                    "Roughness",
                    "Metallic",
                    "Emission Color",
                    "Emission Strength",
                    "Normal",
                ]
            )
            self.outputs = _FakeOutputs(["BSDF"], self)
        elif kind == "ShaderNodeOutputMaterial":
            self.inputs = _FakeInputs(["Surface"])
            self.outputs = _FakeOutputs([], self)
        elif kind == "ShaderNodeTexImage":
            self.inputs = _FakeInputs([])
            self.outputs = _FakeOutputs(["Color", "Alpha"], self)
        elif kind == "ShaderNodeNormalMap":
            self.inputs = _FakeInputs(["Color"])
            self.outputs = _FakeOutputs(["Normal"], self)
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown fake node kind: {kind!r}")


class _FakeNodes:
    def __init__(self) -> None:
        self._items: list[_FakeNode] = []

    def new(self, kind: str) -> _FakeNode:
        n = _FakeNode(kind)
        self._items.append(n)
        return n

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self):
        return iter(self._items)


class _FakeLinks:
    def __init__(self) -> None:
        self._items: list[tuple[_FakeOutput, _FakeInput]] = []

    def new(self, src: _FakeOutput, dst: _FakeInput) -> None:
        dst.linked_from = src
        self._items.append((src, dst))


class _FakeImage:
    def __init__(self, name: str, filepath: str | None = None) -> None:
        self.name = name
        self.filepath = filepath
        self.colorspace_settings = SimpleNamespace(name="sRGB")


class _FakeImages:
    def __init__(self) -> None:
        self._items: dict[str, _FakeImage] = {}

    def get(self, name: str) -> _FakeImage | None:
        return self._items.get(name)

    def new(self, *, name: str, width: int, height: int) -> _FakeImage:
        img = _FakeImage(name)
        self._items[name] = img
        return img

    def load(self, filepath: str, check_existing: bool = True) -> _FakeImage:
        if check_existing and filepath in self._items:
            return self._items[filepath]
        img = _FakeImage(filepath, filepath=filepath)
        self._items[filepath] = img
        return img


class _FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.use_nodes = False
        self.node_tree = SimpleNamespace(nodes=_FakeNodes(), links=_FakeLinks())
        self.blend_method = "OPAQUE"
        self.alpha_threshold = 0.0


class _FakeMaterials:
    def __init__(self) -> None:
        self._items: list[_FakeMaterial] = []

    def new(self, name: str) -> _FakeMaterial:
        m = _FakeMaterial(name)
        self._items.append(m)
        return m


def _make_fake_bpy() -> Any:
    return SimpleNamespace(
        data=SimpleNamespace(materials=_FakeMaterials(), images=_FakeImages())
    )


def test_import_material_dispatches_to_pplighting_decoder() -> None:
    blk = BSShaderPPLightingProperty()
    blk.environment_map_scale = 0.5
    blk.refraction_strength = 0.25

    bpy = _make_fake_bpy()
    mat = import_material(blk, name="m", bpy=bpy)
    # The PropertyGroup stores the FO3 fields; verify origin survived.
    assert getattr(mat, PROP_ATTR).origin == "BSShaderPPLightingProperty"
    assert getattr(mat, PROP_ATTR).environment_map_scale == pytest.approx(0.5)
    assert getattr(mat, PROP_ATTR).refraction_strength == pytest.approx(0.25)


def test_pplighting_import_export_round_trip_preserves_fo3_state() -> None:
    """``MaterialData -> blender material -> MaterialData`` keeps every
    FO3-only scalar via the typed PropertyGroup."""
    src = MaterialData(
        name="m",
        origin="BSShaderPPLightingProperty",
        shader_type=3,
        shader_flags_1=0xAABBCCDD,
        shader_flags_2=0x11223344,
        pp_flags=0xFEED,
        environment_map_scale=0.875,
        texture_clamp_mode=2,
        refraction_strength=0.5,
        refraction_fire_period=21,
        parallax_max_passes=6.0,
        parallax_scale=1.75,
        emissive_color=(0.4, 0.5, 0.6),
        emissive_multiple=2.25,
        textures={
            "diffuse": "textures/d.dds",
            "normal": "textures/n.dds",
            "height": "textures/p.dds",
        },
    )
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(src, bpy=bpy)

    out = material_data_from_blender(mat)

    assert out.origin == "BSShaderPPLightingProperty"
    assert out.shader_type == src.shader_type
    assert out.shader_flags_1 == src.shader_flags_1
    assert out.shader_flags_2 == src.shader_flags_2
    assert out.pp_flags == src.pp_flags
    assert out.environment_map_scale == pytest.approx(src.environment_map_scale)
    assert out.texture_clamp_mode == src.texture_clamp_mode
    assert out.refraction_strength == pytest.approx(src.refraction_strength)
    assert out.refraction_fire_period == src.refraction_fire_period
    assert out.parallax_max_passes == pytest.approx(src.parallax_max_passes)
    assert out.parallax_scale == pytest.approx(src.parallax_scale)
    # Texture slots beyond what the Principled-BSDF graph can wire
    # natively (height) survive via the PropertyGroup CollectionProperty.
    for slot, path in src.textures.items():
        assert out.textures.get(slot) == path, f"lost FO3 texture slot {slot!r}"


def test_export_material_dispatches_to_pplighting_when_origin_set() -> None:
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(
        MaterialData(name="m", origin="BSShaderPPLightingProperty"), bpy=bpy
    )
    blk = export_material(mat, name_index=1)
    assert isinstance(blk, BSShaderPPLightingProperty)
