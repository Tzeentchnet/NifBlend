"""Batch NIF import operator (Phase 7 step 27).

Walks a folder for ``*.nif`` files, parses + decodes each one in a thread
pool (I/O + numpy work — releases the GIL on the read side), then
materialises the resulting :class:`~nifblend.bridge.mesh_in.MeshData`
objects on the main thread (Blender's ``bpy.data.*`` collections are not
thread-safe, so we never touch them from worker threads).

The two phases are exposed as standalone helpers
(:func:`discover_nif_files`, :func:`parse_and_decode`,
:func:`materialise_batch_results`) so the headless test suite can drive
the parallel parser without a real ``bpy`` and so callers (e.g. a future
performance harness) can reuse the same parse path.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from nifblend.bridge.mesh_in import (
    MeshData,
    bssubindextrishape_to_mesh_data,
    bstrishape_to_mesh_data,
    mesh_data_to_blender,
    nitrishape_to_mesh_data,
    nitristrips_to_mesh_data,
)
from nifblend.format.generated.blocks import (
    BSSubIndexTriShape,
    BSTriShape,
    NiTriShape,
    NiTriShapeData,
    NiTriStrips,
    NiTriStripsData,
)
from nifblend.io.block_table import BlockTable, read_nif

__all__ = [
    "BatchFileResult",
    "NIFBLEND_OT_import_batch",
    "discover_nif_files",
    "materialise_batch_results",
    "parse_and_decode",
    "parse_and_decode_many",
]


@dataclass(slots=True)
class BatchFileResult:
    """One parsed file's worth of decoded geometry, ready to materialise."""

    path: Path
    meshes: list[MeshData] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    error: str | None = None


# ---- discovery ------------------------------------------------------------


def discover_nif_files(root: Path | str, *, recursive: bool = True) -> list[Path]:
    """Return every ``*.nif`` file under ``root`` (case-insensitive on Windows).

    Returned in stable sorted order so importer behaviour is deterministic.
    Symlinks are followed only one level (``Path.rglob`` default) to avoid
    accidental cycles.
    """
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(root)
    pattern = "**/*.nif" if recursive else "*.nif"
    # Case-insensitive match on Windows happens for free via the OS; on
    # POSIX we also accept ``*.NIF`` so cross-platform mods import the same.
    found: set[Path] = set()
    for pat in (pattern, pattern.replace(".nif", ".NIF")):
        for p in root.glob(pat):
            if p.is_file():
                found.add(p)
    return sorted(found)


# ---- pure parse + decode (thread-safe) -----------------------------------


def parse_and_decode(path: Path | str) -> BatchFileResult:
    """Read a NIF and decode every supported geometry block into ``MeshData``.

    Pure / thread-safe: opens the file, walks the block table, runs the
    bridge's ``*_to_mesh_data`` decoders. Touches no ``bpy`` state. Errors
    are captured on the result rather than raised so a single bad file
    doesn't cancel a 1000-file batch.
    """
    path = Path(path)
    result = BatchFileResult(path=path)
    try:
        with open(path, "rb") as fh:
            table = read_nif(fh)
    except Exception as exc:  # surface to the operator's report dialog
        result.error = f"read failed: {exc}"
        return result

    for block in table.blocks:
        try:
            mdata = _decode_block(block, table)
        except Exception as exc:
            result.skipped.append(f"{type(block).__name__} (decode failed: {exc})")
            continue
        if mdata is None:
            result.skipped.append(type(block).__name__)
        else:
            result.meshes.append(mdata)
    return result


def parse_and_decode_many(
    paths: list[Path] | list[str],
    *,
    max_workers: int | None = None,
) -> list[BatchFileResult]:
    """Parallel version of :func:`parse_and_decode` over ``paths``.

    Uses a thread pool because the bottleneck is file I/O + numpy bulk
    array reads; both release the GIL. Result order matches input order.
    """
    if not paths:
        return []
    workers = max_workers if max_workers and max_workers > 0 else min(
        32, (os.cpu_count() or 1) + 4
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(parse_and_decode, paths))


# ---- main-thread materialisation -----------------------------------------


