"""Fallout 4 / 76 promotion + mesh-link helpers (Phase 8g).

Pure logic feeding ``ops/games_fallout.py``. Two concerns:

* **FO4 segment promotion** -- turn a plain ``BSTriShape`` triangle
  count into the minimum :class:`nifblend.bridge.mesh_in.MeshSegments`
  sidecar required by ``BSSubIndexTriShape`` (a single full-range
  segment covering every triangle, no sub-segments, no SSF file).
* **FO76 external mesh slots** -- FO76's ``BSGeometry`` carries up to
  four ``BSMeshArray`` LOD slots whose geometry lives in external
  ``.mesh`` files. This module exposes the pure helpers the operator
  layer uses to populate / validate those slot entries.

Both helpers stay import-side-agnostic: they operate on plain
dataclasses / primitive values and never touch ``bpy``.
"""

from __future__ import annotations

from dataclasses import dataclass

from nifblend.bridge.mesh_in import BSGeometryMeshRef, MeshSegment, MeshSegments

__all__ = [
    "FO76_MESH_SLOT_COUNT",
    "ExternalMeshLink",
    "normalise_fo76_slots",
    "promote_triangles_to_segments",
    "validate_segment_coverage",
]


#: ``BSGeometry`` always carries exactly four ``BSMeshArray`` LOD slots
#: (LOD0 .. LOD3). Slots past the populated ones have ``has_mesh=False``.
FO76_MESH_SLOT_COUNT: int = 4


@dataclass(slots=True)
class ExternalMeshLink:
    """One populated FO76 LOD slot -- the operator surface."""

    lod_index: int
    mesh_path: str
    num_verts: int = 0
    indices_size: int = 0
    flags: int = 0


def promote_triangles_to_segments(num_triangles: int) -> MeshSegments:
    """Build the default FO4 segment sidecar for ``num_triangles`` triangles.

    A plain ``BSTriShape`` has no segment metadata. Promoting it to a
    ``BSSubIndexTriShape`` needs *at least* one segment that covers the
    full index range; this helper emits exactly that (no sub-segments,
    no SSF file, no per-segment user indices).

    Raises :class:`ValueError` for negative triangle counts.
    """
    if num_triangles < 0:
        raise ValueError(f"num_triangles must be >= 0, got {num_triangles}")
    segments = [
        MeshSegment(
            start_index=0,
            num_primitives=num_triangles * 3,
            parent_array_index=0xFFFFFFFF,
            sub_segments=[],
        )
    ]
    return MeshSegments(
        num_primitives=num_triangles * 3,
        total_segments=1,
        segments=segments,
        ssf_file="",
        per_segment_user_indices=[],
    )


def validate_segment_coverage(segments: MeshSegments) -> list[str]:
    """Return a list of human-readable coverage warnings, empty on success.

    Checks: every triangle index is covered by exactly one segment,
    segments don't overlap, ``num_primitives`` agrees with the sum of
    per-segment ``num_primitives``, sub-segment parent indices point at
    real segment slots.
    """
    warnings: list[str] = []
    total = 0
    prev_end = 0
    for i, seg in enumerate(segments.segments):
        if seg.start_index != prev_end:
            warnings.append(
                f"segment {i}: start_index {seg.start_index} != previous end {prev_end}"
            )
        total += seg.num_primitives
        prev_end = seg.start_index + seg.num_primitives
        for j, sub in enumerate(seg.sub_segments or ()):
            parent = sub.parent_array_index
            if parent != 0xFFFFFFFF and not (0 <= parent < len(segments.segments)):
                warnings.append(
                    f"segment {i} sub-segment {j}: parent_array_index "
                    f"{parent} out of range"
                )
    if total != segments.num_primitives:
        warnings.append(
            f"segment sum num_primitives {total} != header {segments.num_primitives}"
        )
    return warnings


def normalise_fo76_slots(
    links: list[ExternalMeshLink],
) -> list[BSGeometryMeshRef]:
    """Expand a sparse list of :class:`ExternalMeshLink` into four LOD slots.

    Callers only populate the LOD levels they actually have; this
    helper fills the gaps with empty slots (``has_mesh=False``) so the
    output is always exactly :data:`FO76_MESH_SLOT_COUNT` entries in
    ``lod_index`` order. Duplicate ``lod_index`` values keep the last
    occurrence (last-wins). ``lod_index`` outside ``[0, 4)`` is
    silently dropped.
    """
    buckets: dict[int, ExternalMeshLink] = {}
    for link in links:
        if 0 <= link.lod_index < FO76_MESH_SLOT_COUNT:
            buckets[link.lod_index] = link
    out: list[BSGeometryMeshRef] = []
    for i in range(FO76_MESH_SLOT_COUNT):
        link = buckets.get(i)
        if link is None or not link.mesh_path:
            out.append(BSGeometryMeshRef(lod_index=i, has_mesh=False))
            continue
        out.append(
            BSGeometryMeshRef(
                lod_index=i,
                has_mesh=True,
                mesh_path=str(link.mesh_path),
                num_verts=int(link.num_verts),
                indices_size=int(link.indices_size),
                flags=int(link.flags),
            )
        )
    return out
