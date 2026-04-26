"""Phase 9i tests: Starfield ``.mat`` reload operator + path stamp helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from nifblend.bridge.material_props import (
    PROP_ATTR as MAT_PROP_ATTR,
)
from nifblend.bridge.material_props import (
    get_starfield_material_path,
    set_starfield_material_path,
)
from nifblend.bridge.object_props import apply_profile_to_object
from nifblend.format.versions import GameProfile
from nifblend.ops.games_starfield import NIFBLEND_OT_starfield_reload_material

# ---- PropertyGroup helpers ----------------------------------------------


def test_set_get_starfield_material_path_round_trip() -> None:
    mat = SimpleNamespace()
    set_starfield_material_path(mat, "materials/foo.mat")
    assert get_starfield_material_path(mat) == "materials/foo.mat"


def test_get_starfield_material_path_unset_returns_empty_string() -> None:
    mat = SimpleNamespace()
    assert get_starfield_material_path(mat) == ""


def test_set_starfield_material_path_empty_clears_stamp() -> None:
    mat = SimpleNamespace()
    set_starfield_material_path(mat, "materials/foo.mat")
    set_starfield_material_path(mat, "")
    assert get_starfield_material_path(mat) == ""


def test_get_starfield_material_path_no_propertygroup_returns_empty() -> None:
    class _Frozen:
        __slots__ = ()

    assert get_starfield_material_path(_Frozen()) == ""


# ---- operator: poll() ----------------------------------------------------


def _make_material_with_stamp(name: str, rel_path: str) -> Any:
    mat = SimpleNamespace(name=name, users=1)
    setattr(mat, MAT_PROP_ATTR, SimpleNamespace())
    if rel_path:
        set_starfield_material_path(mat, rel_path)
    return mat


def _make_mesh_object(
    name: str,
    profile: GameProfile,
    *,
    materials: list[Any] | None = None,
) -> Any:
    mesh = SimpleNamespace(
        name=name + "_mesh",
        materials=list(materials or []),
    )
    obj = SimpleNamespace(name=name, type="MESH", data=mesh)
    apply_profile_to_object(
        obj,
        profile=profile,
        nif_version=0x14020007,
        user_version=12,
        bs_version=172,
        source_path="/tmp/test.nif",
        block_origin="BSGeometry",
    )
    return obj


def _ctx(active: Any | None) -> SimpleNamespace:
    return SimpleNamespace(active_object=active)


def test_poll_true_when_active_starfield_mesh_has_stamped_material() -> None:
    mat = _make_material_with_stamp("M", "materials/x.mat")
    obj = _make_mesh_object("O", GameProfile.STARFIELD, materials=[mat])
    assert NIFBLEND_OT_starfield_reload_material.poll(_ctx(obj)) is True


def test_poll_false_for_non_starfield_profile() -> None:
    mat = _make_material_with_stamp("M", "materials/x.mat")
    obj = _make_mesh_object("O", GameProfile.SKYRIM_SE, materials=[mat])
    assert NIFBLEND_OT_starfield_reload_material.poll(_ctx(obj)) is False


def test_poll_false_when_no_material_stamped() -> None:
    mat = _make_material_with_stamp("M", "")
    obj = _make_mesh_object("O", GameProfile.STARFIELD, materials=[mat])
    assert NIFBLEND_OT_starfield_reload_material.poll(_ctx(obj)) is False


def test_poll_false_when_no_active_object() -> None:
    assert NIFBLEND_OT_starfield_reload_material.poll(_ctx(None)) is False


def test_poll_false_when_active_is_not_mesh() -> None:
    obj = SimpleNamespace(type="EMPTY", data=SimpleNamespace(materials=[]))
    apply_profile_to_object(
        obj,
        profile=GameProfile.STARFIELD,
        nif_version=0,
        user_version=0,
        bs_version=172,
        source_path="",
        block_origin="",
    )
    assert NIFBLEND_OT_starfield_reload_material.poll(_ctx(obj)) is False


# ---- operator: execute() -------------------------------------------------


_MAT_PAYLOAD = (
    b'{"Type":"Material","Name":"X","BaseColor":[0.4,0.5,0.6],'
    b'"Roughness":0.2,"Metalness":0.7}'
)


def _make_prefs(data_root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        starfield_data=str(data_root),
        texture_resolution_mode="STRICT",
    )


@pytest.fixture
def stub_material_builder(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Stub out the heavy ``material_data_to_blender`` call.

    Returns the recorded list of ``MaterialData`` instances the operator
    handed to the builder. Each call returns a fresh tagged
    ``SimpleNamespace`` so the test can assert slot replacement.
    """
    import nifblend.ops.games_starfield as op_mod

    calls: list[Any] = []

    def _build(data: Any, *, bpy: Any, resolve_texture: Any) -> Any:
        calls.append(data)
        mat = SimpleNamespace(name=data.name, users=1)
        setattr(mat, MAT_PROP_ATTR, SimpleNamespace())
        return mat

    monkeypatch.setattr(op_mod, "material_data_to_blender", _build)
    return calls


