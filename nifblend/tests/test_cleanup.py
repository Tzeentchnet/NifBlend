"""Tests for nifblend.bridge.cleanup pure helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nifblend.bridge.cleanup import (
    DEFAULT_COLLISION_PATTERNS,
    group_objects_by_material_base,
    matches_collision_pattern,
    material_base_name,
    parse_pattern_list,
)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Stone", "Stone"),
        ("Stone.001", "Stone"),
        ("Stone.045", "Stone"),
        ("Stone.foo", "Stone.foo"),
        ("", ""),
        ("Material.123.001", "Material.123"),  # only the trailing .NNN is stripped
    ],
)
def test_material_base_name(name, expected):
    assert material_base_name(name) == expected


@pytest.mark.parametrize(
    "name,expected",
    [
        ("box", True),
        ("Box", True),
        ("box.001", True),
        ("box1", True),
        ("box_top", True),
        ("boxer", False),
        ("convex", True),
        ("convex_hull_42", True),
        ("Hull.001", True),
        ("hull", True),
        ("rock", False),
        ("", False),
    ],
)
def test_matches_collision_pattern(name, expected):
    assert matches_collision_pattern(name, DEFAULT_COLLISION_PATTERNS) is expected


def test_matches_collision_pattern_custom():
    assert matches_collision_pattern("phantom", ("phantom",)) is True
    assert matches_collision_pattern("phantoms", ("phantom",)) is False


def test_parse_pattern_list():
    assert parse_pattern_list("box,convex,hull") == ("box", "convex", "hull")
    assert parse_pattern_list("box, convex,, hull,") == ("box", "convex", "hull")
    assert parse_pattern_list("") == ()
    assert parse_pattern_list("box,Box,BOX") == ("box",)  # dedup case-insensitive


def test_group_objects_by_material_base():
    def mk(name, mat_name):
        return SimpleNamespace(
            type="MESH",
            data=SimpleNamespace(materials=[SimpleNamespace(name=mat_name)]),
            name=name,
        )

    objs = [mk("a", "Stone"), mk("b", "Stone.001"), mk("c", "Wood")]
    groups = group_objects_by_material_base(objs)
    assert set(groups.keys()) == {"Stone", "Wood"}
    assert len(groups["Stone"]) == 2
    assert len(groups["Wood"]) == 1


def test_group_objects_by_material_base_skips_non_mesh_and_empty():
    objs = [
        SimpleNamespace(type="EMPTY", data=None, name="a"),
        SimpleNamespace(type="MESH", data=SimpleNamespace(materials=[]), name="b"),
        SimpleNamespace(
            type="MESH",
            data=SimpleNamespace(materials=[None]),
            name="c",
        ),
    ]
    assert group_objects_by_material_base(objs) == {}
