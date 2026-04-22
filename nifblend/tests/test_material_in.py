"""Unit tests for :mod:`nifblend.bridge.material_in`.

The decoder side is exercised against synthesised codegen-emitted block
dataclasses (no NIF parsing). The Blender-side wrapper is exercised
through a small fake ``bpy`` module that records node creation + linking
the way ``test_mesh_in.py`` does for meshes.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge.material_in import (
    TEXTURE_SLOT_NAMES,
    MaterialData,
    bseffect_to_material_data,
    bslighting_to_material_data,
    material_data_to_blender,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.bitfields import AlphaFlags
from nifblend.format.generated.blocks import (
    BSEffectShaderProperty,
    BSLightingShaderProperty,
    BSShaderTextureSet,
    NiAlphaProperty,
)
from nifblend.format.generated.structs import (
    Color3,
    Color4,
    Header,
    SizedString,
    TexCoord,
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


def _name_index(idx: int) -> nif_string:
    return nif_string(index=idx)


def _table_with_blocks(blocks: list[Any], names: list[str] | None = None) -> BlockTable:
    h = Header()
    if names is not None:
        h.strings = [_sized(n) for n in names]
        h.num_strings = len(h.strings)
    return BlockTable(
        header=h,
        blocks=list(blocks),
        ctx=ReadContext(version=0x14020007, user_version=12, bs_version=100),
    )


# ---- BSLightingShaderProperty decoder ------------------------------------


def test_bslighting_minimal_decode_uses_defaults_when_table_missing() -> None:
    blk = BSLightingShaderProperty()
    blk.alpha = 0.5
    blk.glossiness = 30.0
    blk.smoothness = 0.75
    blk.specular_color = Color3(0.9, 0.8, 0.7)
    blk.specular_strength = 1.5
    blk.emissive_color = Color3(0.1, 0.2, 0.3)
    blk.emissive_multiple = 2.0

    data = bslighting_to_material_data(blk, name="m")

    assert data.name == "m"
    assert data.origin == "BSLightingShaderProperty"
    assert data.alpha == pytest.approx(0.5)
    assert data.glossiness == pytest.approx(30.0)
    assert data.smoothness == pytest.approx(0.75)
    assert data.specular_color == pytest.approx((0.9, 0.8, 0.7))
    assert data.specular_strength == pytest.approx(1.5)
    assert data.emissive_color == pytest.approx((0.1, 0.2, 0.3))
    assert data.emissive_multiple == pytest.approx(2.0)
    assert data.textures == {}


def test_bslighting_resolves_name_via_string_table() -> None:
    blk = BSLightingShaderProperty()
    blk.name = _name_index(0)
    table = _table_with_blocks([blk], names=["MyShader"])
    data = bslighting_to_material_data(blk, table)
    assert data.name == "MyShader"


def test_bslighting_falls_back_to_class_name_on_null_ref() -> None:
    blk = BSLightingShaderProperty()
    blk.name = _name_index(0xFFFFFFFF)
    table = _table_with_blocks([blk], names=["irrelevant"])
    data = bslighting_to_material_data(blk, table)
    assert data.name == "BSLightingShaderProperty"


def test_bslighting_resolves_texture_set_into_named_slots() -> None:
    paths = [
        "textures/foo/foo_d.dds",  # diffuse
        "textures/foo/foo_n.dds",  # normal
        "",                         # glow (empty -> not stored)
        "",                         # height
        "textures/foo/foo_e.dds",  # environment
        "",                         # env_mask
        "",                         # subsurface
        "",                         # backlight
    ]
    ts = _texture_set(paths)
    blk = BSLightingShaderProperty()
    blk.texture_set = 1  # references blocks[1] in the table below
    blk.uv_offset = TexCoord(0.25, 0.5)
    blk.uv_scale = TexCoord(2.0, 3.0)
    table = _table_with_blocks([blk, ts])

    data = bslighting_to_material_data(blk, table, name="m")

    assert data.textures == {
        "diffuse": "textures/foo/foo_d.dds",
        "normal": "textures/foo/foo_n.dds",
        "environment": "textures/foo/foo_e.dds",
    }
    assert data.uv_offset == pytest.approx((0.25, 0.5))
    assert data.uv_scale == pytest.approx((2.0, 3.0))


def test_bslighting_ignores_texture_set_ref_pointing_at_wrong_block_type() -> None:
    blk = BSLightingShaderProperty()
    blk.texture_set = 0
    # blocks[0] is *not* a BSShaderTextureSet -> resolution returns None.
    table = _table_with_blocks([BSLightingShaderProperty()])
    data = bslighting_to_material_data(blk, table, name="m")
    assert data.textures == {}


def test_bslighting_negative_texture_set_ref_treated_as_null() -> None:
    blk = BSLightingShaderProperty()
    blk.texture_set = -1
    data = bslighting_to_material_data(blk, name="m")
    assert data.textures == {}


def test_bslighting_preserves_shader_flags_and_type() -> None:
    blk = BSLightingShaderProperty()
    blk.shader_type = 7
    blk.shader_flags_1 = 0xDEADBEEF
    blk.shader_flags_2 = 0x12345678
    data = bslighting_to_material_data(blk, name="m")
    assert data.shader_type == 7
    assert data.shader_flags_1 == 0xDEADBEEF
    assert data.shader_flags_2 == 0x12345678


# ---- BSEffectShaderProperty decoder --------------------------------------


def test_bseffect_decoder_pulls_inline_textures_and_base_color() -> None:
    blk = BSEffectShaderProperty()
    blk.base_color = Color4(0.2, 0.4, 0.6, 0.8)
    blk.base_color_scale = 1.5
    blk.emittance_color = Color3(0.1, 0.0, 0.0)
    blk.source_texture = _sized("textures/effects/glow_d.dds")
    blk.normal_texture = _sized("textures/effects/glow_n.dds")
    blk.env_map_texture = _sized("textures/cubemap.dds")
    blk.uv_offset = TexCoord(0.0, 0.0)
    blk.uv_scale = TexCoord(1.0, 1.0)

    data = bseffect_to_material_data(blk, name="effect")

    assert data.origin == "BSEffectShaderProperty"
    assert data.base_color == pytest.approx((0.2, 0.4, 0.6, 0.8))
    assert data.emissive_multiple == pytest.approx(1.5)
    assert data.emissive_color == pytest.approx((0.1, 0.0, 0.0))
    assert data.textures == {
        "diffuse": "textures/effects/glow_d.dds",
        "normal": "textures/effects/glow_n.dds",
        "environment": "textures/cubemap.dds",
    }


# ---- NiAlphaProperty integration -----------------------------------------


def test_alpha_blend_bit_sets_alpha_blend_flag() -> None:
    blk = BSLightingShaderProperty()
    alpha = NiAlphaProperty()
    alpha.flags = AlphaFlags(alpha_blend=1)
    alpha.threshold = 128
    data = bslighting_to_material_data(blk, name="m", alpha=alpha)
    assert data.alpha_blend is True
    assert data.alpha_test is False
    assert data.alpha_threshold == 128


def test_alpha_test_bit_sets_alpha_test_flag() -> None:
    blk = BSLightingShaderProperty()
    alpha = NiAlphaProperty()
    alpha.flags = AlphaFlags(alpha_test=1)
    alpha.threshold = 200
    data = bslighting_to_material_data(blk, name="m", alpha=alpha)
    assert data.alpha_blend is False
    assert data.alpha_test is True
    assert data.alpha_threshold == 200


# ---- Blender wrapper -----------------------------------------------------


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
        self.location: tuple[float, float] = (0.0, 0.0)
        self.image: Any = None
        if kind == "ShaderNodeBsdfPrincipled":
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

    def of_kind(self, kind: str) -> list[_FakeNode]:
        return [n for n in self._items if n.kind == kind]


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


def test_blender_wrapper_builds_principled_with_diffuse_and_normal() -> None:
    data = MaterialData(
        name="m",
        base_color=(0.5, 0.6, 0.7, 0.8),
        alpha=0.75,
        smoothness=0.4,
        specular_strength=0.25,
        emissive_color=(0.1, 0.2, 0.3),
        emissive_multiple=1.5,
        textures={
            "diffuse": "textures/foo_d.dds",
            "normal": "textures/foo_n.dds",
        },
    )
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(data, bpy=bpy)

    assert mat.use_nodes is True
    bsdf = mat.node_tree.nodes.of_kind("ShaderNodeBsdfPrincipled")[0]
    assert bsdf.inputs["Base Color"].default_value == (0.5, 0.6, 0.7, 0.8)
    assert bsdf.inputs["Alpha"].default_value == pytest.approx(0.75)
    assert bsdf.inputs["Roughness"].default_value == pytest.approx(1.0 - 0.4)
    assert bsdf.inputs["Metallic"].default_value == pytest.approx(0.25)
    em = bsdf.inputs["Emission Color"].default_value
    assert em == (0.1, 0.2, 0.3, 1.0)
    assert bsdf.inputs["Emission Strength"].default_value == pytest.approx(1.5)

    # Diffuse: an Image Texture wired into Base Color.
    assert bsdf.inputs["Base Color"].linked_from is not None
    diffuse_node = bsdf.inputs["Base Color"].linked_from.owner
    assert diffuse_node.kind == "ShaderNodeTexImage"
    assert diffuse_node.image.name == "textures/foo_d.dds"

    # Normal: an Image -> NormalMap -> Principled.Normal chain.
    assert bsdf.inputs["Normal"].linked_from is not None
    nm = bsdf.inputs["Normal"].linked_from.owner
    assert nm.kind == "ShaderNodeNormalMap"
    nm_image = nm.inputs["Color"].linked_from.owner
    assert nm_image.kind == "ShaderNodeTexImage"
    assert nm_image.image.name == "textures/foo_n.dds"
    # The normal map should be tagged Non-Color.
    assert nm_image.image.colorspace_settings.name == "Non-Color"


def test_blender_wrapper_uses_resolve_texture_callback() -> None:
    data = MaterialData(
        name="m",
        textures={"diffuse": "textures/foo_d.dds"},
    )
    bpy = _make_fake_bpy()
    seen: list[str] = []

    def resolver(p: str) -> str | None:
        seen.append(p)
        return f"C:/Data/{p}"

    material_data_to_blender(data, bpy=bpy, resolve_texture=resolver)

    assert seen == ["textures/foo_d.dds"]
    img = bpy.data.images.get("C:/Data/textures/foo_d.dds")
    assert img is not None
    assert img.filepath == "C:/Data/textures/foo_d.dds"


def test_blender_wrapper_alpha_blend_routes_to_blend_mode() -> None:
    data = MaterialData(name="m", alpha_blend=True)
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(data, bpy=bpy)
    assert mat.blend_method == "BLEND"


def test_blender_wrapper_alpha_test_routes_to_clip_mode() -> None:
    data = MaterialData(name="m", alpha_test=True, alpha_threshold=128)
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(data, bpy=bpy)
    assert mat.blend_method == "CLIP"
    assert mat.alpha_threshold == pytest.approx(128 / 255.0)


def test_texture_slot_names_aligned_with_bs_indices() -> None:
    # Sanity: regress against accidental reordering -- the indices below
    # are the on-disk meanings the bridge relies on.
    assert TEXTURE_SLOT_NAMES[0] == "diffuse"
    assert TEXTURE_SLOT_NAMES[1] == "normal"
    assert TEXTURE_SLOT_NAMES[2] == "glow"
    assert TEXTURE_SLOT_NAMES[7] == "backlight"
