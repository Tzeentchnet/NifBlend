"""Phase 5 step 21 -- ``ops/import_kf.py`` operator tests.

Exercises the operator's resolution / retargeting helpers and the
end-to-end ``execute`` path against a synthesised in-memory KF (an
empty :class:`NiControllerSequence` rooted in an SSE-shaped header --
matches the fixture style used by ``test_kf_io.py``).

The operator subclasses ``bpy.types.Operator`` (a bare ``type`` in the
conftest stub), so we instantiate it directly and stamp the
``filepath`` / ``rotation_mode`` / ``target_armature`` attributes the
real ``bpy`` would have populated through the file dialog.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import NiControllerSequence
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
)
from nifblend.format.generated.structs import string as nif_string
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif
from nifblend.ops import import_kf as import_kf_mod
from nifblend.ops.import_kf import NIFBLEND_OT_import_kf

# ---- helpers --------------------------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_table_with_sequence() -> BlockTable:
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    seq = NiControllerSequence(
        name=nif_string(index=0xFFFFFFFF),
        num_controlled_blocks=0,
        array_grow_by=0,
        controlled_blocks=[],
        weight=1.0,
        text_keys=-1,
        cycle_type=0,
        frequency=1.0,
        start_time=0.0,
        stop_time=0.0,
        manager=-1,
        accum_root_name=nif_string(index=0xFFFFFFFF),
        accum_flags=0,
        num_anim_note_arrays=0,
        anim_note_arrays=[],
    )
    return BlockTable(
        header=h,
        blocks=[seq],
        footer=Footer(num_roots=1, roots=[0]),
        ctx=ctx,
    )


def _write_kf_to_disk(table: BlockTable) -> str:
    """Serialise ``table`` to a tempfile path that the operator can open."""
    sink = io.BytesIO()
    write_nif(sink, table)
    fh = tempfile.NamedTemporaryFile(suffix=".kf", delete=False)
    try:
        fh.write(sink.getvalue())
    finally:
        fh.close()
    return fh.name


def _write_nif_only_table_to_disk() -> str:
    """A non-KF file (footer roots are not NiControllerSequence) for negative path."""
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    table = BlockTable(header=h, blocks=[], footer=Footer(), ctx=ctx)
    sink = io.BytesIO()
    write_nif(sink, table)
    fh = tempfile.NamedTemporaryFile(suffix=".kf", delete=False)
    try:
        fh.write(sink.getvalue())
    finally:
        fh.close()
    return fh.name


# ---- fakes ---------------------------------------------------------------


class _FakePoseBone:
    def __init__(self) -> None:
        self.rotation_mode = "QUATERNION"


class _FakePoseBones:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: _FakePoseBone() for n in names}

    def get(self, name: str) -> _FakePoseBone | None:
        return self._items.get(name)


class _FakeAnimData:
    def __init__(self) -> None:
        self.action: Any = None


class _FakeArmatureObject:
    def __init__(self, name: str, pose_bones: list[str] | None = None) -> None:
        self.name = name
        self.type = "ARMATURE"
        if pose_bones is not None:
            self.pose = SimpleNamespace(bones=_FakePoseBones(pose_bones))
        else:
            self.pose = None
        self.animation_data: _FakeAnimData | None = None

    def animation_data_create(self) -> _FakeAnimData:
        self.animation_data = _FakeAnimData()
        return self.animation_data


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


@pytest.fixture(autouse=True)
def patch_bpy_data_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give the bridge's ``bpy.data.actions.new`` something to call.

    The conftest stub doesn't carry a ``bpy.data.actions`` collection;
    the operator forwards the bpy module through to
    ``animation_data_to_blender`` only when explicitly passed, but our
    operator doesn't pass it -- it relies on the in-process import. We
    patch the live module under the operator's name binding.
    """
    import bpy

    if not hasattr(bpy, "data"):
        bpy.data = SimpleNamespace()  # type: ignore[attr-defined]

    class _Action:
        def __init__(self, name: str) -> None:
            self.name = name
            self.fcurves = SimpleNamespace(
                new=lambda **_kw: SimpleNamespace(
                    keyframe_points=SimpleNamespace(
                        add=lambda _n: None,
                        foreach_set=lambda *_a, **_kw: None,
                    )
                )
            )

    bpy.data.actions = SimpleNamespace(new=lambda name: _Action(name))  # type: ignore[attr-defined]


# ---- _resolve_target ------------------------------------------------------


