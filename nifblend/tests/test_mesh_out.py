"""Unit tests for :mod:`nifblend.bridge.mesh_out` plus a full
mesh_in → mesh_out round-trip on a synthesised BSTriShape.

Like ``test_mesh_in.py``, the Blender side is exercised through a tiny
duck-typed fake: a ``_FakeMesh`` exposing ``vertices``, ``polygons``,
``loops``, ``uv_layers``, and ``color_attributes`` with the small
``foreach_get`` surface the bridge actually consumes.
"""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.mesh_in import bstrishape_to_mesh_data
from nifblend.bridge.mesh_out import (
    export_bstrishape,
    mesh_data_from_blender,
    mesh_data_to_bstrishape,
    vertex_attributes_for,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import BSTriShape
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
)
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, read_nif, write_nif

# ---- duck-typed bpy fakes ------------------------------------------------


class _BufList:
    """Minimal foreach_get target -- a list of records exposing attrs."""

    def __init__(self, records: list[Any]) -> None:
        self._records = records

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def __getitem__(self, i: int) -> Any:
        return self._records[i]

    def foreach_get(self, attr: str, buf: np.ndarray) -> None:
        # `attr` is one of "co" (3-tuple), "normal" (3-tuple), "vertex_index"
        # (scalar), "uv" (2-tuple), "vertices" (3-tuple loop_triangle).
        flat: list[float] = []
        for rec in self._records:
            v = getattr(rec, attr)
            if isinstance(v, tuple | list | np.ndarray):
                flat.extend(float(x) for x in v)
            else:
                flat.append(float(v))
        buf[:] = np.asarray(flat, dtype=buf.dtype)


def _vertex(co: tuple[float, float, float], normal: tuple[float, float, float] = (0, 0, 1)) -> SimpleNamespace:
    return SimpleNamespace(co=co, normal=normal)


def _loop(vi: int) -> SimpleNamespace:
    return SimpleNamespace(vertex_index=vi)


def _polygon(verts: tuple[int, int, int]) -> SimpleNamespace:
    return SimpleNamespace(vertices=verts)


def _make_fake_mesh(
    *,
    name: str = "fake",
    positions: list[tuple[float, float, float]],
    normals: list[tuple[float, float, float]] | None = None,
    triangles: list[tuple[int, int, int]],
    loop_uvs: list[tuple[float, float]] | None = None,
    vertex_colors: list[tuple[float, float, float, float]] | None = None,
) -> SimpleNamespace:
    """Construct a duck-typed mesh that satisfies the mesh_out reader."""
    if normals is None:
        normals = [(0.0, 0.0, 1.0)] * len(positions)
    verts = _BufList([_vertex(p, n) for p, n in zip(positions, normals, strict=False)])
    polys = _BufList([_polygon(t) for t in triangles])

    uv_layers: SimpleNamespace
    if loop_uvs is not None:
        loops = _BufList([_loop(vi) for tri in triangles for vi in tri])
        uv_records = _BufList([SimpleNamespace(uv=uv) for uv in loop_uvs])
        layer = SimpleNamespace(name="UVMap", data=uv_records)
        uv_layers = SimpleNamespace(active=layer, __len__=lambda: 1)
        # _BufList-style indexing
        uv_layers = type("UVLayers", (), {})()
        uv_layers.active = layer
        uv_layers._items = [layer]
        uv_layers.__class__.__len__ = lambda self: len(self._items)
        uv_layers.__class__.__getitem__ = lambda self, i: self._items[i]
    else:
        uv_layers = type("UVLayers", (), {})()
        uv_layers.active = None
        uv_layers._items = []
        uv_layers.__class__.__len__ = lambda self: 0
        uv_layers.__class__.__getitem__ = lambda self, i: self._items[i]
    loops = _BufList([_loop(vi) for tri in triangles for vi in tri])

    color_attributes_items: list[Any] = []
    if vertex_colors is not None:
        attr_data = _BufList([SimpleNamespace(color=c) for c in vertex_colors])
        attr = SimpleNamespace(name="Color", domain="POINT", data=attr_data)
        color_attributes_items.append(attr)

    color_attributes = type("ColorAttrs", (), {})()
    color_attributes._items = color_attributes_items
    color_attributes.__class__.__len__ = lambda self: len(self._items)
    color_attributes.__class__.__getitem__ = lambda self, i: self._items[i]

    return SimpleNamespace(
        name=name,
        vertices=verts,
        loops=loops,
        polygons=polys,
        uv_layers=uv_layers,
        color_attributes=color_attributes,
    )


