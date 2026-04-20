"""NifBlend — fast NIF/KF import/export for Bethesda game modding.

Blender 5.0+ extension entry point. The bulk of the implementation lives in
sibling subpackages (`io`, `format`, `bridge`, `ops`); this module is only
responsible for class registration and menu wiring.
"""

from __future__ import annotations

import bpy

from .ops import import_nif, export_nif

__all__ = ["register", "unregister"]


# Class registration order matters: operators before menu items that reference
# them by bl_idname.
_CLASSES: tuple[type, ...] = (
    import_nif.NIFBLEND_OT_import_nif,
    export_nif.NIFBLEND_OT_export_nif,
)


def _menu_func_import(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    self.layout.operator(
        import_nif.NIFBLEND_OT_import_nif.bl_idname,
        text="NIF (NifBlend) (.nif)",
    )


def _menu_func_export(self: bpy.types.Menu, _context: bpy.types.Context) -> None:
    self.layout.operator(
        export_nif.NIFBLEND_OT_export_nif.bl_idname,
        text="NIF (NifBlend) (.nif)",
    )


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(_menu_func_export)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(_menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
