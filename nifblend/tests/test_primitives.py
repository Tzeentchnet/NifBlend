"""Unit tests for :mod:`nifblend.format.primitives` -- scalars, bulk arrays,
packed compounds, and the BSVertexData fast path.

These run in plain CPython with the ``bpy`` stub installed by the repo-root
``tests/conftest.py``; no Blender required.
"""

from __future__ import annotations

import io
import struct

import numpy as np
import pytest

from nifblend.format import primitives as p

# ---- scalars --------------------------------------------------------------


@pytest.mark.parametrize(
    ("reader", "writer", "fmt", "value"),
    [
        (p.read_u8, p.write_u8, "<B", 0xAB),
        (p.read_u16, p.write_u16, "<H", 0xCAFE),
        (p.read_u32, p.write_u32, "<I", 0xDEADBEEF),
        (p.read_u64, p.write_u64, "<Q", 0x0123456789ABCDEF),
        (p.read_i8, p.write_i8, "<b", -7),
        (p.read_i16, p.write_i16, "<h", -12345),
        (p.read_i32, p.write_i32, "<i", -123456789),
        (p.read_i64, p.write_i64, "<q", -1),
        (p.read_f32, p.write_f32, "<f", 1.5),
    ],
)
def test_scalar_roundtrip(reader, writer, fmt, value) -> None:
    buf = io.BytesIO()
    writer(buf, value)
    assert buf.getvalue() == struct.pack(fmt, value)
    buf.seek(0)
    assert reader(buf) == value


def test_bool_roundtrip() -> None:
    buf = io.BytesIO()
    p.write_bool(buf, True)
    p.write_bool(buf, False)
    assert buf.getvalue() == b"\x01\x00"
    buf.seek(0)
    assert p.read_bool(buf) is True
    assert p.read_bool(buf) is False


# ---- bulk arrays ----------------------------------------------------------


def test_array_u8_roundtrip() -> None:
    src = np.array([0, 1, 2, 254, 255], dtype=np.uint8)
    buf = io.BytesIO()
    p.write_array_u8(buf, src)
    buf.seek(0)
    out = p.read_array_u8(buf, len(src))
    assert np.array_equal(out, src)


def test_array_u16_endianness() -> None:
    src = np.array([0x0001, 0x00FF, 0xFF00], dtype=np.uint16)
    buf = io.BytesIO()
    p.write_array_u16(buf, src)
    assert buf.getvalue() == b"\x01\x00\xff\x00\x00\xff"


def test_array_f32_roundtrip_large() -> None:
    rng = np.random.default_rng(0xC0FFEE)
    src = rng.standard_normal(1024).astype(np.float32)
    buf = io.BytesIO()
    p.write_array_f32(buf, src)
    buf.seek(0)
    out = p.read_array_f32(buf, len(src))
    assert np.array_equal(out, src)


def test_read_array_short_read_raises() -> None:
    with pytest.raises(EOFError):
        p.read_array_u32(io.BytesIO(b"\x00\x00\x00"), 1)


def test_write_array_handles_non_contiguous() -> None:
    base = np.arange(20, dtype=np.uint16).reshape(4, 5)
    view = base[:, ::2]  # not C-contiguous
    assert not view.flags["C_CONTIGUOUS"]
    buf = io.BytesIO()
    p.write_array_u16(buf, view.reshape(-1))
    buf.seek(0)
    out = p.read_array_u16(buf, view.size)
    assert np.array_equal(out.reshape(view.shape), view)


# ---- packed compounds -----------------------------------------------------


def test_vec3_array_roundtrip() -> None:
    src = np.array([[1.0, 2.0, 3.0], [-1.0, 0.5, 0.25]], dtype=np.float32)
    buf = io.BytesIO()
    p.write_vec3_array(buf, src)
    buf.seek(0)
    assert np.array_equal(p.read_vec3_array(buf, len(src)), src)


def test_half_vec2_array_roundtrip() -> None:
    src = np.array([[0.0, 1.0], [-0.5, 0.25]], dtype=np.float16)
    buf = io.BytesIO()
    p.write_half_vec2_array(buf, src)
    buf.seek(0)
    assert np.array_equal(p.read_half_vec2_array(buf, len(src)), src)


def test_byte_vec3_array_roundtrip() -> None:
    src = np.array([[0, 128, 255], [10, 20, 30]], dtype=np.uint8)
    buf = io.BytesIO()
    p.write_byte_vec3_array(buf, src)
    buf.seek(0)
    assert np.array_equal(p.read_byte_vec3_array(buf, len(src)), src)


def test_triangle_array_roundtrip() -> None:
    src = np.array([[0, 1, 2], [2, 1, 3]], dtype=np.uint16)
    buf = io.BytesIO()
    p.write_triangle_array(buf, src)
    assert buf.getvalue() == b"\x00\x00\x01\x00\x02\x00\x02\x00\x01\x00\x03\x00"
    buf.seek(0)
    assert np.array_equal(p.read_triangle_array(buf, len(src)), src)


def test_vec3_array_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError):
        p.write_vec3_array(io.BytesIO(), np.zeros((4, 2), dtype=np.float32))


# ---- BSVertexData packed dtype --------------------------------------------


