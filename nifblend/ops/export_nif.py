"""Export operator — Phase 1 stub. Real implementation lands in Phase 2."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper


class NIFBLEND_OT_export_nif(Operator, ExportHelper):
    """Export a NIF file (Phase 1 stub)."""

    bl_idname = "nifblend.export_nif"
    bl_label = "Export NIF"
    bl_options = {"REGISTER"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        self.report(
            {"INFO"},
            f"NifBlend stub: would export to {self.filepath!r} (real exporter lands in Phase 2)",
        )
        return {"FINISHED"}
