"""Phase 8g: Fallout 4 / 76 operators.

Thin Blender wrappers around the pure helpers in
:mod:`nifblend.bridge.games.fallout` and the mesh PropertyGroup in
:mod:`nifblend.bridge.mesh_props`.

Operators:

* ``nifblend.fo4_promote_to_subindex`` -- stamp the active mesh with a
  minimum single-segment sidecar and flip ``block_origin`` so the
  export path emits a ``BSSubIndexTriShape``.
* ``nifblend.fo4_add_segment`` / ``nifblend.fo4_remove_segment`` --
  drive the segment UIList in the sidebar.
* ``nifblend.fo76_set_external_mesh`` -- populate one FO76 LOD slot.
* ``nifblend.fo76_clear_external_mesh`` -- empty one FO76 LOD slot.
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from nifblend.bridge.games.fallout import (
    FO76_MESH_SLOT_COUNT,
    promote_triangles_to_segments,
)
from nifblend.bridge.mesh_props import apply_segments_to_mesh
from nifblend.bridge.object_props import (
    apply_profile_to_object,
    read_profile_from_object,
)
from nifblend.format.versions import GameProfile

__all__ = [
    "NIFBLEND_OT_fo4_add_segment",
    "NIFBLEND_OT_fo4_promote_to_subindex",
    "NIFBLEND_OT_fo4_remove_segment",
    "NIFBLEND_OT_fo76_clear_external_mesh",
    "NIFBLEND_OT_fo76_set_external_mesh",
]


_FO4_PROFILES = {GameProfile.FALLOUT_4}
_FO76_PROFILES = {GameProfile.FALLOUT_76}


def _active_mesh(context: bpy.types.Context) -> bpy.types.Object | None:
    obj = context.active_object
    if obj is None or getattr(obj, "type", "") != "MESH":
        return None
    return obj


class NIFBLEND_OT_fo4_promote_to_subindex(Operator):
    """Add a minimum segment sidecar so the export path emits ``BSSubIndexTriShape``."""

    bl_idname = "nifblend.fo4_promote_to_subindex"
    bl_label = "Promote to SubIndexTriShape"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = _active_mesh(context)
        if obj is None:
            return False
        return read_profile_from_object(obj) in _FO4_PROFILES

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = _active_mesh(context)
        if obj is None:
            return {"CANCELLED"}
        mesh = obj.data
        num_triangles = len(getattr(mesh, "polygons", []) or [])
        segments = promote_triangles_to_segments(num_triangles)
        apply_segments_to_mesh(mesh, segments)
        props = getattr(obj, "nifblend", None)
        apply_profile_to_object(
            obj,
            profile=GameProfile.FALLOUT_4,
            nif_version=int(getattr(props, "nif_version", 0)) if props else 0,
            user_version=int(getattr(props, "user_version", 0)) if props else 0,
            bs_version=int(getattr(props, "bs_version", 130)) if props else 130,
            source_path=str(getattr(props, "source_path", "")) if props else "",
            block_origin="BSSubIndexTriShape",
        )
        self.report(
            {"INFO"},
            f"Promoted to BSSubIndexTriShape: 1 segment covering {num_triangles} triangles",
        )
        return {"FINISHED"}


class NIFBLEND_OT_fo4_add_segment(Operator):
    """Append an empty FO4 segment row to the active mesh."""

    bl_idname = "nifblend.fo4_add_segment"
    bl_label = "Add Segment"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return _active_mesh(context) is not None

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = _active_mesh(context)
        if obj is None:
            return {"CANCELLED"}
        shape = getattr(obj.data, "nifblend_shape", None)
        if shape is None:
            self.report({"WARNING"}, "Mesh has no nifblend_shape PropertyGroup")
            return {"CANCELLED"}
        row = shape.segments.add()
        row.parent_array_index = 0xFFFFFFFF
        return {"FINISHED"}


class NIFBLEND_OT_fo4_remove_segment(Operator):
    """Remove the last FO4 segment row from the active mesh."""

    bl_idname = "nifblend.fo4_remove_segment"
    bl_label = "Remove Segment"
    bl_options = {"REGISTER", "UNDO"}

    index: bpy.props.IntProperty(name="Index", default=-1, min=-1)  # type: ignore[valid-type]

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = _active_mesh(context)
        if obj is None:
            return False
        shape = getattr(obj.data, "nifblend_shape", None)
        return shape is not None and len(getattr(shape, "segments", [])) > 0

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = _active_mesh(context)
        if obj is None:
            return {"CANCELLED"}
        shape = obj.data.nifblend_shape
        n = len(shape.segments)
        idx = self.index if self.index >= 0 else n - 1
        if not (0 <= idx < n):
            return {"CANCELLED"}
        shape.segments.remove(idx)
        return {"FINISHED"}


class NIFBLEND_OT_fo76_set_external_mesh(Operator):
    """Populate one FO76 LOD slot with an external ``.mesh`` path."""

    bl_idname = "nifblend.fo76_set_external_mesh"
    bl_label = "Set FO76 External Mesh"
    bl_options = {"REGISTER", "UNDO"}

    lod_index: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="LOD Index",
        default=0,
        min=0,
        max=FO76_MESH_SLOT_COUNT - 1,
    )
    mesh_path: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Mesh Path",
        default="",
        subtype="FILE_PATH",
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = _active_mesh(context)
        if obj is None:
            return False
        return read_profile_from_object(obj) in _FO76_PROFILES

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = _active_mesh(context)
        if obj is None:
            return {"CANCELLED"}
        shape = getattr(obj.data, "nifblend_shape", None)
        if shape is None:
            self.report({"WARNING"}, "Mesh has no nifblend_shape PropertyGroup")
            return {"CANCELLED"}
        # Ensure the CollectionProperty has four slots, one per LOD index.
        while len(shape.fo76_slots) < FO76_MESH_SLOT_COUNT:
            entry = shape.fo76_slots.add()
            entry.lod_index = len(shape.fo76_slots) - 1
        slot = shape.fo76_slots[self.lod_index]
        slot.has_mesh = bool(self.mesh_path)
        slot.mesh_path = self.mesh_path
        self.report({"INFO"}, f"FO76 LOD {self.lod_index} → {self.mesh_path!r}")
        return {"FINISHED"}


class NIFBLEND_OT_fo76_clear_external_mesh(Operator):
    """Clear one FO76 LOD slot (``has_mesh=False``, empty path)."""

    bl_idname = "nifblend.fo76_clear_external_mesh"
    bl_label = "Clear FO76 External Mesh"
    bl_options = {"REGISTER", "UNDO"}

    lod_index: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="LOD Index",
        default=0,
        min=0,
        max=FO76_MESH_SLOT_COUNT - 1,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = _active_mesh(context)
        if obj is None:
            return False
        return read_profile_from_object(obj) in _FO76_PROFILES

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = _active_mesh(context)
        if obj is None:
            return {"CANCELLED"}
        shape = getattr(obj.data, "nifblend_shape", None)
        if shape is None or self.lod_index >= len(shape.fo76_slots):
            return {"CANCELLED"}
        slot = shape.fo76_slots[self.lod_index]
        slot.has_mesh = False
        slot.mesh_path = ""
        slot.num_verts = 0
        slot.indices_size = 0
        slot.flags = 0
        return {"FINISHED"}
