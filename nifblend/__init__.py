"""NifBlend — fast NIF/KF import/export for Bethesda game modding.

Blender 5.0+ extension entry point. The bulk of the implementation lives in
sibling subpackages (`io`, `format`, `bridge`, `ops`); this module is only
responsible for class registration and menu wiring.
"""

from __future__ import annotations

import bpy

from . import preferences
from .bridge import (
    armature_props,
    material_props,
    mesh_props,
    object_props,
    skin_props,
)
from .ops import (
    cleanup,
    export_batch,
    export_nif,
    export_xedit_pas,
    games_fallout,
    games_morrowind,
    games_oblivion,
    games_skyrim,
    import_batch,
    import_cell,
    import_kf,
    import_nif,
    preview_lod,
    textures,
    utilities,
)
from .ui import sidebar

__all__ = ["register", "unregister"]


# Class registration order matters: operators before menu items that reference
# them by bl_idname; panels after the operators they draw.
_CLASSES: tuple[type, ...] = (
    # Import / export operators.
    import_nif.NIFBLEND_OT_import_nif,
    import_kf.NIFBLEND_OT_import_kf,
    import_batch.NIFBLEND_OT_import_batch,
    import_cell.NIFBLEND_OT_import_cell,
    export_nif.NIFBLEND_OT_export_nif,
    export_batch.NIFBLEND_OT_export_batch,
    export_xedit_pas.NIFBLEND_OT_export_xedit_pas,
    # Cleanup + utility operators (Phase 8c + 8h).
    cleanup.NIFBLEND_OT_delete_empties,
    cleanup.NIFBLEND_OT_delete_collision_shells,
    cleanup.NIFBLEND_OT_combine_by_material,
    cleanup.NIFBLEND_OT_clear_extra_materials,
    utilities.NIFBLEND_OT_recenter_to_origin,
    utilities.NIFBLEND_OT_apply_bethesda_scale,
    utilities.NIFBLEND_OT_fix_viewport_clip,
    utilities.NIFBLEND_OT_merge_doubles_safe,
    utilities.NIFBLEND_OT_recalculate_normals_outside,
    utilities.NIFBLEND_OT_split_by_material_slot,
    utilities.NIFBLEND_OT_weld_uv_seams,
    # Game-specific operators (Phase 8d + 8g).
    games_skyrim.NIFBLEND_OT_skyrim_le_to_se,
    games_skyrim.NIFBLEND_OT_skyrim_se_to_le,
    games_oblivion.NIFBLEND_OT_oblivion_stripify,
    games_fallout.NIFBLEND_OT_fo4_promote_to_subindex,
    games_fallout.NIFBLEND_OT_fo4_add_segment,
    games_fallout.NIFBLEND_OT_fo4_remove_segment,
    games_fallout.NIFBLEND_OT_fo76_set_external_mesh,
    games_fallout.NIFBLEND_OT_fo76_clear_external_mesh,
    games_morrowind.NIFBLEND_OT_morrowind_split_classic_props,
    # LOD + sidebar panels.
    preview_lod.NIFBLEND_OT_lod_toggle_level,
    preview_lod.NIFBLEND_OT_lod_show_only,
    preview_lod.NIFBLEND_PT_lod_preview,
    sidebar.NIFBLEND_UL_fo4_segments,
    sidebar.NIFBLEND_UL_fo76_slots,
    sidebar.NIFBLEND_PT_main,
    sidebar.NIFBLEND_PT_utilities,
    sidebar.NIFBLEND_PT_game_specific,
    sidebar.NIFBLEND_PT_game_skyrim,
    sidebar.NIFBLEND_PT_game_oblivion,
    sidebar.NIFBLEND_PT_game_fallout4,
    sidebar.NIFBLEND_PT_game_fallout76,
    sidebar.NIFBLEND_PT_game_fallout3nv,
    sidebar.NIFBLEND_PT_game_morrowind,
    sidebar.NIFBLEND_PT_cell_workflow,
)


def _menu_func_import(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    self.layout.operator(
        import_nif.NIFBLEND_OT_import_nif.bl_idname,
        text="NIF (NifBlend) (.nif)",
    )
    self.layout.operator(
        import_kf.NIFBLEND_OT_import_kf.bl_idname,
        text="KF Animation (NifBlend) (.kf)",
    )
    self.layout.operator(
        import_batch.NIFBLEND_OT_import_batch.bl_idname,
        text="NIF Folder (NifBlend) (batch)",
    )
    self.layout.operator(
        import_cell.NIFBLEND_OT_import_cell.bl_idname,
        text="NIF Cell (NifBlend) (.csv)",
    )


def _menu_func_export(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    self.layout.operator(
        export_nif.NIFBLEND_OT_export_nif.bl_idname,
        text="NIF (NifBlend) (.nif)",
    )
    self.layout.operator(
        export_batch.NIFBLEND_OT_export_batch.bl_idname,
        text="NIF Folder (NifBlend) (batch)",
    )
    self.layout.operator(
        export_xedit_pas.NIFBLEND_OT_export_xedit_pas.bl_idname,
        text="xEdit Cell Script (NifBlend) (.pas)",
    )


def register() -> None:
    preferences.register()
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    material_props.register()
    armature_props.register()
    skin_props.register()
    object_props.register()
    mesh_props.register()
    textures.register()
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(_menu_func_export)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(_menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)
    textures.unregister()
    mesh_props.unregister()
    object_props.unregister()
    skin_props.unregister()
    armature_props.unregister()
    material_props.unregister()
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    preferences.unregister()
