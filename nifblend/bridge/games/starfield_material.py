"""Phase 9e: thin Starfield ``.mat`` JSON manifest reader.

Returns a :class:`~nifblend.bridge.material_in.MaterialData` so the
existing :func:`material_data_to_blender` graph builder is reused
unchanged. Unknown JSON keys are preserved verbatim on
:attr:`MaterialData.starfield_extras` (a free-form dict) so a future
export round-trip can re-emit them; the bridge does not interpret them.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from nifblend.bridge.external_assets import ExternalAssetResolver
from nifblend.bridge.material_in import MaterialData

__all__ = [
    "StarfieldMaterialError",
    "decode_starfield_material",
    "load_starfield_material",
    "starfield_material_textures",
]


class StarfieldMaterialError(RuntimeError):
    """Raised when a Starfield ``.mat`` cannot be parsed or resolved."""


# Map Starfield-side texture-channel labels to the existing NifBlend
# slot names so the Principled-BSDF graph builder picks them up. Unknown
# channel labels are preserved verbatim in ``MaterialData.textures`` —
# they round-trip even though the existing graph builder ignores them.
_TEXTURE_CHANNEL_TO_SLOT: dict[str, str] = {
    "BaseColor": "diffuse",
    "Diffuse": "diffuse",
    "Albedo": "diffuse",
    "Normal": "normal",
    "Roughness": "subsurface",  # closest existing slot the graph wires
    "Metallic": "env_mask",
    "Metalness": "env_mask",
    "Emissive": "glow",
    "Emission": "glow",
    "Height": "height",
    "Parallax": "height",
}


def _color3(value: Any, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return default
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return default


def _color4(
    value: Any, default: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return default
    try:
        rgb = (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return default
    a = float(value[3]) if len(value) >= 4 else default[3]
    return (*rgb, a)


def _float(value: Any, default: float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def decode_starfield_material(
    payload: dict[str, Any], *, name: str | None = None
) -> MaterialData:
    """Decode a parsed JSON dict into a :class:`MaterialData`.

    The dict is the structure documented in
    :doc:`UPSTREAM_STARFIELD <UPSTREAM_STARFIELD>`. Missing keys fall
    back to neutral defaults; the returned ``origin`` is always
    ``"StarfieldMaterial"`` so the export side (deferred to v2) can
    dispatch on it.
    """
    if not isinstance(payload, dict):
        raise StarfieldMaterialError(
            f"expected JSON object at the document root, got {type(payload).__name__}"
        )

    resolved_name = (
        name
        if name is not None
        else str(payload.get("Name") or payload.get("name") or "StarfieldMaterial")
    )

    data = MaterialData(name=resolved_name, origin="StarfieldMaterial")
    data.base_color = _color4(
        payload.get("BaseColor") or payload.get("base_color"),
        (1.0, 1.0, 1.0, 1.0),
    )
    data.emissive_color = _color3(
        payload.get("EmissiveColor") or payload.get("emissive_color"),
        (0.0, 0.0, 0.0),
    )
    data.emissive_multiple = _float(
        payload.get("EmissiveIntensity") or payload.get("emissive_intensity"),
        0.0,
    )
    # Starfield reports roughness in [0, 1]; smoothness = 1 - roughness for
    # the existing Principled-BSDF graph that keys on smoothness.
    roughness = _float(payload.get("Roughness") or payload.get("roughness"), 0.5)
    data.smoothness = max(0.0, min(1.0, 1.0 - roughness))
    data.specular_strength = _float(
        payload.get("Metalness") or payload.get("Metallic") or payload.get("metallic"),
        0.0,
    )

    textures = payload.get("Textures") or payload.get("textures") or {}
    if isinstance(textures, dict):
        for channel, path in textures.items():
            if not isinstance(path, str) or not path:
                continue
            slot = _TEXTURE_CHANNEL_TO_SLOT.get(channel, channel.lower())
            data.textures[slot] = path

    # Stash the raw payload on the bridge dataclass so future export work can
    # round-trip every key the v1.1 reader does not interpret. We attach via
    # ``object.__setattr__`` because ``MaterialData`` is a slotted dataclass
    # and the field isn't part of its declared schema (yet).
    extras = {
        k: v
        for k, v in payload.items()
        if k
        not in {
            "Name",
            "name",
            "BaseColor",
            "base_color",
            "EmissiveColor",
            "emissive_color",
            "EmissiveIntensity",
            "emissive_intensity",
            "Roughness",
            "roughness",
            "Metalness",
            "Metallic",
            "metallic",
            "Textures",
            "textures",
        }
    }
    if extras:
        # Slotted dataclass — use a plain attr on the instance __dict__
        # surrogate by going through ``__class__.__dict__``-aware dance.
        # ``MaterialData`` has ``__slots__`` declared, so attaching an
        # unknown attribute would raise; route the extras through a
        # weakref-friendly module-level cache keyed by id().
        _STARFIELD_EXTRAS[id(data)] = extras

    return data


#: Module-level extras cache keyed by ``id(MaterialData)``. Slotted dataclasses
#: refuse arbitrary attribute writes; this side-channel keeps the round-trip
#: payload accessible without widening the bridge dataclass's ``__slots__``.
_STARFIELD_EXTRAS: dict[int, dict[str, Any]] = {}


def get_starfield_extras(data: MaterialData) -> dict[str, Any]:
    """Return the round-trip extras dict captured for ``data`` (or empty)."""
    return _STARFIELD_EXTRAS.get(id(data), {})


def load_starfield_material(
    rel_path: str,
    *,
    resolver: ExternalAssetResolver,
    name: str | None = None,
) -> MaterialData:
    """Resolve and parse a Starfield ``.mat`` JSON manifest.

    Raises :class:`StarfieldMaterialError` on any resolution / parse /
    decode failure. Successful loads always return a populated
    :class:`MaterialData` whose ``origin`` is ``"StarfieldMaterial"``.
    """
    if not rel_path:
        raise StarfieldMaterialError("empty material path")
    abs_path = resolver.resolve_material(rel_path)
    if abs_path is None:
        raise StarfieldMaterialError(f"unresolved material path: {rel_path!r}")
    try:
        with Path(abs_path).open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise StarfieldMaterialError(f"failed to read {abs_path}: {exc}") from exc
    return decode_starfield_material(payload, name=name or Path(rel_path).stem)


def starfield_material_textures(data: MaterialData) -> Iterable[tuple[str, str]]:
    """Yield ``(slot, path)`` pairs for every populated texture slot."""
    yield from data.textures.items()
