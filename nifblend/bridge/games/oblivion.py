"""Oblivion (and pre-Skyrim) triangle ↔ strip helpers (Phase 8d).

Phase 6.22 already lands the **decode** path
(:func:`nifblend.bridge.mesh_in.strips_to_triangles`); this module is
the inverse, used by an export-time utility operator that targets
``NiTriStrips`` (Morrowind / Oblivion / Fallout 3 / NV).

The stripifier here is a **greedy adjacency walk** -- not optimal in
the NvTriStrip sense, but Oblivion's runtime accepts simple strips
fine and the difference in render perf for static cell meshes is
imperceptible.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

__all__ = ["strips_to_triangles", "triangles_to_strips"]


def triangles_to_strips(
    triangles: Iterable[tuple[int, int, int]],
) -> list[list[int]]:
    """Greedy stripification of an indexed triangle list.

    Each output strip is a flat ``[v0, v1, v2, v3, ...]`` list using the
    standard D3D alternating winding rule (the inverse of
    :func:`strips_to_triangles`). Triangles that can't be appended to the
    current strip start a new strip. Degenerate triangles
    (``a == b == c`` etc.) are dropped.

    The output round-trips through :func:`strips_to_triangles` to recover
    the input *triangle set* (order may differ; per-strip walk visits
    triangles in greedy adjacency order, not original list order).
    """
    tris: list[tuple[int, int, int]] = []
    for tri in triangles:
        if not tri or len(tri) != 3:
            continue
        a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
        if a in (b, c) or b == c:
            continue
        tris.append((a, b, c))

    if not tris:
        return []

    strips: list[list[int]] = []
    used = [False] * len(tris)

    for i, tri in enumerate(tris):
        if used[i]:
            continue
        a, b, c = tri
        strip = [a, b, c]
        used[i] = True
        # walk forward: next triangle must share its first two verts
        # with the strip's last two, alternating winding.
        last2 = (b, c)
        even = True  # next triangle would be even (1-indexed: 2nd in strip)
        while True:
            j = _find_next(tris, used, last2, even)
            if j is None:
                break
            used[j] = True
            d = _next_vertex(tris[j], last2, even)
            strip.append(d)
            last2 = (last2[1], d)
            even = not even
        strips.append(strip)
    return strips


def strips_to_triangles(
    strips: Iterable[Sequence[int]],
) -> list[tuple[int, int, int]]:
    """Inverse of :func:`triangles_to_strips`.

    Re-exported here for symmetry; the canonical implementation lives in
    :func:`nifblend.bridge.mesh_in.strips_to_triangles`. We re-implement
    rather than import to avoid pulling the mesh-bridge dependencies
    into this game-specific module.
    """
    out: list[tuple[int, int, int]] = []
    for strip in strips:
        s = list(strip)
        for i in range(len(s) - 2):
            a, b, c = s[i], s[i + 1], s[i + 2]
            if a in (b, c) or b == c:
                continue
            if i % 2 == 0:
                out.append((int(a), int(b), int(c)))
            else:
                out.append((int(a), int(c), int(b)))
    return out


def _find_next(
    tris: list[tuple[int, int, int]],
    used: list[bool],
    last2: tuple[int, int],
    even: bool,
) -> int | None:
    """Find an unused triangle that extends the strip from ``last2``.

    For an even-indexed continuation (winding ``ABC``), the new triangle
    must contain ``last2[0], last2[1]`` and one new vertex with the
    arrangement ``(last2[1], last2[0], new)``. For odd continuation,
    arrangement is ``(last2[0], last2[1], new)``.
    """
    a, b = last2
    for j, tri in enumerate(tris):
        if used[j]:
            continue
        x, y, z = tri
        verts = (x, y, z)
        if a not in verts or b not in verts:
            continue
        # find the third vertex
        third = next(v for v in verts if v != a and v != b)
        # validate that ordering matches the strip's winding rule
        # (we rebuild the strip such that the implied winding is correct)
        if _matches_winding(tri, a, b, third, even):
            return j
    return None


def _matches_winding(
    tri: tuple[int, int, int],
    prev_a: int,
    prev_b: int,
    new_vert: int,
    even: bool,
) -> bool:
    """True if ``tri`` (in any rotation) has the implied strip winding."""
    rotations = [
        (tri[0], tri[1], tri[2]),
        (tri[1], tri[2], tri[0]),
        (tri[2], tri[0], tri[1]),
    ]
    target = (prev_b, prev_a, new_vert) if even else (prev_a, prev_b, new_vert)
    return target in rotations


def _next_vertex(
    tri: tuple[int, int, int],
    last2: tuple[int, int],
    _even: bool,
) -> int:
    """Return the vertex of ``tri`` not in ``last2``."""
    a, b = last2
    for v in tri:
        if v != a and v != b:
            return int(v)
    raise ValueError(f"triangle {tri!r} does not extend {last2!r}")