# ---- vertex_attributes_for -----------------------------------------------


def test_vertex_attributes_for_minimal() -> None:
    from nifblend.bridge.mesh_in import MeshData

    data = MeshData(
        name="x",
        positions=np.zeros((0, 3), dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.uint32),
    )
    assert vertex_attributes_for(data) == 0x001


def test_vertex_attributes_for_full_set() -> None:
    from nifblend.bridge.mesh_in import MeshData

    n = 1
    data = MeshData(
        name="x",
        positions=np.zeros((n, 3), dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.uint32),
        normals=np.zeros((n, 3), dtype=np.float32),
        tangents=np.zeros((n, 3), dtype=np.float32),
        bitangents=np.zeros((n, 3), dtype=np.float32),
        uv=np.zeros((n, 2), dtype=np.float32),
        vertex_colors=np.zeros((n, 4), dtype=np.float32),
        bone_weights=np.zeros((n, 4), dtype=np.float32),
        bone_indices=np.zeros((n, 4), dtype=np.uint8),
    )
    flags = vertex_attributes_for(data, full_precision=True)
    assert flags == 0x001 | 0x002 | 0x008 | 0x010 | 0x020 | 0x040 | 0x400


# ---- mesh_data_from_blender ----------------------------------------------


def test_from_blender_extracts_positions_and_triangles() -> None:
    mesh = _make_fake_mesh(
        positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        triangles=[(0, 1, 2)],
    )
    data = mesh_data_from_blender(mesh)
    np.testing.assert_array_equal(
        data.positions,
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
    )
    np.testing.assert_array_equal(data.triangles, np.array([[0, 1, 2]], dtype=np.uint32))
    assert data.name == "fake"


def test_from_blender_flips_uv_v_back_to_nif() -> None:
    # Blender V is bottom-up; bridge stores NIF (top-down) UVs.
    mesh = _make_fake_mesh(
        positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        triangles=[(0, 1, 2)],
        loop_uvs=[(0.1, 0.2), (0.3, 0.4), (0.5, 0.9)],
    )
    data = mesh_data_from_blender(mesh)
    assert data.uv is not None
    np.testing.assert_array_almost_equal(
        data.uv,
        np.array([[0.1, 1 - 0.2], [0.3, 1 - 0.4], [0.5, 1 - 0.9]], dtype=np.float32),
    )


def test_from_blender_picks_up_point_domain_colors() -> None:
    mesh = _make_fake_mesh(
        positions=[(0, 0, 0), (1, 0, 0)],
        triangles=[],
        vertex_colors=[(1.0, 0.0, 0.0, 1.0), (0.0, 1.0, 0.0, 0.5)],
    )
    data = mesh_data_from_blender(mesh)
    assert data.vertex_colors is not None
    np.testing.assert_array_almost_equal(
        data.vertex_colors,
        np.array([[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 0.5]], dtype=np.float32),
    )


def test_from_blender_raises_on_non_triangle_polygon() -> None:
    mesh = _make_fake_mesh(positions=[(0, 0, 0)] * 4, triangles=[])
    # Manually inject a quad polygon; mesh_out must reject it.
    mesh.polygons = _BufList([_polygon((0, 1, 2, 3))])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be triangulated"):
        mesh_data_from_blender(mesh)


# ---- mesh_data_to_bstrishape ---------------------------------------------


def test_to_bstrishape_sets_descriptor_and_counts() -> None:
    from nifblend.bridge.mesh_in import MeshData

    data = MeshData(
        name="cube",
        positions=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        normals=np.array([[0, 0, 1]] * 3, dtype=np.float32),
    )
    blk = mesh_data_to_bstrishape(data)
    assert isinstance(blk, BSTriShape)
    assert blk.num_vertices == 3
    assert blk.num_triangles == 1
    assert blk.skin == -1
    assert blk.shader_property == -1
    assert blk.alpha_property == -1
    assert blk.vertex_desc is not None
    assert blk.vertex_desc.vertex_attributes == (0x001 | 0x008)
    assert blk.bounding_sphere is not None
    # 3 vertices forming a right triangle in the XY plane → centre on the
    # midpoint of the longest edge, radius half its length.
    assert blk.bounding_sphere.radius == pytest.approx(0.7071068, abs=1e-5)


