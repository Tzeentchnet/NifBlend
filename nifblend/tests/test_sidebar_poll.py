"""Phase 8j: sidebar panel ``poll()`` gating tests.

Verifies every game-specific sub-panel only surfaces when the active
object's stamped :class:`GameProfile` matches its target game family
(falsy / ``UNKNOWN`` always hides it).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nifblend.format.versions import GameProfile
from nifblend.ui.sidebar import (
    NIFBLEND_PT_game_fallout3nv,
    NIFBLEND_PT_game_fallout4,
    NIFBLEND_PT_game_fallout76,
    NIFBLEND_PT_game_morrowind,
    NIFBLEND_PT_game_oblivion,
    NIFBLEND_PT_game_skyrim,
    NIFBLEND_PT_game_specific,
    active_profile,
)


def _ctx(profile: GameProfile | None) -> SimpleNamespace:
    """Build a fake context whose ``active_object`` is stamped with ``profile``."""
    if profile is None:
        return SimpleNamespace(active_object=None)
    obj = SimpleNamespace(nifblend=SimpleNamespace(game_profile=profile.value))
    return SimpleNamespace(active_object=obj)


# ---- active_profile helper -----------------------------------------------


def test_active_profile_returns_unknown_for_no_active_object() -> None:
    assert active_profile(_ctx(None)) is GameProfile.UNKNOWN


@pytest.mark.parametrize("profile", list(GameProfile))
def test_active_profile_round_trips_every_game(profile: GameProfile) -> None:
    assert active_profile(_ctx(profile)) is profile


def test_active_profile_unknown_when_object_lacks_nifblend() -> None:
    ctx = SimpleNamespace(active_object=SimpleNamespace())
    assert active_profile(ctx) is GameProfile.UNKNOWN


# ---- per-panel poll() ----------------------------------------------------


_GATE = {
    NIFBLEND_PT_game_skyrim: {GameProfile.SKYRIM_LE, GameProfile.SKYRIM_SE},
    NIFBLEND_PT_game_oblivion: {
        GameProfile.MORROWIND,
        GameProfile.OBLIVION,
        GameProfile.FALLOUT_3_NV,
    },
    NIFBLEND_PT_game_fallout4: {GameProfile.FALLOUT_4},
    NIFBLEND_PT_game_fallout76: {GameProfile.FALLOUT_76},
    NIFBLEND_PT_game_fallout3nv: {GameProfile.FALLOUT_3_NV},
    NIFBLEND_PT_game_morrowind: {GameProfile.MORROWIND, GameProfile.OBLIVION},
}


@pytest.mark.parametrize(
    ("panel", "allowed"),
    list(_GATE.items()),
    ids=lambda v: getattr(v, "__name__", str(v)),
)
def test_panel_poll_matches_gate(panel: type, allowed: set[GameProfile]) -> None:
    for profile in GameProfile:
        ctx = _ctx(profile)
        expected = profile in allowed
        assert panel.poll(ctx) is expected, (
            f"{panel.__name__}.poll({profile.value}) -> "
            f"{panel.poll(ctx)} (expected {expected})"
        )


@pytest.mark.parametrize("panel", list(_GATE))
def test_panel_poll_false_when_no_active_object(panel: type) -> None:
    assert panel.poll(_ctx(None)) is False


# ---- the parent "Game-Specific" panel ------------------------------------


def test_game_specific_poll_false_for_unknown() -> None:
    assert NIFBLEND_PT_game_specific.poll(_ctx(GameProfile.UNKNOWN)) is False
    assert NIFBLEND_PT_game_specific.poll(_ctx(None)) is False


@pytest.mark.parametrize(
    "profile",
    [p for p in GameProfile if p is not GameProfile.UNKNOWN],
)
def test_game_specific_poll_true_for_every_known_profile(profile: GameProfile) -> None:
    assert NIFBLEND_PT_game_specific.poll(_ctx(profile)) is True
