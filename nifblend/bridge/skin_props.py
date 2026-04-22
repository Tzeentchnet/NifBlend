"""Phase 4 step 17: typed ``PropertyGroup`` on ``bpy.types.VertexGroup``.

Stores the per-partition ``BodyPartList(part_flag, body_part)`` pair from a
:class:`~nifblend.format.generated.blocks.BSDismemberSkinInstance` so the
partition layout survives a NifBlend *import → edit → export* round-trip.

Bethesda dismember skin instances pair the GPU-skinning partition layout
(produced by :mod:`nifblend.bridge.armature_out`) with a parallel list of
``BodyPartList`` records that name the body part each partition represents
(``BSDismemberBodyPartType``) plus a 16-bit ``part_flag`` (``BSPartFlag`` in
the schema -- editor flags + per-partition ``StartNetBoneSet`` shorts on
SSE / FO4). Blender has no native concept of these, so the convention --
shared with ``blender_niftools_addon`` -- is to model partition membership
as additional vertex groups (one group per partition, holding the
partition's vertices). This module attaches the ``(part_flag, body_part)``
pair to those groups via a typed PropertyGroup so the operator can
re-derive the source ``BSDismemberSkinInstance.partitions`` list on
export.

The module mirrors :mod:`nifblend.bridge.armature_props` /
:mod:`nifblend.bridge.material_props`:

* :class:`NifBlendVertexGroupProperties` -- the registered
  ``PropertyGroup``.
* :func:`apply_partition_to_props` / :func:`read_partition_from_props` --
  duck-typed helpers that work against either a real
  ``PointerProperty``-backed PropertyGroup or any attribute-bearing fake
  (the test suite uses ``SimpleNamespace``).
* :func:`bodypart_lists_to_vertex_groups` /
  :func:`vertex_groups_to_bodypart_lists` -- end-to-end converters
  between the codegen-emitted
  :class:`~nifblend.format.generated.structs.BodyPartList` list and a
  ``{vertex_group_name: vertex_group}`` mapping.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable, Mapping
from types import SimpleNamespace
from typing import Any

import bpy

from nifblend.format.generated.structs import BodyPartList

__all__ = [
    "PROP_ATTR",
    "NifBlendVertexGroupProperties",
    "apply_partition_to_props",
    "bodypart_lists_to_vertex_groups",
    "clear_partition_on_props",
    "read_partition_from_props",
    "register",
    "unregister",
    "vertex_groups_to_bodypart_lists",
]


#: Attribute name on ``bpy.types.VertexGroup`` that carries the PropertyGroup.
PROP_ATTR = "nifblend"


class NifBlendVertexGroupProperties(bpy.types.PropertyGroup):
    """NIF-only vertex-group state attached to ``bpy.types.VertexGroup.nifblend``.

    ``is_partition`` distinguishes a bone-weight vertex group (the
    default, produced by :mod:`nifblend.bridge.skin_in`) from a
    dismember-partition vertex group. ``part_flag`` and ``body_part``
    are the verbatim u16 fields from the source
    :class:`BodyPartList` -- preserved as raw ints so unknown
    ``BSDismemberBodyPartType`` values (modder-defined parts past the
    enum) survive the round-trip without being clamped.
    """

    is_partition: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Is Dismember Partition",
        description=(
            "True when this vertex group represents a "
            "BSDismemberSkinInstance partition (rather than a bone weight)."
        ),
        default=False,
    )
    part_flag: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Part Flag",
        description=(
            "BSPartFlag bitfield from the source BodyPartList "
            "(editor flags + StartNetBoneSet shorts on SSE/FO4)"
        ),
        default=0,
        min=0,
        max=0xFFFF,
        subtype="UNSIGNED",
    )
    body_part: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Body Part",
        description=(
            "BSDismemberBodyPartType value naming the body part this "
            "partition represents (preserved as a raw int)"
        ),
        default=0,
        min=0,
        max=0xFFFF,
        subtype="UNSIGNED",
    )


_REGISTERED_CLASSES: tuple[type, ...] = (NifBlendVertexGroupProperties,)


# ---- duck-typed helpers --------------------------------------------------


def apply_partition_to_props(
    vgroup: Any,
    *,
    part_flag: int,
    body_part: int,
) -> None:
    """Stamp ``(part_flag, body_part)`` onto ``vgroup.nifblend``.

    Marks the group as a dismember partition (``is_partition=True``).
    No-op when neither the real PropertyGroup nor a writable fallback
    attribute is reachable on ``vgroup``.
    """
    props = _get_or_create_props(vgroup)
    if props is None:
        return
    _set_attr(props, "is_partition", True)
    _set_attr(props, "part_flag", int(part_flag) & 0xFFFF)
    _set_attr(props, "body_part", int(body_part) & 0xFFFF)


def read_partition_from_props(vgroup: Any) -> tuple[int, int] | None:
    """Return ``(part_flag, body_part)`` for a partition group, or ``None``.

    Returns ``None`` for groups that aren't marked as partitions (the
    default state for bone-weight groups produced by
    :func:`nifblend.bridge.skin_in.apply_skin_to_object`).
    """
    props = getattr(vgroup, PROP_ATTR, None)
    if props is None:
        return None
    if not getattr(props, "is_partition", False):
        return None
    part_flag = getattr(props, "part_flag", 0)
    body_part = getattr(props, "body_part", 0)
    try:
        return int(part_flag) & 0xFFFF, int(body_part) & 0xFFFF
    except (TypeError, ValueError):
        return None


def clear_partition_on_props(vgroup: Any) -> None:
    """Reset ``vgroup.nifblend`` to the non-partition default."""
    props = getattr(vgroup, PROP_ATTR, None)
    if props is None:
        return
    _set_attr(props, "is_partition", False)
    _set_attr(props, "part_flag", 0)
    _set_attr(props, "body_part", 0)


# ---- end-to-end converters ----------------------------------------------


def bodypart_lists_to_vertex_groups(
    partitions: Iterable[BodyPartList | None],
    obj: Any,
    *,
    name_prefix: str = "BP",
) -> dict[str, Any]:
    """Create one vertex group per :class:`BodyPartList` entry.

    Returns a ``{group_name: vertex_group}`` dict in the same order as
    ``partitions``. Each created group is stamped with the matching
    ``(part_flag, body_part)`` via :func:`apply_partition_to_props`.

    The group naming convention -- ``"{name_prefix}_{i}_{body_part}"``
    -- mirrors what ``blender_niftools_addon`` uses (``SBP_30_HEAD``
    style); we keep it numeric so unknown body-part IDs don't collide
    with the codegen :class:`BSDismemberBodyPartType` enum names.
    """
    out: dict[str, Any] = {}
    for i, part in enumerate(partitions):
        if part is None:
            continue
        body_part = int(getattr(part, "body_part", 0)) & 0xFFFF
        part_flag = int(getattr(part, "part_flag", 0)) & 0xFFFF
        name = f"{name_prefix}_{i}_{body_part}"
        group = obj.vertex_groups.new(name=name)
        apply_partition_to_props(group, part_flag=part_flag, body_part=body_part)
        out[name] = group
    return out


def vertex_groups_to_bodypart_lists(
    groups: Iterable[Any] | Mapping[str, Any],
) -> list[BodyPartList]:
    """Harvest :class:`BodyPartList` records from partition vertex groups.

    Walks ``groups`` (any iterable of vertex-group-shaped objects, or a
    name-keyed mapping) and emits one :class:`BodyPartList` per group
    that :func:`read_partition_from_props` recognises. Bone-weight
    groups (the default state) are silently skipped, so the operator
    can pass ``obj.vertex_groups`` directly.
    """
    iterable: Iterable[Any]
    iterable = groups.values() if isinstance(groups, Mapping) else groups
    out: list[BodyPartList] = []
    for vg in iterable:
        pair = read_partition_from_props(vg)
        if pair is None:
            continue
        part_flag, body_part = pair
        out.append(BodyPartList(part_flag=part_flag, body_part=body_part))
    return out


# ---- registration --------------------------------------------------------


def register() -> None:
    """Register the PropertyGroup and attach the PointerProperty."""
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.VertexGroup.nifblend = bpy.props.PointerProperty(
        type=NifBlendVertexGroupProperties,
        name="NifBlend",
        description="NIF-only vertex-group state preserved across import/export",
    )


def unregister() -> None:
    """Inverse of :func:`register`. Tolerant of partial registration."""
    if hasattr(bpy.types.VertexGroup, "nifblend"):
        with contextlib.suppress(AttributeError, TypeError):
            del bpy.types.VertexGroup.nifblend
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)


# ---- private -------------------------------------------------------------


def _get_or_create_props(vgroup: Any) -> Any:
    props = getattr(vgroup, PROP_ATTR, None)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace()
        setattr(vgroup, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _set_attr(props: Any, name: str, value: Any) -> None:
    with contextlib.suppress(AttributeError, TypeError):
        setattr(props, name, value)
