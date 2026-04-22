"""Smoke tests for nifblend.preferences."""

from __future__ import annotations

from nifblend.format.versions import GameProfile
from nifblend.preferences import (
    ADDON_PACKAGE,
    GAME_PROFILE_ITEMS,
    data_root_for,
    get_prefs,
    resolve_worker_count,
)


def test_addon_package_is_top_level():
    assert ADDON_PACKAGE == "nifblend"


def test_profile_items_cover_every_profile():
    values = {item[0] for item in GAME_PROFILE_ITEMS}
    assert values == {p.value for p in GameProfile}


def test_data_root_for_none_prefs():
    assert data_root_for(GameProfile.SKYRIM_SE, None) == ""


def test_data_root_for_unknown_profile_returns_empty():
    from types import SimpleNamespace

    fake = SimpleNamespace(skyrim_se_data="C:/Skyrim SE/Data")
    assert data_root_for(GameProfile.SKYRIM_SE, fake) == "C:/Skyrim SE/Data"
    assert data_root_for(GameProfile.UNKNOWN, fake) == ""


def test_resolve_worker_count_falls_back_to_cpu():
    assert resolve_worker_count(None) >= 1


def test_resolve_worker_count_explicit():
    from types import SimpleNamespace

    assert resolve_worker_count(SimpleNamespace(worker_count=8)) == 8


def test_get_prefs_returns_none_in_test_env():
    # The headless bpy stub has no preferences/addons surface.
    assert get_prefs() is None
