"""Batch NIF export operator (Phase 7 step 27).

Walks the selected mesh objects, runs the Blender→NIF bridge on the main
thread (``foreach_get`` / Blender data access is not thread-safe), and
fans the resulting :class:`~nifblend.io.block_table.BlockTable`
serialisations out to a thread pool — the heavy lifting on the export
side is the structural ``write`` walk + numpy bulk array writes, both of
which release the GIL.

The two phases are exposed as standalone helpers (:func:`build_tables`,
:func:`write_tables`) so the headless test suite can drive the parallel
writer without a real ``bpy``.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator

from nifblend.bridge.mesh_out import export_bstrishape
from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import BSStreamHeader, ExportString, Footer, Header
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif

__all__ = [
    "BatchExportItem",
    "BatchExportResult",
    "NIFBLEND_OT_export_batch",
    "build_tables",
    "write_tables",
]


@dataclass(slots=True)
class BatchExportItem:
    """A pre-built table + the path to write it to."""

    path: Path
    table: BlockTable


@dataclass(slots=True)
class BatchExportResult:
    """Outcome of one file's worth of writing."""

    path: Path
    bytes_written: int = 0
    error: str | None = None


# ---- internal: header construction ---------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_header() -> tuple[Header, ReadContext]:
    """Skyrim SE-shaped header. Mirrors :mod:`nifblend.ops.export_nif`."""
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
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


# ---- main-thread: build tables from Blender objects ----------------------


def build_tables(
    objects: list[Any], output_dir: Path | str, *, suffix: str = ".nif"
) -> list[BatchExportItem]:
    """Convert each mesh in ``objects`` into a single-shape ``BlockTable``.

    Filenames are derived from ``obj.name`` (Blender already enforces
    uniqueness within a scene). Anything that isn't a ``MESH`` is skipped
    silently — operators add their own warnings.
    """
    output_dir = Path(output_dir)
    items: list[BatchExportItem] = []
    for obj in objects:
        if getattr(obj, "type", None) != "MESH":
            continue
        header, ctx = _sse_header()
        block = export_bstrishape(obj.data, name=obj.name)
        table = BlockTable(header=header, blocks=[block], footer=Footer(), ctx=ctx)
        items.append(BatchExportItem(path=output_dir / f"{obj.name}{suffix}", table=table))
    return items


# ---- worker-thread: serialise tables in parallel -------------------------


def _write_one(item: BatchExportItem) -> BatchExportResult:
    res = BatchExportResult(path=item.path)
    try:
        item.path.parent.mkdir(parents=True, exist_ok=True)
        with open(item.path, "wb") as fh:
            write_nif(fh, item.table)
        res.bytes_written = item.path.stat().st_size
    except Exception as exc:
        res.error = f"write failed: {exc}"
    return res


def write_tables(
    items: list[BatchExportItem], *, max_workers: int | None = None
) -> list[BatchExportResult]:
    """Serialise every item in parallel; result order matches input."""
    if not items:
        return []
    workers = max_workers if max_workers and max_workers > 0 else min(
        32, (os.cpu_count() or 1) + 4
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_write_one, items))


# ---- operator -------------------------------------------------------------


class NIFBLEND_OT_export_batch(Operator):
    """Export every selected mesh as its own ``.nif`` under a chosen folder."""

    bl_idname = "nifblend.export_batch"
    bl_label = "Export NIF Folder (Batch)"
    bl_options = {"REGISTER"}

    directory: StringProperty(  # type: ignore[valid-type]
        name="Directory",
        subtype="DIR_PATH",
        description="Output folder; one .nif per selected mesh object",
    )
    overwrite: BoolProperty(  # type: ignore[valid-type]
        name="Overwrite",
        description="Overwrite existing .nif files in the target folder",
        default=True,
    )
    max_workers: IntProperty(  # type: ignore[valid-type]
        name="Worker Threads",
        description="0 = auto (min(32, cpu_count + 4))",
        default=0,
        min=0,
        max=64,
    )

    def invoke(
        self, context: bpy.types.Context, _event: bpy.types.Event
    ) -> set[str]:
        # Pop the standard folder picker so the user can pick a destination.
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not self.directory:
            self.report({"ERROR"}, "Pick an output folder")
            return {"CANCELLED"}
        meshes = [
            obj for obj in context.selected_objects if getattr(obj, "type", None) == "MESH"
        ]
        if not meshes:
            self.report({"WARNING"}, "Select at least one mesh object to export")
            return {"CANCELLED"}

        items = build_tables(meshes, self.directory)
        if not self.overwrite:
            kept: list[BatchExportItem] = []
            skipped = 0
            for it in items:
                if it.path.exists():
                    skipped += 1
                    continue
                kept.append(it)
            if skipped:
                self.report(
                    {"WARNING"},
                    f"Skipped {skipped} existing file(s); enable Overwrite to replace",
                )
            items = kept

        results = write_tables(items, max_workers=self.max_workers or None)
        errors = [r for r in results if r.error is not None]
        for err in errors:
            self.report({"WARNING"}, f"{err.path.name}: {err.error}")

        ok = len(results) - len(errors)
        if not ok:
            self.report({"WARNING"}, "No files written")
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"Wrote {ok} NIF file(s) to {self.directory!r}",
        )
        return {"FINISHED"}
