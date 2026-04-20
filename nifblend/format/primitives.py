"""Hand-written binary primitives for NIF I/O.

Replaces the `basic.py` that `new-pyffi` would have provided. Codegen output
under `nifblend/format/generated/` calls into this module for every scalar,
fixed-size compound, and bulk array read/write.

Design:
- All `read_*` take a binary stream (anything with `.read(n)`).
- All `write_*` take a stream (`.write(bytes)`) and the value.
- Bulk array variants use `numpy.frombuffer` / `numpy.ndarray.tobytes` for
  zero-copy where possible. Endianness is little-endian (NIF is LE on every
  supported platform; the schema's `endian="big"` cases are PS3 builds we do
  not target).
- No `bpy` imports here — this module must be importable in plain CPython for
  unit tests and codegen output validation.
"""

from __future__ import annotations

import struct
from typing import IO, Final

import numpy as np
import numpy.typing as npt

__all__ = [
    "read_array_f16",
    "read_array_f32",
    "read_array_i16",
    "read_array_u8",
    "read_array_u16",
    "read_array_u32",
    "read_bool",
    "read_byte_color4_array",
    "read_byte_vec3_array",
    "read_f16",
    "read_f32",
    "read_half_vec2_array",
    "read_half_vec3_array",
    "read_i8",
    "read_i16",
    "read_i32",
    "read_i64",
    "read_packed_vertex_data",
    "read_sized_string",
    "read_triangle_array",
    "read_u8",
    "read_u16",
    "read_u32",
    "read_u64",
    "read_vec2_array",
    "read_vec3_array",
    "vertex_dtype_for_desc",
    "write_array_f16",
    "write_array_f32",
    "write_array_i16",
    "write_array_u8",
    "write_array_u16",
    "write_array_u32",
    "write_bool",
    "write_byte_color4_array",
    "write_byte_vec3_array",
    "write_f16",
    "write_f32",
    "write_half_vec2_array",
    "write_half_vec3_array",
    "write_i8",
    "write_i16",
    "write_i32",
    "write_i64",
    "write_packed_vertex_data",
    "write_sized_string",
    "write_triangle_array",
    "write_u8",
    "write_u16",
    "write_u32",
    "write_u64",
    "write_vec2_array",
    "write_vec3_array",
]

_LE: Final[str] = "<"

# ---- scalars --------------------------------------------------------------

_S_U8 = struct.Struct(_LE + "B")
_S_U16 = struct.Struct(_LE + "H")
_S_U32 = struct.Struct(_LE + "I")
_S_U64 = struct.Struct(_LE + "Q")
_S_I8 = struct.Struct(_LE + "b")
_S_I16 = struct.Struct(_LE + "h")
_S_I32 = struct.Struct(_LE + "i")
_S_I64 = struct.Struct(_LE + "q")
_S_F32 = struct.Struct(_LE + "f")
_S_F16 = struct.Struct(_LE + "e")


def read_u8(stream: IO[bytes]) -> int:
    return _S_U8.unpack(stream.read(1))[0]


def read_u16(stream: IO[bytes]) -> int:
    return _S_U16.unpack(stream.read(2))[0]


def read_u32(stream: IO[bytes]) -> int:
    return _S_U32.unpack(stream.read(4))[0]


def read_u64(stream: IO[bytes]) -> int:
    return _S_U64.unpack(stream.read(8))[0]


def read_i8(stream: IO[bytes]) -> int:
    return _S_I8.unpack(stream.read(1))[0]


def read_i16(stream: IO[bytes]) -> int:
    return _S_I16.unpack(stream.read(2))[0]


def read_i32(stream: IO[bytes]) -> int:
    return _S_I32.unpack(stream.read(4))[0]


def read_i64(stream: IO[bytes]) -> int:
    return _S_I64.unpack(stream.read(8))[0]


def read_f32(stream: IO[bytes]) -> float:
    return _S_F32.unpack(stream.read(4))[0]


def read_f16(stream: IO[bytes]) -> float:
    return _S_F16.unpack(stream.read(2))[0]


