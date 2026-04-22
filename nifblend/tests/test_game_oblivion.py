"""Tests for nifblend.bridge.games.oblivion strip ↔ triangle conversion."""

from __future__ import annotations

from nifblend.bridge.games.oblivion import strips_to_triangles, triangles_to_strips


def test_empty_input():
    assert triangles_to_strips([]) == []
    assert strips_to_triangles([]) == []


def test_single_triangle_makes_one_strip():
    strips = triangles_to_strips([(0, 1, 2)])
    assert strips == [[0, 1, 2]]
    # decode recovers original
    assert strips_to_triangles(strips) == [(0, 1, 2)]


def test_quad_two_adjacent_triangles_makes_one_strip():
    # quad (0,1,2,3) → tri (0,1,2) + tri (2,1,3) shares edge (1,2)
    tris = [(0, 1, 2), (2, 1, 3)]
    strips = triangles_to_strips(tris)
    assert len(strips) == 1
    assert strips[0] == [0, 1, 2, 3]
    # decoder produces the strip's canonical winding; compare as triangle sets
    # under rotation equivalence.
    def canon(t):
        rotations = [(t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1])]
        return min(rotations)

    decoded = strips_to_triangles(strips)
    assert sorted(canon(t) for t in decoded) == sorted(canon(t) for t in tris)


def test_disjoint_triangles_make_separate_strips():
    tris = [(0, 1, 2), (10, 11, 12)]
    strips = triangles_to_strips(tris)
    assert len(strips) == 2


def test_degenerate_triangles_dropped():
    assert triangles_to_strips([(0, 0, 1), (5, 5, 5)]) == []


def test_round_trip_recovers_triangle_set():
    tris = [(0, 1, 2), (2, 1, 3), (3, 1, 4), (10, 11, 12)]
    strips = triangles_to_strips(tris)
    decoded = strips_to_triangles(strips)
    # set-equality via canonical rotation (smallest first)
    def canon(t):
        rotations = [(t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1])]
        return min(rotations)

    assert sorted(canon(t) for t in decoded) == sorted(canon(t) for t in tris)
