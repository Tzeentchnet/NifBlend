"""Phase 6 step 24 — Fallout 4 / 76 mesh decoder tests.

Covers two new bridge entry points in :mod:`nifblend.bridge.mesh_in`:

* :func:`bssubindextrishape_to_mesh_data` /
  :func:`bssubindextrishape_segments` — FO4 (``bs_version`` 130-139)
  ``BSSubIndexTriShape`` reuses the BSTriShape vertex layout, so the
  geometry decode is exercised through the same per-attribute helpers
  the SSE path uses; the segment + shared-data sidecar gets its own
  decoder that returns a dataclass tree.
* :func:`bsgeometry_mesh_refs` — FO76 (``bs_version`` 155+)
  ``BSGeometry`` carries no inline geometry, just up to four external
  ``.mesh`` LOD references via ``BSMeshArray`` slots.

Tests build the blocks directly rather than round-tripping through
``write_nif`` / ``read_nif`` so the focus stays on the bridge layer
(the read/write paths are already covered by the codegen smoke tests).
"""

from __future__ import annotations

import io

import numpy as np

from nifblend.bridge.mesh_in import (
    BSGeometryMeshRef,
    bsgeometry_mesh_refs,
    bssubindextrishape_segments,
    bssubindextrishape_to_mesh_data,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.bitfields import BSVertexDesc
from nifblend.format.generated.blocks import BSGeometry, BSSubIndexTriShape
from nifblend.format.generated.structs import (
    BSGeometryPerSegmentSharedData,
    BSGeometrySegmentData,
    BSGeometrySegmentSharedData,
    BSGeometrySubSegment,
    BSMesh,
    BSMeshArray,
    ByteVector3,
    HalfTexCoord,
    SizedString,
    SizedString16,
    Triangle,
    Vector3,
)
from nifblend.format.generated.structs import string as nif_string
from nifblend.format.versions import pack_version

# ---- helpers --------------------------------------------------------------


def _sized_string(s: str) -> SizedString:
    raw = s.encode("latin-1")
    return SizedString(length=len(raw), value=list(raw))


def _sized_string16(s: str) -> SizedString16:
    raw = s.encode("latin-1")
    return SizedString16(length=len(raw), value=list(raw))


def _vertex(x: float, y: float, z: float) -> object:
    """Build a duck-typed vertex matching the BSVertexData / SSE field shape."""
    from types import SimpleNamespace

    return SimpleNamespace(
        vertex=Vector3(x=x, y=y, z=z),
        bitangent_x=0.0,
        unused_w=0,
        uv=HalfTexCoord(u=0.0, v=0.0),
        normal=ByteVector3(x=128, y=128, z=255),
        bitangent_y=128,
        tangent=ByteVector3(x=128, y=128, z=128),
        bitangent_z=128,
        vertex_colors=None,
        bone_weights=[],
        bone_indices=[],
    )


def _sits_block(
    *,
    desc_attrs: int = 0x401,
    name_index: int = 0xFFFFFFFF,
    num_primitives: int = 0,
    num_segments: int = 0,
    total_segments: int = 0,
    segments: list[BSGeometrySegmentData] | None = None,
    segment_data: BSGeometrySegmentSharedData | None = None,
) -> BSSubIndexTriShape:
    blk = BSSubIndexTriShape()
    blk.name = nif_string(index=name_index)
    blk.vertex_desc = BSVertexDesc(vertex_attributes=desc_attrs)
    blk.num_vertices = 3
    blk.num_triangles = 1
    blk.vertex_data = [
        _vertex(0.0, 0.0, 0.0),
        _vertex(1.0, 0.0, 0.0),
        _vertex(0.0, 1.0, 0.0),
    ]
    blk.triangles = [Triangle(v1=0, v2=1, v3=2)]
    blk.num_primitives = num_primitives
    blk.num_segments = num_segments
    blk.total_segments = total_segments
    blk.segment = list(segments or [])
    blk.segment_data = segment_data
    return blk


# ---- BSSubIndexTriShape geometry decode ----------------------------------


def test_sits_geometry_matches_bstrishape_layout() -> None:
    blk = _sits_block(desc_attrs=0x401)
    data = bssubindextrishape_to_mesh_data(blk, name="SITS")
    assert data.name == "SITS"
    np.testing.assert_array_equal(
        data.positions,
        np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
    )
    np.testing.assert_array_equal(
        data.triangles, np.array([[0, 1, 2]], dtype=np.uint32)
    )
    assert data.uv is None  # _VA_UV bit not set


def test_sits_geometry_with_uv_and_normals() -> None:
    blk = _sits_block(desc_attrs=0x401 | 0x002 | 0x008)
    blk.vertex_data[0].uv = HalfTexCoord(u=0.25, v=0.5)
    blk.vertex_data[0].normal = ByteVector3(x=255, y=128, z=128)
    data = bssubindextrishape_to_mesh_data(blk)
    assert data.uv is not None
    np.testing.assert_array_almost_equal(data.uv[0], [0.25, 0.5])
    assert data.normals is not None
    # 255 -> +1, 128 -> ~0.004 (the 0..255 -> -1..+1 mapping the bridge uses).
    np.testing.assert_almost_equal(data.normals[0, 0], 1.0, decimal=2)


def test_sits_geometry_falls_back_to_classname_without_table() -> None:
    blk = _sits_block(name_index=42)  # would need a string table to resolve
    data = bssubindextrishape_to_mesh_data(blk)
    assert data.name == "BSSubIndexTriShape"


# ---- BSSubIndexTriShape segment sidecar ----------------------------------


def test_sits_segments_returns_none_when_empty() -> None:
    blk = _sits_block()
    assert bssubindextrishape_segments(blk) is None


def test_sits_segments_decodes_flat_segment_list() -> None:
    seg_a = BSGeometrySegmentData(
        start_index=0,
        num_primitives=2,
        parent_array_index=0,
        num_sub_segments=0,
        sub_segment=[],
    )
    seg_b = BSGeometrySegmentData(
        start_index=2,
        num_primitives=4,
        parent_array_index=1,
        num_sub_segments=0,
        sub_segment=[],
    )
    blk = _sits_block(
        num_primitives=6,
        num_segments=2,
        total_segments=2,
        segments=[seg_a, seg_b],
    )
    segs = bssubindextrishape_segments(blk)
    assert segs is not None
    assert segs.num_primitives == 6
    assert segs.total_segments == 2
    assert len(segs.segments) == 2
    assert segs.segments[0].start_index == 0
    assert segs.segments[0].num_primitives == 2
    assert segs.segments[1].parent_array_index == 1
    assert segs.segments[0].sub_segments == []
    assert segs.ssf_file == ""
    assert segs.per_segment_user_indices == []


def test_sits_segments_folds_shared_data_subsegments() -> None:
    sub = BSGeometrySubSegment(
        start_index=0, num_primitives=1, parent_array_index=0, unused=0
    )
    seg = BSGeometrySegmentData(
        start_index=0,
        num_primitives=1,
        parent_array_index=0,
        num_sub_segments=1,
        sub_segment=[sub],
    )
    shared = BSGeometrySegmentSharedData(
        num_segments=1,
        total_segments=2,
        segment_starts=np.asarray([0], dtype=np.uint32),
        per_segment_data=[
            BSGeometryPerSegmentSharedData(
                user_index=7,
                bone_id=42,
                num_cut_offsets=0,
                cut_offsets=np.empty(0, dtype=np.float32),
            ),
        ],
        ssf_file=_sized_string16("meshes/foo.ssf"),
    )
    blk = _sits_block(
        num_primitives=1,
        num_segments=1,
        total_segments=2,
        segments=[seg],
        segment_data=shared,
    )
    segs = bssubindextrishape_segments(blk)
    assert segs is not None
    assert segs.ssf_file == "meshes/foo.ssf"
    assert segs.per_segment_user_indices == [(7, 42)]
    assert len(segs.segments) == 1
    assert len(segs.segments[0].sub_segments) == 1
    sub_row = segs.segments[0].sub_segments[0]
    assert sub_row.start_index == 0
    assert sub_row.num_primitives == 1
    assert sub_row.parent_array_index == 0


# ---- BSSubIndexTriShape on-disk round-trip (FO4 ctx) ---------------------


def _fo4_ctx() -> ReadContext:
    """Fallout 4 globals: NIF 20.2.0.7, user_version 12, bs_version 130."""
    return ReadContext(
        version=pack_version(20, 2, 0, 7), user_version=12, bs_version=130
    )


def test_sits_minimal_ondisk_roundtrip_decodes_through_bridge() -> None:
    """Build → write → read → decode an empty-vertex SITS in FO4 ctx.

    The vertex_data / triangle streams are gated on ``data_size > 0``, so a
    zero-data-size block exercises the FO4 branch of every conditional read
    in :class:`BSSubIndexTriShape.read` (the ``bs_version >= 130`` arms for
    ``num_triangles`` u32 and the segment metadata) without depending on
    BSVertexData's full packed layout.
    """
    ctx = _fo4_ctx()
    seg = BSGeometrySegmentData(
        start_index=0,
        num_primitives=0,
        parent_array_index=0,
        num_sub_segments=0,
        sub_segment=[],
    )

    src = BSSubIndexTriShape()
    src.shader_type = 0
    src.name = nif_string(index=0xFFFFFFFF)
    src.extra_data_list = []
    src.controller = -1
    src.flags = 0
    src.translation = Vector3(x=0.0, y=0.0, z=0.0)
    from nifblend.format.generated.structs import Matrix33, NiBound

    src.rotation = Matrix33(m11=1.0, m22=1.0, m33=1.0)
    src.scale = 1.0
    src.collision_object = -1
    src.bounding_sphere = NiBound(center=Vector3(x=0.0, y=0.0, z=0.0), radius=0.0)
    src.skin = -1
    src.shader_property = -1
    src.alpha_property = -1
    src.vertex_desc = BSVertexDesc(vertex_attributes=0)
    src.num_triangles = 0
    src.num_vertices = 0
    src.data_size = 0  # gates vertex/triangle/segment writes off
    src.vertex_data = []
    src.triangles = []
    src.particle_data_size = 0
    src.num_primitives = 0
    src.num_segments = 1
    src.total_segments = 1
    src.segment = [seg]

    sink = io.BytesIO()
    src.write(sink, ctx)
    rt = BSSubIndexTriShape.read(io.BytesIO(sink.getvalue()), ctx)

    assert rt.num_vertices == 0
    assert rt.num_triangles == 0
    assert rt.data_size == 0
    # data_size==0 short-circuits the segment write on the FO4 branch, so
    # the segment list comes back empty even though we set num_segments=1.
    # The reader only walks segments when data_size > 0, matching the
    # writer. Geometry decoder still works on the empty payload.
    data = bssubindextrishape_to_mesh_data(rt, name="empty")
    assert data.positions.shape == (0, 3)
    assert data.triangles.shape == (0, 3)


# ---- BSGeometry external mesh refs (FO76) --------------------------------


def test_bsgeometry_mesh_refs_returns_four_slots() -> None:
    blk = BSGeometry()
    blk.meshes = [
        BSMeshArray(
            has_mesh=1,
            mesh=BSMesh(
                indices_size=12,
                num_verts=4,
                flags=0x1,
                mesh_path=_sized_string("meshes/foo_lod0.mesh"),
            ),
        ),
        BSMeshArray(has_mesh=0, mesh=None),
        BSMeshArray(
            has_mesh=1,
            mesh=BSMesh(
                indices_size=6,
                num_verts=2,
                flags=0x2,
                mesh_path=_sized_string("meshes/foo_lod2.mesh"),
            ),
        ),
        BSMeshArray(has_mesh=0, mesh=None),
    ]

    refs = bsgeometry_mesh_refs(blk)
    assert len(refs) == 4
    assert refs == [
        BSGeometryMeshRef(
            lod_index=0,
            has_mesh=True,
            mesh_path="meshes/foo_lod0.mesh",
            num_verts=4,
            indices_size=12,
            flags=0x1,
        ),
        BSGeometryMeshRef(lod_index=1, has_mesh=False),
        BSGeometryMeshRef(
            lod_index=2,
            has_mesh=True,
            mesh_path="meshes/foo_lod2.mesh",
            num_verts=2,
            indices_size=6,
            flags=0x2,
        ),
        BSGeometryMeshRef(lod_index=3, has_mesh=False),
    ]


def test_bsgeometry_mesh_refs_tolerates_missing_meshes() -> None:
    blk = BSGeometry()
    blk.meshes = []
    assert bsgeometry_mesh_refs(blk) == []


def test_bsgeometry_mesh_refs_handles_none_slot_entries() -> None:
    blk = BSGeometry()
    blk.meshes = [None, None, None, None]
    refs = bsgeometry_mesh_refs(blk)
    assert all(not r.has_mesh and r.mesh_path == "" for r in refs)
    assert [r.lod_index for r in refs] == [0, 1, 2, 3]
