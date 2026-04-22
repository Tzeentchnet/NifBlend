"""Tests for nifblend.bridge.object_props duck-typed helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nifblend.bridge.object_props import (
    apply_profile_to_object,
    object_profile,
    read_profile_from_object,
)
from nifblend.format.versions import GameProfile


@pytest.mark.parametrize("profile", list(GameProfile))
def test_apply_and_read_round_trip(profile):
    obj = SimpleNamespace()
    apply_profile_to_object(
        obj,
        profile=profile,
        nif_version=0x14020007,
        user_version=12,
        bs_version=100,
        source_path="C:/foo.nif",
        block_origin="BSTriShape",
    )
    assert read_profile_from_object(obj) == profile
    assert obj.nifblend.nif_version == 0x14020007
    assert obj.nifblend.user_version == 12
    assert obj.nifblend.bs_version == 100
    assert obj.nifblend.source_path == "C:/foo.nif"
    assert obj.nifblend.block_origin == "BSTriShape"


def test_object_profile_none_returns_unknown():
    assert object_profile(None) == GameProfile.UNKNOWN


def test_object_profile_no_props_returns_unknown():
    assert object_profile(SimpleNamespace()) == GameProfile.UNKNOWN


def test_read_profile_invalid_value_returns_unknown():
    obj = SimpleNamespace(nifblend=SimpleNamespace(game_profile="bogus"))
    assert read_profile_from_object(obj) == GameProfile.UNKNOWN
