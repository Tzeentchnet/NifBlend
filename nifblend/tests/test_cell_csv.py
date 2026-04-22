"""Tests for nifblend.bridge.cell_csv pure helpers."""

from __future__ import annotations

import math

import pytest

from nifblend.bridge.cell_csv import (
    CSV_HEADER_LINE,
    CellPlacement,
    bethesda_euler_to_blender,
    compute_origin_offset,
    parse_cell_csv,
    should_skip,
)


def test_parse_cell_csv_basic():
    text = (
        f"{CSV_HEADER_LINE}\n"
        "meshes/rock.nif,100,200,300,0,0,90,1.5\n"
        "meshes/tree.nif,400,500,600,45,0,0,\n"
    )
    rows = parse_cell_csv(text)
    assert len(rows) == 2
    assert rows[0] == CellPlacement(
        model_path="meshes/rock.nif",
        location=(100.0, 200.0, 300.0),
        rotation_deg=(0.0, 0.0, 90.0),
        scale=1.5,
    )
    assert rows[1].scale == 1.0  # empty scale → 1.0


def test_parse_cell_csv_tolerant():
    text = "\n# comment row\n,,,,,,,,\nmeshes/a.nif,bad,0,0,0,0,0,1\nmeshes/b.nif,1,2,3,0,0,0,1\n"
    rows = parse_cell_csv(text)
    assert len(rows) == 1
    assert rows[0].model_path == "meshes/b.nif"


def test_parse_cell_csv_too_few_fields():
    rows = parse_cell_csv("meshes/a.nif,1,2\n")
    assert rows == []


def test_compute_origin_offset_truncates():
    placements = [
        CellPlacement("a", (10.7, 20.7, 30.7), (0, 0, 0), 1.0),
        CellPlacement("b", (20.7, 30.7, 40.7), (0, 0, 0), 1.0),
    ]
    # average is (15.7, 25.7, 35.7); int-truncates to (15, 25, 35)
    assert compute_origin_offset(placements) == (15.0, 25.0, 35.0)


def test_compute_origin_offset_empty():
    assert compute_origin_offset([]) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize(
    "name,prefixes,expected",
    [
        ("meshes/marker.nif", ("marker",), True),
        ("meshes/marker_arrow.nif", ("marker",), True),
        ("meshes/markette.nif", ("marker",), False),  # NifCity false-positive avoided
        ("meshes/MARKER.nif", ("marker",), True),
        ("meshes/fxsmoke.nif", ("fx",), False),  # letter continuation
        ("meshes/fx_smoke.nif", ("fx",), True),
        ("meshes/fx.nif", ("fx",), True),
        ("", ("marker",), True),  # empty path → skip
        ("meshes/rock.nif", ("marker", "fx"), False),
    ],
)
def test_should_skip(name, prefixes, expected):
    assert should_skip(name, prefixes) is expected


def test_bethesda_euler_to_blender_zero():
    rx, ry, rz = bethesda_euler_to_blender(0, 0, 0)
    # 360 - 0 = 360 → 2π ≡ 0 mod 2π but the helper returns 2π verbatim.
    assert math.isclose(rx, 2 * math.pi)
    assert math.isclose(ry, 2 * math.pi)
    assert math.isclose(rz, 2 * math.pi)


def test_bethesda_euler_to_blender_90():
    rx, _ry, _rz = bethesda_euler_to_blender(90, 0, 0)
    # 360 - 90 = 270 → 3π/2
    assert math.isclose(rx, 3 * math.pi / 2)
