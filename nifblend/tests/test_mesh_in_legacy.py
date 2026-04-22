"""Unit tests for the legacy ``NiTriShape`` / ``NiTriStrips`` import path
(Phase 6 step 22 — Oblivion).

Covers:

* :func:`strips_to_triangles` — the pure D3D-strip → indexed-triangle
  decoder, including alternating winding and degenerate filtering.
* :func:`nitrishape_to_mesh_data` — packs a flat triangle list and the
  ``NiTriShapeData`` vertex / normal / UV / colour streams into the same
  ``MeshData`` container the BSTriShape path produces.
* :func:`nitristrips_to_mesh_data` — same, but reconstructs triangles from
  ``NiTriStripsData.strip_lengths`` + ``points``.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from nifblend.bridge.mesh_in import (
    nitrishape_to_mesh_data,
    nitristrips_to_mesh_data,
    strips_to_triangles,
)


def _vec3(x: float, y: float, z: float) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, z=z)


def _color(r: float, g: float, b: float, a: float) -> SimpleNamespace:
    return SimpleNamespace(r=r, g=g, b=b, a=a)


def _uv(u: float, v: float) -> SimpleNamespace:
    return SimpleNamespace(u=u, v=v)


def _tri(a: int, b: int, c: int) -> SimpleNamespace:
    return SimpleNamespace(v1=a, v2=b, v3=c)


# ---- strips_to_triangles --------------------------------------------------


def test_strips_to_triangles_alternates_winding_and_filters_degenerates() -> None:
    # Single strip [0,1,2,3,4] → triangles (0,1,2), (1,3,2 — flipped), (2,3,4)
    tris = strips_to_triangles([5], [[0, 1, 2, 3, 4]])
    assert tris.dtype == np.uint32
    assert tris.tolist() == [[0, 1, 2], [1, 3, 2], [2, 3, 4]]


def test_strips_to_triangles_skips_degenerate_triples() -> None:
    # The repeated 2 makes triples (1,2,2) and (2,2,3) degenerate — both
    # dropped, leaving only the leading (0,1,2) triangle.
    tris = strips_to_triangles([5], [[0, 1, 2, 2, 3]])
    assert tris.tolist() == [[0, 1, 2]]


def test_strips_to_triangles_handles_multiple_strips() -> None:
    tris = strips_to_triangles([4, 3], [[0, 1, 2, 3], [4, 5, 6]])
    # First strip: (0,1,2), (1,3,2 — flipped). Second strip: (4,5,6).
    assert tris.tolist() == [[0, 1, 2], [1, 3, 2], [4, 5, 6]]


def test_strips_to_triangles_returns_empty_on_no_input() -> None:
    tris = strips_to_triangles([], [])
    assert tris.shape == (0, 3)
    assert tris.dtype == np.uint32


def test_strips_to_triangles_skips_strips_shorter_than_three() -> None:
    tris = strips_to_triangles([2, 3], [[0, 1], [2, 3, 4]])
    assert tris.tolist() == [[2, 3, 4]]


def test_strips_to_triangles_truncates_to_declared_length() -> None:
    # ``points`` row may carry trailing junk; only ``strip_lengths[i]``
    # entries are walked.
    tris = strips_to_triangles([3], [[0, 1, 2, 99, 99]])
    assert tris.tolist() == [[0, 1, 2]]


# ---- nitrishape_to_mesh_data ---------------------------------------------


def test_nitrishape_to_mesh_data_packs_streams() -> None:
    data = SimpleNamespace(
        num_vertices=4,
        vertices=[_vec3(0, 0, 0), _vec3(1, 0, 0), _vec3(1, 1, 0), _vec3(0, 1, 0)],
        triangles=[_tri(0, 1, 2), _tri(0, 2, 3)],
        has_normals=True,
        normals=[_vec3(0, 0, 1)] * 4,
        tangents=[],
        bitangents=[],
        has_vertex_colors=True,
        vertex_colors=[
            _color(1.0, 0.0, 0.0, 1.0),
            _color(0.0, 1.0, 0.0, 1.0),
            _color(0.0, 0.0, 1.0, 1.0),
            _color(1.0, 1.0, 1.0, 1.0),
        ],
        uv_sets=[[_uv(0, 0), _uv(1, 0), _uv(1, 1), _uv(0, 1)]],
    )
    shape = SimpleNamespace(name=None)

    mdata = nitrishape_to_mesh_data(shape, data, name="Quad")

    assert mdata.name == "Quad"
    assert mdata.positions.shape == (4, 3)
    assert mdata.triangles.tolist() == [[0, 1, 2], [0, 2, 3]]
    assert mdata.normals is not None
    assert np.allclose(mdata.normals, [[0, 0, 1]] * 4)
    assert mdata.uv is not None
    assert mdata.uv.tolist() == [[0, 0], [1, 0], [1, 1], [0, 1]]
    assert mdata.vertex_colors is not None
    assert mdata.vertex_colors.shape == (4, 4)
    assert mdata.tangents is None
    assert mdata.bitangents is None


def test_nitrishape_to_mesh_data_without_normals_or_colors() -> None:
    data = SimpleNamespace(
        num_vertices=3,
        vertices=[_vec3(0, 0, 0), _vec3(1, 0, 0), _vec3(0, 1, 0)],
        triangles=[_tri(0, 1, 2)],
        has_normals=False,
        normals=[],
        tangents=[],
        bitangents=[],
        has_vertex_colors=False,
        vertex_colors=[],
        uv_sets=[],
    )
    mdata = nitrishape_to_mesh_data(SimpleNamespace(name=None), data, name="Tri")

    assert mdata.normals is None
    assert mdata.vertex_colors is None
    assert mdata.uv is None
    assert mdata.tangents is None
    assert mdata.bitangents is None


# ---- nitristrips_to_mesh_data --------------------------------------------


def test_nitristrips_to_mesh_data_decodes_strips() -> None:
    data = SimpleNamespace(
        num_vertices=4,
        vertices=[_vec3(0, 0, 0), _vec3(1, 0, 0), _vec3(1, 1, 0), _vec3(0, 1, 0)],
        strip_lengths=[4],
        points=[[0, 1, 2, 3]],
        has_normals=False,
        normals=[],
        tangents=[],
        bitangents=[],
        has_vertex_colors=False,
        vertex_colors=[],
        uv_sets=[[_uv(0, 0), _uv(1, 0), _uv(1, 1), _uv(0, 1)]],
    )
    strips = SimpleNamespace(name=None)

    mdata = nitristrips_to_mesh_data(strips, data, name="Strip")

    assert mdata.name == "Strip"
    # Strip [0,1,2,3] -> (0,1,2), (1,3,2 — flipped winding)
    assert mdata.triangles.tolist() == [[0, 1, 2], [1, 3, 2]]
    assert mdata.positions.shape == (4, 3)
    assert mdata.uv is not None
    assert mdata.uv.shape == (4, 2)


def test_nitristrips_to_mesh_data_handles_empty_strip_lists() -> None:
    data = SimpleNamespace(
        num_vertices=0,
        vertices=[],
        strip_lengths=[],
        points=[],
        has_normals=False,
        normals=[],
        tangents=[],
        bitangents=[],
        has_vertex_colors=False,
        vertex_colors=[],
        uv_sets=[],
    )
    mdata = nitristrips_to_mesh_data(SimpleNamespace(name=None), data, name="Empty")

    assert mdata.triangles.shape == (0, 3)
    assert mdata.positions.shape == (0, 3)
