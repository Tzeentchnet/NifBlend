"""Unit tests for :mod:`nifblend.bridge.mesh_in`.

The bridge is split so the BSTriShape -> :class:`MeshData` conversion is
pure and testable without Blender. The Blender-side wrapper is exercised
through a small fake ``bpy`` module asserted against ``foreach_set`` calls.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.mesh_in import (
    MeshData,
    bstrishape_to_mesh_data,
    mesh_data_to_blender,
)
from nifblend.format.generated.bitfields import BSVertexDesc
from nifblend.format.generated.blocks import BSTriShape
from nifblend.format.generated.structs import (
    ByteColor4,
    ByteVector3,
    HalfTexCoord,
    HalfVector3,
    SizedString,
    Triangle,
    Vector3,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)

# ---- helpers --------------------------------------------------------------


def _vertex_record(
    *,
    vertex: Vector3 | HalfVector3 | None = None,
    uv: HalfTexCoord | None = None,
    normal: ByteVector3 | None = None,
    bitangent_y: int = 0,
    tangent: ByteVector3 | None = None,
    bitangent_z: int = 0,
    bitangent_x: float = 0.0,
    vertex_colors: ByteColor4 | None = None,
    bone_weights: list[float] | None = None,
    bone_indices: list[int] | None = None,
) -> SimpleNamespace:
    """Build a duck-typed vertex record matching the BSVertexData shape."""
    return SimpleNamespace(
        vertex=vertex,
        uv=uv,
        normal=normal,
        bitangent_y=bitangent_y,
        tangent=tangent,
        bitangent_z=bitangent_z,
        bitangent_x=bitangent_x,
        vertex_colors=vertex_colors,
        bone_weights=bone_weights or [],
        bone_indices=bone_indices or [],
    )


def _triangle_block(verts: list[Any], tris: list[Triangle], desc_attrs: int) -> BSTriShape:
    blk = BSTriShape()
    blk.vertex_desc = BSVertexDesc(vertex_attributes=desc_attrs)
    blk.num_vertices = len(verts)
    blk.num_triangles = len(tris)
    blk.vertex_data = verts
    blk.triangles = tris
    return blk


# ---- conversion: positions + triangles -----------------------------------


def test_minimal_positions_and_triangles() -> None:
    verts = [
        _vertex_record(vertex=Vector3(0.0, 0.0, 0.0)),
        _vertex_record(vertex=Vector3(1.0, 0.0, 0.0)),
        _vertex_record(vertex=Vector3(0.0, 1.0, 0.0)),
    ]
    blk = _triangle_block(verts, [Triangle(0, 1, 2)], desc_attrs=0x401)

    data = bstrishape_to_mesh_data(blk, name="tri")

    assert data.name == "tri"
    np.testing.assert_array_equal(
        data.positions,
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
    )
    np.testing.assert_array_equal(
        data.triangles,
        np.array([[0, 1, 2]], dtype=np.uint32),
    )
    assert data.normals is None
    assert data.uv is None
    assert data.vertex_colors is None
    assert data.bone_weights is None


def test_empty_block_yields_empty_arrays() -> None:
    blk = _triangle_block([], [], desc_attrs=0)
    data = bstrishape_to_mesh_data(blk, name="empty")
    assert data.positions.shape == (0, 3)
    assert data.triangles.shape == (0, 3)


def test_half_precision_vertex_uses_halfvector3() -> None:
    verts = [_vertex_record(vertex=HalfVector3(1.5, -2.0, 3.25))]
    blk = _triangle_block(verts, [], desc_attrs=0x001)  # not full-precision
    data = bstrishape_to_mesh_data(blk, name="half")
    np.testing.assert_array_almost_equal(
        data.positions, np.array([[1.5, -2.0, 3.25]], dtype=np.float32)
    )


# ---- conversion: per-attribute decoders ----------------------------------


def test_uvs_passed_through_unflipped() -> None:
    # The bridge stores raw NIF UVs; the Blender wrapper does the V flip.
    verts = [_vertex_record(uv=HalfTexCoord(0.25, 0.75))]
    blk = _triangle_block(verts, [], desc_attrs=0x002)
    data = bstrishape_to_mesh_data(blk)
    assert data.uv is not None
    np.testing.assert_array_almost_equal(
        data.uv, np.array([[0.25, 0.75]], dtype=np.float32)
    )


def test_normals_decoded_from_byte_to_unit_range() -> None:
    # 0 -> -1, 255 -> +1 (approx, via /127.5 - 1)
    verts = [_vertex_record(normal=ByteVector3(0, 255, 128))]
    blk = _triangle_block(verts, [], desc_attrs=0x008)
    data = bstrishape_to_mesh_data(blk)
    assert data.normals is not None
    np.testing.assert_allclose(
        data.normals, np.array([[-1.0, 1.0, 128 / 127.5 - 1.0]]), atol=1e-6
    )


def test_tangents_require_normals_and_tangent_bits() -> None:
    verts = [
        _vertex_record(
            normal=ByteVector3(255, 128, 0),
            tangent=ByteVector3(64, 64, 64),
            bitangent_y=200,
            bitangent_z=50,
            bitangent_x=0.5,
        )
    ]
    blk = _triangle_block(verts, [], desc_attrs=0x008 | 0x010)
    data = bstrishape_to_mesh_data(blk)
    assert data.tangents is not None
    assert data.bitangents is not None
    np.testing.assert_allclose(
        data.tangents[0], np.array([64 / 127.5 - 1] * 3), atol=1e-6
    )
    np.testing.assert_allclose(
        data.bitangents[0],
        np.array([0.5, 200 / 127.5 - 1.0, 50 / 127.5 - 1.0]),
        atol=1e-6,
    )


def test_vertex_colors_normalised_to_unit_floats() -> None:
    verts = [_vertex_record(vertex_colors=ByteColor4(255, 0, 128, 64))]
    blk = _triangle_block(verts, [], desc_attrs=0x020)
    data = bstrishape_to_mesh_data(blk)
    assert data.vertex_colors is not None
    np.testing.assert_allclose(
        data.vertex_colors[0],
        np.array([1.0, 0.0, 128 / 255.0, 64 / 255.0]),
        atol=1e-6,
    )


def test_skinning_attributes_extracted() -> None:
    verts = [
        _vertex_record(
            bone_weights=[0.6, 0.3, 0.1, 0.0],
            bone_indices=[7, 4, 2, 0],
        )
    ]
    blk = _triangle_block(verts, [], desc_attrs=0x040)
    data = bstrishape_to_mesh_data(blk)
    assert data.bone_weights is not None
    assert data.bone_indices is not None
    np.testing.assert_array_almost_equal(
        data.bone_weights, np.array([[0.6, 0.3, 0.1, 0.0]], dtype=np.float32)
    )
    np.testing.assert_array_equal(
        data.bone_indices, np.array([[7, 4, 2, 0]], dtype=np.uint8)
    )


# ---- name resolution ------------------------------------------------------


def test_name_resolved_from_block_table_strings() -> None:
    blk = BSTriShape()
    blk.name = nif_string(index=1)
    blk.vertex_desc = BSVertexDesc(vertex_attributes=0)
    blk.vertex_data = []
    blk.triangles = []

    table = SimpleNamespace(
        header=SimpleNamespace(
            strings=[
                SizedString(length=5, value=list(b"first")),
                SizedString(length=6, value=list(b"second")),
            ]
        )
    )
    data = bstrishape_to_mesh_data(blk, table)  # type: ignore[arg-type]
    assert data.name == "second"


def test_name_falls_back_when_index_invalid() -> None:
    blk = BSTriShape()
    blk.name = nif_string(index=0xFFFFFFFF)
    blk.vertex_desc = BSVertexDesc(vertex_attributes=0)
    blk.vertex_data = []
    blk.triangles = []
    data = bstrishape_to_mesh_data(blk, table=None)
    assert data.name == "BSTriShape"


# ---- Blender wrapper ------------------------------------------------------


class _FakeUVData:
    def __init__(self) -> None:
        self.uv: list[float] = []

    def foreach_set(self, attr: str, values: Any) -> None:
        assert attr == "uv"
        self.uv = list(values)


class _FakeUVLayer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.data = _FakeUVData()


class _FakeUVLayers:
    def __init__(self) -> None:
        self.layers: list[_FakeUVLayer] = []

    def new(self, name: str) -> _FakeUVLayer:
        layer = _FakeUVLayer(name)
        self.layers.append(layer)
        return layer


class _FakeColorAttrData:
    def __init__(self) -> None:
        self.color: list[float] = []

    def foreach_set(self, attr: str, values: Any) -> None:
        assert attr == "color"
        self.color = list(values)


class _FakeColorAttribute:
    def __init__(self, name: str, type: str, domain: str) -> None:
        self.name, self.type, self.domain = name, type, domain
        self.data = _FakeColorAttrData()


class _FakeColorAttributes:
    def __init__(self) -> None:
        self.attrs: list[_FakeColorAttribute] = []

    def new(self, name: str, type: str, domain: str) -> _FakeColorAttribute:
        attr = _FakeColorAttribute(name, type, domain)
        self.attrs.append(attr)
        return attr


class _FakeMesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.from_pydata_args: tuple[Any, ...] | None = None
        self.uv_layers = _FakeUVLayers()
        self.color_attributes = _FakeColorAttributes()
        self.split_normals: list[list[float]] | None = None
        self.use_auto_smooth = False
        self.updated = False

    def from_pydata(self, verts: Any, edges: Any, faces: Any) -> None:
        self.from_pydata_args = (verts, edges, faces)

    def normals_split_custom_set(self, normals: list[list[float]]) -> None:
        self.split_normals = normals

    def update(self) -> None:
        self.updated = True


class _FakeMeshes:
    def __init__(self) -> None:
        self.created: list[_FakeMesh] = []

    def new(self, name: str) -> _FakeMesh:
        mesh = _FakeMesh(name)
        self.created.append(mesh)
        return mesh


@pytest.fixture
def fake_bpy() -> SimpleNamespace:
    return SimpleNamespace(data=SimpleNamespace(meshes=_FakeMeshes()))


def test_blender_wrapper_pipes_geometry_via_from_pydata(fake_bpy: Any) -> None:
    data = MeshData(
        name="cube",
        positions=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )
    mesh = mesh_data_to_blender(data, bpy=fake_bpy)
    assert mesh.name == "cube"
    assert mesh.from_pydata_args is not None
    verts, edges, faces = mesh.from_pydata_args
    assert verts == [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert edges == []
    assert faces == [[0, 1, 2]]
    assert mesh.updated


def test_blender_wrapper_flips_uv_v(fake_bpy: Any) -> None:
    data = MeshData(
        name="uvtest",
        positions=np.zeros((3, 3), dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        uv=np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.9]], dtype=np.float32),
    )
    mesh = mesh_data_to_blender(data, bpy=fake_bpy)
    layer = mesh.uv_layers.layers[0]
    assert layer.name == "UVMap"
    # Three loops × 2 floats = 6 entries; V flipped to 1 - V.
    assert layer.data.uv == pytest.approx(
        [0.1, 1 - 0.2, 0.3, 1 - 0.4, 0.5, 1 - 0.9]
    )


def test_blender_wrapper_writes_vertex_colors(fake_bpy: Any) -> None:
    data = MeshData(
        name="col",
        positions=np.zeros((2, 3), dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.uint32),
        vertex_colors=np.array(
            [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 0.5]], dtype=np.float32
        ),
    )
    mesh = mesh_data_to_blender(data, bpy=fake_bpy)
    attr = mesh.color_attributes.attrs[0]
    assert (attr.name, attr.type, attr.domain) == ("Color", "FLOAT_COLOR", "POINT")
    assert attr.data.color == pytest.approx([1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.5])
