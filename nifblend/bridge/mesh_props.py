"""Phase 8g: typed ``PropertyGroup`` on ``bpy.types.Mesh`` for game-specific metadata.

Hosts two sidecars the core BSTriShape PropertyGroup (material / bone /
vertex-group layers) doesn't cover:

* :class:`NifBlendMeshSegment` -- one FO4 ``BSGeometrySegmentData`` row.
* :class:`NifBlendFO76MeshSlot` -- one of four FO76 ``BSMeshArray`` LOD slots.

The container :class:`NifBlendMeshProperties` is registered as
``bpy.types.Mesh.nifblend_shape``; the attribute name deliberately
differs from the per-object ``bpy.types.Object.nifblend`` pointer from
:mod:`nifblend.bridge.object_props` so sidebar draw code can dereference
each without ambiguity.

As with the other NifBlend PropertyGroups, every helper here is
duck-typed so unit tests can exercise the round-trip against a plain
``SimpleNamespace`` fake without a live Blender.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from typing import Any

import bpy

from nifblend.bridge.games.fallout import (
    FO76_MESH_SLOT_COUNT,
    ExternalMeshLink,
)
from nifblend.bridge.mesh_in import (
    BSGeometryMeshRef,
    MeshSegment,
    MeshSegments,
    MeshSubSegment,
)

__all__ = [
    "PROP_ATTR",
    "NifBlendFO76MeshSlot",
    "NifBlendMeshProperties",
    "NifBlendMeshSegment",
    "NifBlendMeshSubSegment",
    "apply_fo76_slots_to_mesh",
    "apply_segments_to_mesh",
    "read_fo76_slots_from_mesh",
    "read_segments_from_mesh",
    "register",
    "unregister",
]


PROP_ATTR = "nifblend_shape"


class NifBlendMeshSubSegment(bpy.types.PropertyGroup):
    """One ``BSGeometrySubSegment`` row."""

    start_index: bpy.props.IntProperty(name="Start Index", default=0)  # type: ignore[valid-type]
    num_primitives: bpy.props.IntProperty(name="Num Primitives", default=0)  # type: ignore[valid-type]
    parent_array_index: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Parent Segment", default=0
    )
    unused: bpy.props.IntProperty(name="Unused", default=0)  # type: ignore[valid-type]


class NifBlendMeshSegment(bpy.types.PropertyGroup):
    """One ``BSGeometrySegmentData`` row."""

    start_index: bpy.props.IntProperty(name="Start Index", default=0)  # type: ignore[valid-type]
    num_primitives: bpy.props.IntProperty(name="Num Primitives", default=0)  # type: ignore[valid-type]
    parent_array_index: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Parent", default=0xFFFFFFFF
    )
    sub_segments: bpy.props.CollectionProperty(  # type: ignore[valid-type]
        name="Sub-Segments", type=NifBlendMeshSubSegment
    )


class NifBlendFO76MeshSlot(bpy.types.PropertyGroup):
    """One FO76 ``BSMeshArray`` LOD slot."""

    lod_index: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="LOD Index",
        default=0,
        min=0,
        max=FO76_MESH_SLOT_COUNT - 1,
    )
    has_mesh: bpy.props.BoolProperty(name="Has Mesh", default=False)  # type: ignore[valid-type]
    mesh_path: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Mesh Path",
        description="Path to the external .mesh file (FO76)",
        default="",
        subtype="FILE_PATH",
    )
    num_verts: bpy.props.IntProperty(name="Num Verts", default=0)  # type: ignore[valid-type]
    indices_size: bpy.props.IntProperty(name="Indices Size", default=0)  # type: ignore[valid-type]
    flags: bpy.props.IntProperty(name="Flags", default=0, subtype="UNSIGNED")  # type: ignore[valid-type]


class NifBlendMeshProperties(bpy.types.PropertyGroup):
    """Mesh-level NIF sidecar metadata (segments + FO76 slots)."""

    segments: bpy.props.CollectionProperty(  # type: ignore[valid-type]
        name="FO4 Segments",
        type=NifBlendMeshSegment,
    )
    num_primitives: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Num Primitives",
        description="Total indices covered by segments (num_triangles * 3)",
        default=0,
    )
    ssf_file: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="SSF File",
        description="BSGeometrySegmentSharedData.ssf_file (FO4)",
        default="",
    )
    fo76_slots: bpy.props.CollectionProperty(  # type: ignore[valid-type]
        name="FO76 Mesh Slots",
        type=NifBlendFO76MeshSlot,
    )


_REGISTERED_CLASSES: tuple[type, ...] = (
    NifBlendMeshSubSegment,
    NifBlendMeshSegment,
    NifBlendFO76MeshSlot,
    NifBlendMeshProperties,
)


# ---- duck-typed helpers --------------------------------------------------


def _get_or_create_props(mesh: Any) -> Any:
    props = getattr(mesh, PROP_ATTR, None)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace(
            segments=[],
            num_primitives=0,
            ssf_file="",
            fo76_slots=[],
        )
        setattr(mesh, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _clear_collection(collection: Any) -> None:
    """Empty ``collection`` whether it's a real CollectionProperty or a list."""
    if hasattr(collection, "clear"):
        with contextlib.suppress(TypeError):
            collection.clear()
            return
    if isinstance(collection, list):
        del collection[:]