def test_execute_reloads_and_swaps_material(
    tmp_path: Path,
    stub_material_builder: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rel_path = "materials/x.mat"
    abs_path = tmp_path / "materials" / "x.mat"
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(_MAT_PAYLOAD)

    mat = _make_material_with_stamp("OldMat", rel_path)
    obj = _make_mesh_object("O", GameProfile.STARFIELD, materials=[mat])
    ctx = SimpleNamespace(active_object=obj)

    import nifblend.ops.games_starfield as op_mod

    monkeypatch.setattr(op_mod, "get_prefs", lambda _ctx: _make_prefs(tmp_path))

    op = NIFBLEND_OT_starfield_reload_material()
    op.report = lambda *_args, **_kw: None  # type: ignore[assignment]
    result = op.execute(ctx)

    assert result == {"FINISHED"}
    assert len(stub_material_builder) == 1
    decoded = stub_material_builder[0]
    assert decoded.base_color[:3] == pytest.approx((0.4, 0.5, 0.6))
    new_mat = obj.data.materials[0]
    assert new_mat is not mat
    assert get_starfield_material_path(new_mat) == rel_path


def test_execute_cancels_when_no_data_root_configured(
    tmp_path: Path,
    stub_material_builder: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mat = _make_material_with_stamp("M", "materials/x.mat")
    obj = _make_mesh_object("O", GameProfile.STARFIELD, materials=[mat])
    ctx = SimpleNamespace(active_object=obj)

    import nifblend.ops.games_starfield as op_mod

    monkeypatch.setattr(
        op_mod,
        "get_prefs",
        lambda _ctx: SimpleNamespace(
            starfield_data="", texture_resolution_mode="STRICT"
        ),
    )

    op = NIFBLEND_OT_starfield_reload_material()
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((set(level), msg))  # type: ignore[assignment]
    result = op.execute(ctx)

    assert result == {"CANCELLED"}
    assert any("Data root" in msg for _, msg in reports)
    assert obj.data.materials[0] is mat
    assert stub_material_builder == []


def test_execute_cancels_when_mat_unresolved(
    tmp_path: Path,
    stub_material_builder: list[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mat = _make_material_with_stamp("M", "materials/missing.mat")
    obj = _make_mesh_object("O", GameProfile.STARFIELD, materials=[mat])
    ctx = SimpleNamespace(active_object=obj)

    import nifblend.ops.games_starfield as op_mod

    monkeypatch.setattr(op_mod, "get_prefs", lambda _ctx: _make_prefs(tmp_path))

    op = NIFBLEND_OT_starfield_reload_material()
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((set(level), msg))  # type: ignore[assignment]
    result = op.execute(ctx)

    assert result == {"CANCELLED"}
    assert any("ERROR" in level for level, _ in reports)
    assert obj.data.materials[0] is mat
    assert stub_material_builder == []
