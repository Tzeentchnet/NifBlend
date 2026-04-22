"""LOD-group detection (Phase 7 step 28).

Two distinct LOD encodings exist in Bethesda NIFs and we surface both
through a single :class:`LODGroup` dataclass so the operator layer
(and any future LOD viewport panel) can treat them uniformly:

* ``NiLODNode``: a switching parent node whose ``children`` are sibling
  shape blocks; each child is paired with a near/far distance range
  read out of the parent's ``lod_levels`` list. Used by Morrowind /
  Oblivion / FO3-NV legacy meshes (and by exterior Skyrim cell
  composites).
* ``BSLODTriShape``: a single shape that carries three triangle-count
  slices on the same vertex pool (``lod0_size`` / ``lod1_size`` /
  ``lod2_size``). Each level renders the first ``N`` triangles of the
  shape's ``NiTriShapeData.triangles`` array.

This module is pure (no ``bpy``); the operator wrapper lives in
:mod:`nifblend.ops.preview_lod` and walks the dataclasses returned
here to materialise per-level Blender collections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nifblend.format.generated.blocks import (
    BSLODTriShape,
    NiLODNode,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.io.block_table import BlockTable

__all__ = [
    "LODGroup",
    "LODLevel",
    "TriangleSliceLevel",
    "detect_lod_groups",
]


@dataclass(slots=True)
class LODLevel:
    """One LOD level inside a :class:`LODGroup`.

    ``block_ref`` is the absolute block-table index of the *child shape*
    that should render at this level (NiLODNode encoding).
    ``triangle_slice`` is set instead when the level is a triangle-count
    slice on a single :class:`BSLODTriShape`.
    """

    index: int
    near_extent: float = 0.0
    far_extent: float = 0.0
    block_ref: int | None = None
    triangle_slice: TriangleSliceLevel | None = None


@dataclass(slots=True)
class TriangleSliceLevel:
    """The first ``num_triangles`` triangles of ``shape_ref``'s data block."""

    shape_ref: int
    num_triangles: int


@dataclass(slots=True)
class LODGroup:
    """A switchable group of LOD levels that originated from the same parent."""

    name: str
    parent_ref: int  # block-table index of the originating LOD parent
    origin: str  # "NiLODNode" or "BSLODTriShape"
    levels: list[LODLevel] = field(default_factory=list)


# ---- detection ------------------------------------------------------------


_INVALID_REF = 0xFFFFFFFF


def detect_lod_groups(table: BlockTable) -> list[LODGroup]:
    """Return every LOD group present in ``table`` in block order.

    Returned groups are stable: NiLODNode groups appear in the order
    their parent block is laid out; BSLODTriShape groups follow.
    Groups with zero usable levels are dropped (e.g. an
    ``NiLODNode`` whose ``children`` array is empty, or a
    ``BSLODTriShape`` with all three ``lodN_size`` fields set to zero).
    """
    groups: list[LODGroup] = []
    for idx, block in enumerate(table.blocks):
        if isinstance(block, NiLODNode):
            group = _from_nilodnode(idx, block, table)
            if group is not None:
                groups.append(group)
    for idx, block in enumerate(table.blocks):
        if isinstance(block, BSLODTriShape):
            group = _from_bslodtrishape(idx, block, table)
            if group is not None:
                groups.append(group)
    return groups


def _from_nilodnode(
    idx: int, block: NiLODNode, table: BlockTable
) -> LODGroup | None:
    children = list(block.children or [])
    ranges = list(block.lod_levels or [])
    levels: list[LODLevel] = []
    for level_idx, child_ref in enumerate(children):
        if not _ref_in_range(child_ref, len(table.blocks)):
            continue
        rng = ranges[level_idx] if level_idx < len(ranges) else None
        levels.append(
            LODLevel(
                index=level_idx,
                near_extent=float(rng.near_extent) if rng is not None else 0.0,
                far_extent=float(rng.far_extent) if rng is not None else 0.0,
                block_ref=int(child_ref),
            )
        )
    if not levels:
        return None
    return LODGroup(
        name=_resolve_name(block, table) or f"NiLODNode_{idx}",
        parent_ref=idx,
        origin="NiLODNode",
        levels=levels,
    )


def _from_bslodtrishape(
    idx: int, block: BSLODTriShape, table: BlockTable
) -> LODGroup | None:
    sizes = (
        int(block.lod0_size),
        int(block.lod1_size),
        int(block.lod2_size),
    )
    if not any(sizes):
        return None
    levels: list[LODLevel] = []
    for level_idx, count in enumerate(sizes):
        if count <= 0:
            continue
        levels.append(
            LODLevel(
                index=level_idx,
                triangle_slice=TriangleSliceLevel(shape_ref=idx, num_triangles=count),
            )
        )
    if not levels:
        return None
    return LODGroup(
        name=_resolve_name(block, table) or f"BSLODTriShape_{idx}",
        parent_ref=idx,
        origin="BSLODTriShape",
        levels=levels,
    )


# ---- helpers --------------------------------------------------------------


def _ref_in_range(ref: int | None, table_len: int) -> bool:
    if ref is None:
        return False
    if ref < 0 or ref == _INVALID_REF:
        return False
    return ref < table_len


def _resolve_name(block: object, table: BlockTable) -> str | None:
    """Best-effort name lookup: inline string → string-table index → ``None``."""
    name_obj = getattr(block, "name", None)
    if name_obj is None:
        return None
    inline = getattr(name_obj, "string", None)
    if inline is not None:
        try:
            return bytes(inline.value).decode("latin-1") or None
        except (AttributeError, ValueError):
            return None
    idx_attr = getattr(name_obj, "index", None)
    idx = idx_attr if idx_attr is not None else name_obj
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return None
    if idx < 0 or idx == _INVALID_REF:
        return None
    strings = getattr(table.header, "strings", None) or []
    if idx >= len(strings):
        return None
    s = strings[idx]
    return s if s else None
