"""Phase 9b: clean-room Starfield ``.mesh`` binary decoder / encoder.

Decodes the v1 Starfield mesh format into the same dense numpy arrays
that the existing :class:`~nifblend.bridge.mesh_in.MeshData` shape
produces for FO4 / FO76 / SSE, so the downstream bridge layer
(:mod:`nifblend.bridge.games.starfield`) can reuse every existing
materialisation path verbatim.

Format reference: :doc:`UPSTREAM_STARFIELD <UPSTREAM_STARFIELD>` — the
binary layout was authored from public reverse-engineering notes (no
SGB MIT-licensed source ported).

Scope: the headline geometry surface (positions / indices / UVs /
colours / normals / tangents / per-vertex skin influences). Meshlet and
cull-data trailers are recognised but skipped — they're GPU-pipeline
hints, not source-of-truth geometry, and parsing them is deferred to v2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import IO, Final

import numpy as np
import numpy.typing as npt

from .primitives import (
    read_array_f16,
    read_array_f32,
    read_array_u8,
    read_array_u16,
    read_array_u32,
    read_f32,
    read_u32,
    write_array_f16,
    write_array_f32,
    write_array_u8,
    write_array_u16,
    write_array_u32,
    write_f32,
    write_u32,
)

__all__ = [
    "STARFIELD_MESH_MAGIC",
    "StarfieldMeshData",
    "StarfieldMeshLOD",
    "is_starfield_mesh",
    "read_starfield_mesh",
    "write_starfield_mesh",
]


#: Currently observed magic / format version for v1 ``.mesh`` files.
STARFIELD_MESH_MAGIC: Final[int] = 1

#: Snorm scale divisor for i16-packed positions (``scale != 1.0`` path).
_SNORM_DIV: Final[float] = 32767.0

#: Unorm scale divisor for u16-packed bone weights.
_UNORM16_DIV: Final[float] = 65535.0


@dataclass(slots=True)
class StarfieldMeshLOD:
    """One LOD slice — index-buffer offset + length + engine-side distance."""

    start_index: int
    num_indices: int
    distance: float = 0.0


@dataclass(slots=True)
class StarfieldMeshData:
    """Decoded Starfield ``.mesh`` v1 contents.

    Mirrors the shape of :class:`~nifblend.bridge.mesh_in.MeshData`
    (positions / triangles / normals / uvs / colours / skin) so the
    bridge layer can adapt with a thin shim. The ``magic`` and
    ``num_weights_per_vertex`` fields are preserved verbatim so a
    ``read_starfield_mesh`` -> ``write_starfield_mesh`` round-trip is
    byte-equivalent for the geometry surface.
    """

    magic: int = STARFIELD_MESH_MAGIC
    scale: float = 1.0
    num_weights_per_vertex: int = 0
    positions: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 3), dtype=np.float32)
    )
    triangles: npt.NDArray[np.uint32] = field(
        default_factory=lambda: np.empty((0, 3), dtype=np.uint32)
    )
    uv: npt.NDArray[np.float32] | None = None
    uv2: npt.NDArray[np.float32] | None = None
    colors: npt.NDArray[np.float32] | None = None  # (N, 4) RGBA in [0, 1]
    normals: npt.NDArray[np.float32] | None = None  # (N, 3) unit
    tangents: npt.NDArray[np.float32] | None = None  # (N, 3) unit
    bone_indices: npt.NDArray[np.uint8] | None = None  # (N, K)
    bone_weights: npt.NDArray[np.float32] | None = None  # (N, K)
    lods: list[StarfieldMeshLOD] = field(default_factory=list)


# ---- detection ------------------------------------------------------------


def is_starfield_mesh(stream: IO[bytes]) -> bool:
    """Peek the leading u32 and reset the stream cursor.

    Returns ``True`` when the magic matches a known Starfield ``.mesh``
    version. The stream must be seekable; non-seekable callers should
    buffer the first 4 bytes themselves.
    """
    pos = stream.tell()
    try:
        head = stream.read(4)
    finally:
        stream.seek(pos)
    if len(head) != 4:
        return False
    magic = int.from_bytes(head, "little", signed=False)
    return magic in (STARFIELD_MESH_MAGIC,)


# ---- normal / tangent packing --------------------------------------------
#
# Starfield packs unit vectors into a 10/10/10/2 unsigned int. Each axis
# is unorm-encoded in 10 bits (range [0, 1023]); decode by mapping
# ``v / 1023 * 2 - 1`` and renormalising. The 2-bit field is a "sign of
# the cross product" for tangent-handedness; on the normal stream it is
# ignored.


def _unpack_10_10_10(packed: npt.NDArray[np.uint32]) -> npt.NDArray[np.float32]:
    """Decode an ``(N,)`` u32 stream of 10/10/10/2 packed unit vectors."""
    if packed.size == 0:
        return np.empty((0, 3), dtype=np.float32)
    x = (packed & 0x3FF).astype(np.float32)
    y = ((packed >> 10) & 0x3FF).astype(np.float32)
    z = ((packed >> 20) & 0x3FF).astype(np.float32)
    out = np.empty((packed.size, 3), dtype=np.float32)
    out[:, 0] = x / 1023.0 * 2.0 - 1.0
    out[:, 1] = y / 1023.0 * 2.0 - 1.0
    out[:, 2] = z / 1023.0 * 2.0 - 1.0
    # Renormalise; a packed unit vector decodes to roughly-unit length but
    # quantisation drifts away from exactly 1.0.
    lengths = np.linalg.norm(out, axis=1, keepdims=True)
    lengths[lengths == 0.0] = 1.0
    return out / lengths


def _pack_10_10_10(vectors: npt.NDArray[np.float32]) -> npt.NDArray[np.uint32]:
    """Encode an ``(N, 3)`` unit-vector stream into 10/10/10/2 packed u32."""
    if vectors.size == 0:
        return np.empty((0,), dtype=np.uint32)
    if vectors.ndim != 2 or vectors.shape[1] != 3:
        raise ValueError(f"expected (N, 3) vectors, got shape {vectors.shape}")
    clipped = np.clip(vectors, -1.0, 1.0)
    quantised = np.rint((clipped + 1.0) * 0.5 * 1023.0).astype(np.uint32)
    return (
        (quantised[:, 0] & 0x3FF)
        | ((quantised[:, 1] & 0x3FF) << 10)
        | ((quantised[:, 2] & 0x3FF) << 20)
    )


# ---- reader --------------------------------------------------------------


def read_starfield_mesh(stream: IO[bytes]) -> StarfieldMeshData:
    """Decode a Starfield v1 ``.mesh`` from ``stream``.

    Raises ``ValueError`` when the magic is unrecognised; ``EOFError``
    propagates from the underlying scalar / bulk-array primitives when
    a section is truncated.
    """
    magic = read_u32(stream)
    if magic not in (STARFIELD_MESH_MAGIC,):
        raise ValueError(f"unrecognised Starfield .mesh magic: {magic!r}")

    num_indices = read_u32(stream)
    if num_indices % 3 != 0:
        raise ValueError(
            f"index buffer length {num_indices} is not a multiple of 3"
        )
    indices_flat = read_array_u16(stream, num_indices)
    triangles = indices_flat.astype(np.uint32, copy=False).reshape(-1, 3)

    scale = read_f32(stream)
    num_weights_per_vertex = read_u32(stream)

    num_positions = read_u32(stream)
    positions = _read_positions(stream, num_positions, scale)

    num_uvs = read_u32(stream)
    uv = _read_half_uvs(stream, num_uvs) if num_uvs else None

    num_uvs2 = read_u32(stream)
    uv2 = _read_half_uvs(stream, num_uvs2) if num_uvs2 else None

    num_colors = read_u32(stream)
    colors: npt.NDArray[np.float32] | None
    if num_colors:
        raw = read_array_u8(stream, num_colors * 4).reshape(-1, 4)
        colors = raw.astype(np.float32) / 255.0
    else:
        colors = None

    num_normals = read_u32(stream)
    normals = _unpack_10_10_10(read_array_u32(stream, num_normals)) if num_normals else None

    num_tangents = read_u32(stream)
    tangents = _unpack_10_10_10(read_array_u32(stream, num_tangents)) if num_tangents else None

    num_weights = read_u32(stream)
    bone_indices: npt.NDArray[np.uint8] | None = None
    bone_weights: npt.NDArray[np.float32] | None = None
    if num_weights and num_weights_per_vertex:
        k = int(num_weights_per_vertex)
        bone_indices = read_array_u8(stream, num_weights * k).reshape(-1, k)
        raw_w = read_array_u16(stream, num_weights * k).reshape(-1, k)
        bone_weights = raw_w.astype(np.float32) / _UNORM16_DIV

    num_lods = read_u32(stream)
    lods: list[StarfieldMeshLOD] = []
    for _ in range(num_lods):
        start = read_u32(stream)
        count = read_u32(stream)
        distance = read_f32(stream)
        lods.append(StarfieldMeshLOD(start_index=start, num_indices=count, distance=distance))

    # Trailing meshlet / culldata streams are skipped; we don't consume them
    # in v1.1 import. The file may legitimately end after the LOD list.
    return StarfieldMeshData(
        magic=magic,
        scale=scale,
        num_weights_per_vertex=num_weights_per_vertex,
        positions=positions,
        triangles=triangles,
        uv=uv,
        uv2=uv2,
        colors=colors,
        normals=normals,
        tangents=tangents,
        bone_indices=bone_indices,
        bone_weights=bone_weights,
        lods=lods,
    )


def _read_positions(
    stream: IO[bytes], count: int, scale: float
) -> npt.NDArray[np.float32]:
    if count == 0:
        return np.empty((0, 3), dtype=np.float32)
    if scale == 1.0:
        flat = read_array_f32(stream, count * 3)
        return flat.reshape(-1, 3)
    raw = read_array_u16(stream, count * 3).view(np.int16).reshape(-1, 3)
    return raw.astype(np.float32) / _SNORM_DIV * float(scale)


def _read_half_uvs(stream: IO[bytes], count: int) -> npt.NDArray[np.float32]:
    flat = read_array_f16(stream, count * 2)
    return flat.reshape(-1, 2).astype(np.float32)


# ---- writer --------------------------------------------------------------


def write_starfield_mesh(stream: IO[bytes], data: StarfieldMeshData) -> None:
    """Encode a :class:`StarfieldMeshData` back to ``stream``.

    Round-trip discipline: the geometry surface (positions / triangles /
    UVs / colours / normals / tangents / skin / LODs) is byte-equivalent
    when the input came from :func:`read_starfield_mesh`. Trailing
    meshlet / culldata streams are not emitted (the v1.1 import slice
    does not consume them either).
    """
    write_u32(stream, int(data.magic))

    triangles = data.triangles.reshape(-1).astype(np.uint16, copy=False)
    write_u32(stream, int(triangles.size))
    write_array_u16(stream, triangles)

    write_f32(stream, float(data.scale))
    write_u32(stream, int(data.num_weights_per_vertex))

    write_u32(stream, int(data.positions.shape[0]))
    _write_positions(stream, data.positions, data.scale)

    _write_half_uv_section(stream, data.uv)
    _write_half_uv_section(stream, data.uv2)

    if data.colors is None:
        write_u32(stream, 0)
    else:
        write_u32(stream, int(data.colors.shape[0]))
        raw = np.clip(np.rint(data.colors * 255.0), 0, 255).astype(np.uint8)
        write_array_u8(stream, raw.reshape(-1))

    _write_packed_unit_section(stream, data.normals)
    _write_packed_unit_section(stream, data.tangents)

    if data.bone_indices is None or data.bone_weights is None or data.num_weights_per_vertex == 0:
        write_u32(stream, 0)
    else:
        n = int(data.bone_indices.shape[0])
        write_u32(stream, n)
        write_array_u8(stream, data.bone_indices.astype(np.uint8, copy=False).reshape(-1))
        raw_w = np.clip(np.rint(data.bone_weights * _UNORM16_DIV), 0, _UNORM16_DIV).astype(
            np.uint16
        )
        write_array_u16(stream, raw_w.reshape(-1))

    write_u32(stream, len(data.lods))
    for lod in data.lods:
        write_u32(stream, int(lod.start_index))
        write_u32(stream, int(lod.num_indices))
        write_f32(stream, float(lod.distance))


def _write_positions(
    stream: IO[bytes], positions: npt.NDArray[np.float32], scale: float
) -> None:
    if positions.size == 0:
        return
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"expected (N, 3) positions, got shape {positions.shape}")
    if scale == 1.0:
        write_array_f32(stream, positions.astype(np.float32, copy=False).reshape(-1))
        return
    raw = np.clip(
        np.rint(positions / float(scale) * _SNORM_DIV), -_SNORM_DIV - 1, _SNORM_DIV
    ).astype(np.int16)
    write_array_u16(stream, raw.view(np.uint16).reshape(-1))


def _write_half_uv_section(
    stream: IO[bytes], uv: npt.NDArray[np.float32] | None
) -> None:
    if uv is None or uv.size == 0:
        write_u32(stream, 0)
        return
    if uv.ndim != 2 or uv.shape[1] != 2:
        raise ValueError(f"expected (N, 2) UVs, got shape {uv.shape}")
    write_u32(stream, int(uv.shape[0]))
    write_array_f16(stream, uv.astype(np.float16, copy=False).reshape(-1))


def _write_packed_unit_section(
    stream: IO[bytes], vectors: npt.NDArray[np.float32] | None
) -> None:
    if vectors is None or vectors.size == 0:
        write_u32(stream, 0)
        return
    write_u32(stream, int(vectors.shape[0]))
    write_array_u32(stream, _pack_10_10_10(vectors))


# Convenience: encode to bytes (used by tests for round-trip parity).
def _encode_bytes(data: StarfieldMeshData) -> bytes:
    buf = BytesIO()
    write_starfield_mesh(buf, data)
    return buf.getvalue()
