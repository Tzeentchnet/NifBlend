"""Phase 8c: pure helpers backing generic post-import utility operators.

Blender-free / unit-testable. The matching :mod:`nifblend.ops.utilities`
module wraps each helper in a thin Operator.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

__all__ = [
    "BETHESDA_UNIT_TO_BLENDER",
    "BETHESDA_UNIT_TO_METERS",
    "DEFAULT_MERGE_DISTANCE",
    "fit_clip_distance",
    "group_loops_by_vertex",
    "group_polygons_by_material_slot",
    "recenter_offset",
    "scene_bounds_radius",
    "suggest_merge_distance",
]


#: Small-enough merge distance that BSTriShape's half-float position
#: quantisation (~1/512 of a Blender unit on the ``[-64, 64]`` range) never
#: collapses intended neighbours, large enough to sweep up the sub-``1e-4``
#: duplicates import side tends to emit on shared-seam verts.
DEFAULT_MERGE_DISTANCE: float = 1e-4


#: Bethesda's NIF unit is approximately 1.428 cm (0.01428 m). Modders
#: routinely refer to this as "the Bethesda unit". Used by
#: :func:`apply_bethesda_scale_factor` in the operator layer to scale
#: imported worldspace objects to Blender's default unit metric (1 BU = 1m).
BETHESDA_UNIT_TO_METERS: float = 0.01428


#: Same value, named for the most common usage (multiply NIF-unit
#: dimensions by this to get Blender units when Blender's scene unit
#: scale is the default 1.0).
BETHESDA_UNIT_TO_BLENDER: float = BETHESDA_UNIT_TO_METERS


def recenter_offset(
    positions: Iterable[tuple[float, float, float]],
) -> tuple[float, float, float]:
    """Mean of the positions, suitable for subtracting from each.

    Empty input → ``(0.0, 0.0, 0.0)``. No truncation (unlike
    :func:`nifblend.bridge.cell_csv.compute_origin_offset` which
    matches NifCity's int-truncation for shareable CSV offsets); this
    helper backs the standalone "Recenter Selection to Origin"
    operator and wants pixel-accurate centering.
    """
    pts = list(positions)
    if not pts:
        return (0.0, 0.0, 0.0)
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sz = sum(p[2] for p in pts)
    return (sx / n, sy / n, sz / n)


def scene_bounds_radius(
    positions: Iterable[tuple[float, float, float]],
) -> float:
    """Distance from origin to the farthest point. Empty → ``0.0``."""
    far = 0.0
    for p in positions:
        d2 = p[0] * p[0] + p[1] * p[1] + p[2] * p[2]
        if d2 > far:
            far = d2
    return far ** 0.5


def fit_clip_distance(
    positions: Iterable[tuple[float, float, float]],
    *,
    pad_factor: float = 1.5,
    minimum: float = 1000.0,
) -> float:
    """Return a viewport ``clip_end`` value that fits ``positions``.

    Bethesda cell-scale scenes routinely live at 50k-200k worldspace
    units; Blender's default ``clip_end`` of 1000 hides everything.
    NifCity exposed clip props in its panel but didn't auto-fit;
    this helper does. Falls back to ``minimum`` for empty / origin-only
    scenes so the user never gets a too-small ``clip_end``.
    """
    radius = scene_bounds_radius(positions) * float(pad_factor)
    return max(radius, float(minimum))


def suggest_merge_distance(
    positions: Iterable[tuple[float, float, float]],
    triangles: Iterable[tuple[int, int, int]] | None = None,
    *,
    fraction: float = 1e-4,
    minimum: float = 1e-6,
    maximum: float = 1e-2,
) -> float:
    """Heuristic per-scene merge distance clamped to ``[minimum, maximum]``.

    With a triangle list supplied, returns ``fraction`` times the shortest
    triangle edge in the mesh -- safe lower bound that never collapses a
    legitimate shared-seam vertex pair. Without triangles, falls back to
    ``fraction * scene_bounds_radius(positions)`` which is fine for most
    NIF-scale meshes (positions in the ``[-1000, 1000]`` range give
    `0.0001` → a sub-float-epsilon threshold).

    Empty input falls through to ``minimum``.
    """
    pts = list(positions)
    if not pts:
        return float(minimum)
    if triangles is not None:
        shortest_sq: float | None = None
        for tri in triangles:
            if not tri or len(tri) != 3:
                continue
            for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
                if a == b or a >= len(pts) or b >= len(pts):
                    continue
                pa = pts[a]
                pb = pts[b]
                dx = pa[0] - pb[0]
                dy = pa[1] - pb[1]
                dz = pa[2] - pb[2]
                d2 = dx * dx + dy * dy + dz * dz
                if d2 > 0.0 and (shortest_sq is None or d2 < shortest_sq):
                    shortest_sq = d2
        if shortest_sq is not None:
            return _clamp(float(shortest_sq) ** 0.5 * float(fraction), minimum, maximum)
    radius = scene_bounds_radius(pts)
    return _clamp(radius * float(fraction), minimum, maximum)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(float(lo), min(float(hi), float(value)))


def group_polygons_by_material_slot(
    material_indices: Iterable[int],
) -> dict[int, list[int]]:
    """Bucket polygon indices by the ``material_index`` on each polygon.

    Input is the flat sequence of ``poly.material_index`` values (one per
    polygon, in mesh order). Output is ``{slot_index: [poly_index, ...]}``,
    suitable for driving ``bpy.ops.mesh.separate(type='MATERIAL')``'s
    bookkeeping in a single pass.
    """
    out: dict[int, list[int]] = {}
    for poly_index, slot in enumerate(material_indices):
        out.setdefault(int(slot), []).append(poly_index)
    return out


def group_loops_by_vertex(
    loop_vertex_indices: Sequence[int],
    loop_uvs: Sequence[tuple[float, float]],
) -> dict[int, list[tuple[int, tuple[float, float]]]]:
    """Bucket ``(loop_index, uv)`` pairs by the vertex they reference.

    Backs the UV-seam welder: loops sharing a vertex but with UVs that
    differ by more than an epsilon define a seam. Input sequences must
    be same-length (one entry per mesh loop).
    """
    if len(loop_vertex_indices) != len(loop_uvs):
        raise ValueError(
            "loop_vertex_indices and loop_uvs must be same length; "
            f"got {len(loop_vertex_indices)} and {len(loop_uvs)}"
        )
    out: dict[int, list[tuple[int, tuple[float, float]]]] = {}
    for loop_index, (vidx, uv) in enumerate(zip(loop_vertex_indices, loop_uvs, strict=False)):
        out.setdefault(int(vidx), []).append((loop_index, (float(uv[0]), float(uv[1]))))
    return out
