"""Phase 8b: NifBlend sidebar UI panels.

Single 3D-view N-panel tab named ``NifBlend`` hosting:

* ``NIFBLEND_PT_main`` -- detected GameProfile / quick-action header.
* ``NIFBLEND_PT_utilities`` -- generic post-import utilities (Phase 8c).
* ``NIFBLEND_PT_game_specific`` -- game-gated sub-panels (Phase 8d).
* ``NIFBLEND_PT_cell_workflow`` -- cell-layout import (Phase 8e).

The existing :class:`nifblend.ops.preview_lod.NIFBLEND_PT_lod_preview`
panel keeps its own ``bl_category="NifBlend"`` registration; nothing
to re-home.
"""

from __future__ import annotations

import bpy
from bpy.types import Panel

from nifblend.bridge.material_props import get_starfield_material_path
from nifblend.bridge.object_props import object_profile
from nifblend.format.versions import GameProfile

__all__ = [
    "NIFBLEND_PT_cell_workflow",
    "NIFBLEND_PT_game_fallout3nv",
    "NIFBLEND_PT_game_fallout4",
    "NIFBLEND_PT_game_fallout76",
    "NIFBLEND_PT_game_morrowind",
    "NIFBLEND_PT_game_oblivion",
    "NIFBLEND_PT_game_skyrim",
    "NIFBLEND_PT_game_specific",
    "NIFBLEND_PT_game_starfield",
    "NIFBLEND_PT_main",
    "NIFBLEND_PT_utilities",
    "NIFBLEND_UL_fo4_segments",
    "NIFBLEND_UL_fo76_slots",
    "active_profile",
]


_TAB = "NifBlend"


def active_profile(context: bpy.types.Context) -> GameProfile:
    """Read the GameProfile stamped on the active object, falling back to UNKNOWN."""
    obj = getattr(context, "active_object", None)
    return object_profile(obj)


class _SidebarPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = _TAB


