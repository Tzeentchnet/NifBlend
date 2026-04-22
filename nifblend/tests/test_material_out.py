"""Unit tests for :mod:`nifblend.bridge.material_out`.

Covers:

* The Blender-side reader (``material_data_from_blender``) against the
  same fake-bpy graph the import side builds.
* Block construction (``material_data_to_bslighting`` /
  ``material_data_to_bseffect`` / ``build_texture_set`` /
  ``build_alpha_property``) -- field-for-field.
* A round-trip: ``MaterialData → bslighting block → BSShaderTextureSet
  → BlockTable → bridge import → MaterialData``, asserting every Phase 3
  field survives.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge.material_in import (
    MaterialData,
    bseffect_to_material_data,
    bslighting_to_material_data,
)
from nifblend.bridge.material_out import (
    build_alpha_property,
    build_texture_set,
    export_material,
    material_data_from_blender,
    material_data_to_bseffect,
    material_data_to_bslighting,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import (
    BSEffectShaderProperty,
    BSLightingShaderProperty,
    BSShaderTextureSet,
    NiAlphaProperty,
)
from nifblend.format.generated.structs import Header
from nifblend.io.block_table import BlockTable

# ---- fake bpy material graph ---------------------------------------------


class _FakeInput:
    def __init__(self, name: str, default: Any = None) -> None:
        self.name = name
        self.default_value = default
        self.linked_from: Any = None


class _FakeOutput:
    def __init__(self, name: str, owner: _FakeNode) -> None:
        self.name = name
        self.owner = owner


class _FakeInputs:
    def __init__(self, defaults: dict[str, Any]) -> None:
        self._items = {n: _FakeInput(n, v) for n, v in defaults.items()}

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
    def __init__(self, kind: str, **kwargs: Any) -> None:
        self.kind = kind
        self.bl_idname = kind
        self.image = kwargs.pop("image", None)
        if kind == "ShaderNodeBsdfPrincipled":
            self.type = "BSDF_PRINCIPLED"
            self.inputs = _FakeInputs(
                {
                    "Base Color": (0.4, 0.5, 0.6, 1.0),
                    "Alpha": 0.9,
                    "Roughness": 0.2,
                    "Metallic": 0.3,
                    "Emission Color": (0.7, 0.8, 0.9, 1.0),
                    "Emission Strength": 1.25,
                    "Normal": None,
                }
            )
            self.outputs = _FakeOutputs(["BSDF"], self)
        elif kind == "ShaderNodeTexImage":
            self.inputs = _FakeInputs({})
            self.outputs = _FakeOutputs(["Color", "Alpha"], self)
        elif kind == "ShaderNodeNormalMap":
            self.inputs = _FakeInputs({"Color": None})
            self.outputs = _FakeOutputs(["Normal"], self)
        else:  # pragma: no cover
            raise ValueError(f"unknown fake node kind: {kind!r}")


def _link(src: _FakeOutput, dst: _FakeInput) -> None:
    dst.linked_from = src


def _make_image(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def _make_fake_material(
    *,
    name: str = "m",
    use_nodes: bool = True,
    diffuse_image: str | None = None,
    normal_image: str | None = None,
    glow_image: str | None = None,
    blend_method: str = "OPAQUE",
    alpha_threshold: float = 0.0,
) -> Any:
    nodes: list[_FakeNode] = []

    bsdf = _FakeNode("ShaderNodeBsdfPrincipled")
    nodes.append(bsdf)

    if diffuse_image is not None:
        tex = _FakeNode("ShaderNodeTexImage", image=_make_image(diffuse_image))
        nodes.append(tex)
        _link(tex.outputs["Color"], bsdf.inputs["Base Color"])

    if normal_image is not None:
        tex = _FakeNode("ShaderNodeTexImage", image=_make_image(normal_image))
        nm = _FakeNode("ShaderNodeNormalMap")
        nodes.extend([tex, nm])
        _link(tex.outputs["Color"], nm.inputs["Color"])
        _link(nm.outputs["Normal"], bsdf.inputs["Normal"])

    if glow_image is not None:
        tex = _FakeNode("ShaderNodeTexImage", image=_make_image(glow_image))
        nodes.append(tex)
        _link(tex.outputs["Color"], bsdf.inputs["Emission Color"])

    tree = SimpleNamespace(nodes=nodes)
    return SimpleNamespace(
        name=name,
        use_nodes=use_nodes,
        node_tree=tree,
        blend_method=blend_method,
        alpha_threshold=alpha_threshold,
    )


# ---- material_data_from_blender ------------------------------------------


def test_from_blender_reads_principled_constants() -> None:
    mat = _make_fake_material()
    data = material_data_from_blender(mat)
    assert data.name == "m"
    assert data.base_color == pytest.approx((0.4, 0.5, 0.6, 1.0))
    assert data.alpha == pytest.approx(0.9)
    assert data.smoothness == pytest.approx(1.0 - 0.2)
    assert data.specular_strength == pytest.approx(0.3)
    assert data.emissive_color == pytest.approx((0.7, 0.8, 0.9))
    assert data.emissive_multiple == pytest.approx(1.25)
    assert data.textures == {}


def test_from_blender_picks_up_diffuse_normal_and_glow_textures() -> None:
    mat = _make_fake_material(
        diffuse_image="textures/foo_d.dds",
        normal_image="textures/foo_n.dds",
        glow_image="textures/foo_g.dds",
    )
    data = material_data_from_blender(mat)
    assert data.textures == {
        "diffuse": "textures/foo_d.dds",
        "normal": "textures/foo_n.dds",
        "glow": "textures/foo_g.dds",
    }


def test_from_blender_routes_blend_method_to_alpha_flags() -> None:
    blend = material_data_from_blender(
        _make_fake_material(blend_method="BLEND")
    )
    assert blend.alpha_blend and not blend.alpha_test

    clip = material_data_from_blender(
        _make_fake_material(blend_method="CLIP", alpha_threshold=128 / 255.0)
    )
    assert clip.alpha_test and not clip.alpha_blend
    assert clip.alpha_threshold == 128


def test_from_blender_handles_node_less_material_with_defaults() -> None:
    mat = SimpleNamespace(name="bare", use_nodes=False, blend_method="OPAQUE")
    data = material_data_from_blender(mat)
    assert data.name == "bare"
    assert data.alpha == 1.0  # MaterialData default


# ---- material_data_to_bslighting -----------------------------------------


def test_to_bslighting_populates_sse_fields() -> None:
    data = MaterialData(
        name="m",
        base_color=(1.0, 0.5, 0.25, 0.5),
        alpha=0.5,
        smoothness=0.7,
        specular_color=(0.1, 0.2, 0.3),
        specular_strength=0.4,
        emissive_color=(0.8, 0.9, 1.0),
        emissive_multiple=2.5,
        glossiness=42.0,
        uv_offset=(0.25, -0.5),
        uv_scale=(2.0, 3.0),
        shader_type=4,
        shader_flags_1=0xFEEDFACE,
        shader_flags_2=0xCAFEBABE,
    )
    blk = material_data_to_bslighting(data, name_index=7, texture_set_ref=42)
    assert isinstance(blk, BSLightingShaderProperty)
    assert blk.name is not None
    assert int(blk.name.index) == 7
    assert blk.texture_set == 42
    assert blk.alpha == pytest.approx(0.5)
    assert blk.smoothness == pytest.approx(0.7)
    assert blk.glossiness == pytest.approx(42.0)
    assert blk.specular_strength == pytest.approx(0.4)
    assert blk.specular_color is not None
    assert (blk.specular_color.r, blk.specular_color.g, blk.specular_color.b) == pytest.approx((0.1, 0.2, 0.3))
    assert blk.emissive_color is not None
    assert blk.emissive_multiple == pytest.approx(2.5)
    assert blk.uv_offset is not None
    assert (blk.uv_offset.u, blk.uv_offset.v) == pytest.approx((0.25, -0.5))
    assert (blk.uv_scale.u, blk.uv_scale.v) == pytest.approx((2.0, 3.0))
    assert blk.shader_type == 4
    assert blk.shader_flags_1 == 0xFEEDFACE
    assert blk.shader_flags_2 == 0xCAFEBABE
    assert blk.controller == -1


def test_to_bslighting_defaults_texture_set_ref_to_minus_one() -> None:
    blk = material_data_to_bslighting(MaterialData(name="m"))
    assert blk.texture_set == -1


# ---- material_data_to_bseffect -------------------------------------------


def test_to_bseffect_populates_inline_textures_and_base_color() -> None:
    data = MaterialData(
        name="fx",
        origin="BSEffectShaderProperty",
        base_color=(0.2, 0.4, 0.6, 0.8),
        emissive_multiple=1.5,
        emissive_color=(0.3, 0.0, 0.0),
        textures={
            "diffuse": "textures/fx/d.dds",
            "normal": "textures/fx/n.dds",
            "environment": "textures/cube.dds",
            "glow": "textures/fx/g.dds",
        },
    )
    blk = material_data_to_bseffect(data, name_index=3)
    assert isinstance(blk, BSEffectShaderProperty)
    assert int(blk.name.index) == 3
    assert blk.base_color is not None
    assert (
        blk.base_color.r,
        blk.base_color.g,
        blk.base_color.b,
        blk.base_color.a,
    ) == pytest.approx((0.2, 0.4, 0.6, 0.8))
    assert blk.base_color_scale == pytest.approx(1.5)
    assert bytes(blk.source_texture.value).decode("latin-1") == "textures/fx/d.dds"
    assert bytes(blk.normal_texture.value).decode("latin-1") == "textures/fx/n.dds"
    assert bytes(blk.env_map_texture.value).decode("latin-1") == "textures/cube.dds"
    assert bytes(blk.emit_gradient_texture.value).decode("latin-1") == "textures/fx/g.dds"


# ---- build_texture_set ---------------------------------------------------


def test_build_texture_set_returns_none_for_empty_textures() -> None:
    assert build_texture_set(MaterialData(name="m")) is None


def test_build_texture_set_emits_stable_slot_layout() -> None:
    data = MaterialData(
        name="m",
        textures={
            "diffuse": "d.dds",
            "normal": "n.dds",
            "environment": "e.dds",
        },
    )
    ts = build_texture_set(data)
    assert isinstance(ts, BSShaderTextureSet)
    assert ts.num_textures == 8
    assert bytes(ts.textures[0].value).decode("latin-1") == "d.dds"
    assert bytes(ts.textures[1].value).decode("latin-1") == "n.dds"
    assert bytes(ts.textures[2].value).decode("latin-1") == ""  # glow empty
    assert bytes(ts.textures[3].value).decode("latin-1") == ""  # height empty
    assert bytes(ts.textures[4].value).decode("latin-1") == "e.dds"


# ---- build_alpha_property ------------------------------------------------


def test_build_alpha_property_returns_none_for_opaque() -> None:
    assert build_alpha_property(MaterialData(name="m")) is None


def test_build_alpha_property_blend_sets_bit_0() -> None:
    blk = build_alpha_property(MaterialData(name="m", alpha_blend=True))
    assert isinstance(blk, NiAlphaProperty)
    assert blk.flags is not None
    assert blk.flags.alpha_blend == 1
    assert blk.flags.alpha_test == 0


def test_build_alpha_property_test_sets_bit_9_and_threshold() -> None:
    blk = build_alpha_property(
        MaterialData(name="m", alpha_test=True, alpha_threshold=200)
    )
    assert blk is not None
    assert blk.flags.alpha_test == 1
    assert blk.threshold == 200


# ---- export_material dispatch -------------------------------------------


def test_export_material_dispatches_to_bslighting_by_default() -> None:
    mat = _make_fake_material()
    blk = export_material(mat, name_index=1, texture_set_ref=-1)
    assert isinstance(blk, BSLightingShaderProperty)


def test_export_material_dispatches_to_bseffect_when_origin_overridden() -> None:
    mat = _make_fake_material()
    blk = export_material(mat, origin="BSEffectShaderProperty", name_index=2)
    assert isinstance(blk, BSEffectShaderProperty)


# ---- end-to-end material round-trip --------------------------------------


def test_material_round_trip_through_block_table() -> None:
    """MaterialData -> bslighting + texture set -> BlockTable -> import -> MaterialData."""
    src = MaterialData(
        name="rt",
        base_color=(0.5, 0.5, 0.5, 1.0),
        alpha=0.75,
        smoothness=0.6,
        specular_color=(0.2, 0.4, 0.6),
        specular_strength=0.8,
        emissive_color=(0.1, 0.2, 0.3),
        emissive_multiple=1.5,
        glossiness=20.0,
        uv_offset=(0.0, 0.0),
        uv_scale=(1.0, 1.0),
        shader_type=2,
        shader_flags_1=0xAABBCCDD,
        shader_flags_2=0x11223344,
        textures={
            "diffuse": "textures/rt_d.dds",
            "normal": "textures/rt_n.dds",
        },
    )
    ts = build_texture_set(src)
    assert ts is not None
    shader = material_data_to_bslighting(src, name_index=0, texture_set_ref=1)

    # Mock up a minimal table: blocks[0] = shader, blocks[1] = texture set,
    # header.strings[0] = "rt".
    h = Header()
    from nifblend.format.generated.structs import SizedString

    h.strings = [SizedString(length=2, value=list(b"rt"))]
    h.num_strings = 1
    table = BlockTable(
        header=h,
        blocks=[shader, ts],
        ctx=ReadContext(version=0x14020007, user_version=12, bs_version=100),
    )

    decoded = bslighting_to_material_data(shader, table)
    assert decoded.name == "rt"
    assert decoded.alpha == pytest.approx(0.75)
    assert decoded.smoothness == pytest.approx(0.6)
    assert decoded.specular_color == pytest.approx((0.2, 0.4, 0.6))
    assert decoded.specular_strength == pytest.approx(0.8)
    assert decoded.emissive_color == pytest.approx((0.1, 0.2, 0.3))
    assert decoded.emissive_multiple == pytest.approx(1.5)
    assert decoded.glossiness == pytest.approx(20.0)
    assert decoded.shader_type == 2
    assert decoded.shader_flags_1 == 0xAABBCCDD
    assert decoded.shader_flags_2 == 0x11223344
    assert decoded.textures == {
        "diffuse": "textures/rt_d.dds",
        "normal": "textures/rt_n.dds",
    }


def test_bseffect_material_round_trip() -> None:
    src = MaterialData(
        name="fx",
        origin="BSEffectShaderProperty",
        base_color=(0.7, 0.6, 0.5, 0.4),
        emissive_color=(0.3, 0.3, 0.3),
        emissive_multiple=2.0,
        shader_type=1,
        shader_flags_1=0xDEADBEEF,
        shader_flags_2=0xFEEDFACE,
        textures={
            "diffuse": "fx/d.dds",
            "normal": "fx/n.dds",
            "environment": "fx/e.dds",
            "glow": "fx/g.dds",
        },
    )
    blk = material_data_to_bseffect(src, name_index=0xFFFFFFFF)
    decoded = bseffect_to_material_data(blk, name="fx")
    assert decoded.base_color == pytest.approx((0.7, 0.6, 0.5, 0.4))
    assert decoded.emissive_color == pytest.approx((0.3, 0.3, 0.3))
    assert decoded.emissive_multiple == pytest.approx(2.0)
    assert decoded.textures == {
        "diffuse": "fx/d.dds",
        "normal": "fx/n.dds",
        "environment": "fx/e.dds",
        "glow": "fx/g.dds",
    }
    assert decoded.shader_type == 1
    assert decoded.shader_flags_1 == 0xDEADBEEF
    assert decoded.shader_flags_2 == 0xFEEDFACE
