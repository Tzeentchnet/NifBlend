"""LOD preview support (Phase 7 step 28).

Provides a Blender-side wrapper that takes the pure
:func:`nifblend.bridge.lod.detect_lod_groups` output and materialises
each LOD level into its own collection (one parent ``Collection`` per
group, child collections named ``LOD0`` / ``LOD1`` / …). A small panel
in the 3D-view sidebar (``N`` key, ``NifBlend`` tab) lets the user
toggle viewport visibility per level on the active LOD group, plus a
"show only" radio that hides every other level in the group at once.

The detection / materialisation helpers are pure on the bridge side
and the wrapper takes an injectable ``bpy`` so the headless test suite
can exercise the collection plumbing without Blender installed.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any

import bpy
from bpy.props import IntProperty, StringProperty
from bpy.types import Operator, Panel

from nifblend.bridge.lod import LODGroup

__all__ = [
    "BlenderLODGroup",
    "BlenderLODLevel",
    "NIFBLEND_OT_lod_show_only",
    "NIFBLEND_OT_lod_toggle_level",
    "NIFBLEND_PT_lod_preview",
    "materialise_lod_groups",
]


@dataclass(slots=True)
class BlenderLODLevel:
    index: int
    near_extent: float
    far_extent: float
    collection: Any  # bpy.types.Collection


@dataclass(slots=True)
class BlenderLODGroup:
    name: str
    parent_collection: Any  # bpy.types.Collection
    levels: list[BlenderLODLevel] = field(default_factory=list)


# ---- materialisation -----------------------------------------------------


def materialise_lod_groups(
    groups: list[LODGroup],
    *,
    block_to_object: dict[int, Any],
    bpy: Any = None,
) -> list[BlenderLODGroup]:
    """Create per-LOD-group / per-level Blender collections.

    ``block_to_object`` maps block-table indices (the same ones the
    detector emitted on :attr:`LODLevel.block_ref` /
    :attr:`TriangleSliceLevel.shape_ref`) to the materialised
    ``bpy.types.Object`` produced by the importer. Objects referenced
    by an LOD level are unlinked from the active scene collection (so
    they only appear inside their LOD child collection) and re-linked
    under the matching child collection. By default LOD0 stays visible
    and LOD1+ are hidden via ``Collection.hide_viewport = True``.

    BSLODTriShape groups all reference the same shape object, so they
    appear once per LOD child collection (same Object linked into
    multiple collections — Blender supports this) until the user
    duplicates the mesh and trims its triangles per level. The
    triangle-count metadata is stamped on the level's collection via
    a ``.nifblend_lod_num_triangles`` ID property so any downstream
    auto-decimator can pick it up.
    """
    if bpy is None:
        import bpy as bpy
    scene = bpy.context.scene
    root_collection = scene.collection if scene is not None else None

    out: list[BlenderLODGroup] = []
    for group in groups:
        parent = bpy.data.collections.new(f"LOD_{group.name}")
        if root_collection is not None:
            root_collection.children.link(parent)
        bgroup = BlenderLODGroup(name=group.name, parent_collection=parent)
        for lvl in group.levels:
            child = bpy.data.collections.new(f"LOD{lvl.index}")
            parent.children.link(child)
            # Hide every level above LOD0 by default so the viewport
            # opens onto the highest-detail mesh.
            if lvl.index > 0:
                _set_collection_hidden(child, True)
            ref = (
                lvl.block_ref
                if lvl.block_ref is not None
                else (lvl.triangle_slice.shape_ref if lvl.triangle_slice else None)
            )
            obj = block_to_object.get(ref) if ref is not None else None
            if obj is not None:
                _move_object_to_collection(obj, child, root_collection)
            if lvl.triangle_slice is not None:
                child["nifblend_lod_num_triangles"] = int(lvl.triangle_slice.num_triangles)
            bgroup.levels.append(
                BlenderLODLevel(
                    index=lvl.index,
                    near_extent=lvl.near_extent,
                    far_extent=lvl.far_extent,
                    collection=child,
                )
            )
        out.append(bgroup)
    return out


# ---- viewport panel + operators ------------------------------------------


class NIFBLEND_OT_lod_toggle_level(Operator):
    """Toggle viewport visibility for a single LOD level."""

    bl_idname = "nifblend.lod_toggle_level"
    bl_label = "Toggle LOD Level"
    bl_options = {"REGISTER", "UNDO"}

    collection_name: StringProperty()  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        coll = bpy.data.collections.get(self.collection_name)
        if coll is None:
            self.report({"WARNING"}, f"No collection named {self.collection_name!r}")
            return {"CANCELLED"}
        _set_collection_hidden(coll, not bool(coll.hide_viewport))
        return {"FINISHED"}


class NIFBLEND_OT_lod_show_only(Operator):
    """Show one LOD level inside a group; hide every sibling."""

    bl_idname = "nifblend.lod_show_only"
    bl_label = "Show Only LOD Level"
    bl_options = {"REGISTER", "UNDO"}

    parent_collection_name: StringProperty()  # type: ignore[valid-type]
    visible_index: IntProperty(default=0)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        parent = bpy.data.collections.get(self.parent_collection_name)
        if parent is None:
            self.report({"WARNING"}, f"No collection {self.parent_collection_name!r}")
            return {"CANCELLED"}
        for child in parent.children:
            level_idx = _level_index_from_name(child.name)
            _set_collection_hidden(child, level_idx != self.visible_index)
        return {"FINISHED"}


class NIFBLEND_PT_lod_preview(Panel):
    """Sidebar panel listing every LOD group in the scene."""

    bl_idname = "NIFBLEND_PT_lod_preview"
    bl_label = "LOD Preview"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "NifBlend"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        scene = context.scene
        if scene is None:
            layout.label(text="No active scene")
            return
        groups = [
            c
            for c in scene.collection.children
            if c.name.startswith("LOD_")
        ]
        if not groups:
            layout.label(text="No LOD groups detected")
            return
        for parent in groups:
            box = layout.box()
            box.label(text=parent.name, icon="GROUP")
            for child in parent.children:
                row = box.row(align=True)
                level_idx = _level_index_from_name(child.name)
                hidden = bool(child.hide_viewport)
                row.operator(
                    NIFBLEND_OT_lod_toggle_level.bl_idname,
                    text=child.name,
                    depress=not hidden,
                ).collection_name = child.name
                op = row.operator(
                    NIFBLEND_OT_lod_show_only.bl_idname,
                    text="",
                    icon="HIDE_OFF",
                )
                op.parent_collection_name = parent.name
                op.visible_index = level_idx


# ---- private helpers -----------------------------------------------------


def _set_collection_hidden(coll: Any, hidden: bool) -> None:
    """Set ``hide_viewport`` (and ``hide_render``) on a collection."""
    with contextlib.suppress(AttributeError, TypeError):
        coll.hide_viewport = bool(hidden)
    with contextlib.suppress(AttributeError, TypeError):
        coll.hide_render = bool(hidden)


def _move_object_to_collection(obj: Any, target: Any, root: Any | None) -> None:
    """Unlink ``obj`` from ``root`` (if linked there) and link into ``target``.

    Blender allows the same object to be linked into multiple
    collections; for BSLODTriShape we *do* want the same Object in
    every LOD child collection, so the unlink-from-root is best-effort
    (a missing-object error is silently ignored).
    """
    if root is not None:
        with contextlib.suppress(RuntimeError, AttributeError):
            root.objects.unlink(obj)
    # Already linked into ``target`` is harmless: silently swallow.
    with contextlib.suppress(RuntimeError):
        target.objects.link(obj)


def _level_index_from_name(name: str) -> int:
    """Parse the trailing integer of an ``LODn`` collection name."""
    if not name.startswith("LOD"):
        return -1
    try:
        return int(name[3:])
    except ValueError:
        return -1
