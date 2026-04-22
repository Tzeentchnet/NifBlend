"""Phase 6 step 22 — Oblivion-shaped NiTriStripsData round-trip.

Validates that the codegen jagged-array fix (``width="Strip Lengths"`` for
``NiTriStripsData.points``) survives a write → read cycle byte-faithfully.
The Oblivion (NIF 20.0.0.5, user_version 11) header is set up just enough
to satisfy the version guards inside :class:`NiTriStripsData`; the block is
serialised and parsed in isolation (no full :func:`write_nif` wrapper), so
the test stays focused on the codegen path that step 22 fixed.
"""

from __future__ import annotations

import io

import numpy as np

from nifblend.bridge.mesh_in import nitristrips_to_mesh_data
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import NiTriStripsData
from nifblend.format.generated.structs import NiBound, Vector3
from nifblend.format.versions import pack_version


def _oblivion_ctx() -> ReadContext:
    """Match Oblivion's on-disk header globals: 20.0.0.5 / user 11 / no BS hdr."""
    return ReadContext(version=pack_version(20, 0, 0, 5), user_version=11, bs_version=0)


def _build_strips_data() -> NiTriStripsData:
    data = NiTriStripsData()
    data.group_id = 0
    data.num_vertices = 4
    data.bs_max_vertices = 0
    data.keep_flags = 0
    data.compress_flags = 0
    data.has_vertices = True
    data.vertices = [
        Vector3(x=0.0, y=0.0, z=0.0),
        Vector3(x=1.0, y=0.0, z=0.0),
        Vector3(x=1.0, y=1.0, z=0.0),
        Vector3(x=0.0, y=1.0, z=0.0),
    ]
    # Disable normals / tangents / colours / UVs for a minimal payload.
    data.material_crc = 0
    data.has_normals = False
    data.normals = []
    data.tangents = []
    data.bitangents = []
    data.bounding_sphere = NiBound(center=Vector3(x=0.0, y=0.0, z=0.0), radius=1.0)
    data.has_vertex_colors = False
    data.vertex_colors = []
    data.uv_sets = []
    data.consistency_flags = 0
    data.additional_data = -1
    data.num_triangles = 2
    data.num_strips = 2
    data.strip_lengths = np.asarray([4, 3], dtype=np.uint16)
    data.has_points = True
    data.points = [
        np.asarray([0, 1, 2, 3], dtype=np.uint16),
        np.asarray([1, 2, 3], dtype=np.uint16),
    ]
    return data


def test_nitristripsdata_roundtrip_preserves_jagged_points() -> None:
    ctx = _oblivion_ctx()
    src = _build_strips_data()

    sink = io.BytesIO()
    src.write(sink, ctx)

    rt = NiTriStripsData.read(io.BytesIO(sink.getvalue()), ctx)

    assert rt.num_vertices == src.num_vertices
    assert rt.num_strips == src.num_strips
    assert list(rt.strip_lengths) == [4, 3]
    # The jagged ``points`` field is the codegen change exercised by this
    # test: each row must carry exactly ``strip_lengths[i]`` u16s, not the
    # pre-fix flat ``num_strips`` u16s.
    assert len(rt.points) == 2
    assert list(rt.points[0]) == [0, 1, 2, 3]
    assert list(rt.points[1]) == [1, 2, 3]


def test_nitristrips_bridge_decodes_roundtripped_block() -> None:
    """End-to-end check: build → write → read → decode strips through the bridge."""
    ctx = _oblivion_ctx()
    src = _build_strips_data()
    sink = io.BytesIO()
    src.write(sink, ctx)
    rt = NiTriStripsData.read(io.BytesIO(sink.getvalue()), ctx)

    from types import SimpleNamespace

    mdata = nitristrips_to_mesh_data(SimpleNamespace(name=None), rt, name="Quad")

    # Two strips: [0,1,2,3] -> (0,1,2), (1,3,2 — flipped); [1,2,3] -> (1,2,3).
    assert mdata.triangles.tolist() == [[0, 1, 2], [1, 3, 2], [1, 2, 3]]
    assert mdata.positions.shape == (4, 3)