def read_bool(stream: IO[bytes]) -> bool:
    # NIF `bool` is one byte from version 4.1+, four bytes before. The codegen
    # selects the right reader based on header version; this is the modern path.
    return stream.read(1) != b"\x00"


def write_u8(stream: IO[bytes], v: int) -> None:
    stream.write(_S_U8.pack(v))


def write_u16(stream: IO[bytes], v: int) -> None:
    stream.write(_S_U16.pack(v))


def write_u32(stream: IO[bytes], v: int) -> None:
    stream.write(_S_U32.pack(v))


def write_u64(stream: IO[bytes], v: int) -> None:
    stream.write(_S_U64.pack(v))


def write_i8(stream: IO[bytes], v: int) -> None:
    stream.write(_S_I8.pack(v))


def write_i16(stream: IO[bytes], v: int) -> None:
    stream.write(_S_I16.pack(v))


def write_i32(stream: IO[bytes], v: int) -> None:
    stream.write(_S_I32.pack(v))


def write_i64(stream: IO[bytes], v: int) -> None:
    stream.write(_S_I64.pack(v))


def write_f32(stream: IO[bytes], v: float) -> None:
    stream.write(_S_F32.pack(v))


def write_f16(stream: IO[bytes], v: float) -> None:
    stream.write(_S_F16.pack(v))


def write_bool(stream: IO[bytes], v: bool) -> None:
    stream.write(b"\x01" if v else b"\x00")


# ---- bulk arrays (numpy fast paths) ---------------------------------------


def _read_array(stream: IO[bytes], dtype: np.dtype, count: int) -> npt.NDArray:
    raw = stream.read(int(dtype.itemsize) * count)
    if len(raw) != int(dtype.itemsize) * count:
        raise EOFError(f"expected {dtype.itemsize * count} bytes, got {len(raw)}")
    # `frombuffer` returns a read-only view; copy so callers can mutate freely.
    return np.frombuffer(raw, dtype=dtype, count=count).copy()


def read_array_u8(stream: IO[bytes], count: int) -> npt.NDArray[np.uint8]:
    return _read_array(stream, np.dtype("u1"), count)


def read_array_u16(stream: IO[bytes], count: int) -> npt.NDArray[np.uint16]:
    return _read_array(stream, np.dtype("<u2"), count)


def read_array_u32(stream: IO[bytes], count: int) -> npt.NDArray[np.uint32]:
    return _read_array(stream, np.dtype("<u4"), count)


def read_array_i16(stream: IO[bytes], count: int) -> npt.NDArray[np.int16]:
    return _read_array(stream, np.dtype("<i2"), count)


def read_array_f16(stream: IO[bytes], count: int) -> npt.NDArray[np.float16]:
    return _read_array(stream, np.dtype("<f2"), count)


def read_array_f32(stream: IO[bytes], count: int) -> npt.NDArray[np.float32]:
    return _read_array(stream, np.dtype("<f4"), count)


def _write_array(stream: IO[bytes], arr: npt.NDArray, expected_dtype: np.dtype) -> None:
    if arr.dtype != expected_dtype:
        arr = arr.astype(expected_dtype, copy=False)
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    stream.write(arr.tobytes())


def write_array_u8(stream: IO[bytes], arr: npt.NDArray[np.uint8]) -> None:
    _write_array(stream, arr, np.dtype("u1"))


def write_array_u16(stream: IO[bytes], arr: npt.NDArray[np.uint16]) -> None:
    _write_array(stream, arr, np.dtype("<u2"))


def write_array_u32(stream: IO[bytes], arr: npt.NDArray[np.uint32]) -> None:
    _write_array(stream, arr, np.dtype("<u4"))


def write_array_i16(stream: IO[bytes], arr: npt.NDArray[np.int16]) -> None:
    _write_array(stream, arr, np.dtype("<i2"))


def write_array_f16(stream: IO[bytes], arr: npt.NDArray[np.float16]) -> None:
    _write_array(stream, arr, np.dtype("<f2"))


def write_array_f32(stream: IO[bytes], arr: npt.NDArray[np.float32]) -> None:
    _write_array(stream, arr, np.dtype("<f4"))


