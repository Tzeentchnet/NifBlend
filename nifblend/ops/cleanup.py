"""Phase 8c: post-import cleanup operators (NifCity port + hardened defaults).

Each operator scopes to selection by default (NifCity scoped to the
whole scene -- footgun). Pure logic lives in
:mod:`nifblend.bridge.cleanup`; this module is a thin Blender wrapper.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty
from bpy.types import Operator

from nifblend.bridge.cleanup import (
    DEFAULT_COLLISION_PATTERNS,
    group_objects_by_material_base,
    matches_collision_pattern,
    parse_pattern_list,
    strip_blender_dup_suffix,
)

__all__ = [
    "NIFBLEND_OT_clear_extra_materials",
    "NIFBLEND_OT_combine_by_material",
    "NIFBLEND_OT_delete_collision_shells",
    "NIFBLEND_OT_delete_empties",
]


_SCOPE_ITEMS = [
    ("SELECTED", "Selected", "Operate on the current selection only"),
    ("SCENE", "Scene", "Operate on every object in the active scene"),
]


def _scoped_objects(context: bpy.types.Context, scope: str) -> list:
    if scope == "SCENE":
        scene = context.scene
        return list(scene.objects) if scene is not None else []
    return list(context.selected_objects or [])


class NIFBLEND_OT_delete_empties(Operator):
    """Delete empty objects (with optional transform-bake on their children)."""

    bl_idname = "nifblend.delete_empties"
    bl_label = "Delete Empties"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]
    bake_children_transforms: BoolProperty(  # type: ignore[valid-type]
        name="Apply Transforms First",
        description=(
            "Apply location/rotation/scale to non-empty children before "
            "deleting parents (NifCity-style; off by default)"
        ),
        default=False,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        targets = _scoped_objects(context, self.scope)
        empties = [o for o in targets if getattr(o, "type", "") == "EMPTY"]
        if not empties:
            self.report({"INFO"}, "No empties to delete")
            return {"CANCELLED"}

        if self.bake_children_transforms:
            bpy.ops.object.select_all(action="DESELECT")
            for empty in empties:
                for child in list(empty.children):
                    child.select_set(True)
            try:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            except RuntimeError as exc:
                self.report({"WARNING"}, f"Transform apply failed: {exc}")

        for obj in empties:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.report({"INFO"}, f"Deleted {len(empties)} empty/empties")
        return {"FINISHED"}


class NIFBLEND_OT_delete_collision_shells(Operator):
    """Delete collision-shell-shaped objects (box/convex/hull)."""

    bl_idname = "nifblend.delete_collision_shells"
    bl_label = "Delete Collision Shells"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]
    patterns: StringProperty(  # type: ignore[valid-type]
        name="Patterns",
        description="Comma-separated name prefixes to match",
        default=",".join(DEFAULT_COLLISION_PATTERNS),
    )
    also_delete_armatures: BoolProperty(  # type: ignore[valid-type]
        name="Also Delete Armatures",
        description="Include ARMATURE objects in the deletion (NifCity bundled this)",
        default=False,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        targets = _scoped_objects(context, self.scope)
        patterns = parse_pattern_list(self.patterns) or DEFAULT_COLLISION_PATTERNS
        to_remove = []
        for obj in targets:
            otype = getattr(obj, "type", "")
            if self.also_delete_armatures and otype == "ARMATURE":
                to_remove.append(obj)
                continue
            if otype != "MESH":
                continue
            if matches_collision_pattern(getattr(obj, "name", ""), patterns):
                to_remove.append(obj)
        if not to_remove:
            self.report({"INFO"}, "No collision shells matched")
            return {"CANCELLED"}
        for obj in to_remove:
            bpy.data.objects.remove(obj, do_unlink=True)
        self.report({"INFO"}, f"Deleted {len(to_remove)} object(s)")
        return {"FINISHED"}


class NIFBLEND_OT_combine_by_material(Operator):
    """Join meshes whose first material's base name matches."""

    bl_idname = "nifblend.combine_by_material"
    bl_label = "Combine Meshes by Material"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        targets = _scoped_objects(context, self.scope)
        groups = group_objects_by_material_base(targets)
        joined = 0
        for objs in groups.values():
            if len(objs) < 2:
                continue
            active = objs[0]
            try:
                with context.temp_override(
                    active_object=active,
                    selected_objects=list(objs),
                    selected_editable_objects=list(objs),
                ):
                    bpy.ops.object.join()
                joined += len(objs) - 1
            except (RuntimeError, AttributeError) as exc:
                self.report({"WARNING"}, f"Join failed for {active.name!r}: {exc}")
        if joined == 0:
            self.report({"INFO"}, "Nothing to combine")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Combined {joined} mesh(es)")
        return {"FINISHED"}


class NIFBLEND_OT_clear_extra_materials(Operator):
    """Reduce each object to one material slot, stripping Blender's .NNN suffix."""

    bl_idname = "nifblend.clear_extra_materials"
    bl_label = "Clear Extra Materials"
    bl_options = {"REGISTER", "UNDO"}

    scope: EnumProperty(items=_SCOPE_ITEMS, default="SELECTED")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        targets = _scoped_objects(context, self.scope)
        touched = 0
        for obj in targets:
            if getattr(obj, "type", "") != "MESH":
                continue
            data = obj.data
            if not getattr(data, "materials", None):
                continue
            primary = data.materials[0]
            if primary is None:
                continue
            data.materials.clear()
            data.materials.append(primary)
            primary.name = strip_blender_dup_suffix(primary.name)
            touched += 1
        if touched == 0:
            self.report({"INFO"}, "No materials to clean")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Cleaned materials on {touched} object(s)")
        return {"FINISHED"}