def test_resolve_target_uses_explicit_pick() -> None:
    op = NIFBLEND_OT_import_kf()
    rig_a = _FakeArmatureObject("RigA", pose_bones=[])
    rig_b = _FakeArmatureObject("RigB", pose_bones=[])
    ctx = SimpleNamespace(
        scene=_FakeScene([rig_a, rig_b]),
        active_object=rig_a,
    )
    op.target_armature = "RigB"
    assert op._resolve_target(ctx) is rig_b


def test_resolve_target_falls_back_to_active_object() -> None:
    op = NIFBLEND_OT_import_kf()
    rig = _FakeArmatureObject("Rig", pose_bones=[])
    ctx = _fake_context(rig)
    op.target_armature = ""
    assert op._resolve_target(ctx) is rig


def test_resolve_target_returns_none_when_active_is_not_armature() -> None:
    op = NIFBLEND_OT_import_kf()
    mesh = SimpleNamespace(name="Mesh", type="MESH")
    ctx = SimpleNamespace(
        scene=_FakeScene([mesh]),
        active_object=mesh,
    )
    op.target_armature = ""
    assert op._resolve_target(ctx) is None


# ---- _unresolved_bones ----------------------------------------------------


def test_unresolved_bones_lists_missing_pose_bones() -> None:
    op = NIFBLEND_OT_import_kf()
    rig = _FakeArmatureObject("Rig", pose_bones=["A"])
    anim = SimpleNamespace(
        tracks=[SimpleNamespace(bone_name="A"), SimpleNamespace(bone_name="GHOST")]
    )
    assert op._unresolved_bones(rig, anim) == ["GHOST"]


def test_unresolved_bones_returns_all_when_no_pose() -> None:
    op = NIFBLEND_OT_import_kf()
    rig = _FakeArmatureObject("Rig", pose_bones=None)  # no pose attribute
    anim = SimpleNamespace(tracks=[SimpleNamespace(bone_name="A")])
    assert op._unresolved_bones(rig, anim) == ["A"]


# ---- end-to-end execute --------------------------------------------------


def test_execute_imports_action_onto_active_armature(tmp_path: Path) -> None:
    table = _sse_table_with_sequence()
    kf_path = _write_kf_to_disk(table)

    op = NIFBLEND_OT_import_kf()
    op.filepath = kf_path
    op.rotation_mode = "QUATERNION"
    op.target_armature = ""
    op.report = lambda *_a, **_kw: None  # type: ignore[assignment]

    rig = _FakeArmatureObject("Rig", pose_bones=[])
    ctx = _fake_context(rig)

    result = op.execute(ctx)

    assert result == {"FINISHED"}
    assert rig.animation_data is not None
    assert rig.animation_data.action is not None


def test_execute_rejects_non_kf_file(tmp_path: Path) -> None:
    path = _write_nif_only_table_to_disk()
    op = NIFBLEND_OT_import_kf()
    op.filepath = path
    op.rotation_mode = "QUATERNION"
    op.target_armature = ""

    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]

    rig = _FakeArmatureObject("Rig", pose_bones=[])
    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("not a KF file" in msg for _, msg in reports)


def test_execute_rejects_missing_target() -> None:
    table = _sse_table_with_sequence()
    kf_path = _write_kf_to_disk(table)

    op = NIFBLEND_OT_import_kf()
    op.filepath = kf_path
    op.rotation_mode = "QUATERNION"
    op.target_armature = ""

    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]

    ctx = SimpleNamespace(scene=_FakeScene([]), active_object=None)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("Select an armature" in msg for _, msg in reports)


def test_execute_unreadable_file_reports_error() -> None:
    op = NIFBLEND_OT_import_kf()
    op.filepath = "C:/this/path/does/not/exist.kf"
    op.rotation_mode = "QUATERNION"
    op.target_armature = ""

    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]

    rig = _FakeArmatureObject("Rig", pose_bones=[])
    ctx = _fake_context(rig)
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("Failed to read" in msg for _, msg in reports)


# ---- enum helper ---------------------------------------------------------


def test_armature_enum_items_returns_sentinel_when_empty() -> None:
    ctx = SimpleNamespace(scene=_FakeScene([]))
    items = import_kf_mod._armature_enum_items(None, ctx)
    assert items == [("", "<no armature in scene>", "Add an armature first")]


def test_armature_enum_items_lists_armature_objects_only() -> None:
    rig = _FakeArmatureObject("Rig", pose_bones=[])
    mesh = SimpleNamespace(name="Mesh", type="MESH")
    ctx = SimpleNamespace(scene=_FakeScene([rig, mesh]))
    items = import_kf_mod._armature_enum_items(None, ctx)
    assert [i[0] for i in items] == ["Rig"]