def read_vec3_array(stream: IO[bytes], count: int) -> npt.NDArray[np.float32]:
    """Read `count` packed Vector3 (12 bytes each) into shape (count, 3) f32."""
    flat = read_array_f32(stream, count * 3)
    return flat.reshape((count, 3))


def write_vec3_array(stream: IO[bytes], arr: npt.NDArray[np.float32]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"expected (N, 3) array, got shape {arr.shape}")
    write_array_f32(stream, arr.reshape(-1))


def read_vec2_array(stream: IO[bytes], count: int) -> npt.NDArray[np.float32]:
    flat = read_array_f32(stream, count * 2)
    return flat.reshape((count, 2))


def write_vec2_array(stream: IO[bytes], arr: npt.NDArray[np.float32]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"expected (N, 2) array, got shape {arr.shape}")
    write_array_f32(stream, arr.reshape(-1))


# ---- bulk packed compounds (vectorized fast paths) ------------------------
#
# These accelerate the common BSTriShape per-vertex layouts where the
# generated per-instance read loop would otherwise dominate runtime. They
# return numpy arrays in the schema's native packed dtype; the bridge layer
# is expected to upcast (e.g. f16 -> f32, u8 -> normalized f32) when handing
# data to Blender.


def read_half_vec2_array(stream: IO[bytes], count: int) -> npt.NDArray[np.float16]:
    """Packed array of `count` HalfTexCoord (4 bytes each) -> shape (count, 2)."""
    flat = read_array_f16(stream, count * 2)
    return flat.reshape((count, 2))


