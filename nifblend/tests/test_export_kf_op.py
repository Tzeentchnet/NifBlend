"""Phase 10f -- ``ops/export_kf.py`` operator tests.

Mirrors :mod:`nifblend.tests.test_import_kf_op`'s structure: exercises the
operator's target/preset/action-collection resolution helpers plus the
end-to-end ``execute`` path against a fake armature + action, using a real
:func:`~nifblend.io.block_table.write_nif` round-trip so the written file is
verified with the same reader the rest of the suite uses.

Until this test module landed, ``NIFBLEND_OT_export_kf`` had zero dedicated
coverage even though the operator itself was fully implemented (see
docs/REVIEW_2026-07.md finding 3).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.io.block_table import read_nif
from nifblend.io.kf import is_kf_file, kf_root_sequences
from nifblend.ops import export_kf as export_kf_mod
from nifblend.ops.export_kf import VERSION_PRESETS, NIFBLEND_OT_export_kf

# ---- fakes -----------------------------------------------------------------


class _FakeAction:
    def __init__(self, name: str, fcurves: list[Any] | None = None) -> None:
        self.name = name
        self.fcurves = fcurves or []
        self.frame_range = (0.0, 1.0)


class _FakeAnimData:
    def __init__(self, action: Any | None = None) -> None:
        self.action = action


class _FakePoseBones:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: SimpleNamespace(rotation_mode="QUATERNION") for n in names}

    def __iter__(self):
        return iter(SimpleNamespace(name=n) for n in self._items)

    def get(self, name: str) -> Any | None:
        return self._items.get(name)


class _FakeArmatureObject:
    def __init__(
        self,
        name: str,
        *,
        pose_bones: list[str] | None = None,
        action: Any | None = None,
        game_profile: str | None = None,
    ) -> None:
        self.name = name
        self.type = "ARMATURE"
        self.pose = SimpleNamespace(bones=_FakePoseBones(pose_bones or []))
        self.animation_data = _FakeAnimData(action) if action is not None else None
        if game_profile is not None:
            self.nifblend = SimpleNamespace(game_profile=game_profile)


class _FakeScene:
    def __init__(self, objs: list[Any]) -> None:
        self.objects = _FakeObjectStore(objs)


class _FakeObjectStore:
    def __init__(self, objs: list[Any]) -> None:
        self._items = {o.name: o for o in objs}

    def get(self, name: str) -> Any:
        return self._items.get(name)

    def __iter__(self):
        return iter(self._items.values())


def _fake_context(armature: Any | None, *, active: Any | None = None) -> SimpleNamespace:
    objs: list[Any] = [armature] if armature is not None else []
    return SimpleNamespace(
        scene=_FakeScene(objs),
        active_object=active if active is not None else armature,
    )


def _op(**overrides: Any) -> NIFBLEND_OT_export_kf:
    op = NIFBLEND_OT_export_kf()
    op.target_armature = overrides.pop("target_armature", "")
    op.actions_mode = overrides.pop("actions_mode", "ACTIVE")
    op.version_preset = overrides.pop("version_preset", "AUTO")
    op.fps = overrides.pop("fps", 30.0)
    for k, v in overrides.items():
        setattr(op, k, v)
    return op


# ---- _resolve_target (mirrors import_kf's picker semantics) ---------------


def test_resolve_target_uses_explicit_pick() -> None:
    op = _op()
    rig_a = _FakeArmatureObject("RigA")
    rig_b = _FakeArmatureObject("RigB")
    ctx = SimpleNamespace(scene=_FakeScene([rig_a, rig_b]), active_object=rig_a)
    op.target_armature = "RigB"
    assert op._resolve_target(ctx) is rig_b


def test_resolve_target_falls_back_to_active_object() -> None:
    op = _op()
    rig = _FakeArmatureObject("Rig")
    ctx = _fake_context(rig)
    assert op._resolve_target(ctx) is rig


def test_resolve_target_returns_none_when_active_is_not_armature() -> None:
    op = _op()
    mesh = SimpleNamespace(name="Mesh", type="MESH")
    ctx = SimpleNamespace(scene=_FakeScene([mesh]), active_object=mesh)
    assert op._resolve_target(ctx) is None


# ---- _resolve_preset --------------------------------------------------------


def test_resolve_preset_explicit_override_ignores_profile() -> None:
    op = _op(version_preset="FALLOUT_4")
    rig = _FakeArmatureObject("Rig", game_profile="skyrim_se")
    assert op._resolve_preset(rig) == "FALLOUT_4"


def test_resolve_preset_auto_maps_stamped_profile() -> None:
    op = _op(version_preset="AUTO")
    rig = _FakeArmatureObject("Rig", game_profile="skyrim_se")
    assert op._resolve_preset(rig) == "SKYRIM_SE"


def test_resolve_preset_auto_returns_none_for_unstamped_profile() -> None:
    op = _op(version_preset="AUTO")
    rig = _FakeArmatureObject("Rig")  # no .nifblend -> UNKNOWN profile
    assert op._resolve_preset(rig) is None


def test_version_presets_cover_every_auto_mapped_profile() -> None:
    for preset_key in ("SKYRIM_SE", "SKYRIM_LE", "FALLOUT_4"):
        assert preset_key in VERSION_PRESETS


# ---- _collect_actions -------------------------------------------------------


def test_collect_actions_active_mode_returns_assigned_action() -> None:
    op = _op(actions_mode="ACTIVE")
    action = _FakeAction("Idle")
    rig = _FakeArmatureObject("Rig", action=action)
    assert op._collect_actions(rig) == [action]


def test_collect_actions_active_mode_empty_when_unassigned() -> None:
    op = _op(actions_mode="ACTIVE")
    rig = _FakeArmatureObject("Rig")
    assert op._collect_actions(rig) == []


def test_collect_actions_all_from_armature_filters_by_bone_fcurves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    op = _op(actions_mode="ALL_FROM_ARMATURE")
    matching = _FakeAction(
        "Walk", fcurves=[SimpleNamespace(data_path='pose.bones["Root"].location')]
    )
    other_rig_action = _FakeAction(
        "OtherRig", fcurves=[SimpleNamespace(data_path='pose.bones["Ghost"].location')]
    )
    active = _FakeAction("Idle")
    rig = _FakeArmatureObject("Rig", pose_bones=["Root"], action=active)

    import bpy

    monkeypatch.setattr(
        bpy,
        "data",
        SimpleNamespace(actions=[matching, other_rig_action, active]),
        raising=False,
    )

    out = op._collect_actions(rig)
    assert active in out  # active action always included, even without a match
    assert matching in out
    assert other_rig_action not in out


# ---- end-to-end execute -----------------------------------------------------


def test_execute_rejects_missing_target() -> None:
    op = _op()
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]
    ctx = SimpleNamespace(scene=_FakeScene([]), active_object=None)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("Select an armature" in msg for _, msg in reports)


def test_execute_rejects_unresolvable_preset() -> None:
    op = _op(version_preset="AUTO")
    rig = _FakeArmatureObject("Rig")  # UNKNOWN profile, no override
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]
    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("version preset" in msg for _, msg in reports)


def test_execute_rejects_no_actions() -> None:
    op = _op(version_preset="SKYRIM_SE")
    rig = _FakeArmatureObject("Rig")  # no action assigned
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]
    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("No Actions to export" in msg for _, msg in reports)


def _seq_name(table: Any, seq: Any) -> str:
    """Resolve a written NiControllerSequence's name via the string table."""
    idx = int(seq.name.index)
    s = table.header.strings[idx]
    return bytes(s.value).decode("latin-1")