class NIFBLEND_PT_main(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_main"
    bl_label = "NifBlend"

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        prof = active_profile(context)

        col = layout.column(align=True)
        col.label(text=f"Game: {prof.value}", icon="WORLD")
        if obj is not None and hasattr(obj, "nifblend"):
            props = obj.nifblend
            col.prop(props, "game_profile", text="Override")
            col.label(text=f"Source: {getattr(props, 'source_path', '') or '(none)'}")
            col.label(text=f"Origin: {getattr(props, 'block_origin', '') or '(none)'}")

        layout.separator()
        row = layout.row(align=True)
        row.operator("nifblend.import_nif", icon="IMPORT", text="Import NIF")
        row.operator("nifblend.import_kf", icon="IMPORT", text="KF")
        row = layout.row(align=True)
        row.operator("nifblend.import_batch", icon="IMPORT", text="Folder")
        row.operator("nifblend.import_cell", icon="WORLD_DATA", text="Cell")
        layout.operator("nifblend.export_nif", icon="EXPORT", text="Export NIF")


class NIFBLEND_PT_utilities(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_utilities"
    bl_label = "Utilities"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Cleanup", icon="TRASH")
        col.operator("nifblend.delete_empties")
        col.operator("nifblend.delete_collision_shells")
        col.operator("nifblend.combine_by_material")
        col.operator("nifblend.clear_extra_materials")

        col = layout.column(align=True)
        col.label(text="Scene", icon="WORLD")
        col.operator("nifblend.recenter_to_origin")
        col.operator("nifblend.apply_bethesda_scale")
        col.operator("nifblend.fix_viewport_clip")

        col = layout.column(align=True)
        col.label(text="Textures", icon="IMAGE_DATA")
        col.operator("nifblend.relink_textures_against_data_root")
        col.operator("nifblend.bake_diffuse_to_texture")
        scene = context.scene
        misses = getattr(scene, "nifblend_texture_misses", None)
        if misses is not None and len(misses) > 0:
            col.label(text=f"Unresolved ({len(misses)}):", icon="ERROR")
            col.template_list(
                "NIFBLEND_UL_texture_misses",
                "",
                scene,
                "nifblend_texture_misses",
                scene,
                "nifblend_texture_misses_active",
                rows=3,
            )


class NIFBLEND_PT_game_specific(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_specific"
    bl_label = "Game-Specific"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) != GameProfile.UNKNOWN

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        prof = active_profile(context)
        layout.label(text=f"Active profile: {prof.value}")


class NIFBLEND_PT_game_skyrim(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_skyrim"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Skyrim"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) in (GameProfile.SKYRIM_LE, GameProfile.SKYRIM_SE)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.operator("nifblend.skyrim_le_to_se")
        col.operator("nifblend.skyrim_se_to_le")


class NIFBLEND_PT_game_oblivion(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_oblivion"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Oblivion / Pre-Skyrim"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) in (
            GameProfile.MORROWIND,
            GameProfile.OBLIVION,
            GameProfile.FALLOUT_3_NV,
        )

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator("nifblend.oblivion_stripify")


class NIFBLEND_UL_fo4_segments(bpy.types.UIList):
    """Read-only segment list for the FO4 sub-panel."""

    bl_idname = "NIFBLEND_UL_fo4_segments"

    def draw_item(
        self,
        _context: bpy.types.Context,
        layout: bpy.types.UILayout,
        _data: object,
        item: object,
        _icon: int,
        _active_data: object,
        _active_propname: str,
        _index: int = 0,
    ) -> None:
        row = layout.row(align=True)
        row.prop(item, "start_index", text="Start")
        row.prop(item, "num_primitives", text="Count")
        row.prop(item, "parent_array_index", text="Parent")


class NIFBLEND_UL_fo76_slots(bpy.types.UIList):
    """FO76 LOD-slot list for the FO76 sub-panel."""

    bl_idname = "NIFBLEND_UL_fo76_slots"

    def draw_item(
        self,
        _context: bpy.types.Context,
        layout: bpy.types.UILayout,
        _data: object,
        item: object,
        _icon: int,
        _active_data: object,
        _active_propname: str,
        _index: int = 0,
    ) -> None:
        row = layout.row(align=True)
        row.prop(item, "lod_index", text="LOD")
        row.prop(item, "has_mesh", text="")
        row.prop(item, "mesh_path", text="")


class NIFBLEND_PT_game_fallout4(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_fallout4"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Fallout 4 (SubIndex)"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) == GameProfile.FALLOUT_4

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        layout.operator("nifblend.fo4_promote_to_subindex", icon="PLUS")
        if obj is None or getattr(obj, "type", "") != "MESH":
            return
        shape = getattr(obj.data, "nifblend_shape", None)
        if shape is None:
            return
        box = layout.box()
        row = box.row(align=True)
        row.label(text=f"Segments ({len(shape.segments)}):")
        row.operator("nifblend.fo4_add_segment", text="", icon="ADD")
        row.operator("nifblend.fo4_remove_segment", text="", icon="REMOVE")
        box.template_list(
            "NIFBLEND_UL_fo4_segments",
            "",
            shape,
            "segments",
            shape,
            "num_primitives",
            rows=3,
        )
        box.prop(shape, "ssf_file")


class NIFBLEND_PT_game_fallout76(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_fallout76"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Fallout 76 (External Meshes)"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) == GameProfile.FALLOUT_76

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            layout.label(text="Select a mesh.")
            return
        shape = getattr(obj.data, "nifblend_shape", None)
        if shape is None:
            layout.label(text="(no nifblend_shape PropertyGroup)")
            return
        row = layout.row(align=True)
        row.operator("nifblend.fo76_set_external_mesh", icon="LINKED")
        row.operator("nifblend.fo76_clear_external_mesh", icon="UNLINKED")
        layout.template_list(
            "NIFBLEND_UL_fo76_slots",
            "",
            shape,
            "fo76_slots",
            shape,
            "num_primitives",
            rows=4,
        )


class NIFBLEND_PT_game_fallout3nv(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_fallout3nv"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Fallout 3 / NV (PP Shader)"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) == GameProfile.FALLOUT_3_NV

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            layout.label(text="Select a mesh.")
            return
        drawn = False
        for slot in getattr(obj, "material_slots", []) or []:
            mat = getattr(slot, "material", None)
            if mat is None:
                continue
            props = getattr(mat, "nifblend", None)
            if props is None:
                continue
            box = layout.box()
            box.label(text=mat.name, icon="MATERIAL")
            col = box.column(align=True)
            col.prop(props, "pp_flags")
            col.prop(props, "environment_map_scale")
            col.prop(props, "texture_clamp_mode")
            col.prop(props, "refraction_strength")
            col.prop(props, "refraction_fire_period")
            col.prop(props, "parallax_max_passes")
            col.prop(props, "parallax_scale")
            drawn = True
        if not drawn:
            layout.label(text="(no NifBlend materials on active object)")


class NIFBLEND_PT_game_morrowind(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_morrowind"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Morrowind / Classic Props"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) in (GameProfile.MORROWIND, GameProfile.OBLIVION)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.operator("nifblend.morrowind_split_classic_props", icon="NODE_MATERIAL")
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            return
        for slot in getattr(obj, "material_slots", []) or []:
            mat = getattr(slot, "material", None)
            if mat is None:
                continue
            props = getattr(mat, "nifblend", None)
            if props is None:
                continue
            box = layout.box()
            box.label(text=mat.name, icon="MATERIAL")
            col = box.column(align=True)
            col.prop(props, "ambient_color")
            col.prop(props, "diffuse_color")
            col.prop(props, "specular_color")
            col.prop(props, "glossiness")
            col.prop(props, "texturing_apply_mode")
            col.prop(props, "texturing_flags")
            col.prop(props, "texture_count")


class NIFBLEND_PT_game_starfield(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_game_starfield"
    bl_parent_id = "NIFBLEND_PT_game_specific"
    bl_label = "Starfield (External Meshes)"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return active_profile(context) == GameProfile.STARFIELD

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            layout.label(text="Select a mesh.")
            return
        shape = getattr(obj.data, "nifblend_shape", None)
        slots = list(getattr(shape, "fo76_slots", []) or []) if shape is not None else []
        if slots:
            layout.template_list(
                "NIFBLEND_UL_fo76_slots",
                "",
                shape,
                "fo76_slots",
                shape,
                "num_primitives",
                rows=4,
            )
        else:
            layout.label(text="(no external mesh references)")
        layout.operator("nifblend.starfield_reload_external_mesh", icon="FILE_REFRESH")

        # Phase 9i: Starfield .mat reload
        mat_slots = list(getattr(obj.data, "materials", []) or [])
        stamped: list[tuple[int, str]] = []
        for idx, mslot in enumerate(mat_slots):
            if mslot is None:
                continue
            stamp = get_starfield_material_path(mslot)
            if stamp:
                stamped.append((idx, stamp))
        layout.separator()
        layout.label(text="Starfield Material (.mat)")
        if stamped:
            for idx, rel in stamped:
                row = layout.row()
                row.label(text=f"[{idx}] {rel}", icon="MATERIAL")
            layout.operator("nifblend.starfield_reload_material", icon="FILE_REFRESH")
        else:
            layout.label(text="(no .mat path stamped)")


class NIFBLEND_PT_cell_workflow(_SidebarPanel, Panel):
    bl_idname = "NIFBLEND_PT_cell_workflow"
    bl_label = "Cell Workflow"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Phase 1: xEdit", icon="FILE_SCRIPT")
        col.operator("nifblend.export_xedit_pas")
        col.label(text="Phase 2: Blender", icon="IMPORT")
        col.operator("nifblend.import_cell")
        col.separator()
        col.operator("nifblend.recenter_to_origin")
        col.operator("nifblend.fix_viewport_clip")
