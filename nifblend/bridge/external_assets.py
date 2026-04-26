"""Phase 9c: external-asset resolver protocol.

Generalises the per-game ``Data/`` root + texture-resolution machinery
(:mod:`nifblend.bridge.textures`) into a small protocol that operators
can pass to bridge code without dragging in :class:`bpy.types.Context`.

Concrete consumers:

* Starfield's external ``.mesh`` references on :class:`BSGeometry`
  (Phase 9d, :mod:`nifblend.bridge.games.starfield`).
* Starfield's ``.mat`` JSON material manifests (Phase 9e,
  :mod:`nifblend.bridge.games.starfield_material`).
* The pre-existing FO76 :func:`bsgeometry_mesh_refs` consumers — the
  resolver becomes the first concrete way to turn a path string into a
  loose file on disk for that game too.

The protocol is structural (``typing.Protocol``), so callers can either
use :class:`PrefsExternalAssetResolver` (driven by the live
:class:`~nifblend.preferences.NIFBLEND_AddonPreferences`) or supply
their own implementation in tests / scripts.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .textures import resolve_texture_path

__all__ = [
    "ExternalAssetResolver",
    "PrefsExternalAssetResolver",
    "StaticExternalAssetResolver",
]


class ExternalAssetResolver(Protocol):
    """Resolve game-relative paths to absolute on-disk files."""

    def resolve_mesh(self, rel_path: str) -> Path | None:
        """Return the absolute ``.mesh`` path or ``None`` when not found."""

    def resolve_material(self, rel_path: str) -> Path | None:
        """Return the absolute ``.mat`` path or ``None`` when not found."""

    def resolve_texture(self, rel_path: str) -> Path | None:
        """Return the absolute texture path or ``None`` when not found."""


@dataclass(slots=True)
class PrefsExternalAssetResolver:
    """Resolver backed by an explicit Data root + extra search roots.

    Thin adapter over :func:`resolve_texture_path` that applies the
    same case-insensitive walk + fuzzy-fallback strategy uniformly to
    meshes / materials / textures. The ``mode`` argument matches the
    :class:`NIFBLEND_AddonPreferences.texture_resolution_mode` enum.
    """

    data_root: str
    mode: str = "CASE_INSENSITIVE"
    extra_roots: tuple[str, ...] = ()

    def _resolve(self, rel_path: str) -> Path | None:
        if not rel_path:
            return None
        return resolve_texture_path(
            rel_path,
            data_root=self.data_root,
            mode=self.mode,
            extra_roots=self.extra_roots,
        )

    def resolve_mesh(self, rel_path: str) -> Path | None:
        return self._resolve(rel_path)

    def resolve_material(self, rel_path: str) -> Path | None:
        return self._resolve(rel_path)

    def resolve_texture(self, rel_path: str) -> Path | None:
        return self._resolve(rel_path)


@dataclass(slots=True)
class StaticExternalAssetResolver:
    """Test resolver that resolves against an in-memory mapping.

    Each map is keyed by the *normalised* relative path the caller
    expects (lowercase, forward-slash). Entries that map to ``None``
    represent known-absent assets.
    """

    meshes: dict[str, Path | None]
    materials: dict[str, Path | None] | None = None
    textures: dict[str, Path | None] | None = None

    def _lookup(
        self, rel_path: str, table: dict[str, Path | None] | None
    ) -> Path | None:
        if not rel_path or table is None:
            return None
        return table.get(rel_path.replace("\\", "/").lower())

    def resolve_mesh(self, rel_path: str) -> Path | None:
        return self._lookup(rel_path, self.meshes)

    def resolve_material(self, rel_path: str) -> Path | None:
        return self._lookup(rel_path, self.materials)

    def resolve_texture(self, rel_path: str) -> Path | None:
        return self._lookup(rel_path, self.textures)


def collect_extra_roots(
    primary: str, candidates: Sequence[str]
) -> tuple[str, ...]:
    """Return ``candidates`` minus ``primary`` (case-insensitive), filtered for non-empty."""
    seen = {os.path.normcase(primary)} if primary else set()
    out: list[str] = []
    for c in candidates:
        if not c:
            continue
        key = os.path.normcase(c)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return tuple(out)
