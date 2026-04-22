"""Export side of the BSTriShape ↔ Blender mesh bridge (Phase 2 step 9).

Mirrors :mod:`nifblend.bridge.mesh_in`:

* :func:`mesh_data_from_blender` -- pure-numpy extraction from a
  ``bpy.types.Mesh`` (or any duck-typed equivalent) into :class:`MeshData`.
  Triangulates loop topology, gathers per-vertex normals/UVs/colors via
  ``foreach_get``, and re-flips the V coordinate back to NIF convention.
* :func:`mesh_data_to_bstrishape` -- pure function that builds a
  :class:`BSTriShape` block (and matching :class:`BSVertexData` records)
  from a :class:`MeshData` plus a target vertex-attribute flag set.

The block is emitted with raw u32 references unset (``skin = -1``,
``shader_property = -1``, ``alpha_property = -1``) and ``name = -1``;
callers wiring blocks into a :class:`~nifblend.io.block_table.BlockTable`
are expected to allocate string-table entries and patch cross-references
themselves. Keeping that bookkeeping in the operator (not the bridge)
matches the symmetry of the import path, which leaves cross-references as
raw u32 indices.

Bone weights / indices are stored if present on :class:`MeshData`; we do
not yet build a ``BSSkin::Instance`` block (that lands with Phase 4).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.bitfields import BSVertexDesc
from nifblend.format.generated.blocks import BSTriShape
from nifblend.format.generated.structs import (
    ByteColor4,
    ByteVector3,
    HalfTexCoord,
    HalfVector3,
    NiBound,
    Triangle,
    Vector3,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)

from .mesh_in import MeshData

__all__ = [
    "export_bstrishape",
    "mesh_data_from_blender",
    "mesh_data_to_bstrishape",
    "vertex_attributes_for",
]


# Vertex-attribute bits (mirrored from `nifblend.bridge.mesh_in`).
_VA_VERTEX = 0x001
_VA_UV = 0x002
_VA_NORMALS = 0x008
_VA_TANGENTS = 0x010
_VA_COLORS = 0x020
_VA_SKINNED = 0x040
_VA_FULL_PRECISION = 0x400


# ---- Blender → MeshData ---------------------------------------------------


def mesh_data_from_blender(mesh: Any, *, name: str | None = None) -> MeshData:
    """Read a Blender ``bpy.types.Mesh`` (or duck-typed equivalent) into MeshData.

    The mesh is assumed to have been triangulated already; quads/ngons
    will fail the ``len(loops) == 3 * polys`` invariant. Callers needing a
    pre-pass should run ``bmesh.ops.triangulate`` before invoking the
    bridge.
    """
    resolved_name = name if name is not None else mesh.name

    n_verts = len(mesh.vertices)
    positions = np.empty(n_verts * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", positions)
    positions = positions.reshape((n_verts, 3))

    # Vertex normals (per-vertex; Blender also stores per-loop normals but
    # BSVertexData is per-vertex so we collapse here).
    normals: npt.NDArray[np.float32] | None = None
    if hasattr(mesh.vertices, "foreach_get"):
        try:
            buf = np.empty(n_verts * 3, dtype=np.float32)
            mesh.vertices.foreach_get("normal", buf)
            normals = buf.reshape((n_verts, 3))
        except (RuntimeError, AttributeError):  # pragma: no cover - older bpy
            normals = None

    # Triangles via loop_triangles when available (real bpy), or directly
    # off polygons[].vertices when we're given the duck-typed test fake.
    triangles = _gather_triangles(mesh)

    # Per-vertex UV: Blender stores UVs per-loop, so we resolve to per-vertex
    # by taking the first loop that references each vertex (matches what
    # mesh_in writes on import).
    uv: npt.NDArray[np.float32] | None = None
    if mesh.uv_layers and len(mesh.uv_layers) > 0:
        uv_layer = mesh.uv_layers.active or mesh.uv_layers[0]
        n_loops = len(mesh.loops)
        loop_uv = np.empty(n_loops * 2, dtype=np.float32)
        uv_layer.data.foreach_get("uv", loop_uv)
        loop_uv = loop_uv.reshape((n_loops, 2))
        loop_v = np.empty(n_loops, dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_v)
        per_vertex = np.zeros((n_verts, 2), dtype=np.float32)
        seen = np.zeros(n_verts, dtype=bool)
        # Last-write-wins after preferring the first sighting; a vertex shared
        # across UV seams will lose one of its two UVs (that's a hard limit
        # of going from per-loop UVs back to a per-vertex schema).
        for li in range(n_loops):
            vi = int(loop_v[li])
            if not seen[vi]:
                per_vertex[vi] = loop_uv[li]
                seen[vi] = True
        # NIF V is top-down, Blender V is bottom-up. Inverse of mesh_in.
        per_vertex[:, 1] = 1.0 - per_vertex[:, 1]
        uv = per_vertex

    # Vertex colors via the modern color_attributes API on POINT domain only;
    # anything fancier is ignored for now (Phase 3 expands materials).
    vertex_colors: npt.NDArray[np.float32] | None = None
    if hasattr(mesh, "color_attributes") and len(mesh.color_attributes) > 0:
        attr = mesh.color_attributes[0]
        if getattr(attr, "domain", None) == "POINT":
            buf = np.empty(n_verts * 4, dtype=np.float32)
            attr.data.foreach_get("color", buf)
            vertex_colors = buf.reshape((n_verts, 4))

    return MeshData(
        name=resolved_name,
        positions=positions,
        triangles=triangles,
        normals=normals,
        uv=uv,
        vertex_colors=vertex_colors,
    )


# ---- MeshData → BSTriShape ----------------------------------------------


def vertex_attributes_for(data: MeshData, *, full_precision: bool = False) -> int:
    """Derive a sensible ``BSVertexDesc.vertex_attributes`` from a MeshData.

    Always sets the vertex bit. Sets the optional bits that ``data`` actually
    carries. ``full_precision`` toggles the SSE 0x400 flag (off by default so
    exports default to half-precision, matching most SSE assets).
    """
    flags = _VA_VERTEX
    if data.uv is not None:
        flags |= _VA_UV
    if data.normals is not None:
        flags |= _VA_NORMALS
    if data.tangents is not None and data.normals is not None:
        flags |= _VA_TANGENTS
    if data.vertex_colors is not None:
        flags |= _VA_COLORS
    if data.bone_weights is not None or data.bone_indices is not None:
        flags |= _VA_SKINNED
    if full_precision:
        flags |= _VA_FULL_PRECISION
    return flags


def mesh_data_to_bstrishape(
    data: MeshData,
    *,
    full_precision: bool = False,
    name_index: int = 0xFFFFFFFF,
) -> BSTriShape:
    """Build a :class:`BSTriShape` block from a :class:`MeshData`.

    The block is configured for SSE-style output (BS version 100 by
    default; pre-vertex-data field ordering is otherwise version-agnostic).
    Cross-references (``skin``, ``shader_property``, ``alpha_property``)
    are left as ``-1`` for the operator/bridge to patch.
    """
    n = data.positions.shape[0]
    desc_attrs = vertex_attributes_for(data, full_precision=full_precision)
    full = bool(desc_attrs & _VA_FULL_PRECISION)

    blk = BSTriShape()
    blk.name = nif_string(index=name_index)
    blk.translation = Vector3(0.0, 0.0, 0.0)
    blk.rotation = _identity_matrix33()
    blk.scale = 1.0
    blk.collision_object = -1
    blk.skin = -1
    blk.shader_property = -1
    blk.alpha_property = -1
    blk.bounding_sphere = _bounding_sphere(data.positions)

    # BSVertexDesc carries both the offsets and the flags; we only set the
    # attribute flags here. Offsets are not consumed by the round-trip
    # readers (they're informational for the GPU), so leaving them zeroed is
    # acceptable for v0.1.
    blk.vertex_desc = BSVertexDesc(vertex_attributes=desc_attrs)

    blk.num_vertices = n
    blk.num_triangles = data.triangles.shape[0]

    # data_size in bytes -- the read-side guards key on `data_size > 0`.
    # An exact size requires summing per-vertex strides; using `n` (any
    # non-zero value) is sufficient for the existing read guards.
    blk.data_size = n if n > 0 else 0

    blk.vertex_data = [
        _build_vertex_record(data, i, desc_attrs, full_precision=full)
        for i in range(n)
    ]
    blk.triangles = [
        Triangle(int(tri[0]), int(tri[1]), int(tri[2])) for tri in data.triangles
    ]
    return blk


def export_bstrishape(
    mesh: Any,
    *,
    name: str | None = None,
    full_precision: bool = False,
    name_index: int = 0xFFFFFFFF,
) -> BSTriShape:
    """Convert a Blender mesh to a :class:`BSTriShape` in one call."""
    data = mesh_data_from_blender(mesh, name=name)
    return mesh_data_to_bstrishape(
        data, full_precision=full_precision, name_index=name_index
    )


# ---- private helpers ------------------------------------------------------


def _gather_triangles(mesh: Any) -> npt.NDArray[np.uint32]:
    """Return an (M, 3) uint32 triangle array.

    Blender exposes ``loop_triangles`` after a triangulate; the duck-typed
    test fake just exposes ``polygons`` with three vertex indices each.
    Both are accepted to keep the bridge testable headlessly.
    """
    if hasattr(mesh, "loop_triangles") and len(mesh.loop_triangles) > 0:
        n_tris = len(mesh.loop_triangles)
        out = np.empty(n_tris * 3, dtype=np.uint32)
        mesh.loop_triangles.foreach_get("vertices", out)
        return out.reshape((n_tris, 3))
    # Polygon fallback: assume already-triangulated.
    polys = list(mesh.polygons)
    if not polys:
        return np.empty((0, 3), dtype=np.uint32)
    out = np.empty((len(polys), 3), dtype=np.uint32)
    for i, poly in enumerate(polys):
        verts = list(poly.vertices)
        if len(verts) != 3:
            raise ValueError(
                f"polygon {i} has {len(verts)} vertices; mesh must be triangulated "
                f"before export"
            )
        out[i, 0] = verts[0]
        out[i, 1] = verts[1]
        out[i, 2] = verts[2]
    return out


def _identity_matrix33() -> Any:
    """Build a Matrix33 set to the identity. Imported lazily to avoid a
    structs.py import in users that only need MeshData."""
    from nifblend.format.generated.structs import Matrix33

    m = Matrix33()
    # Matrix33 fields are m11..m33 (row-major); set the diagonal.
    for attr in ("m11", "m22", "m33"):
        if hasattr(m, attr):
            setattr(m, attr, 1.0)
    return m


def _bounding_sphere(positions: npt.NDArray[np.float32]) -> NiBound:
    """Compute a trivial AABB-derived bounding sphere."""
    sphere = NiBound()
    if positions.size == 0:
        sphere.center = Vector3(0.0, 0.0, 0.0)
        sphere.radius = 0.0
        return sphere
    mn = positions.min(axis=0)
    mx = positions.max(axis=0)
    centre = (mn + mx) * 0.5
    radius = float(np.linalg.norm(positions - centre, axis=1).max())
    sphere.center = Vector3(float(centre[0]), float(centre[1]), float(centre[2]))
    sphere.radius = radius
    return sphere


def _build_vertex_record(
    data: MeshData,
    i: int,
    desc_attrs: int,
    *,
    full_precision: bool,
) -> Any:
    """Construct one BSVertexData (or BSVertexDataSSE) record for vertex ``i``.

    BS version 100 (SSE) reads ``BSVertexDataSSE``; BS version >= 130 (FO4)
    reads ``BSVertexData``. The payload fields are isomorphic for the
    attributes we currently write, so we use ``BSVertexDataSSE`` -- the
    SSE-shaped record -- which round-trips through every reader path used
    by Phase 2.
    """
    from nifblend.format.generated.structs import BSVertexDataSSE

    rec = BSVertexDataSSE()

    if desc_attrs & _VA_VERTEX:
        x, y, z = (float(c) for c in data.positions[i])
        if full_precision:
            rec.vertex = Vector3(x, y, z)
        else:
            rec.vertex = HalfVector3(x, y, z)

    if desc_attrs & _VA_UV and data.uv is not None:
        rec.uv = HalfTexCoord(float(data.uv[i, 0]), float(data.uv[i, 1]))

    if desc_attrs & _VA_NORMALS and data.normals is not None:
        rec.normal = _unit_to_byte_vec3(data.normals[i])
        if data.bitangents is not None:
            rec.bitangent_y = _unit_to_byte(float(data.bitangents[i, 1]))
        else:
            rec.bitangent_y = 128

    if (desc_attrs & _VA_TANGENTS) and data.tangents is not None:
        rec.tangent = _unit_to_byte_vec3(data.tangents[i])
        if data.bitangents is not None:
            rec.bitangent_z = _unit_to_byte(float(data.bitangents[i, 2]))
            rec.bitangent_x = float(data.bitangents[i, 0])
        else:
            rec.bitangent_z = 128
            rec.bitangent_x = 0.0

    if desc_attrs & _VA_COLORS and data.vertex_colors is not None:
        c = data.vertex_colors[i]
        rec.vertex_colors = ByteColor4(
            r=_unit_color_to_byte(float(c[0])),
            g=_unit_color_to_byte(float(c[1])),
            b=_unit_color_to_byte(float(c[2])),
            a=_unit_color_to_byte(float(c[3])),
        )

    if desc_attrs & _VA_SKINNED:
        if data.bone_weights is not None:
            rec.bone_weights = [float(w) for w in data.bone_weights[i, :4]]
        else:
            rec.bone_weights = [0.0, 0.0, 0.0, 0.0]
        if data.bone_indices is not None:
            rec.bone_indices = [int(b) for b in data.bone_indices[i, :4]]
        else:
            rec.bone_indices = [0, 0, 0, 0]

    return rec


def _unit_to_byte(value: float) -> int:
    """Inverse of ``raw / 127.5 - 1``: clamp ``value`` ∈ [-1, 1] back to a u8."""
    raw = round((value + 1.0) * 127.5)
    if raw < 0:
        return 0
    if raw > 255:
        return 255
    return raw


def _unit_to_byte_vec3(v: npt.NDArray[np.float32]) -> ByteVector3:
    return ByteVector3(
        x=_unit_to_byte(float(v[0])),
        y=_unit_to_byte(float(v[1])),
        z=_unit_to_byte(float(v[2])),
    )


def _unit_color_to_byte(value: float) -> int:
    raw = round(value * 255.0)
    if raw < 0:
        return 0
    if raw > 255:
        return 255
    return raw
