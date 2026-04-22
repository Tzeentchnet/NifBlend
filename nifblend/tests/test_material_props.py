"""Unit tests for :mod:`nifblend.bridge.material_props` (Phase 3 step 13).

The real PropertyGroup classes are registered against the bpy stub at
import time (see ``conftest.py``); these tests exercise the duck-typed
:func:`apply_material_data_to_props` /
:func:`read_material_data_from_props` helpers and the end-to-end
round-trip through the material bridge.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge import material_props
from nifblend.bridge.material_in import MaterialData, material_data_to_blender
from nifblend.bridge.material_out import material_data_from_blender
from nifblend.bridge.material_props import (
    PROP_ATTR,
    apply_material_data_to_props,
    read_material_data_from_props,
)

# ---- minimal fakes -------------------------------------------------------


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
        else:  # pragma: no cover
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


# ---- PropertyGroup class shape -------------------------------------------


def test_property_group_classes_exported() -> None:
    assert hasattr(material_props, "NifBlendMaterialProperties")
    assert hasattr(material_props, "NifBlendMaterialTextureSlot")


def test_property_group_has_expected_annotations() -> None:
    ann = material_props.NifBlendMaterialProperties.__annotations__
    for expected in (
        "origin",
        "shader_type",
        "shader_flags_1",
        "shader_flags_2",
        "alpha_threshold",
        "emissive_multiple",
        "glossiness",
        "specular_strength",
        "specular_color",
        "uv_offset",
        "uv_scale",
        "textures",
    ):
        assert expected in ann, f"missing PropertyGroup field {expected!r}"


# ---- apply / read helpers ------------------------------------------------


def test_apply_creates_props_on_bare_material() -> None:
    mat = SimpleNamespace(name="m")
    data = MaterialData(
        name="m",
        shader_type=7,
        shader_flags_1=0xDEADBEEF,
        shader_flags_2=0x12345678,
        glossiness=30.0,
        specular_color=(0.9, 0.8, 0.7),
        specular_strength=1.5,
        emissive_multiple=2.0,
        uv_offset=(0.25, 0.5),
        uv_scale=(2.0, 3.0),
        alpha_threshold=200,
        textures={
            "diffuse": "textures/foo_d.dds",
            "environment": "textures/foo_e.dds",
        },
    )

    apply_material_data_to_props(mat, data)

    props = getattr(mat, PROP_ATTR)
    assert props.shader_type == 7
    assert props.shader_flags_1 == 0xDEADBEEF
    assert props.shader_flags_2 == 0x12345678
    assert props.glossiness == pytest.approx(30.0)
    assert props.specular_color == pytest.approx((0.9, 0.8, 0.7))
    assert props.specular_strength == pytest.approx(1.5)
    assert props.emissive_multiple == pytest.approx(2.0)
    assert props.uv_offset == pytest.approx((0.25, 0.5))
    assert props.uv_scale == pytest.approx((2.0, 3.0))
    assert props.alpha_threshold == 200
    assert props.origin == "BSLightingShaderProperty"
    assert props.textures == {
        "diffuse": "textures/foo_d.dds",
        "environment": "textures/foo_e.dds",
    }


def test_apply_preserves_bseffect_origin() -> None:
    mat = SimpleNamespace(name="m")
    data = MaterialData(name="m", origin="BSEffectShaderProperty")
    apply_material_data_to_props(mat, data)
    assert getattr(mat, PROP_ATTR).origin == "BSEffectShaderProperty"


def test_read_restores_fields_into_fresh_material_data() -> None:
    mat = SimpleNamespace(
        **{
            PROP_ATTR: SimpleNamespace(
                origin="BSEffectShaderProperty",
                shader_type=5,
                shader_flags_1=0xAABBCCDD,
                shader_flags_2=0x11223344,
                alpha_threshold=128,
                emissive_multiple=3.5,
                glossiness=25.0,
                specular_strength=0.5,
                specular_color=(0.1, 0.2, 0.3),
                uv_offset=(0.125, 0.25),
                uv_scale=(4.0, 2.0),
                textures={"height": "textures/height.dds"},
            )
        }
    )
    data = MaterialData(name="m")
    read_material_data_from_props(mat, data)

    assert data.origin == "BSEffectShaderProperty"
    assert data.shader_type == 5
    assert data.shader_flags_1 == 0xAABBCCDD
    assert data.shader_flags_2 == 0x11223344
    assert data.alpha_threshold == 128
    assert data.emissive_multiple == pytest.approx(3.5)
    assert data.glossiness == pytest.approx(25.0)
    assert data.specular_strength == pytest.approx(0.5)
    assert data.specular_color == pytest.approx((0.1, 0.2, 0.3))
    assert data.uv_offset == pytest.approx((0.125, 0.25))
    assert data.uv_scale == pytest.approx((4.0, 2.0))
    assert data.textures == {"height": "textures/height.dds"}


def test_read_does_not_clobber_textures_already_found_in_graph() -> None:
    mat = SimpleNamespace(
        **{
            PROP_ATTR: SimpleNamespace(
                textures={
                    "diffuse": "propgroup_diffuse.dds",
                    "height": "height.dds",
                }
            )
        }
    )
    data = MaterialData(name="m", textures={"diffuse": "graph_diffuse.dds"})
    read_material_data_from_props(mat, data)

    # The graph-sourced value wins for slots Blender could represent.
    assert data.textures["diffuse"] == "graph_diffuse.dds"
    # Slots Blender can't represent are merged from the PropertyGroup.
    assert data.textures["height"] == "height.dds"


def test_read_is_noop_when_props_absent() -> None:
    mat = SimpleNamespace(name="m")
    data = MaterialData(name="m", shader_flags_1=42)
    read_material_data_from_props(mat, data)
    # Defaults unchanged, pre-existing value preserved.
    assert data.shader_flags_1 == 42
    assert data.shader_type == 0


# ---- CollectionProperty-style textures ----------------------------------


class _FakeTextureSlotItem:
    def __init__(self) -> None:
        self.slot = ""
        self.path = ""


class _FakeTextureCollection:
    def __init__(self) -> None:
        self._items: list[_FakeTextureSlotItem] = []

    def clear(self) -> None:
        self._items.clear()

    def add(self) -> _FakeTextureSlotItem:
        item = _FakeTextureSlotItem()
        self._items.append(item)
        return item

    def __iter__(self):
        return iter(self._items)


def test_apply_uses_collection_add_when_available() -> None:
    mat = SimpleNamespace(name="m")
    mat.nifblend = SimpleNamespace(textures=_FakeTextureCollection())
    data = MaterialData(
        name="m",
        textures={"diffuse": "d.dds", "normal": "n.dds"},
    )

    apply_material_data_to_props(mat, data)

    coll = mat.nifblend.textures
    pairs = [(it.slot, it.path) for it in coll]
    assert pairs == [("diffuse", "d.dds"), ("normal", "n.dds")]


def test_read_walks_collection_items() -> None:
    coll = _FakeTextureCollection()
    for slot, path in (("subsurface", "s.dds"), ("env_mask", "e.dds")):
        item = coll.add()
        item.slot = slot
        item.path = path
    mat = SimpleNamespace(name="m", nifblend=SimpleNamespace(textures=coll))
    data = MaterialData(name="m")
    read_material_data_from_props(mat, data)
    assert data.textures == {"subsurface": "s.dds", "env_mask": "e.dds"}


# ---- end-to-end via the bridge ------------------------------------------


def test_import_stashes_nif_only_state_on_material() -> None:
    data = MaterialData(
        name="m",
        shader_type=3,
        shader_flags_1=0xCAFEBABE,
        shader_flags_2=0x0BADF00D,
        glossiness=42.0,
        specular_color=(0.5, 0.25, 0.125),
        uv_offset=(0.1, 0.2),
        uv_scale=(1.5, 2.5),
        alpha_threshold=99,
        origin="BSEffectShaderProperty",
        textures={
            "diffuse": "d.dds",
            "height": "h.dds",
            "environment": "cube.dds",
        },
    )
    bpy = _make_fake_bpy()

    mat = material_data_to_blender(data, bpy=bpy)

    assert hasattr(mat, PROP_ATTR)
    props = mat.nifblend
    assert props.shader_type == 3
    assert props.shader_flags_1 == 0xCAFEBABE
    assert props.shader_flags_2 == 0x0BADF00D
    assert props.glossiness == pytest.approx(42.0)
    assert props.uv_offset == pytest.approx((0.1, 0.2))
    assert props.uv_scale == pytest.approx((1.5, 2.5))
    assert props.alpha_threshold == 99
    assert props.origin == "BSEffectShaderProperty"
    # All three NIF slots are recorded, including ones the Principled
    # graph never plugs in (height, environment).
    assert props.textures == {
        "diffuse": "d.dds",
        "height": "h.dds",
        "environment": "cube.dds",
    }


def test_import_export_round_trip_preserves_nif_only_state() -> None:
    data_in = MaterialData(
        name="m",
        shader_type=4,
        shader_flags_1=0x1234_5678,
        shader_flags_2=0x9ABC_DEF0,
        glossiness=55.0,
        specular_color=(0.2, 0.4, 0.8),
        specular_strength=0.75,
        emissive_color=(0.1, 0.2, 0.3),
        emissive_multiple=2.5,
        base_color=(0.5, 0.6, 0.7, 0.9),
        alpha=0.9,
        smoothness=0.6,
        uv_offset=(0.3, 0.4),
        uv_scale=(1.25, 1.75),
        alpha_threshold=77,
        alpha_test=True,
        origin="BSLightingShaderProperty",
        textures={
            "diffuse": "textures/armor_d.dds",
            "normal": "textures/armor_n.dds",
            "glow": "textures/armor_g.dds",
            "height": "textures/armor_p.dds",
            "environment": "textures/cube.dds",
            "env_mask": "textures/em.dds",
        },
    )
    bpy = _make_fake_bpy()
    mat = material_data_to_blender(data_in, bpy=bpy)

    data_out = material_data_from_blender(mat)

    # NIF-only fields survive exactly.
    assert data_out.shader_type == data_in.shader_type
    assert data_out.shader_flags_1 == data_in.shader_flags_1
    assert data_out.shader_flags_2 == data_in.shader_flags_2
    assert data_out.glossiness == pytest.approx(data_in.glossiness)
    assert data_out.specular_color == pytest.approx(data_in.specular_color)
    assert data_out.uv_offset == pytest.approx(data_in.uv_offset)
    assert data_out.uv_scale == pytest.approx(data_in.uv_scale)
    assert data_out.alpha_threshold == data_in.alpha_threshold
    assert data_out.origin == data_in.origin
    assert data_out.emissive_multiple == pytest.approx(data_in.emissive_multiple)
    # All texture slots — including ones the Principled graph skips —
    # survive the round-trip.
    for slot, path in data_in.textures.items():
        assert data_out.textures.get(slot) == path, f"lost texture slot {slot!r}"
