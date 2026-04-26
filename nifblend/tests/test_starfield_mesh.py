"""Phase 9b tests: Starfield ``.mesh`` decoder + encoder round-trip."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest

from nifblend.format.starfield_mesh import (
    STARFIELD_MESH_MAGIC,
    StarfieldMeshData,
    StarfieldMeshLOD,
    is_starfield_mesh,
    read_starfield_mesh,
    write_starfield_mesh,
)


def _roundtrip(data: StarfieldMeshData) -> StarfieldMeshData:
    buf = BytesIO()
    write_starfield_mesh(buf, data)
    buf.seek(0)
    return read_starfield_mesh(buf)


def _make_minimal() -> StarfieldMeshData:
    return StarfieldMeshData(
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
        ),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )


def test_is_starfield_mesh_recognises_magic() -> None:
    buf = BytesIO()
    write_starfield_mesh(buf, _make_minimal())
    buf.seek(0)
    assert is_starfield_mesh(buf) is True
    # The stream cursor must be reset after the peek.
    assert buf.tell() == 0


def test_is_starfield_mesh_rejects_unknown_magic() -> None:
    buf = BytesIO(b"\xff\xff\xff\xff" + b"\x00" * 32)
    assert is_starfield_mesh(buf) is False


def test_is_starfield_mesh_rejects_short_stream() -> None:
    assert is_starfield_mesh(BytesIO(b"\x01\x00")) is False


def test_minimal_roundtrip_preserves_geometry() -> None:
    src = _make_minimal()
    out = _roundtrip(src)
    assert out.magic == STARFIELD_MESH_MAGIC
    np.testing.assert_array_equal(out.positions, src.positions)
    np.testing.assert_array_equal(out.triangles, src.triangles)
    assert out.uv is None
    assert out.normals is None
    assert out.bone_indices is None


def test_full_geometry_roundtrip() -> None:
    src = StarfieldMeshData(
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]],
            dtype=np.float32,
        ),
        triangles=np.array([[0, 1, 2], [1, 3, 2]], dtype=np.uint32),
        uv=np.array(
            [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32
        ),
        colors=np.array(
            [
                [1.0, 0.0, 0.0, 1.0],
                [0.0, 1.0, 0.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [1.0, 1.0, 1.0, 1.0],
            ],
            dtype=np.float32,
        ),
        normals=np.array(
            [[0, 0, 1], [0, 0, 1], [0, 0, 1], [0, 0, 1]], dtype=np.float32
        ),
        lods=[StarfieldMeshLOD(start_index=0, num_indices=6, distance=100.0)],
    )
    out = _roundtrip(src)
    np.testing.assert_array_equal(out.positions, src.positions)
    np.testing.assert_array_equal(out.triangles, src.triangles)
    # half-float UV round-trip is exact for these values.
    np.testing.assert_allclose(out.uv, src.uv, atol=1e-3)
    # u8 colour quantisation is exact for these values.
    np.testing.assert_allclose(out.colors, src.colors, atol=1.0 / 255.0)
    # 10/10/10 normal pack is approximate but within ~0.001 for axis-aligned.
    np.testing.assert_allclose(out.normals, src.normals, atol=2e-3)
    assert len(out.lods) == 1
    assert out.lods[0].start_index == 0
    assert out.lods[0].num_indices == 6
    assert out.lods[0].distance == pytest.approx(100.0)


def test_skinned_roundtrip_preserves_weights() -> None:
    n = 3
    k = 4
    src = StarfieldMeshData(
        num_weights_per_vertex=k,
        positions=np.zeros((n, 3), dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        bone_indices=np.array(
            [[0, 1, 2, 3], [0, 0, 0, 0], [3, 2, 1, 0]], dtype=np.uint8
        ),
        bone_weights=np.array(
            [
                [0.4, 0.3, 0.2, 0.1],
                [1.0, 0.0, 0.0, 0.0],
                [0.25, 0.25, 0.25, 0.25],
            ],
            dtype=np.float32,
        ),
    )
    out = _roundtrip(src)
    assert out.num_weights_per_vertex == k
    np.testing.assert_array_equal(out.bone_indices, src.bone_indices)
    # u16 unorm quantisation is well within 1e-4.
    np.testing.assert_allclose(out.bone_weights, src.bone_weights, atol=2e-5)


def test_bad_index_count_raises() -> None:
    # Manually craft a stream with num_indices not a multiple of 3.
    buf = BytesIO()
    buf.write((1).to_bytes(4, "little"))   # magic
    buf.write((4).to_bytes(4, "little"))   # num_indices = 4 (bad)
    buf.write(b"\x00" * 8)                  # 4 u16 indices
    buf.seek(0)
    with pytest.raises(ValueError, match="multiple of 3"):
        read_starfield_mesh(buf)


def test_bad_magic_raises() -> None:
    buf = BytesIO(b"\xab\xcd\x00\x00" + b"\x00" * 32)
    with pytest.raises(ValueError, match="magic"):
        read_starfield_mesh(buf)


def test_snorm_position_path_roundtrips_within_quantisation() -> None:
    # When scale != 1.0, positions go through i16 snorm packing.
    src = StarfieldMeshData(
        scale=2.0,
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, -0.5, 0.25], [-1.5, 1.0, 2.0]], dtype=np.float32
        ),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )
    out = _roundtrip(src)
    # Quantisation: 2.0 / 32767 ~= 6.1e-5; allow generous slack.
    np.testing.assert_allclose(out.positions, src.positions, atol=1e-4)