def _add_row(collection: Any) -> Any:
    """Append an empty row and return it, handling both real + fake collections."""
    if hasattr(collection, "add") and callable(collection.add):
        try:
            return collection.add()
        except TypeError:
            pass
    row = SimpleNamespace()
    if isinstance(collection, list):
        collection.append(row)
    return row


def apply_segments_to_mesh(mesh: Any, segments: MeshSegments | None) -> None:
    """Stamp :class:`MeshSegments` onto ``mesh.nifblend_shape``."""
    props = _get_or_create_props(mesh)
    if props is None:
        return
    _clear_collection(props.segments)
    if segments is None:
        with contextlib.suppress(AttributeError, TypeError):
            props.num_primitives = 0
            props.ssf_file = ""
        return
    with contextlib.suppress(AttributeError, TypeError):
        props.num_primitives = int(segments.num_primitives)
        props.ssf_file = str(segments.ssf_file)
    for seg in segments.segments:
        row = _add_row(props.segments)
        with contextlib.suppress(AttributeError, TypeError):
            row.start_index = int(seg.start_index)
            row.num_primitives = int(seg.num_primitives)
            row.parent_array_index = int(seg.parent_array_index)
        if not hasattr(row, "sub_segments"):
            row.sub_segments = []
        _clear_collection(row.sub_segments)
        for sub in seg.sub_segments or ():
            sub_row = _add_row(row.sub_segments)
            with contextlib.suppress(AttributeError, TypeError):
                sub_row.start_index = int(sub.start_index)
                sub_row.num_primitives = int(sub.num_primitives)
                sub_row.parent_array_index = int(sub.parent_array_index)
                sub_row.unused = int(sub.unused)


def read_segments_from_mesh(mesh: Any) -> MeshSegments | None:
    """Inverse of :func:`apply_segments_to_mesh`. ``None`` when empty."""
    props = getattr(mesh, PROP_ATTR, None)
    if props is None:
        return None
    rows = list(getattr(props, "segments", []) or [])
    if not rows:
        return None
    segments: list[MeshSegment] = []
    for row in rows:
        subs: list[MeshSubSegment] = []
        for sub in getattr(row, "sub_segments", []) or []:
            subs.append(
                MeshSubSegment(
                    start_index=int(getattr(sub, "start_index", 0)),
                    num_primitives=int(getattr(sub, "num_primitives", 0)),
                    parent_array_index=int(getattr(sub, "parent_array_index", 0)),
                    unused=int(getattr(sub, "unused", 0)),
                )
            )
        segments.append(
            MeshSegment(
                start_index=int(getattr(row, "start_index", 0)),
                num_primitives=int(getattr(row, "num_primitives", 0)),
                parent_array_index=int(
                    getattr(row, "parent_array_index", 0xFFFFFFFF)
                ),
                sub_segments=subs,
            )
        )
    return MeshSegments(
        num_primitives=int(getattr(props, "num_primitives", 0)),
        total_segments=len(segments),
        segments=segments,
        ssf_file=str(getattr(props, "ssf_file", "") or ""),
        per_segment_user_indices=[],
    )


def apply_fo76_slots_to_mesh(mesh: Any, slots: list[BSGeometryMeshRef]) -> None:
    """Stamp the four FO76 LOD slots onto ``mesh.nifblend_shape.fo76_slots``."""
    props = _get_or_create_props(mesh)
    if props is None:
        return
    _clear_collection(props.fo76_slots)
    for slot in slots:
        row = _add_row(props.fo76_slots)
        with contextlib.suppress(AttributeError, TypeError):
            row.lod_index = int(slot.lod_index)
            row.has_mesh = bool(slot.has_mesh)
            row.mesh_path = str(slot.mesh_path)
            row.num_verts = int(slot.num_verts)
            row.indices_size = int(slot.indices_size)
            row.flags = int(slot.flags)


def read_fo76_slots_from_mesh(mesh: Any) -> list[ExternalMeshLink]:
    """Return only the *populated* FO76 slots as :class:`ExternalMeshLink`."""
    props = getattr(mesh, PROP_ATTR, None)
    if props is None:
        return []
    out: list[ExternalMeshLink] = []
    for row in getattr(props, "fo76_slots", []) or []:
        if not bool(getattr(row, "has_mesh", False)):
            continue
        path = str(getattr(row, "mesh_path", "") or "")
        if not path:
            continue
        out.append(
            ExternalMeshLink(
                lod_index=int(getattr(row, "lod_index", 0)),
                mesh_path=path,
                num_verts=int(getattr(row, "num_verts", 0)),
                indices_size=int(getattr(row, "indices_size", 0)),
                flags=int(getattr(row, "flags", 0)),
            )
        )
    return out


def register() -> None:
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Mesh.nifblend_shape = bpy.props.PointerProperty(
        type=NifBlendMeshProperties,
        name="NifBlend Shape",
        description="NIF-only per-shape metadata (FO4 segments, FO76 mesh slots)",
    )


def unregister() -> None:
    if hasattr(bpy.types.Mesh, "nifblend_shape"):
        with contextlib.suppress(AttributeError, TypeError):
            del bpy.types.Mesh.nifblend_shape
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)
