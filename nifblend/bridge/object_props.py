"""Phase 8a: typed ``PropertyGroup`` on ``bpy.types.Object``.

Records which game produced an imported NIF mesh / armature object, so
sidebar panels (Phase 8d) can self-gate via ``poll()`` without re-reading
the NIF. Mirrors the duck-typed pattern used by
:mod:`nifblend.bridge.material_props` / :mod:`armature_props` /
:mod:`skin_props`.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from typing import Any

import bpy

from nifblend.format.versions import GameProfile

__all__ = [
    "PROP_ATTR",
    "NifBlendObjectProperties",
    "apply_profile_to_object",
    "object_profile",
    "read_profile_from_object",
    "register",
    "unregister",
]


PROP_ATTR = "nifblend"


def _profile_items() -> list[tuple[str, str, str]]:
    return [(p.value, p.value.replace("_", " ").title(), "") for p in GameProfile]


class NifBlendObjectProperties(bpy.types.PropertyGroup):
    """Per-object NIF metadata."""

    game_profile: bpy.props.EnumProperty(  # type: ignore[valid-type]
        name="Game Profile",
        description="Game family this object's source NIF belongs to",
        items=_profile_items(),
        default=GameProfile.UNKNOWN.value,
    )
    nif_version: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="NIF Version",
        description="Packed NIF header version (4 bytes major.minor.patch.sub)",
        default=0,
        subtype="UNSIGNED",
    )
    user_version: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="User Version",
        description="Bethesda user_version field",
        default=0,
        subtype="UNSIGNED",
    )
    bs_version: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="BS Version",
        description="Bethesda bs_version field (BSStream/Header bs_header)",
        default=0,
        subtype="UNSIGNED",
    )
    source_path: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Source Path",
        description="Filesystem path the object was imported from",
        default="",
        subtype="FILE_PATH",
    )
    block_origin: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Block Origin",
        description="Source block-type name (BSTriShape, NiTriShape, NiTriStrips, BSSubIndexTriShape, ...)",
        default="",
    )


_REGISTERED_CLASSES: tuple[type, ...] = (NifBlendObjectProperties,)


def apply_profile_to_object(
    obj: Any,
    *,
    profile: GameProfile,
    nif_version: int = 0,
    user_version: int = 0,
    bs_version: int = 0,
    source_path: str = "",
    block_origin: str = "",
) -> None:
    """Stamp NIF-origin metadata onto ``obj.nifblend``.

    Duck-typed: works against either the real ``PointerProperty`` or any
    attribute-bearing fake (test suite uses ``SimpleNamespace``).
    """
    props = _get_or_create_props(obj)
    if props is None:
        return
    _set_attr(props, "game_profile", profile.value)
    _set_attr(props, "nif_version", int(nif_version))
    _set_attr(props, "user_version", int(user_version))
    _set_attr(props, "bs_version", int(bs_version))
    _set_attr(props, "source_path", str(source_path))
    _set_attr(props, "block_origin", str(block_origin))


def read_profile_from_object(obj: Any) -> GameProfile:
    """Return the :class:`GameProfile` stamped on ``obj``, or ``UNKNOWN``."""
    props = getattr(obj, PROP_ATTR, None)
    if props is None:
        return GameProfile.UNKNOWN
    raw = getattr(props, "game_profile", GameProfile.UNKNOWN.value)
    try:
        return GameProfile(str(raw))
    except ValueError:
        return GameProfile.UNKNOWN


def object_profile(obj: Any | None) -> GameProfile:
    """Convenience wrapper: ``UNKNOWN`` when ``obj`` is ``None``."""
    if obj is None:
        return GameProfile.UNKNOWN
    return read_profile_from_object(obj)


def register() -> None:
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.nifblend = bpy.props.PointerProperty(
        type=NifBlendObjectProperties,
        name="NifBlend",
        description="NIF-origin metadata preserved across import/export",
    )


def unregister() -> None:
    if hasattr(bpy.types.Object, "nifblend"):
        with contextlib.suppress(AttributeError, TypeError):
            del bpy.types.Object.nifblend
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)


def _get_or_create_props(obj: Any) -> Any:
    props = getattr(obj, PROP_ATTR, None)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace()
        setattr(obj, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _set_attr(props: Any, name: str, value: Any) -> None:
    with contextlib.suppress(AttributeError, TypeError):
        setattr(props, name, value)
