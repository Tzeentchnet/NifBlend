"""Phase 10 step 10c: typed ``PropertyGroup`` on ``bpy.types.Action`` and
``bpy.types.PoseBone``.

KF import (Phase 5) loses sequence-level
:class:`~nifblend.format.generated.blocks.NiControllerSequence` metadata
(``weight`` / ``frequency`` / ``cycle_type`` / ``start_time`` /
``stop_time`` / ``accum_root_name`` / ``accum_flags`` / ``phase`` /
``play_backwards``) and per-bone
:class:`~nifblend.format.generated.structs.ControlledBlock` metadata
(``priority`` / ``controller_type`` / ``controller_id`` /
``interpolator_id`` / ``property_type``) plus the
:class:`~nifblend.format.generated.blocks.NiTextKeyExtraData` text-key
list, because Blender's ``Action`` / ``PoseBone`` only model fcurve
data. This module attaches the missing state to two new typed
PropertyGroups so a NifBlend Action can round-trip through *import →
edit → export* without dropping the sequence shell.

The module mirrors :mod:`nifblend.bridge.material_props` /
:mod:`nifblend.bridge.skin_props` / :mod:`nifblend.bridge.armature_props`:

* :class:`NifBlendActionTextKey`,
  :class:`NifBlendActionProperties`,
  :class:`NifBlendPoseBoneProperties` -- the registered
  ``PropertyGroup`` classes.
* Duck-typed ``apply_*`` / ``read_*`` helpers mirroring the Phase 3.13
  / 4.14 / 4.17 PropertyGroup pattern -- they work against either a
  real ``PointerProperty``-backed PropertyGroup or any
  attribute-bearing fake (the test suite uses ``SimpleNamespace``).

Registration is wired by :func:`register` / :func:`unregister`, called
from the addon entry point. The ``bpy.types.Action.nifblend`` and
``bpy.types.PoseBone.nifblend`` PointerProperties are the public
surface -- everything else is an internal storage detail.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import bpy

from nifblend.format.generated.enums import CycleType

__all__ = [
    "ACTION_FIELDS",
    "CYCLE_TYPE_ITEMS",
    "POSE_BONE_FIELDS",
    "PROP_ATTR",
    "NifBlendActionProperties",
    "NifBlendActionTextKey",
    "NifBlendPoseBoneProperties",
    "apply_controlled_block_to_pose_bone",
    "apply_sequence_metadata_to_action",
    "apply_text_keys_to_action",
    "clear_controlled_block_on_pose_bone",
    "clear_sequence_metadata_on_action",
    "read_controlled_block_from_pose_bone",
    "read_sequence_metadata_from_action",
    "read_text_keys_from_action",
    "register",
    "unregister",
]


#: Attribute name on ``bpy.types.Action`` / ``bpy.types.PoseBone`` that
#: carries the PropertyGroup. Same identifier used by every other
#: ``*_props`` module so the sidebar can reach them uniformly.
PROP_ATTR = "nifblend"


#: ``EnumProperty`` items for :attr:`NifBlendActionProperties.cycle_type`,
#: derived from :class:`CycleType`. Stored as a stringified int so the
#: raw value survives even if the enum gains entries upstream.
CYCLE_TYPE_ITEMS: tuple[tuple[str, str, str], ...] = tuple(
    (str(int(member)), member.name, member.name)
    for member in CycleType
)


# Field tables driving the apply/read helpers. Keeping them as plain
# tuples (rather than introspecting the PropertyGroup) means the helpers
# work just as well against a SimpleNamespace fake in unit tests.
ACTION_FIELDS: dict[str, tuple[str, ...]] = {
    "float": (
        "weight",
        "frequency",
        "start_time",
        "stop_time",
        "phase",
    ),
    "int": (
        "accum_flags",
    ),
    "str": (
        "accum_root_name",
    ),
    "bool": (
        "play_backwards",
    ),
}

POSE_BONE_FIELDS: dict[str, tuple[str, ...]] = {
    "int": (
        "priority",
    ),
    "str": (
        "controller_type",
        "controller_id",
        "interpolator_id",
        "property_type",
    ),
}


# ---- PropertyGroup classes -----------------------------------------------


class NifBlendActionTextKey(bpy.types.PropertyGroup):
    """One row in :attr:`NifBlendActionProperties.text_keys`.

    Mirrors :class:`~nifblend.format.generated.structs.TextKey`:
    ``time`` is in NIF seconds (not Blender frames); ``name`` is the
    raw text-key string (typically ``"start"`` / ``"end"`` / Bethesda
    annotation tokens like ``"hit"``).
    """

    time: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Time",
        description="Text-key time in NIF seconds (not Blender frames)",
        default=0.0,
    )
    name: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Name",
        description="Text-key string (e.g. start / end / hit)",
        default="",
    )


class NifBlendActionProperties(bpy.types.PropertyGroup):
    """NIF-only sequence state attached to ``bpy.types.Action.nifblend``.

    Stores the verbatim
    :class:`~nifblend.format.generated.blocks.NiControllerSequence`
    metadata that Blender's ``Action`` can't represent natively, plus
    the resolved
    :class:`~nifblend.format.generated.blocks.NiTextKeyExtraData` text
    keys. Defaults match the Phase 10 export contract:
    ``cycle_type=CYCLE_CLAMP``, ``frequency=1.0``, ``weight=1.0``.
    """

    weight: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Weight",
        description="NiControllerSequence.weight (sequence blend weight)",
        default=1.0,
    )
    frequency: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Frequency",
        description="NiControllerSequence.frequency (playback rate multiplier)",
        default=1.0,
    )
    start_time: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Start Time",
        description="NiControllerSequence.start_time in NIF seconds",
        default=0.0,
    )
    stop_time: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Stop Time",
        description="NiControllerSequence.stop_time in NIF seconds",
        default=0.0,
    )
    cycle_type: bpy.props.EnumProperty(  # type: ignore[valid-type]
        name="Cycle Type",
        description="NiControllerSequence.cycle_type (loop / reverse / clamp)",
        items=CYCLE_TYPE_ITEMS,
        default=str(int(CycleType.CYCLE_CLAMP)),
    )
    accum_root_name: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Accum Root Name",
        description="NiControllerSequence.accum_root_name (root-motion bone)",
        default="",
    )
    accum_flags: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Accum Flags",
        description="NiControllerSequence.accum_flags (root-motion accumulation bitfield)",
        default=0,
        min=0,
        subtype="UNSIGNED",
    )
    phase: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Phase",
        description="NiControllerSequence.phase (deprecated, preserved verbatim)",
        default=0.0,
    )
    play_backwards: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Play Backwards",
        description="NiControllerSequence flag bit -- play the sequence in reverse",
        default=False,
    )
    text_keys: bpy.props.CollectionProperty(  # type: ignore[valid-type]
        name="Text Keys",
        description="Resolved NiTextKeyExtraData entries (time, name pairs)",
        type=NifBlendActionTextKey,
    )


class NifBlendPoseBoneProperties(bpy.types.PropertyGroup):
    """NIF-only ControlledBlock state attached to ``bpy.types.PoseBone.nifblend``.

    Stores the verbatim
    :class:`~nifblend.format.generated.structs.ControlledBlock` metadata
    that doesn't survive the conversion to Blender fcurves: the u8
    ``priority`` plus the four string refs (``controller_type`` /
    ``controller_id`` / ``interpolator_id`` / ``property_type``) used to
    re-emit the ControlledBlock on export.
    """

    priority: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Priority",
        description="ControlledBlock.priority (u8, blend tier)",
        default=0,
        min=0,
        max=255,
        subtype="UNSIGNED",
    )
    controller_type: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Controller Type",
        description="ControlledBlock.controller_type (e.g. NiTransformController)",
        default="",
    )
    controller_id: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Controller ID",
        description="ControlledBlock.controller_id (target node identifier)",
        default="",
    )
    interpolator_id: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Interpolator ID",
        description="ControlledBlock.interpolator_id",
        default="",
    )
    property_type: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Property Type",
        description="ControlledBlock.property_type",
        default="",
    )


_REGISTERED_CLASSES: tuple[type, ...] = (
    NifBlendActionTextKey,
    NifBlendActionProperties,
    NifBlendPoseBoneProperties,
)


# ---- duck-typed helpers --------------------------------------------------


def apply_sequence_metadata_to_action(
    action: Any,
    *,
    weight: float = 1.0,
    frequency: float = 1.0,
    start_time: float = 0.0,
    stop_time: float = 0.0,
    cycle_type: int = int(CycleType.CYCLE_CLAMP),
    accum_root_name: str = "",
    accum_flags: int = 0,
    phase: float = 0.0,
    play_backwards: bool = False,
) -> None:
    """Stamp NiControllerSequence metadata onto ``action.nifblend``.

    No-op when neither the real PropertyGroup nor a writable fallback
    attribute is reachable on ``action``.
    """
    props = _get_or_create_props(action)
    if props is None:
        return
    _set_attr(props, "weight", float(weight))
    _set_attr(props, "frequency", float(frequency))
    _set_attr(props, "start_time", float(start_time))
    _set_attr(props, "stop_time", float(stop_time))
    _set_attr(props, "cycle_type", _cycle_type_to_enum(cycle_type))
    _set_attr(props, "accum_root_name", str(accum_root_name or ""))
    _set_attr(props, "accum_flags", int(accum_flags) & 0xFFFFFFFF)
    _set_attr(props, "phase", float(phase))
    _set_attr(props, "play_backwards", bool(play_backwards))


def read_sequence_metadata_from_action(action: Any) -> dict[str, Any] | None:
    """Return the stamped NiControllerSequence metadata, or ``None``.

    Returns ``None`` when no PropertyGroup is attached -- callers fall
    back to defaults (e.g. action ``frame_range`` for ``stop_time``).
    """
    props = getattr(action, PROP_ATTR, None)
    if props is None:
        return None
    return {
        "weight": float(getattr(props, "weight", 1.0)),
        "frequency": float(getattr(props, "frequency", 1.0)),
        "start_time": float(getattr(props, "start_time", 0.0)),
        "stop_time": float(getattr(props, "stop_time", 0.0)),
        "cycle_type": _cycle_type_from_enum(
            getattr(props, "cycle_type", str(int(CycleType.CYCLE_CLAMP)))
        ),
        "accum_root_name": str(getattr(props, "accum_root_name", "") or ""),
        "accum_flags": int(getattr(props, "accum_flags", 0)) & 0xFFFFFFFF,
        "phase": float(getattr(props, "phase", 0.0)),
        "play_backwards": bool(getattr(props, "play_backwards", False)),
    }


def clear_sequence_metadata_on_action(action: Any) -> None:
    """Reset ``action.nifblend`` to the Phase 10 default contract."""
    apply_sequence_metadata_to_action(action)
    props = getattr(action, PROP_ATTR, None)
    if props is None:
        return
    _clear_collection(getattr(props, "text_keys", None))


def apply_text_keys_to_action(
    action: Any,
    text_keys: Iterable[tuple[float, str]],
) -> None:
    """Replace ``action.nifblend.text_keys`` with the supplied entries.

    ``text_keys`` is an iterable of ``(time, name)`` pairs in NIF
    seconds. The collection is cleared first so duplicate stamps don't
    accumulate.
    """
    props = _get_or_create_props(action)
    if props is None:
        return
    _write_text_keys(props, text_keys)


def read_text_keys_from_action(action: Any) -> list[tuple[float, str]]:
    """Return ``[(time, name), …]`` from the Action PropertyGroup, or ``[]``."""
    props = getattr(action, PROP_ATTR, None)
    if props is None:
        return []
    return _read_text_keys(props)


def apply_controlled_block_to_pose_bone(
    pose_bone: Any,
    *,
    priority: int = 0,
    controller_type: str = "",
    controller_id: str = "",
    interpolator_id: str = "",
    property_type: str = "",
) -> None:
    """Stamp ControlledBlock metadata onto ``pose_bone.nifblend``."""
    props = _get_or_create_props(pose_bone)
    if props is None:
        return
    _set_attr(props, "priority", int(priority) & 0xFF)
    _set_attr(props, "controller_type", str(controller_type or ""))
    _set_attr(props, "controller_id", str(controller_id or ""))
    _set_attr(props, "interpolator_id", str(interpolator_id or ""))
    _set_attr(props, "property_type", str(property_type or ""))


def read_controlled_block_from_pose_bone(pose_bone: Any) -> dict[str, Any] | None:
    """Return ControlledBlock metadata stamped on ``pose_bone.nifblend``.

    Returns ``None`` only when no PropertyGroup is attached at all;
    returns the default-shaped dict (zero priority, empty strings) when
    the group exists but was never stamped, so callers can decide
    whether to emit a zeroed ControlledBlock or skip the bone entirely.
    """
    props = getattr(pose_bone, PROP_ATTR, None)
    if props is None:
        return None
    return {
        "priority": int(getattr(props, "priority", 0)) & 0xFF,
        "controller_type": str(getattr(props, "controller_type", "") or ""),
        "controller_id": str(getattr(props, "controller_id", "") or ""),
        "interpolator_id": str(getattr(props, "interpolator_id", "") or ""),
        "property_type": str(getattr(props, "property_type", "") or ""),
    }


def clear_controlled_block_on_pose_bone(pose_bone: Any) -> None:
    """Reset ``pose_bone.nifblend`` to its zeroed default."""
    apply_controlled_block_to_pose_bone(pose_bone)


# ---- registration --------------------------------------------------------


def register() -> None:
    """Register the PropertyGroup classes and attach the PointerProperties."""
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Action.nifblend = bpy.props.PointerProperty(
        type=NifBlendActionProperties,
        name="NifBlend",
        description="NIF-only sequence state preserved across import/export",
    )
    bpy.types.PoseBone.nifblend = bpy.props.PointerProperty(
        type=NifBlendPoseBoneProperties,
        name="NifBlend",
        description="NIF-only ControlledBlock state preserved across import/export",
    )


def unregister() -> None:
    """Inverse of :func:`register`. Tolerant of partial registration."""
    for owner in (bpy.types.PoseBone, bpy.types.Action):
        if hasattr(owner, "nifblend"):
            with contextlib.suppress(AttributeError, TypeError):
                del owner.nifblend
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)


# ---- private -------------------------------------------------------------


def _get_or_create_props(owner: Any) -> Any:
    """Return ``owner.nifblend`` or, in tests, attach a SimpleNamespace.

    In real Blender the PointerProperty is auto-created on first access
    and can't be reassigned, so the ``getattr`` branch always wins.
    """
    props = getattr(owner, PROP_ATTR, None)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace()
        setattr(owner, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _set_attr(props: Any, name: str, value: Any) -> None:
    with contextlib.suppress(AttributeError, TypeError):
        setattr(props, name, value)


def _cycle_type_to_enum(value: int | str) -> str:
    """Coerce a raw :class:`CycleType` int (or already-stringified one) to the EnumProperty key."""
    try:
        as_int = int(value)
    except (TypeError, ValueError):
        return str(int(CycleType.CYCLE_CLAMP))
    # Round-trip unknown values through the stringified int so future
    # CycleType extensions don't get clamped.
    return str(as_int)


def _cycle_type_from_enum(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(CycleType.CYCLE_CLAMP)


def _write_text_keys(props: Any, text_keys: Iterable[tuple[float, str]]) -> None:
    coll = getattr(props, "text_keys", None)
    pairs = [(float(t), str(n or "")) for t, n in text_keys]
    if coll is None:
        with contextlib.suppress(AttributeError, TypeError):
            props.text_keys = [SimpleNamespace(time=t, name=n) for t, n in pairs]
        return
    if isinstance(coll, list):
        coll.clear()
        coll.extend(SimpleNamespace(time=t, name=n) for t, n in pairs)
        return
    clear = getattr(coll, "clear", None)
    if clear is not None:
        clear()
    add = getattr(coll, "add", None)
    if add is None:
        with contextlib.suppress(AttributeError, TypeError):
            props.text_keys = [SimpleNamespace(time=t, name=n) for t, n in pairs]
        return
    for time, name in pairs:
        item = add()
        with contextlib.suppress(AttributeError, TypeError):
            item.time = time
            item.name = name


def _read_text_keys(props: Any) -> list[tuple[float, str]]:
    coll = getattr(props, "text_keys", None)
    if coll is None:
        return []
    out: list[tuple[float, str]] = []
    try:
        for item in coll:
            time = getattr(item, "time", None)
            name = getattr(item, "name", None)
            if time is None or name is None:
                continue
            out.append((float(time), str(name)))
    except TypeError:
        return []
    return out


def _clear_collection(coll: Any) -> None:
    if coll is None:
        return
    clear = getattr(coll, "clear", None)
    if clear is not None:
        with contextlib.suppress(TypeError):
            clear()
