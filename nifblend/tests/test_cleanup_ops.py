"""Phase 8j: cleanup operator scope-handling tests.

Verifies each :mod:`nifblend.ops.cleanup` operator honours its
``'SELECTED' | 'SCENE'`` scope (default ``SELECTED`` -- NifCity always
swept the whole scene, which the README calls out as the explicit
footgun fix).
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import bpy
import pytest

from nifblend.ops.cleanup import (
    NIFBLEND_OT_clear_extra_materials,
    NIFBLEND_OT_combine_by_material,
    NIFBLEND_OT_delete_collision_shells,
    NIFBLEND_OT_delete_empties,
)

# ---- fakes ---------------------------------------------------------------


class _FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeMaterialList(list):
    def append(self, item: Any) -> None:  # type: ignore[override]
        super().append(item)

    def clear(self) -> None:  # type: ignore[override]
        del self[:]


class _FakeMesh:
    def __init__(self, materials: list[_FakeMaterial] | None = None) -> None:
        self.materials = _FakeMaterialList(materials or [])


class _FakeObject:
    def __init__(
        self,
        name: str,
        otype: str = "MESH",
        *,
        data: Any = None,
    ) -> None:
        self.name = name
        self.type = otype
        self.data = data


@contextmanager
def _noop_override(**_kw: Any):
    yield


def _ctx(selected: list[Any], scene_objects: list[Any] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        selected_objects=list(selected),
        scene=SimpleNamespace(objects=list(scene_objects or selected)),
        temp_override=_noop_override,
    )


@pytest.fixture
def fake_bpy_data(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Replace ``bpy.data.objects`` with a recorder, return the deletion log."""
    removed: list[Any] = []

    def _remove(obj: Any, do_unlink: bool = True) -> None:
        removed.append(obj)

    monkeypatch.setattr(
        bpy,
        "data",
        SimpleNamespace(objects=SimpleNamespace(remove=_remove)),
        raising=False,
    )
    return removed


# ---- delete_empties ------------------------------------------------------


def test_delete_empties_selected_scope_only_touches_selection(
    fake_bpy_data: list[Any],
) -> None:
    sel_empty = _FakeObject("EmptyA", "EMPTY")
    sel_mesh = _FakeObject("MeshA", "MESH")
    other_empty = _FakeObject("EmptyB", "EMPTY")
    ctx = _ctx(
        selected=[sel_empty, sel_mesh],
        scene_objects=[sel_empty, sel_mesh, other_empty],
    )

    op = NIFBLEND_OT_delete_empties()
    op.scope = "SELECTED"
    op.bake_children_transforms = False
    op.report = lambda *_a, **_kw: None
    result = op.execute(ctx)

    assert result == {"FINISHED"}
    assert fake_bpy_data == [sel_empty]


def test_delete_empties_scene_scope_walks_every_object(
    fake_bpy_data: list[Any],
) -> None:
    sel_empty = _FakeObject("EmptyA", "EMPTY")
    other_empty = _FakeObject("EmptyB", "EMPTY")
    mesh = _FakeObject("Mesh", "MESH")
    ctx = _ctx(selected=[sel_empty], scene_objects=[sel_empty, other_empty, mesh])

    op = NIFBLEND_OT_delete_empties()
    op.scope = "SCENE"
    op.bake_children_transforms = False
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert set(fake_bpy_data) == {sel_empty, other_empty}


def test_delete_empties_no_match_returns_cancelled(fake_bpy_data: list[Any]) -> None:
    mesh = _FakeObject("Mesh", "MESH")
    ctx = _ctx(selected=[mesh])
    op = NIFBLEND_OT_delete_empties()
    op.scope = "SELECTED"
    op.bake_children_transforms = False
    op.report = lambda *_a, **_kw: None
    assert op.execute(ctx) == {"CANCELLED"}
    assert fake_bpy_data == []


# ---- delete_collision_shells --------------------------------------------


def test_delete_collision_shells_selected_only(fake_bpy_data: list[Any]) -> None:
    box_sel = _FakeObject("box_door", "MESH")
    keep_sel = _FakeObject("Stone", "MESH")
    box_unsel = _FakeObject("box_other", "MESH")
    ctx = _ctx(
        selected=[box_sel, keep_sel],
        scene_objects=[box_sel, keep_sel, box_unsel],
    )

    op = NIFBLEND_OT_delete_collision_shells()
    op.scope = "SELECTED"
    op.patterns = "box,convex,hull"
    op.also_delete_armatures = False
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert fake_bpy_data == [box_sel]


