"""Phase 8c + 8h: generic post-import scene/transform utility operators.

Each is a thin wrapper around pure helpers in
:mod:`nifblend.bridge.utilities`.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator

from nifblend.bridge.utilities import (
    BETHESDA_UNIT_TO_BLENDER,
    DEFAULT_MERGE_DISTANCE,
    fit_clip_distance,
    recenter_offset,
)

__all__ = [
    "NIFBLEND_OT_apply_bethesda_scale",
    "NIFBLEND_OT_fix_viewport_clip",
    "NIFBLEND_OT_merge_doubles_safe",
    "NIFBLEND_OT_recalculate_normals_outside",
    "NIFBLEND_OT_recenter_to_origin",
    "NIFBLEND_OT_split_by_material_slot",
    "NIFBLEND_OT_weld_uv_seams",
]


_SCOPE_ITEMS = [
    ("SELECTED", "Selected", "Operate on the current selection"),
    ("SCENE", "Scene", "Operate on every object in the active scene"),
]


def _scoped_objects(context: bpy.types.Context, scope: str) -> list:
    if scope == "SCENE":
        scene = context.scene
        return list(scene.objects) if scene is not None else []
    return list(context.selected_objects or [])


class NIFBLEND_OT_recenter_to_origin(Operator):
    """Subtract the average position from every object so the group centers on origin."""

    bl_idname = "nifblend.recenter_to_origin"
    bl_label = "Recenter to Origin"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        objs = _scoped_objects(context, self.scope)
        if not objs:
            self.report({"INFO"}, "No objects to recenter")
            return {"CANCELLED"}
        positions = [tuple(o.location) for o in objs if hasattr(o, "location")]
        ox, oy, oz = recenter_offset(positions)
        for obj in objs:
            if not hasattr(obj, "location"):
                continue
            obj.location = (
                obj.location[0] - ox,
                obj.location[1] - oy,
                obj.location[2] - oz,
            )
        self.report({"INFO"}, f"Recentered {len(objs)} object(s) by ({ox:.1f}, {oy:.1f}, {oz:.1f})")
        return {"FINISHED"}


class NIFBLEND_OT_apply_bethesda_scale(Operator):
    """Multiply selected object scales by the NIF-unit → Blender-unit ratio."""

    bl_idname = "nifblend.apply_bethesda_scale"
    bl_label = "Apply Bethesda Unit Scale"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]
    factor: FloatProperty(  # type: ignore[valid-type]
        name="Factor",
        description="Multiplier (default = 0.01428, 1 NIF unit ≈ 1.428 cm)",
        default=BETHESDA_UNIT_TO_BLENDER,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        objs = _scoped_objects(context, self.scope)
        applied = 0
        for obj in objs:
            if not hasattr(obj, "scale"):
                continue
            obj.scale = (
                obj.scale[0] * self.factor,
                obj.scale[1] * self.factor,
                obj.scale[2] * self.factor,
            )
            applied += 1
        self.report({"INFO"}, f"Scaled {applied} object(s) by {self.factor}")
        return {"FINISHED"}


class NIFBLEND_OT_fix_viewport_clip(Operator):
    """Auto-fit every 3D-view clip_end to scene bounds."""

    bl_idname = "nifblend.fix_viewport_clip"
    bl_label = "Fix Viewport Clip"
    bl_options = {"REGISTER", "UNDO"}

    pad_factor: FloatProperty(  # type: ignore[valid-type]
        name="Pad Factor",
        description="Multiplier on the scene radius",
        default=1.5,
        min=1.0,
    )
    apply_to_all_3d_views: BoolProperty(  # type: ignore[valid-type]
        name="All 3D Views",
        description="Also update non-active 3D viewports",
        default=True,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        scene = context.scene
        if scene is None:
            return {"CANCELLED"}
        positions = [tuple(o.location) for o in scene.objects if hasattr(o, "location")]
        clip_end = fit_clip_distance(positions, pad_factor=self.pad_factor)
        updated = 0
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.clip_end = clip_end
                        updated += 1
                        if not self.apply_to_all_3d_views:
                            break
        self.report({"INFO"}, f"Set clip_end={clip_end:.0f} on {updated} viewport(s)")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Phase 8h: mesh-hygiene operators.
#
# Thin wrappers around Blender's built-in mesh ops. Each one scopes to the
# active object by default (``'ACTIVE' | 'SELECTED'``) because the mesh-edit
# operations mutate geometry -- a full-scene sweep here is a destructive
# footgun.
# ---------------------------------------------------------------------------


_MESH_SCOPE_ITEMS = [
    ("ACTIVE", "Active", "Operate on the active object only"),
    ("SELECTED", "Selected", "Operate on every selected mesh object"),
]


def _scoped_meshes(context: bpy.types.Context, scope: str) -> list:
    if scope == "ACTIVE":
        obj = context.active_object
        return [obj] if obj is not None and getattr(obj, "type", "") == "MESH" else []
    return [o for o in (context.selected_objects or []) if getattr(o, "type", "") == "MESH"]


def _run_in_edit_mode(context: bpy.types.Context, obj, body) -> None:
    """Enter EDIT mode on ``obj``, run ``body()``, restore OBJECT mode."""
    prev_active = context.view_layer.objects.active if hasattr(context, "view_layer") else None
    context.view_layer.objects.active = obj
    prev_mode = obj.mode
    if prev_mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")
    try:
        body()
    finally:
        if prev_mode != "EDIT":
            bpy.ops.object.mode_set(mode=prev_mode)
        if prev_active is not None:
            context.view_layer.objects.active = prev_active


class NIFBLEND_OT_merge_doubles_safe(Operator):
    """Merge coincident vertices without collapsing UV or normal seams."""

    bl_idname = "nifblend.merge_doubles_safe"
    bl_label = "Merge Doubles (Safe)"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_MESH_SCOPE_ITEMS, default="ACTIVE")  # type: ignore[valid-type]
    merge_distance: FloatProperty(  # type: ignore[valid-type]
        name="Merge Distance",
        description="Vertices closer than this collapse to one",
        default=DEFAULT_MERGE_DISTANCE,
        min=0.0,
        precision=6,
    )
    respect_uv_seams: BoolProperty(  # type: ignore[valid-type]
        name="Respect UV Seams",
        description=(
            "Only merge verts whose loops share UVs; leave seam verts "
            "split (avoids UV distortion on BSTriShape imports)"
        ),
        default=True,
    )
    respect_normal_seams: BoolProperty(  # type: ignore[valid-type]
        name="Respect Normal Seams",
        description="Skip verts whose adjacent face normals disagree",
        default=True,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        import bmesh

        meshes = _scoped_meshes(context, self.scope)
        if not meshes:
            self.report({"INFO"}, "No mesh objects to merge")
            return {"CANCELLED"}

        touched = 0
        for obj in meshes:
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                verts = list(bm.verts)
                if self.respect_uv_seams and bm.loops.layers.uv:
                    uv_layer = bm.loops.layers.uv.active or bm.loops.layers.uv[0]
                    verts = [
                        v for v in verts
                        if len({tuple(loop[uv_layer].uv) for loop in v.link_loops}) <= 1
                    ]
                if self.respect_normal_seams:
                    verts = [v for v in verts if not v.is_boundary]
                if verts:
                    bmesh.ops.remove_doubles(bm, verts=verts, dist=float(self.merge_distance))
                    bm.to_mesh(obj.data)
                    obj.data.update()
                    touched += 1
            finally:
                bm.free()
        self.report({"INFO"}, f"Merged doubles on {touched} mesh(es)")
        return {"FINISHED"}


class NIFBLEND_OT_recalculate_normals_outside(Operator):
    """Recalculate face normals pointing outward."""

    bl_idname = "nifblend.recalculate_normals_outside"
    bl_label = "Recalculate Normals Outside"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_MESH_SCOPE_ITEMS, default="ACTIVE")  # type: ignore[valid-type]
    inside: BoolProperty(  # type: ignore[valid-type]
        name="Flip Inside",
        description="Flip all normals to point inward instead of outward",
        default=False,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        meshes = _scoped_meshes(context, self.scope)
        if not meshes:
            self.report({"INFO"}, "No mesh objects selected")
            return {"CANCELLED"}

        touched = 0
        for obj in meshes:
            def _body(inside=bool(self.inside)) -> None:
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.normals_make_consistent(inside=inside)

            try:
                _run_in_edit_mode(context, obj, _body)
                touched += 1
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Normals recalc failed on {obj.name!r}: {exc}")
        self.report({"INFO"}, f"Recalculated normals on {touched} mesh(es)")
        return {"FINISHED"}


class NIFBLEND_OT_split_by_material_slot(Operator):
    """Split each mesh into one object per material slot.

    Inverse of :class:`nifblend.ops.cleanup.NIFBLEND_OT_combine_by_material`.
    Uses Blender's built-in ``bpy.ops.mesh.separate(type='MATERIAL')``.
    """

    bl_idname = "nifblend.split_by_material_slot"
    bl_label = "Split by Material Slot"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_MESH_SCOPE_ITEMS, default="ACTIVE")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        meshes = _scoped_meshes(context, self.scope)
        if not meshes:
            self.report({"INFO"}, "No mesh objects selected")
            return {"CANCELLED"}

        split_count = 0
        for obj in meshes:
            slots = getattr(obj.data, "materials", None)
            if not slots or len(slots) <= 1:
                continue

            def _body() -> None:
                bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.separate(type="MATERIAL")

            try:
                _run_in_edit_mode(context, obj, _body)
                split_count += 1
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Separate failed on {obj.name!r}: {exc}")
        if split_count == 0:
            self.report({"INFO"}, "Nothing to split (objects had ≤1 material slot)")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Split {split_count} mesh(es) by material")
        return {"FINISHED"}


class NIFBLEND_OT_weld_uv_seams(Operator):
    """Weld UVs at coincident vertex positions (closes UV seams)."""

    bl_idname = "nifblend.weld_uv_seams"
    bl_label = "Weld UV Seams"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_MESH_SCOPE_ITEMS, default="ACTIVE")  # type: ignore[valid-type]
    uv_threshold: FloatProperty(  # type: ignore[valid-type]
        name="UV Threshold",
        description="Loops whose UVs differ by less than this collapse to one",
        default=1e-4,
        min=0.0,
        precision=6,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        import bmesh

        meshes = _scoped_meshes(context, self.scope)
        if not meshes:
            self.report({"INFO"}, "No mesh objects selected")
            return {"CANCELLED"}

        thresh = float(self.uv_threshold)
        touched = 0
        for obj in meshes:
            bm = bmesh.new()
            try:
                bm.from_mesh(obj.data)
                if not bm.loops.layers.uv:
                    continue
                uv_layer = bm.loops.layers.uv.active or bm.loops.layers.uv[0]
                welded = 0
                for vert in bm.verts:
                    loops = list(vert.link_loops)
                    if len(loops) <= 1:
                        continue
                    reference = None
                    for loop in loops:
                        uv = loop[uv_layer].uv
                        if reference is None:
                            reference = (uv[0], uv[1])
                            continue
                        if abs(uv[0] - reference[0]) <= thresh and abs(uv[1] - reference[1]) <= thresh:
                            loop[uv_layer].uv = reference
                            welded += 1
                if welded:
                    bm.to_mesh(obj.data)
                    obj.data.update()
                    touched += 1
            finally:
                bm.free()
        self.report({"INFO"}, f"Welded UV seams on {touched} mesh(es)")
        return {"FINISHED"}