def write_half_vec2_array(stream: IO[bytes], arr: npt.NDArray[np.float16]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError(f"expected (N, 2) array, got shape {arr.shape}")
    write_array_f16(stream, arr.reshape(-1))


def read_half_vec3_array(stream: IO[bytes], count: int) -> npt.NDArray[np.float16]:
    """Packed array of `count` HalfVector3 (6 bytes each) -> shape (count, 3)."""
    flat = read_array_f16(stream, count * 3)
    return flat.reshape((count, 3))


def write_half_vec3_array(stream: IO[bytes], arr: npt.NDArray[np.float16]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"expected (N, 3) array, got shape {arr.shape}")
    write_array_f16(stream, arr.reshape(-1))


def read_byte_vec3_array(stream: IO[bytes], count: int) -> npt.NDArray[np.uint8]:
    """Packed array of `count` ByteVector3 (3 bytes each) -> shape (count, 3).

    Bytes map [0, 255] to [-1, 1]; the bridge does the rescale.
    """
    flat = read_array_u8(stream, count * 3)
    return flat.reshape((count, 3))


def write_byte_vec3_array(stream: IO[bytes], arr: npt.NDArray[np.uint8]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"expected (N, 3) array, got shape {arr.shape}")
    write_array_u8(stream, arr.reshape(-1))


def read_byte_color4_array(stream: IO[bytes], count: int) -> npt.NDArray[np.uint8]:
    """Packed array of `count` ByteColor4 (4 bytes each) -> shape (count, 4)."""
    flat = read_array_u8(stream, count * 4)
    return flat.reshape((count, 4))


def write_byte_color4_array(stream: IO[bytes], arr: npt.NDArray[np.uint8]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 4:
        raise ValueError(f"expected (N, 4) array, got shape {arr.shape}")
    write_array_u8(stream, arr.reshape(-1))


def read_triangle_array(stream: IO[bytes], count: int) -> npt.NDArray[np.uint16]:
    """Packed array of `count` Triangle (3 x u16 = 6 bytes) -> shape (count, 3)."""
    flat = read_array_u16(stream, count * 3)
    return flat.reshape((count, 3))


def write_triangle_array(stream: IO[bytes], arr: npt.NDArray[np.uint16]) -> None:
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"expected (N, 3) array, got shape {arr.shape}")
    write_array_u16(stream, arr.reshape(-1))


# ---- BSVertexData packed reader -------------------------------------------
#
# BSTriShape stores `num_vertices` BSVertexData records back-to-back. Each
# record's layout is fully determined by the low 16 bits of the BSVertexDesc
# `vertex_attributes` field passed as `arg`. We build a structured numpy
# dtype matching that layout once and read the entire array in a single I/O
# call -- ~50-100x faster than the per-vertex Python loop the codegen emits.
#
# Flag bits we honor (mirroring `BSVertexData.read` in the generated code):
#   0x001  Vertex          (Vector3/HalfVector3 depending on 0x400)
#   0x002  UVs             (HalfTexCoord)
#   0x008  Normals         (ByteVector3 + bitangent_y u8)
#   0x010  Tangents        (when also 0x008: ByteVector3 + bitangent_z u8;
#                           plus bitangent_x as f32 if 0x400 else f16)
#   0x020  Vertex Colors   (ByteColor4)
#   0x040  Skinned         (4x f16 weights + 4x u8 indices)
#   0x100  Eye Data        (f32)
#   0x400  Full Precision  (Vector3 + f32 bitangent_x + u32 unused_w)


def vertex_dtype_for_desc(desc: int) -> np.dtype:
    """Return the structured numpy dtype for a BSVertexData stride.

    `desc` is the low 16 bits of `BSVertexDesc.vertex_attributes` (the value
    the codegen passes as `ctx.arg`). Field names match the schema attribute
    names (lowercased, snake_case) so the bridge can look them up directly.
    """
    fields: list[tuple[str, str | np.dtype, tuple[int, ...]]] = []
    full_precision = (desc & 0x400) == 0x400
    has_vertex = (desc & 0x001) != 0
    has_tangents = (desc & 0x010) != 0

    if has_vertex:
        if full_precision:
            fields.append(("vertex", "<f4", (3,)))
            if has_tangents:
                fields.append(("bitangent_x", "<f4", ()))
            else:
                fields.append(("unused_w", "<u4", ()))
        else:
            fields.append(("vertex", "<f2", (3,)))
            if has_tangents:
                fields.append(("bitangent_x", "<f2", ()))
            else:
                fields.append(("unused_w", "<u2", ()))
    if (desc & 0x002) != 0:
        fields.append(("uv", "<f2", (2,)))
    if (desc & 0x008) != 0:
        fields.append(("normal", "u1", (3,)))
        fields.append(("bitangent_y", "u1", ()))
    if (desc & 0x018) == 0x018:
        fields.append(("tangent", "u1", (3,)))
        fields.append(("bitangent_z", "u1", ()))
    if (desc & 0x020) != 0:
        fields.append(("vertex_colors", "u1", (4,)))
    if (desc & 0x040) != 0:
        fields.append(("bone_weights", "<f2", (4,)))
        fields.append(("bone_indices", "u1", (4,)))
    if (desc & 0x100) != 0:
        fields.append(("eye_data", "<f4", ()))

    return np.dtype(fields)


def read_packed_vertex_data(
    stream: IO[bytes], count: int, desc: int
) -> npt.NDArray[np.void]:
    """Read `count` BSVertexData records in one shot using a packed dtype."""
    dtype = vertex_dtype_for_desc(desc)
    return _read_array(stream, dtype, count)


def write_packed_vertex_data(stream: IO[bytes], arr: npt.NDArray[np.void], desc: int) -> None:
    expected = vertex_dtype_for_desc(desc)
    if arr.dtype != expected:
        raise ValueError(
            f"vertex array dtype {arr.dtype} does not match desc 0x{desc:x} "
            f"(expected {expected})"
        )
    if not arr.flags["C_CONTIGUOUS"]:
        arr = np.ascontiguousarray(arr)
    stream.write(arr.tobytes())


# ---- strings --------------------------------------------------------------


def read_sized_string(stream: IO[bytes]) -> str:
    """SizedString: u32 length followed by `length` bytes (latin-1)."""
    length = read_u32(stream)
    raw = stream.read(length)
    if len(raw) != length:
        raise EOFError(f"sized string truncated: wanted {length}, got {len(raw)}")
    return raw.decode("latin-1")


def write_sized_string(stream: IO[bytes], value: str) -> None:
    raw = value.encode("latin-1")
    write_u32(stream, len(raw))
    stream.write(raw)
