"""Phase 8j: Skyrim LE↔SE shader-flag-walk operator tests.

Verifies the conversion operators only walk the **selected** meshes
(siblings outside the selection are untouched), share-deduplicate
materials, restamp the per-object profile + ``bs_version``, and that
``poll()`` gates correctly on the active selection's stamped profile.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge.material_props import PROP_ATTR as MAT_PROP_ATTR
from nifblend.bridge.object_props import (
    PROP_ATTR as OBJ_PROP_ATTR,
)
from nifblend.bridge.object_props import (
    apply_profile_to_object,
    read_profile_from_object,
)
from nifblend.format.versions import GameProfile
from nifblend.ops.games_skyrim import (
    NIFBLEND_OT_skyrim_le_to_se,
    NIFBLEND_OT_skyrim_se_to_le,
)


def _make_material(name: str, f1: int = 0, f2: int = 0) -> Any:
    mat = SimpleNamespace(name=name)
    setattr(
        mat,
        MAT_PROP_ATTR,
        SimpleNamespace(shader_flags_1=f1, shader_flags_2=f2),
    )
    return mat


def _make_mesh_object(
    name: str,
    profile: GameProfile,
    *,
    materials: list[Any] | None = None,
) -> Any:
    obj = SimpleNamespace(
        name=name,
        type="MESH",
        material_slots=[SimpleNamespace(material=m) for m in (materials or [])],
    )
    apply_profile_to_object(
        obj,
        profile=profile,
        nif_version=0x14020007,
        user_version=12,
        bs_version=83 if profile == GameProfile.SKYRIM_LE else 100,
        source_path="/tmp/test.nif",
        block_origin="BSTriShape",
    )
    return obj


def _ctx(selected: list[Any], active: Any | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        selected_objects=list(selected),
        active_object=active if active is not None else (selected[0] if selected else None),
    )


# ---- execute(): scope ----------------------------------------------------


def test_le_to_se_only_touches_selected_objects() -> None:
    mat_sel = _make_material("MatSel", f1=0xDEADBEEF, f2=0x1234)
    mat_unsel = _make_material("MatUnsel", f1=0xCAFEBABE, f2=0x5678)
    sel = _make_mesh_object("Sel", GameProfile.SKYRIM_LE, materials=[mat_sel])
    unsel = _make_mesh_object("Unsel", GameProfile.SKYRIM_LE, materials=[mat_unsel])
    ctx = _ctx(selected=[sel])

    op = NIFBLEND_OT_skyrim_le_to_se()
    op.report = lambda *_a, **_kw: None
    assert op.execute(ctx) == {"FINISHED"}

    # Empty move-table → values unchanged but profile/bs_version restamped on selected only.
    assert read_profile_from_object(sel) is GameProfile.SKYRIM_SE
    assert getattr(sel, OBJ_PROP_ATTR).bs_version == 100
    # Sibling outside the selection keeps its LE stamp.
    assert read_profile_from_object(unsel) is GameProfile.SKYRIM_LE
    assert getattr(unsel, OBJ_PROP_ATTR).bs_version == 83


def test_se_to_le_restamps_bs_version_to_83() -> None:
    obj = _make_mesh_object(
        "A", GameProfile.SKYRIM_SE, materials=[_make_material("M")]
    )
    ctx = _ctx(selected=[obj])

    op = NIFBLEND_OT_skyrim_se_to_le()
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert read_profile_from_object(obj) is GameProfile.SKYRIM_LE
    assert getattr(obj, OBJ_PROP_ATTR).bs_version == 83


def test_conversion_skips_non_mesh_objects() -> None:
    mesh = _make_mesh_object(
        "M", GameProfile.SKYRIM_LE, materials=[_make_material("Mat")]
    )
    armature = SimpleNamespace(name="Skel", type="ARMATURE", material_slots=[])
    apply_profile_to_object(
        armature, profile=GameProfile.SKYRIM_LE, bs_version=83
    )
    ctx = _ctx(selected=[mesh, armature])

    op = NIFBLEND_OT_skyrim_le_to_se()
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert read_profile_from_object(mesh) is GameProfile.SKYRIM_SE
    # Armature is unchanged (not a MESH → skipped entirely).
    assert read_profile_from_object(armature) is GameProfile.SKYRIM_LE


def test_shared_material_only_converted_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """A material shared between two meshes is only run through the converter once."""
    converted: list[tuple[int, int]] = []

    def _spy(f1: int, f2: int) -> tuple[int, int]:
        converted.append((f1, f2))
        return f1, f2

    monkeypatch.setattr(
        "nifblend.ops.games_skyrim.convert_shader_flags_le_to_se", _spy
    )

    shared = _make_material("Shared", f1=1, f2=2)
    a = _make_mesh_object("A", GameProfile.SKYRIM_LE, materials=[shared])
    b = _make_mesh_object("B", GameProfile.SKYRIM_LE, materials=[shared])
    ctx = _ctx(selected=[a, b])

    op = NIFBLEND_OT_skyrim_le_to_se()
    op.report = lambda *_a, **_kw: None
    op.execute(ctx)

    assert converted == [(1, 2)]


def test_empty_selection_is_a_clean_noop() -> None:
    ctx = _ctx(selected=[])
    op = NIFBLEND_OT_skyrim_le_to_se()
    op.report = lambda *_a, **_kw: None
    assert op.execute(ctx) == {"FINISHED"}


# ---- poll() --------------------------------------------------------------


def test_le_to_se_poll_true_only_when_an_le_object_is_selected() -> None:
    le = _make_mesh_object("LE", GameProfile.SKYRIM_LE, materials=[])
    se = _make_mesh_object("SE", GameProfile.SKYRIM_SE, materials=[])

    assert NIFBLEND_OT_skyrim_le_to_se.poll(_ctx(selected=[le])) is True
    assert NIFBLEND_OT_skyrim_le_to_se.poll(_ctx(selected=[le, se])) is True
    assert NIFBLEND_OT_skyrim_le_to_se.poll(_ctx(selected=[se])) is False
    assert NIFBLEND_OT_skyrim_le_to_se.poll(_ctx(selected=[])) is False


def test_se_to_le_poll_true_only_when_an_se_object_is_selected() -> None:
    le = _make_mesh_object("LE", GameProfile.SKYRIM_LE, materials=[])
    se = _make_mesh_object("SE", GameProfile.SKYRIM_SE, materials=[])

    assert NIFBLEND_OT_skyrim_se_to_le.poll(_ctx(selected=[se])) is True
    assert NIFBLEND_OT_skyrim_se_to_le.poll(_ctx(selected=[le])) is False
    assert NIFBLEND_OT_skyrim_se_to_le.poll(_ctx(selected=[])) is False
