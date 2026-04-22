"""Import side of the BSTriShape ↔ Blender mesh bridge (Phase 2 step 8).

The bridge is split in two so the heavy lifting stays testable headlessly:

* :func:`bstrishape_to_mesh_data` -- pure function that turns a parsed
  :class:`BSTriShape` block (plus its enclosing :class:`BlockTable` for
  string-table lookup) into a :class:`MeshData` of dense numpy arrays. No
  ``bpy`` dependency.
* :func:`mesh_data_to_blender` -- thin wrapper that materialises a
  :class:`MeshData` as a ``bpy.types.Mesh`` via ``foreach_set``. Imports
  ``bpy`` lazily so unit tests can exercise the conversion path without
  Blender installed.

BSTriShape is treated as a first-class shape (no NiTriShape conversion). We
decode the per-vertex packed records the codegen emitted as
``list[BSVertexDataSSE | None]`` into numpy arrays here; the packed-dtype
fast path in :mod:`nifblend.format.primitives` is reserved for a future
codegen widening.

Coordinate spaces are passed through unchanged -- the NIF stores positions
in object-local space and the bridge does not (yet) apply BSTriShape's
``translation`` / ``rotation`` / ``scale``. Callers that need world-space
geometry must apply the transform themselves; see
:meth:`MeshData.transform` for the canonical formula.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.blocks import (
    BSGeometry,
    BSSubIndexTriShape,
    BSTriShape,
    NiTriShape,
    NiTriShapeData,
    NiTriStrips,
    NiTriStripsData,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.io.block_table import BlockTable


__all__ = [
    "BSGeometryMeshRef",
    "MeshData",
    "MeshSegment",
    "MeshSegments",
    "MeshSubSegment",
    "bsgeometry_mesh_refs",
    "bssubindextrishape_segments",
    "bssubindextrishape_to_mesh_data",
    "bstrishape_to_mesh_data",
    "import_bstrishape",
    "mesh_data_to_blender",
    "nitrishape_to_mesh_data",
    "nitristrips_to_mesh_data",
    "strips_to_triangles",
]


# Vertex-attribute bits on BSVertexDesc.vertex_attributes (mirrored from the
# schema). Kept here so the bridge does not need to import primitives just to
# read flags.
_VA_VERTEX = 0x001
_VA_UV = 0x002
_VA_NORMALS = 0x008
_VA_TANGENTS = 0x010
_VA_COLORS = 0x020
_VA_SKINNED = 0x040
_VA_FULL_PRECISION = 0x400


@dataclass(slots=True)
class MeshData:
    """Dense numpy view of a single BSTriShape, ready for ``foreach_set``."""

    name: str
    positions: npt.NDArray[np.float32]  # (N, 3)
    triangles: npt.NDArray[np.uint32]  # (M, 3)
    normals: npt.NDArray[np.float32] | None = None  # (N, 3)
    tangents: npt.NDArray[np.float32] | None = None  # (N, 3)
    bitangents: npt.NDArray[np.float32] | None = None  # (N, 3)
    uv: npt.NDArray[np.float32] | None = None  # (N, 2)
    vertex_colors: npt.NDArray[np.float32] | None = None  # (N, 4) RGBA in [0, 1]
    bone_weights: npt.NDArray[np.float32] | None = None  # (N, 4)
    bone_indices: npt.NDArray[np.uint8] | None = None  # (N, 4)


# ---- block → MeshData -----------------------------------------------------


def bstrishape_to_mesh_data(
    block: BSTriShape,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
) -> MeshData:
    """Convert a parsed :class:`BSTriShape` into a :class:`MeshData`.

    ``table`` is consulted only to resolve ``block.name`` (a u32 index into
    the header string table) into a Python ``str``. If ``name`` is provided
    it overrides the lookup, and ``table`` may be ``None`` (useful for
    synthesised tests).
    """
    resolved_name = name if name is not None else _resolve_name(block, table)
    desc = _vertex_desc_attributes(block)
    vertex_data = block.vertex_data or []
    triangles = _triangles_to_array(block.triangles or [])
    positions = _vertices_to_array(vertex_data)

    has_uv = bool(desc & _VA_UV)
    has_normals = bool(desc & _VA_NORMALS)
    has_tangents = bool(desc & _VA_TANGENTS) and has_normals
    has_colors = bool(desc & _VA_COLORS)
    has_skin = bool(desc & _VA_SKINNED)

    return MeshData(
        name=resolved_name,
        positions=positions,
        triangles=triangles,
        normals=_byte_vec3_to_unit(vertex_data, "normal") if has_normals else None,
        tangents=_byte_vec3_to_unit(vertex_data, "tangent") if has_tangents else None,
        bitangents=_bitangents_to_array(vertex_data) if has_tangents else None,
        uv=_uvs_to_array(vertex_data) if has_uv else None,
        vertex_colors=_colors_to_array(vertex_data) if has_colors else None,
        bone_weights=_bone_weights_to_array(vertex_data) if has_skin else None,
        bone_indices=_bone_indices_to_array(vertex_data) if has_skin else None,
    )


# ---- MeshData → bpy.types.Mesh -------------------------------------------


def mesh_data_to_blender(data: MeshData, *, bpy: Any = None) -> Any:
    """Materialise ``data`` as a Blender ``bpy.types.Mesh``.

    ``bpy`` is injected so headless tests can pass a fake module; production
    callers leave it as ``None`` and we import the real ``bpy`` lazily.
    """
    if bpy is None:
        import bpy as bpy  # (lazy import; keep name local)

    mesh = bpy.data.meshes.new(data.name)
    mesh.from_pydata(
        data.positions.tolist(),
        [],
        data.triangles.tolist(),
    )

    if data.normals is not None:
        # Per-loop normals; replicate the per-vertex normal across each
        # triangle's three loops. ``foreach_set`` wants a flat float buffer.
        loop_normals = data.normals[data.triangles.reshape(-1)].astype(np.float32, copy=False)
        mesh.normals_split_custom_set(loop_normals.reshape(-1, 3).tolist())
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True

    if data.uv is not None:
        uv_layer = mesh.uv_layers.new(name="UVMap")
        # NIF V is top-down, Blender V is bottom-up.
        uvs = data.uv.copy()
        uvs[:, 1] = 1.0 - uvs[:, 1]
        loop_uv = uvs[data.triangles.reshape(-1)].astype(np.float32, copy=False)
        uv_layer.data.foreach_set("uv", loop_uv.reshape(-1))

    if data.vertex_colors is not None:
        # Prefer the modern color_attributes API (Blender 3.2+); fall back to
        # the legacy vertex_colors layer for compatibility with older stubs.
        if hasattr(mesh, "color_attributes"):
            attr = mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="POINT")
            attr.data.foreach_set("color", data.vertex_colors.reshape(-1).tolist())
        else:  # pragma: no cover - legacy path
            layer = mesh.vertex_colors.new(name="Color")
            loop_col = data.vertex_colors[data.triangles.reshape(-1)]
            layer.data.foreach_set("color", loop_col.reshape(-1).tolist())

    mesh.update()
    return mesh


# ---- top-level convenience ------------------------------------------------


def import_bstrishape(
    block: BSTriShape,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    bpy: Any = None,
) -> Any:
    """Convert ``block`` into a Blender mesh in one call."""
    data = bstrishape_to_mesh_data(block, table, name=name)
    return mesh_data_to_blender(data, bpy=bpy)


# ---- private helpers ------------------------------------------------------


def _resolve_name(block: Any, table: BlockTable | None) -> str:
    """Resolve the geometry block's ``name`` into a Python string.

    Works for any block that exposes a ``name`` attribute holding either an
    inline ``string`` (legacy, pre-20.1.0.3) or a u32 string-table index.
    BSTriShape, NiTriShape and NiTriStrips all share this layout via the
    schema's ``string`` substrate.
    """
    name_obj = block.name
    if name_obj is None:
        return type(block).__name__

    # Inline legacy string (pre-20.1.0.3): use it directly, no table lookup.
    inline = getattr(name_obj, "string", None)
    if inline is not None:
        try:
            return bytes(inline.value).decode("latin-1")
        except (AttributeError, ValueError):
            pass

    # Modern string-table index path.
    idx_attr = getattr(name_obj, "index", None)
    idx = idx_attr if idx_attr is not None else name_obj
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return type(block).__name__
    if idx < 0 or idx == 0xFFFFFFFF or table is None:
        return type(block).__name__
    strings = table.header.strings
    if idx >= len(strings):
        return type(block).__name__
    s = strings[idx]
    if s is None:
        return type(block).__name__
    return bytes(s.value).decode("latin-1")


def _vertex_desc_attributes(block: BSTriShape) -> int:
    desc = block.vertex_desc
    if desc is None:
        return 0
    return int(desc.vertex_attributes)


def _triangles_to_array(triangles: list[Any]) -> npt.NDArray[np.uint32]:
    if not triangles:
        return np.empty((0, 3), dtype=np.uint32)
    out = np.empty((len(triangles), 3), dtype=np.uint32)
    for i, t in enumerate(triangles):
        out[i, 0] = t.v1
        out[i, 1] = t.v2
        out[i, 2] = t.v3
    return out


def _vertices_to_array(vertex_data: list[Any]) -> npt.NDArray[np.float32]:
    n = len(vertex_data)
    out = np.zeros((n, 3), dtype=np.float32)
    for i, v in enumerate(vertex_data):
        if v is None or v.vertex is None:
            continue
        out[i, 0] = v.vertex.x
        out[i, 1] = v.vertex.y
        out[i, 2] = v.vertex.z
    return out


def _byte_vec3_to_unit(vertex_data: list[Any], attr: str) -> npt.NDArray[np.float32]:
    """Decode a ByteVector3 attribute into unit-vector floats.

    Per the BSVertexData schema comment, byte fields for normal/tangent/
    bitangent map ``[0, 255]`` linearly to ``[-1, 1]``.
    """
    n = len(vertex_data)
    raw = np.zeros((n, 3), dtype=np.uint8)
    for i, v in enumerate(vertex_data):
        if v is None:
            continue
        bv = getattr(v, attr, None)
        if bv is None:
            continue
        raw[i, 0] = bv.x
        raw[i, 1] = bv.y
        raw[i, 2] = bv.z
    return raw.astype(np.float32) / 127.5 - 1.0


def _bitangents_to_array(vertex_data: list[Any]) -> npt.NDArray[np.float32]:
    """Reconstruct bitangents from the (bitangent_x, bitangent_y, bitangent_z) trio.

    ``bitangent_x`` is stored as a half/full float on the vertex record;
    ``bitangent_y`` and ``bitangent_z`` are u8s packed into the normal /
    tangent records. The y/z components use the same [-1, 1] mapping as the
    other byte fields.
    """
    n = len(vertex_data)
    out = np.zeros((n, 3), dtype=np.float32)
    for i, v in enumerate(vertex_data):
        if v is None:
            continue
        out[i, 0] = float(v.bitangent_x)
        out[i, 1] = float(v.bitangent_y) / 127.5 - 1.0
        out[i, 2] = float(v.bitangent_z) / 127.5 - 1.0
    return out


def _uvs_to_array(vertex_data: list[Any]) -> npt.NDArray[np.float32]:
    n = len(vertex_data)
    out = np.zeros((n, 2), dtype=np.float32)
    for i, v in enumerate(vertex_data):
        if v is None or v.uv is None:
            continue
        out[i, 0] = v.uv.u
        out[i, 1] = v.uv.v
    return out


def _colors_to_array(vertex_data: list[Any]) -> npt.NDArray[np.float32]:
    n = len(vertex_data)
    raw = np.zeros((n, 4), dtype=np.uint8)
    for i, v in enumerate(vertex_data):
        if v is None or v.vertex_colors is None:
            continue
        c = v.vertex_colors
        raw[i, 0] = c.r
        raw[i, 1] = c.g
        raw[i, 2] = c.b
        raw[i, 3] = c.a
    return raw.astype(np.float32) / 255.0


def _bone_weights_to_array(vertex_data: list[Any]) -> npt.NDArray[np.float32]:
    n = len(vertex_data)
    out = np.zeros((n, 4), dtype=np.float32)
    for i, v in enumerate(vertex_data):
        if v is None or not v.bone_weights:
            continue
        weights = v.bone_weights[:4]
        out[i, : len(weights)] = weights
    return out


def _bone_indices_to_array(vertex_data: list[Any]) -> npt.NDArray[np.uint8]:
    n = len(vertex_data)
    out = np.zeros((n, 4), dtype=np.uint8)
    for i, v in enumerate(vertex_data):
        if v is None or not v.bone_indices:
            continue
        idx = v.bone_indices[:4]
        out[i, : len(idx)] = idx
    return out


# ---- NiTriShape / NiTriStrips (Phase 6 step 22 — Oblivion path) ----------
#
# Pre-Skyrim Bethesda games (Morrowind, Oblivion, FO3/NV) and any non-
# Bethesda NIF use the classic NiTriShape (indexed triangles) and
# NiTriStrips (D3D triangle strips) geometry pair. Vertex / normal / colour
# / UV streams live on the ``data`` block (NiTriShapeData / NiTriStripsData)
# rather than packed onto the shape itself, and triangles are either a flat
# ``Triangle`` list or have to be reconstructed from strip indices.
#
# Strips are converted to indexed triangles up front so the rest of the
# bridge (and Blender) only ever sees the same ``MeshData`` shape produced
# by ``bstrishape_to_mesh_data``. BSTriShape stays first-class on its own
# code path; the legacy decoders are additive.


def strips_to_triangles(
    strip_lengths: Iterable[int],
    points: Iterable[Iterable[int]],
) -> npt.NDArray[np.uint32]:
    """Convert NIF triangle-strip data into an ``(M, 3)`` triangle index array.

    NIF stores strips in the D3D / OpenGL convention: each strip is a flat
    list of vertex indices ``[a, b, c, d, e, …]`` representing the triangles
    ``(a, b, c), (b, c, d), (c, d, e), …`` with **alternating winding** —
    the second, fourth, sixth, … triangles get their last two indices
    swapped so every emitted triangle has consistent CCW orientation.
    Degenerate triangles (any two indices equal — used by content tools to
    stitch multiple strips into a single one) are silently dropped.
    """
    lengths = list(strip_lengths)
    rows = list(points)
    if len(rows) != len(lengths):
        # The schema says the two arrays are parallel; tolerate truncation
        # by walking only the common prefix (defensive against malformed
        # files), but never read past the declared row width.
        common = min(len(rows), len(lengths))
        rows = rows[:common]
        lengths = lengths[:common]

    out: list[tuple[int, int, int]] = []
    for length, row in zip(lengths, rows, strict=True):
        seq = list(row)[: int(length)]
        if len(seq) < 3:
            continue
        for i in range(len(seq) - 2):
            a, b, c = seq[i], seq[i + 1], seq[i + 2]
            if a in (b, c) or b == c:
                continue
            if i % 2 == 0:
                out.append((a, b, c))
            else:
                out.append((a, c, b))
    if not out:
        return np.empty((0, 3), dtype=np.uint32)
    return np.asarray(out, dtype=np.uint32)


def nitrishape_to_mesh_data(
    shape: NiTriShape,
    data: NiTriShapeData,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
) -> MeshData:
    """Convert a classic ``NiTriShape`` + ``NiTriShapeData`` pair into ``MeshData``.

    The shape block carries the scene-graph metadata (transform, name, prop
    refs); the data block carries the vertex / normal / UV / colour streams
    and a flat triangle list. Resolved as parallel arrays via the same
    ``MeshData`` container used by the BSTriShape path so downstream Blender
    materialisation is uniform.
    """
    resolved_name = name if name is not None else _resolve_name(shape, table)
    return MeshData(
        name=resolved_name,
        positions=_geom_positions_to_array(data),
        triangles=_triangle_list_to_array(data.triangles or []),
        normals=_geom_vec3_to_array(data.normals) if data.has_normals else None,
        tangents=_geom_vec3_to_array(data.tangents) if data.tangents else None,
        bitangents=_geom_vec3_to_array(data.bitangents) if data.bitangents else None,
        uv=_geom_first_uv_set(data.uv_sets),
        vertex_colors=_geom_colors_to_array(data.vertex_colors) if data.has_vertex_colors else None,
    )


def nitristrips_to_mesh_data(
    strips: NiTriStrips,
    data: NiTriStripsData,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
) -> MeshData:
    """Convert a classic ``NiTriStrips`` + ``NiTriStripsData`` pair into ``MeshData``.

    Identical to :func:`nitrishape_to_mesh_data` but rebuilds the indexed
    triangle list from the strip points via :func:`strips_to_triangles`.
    """
    resolved_name = name if name is not None else _resolve_name(strips, table)
    return MeshData(
        name=resolved_name,
        positions=_geom_positions_to_array(data),
        triangles=strips_to_triangles(
            data.strip_lengths if data.strip_lengths is not None else (),
            data.points or (),
        ),
        normals=_geom_vec3_to_array(data.normals) if data.has_normals else None,
        tangents=_geom_vec3_to_array(data.tangents) if data.tangents else None,
        bitangents=_geom_vec3_to_array(data.bitangents) if data.bitangents else None,
        uv=_geom_first_uv_set(data.uv_sets),
        vertex_colors=_geom_colors_to_array(data.vertex_colors) if data.has_vertex_colors else None,
    )


def _geom_positions_to_array(data: Any) -> npt.NDArray[np.float32]:
    verts = data.vertices or []
    n = int(getattr(data, "num_vertices", len(verts)) or len(verts))
    if n == 0:
        return np.empty((0, 3), dtype=np.float32)
    out = np.zeros((n, 3), dtype=np.float32)
    for i, v in enumerate(verts[:n]):
        if v is None:
            continue
        out[i, 0] = v.x
        out[i, 1] = v.y
        out[i, 2] = v.z
    return out


def _triangle_list_to_array(triangles: list[Any]) -> npt.NDArray[np.uint32]:
    if not triangles:
        return np.empty((0, 3), dtype=np.uint32)
    out = np.empty((len(triangles), 3), dtype=np.uint32)
    for i, t in enumerate(triangles):
        if t is None:
            out[i] = (0, 0, 0)
            continue
        out[i, 0] = t.v1
        out[i, 1] = t.v2
        out[i, 2] = t.v3
    return out


def _geom_vec3_to_array(vectors: list[Any]) -> npt.NDArray[np.float32] | None:
    if not vectors:
        return None
    out = np.zeros((len(vectors), 3), dtype=np.float32)
    for i, v in enumerate(vectors):
        if v is None:
            continue
        out[i, 0] = v.x
        out[i, 1] = v.y
        out[i, 2] = v.z
    return out


def _geom_colors_to_array(colors: list[Any]) -> npt.NDArray[np.float32] | None:
    if not colors:
        return None
    out = np.zeros((len(colors), 4), dtype=np.float32)
    for i, c in enumerate(colors):
        if c is None:
            continue
        out[i, 0] = c.r
        out[i, 1] = c.g
        out[i, 2] = c.b
        out[i, 3] = c.a
    return out


def _geom_first_uv_set(uv_sets: list[Any]) -> npt.NDArray[np.float32] | None:
    """Return UV set 0 as an ``(N, 2)`` float32 array, or ``None`` when absent.

    Pre-Skyrim NIFs store UVs as a 2D ``[num_uv_sets][num_vertices]`` jagged
    grid (see :class:`NiTriShapeData.uv_sets` after the codegen width fix).
    Blender only consumes one set in v0.1, so we take the first row.
    """
    if not uv_sets:
        return None
    first = uv_sets[0]
    if first is None:
        return None
    if not first:
        return None
    out = np.zeros((len(first), 2), dtype=np.float32)
    for i, uv in enumerate(first):
        if uv is None:
            continue
        out[i, 0] = uv.u
        out[i, 1] = uv.v
    return out


# ---- BSSubIndexTriShape / BSGeometry (Phase 6 step 24 — FO4 / FO76) ------
#
# Fallout 4 (bs_version 130-139) introduces ``BSSubIndexTriShape``: the same
# packed BSVertexData layout as ``BSTriShape`` (so the bridge reuses every
# ``_byte_vec3_to_unit`` / ``_uvs_to_array`` helper), plus a per-shape list
# of ``BSGeometrySegmentData`` entries that carve the triangle list into
# named body-part / LOD ranges and an optional shared-data sidecar
# (``BSGeometrySegmentSharedData``) carrying sub-segment cut offsets and an
# external SSF (sub-segment-file) path.
#
# Fallout 76 (bs_version 155+) replaces the inline geometry entirely with
# ``BSGeometry``: up to four ``BSMeshArray`` LOD slots, each pointing at an
# external ``.mesh`` file that lives outside the NIF. The NIF only carries
# the path + vertex / index sizes + flags; the actual streams are parsed
# elsewhere (deferred to the Starfield-tier external-asset work).
#
# Geometry decoding for BSSubIndexTriShape goes through the existing
# BSTriShape helpers — ``BSVertexData`` (FO4) and ``BSVertexDataSSE`` (SSE)
# share field names so attribute-based access is uniform. Segments and
# external mesh refs are surfaced as separate dataclasses; PropertyGroup
# wiring (so the metadata round-trips through Blender) follows the same
# operator-pass pattern as Phase 6.22 / 6.23.


@dataclass(slots=True)
class MeshSubSegment:
    """One ``BSGeometrySubSegment`` row (FO4 SITS shared data)."""

    start_index: int
    num_primitives: int
    parent_array_index: int
    unused: int = 0


@dataclass(slots=True)
class MeshSegment:
    """One ``BSGeometrySegmentData`` entry on a BSSubIndexTriShape."""

    start_index: int
    num_primitives: int
    parent_array_index: int = 0
    sub_segments: list[MeshSubSegment] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.sub_segments is None:
            self.sub_segments = []


@dataclass(slots=True)
class MeshSegments:
    """Sidecar segment metadata for a :class:`BSSubIndexTriShape`.

    ``segments`` is the per-shape ``BSGeometrySegmentData`` list (with
    nested sub-segments flattened into :class:`MeshSubSegment` rows).
    ``num_primitives`` / ``total_segments`` / ``ssf_file`` /
    ``per_segment_user_indices`` mirror the optional shared-data block
    that FO4 emits when the shape uses sub-segments.
    """

    num_primitives: int
    total_segments: int
    segments: list[MeshSegment]
    ssf_file: str = ""
    per_segment_user_indices: list[tuple[int, int]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.per_segment_user_indices is None:
            self.per_segment_user_indices = []


@dataclass(slots=True)
class BSGeometryMeshRef:
    """One ``BSMeshArray`` slot on a :class:`BSGeometry` (FO76)."""

    lod_index: int
    has_mesh: bool
    mesh_path: str = ""
    num_verts: int = 0
    indices_size: int = 0
    flags: int = 0


def bssubindextrishape_to_mesh_data(
    block: BSSubIndexTriShape,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
) -> MeshData:
    """Convert a parsed :class:`BSSubIndexTriShape` into a :class:`MeshData`.

    The vertex layout matches BSTriShape, so all the existing per-attribute
    decoders (positions / UVs / normals / tangents / colours / skin) are
    reused verbatim. Segment metadata is *not* embedded in :class:`MeshData`
    — call :func:`bssubindextrishape_segments` to harvest it as a sidecar.
    """
    resolved_name = name if name is not None else _resolve_name(block, table)
    desc = _vertex_desc_attributes(block)
    vertex_data = block.vertex_data or []
    triangles = _triangles_to_array(block.triangles or [])
    positions = _vertices_to_array(vertex_data)

    has_uv = bool(desc & _VA_UV)
    has_normals = bool(desc & _VA_NORMALS)
    has_tangents = bool(desc & _VA_TANGENTS) and has_normals
    has_colors = bool(desc & _VA_COLORS)
    has_skin = bool(desc & _VA_SKINNED)

    return MeshData(
        name=resolved_name,
        positions=positions,
        triangles=triangles,
        normals=_byte_vec3_to_unit(vertex_data, "normal") if has_normals else None,
        tangents=_byte_vec3_to_unit(vertex_data, "tangent") if has_tangents else None,
        bitangents=_bitangents_to_array(vertex_data) if has_tangents else None,
        uv=_uvs_to_array(vertex_data) if has_uv else None,
        vertex_colors=_colors_to_array(vertex_data) if has_colors else None,
        bone_weights=_bone_weights_to_array(vertex_data) if has_skin else None,
        bone_indices=_bone_indices_to_array(vertex_data) if has_skin else None,
    )


def bssubindextrishape_segments(block: BSSubIndexTriShape) -> MeshSegments | None:
    """Decode the segment sidecar on a :class:`BSSubIndexTriShape`.

    Returns ``None`` when the shape has no segments (an empty SITS, or a
    pre-130 ``bs_version`` shape that didn't read the segment block).
    The shared-data block (sub-segments + SSF file) is folded into the
    per-segment :class:`MeshSubSegment` rows by ``parent_array_index``.
    """
    raw_segments = list(block.segment or [])
    shared = block.segment_data
    if not raw_segments and shared is None:
        return None

    segments: list[MeshSegment] = []
    for seg in raw_segments:
        if seg is None:
            continue
        sub_rows: list[MeshSubSegment] = []
        for sub in seg.sub_segment or ():
            if sub is None:
                continue
            sub_rows.append(
                MeshSubSegment(
                    start_index=int(sub.start_index),
                    num_primitives=int(sub.num_primitives),
                    parent_array_index=int(sub.parent_array_index),
                    unused=int(sub.unused),
                )
            )
        segments.append(
            MeshSegment(
                start_index=int(seg.start_index),
                num_primitives=int(seg.num_primitives),
                parent_array_index=int(seg.parent_array_index),
                sub_segments=sub_rows,
            )
        )

    ssf_file = ""
    user_indices: list[tuple[int, int]] = []
    total_segments = int(block.total_segments)
    if shared is not None:
        ssf_file = _decode_sized_string(shared.ssf_file)
        for entry in shared.per_segment_data or ():
            if entry is None:
                continue
            user_indices.append((int(entry.user_index), int(entry.bone_id)))
        if not total_segments:
            total_segments = int(shared.total_segments)

    return MeshSegments(
        num_primitives=int(block.num_primitives),
        total_segments=total_segments or len(segments),
        segments=segments,
        ssf_file=ssf_file,
        per_segment_user_indices=user_indices,
    )


def bsgeometry_mesh_refs(block: BSGeometry) -> list[BSGeometryMeshRef]:
    """Decode the four ``BSMeshArray`` LOD slots on a :class:`BSGeometry`.

    Returns one :class:`BSGeometryMeshRef` per slot, in declaration order
    (LOD0 first). Slots that the shape did not populate (``has_mesh == 0``)
    still appear with ``has_mesh=False`` so the round-trip preserves which
    LOD levels are present. Geometry itself lives in the external ``.mesh``
    file at ``mesh_path``; parsing those is deferred to the
    Starfield-tier external-asset work.
    """
    out: list[BSGeometryMeshRef] = []
    for i, slot in enumerate(block.meshes or ()):
        if slot is None:
            out.append(BSGeometryMeshRef(lod_index=i, has_mesh=False))
            continue
        has = bool(int(getattr(slot, "has_mesh", 0)))
        mesh = slot.mesh
        if not has or mesh is None:
            out.append(BSGeometryMeshRef(lod_index=i, has_mesh=has))
            continue
        out.append(
            BSGeometryMeshRef(
                lod_index=i,
                has_mesh=True,
                mesh_path=_decode_sized_string(mesh.mesh_path),
                num_verts=int(mesh.num_verts),
                indices_size=int(mesh.indices_size),
                flags=int(mesh.flags),
            )
        )
    return out


def _decode_sized_string(s: Any) -> str:
    """Decode a :class:`SizedString` / :class:`SizedString16` into latin-1."""
    if s is None:
        return ""
    value = getattr(s, "value", None)
    if value is None:
        return ""
    try:
        return bytes(value).decode("latin-1")
    except (TypeError, ValueError):
        return ""
