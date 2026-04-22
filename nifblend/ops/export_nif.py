"""Export operator wired to the Phase 2 BSTriShape bridge.

Walks every selected mesh object in the scene, converts each to a
:class:`~nifblend.format.generated.blocks.BSTriShape` via the bridge, and
writes them as a fresh NIF (Skyrim SE-shaped header by default).
String-table allocation and cross-reference patching are deliberately
minimal -- this is the v0.1 path; richer scene graphs land in later
phases.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from nifblend.bridge.mesh_out import export_bstrishape
from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import BSStreamHeader, ExportString, Footer, Header
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_header() -> tuple[Header, ReadContext]:
    """Return a minimal SSE-shaped header + matching ReadContext."""
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,  # filled in by write_nif
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
        num_block_types=0,
        block_types=[],
        block_type_index=[],
        num_strings=0,
        max_string_length=0,
        strings=[],
        num_groups=0,
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return h, ctx


class NIFBLEND_OT_export_nif(Operator, ExportHelper):
    """Export selected mesh objects as a Skyrim SE-shaped NIF (Phase 2)."""

    bl_idname = "nifblend.export_nif"
    bl_label = "Export NIF"
    bl_options = {"REGISTER"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        meshes = [
            obj for obj in context.selected_objects if getattr(obj, "type", None) == "MESH"
        ]
        if not meshes:
            self.report({"WARNING"}, "Select at least one mesh object to export")
            return {"CANCELLED"}

        header, ctx = _sse_header()
        blocks = [
            export_bstrishape(obj.data, name=obj.name) for obj in meshes
        ]
        table = BlockTable(header=header, blocks=blocks, footer=Footer(), ctx=ctx)

        try:
            with open(self.filepath, "wb") as fh:
                write_nif(fh, table)
        except Exception as exc:  # - surface any write error to the user
            self.report({"ERROR"}, f"Failed to write {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported {len(blocks)} BSTriShape mesh(es) to {self.filepath!r}")
        return {"FINISHED"}
