"""Phase 2 step 10 — multi-mesh import → export → re-import round-trip tests.

These tests exercise the full v0.1 path the operators take:

    MeshData → mesh_data_to_bstrishape → BlockTable → write_nif
        → read_nif → bstrishape_to_mesh_data

against three distinct synthesised SSE meshes (single triangle, an
indexed quad split into two triangles, and a small tetrahedron). For
each sample the decoded :class:`MeshData` is compared back to the
source within attribute-appropriate float epsilons (full-precision
positions/UVs are bit-exact; byte-quantised normals/colors get
``1/127`` slack).

The operator wrappers themselves are thin glue around this loop --
:func:`nifblend.ops.import_nif.execute` calls :func:`read_nif` +
:func:`import_bstrishape`, and :func:`nifblend.ops.export_nif.execute`
calls :func:`export_bstrishape` + :func:`write_nif`. Covering the
underlying bridge + I/O for multiple distinct meshes is what the
roadmap actually requires (byte-equivalence is explicitly out of
scope; semantic equality within float epsilon is the gate).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
import pytest

from nifblend.bridge.mesh_in import MeshData, bstrishape_to_mesh_data
from nifblend.bridge.mesh_out import mesh_data_to_bstrishape
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import BSTriShape
from nifblend.format.generated.structs import BSStreamHeader, ExportString, Footer, Header
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, read_nif, write_nif

# ---- helpers --------------------------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_table(blocks: list[BSTriShape]) -> BlockTable:
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return BlockTable(header=h, blocks=list(blocks), footer=Footer(), ctx=ctx)


def _round_trip(data: MeshData, *, full_precision: bool = True) -> MeshData:
    """Build a BSTriShape, write a one-block NIF to bytes, read it back."""
    blk = mesh_data_to_bstrishape(data, full_precision=full_precision)
    table = _sse_table([blk])

    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    assert parsed.header.num_blocks == 1
    assert parsed.block_type_name(0) == "BSTriShape"
    rt_block = parsed.blocks[0]
    assert isinstance(rt_block, BSTriShape)
    return bstrishape_to_mesh_data(rt_block, name=data.name)


@dataclass
class _Sample:
    name: str
    data: MeshData


def _sample_triangle() -> _Sample:
    return _Sample(
        name="triangle",
        data=MeshData(
            name="triangle",
            positions=np.array(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                dtype=np.float32,
            ),
            triangles=np.array([[0, 1, 2]], dtype=np.uint32),
            normals=np.array([[0.0, 0.0, 1.0]] * 3, dtype=np.float32),
            uv=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            vertex_colors=np.array(
                [
                    [1.0, 0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0, 1.0],
                    [0.0, 0.0, 1.0, 1.0],
                ],
                dtype=np.float32,
            ),
        ),
    )


def _sample_quad() -> _Sample:
    # Indexed quad split into two triangles; shares vertices 0 and 2.
    return _Sample(
        name="quad",
        data=MeshData(
            name="quad",
            positions=np.array(
                [
                    [0.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0],
                    [0.0, 1.0, 0.0],
                ],
                dtype=np.float32,
            ),
            triangles=np.array([[0, 1, 2], [0, 2, 3]], dtype=np.uint32),
            normals=np.array([[0.0, 0.0, 1.0]] * 4, dtype=np.float32),
            uv=np.array(
                [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                dtype=np.float32,
            ),
        ),
    )


def _sample_tetrahedron() -> _Sample:
    # Regular-ish tetrahedron; per-vertex normals are the (normalised)
    # positions to give every component a distinct non-axis-aligned value.
    positions = np.array(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ],
        dtype=np.float32,
    )
    norms = positions / np.linalg.norm(positions, axis=1, keepdims=True)
    return _Sample(
        name="tetra",
        data=MeshData(
            name="tetra",
            positions=positions,
            triangles=np.array([[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]], dtype=np.uint32),
            normals=norms.astype(np.float32),
            uv=np.array(
                [[0.0, 0.0], [1.0, 0.0], [0.5, 1.0], [0.5, 0.5]],
                dtype=np.float32,
            ),
        ),
    )


# ---- the actual round-trip parametrisation --------------------------------


SAMPLES = [_sample_triangle(), _sample_quad(), _sample_tetrahedron()]


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: s.name)
def test_full_round_trip(sample: _Sample) -> None:
    src = sample.data
    decoded = _round_trip(src, full_precision=True)

    # Topology survives bit-exact.
    np.testing.assert_array_equal(decoded.triangles, src.triangles)
    # Full-precision positions and UVs are bit-exact (no half-float quant).
    np.testing.assert_array_equal(decoded.positions, src.positions)
    if src.uv is not None:
        assert decoded.uv is not None
        # UVs are stored as half-floats even in the "full-precision" path
        # (only positions get the float32 promotion); allow ~1/2048 slack.
        np.testing.assert_allclose(decoded.uv, src.uv, atol=1e-3)
    # Normals are byte-quantised on the wire; ~1/127 slack.
    if src.normals is not None:
        assert decoded.normals is not None
        np.testing.assert_allclose(decoded.normals, src.normals, atol=2 / 255)
    # Vertex colors round-trip through u8 too.
    if src.vertex_colors is not None:
        assert decoded.vertex_colors is not None
        np.testing.assert_allclose(decoded.vertex_colors, src.vertex_colors, atol=1 / 255)


def test_multi_block_round_trip_preserves_order_and_geometry() -> None:
    """Three distinct BSTriShapes in a single NIF survive a write→read pass."""
    blocks = [mesh_data_to_bstrishape(s.data, full_precision=True) for s in SAMPLES]
    table = _sse_table(blocks)

    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    assert parsed.header.num_blocks == len(SAMPLES)
    for i, sample in enumerate(SAMPLES):
        assert parsed.block_type_name(i) == "BSTriShape"
        rt = parsed.blocks[i]
        assert isinstance(rt, BSTriShape)
        decoded = bstrishape_to_mesh_data(rt, name=sample.name)
        np.testing.assert_array_equal(decoded.triangles, sample.data.triangles)
        np.testing.assert_array_equal(decoded.positions, sample.data.positions)