def materialise_batch_results(
    results: list[BatchFileResult],
    *,
    bpy: Any = None,
    collection_per_file: bool = True,
) -> tuple[int, list[str]]:
    """Turn batch parse results into Blender objects on the main thread.

    Returns ``(imported_count, error_messages)``. ``error_messages``
    aggregates per-file failures and per-block decode skips so the operator
    can roll them into a single user-facing report.

    When ``collection_per_file`` is True each file's meshes are linked into
    a fresh :class:`bpy.types.Collection` named after the file's stem;
    otherwise everything is parented to the active scene collection.
    """
    if bpy is None:
        import bpy as bpy

    scene = bpy.context.scene
    root_collection = scene.collection if scene is not None else None

    imported = 0
    errors: list[str] = []
    for res in results:
        if res.error is not None:
            errors.append(f"{res.path.name}: {res.error}")
            continue
        if res.skipped:
            errors.append(
                f"{res.path.name}: skipped {len(res.skipped)} block(s) "
                f"({sorted(set(res.skipped))})"
            )
        if not res.meshes:
            continue
        target = root_collection
        if collection_per_file and root_collection is not None:
            target = bpy.data.collections.new(res.path.stem)
            root_collection.children.link(target)
        for mdata in res.meshes:
            mesh = mesh_data_to_blender(mdata, bpy=bpy)
            obj = bpy.data.objects.new(mesh.name, mesh)
            if target is not None:
                target.objects.link(obj)
            imported += 1
    return imported, errors


# ---- private helpers ------------------------------------------------------


def _decode_block(block: object, table: BlockTable) -> MeshData | None:
    """Dispatch one block to the matching bridge decoder, or ``None``."""
    if isinstance(block, BSTriShape) and not isinstance(block, BSSubIndexTriShape):
        # BSSubIndexTriShape *is-a* BSTriShape in the schema; route the FO4
        # subclass through its own decoder so segment-aware data comes out
        # right.
        return bstrishape_to_mesh_data(block, table)
    if isinstance(block, BSSubIndexTriShape):
        return bssubindextrishape_to_mesh_data(block, table)
    if isinstance(block, NiTriShape):
        data = _resolve_geometry_data(table, block.data, NiTriShapeData)
        if data is None:
            return None
        return nitrishape_to_mesh_data(block, data, table)
    if isinstance(block, NiTriStrips):
        data = _resolve_geometry_data(table, block.data, NiTriStripsData)
        if data is None:
            return None
        return nitristrips_to_mesh_data(block, data, table)
    return None


def _resolve_geometry_data(
    table: BlockTable, ref: int, expected_type: type
) -> object | None:
    if ref is None or ref < 0 or ref == 0xFFFFFFFF:
        return None
    if ref >= len(table.blocks):
        return None
    block = table.blocks[ref]
    if not isinstance(block, expected_type):
        return None
    return block


# ---- operator -------------------------------------------------------------


class NIFBLEND_OT_import_batch(Operator, ImportHelper):
    """Import every ``.nif`` under a folder in one click."""

    bl_idname = "nifblend.import_batch"
    bl_label = "Import NIF Folder (Batch)"
    bl_options = {"REGISTER", "UNDO"}

    # ImportHelper expects a filename_ext; we open a folder picker by
    # consuming only the dirname of self.filepath, but Blender's file dialog
    # still filters in the file list pane.
    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    directory: StringProperty(  # type: ignore[valid-type]
        name="Directory",
        subtype="DIR_PATH",
        description="Folder containing .nif files to import",
    )
    recursive: BoolProperty(  # type: ignore[valid-type]
        name="Recursive",
        description="Walk subdirectories",
        default=True,
    )
    collection_per_file: BoolProperty(  # type: ignore[valid-type]
        name="Collection Per File",
        description="Create a Blender collection for each imported NIF",
        default=True,
    )
    max_workers: IntProperty(  # type: ignore[valid-type]
        name="Worker Threads",
        description="0 = auto (min(32, cpu_count + 4))",
        default=0,
        min=0,
        max=64,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        root = self.directory or os.path.dirname(self.filepath)
        if not root:
            self.report({"ERROR"}, "Pick a folder to import")
            return {"CANCELLED"}
        try:
            paths = discover_nif_files(root, recursive=self.recursive)
        except NotADirectoryError:
            self.report({"ERROR"}, f"Not a directory: {root!r}")
            return {"CANCELLED"}
        if not paths:
            self.report({"WARNING"}, f"No .nif files found under {root!r}")
            return {"CANCELLED"}

        results = parse_and_decode_many(
            paths, max_workers=self.max_workers or None
        )
        imported, errors = materialise_batch_results(
            results, collection_per_file=self.collection_per_file
        )

        for msg in errors:
            self.report({"WARNING"}, msg)
        if not imported:
            self.report(
                {"WARNING"},
                f"No geometry imported from {len(paths)} file(s)",
            )
            return {"CANCELLED"}
        self.report(
            {"INFO"},
            f"Imported {imported} mesh(es) from {len(paths)} file(s)",
        )
        return {"FINISHED"}