# Bit reference (mirrors generated BSVertexData.read):
#   0x001 vertex, 0x002 uv, 0x008 normal, 0x010 tangent, 0x020 colors,
#   0x040 skinned, 0x100 eye, 0x400 full precision.

# Skyrim SE static mesh: vertex + uv + normal + tangent + colors, half precision.
SSE_STATIC_DESC = 0x001 | 0x002 | 0x008 | 0x010 | 0x020
# Skyrim SE skinned full-precision: + skinned + full precision.
SSE_SKINNED_FP_DESC = SSE_STATIC_DESC | 0x040 | 0x400


def test_vertex_dtype_static_sse_stride() -> None:
    dtype = p.vertex_dtype_for_desc(SSE_STATIC_DESC)
    # 6 (HalfVec3) + 2 (HalfTexCoord uv) -> wait: tangent is set, so bitangent_x is f16
    # 6 vertex + 2 bitangent_x + 4 uv + 4 normal+by + 4 tangent+bz + 4 colors = 24
    assert dtype.itemsize == 24
    assert set(dtype.names or ()) == {
        "vertex",
        "bitangent_x",
        "uv",
        "normal",
        "bitangent_y",
        "tangent",
        "bitangent_z",
        "vertex_colors",
    }


def test_vertex_dtype_full_precision_skinned_stride() -> None:
    dtype = p.vertex_dtype_for_desc(SSE_SKINNED_FP_DESC)
    # 12 vertex + 4 bitangent_x(f32) + 4 uv + 4 normal+by + 4 tangent+bz +
    # 4 colors + 8 weights(4 f16) + 4 indices(4 u8) = 44
    assert dtype.itemsize == 44
    assert "bone_weights" in (dtype.names or ())
    assert "bone_indices" in (dtype.names or ())


def test_packed_vertex_data_roundtrip_matches_per_record_codegen() -> None:
    """The vectorised reader must produce bytes identical to N per-record writes."""
    from nifblend.format.base import ReadContext
    from nifblend.format.generated.structs import BSVertexData

    desc = SSE_STATIC_DESC
    ctx = ReadContext(version=0x14020007, user_version=12, bs_version=100)
    ctx.push_arg(desc)

    # Build three vertices through the codegen path so any layout drift
    # between the dtype and the per-record reader is caught immediately.
    rng = np.random.default_rng(42)
    expected = np.zeros(3, dtype=p.vertex_dtype_for_desc(desc))
    expected["vertex"] = rng.standard_normal((3, 3)).astype(np.float16)
    expected["bitangent_x"] = rng.standard_normal(3).astype(np.float16)
    expected["uv"] = rng.standard_normal((3, 2)).astype(np.float16)
    expected["normal"] = rng.integers(0, 256, size=(3, 3), dtype=np.uint8)
    expected["bitangent_y"] = rng.integers(0, 256, size=3, dtype=np.uint8)
    expected["tangent"] = rng.integers(0, 256, size=(3, 3), dtype=np.uint8)
    expected["bitangent_z"] = rng.integers(0, 256, size=3, dtype=np.uint8)
    expected["vertex_colors"] = rng.integers(0, 256, size=(3, 4), dtype=np.uint8)

    buf = io.BytesIO()
    p.write_packed_vertex_data(buf, expected, desc)

    # Round-trip via the packed reader.
    buf.seek(0)
    got = p.read_packed_vertex_data(buf, 3, desc)
    assert got.dtype == expected.dtype
    assert np.array_equal(got.tobytes(), expected.tobytes())

    # Now feed the same bytes through the per-record codegen reader and check
    # the field values agree (catches dtype/codegen drift).
    buf.seek(0)
    for i in range(3):
        rec = BSVertexData.read(buf, ctx)
        assert rec.vertex.x == pytest.approx(float(expected["vertex"][i, 0]))
        assert rec.vertex.y == pytest.approx(float(expected["vertex"][i, 1]))
        assert rec.vertex.z == pytest.approx(float(expected["vertex"][i, 2]))
        assert rec.normal.x == int(expected["normal"][i, 0])
        assert rec.bitangent_y == int(expected["bitangent_y"][i])
        assert rec.tangent.x == int(expected["tangent"][i, 0])
        assert rec.bitangent_z == int(expected["bitangent_z"][i])
        assert rec.vertex_colors.r == int(expected["vertex_colors"][i, 0])

    ctx.pop_arg()


def test_write_packed_vertex_data_rejects_wrong_dtype() -> None:
    bad = np.zeros(2, dtype=np.uint8)
    with pytest.raises(ValueError, match="does not match desc"):
        p.write_packed_vertex_data(io.BytesIO(), bad, SSE_STATIC_DESC)


# ---- strings --------------------------------------------------------------


def test_sized_string_roundtrip() -> None:
    buf = io.BytesIO()
    p.write_sized_string(buf, "BSTriShape")
    buf.seek(0)
    assert p.read_sized_string(buf) == "BSTriShape"


def test_sized_string_truncated_raises() -> None:
    # length=10 in the header, but only 3 payload bytes follow.
    buf = io.BytesIO(struct.pack("<I", 10) + b"abc")
    with pytest.raises(EOFError):
        p.read_sized_string(buf)
