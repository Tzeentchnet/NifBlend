"""Import operator — Phase 1 stub. Real implementation lands in Phase 2."""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper


class NIFBLEND_OT_import_nif(Operator, ImportHelper):
    """Import a NIF file (Phase 1 stub)."""

    bl_idname = "nifblend.import_nif"
    bl_label = "Import NIF"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        self.report(
            {"INFO"},
            f"NifBlend stub: would import {self.filepath!r} (real importer lands in Phase 2)",
        )
        return {"FINISHED"}
