"""Tests for Phase 8g Fallout helpers + mesh PropertyGroup (pure layer)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nifblend.bridge.games.fallout import (
    FO76_MESH_SLOT_COUNT,
    ExternalMeshLink,
    normalise_fo76_slots,
    promote_triangles_to_segments,
    validate_segment_coverage,
)
from nifblend.bridge.mesh_in import (
    BSGeometryMeshRef,
    MeshSegment,
    MeshSegments,
    MeshSubSegment,
)
from nifblend.bridge.mesh_props import (
    apply_fo76_slots_to_mesh,
    apply_segments_to_mesh,
    read_fo76_slots_from_mesh,
    read_segments_from_mesh,
)

# ---- promote_triangles_to_segments --------------------------------------


def test_promote_triangles_single_full_range_segment():
    seg = promote_triangles_to_segments(12)
    assert seg.num_primitives == 36
    assert seg.total_segments == 1
    assert len(seg.segments) == 1
    only = seg.segments[0]
    assert only.start_index == 0
    assert only.num_primitives == 36
    assert only.parent_array_index == 0xFFFFFFFF
    assert only.sub_segments == []
    assert seg.ssf_file == ""
    assert seg.per_segment_user_indices == []


def test_promote_triangles_zero():
    seg = promote_triangles_to_segments(0)
    assert seg.num_primitives == 0
    assert seg.segments[0].num_primitives == 0


def test_promote_triangles_negative_raises():
    with pytest.raises(ValueError):
        promote_triangles_to_segments(-1)


# ---- validate_segment_coverage ------------------------------------------


def test_validate_clean_coverage_empty():
    seg = promote_triangles_to_segments(10)
    assert validate_segment_coverage(seg) == []


def test_validate_detects_gap():
    seg = MeshSegments(
        num_primitives=60,
        total_segments=2,
        segments=[
            MeshSegment(start_index=0, num_primitives=30, parent_array_index=0xFFFFFFFF),
            # gap at 30..40
            MeshSegment(start_index=40, num_primitives=20, parent_array_index=0xFFFFFFFF),
        ],
    )
    warnings = validate_segment_coverage(seg)
    assert any("start_index 40" in w for w in warnings)
    assert any("50 != header 60" in w for w in warnings)


def test_validate_sub_segment_parent_out_of_range():
    seg = MeshSegments(
        num_primitives=30,
        total_segments=1,
        segments=[
            MeshSegment(
                start_index=0,
                num_primitives=30,
                parent_array_index=0xFFFFFFFF,
                sub_segments=[
                    MeshSubSegment(
                        start_index=0,
                        num_primitives=15,
                        parent_array_index=7,  # no such segment
                    )
                ],
            )
        ],
    )
    warnings = validate_segment_coverage(seg)
    assert any("parent_array_index 7" in w for w in warnings)


# ---- normalise_fo76_slots -----------------------------------------------


def test_normalise_fo76_slots_fills_empty_slots():
    out = normalise_fo76_slots(
        [ExternalMeshLink(lod_index=0, mesh_path="a.mesh", num_verts=10, indices_size=30)]
    )
    assert len(out) == FO76_MESH_SLOT_COUNT
    assert out[0].has_mesh is True
    assert out[0].mesh_path == "a.mesh"
    for i in range(1, 4):
        assert out[i].has_mesh is False
        assert out[i].mesh_path == ""
        assert out[i].lod_index == i


def test_normalise_fo76_slots_last_wins_on_duplicates():
    out = normalise_fo76_slots(
        [
            ExternalMeshLink(lod_index=1, mesh_path="first.mesh"),
            ExternalMeshLink(lod_index=1, mesh_path="second.mesh"),
        ]
    )
    assert out[1].mesh_path == "second.mesh"


def test_normalise_fo76_slots_drops_out_of_range():
    out = normalise_fo76_slots([ExternalMeshLink(lod_index=99, mesh_path="x.mesh")])
    assert all(s.has_mesh is False for s in out)


def test_normalise_fo76_slots_empty_path_is_unpopulated():
    out = normalise_fo76_slots([ExternalMeshLink(lod_index=0, mesh_path="")])
    assert out[0].has_mesh is False


# ---- mesh PropertyGroup round-trip (duck-typed) --------------------------


def _fake_mesh() -> SimpleNamespace:
    """A SimpleNamespace that apply_* helpers can use as a stand-in."""
    return SimpleNamespace()


def test_apply_and_read_segments_round_trip():
    original = promote_triangles_to_segments(8)
    mesh = _fake_mesh()
    apply_segments_to_mesh(mesh, original)
    restored = read_segments_from_mesh(mesh)
    assert restored is not None
    assert restored.num_primitives == original.num_primitives
    assert len(restored.segments) == len(original.segments)
    assert restored.segments[0].num_primitives == original.segments[0].num_primitives
    assert restored.segments[0].parent_array_index == 0xFFFFFFFF


def test_apply_segments_none_clears():
    mesh = _fake_mesh()
    apply_segments_to_mesh(mesh, promote_triangles_to_segments(4))
    apply_segments_to_mesh(mesh, None)
    assert read_segments_from_mesh(mesh) is None


def test_apply_and_read_segments_with_subsegments():
    original = MeshSegments(
        num_primitives=30,
        total_segments=1,
        segments=[
            MeshSegment(
                start_index=0,
                num_primitives=30,
                parent_array_index=0xFFFFFFFF,
                sub_segments=[
                    MeshSubSegment(
                        start_index=0, num_primitives=15, parent_array_index=0, unused=7
                    ),
                    MeshSubSegment(
                        start_index=15, num_primitives=15, parent_array_index=0
                    ),
                ],
            )
        ],
        ssf_file="foo.ssf",
    )
    mesh = _fake_mesh()
    apply_segments_to_mesh(mesh, original)
    restored = read_segments_from_mesh(mesh)
    assert restored is not None
    assert restored.ssf_file == "foo.ssf"
    assert len(restored.segments[0].sub_segments) == 2
    assert restored.segments[0].sub_segments[0].unused == 7


def test_apply_and_read_fo76_slots_only_populated():
    refs = normalise_fo76_slots(
        [
            ExternalMeshLink(
                lod_index=0,
                mesh_path="meshes/lod0.mesh",
                num_verts=100,
                indices_size=300,
                flags=5,
            ),
            ExternalMeshLink(lod_index=2, mesh_path="meshes/lod2.mesh"),
        ]
    )
    mesh = _fake_mesh()
    apply_fo76_slots_to_mesh(mesh, refs)
    links = read_fo76_slots_from_mesh(mesh)
    assert len(links) == 2
    assert {link.lod_index for link in links} == {0, 2}
    lod0 = next(link for link in links if link.lod_index == 0)
    assert lod0.mesh_path == "meshes/lod0.mesh"
    assert lod0.num_verts == 100
    assert lod0.indices_size == 300
    assert lod0.flags == 5


def test_read_fo76_slots_empty_when_no_props():
    assert read_fo76_slots_from_mesh(SimpleNamespace()) == []


def test_apply_fo76_slots_empty_has_mesh_preserves_lod_count():
    refs = [
        BSGeometryMeshRef(lod_index=i, has_mesh=False) for i in range(FO76_MESH_SLOT_COUNT)
    ]
    mesh = _fake_mesh()
    apply_fo76_slots_to_mesh(mesh, refs)
    assert read_fo76_slots_from_mesh(mesh) == []
