"""Phase 8e: NifCity-style cell-layout import operator.

Reads a CSV produced by the bundled xEdit ``.pas`` script
(:mod:`nifblend.scripts.blender_export`), parses + decodes every
referenced ``.nif`` in parallel via
:func:`nifblend.ops.import_batch.parse_and_decode_many`, then
materialises one Blender object per CSV row. **Instances**
(``obj.data`` shared) are used for duplicate references so a 50-row
CSV referencing one ``.nif`` produces 1 mesh datablock + 50 objects.
"""

from __future__ import annotations

import os
from pathlib import Path

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from nifblend.bridge.cell_csv import (
    bethesda_euler_to_blender,
    compute_origin_offset,
    parse_cell_csv,
    should_skip,
)
from nifblend.bridge.mesh_in import mesh_data_to_blender
from nifblend.ops.import_batch import parse_and_decode_many

__all__ = ["NIFBLEND_OT_import_cell"]


class NIFBLEND_OT_import_cell(Operator, ImportHelper):
    """Import a cell layout CSV: parse all referenced NIFs in parallel + place them."""

    bl_idname = "nifblend.import_cell"
    bl_label = "Import Cell (CSV)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={"HIDDEN"})  # type: ignore[valid-type]

    mesh_root: StringProperty(  # type: ignore[valid-type]
        name="Mesh Root",
        description="Folder containing the meshes referenced by the CSV (e.g. Data/Meshes)",
        subtype="DIR_PATH",
        default="",
    )
    normalize_location: BoolProperty(  # type: ignore[valid-type]
        name="Normalize Location",
        description="Subtract the average position so the cell centers on world origin",
        default=True,
    )
    instance_duplicates: BoolProperty(  # type: ignore[valid-type]
        name="Instance Duplicates",
        description="Share one mesh datablock across rows referencing the same NIF",
        default=True,
    )
    exclude_prefixes: StringProperty(  # type: ignore[valid-type]
        name="Exclude Prefixes",
        description="Comma-separated basename prefixes to skip",
        default="marker,fx",
    )
    worker_count: IntProperty(  # type: ignore[valid-type]
        name="Workers",
        description="Threads used for parallel NIF parsing (0 = auto)",
        default=0,
        min=0,
        max=64,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            placements = parse_cell_csv(self.filepath)
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to read CSV {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        if not placements:
            self.report({"WARNING"}, "CSV contained no usable rows")
            return {"CANCELLED"}

        prefixes = tuple(p.strip() for p in self.exclude_prefixes.split(",") if p.strip())
        kept = [p for p in placements if not should_skip(p.model_path, prefixes)]
        skipped_prefix = len(placements) - len(kept)

        # Resolve unique mesh paths against the mesh root; preserve a
        # placement→full-path map so per-row failures stay associated.
        unique_relpaths = sorted({p.model_path for p in kept})
        full_paths: dict[str, Path] = {}
        missing: list[str] = []
        for rel in unique_relpaths:
            full = Path(self.mesh_root) / rel.replace("/", os.sep)
            if full.exists():
                full_paths[rel] = full
            else:
                missing.append(rel)

        if not full_paths:
            self.report(
                {"ERROR"},
                f"No referenced NIFs exist under {self.mesh_root!r} "
                f"({len(missing)} missing)",
            )
            return {"CANCELLED"}

        # Parallel decode (one parse per unique mesh path, even if the
        # CSV references it 50 times).
        max_workers = self.worker_count if self.worker_count > 0 else None
        results = parse_and_decode_many(
            list(full_paths.values()),
            max_workers=max_workers,
        )

        # Build a single Blender mesh datablock per unique path so
        # duplicate rows get instances.
        mesh_by_relpath: dict[str, list] = {}
        decode_errors: list[str] = []
        path_to_relpath = {v: k for k, v in full_paths.items()}
        for res in results:
            relpath = path_to_relpath.get(res.path)
            if relpath is None:
                continue
            if res.error:
                decode_errors.append(f"{relpath}: {res.error}")
                continue
            if not res.meshes:
                decode_errors.append(f"{relpath}: no decodable geometry")
                continue
            blender_meshes = []
            for mdata in res.meshes:
                bm = mesh_data_to_blender(mdata)
                blender_meshes.append(bm)
            mesh_by_relpath[relpath] = blender_meshes

        # Compute and apply position offset.
        offset = compute_origin_offset(kept) if self.normalize_location else (0.0, 0.0, 0.0)

        # Materialise one object per CSV row.
        scene = context.scene
        target_collection = scene.collection if scene is not None else context.collection
        cell_collection = bpy.data.collections.new(Path(self.filepath).stem)
        if target_collection is not None:
            target_collection.children.link(cell_collection)

        placed = 0
        for placement in kept:
            blender_meshes = mesh_by_relpath.get(placement.model_path)
            if not blender_meshes:
                continue
            for i, mesh in enumerate(blender_meshes):
                obj_data = mesh if self.instance_duplicates else mesh.copy()
                obj_name = (
                    Path(placement.model_path).stem
                    if i == 0
                    else f"{Path(placement.model_path).stem}_{i}"
                )
                obj = bpy.data.objects.new(obj_name, obj_data)
                obj.location = (
                    placement.location[0] - offset[0],
                    placement.location[1] - offset[1],
                    placement.location[2] - offset[2],
                )
                obj.rotation_mode = "XYZ"
                obj.rotation_euler = bethesda_euler_to_blender(*placement.rotation_deg)
                obj.scale = (placement.scale, placement.scale, placement.scale)
                cell_collection.objects.link(obj)
                placed += 1

        if missing:
            self.report({"WARNING"}, f"{len(missing)} referenced NIF(s) missing under {self.mesh_root!r}")
        if decode_errors:
            self.report({"WARNING"}, f"{len(decode_errors)} NIF(s) failed to decode")
        if skipped_prefix:
            self.report({"INFO"}, f"Skipped {skipped_prefix} marker/fx row(s)")
        self.report(
            {"INFO"},
            f"Imported {placed} object(s) from {len(mesh_by_relpath)} unique NIF(s); "
            f"offset=({offset[0]:.1f},{offset[1]:.1f},{offset[2]:.1f})",
        )
        return {"FINISHED"}
