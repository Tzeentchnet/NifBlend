"""Phase 8e: write the bundled xEdit ``.pas`` companion script to disk.

A single-action operator that reads
``nifblend/scripts/blender_export.pas`` via :mod:`importlib.resources`
and writes a copy into a user-chosen folder. The script then runs
inside xEdit (``D`` key on a cell → "Apply Script") to produce a
``nifblend_cell.csv`` consumed by :class:`NIFBLEND_OT_import_cell`.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

__all__ = ["PAS_RESOURCE", "NIFBLEND_OT_export_xedit_pas", "load_pas_text"]


PAS_RESOURCE = "blender_export.pas"


def load_pas_text() -> str:
    """Return the bundled ``.pas`` script's source text."""
    return (
        resources.files("nifblend.scripts")
        .joinpath(PAS_RESOURCE)
        .read_text(encoding="utf-8")
    )


class NIFBLEND_OT_export_xedit_pas(Operator):
    """Write the bundled NifBlend xEdit companion script to a folder."""

    bl_idname = "nifblend.export_xedit_pas"
    bl_label = "Export NifBlend xEdit Script"
    bl_options = {"REGISTER"}

    directory: StringProperty(  # type: ignore[valid-type]
        name="Output Folder",
        description="Folder to write blender_export.pas into (typically xEdit's Edit Scripts/)",
        subtype="DIR_PATH",
        default="",
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not self.directory:
            self.report({"ERROR"}, "No output folder selected")
            return {"CANCELLED"}
        out_dir = Path(self.directory)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            text = load_pas_text()
            target = out_dir / PAS_RESOURCE
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            self.report({"ERROR"}, f"Failed to write {PAS_RESOURCE!r}: {exc}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Wrote {target}")
        return {"FINISHED"}