def test_to_bstrishape_vertex_records_round_trip_through_decoder() -> None:
    from nifblend.bridge.mesh_in import MeshData

    data = MeshData(
        name="x",
        positions=np.array([[1.0, -2.0, 3.0]], dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.uint32),
        normals=np.array([[0.0, 1.0, 0.0]], dtype=np.float32),
        uv=np.array([[0.25, 0.75]], dtype=np.float32),
        vertex_colors=np.array([[1.0, 0.5, 0.0, 1.0]], dtype=np.float32),
    )
    blk = mesh_data_to_bstrishape(data, full_precision=True)
    decoded = bstrishape_to_mesh_data(blk, name="x")

    np.testing.assert_array_almost_equal(decoded.positions, data.positions)
    assert decoded.uv is not None
    np.testing.assert_array_almost_equal(decoded.uv, data.uv, decimal=3)
    assert decoded.normals is not None
    # u8 quantisation introduces ~1/127 error.
    np.testing.assert_allclose(decoded.normals, data.normals, atol=2 / 255)
    assert decoded.vertex_colors is not None
    np.testing.assert_allclose(decoded.vertex_colors, data.vertex_colors, atol=1 / 255)


# ---- end-to-end binary round-trip ----------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_header() -> tuple[Header, ReadContext]:
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    return h, ReadContext(version=h.version, user_version=h.user_version, bs_version=100)


def test_bstrishape_full_binary_round_trip() -> None:
    """Build a BSTriShape via the bridge, write it through write_nif, read it
    back, and verify every per-vertex attribute survives."""
    from nifblend.bridge.mesh_in import MeshData

    positions = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
    )
    data = MeshData(
        name="rt",
        positions=positions,
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        normals=np.array([[0.0, 0.0, 1.0]] * 3, dtype=np.float32),
        uv=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        vertex_colors=np.array(
            [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]],
            dtype=np.float32,
        ),
    )
    blk = mesh_data_to_bstrishape(data, full_precision=True)
    header, ctx = _sse_header()
    table = BlockTable(header=header, blocks=[blk], footer=Footer(), ctx=ctx)

    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    assert parsed.header.num_blocks == 1
    assert parsed.block_type_name(0) == "BSTriShape"
    rt_block = parsed.blocks[0]
    assert isinstance(rt_block, BSTriShape)
    assert rt_block.num_vertices == 3
    assert rt_block.num_triangles == 1
    assert rt_block.vertex_desc is not None
    # Same vertex_attributes survives the bitfield encode/decode.
    assert rt_block.vertex_desc.vertex_attributes == (
        0x001 | 0x002 | 0x008 | 0x020 | 0x400
    )

    # Decode back to MeshData and compare.
    decoded = bstrishape_to_mesh_data(rt_block, name="rt")
    np.testing.assert_array_almost_equal(decoded.positions, positions)
    assert decoded.uv is not None
    np.testing.assert_array_almost_equal(decoded.uv, data.uv, decimal=3)
    assert decoded.normals is not None
    np.testing.assert_allclose(decoded.normals, data.normals, atol=2 / 255)
    assert decoded.vertex_colors is not None
    np.testing.assert_allclose(decoded.vertex_colors, data.vertex_colors, atol=1 / 255)


def test_export_bstrishape_helper_consumes_fake_mesh() -> None:
    mesh = _make_fake_mesh(
        positions=[(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        triangles=[(0, 1, 2)],
        loop_uvs=[(0.1, 0.2), (0.3, 0.4), (0.5, 0.9)],
    )
    blk = export_bstrishape(mesh)
    assert isinstance(blk, BSTriShape)
    assert blk.num_vertices == 3
    assert blk.num_triangles == 1
    assert blk.vertex_desc is not None
    # Vertex + UV + Normals (vertices have a default normal of (0, 0, 1)).
    assert blk.vertex_desc.vertex_attributes & 0x002
    assert blk.vertex_desc.vertex_attributes & 0x008
