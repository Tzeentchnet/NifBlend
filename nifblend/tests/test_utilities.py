"""Tests for nifblend.bridge.utilities pure helpers."""

from __future__ import annotations

import math

import pytest

from nifblend.bridge.utilities import (
    BETHESDA_UNIT_TO_BLENDER,
    DEFAULT_MERGE_DISTANCE,
    fit_clip_distance,
    group_loops_by_vertex,
    group_polygons_by_material_slot,
    recenter_offset,
    scene_bounds_radius,
    suggest_merge_distance,
)


def test_recenter_offset_empty():
    assert recenter_offset([]) == (0.0, 0.0, 0.0)


def test_recenter_offset_average():
    pts = [(0.0, 0.0, 0.0), (10.0, 20.0, 30.0)]
    assert recenter_offset(pts) == (5.0, 10.0, 15.0)


def test_scene_bounds_radius():
    assert scene_bounds_radius([]) == 0.0
    assert math.isclose(scene_bounds_radius([(3.0, 4.0, 0.0)]), 5.0)


def test_fit_clip_distance_minimum():
    # tiny scene → clamps to minimum
    assert fit_clip_distance([(1.0, 1.0, 1.0)]) == 1000.0


def test_fit_clip_distance_padded():
    # 100k radius * 1.5 pad = 150k
    pts = [(100000.0, 0.0, 0.0)]
    assert math.isclose(fit_clip_distance(pts, pad_factor=1.5), 150000.0)


def test_bethesda_unit_constant():
    assert math.isclose(BETHESDA_UNIT_TO_BLENDER, 0.01428)


# ---------------------------------------------------------------------------
# Phase 8h: mesh-hygiene pure helpers.
# ---------------------------------------------------------------------------


def test_suggest_merge_distance_empty():
    assert suggest_merge_distance([]) == 1e-6


def test_suggest_merge_distance_clamps_to_minimum():
    # scene_radius of 1e-3 * fraction 1e-4 = 1e-7, below minimum 1e-6.
    got = suggest_merge_distance([(0.0, 0.0, 1e-3)])
    assert got == 1e-6


def test_suggest_merge_distance_clamps_to_maximum():
    # massive radius → fraction * radius exceeds maximum 1e-2.
    got = suggest_merge_distance([(0.0, 0.0, 1e9)])
    assert got == 1e-2


def test_suggest_merge_distance_with_triangles():
    # single triangle with edges of length 1; fraction 1e-4 → 1e-4.
    got = suggest_merge_distance(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        [(0, 1, 2)],
        fraction=1e-4,
    )
    assert math.isclose(got, 1e-4)


def test_suggest_merge_distance_picks_shortest_edge():
    # shortest edge is 0.01; fraction 1e-4 → 1e-6 (clamped to minimum).
    got = suggest_merge_distance(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.01, 0.0, 0.0)],
        [(0, 1, 2)],
        fraction=1e-3,
    )
    # shortest edge = 0.01; 0.01 * 1e-3 = 1e-5, above minimum.
    assert math.isclose(got, 1e-5)


def test_group_polygons_by_material_slot():
    # polys 0,2 slot 0; polys 1,3 slot 1.
    got = group_polygons_by_material_slot([0, 1, 0, 1])
    assert got == {0: [0, 2], 1: [1, 3]}


def test_group_polygons_by_material_slot_empty():
    assert group_polygons_by_material_slot([]) == {}


def test_group_loops_by_vertex():
    # Two loops per vertex for 2 verts.
    got = group_loops_by_vertex(
        loop_vertex_indices=[0, 0, 1, 1],
        loop_uvs=[(0.0, 0.0), (0.5, 0.5), (1.0, 0.0), (1.0, 1.0)],
    )
    assert got[0] == [(0, (0.0, 0.0)), (1, (0.5, 0.5))]
    assert got[1] == [(2, (1.0, 0.0)), (3, (1.0, 1.0))]


def test_group_loops_by_vertex_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        group_loops_by_vertex([0, 1], [(0.0, 0.0)])


def test_default_merge_distance_positive():
    assert DEFAULT_MERGE_DISTANCE > 0.0
    assert DEFAULT_MERGE_DISTANCE < 1.0
