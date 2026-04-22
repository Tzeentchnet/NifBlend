"""Import operator wired to the Phase 2 BSTriShape bridge.

Also handles the legacy NiTriShape / NiTriStrips geometry pair used by
Morrowind, Oblivion, Fallout 3 / NV and any pre-Skyrim NIF (Phase 6 step
22). Strips are converted to indexed triangles in
:func:`nifblend.bridge.mesh_in.strips_to_triangles` before reaching Blender,
so the operator only deals in :class:`MeshData`.
"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from nifblend.bridge.mesh_in import (
    import_bstrishape,
    mesh_data_to_blender,
    nitrishape_to_mesh_data,
    nitristrips_to_mesh_data,
)
from nifblend.bridge.object_props import apply_profile_to_object
from nifblend.format.generated.blocks import (
    BSTriShape,
    NiTriShape,
    NiTriShapeData,
    NiTriStrips,
    NiTriStripsData,
)
from nifblend.format.versions import detect_profile
from nifblend.io.block_table import read_nif


class NIFBLEND_OT_import_nif(Operator, ImportHelper):
    """Import a NIF file (BSTriShape + legacy NiTriShape / NiTriStrips meshes)."""

    bl_idname = "nifblend.import_nif"
    bl_label = "Import NIF"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            with open(self.filepath, "rb") as fh:
                table = read_nif(fh)
        except Exception as exc:  # - surface any parse error to the user
            self.report({"ERROR"}, f"Failed to read {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        collection = context.collection
        ctx = table.ctx
        profile = detect_profile(
            int(getattr(ctx, "version", 0)),
            int(getattr(ctx, "user_version", 0)),
            int(getattr(ctx, "bs_version", 0)),
        )

        def _stamp(obj, origin: str) -> None:
            apply_profile_to_object(
                obj,
                profile=profile,
                nif_version=int(getattr(ctx, "version", 0)),
                user_version=int(getattr(ctx, "user_version", 0)),
                bs_version=int(getattr(ctx, "bs_version", 0)),
                source_path=str(self.filepath),
                block_origin=origin,
            )

        imported = 0
        skipped: list[str] = []
        for block in table.blocks:
            if isinstance(block, BSTriShape):
                mesh = import_bstrishape(block, table)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, type(block).__name__)
                imported += 1
            elif isinstance(block, NiTriShape):
                data = _resolve_geometry_data(table, block.data, NiTriShapeData)
                if data is None:
                    skipped.append("NiTriShape (missing data)")
                    continue
                mdata = nitrishape_to_mesh_data(block, data, table)
                mesh = mesh_data_to_blender(mdata)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, "NiTriShape")
                imported += 1
            elif isinstance(block, NiTriStrips):
                data = _resolve_geometry_data(table, block.data, NiTriStripsData)
                if data is None:
                    skipped.append("NiTriStrips (missing data)")
                    continue
                mdata = nitristrips_to_mesh_data(block, data, table)
                mesh = mesh_data_to_blender(mdata)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, "NiTriStrips")
                imported += 1
            else:
                skipped.append(type(block).__name__)

        if not imported:
            self.report(
                {"WARNING"},
                f"No geometry blocks in {self.filepath!r}; skipped: {sorted(set(skipped))}",
            )
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Imported {imported} mesh(es); skipped {len(skipped)} other block(s)",
        )
        return {"FINISHED"}


def _resolve_geometry_data(table, ref: int, expected_type):
    """Resolve a ``NiTriShape``/``NiTriStrips`` data ref into the data block.

    Returns ``None`` when the ref is unset (negative / 0xFFFFFFFF) or points
    at a block of the wrong type — the caller skips that shape with a
    user-visible message rather than crashing the import.
    """
    if ref is None or ref < 0 or ref == 0xFFFFFFFF:
        return None
    if ref >= len(table.blocks):
        return None
    block = table.blocks[ref]
    if not isinstance(block, expected_type):
        return None
    return block
