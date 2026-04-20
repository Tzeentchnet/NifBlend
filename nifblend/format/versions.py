"""Version packing and comparison helpers.

NIF version literals in the schema use the dotted form `20.2.0.7`. Internally
we pack to a single 32-bit unsigned int with one byte per component, so
comparisons reduce to ordinary integer comparisons.

This module replaces what `new-pyffi/versions.py` would have provided to
codegen output. Generated code references `pack_version` for version literals
and `ReadContext.version / .user_version / .bs_version` for the three globals.

The :class:`GameProfile` enum maps the on-disk ``(version, user_version,
bs_version)`` triple to the small set of game targets the bridge layer cares
about; see :func:`detect_profile`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

__all__ = ["GameProfile", "Version", "detect_profile", "pack_version", "unpack_version"]


def pack_version(major: int, minor: int = 0, patch: int = 0, sub: int = 0) -> int:
    """Pack a 4-component NIF version into a 32-bit unsigned int.

    Each component must fit in a byte. The packing matches the on-disk byte
    order used by the NIF header (`major << 24 | minor << 16 | patch << 8 | sub`).
    """
    for name, value in (("major", major), ("minor", minor), ("patch", patch), ("sub", sub)):
        if not 0 <= value <= 0xFF:
            raise ValueError(f"version component {name}={value!r} out of byte range")
    return (major << 24) | (minor << 16) | (patch << 8) | sub


def unpack_version(packed: int) -> tuple[int, int, int, int]:
    """Inverse of `pack_version`."""
    return (
        (packed >> 24) & 0xFF,
        (packed >> 16) & 0xFF,
        (packed >> 8) & 0xFF,
        packed & 0xFF,
    )


@dataclass(frozen=True, slots=True)
class Version:
    """Convenience wrapper around a packed NIF version."""

    packed: int

    @classmethod
    def parse(cls, dotted: str) -> Version:
        parts = [int(p) for p in dotted.split(".")]
        if not 1 <= len(parts) <= 4:
            raise ValueError(f"expected 1-4 dotted components, got {dotted!r}")
        parts += [0] * (4 - len(parts))
        return cls(pack_version(*parts))

    def __int__(self) -> int:
        return self.packed


# ---- game-profile dispatch ------------------------------------------------


class GameProfile(Enum):
    """Coarse target enum derived from the NIF header globals.

    Membership is small on purpose: the bridge layer branches on the *family*
    of behaviour (e.g. "Skyrim Special Edition's BSTriShape vertex layout"),
    not on every dot-release. Add entries as later phases need to discriminate.

    ``UNKNOWN`` is returned when the triple does not match any known game; the
    caller may still proceed (the codegen layer keys on raw version comparisons),
    but high-level bridge code should treat it as best-effort.
    """

    UNKNOWN = "unknown"
    MORROWIND = "morrowind"
    OBLIVION = "oblivion"
    FALLOUT_3_NV = "fallout3_nv"
    SKYRIM_LE = "skyrim_le"
    SKYRIM_SE = "skyrim_se"
    FALLOUT_4 = "fallout4"
    FALLOUT_76 = "fallout76"
    # Reserved -- Starfield support is deferred to v1.1 (see ROADMAP Phase 6).
    STARFIELD = "starfield"


def detect_profile(version: int, user_version: int, bs_version: int) -> GameProfile:
    """Map the three NIF header globals to a :class:`GameProfile`.

    Heuristics follow the conventions used by NifSkope / pyffi:

    - **Morrowind**: ``version == 4.0.0.2`` (no user/bs versions).
    - **Oblivion**: ``version == 20.0.0.5``, ``user_version in {10, 11}``.
    - **Fallout 3 / NV**: ``version == 20.2.0.7``, ``user_version == 11``,
      ``bs_version in {34, 83}`` (FO3 is 34, NV is 34 with bs_version 34;
      both share the same code path here).
    - **Skyrim LE**: ``version == 20.2.0.7``, ``user_version == 12``,
      ``bs_version == 83``.
    - **Skyrim SE**: ``version == 20.2.0.7``, ``user_version == 12``,
      ``bs_version == 100``.
    - **Fallout 4**: ``bs_version in {130, 131, 132}``.
    - **Fallout 76**: ``bs_version in {139, 152, 155}``.
    - **Starfield**: ``bs_version >= 172``.
    """
    if version == pack_version(4, 0, 0, 2):
        return GameProfile.MORROWIND
    if version == pack_version(20, 0, 0, 5) and user_version in (10, 11):
        return GameProfile.OBLIVION
    if version == pack_version(20, 2, 0, 7):
        if user_version == 11:
            return GameProfile.FALLOUT_3_NV
        if user_version == 12:
            if bs_version == 100:
                return GameProfile.SKYRIM_SE
            if bs_version == 83:
                return GameProfile.SKYRIM_LE
            if bs_version in (130, 131, 132):
                return GameProfile.FALLOUT_4
            if bs_version in (139, 152, 155):
                return GameProfile.FALLOUT_76
            if bs_version >= 172:
                return GameProfile.STARFIELD
    return GameProfile.UNKNOWN