def test_delete_collision_shells_scene_scope_includes_unselected(
    fake_bpy_data: list[Any],
) -> None:
    box_sel = _FakeObject("box_door", "MESH")
    box_unsel = _FakeObject("box_other", "MESH")
    keep = _FakeObject("Stone", "MESH")
    ctx = _ctx(
        selected=[box_sel],
        scene_objects=[box_sel, box_unsel, keep],
    )

    op = NIFBLEND_OT_delete_collision_shells()
    op.scope = "SCENE"
    op.patterns = "box,convex,hull"
    op.also_delete_armatures = False
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert set(fake_bpy_data) == {box_sel, box_unsel}


def test_delete_collision_shells_armature_toggle(fake_bpy_data: list[Any]) -> None:
    arma = _FakeObject("Skeleton", "ARMATURE")
    box = _FakeObject("box_door", "MESH")
    ctx = _ctx(selected=[arma, box])

    op = NIFBLEND_OT_delete_collision_shells()
    op.scope = "SELECTED"
    op.patterns = "box,convex,hull"
    op.also_delete_armatures = False
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)
    assert fake_bpy_data == [box]

    fake_bpy_data.clear()
    op.also_delete_armatures = True
    op.execute(ctx)
    assert set(fake_bpy_data) == {arma, box}


# ---- combine_by_material ------------------------------------------------


def test_combine_by_material_only_walks_selection(
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy_data: list[Any],
) -> None:
    join_calls: list[None] = []

    class _Ops:
        class object:  # noqa: N801 -- mimics bpy.ops layout
            @staticmethod
            def join() -> None:
                join_calls.append(None)

    monkeypatch.setattr(bpy, "ops", _Ops, raising=False)

    mat_stone = _FakeMaterial("Stone")
    a = _FakeObject("A", "MESH", data=_FakeMesh([mat_stone]))
    b = _FakeObject("B", "MESH", data=_FakeMesh([mat_stone]))
    other_group = _FakeObject(
        "C", "MESH", data=_FakeMesh([_FakeMaterial("Wood")])
    )
    unsel = _FakeObject("D", "MESH", data=_FakeMesh([mat_stone]))

    ctx = _ctx(selected=[a, b, other_group], scene_objects=[a, b, other_group, unsel])

    op = NIFBLEND_OT_combine_by_material()
    op.scope = "SELECTED"
    op.report = lambda *_a, **_kw: None
    result = op.execute(ctx)

    assert result == {"FINISHED"}
    # Only one group with 2 members → exactly one join call.
    assert len(join_calls) == 1


# ---- clear_extra_materials ---------------------------------------------


def test_clear_extra_materials_truncates_to_first_slot(
    fake_bpy_data: list[Any],
) -> None:
    mats = [_FakeMaterial("Stone.001"), _FakeMaterial("Wood"), _FakeMaterial("Iron")]
    obj = _FakeObject("A", "MESH", data=_FakeMesh(mats))
    other = _FakeObject("Empty", "EMPTY")
    ctx = _ctx(selected=[obj, other])

    op = NIFBLEND_OT_clear_extra_materials()
    op.scope = "SELECTED"
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert len(obj.data.materials) == 1
    assert obj.data.materials[0].name == "Stone"  # .001 dup-suffix stripped


def test_clear_extra_materials_scene_scope_picks_up_unselected(
    fake_bpy_data: list[Any],
) -> None:
    obj_sel = _FakeObject(
        "A", "MESH", data=_FakeMesh([_FakeMaterial("Stone.001"), _FakeMaterial("X")])
    )
    obj_unsel = _FakeObject(
        "B", "MESH", data=_FakeMesh([_FakeMaterial("Wood.045"), _FakeMaterial("Y")])
    )
    ctx = _ctx(selected=[obj_sel], scene_objects=[obj_sel, obj_unsel])

    op = NIFBLEND_OT_clear_extra_materials()
    op.scope = "SCENE"
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert [m.name for m in obj_sel.data.materials] == ["Stone"]
    assert [m.name for m in obj_unsel.data.materials] == ["Wood"]


def test_clear_extra_materials_no_targets_returns_cancelled(
    fake_bpy_data: list[Any],
) -> None:
    ctx = _ctx(selected=[_FakeObject("Empty", "EMPTY")])
    op = NIFBLEND_OT_clear_extra_materials()
    op.scope = "SELECTED"
    op.report = lambda *_a, **_kw: None
    assert op.execute(ctx) == {"CANCELLED"}