def test_execute_happy_path_writes_readable_kf(tmp_path: Path) -> None:
    action = _FakeAction("Idle")
    rig = _FakeArmatureObject("Rig", pose_bones=["Root"], action=action)
    out_path = tmp_path / "idle.kf"

    op = _op(version_preset="SKYRIM_SE")
    op.filepath = str(out_path)
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]

    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"FINISHED"}
    assert out_path.exists()
    assert any("Exported" in msg for _, msg in reports)

    with out_path.open("rb") as fh:
        table = read_nif(fh)
    assert is_kf_file(table)
    sequences = kf_root_sequences(table)
    assert len(sequences) == 1
    assert _seq_name(table, sequences[0]) == "Idle"


def test_execute_all_from_armature_writes_multiple_sequences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = _FakeAction("Idle")
    walk = _FakeAction("Walk", fcurves=[SimpleNamespace(data_path='pose.bones["Root"].location')])
    rig = _FakeArmatureObject("Rig", pose_bones=["Root"], action=active)
    out_path = tmp_path / "all.kf"

    op = _op(version_preset="SKYRIM_SE", actions_mode="ALL_FROM_ARMATURE")
    op.filepath = str(out_path)
    op.report = lambda *_a, **_kw: None  # type: ignore[assignment]

    monkeypatch.setattr(
        export_kf_mod.bpy,
        "data",
        SimpleNamespace(actions=[active, walk]),
        raising=False,
    )
    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"FINISHED"}

    with out_path.open("rb") as fh:
        table = read_nif(fh)
    names = {_seq_name(table, seq) for seq in kf_root_sequences(table)}
    assert names == {"Idle", "Walk"}


# ---- _armature_enum_items ----------------------------------------------------


def test_armature_enum_items_returns_sentinel_when_empty() -> None:
    ctx = SimpleNamespace(scene=_FakeScene([]))
    items = export_kf_mod._armature_enum_items(None, ctx)
    assert items == [("", "<no armature in scene>", "Add an armature first")]


def test_armature_enum_items_lists_armature_objects_only() -> None:
    rig = _FakeArmatureObject("Rig")
    mesh = SimpleNamespace(name="Mesh", type="MESH")
    ctx = SimpleNamespace(scene=_FakeScene([rig, mesh]))
    items = export_kf_mod._armature_enum_items(None, ctx)
    assert [i[0] for i in items] == ["Rig"]
