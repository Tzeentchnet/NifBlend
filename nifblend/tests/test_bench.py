"""Phase 7 step 29 — benchmark harness tests.

Drives the pure timing helpers against synthesised in-memory NIFs;
the reference-addon comparison path is exercised via dependency
injection so the suite doesn't need ``blender_niftools_addon``
installed.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest

from nifblend.bench import (
    BenchmarkComparison,
    BenchmarkResult,
    compare,
    format_markdown_summary,
    run_cli,
    time_nifblend_parse,
    time_reference_parse,
)
from nifblend.bridge.mesh_in import MeshData
from nifblend.bridge.mesh_out import mesh_data_to_bstrishape
from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import BSStreamHeader, ExportString, Footer, Header
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _write_tiny_nif(path: Path) -> None:
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
    mdata = MeshData(
        name="t",
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
        ),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )
    block = mesh_data_to_bstrishape(mdata, full_precision=True)
    table = BlockTable(header=h, blocks=[block], footer=Footer(), ctx=ctx)
    sink = io.BytesIO()
    write_nif(sink, table)
    path.write_bytes(sink.getvalue())


@pytest.fixture
def nif_dir(tmp_path: Path) -> tuple[Path, list[Path]]:
    paths: list[Path] = []
    for i in range(3):
        p = tmp_path / f"m{i}.nif"
        _write_tiny_nif(p)
        paths.append(p)
    return tmp_path, paths


# ---- time_nifblend_parse -------------------------------------------------


def test_time_nifblend_parse_returns_per_iteration_samples(nif_dir) -> None:
    _, paths = nif_dir
    res = time_nifblend_parse(paths, iterations=3, max_workers=2)
    assert res.label == "nifblend"
    assert res.iterations == 3
    assert res.file_count == 3
    assert len(res.samples_seconds) == 3
    assert all(s >= 0.0 for s in res.samples_seconds)
    assert res.best <= res.median <= max(res.samples_seconds)


def test_time_nifblend_parse_rejects_zero_iterations(nif_dir) -> None:
    _, paths = nif_dir
    with pytest.raises(ValueError):
        time_nifblend_parse(paths, iterations=0)


# ---- time_reference_parse ------------------------------------------------


def test_time_reference_parse_returns_none_without_addon(nif_dir) -> None:
    """The headless test environment has no blender_niftools_addon."""
    _, paths = nif_dir
    assert time_reference_parse(paths, iterations=2) is None


def test_time_reference_parse_uses_resolver_when_present(
    nif_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, paths = nif_dir
    calls: list[int] = []

    def _fake_reader(_stream: object) -> object:
        calls.append(1)
        return object()

    from nifblend import bench

    monkeypatch.setattr(bench, "_resolve_reference_reader", lambda: _fake_reader)
    res = time_reference_parse(paths, iterations=2)
    assert res is not None
    assert res.label == "blender_niftools_addon"
    assert res.iterations == 2
    assert len(calls) == 2 * len(paths)  # iterations * files


# ---- compare + format ----------------------------------------------------


def test_compare_without_reference_yields_no_speedup(nif_dir) -> None:
    _, paths = nif_dir
    cmp = compare(paths, iterations=2, max_workers=2)
    assert cmp.reference is None
    assert cmp.speedup is None
    assert cmp.nifblend.file_count == 3


def test_compare_with_reference_computes_speedup(
    nif_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, paths = nif_dir

    def _slow_reader(_stream: object) -> object:
        # Burn a tiny but predictable amount of work so the timing is
        # measurable without making the test flaky.
        sum(range(2000))
        return object()

    from nifblend import bench

    monkeypatch.setattr(bench, "_resolve_reference_reader", lambda: _slow_reader)
    cmp = compare(paths, iterations=2, max_workers=2)
    assert cmp.reference is not None
    assert cmp.speedup is not None and cmp.speedup > 0.0


def test_format_markdown_summary_handles_missing_reference() -> None:
    nb = BenchmarkResult(
        label="nifblend", iterations=2, file_count=4, samples_seconds=[0.1, 0.2]
    )
    cmp = BenchmarkComparison(nifblend=nb, reference=None, speedup=None)
    md = format_markdown_summary(cmp)
    assert "nifblend" in md
    assert "_not installed_" in md
    assert "speedup" not in md.lower()


def test_format_markdown_summary_emits_speedup_line() -> None:
    nb = BenchmarkResult(
        label="nifblend", iterations=2, file_count=4, samples_seconds=[0.1, 0.2]
    )
    ref = BenchmarkResult(
        label="blender_niftools_addon",
        iterations=2,
        file_count=4,
        samples_seconds=[0.4, 0.5],
    )
    cmp = BenchmarkComparison(nifblend=nb, reference=ref, speedup=4.0)
    md = format_markdown_summary(cmp)
    assert "4.00x" in md
    assert ">=3x" in md


# ---- run_cli -------------------------------------------------------------


def test_run_cli_returns_2_on_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    assert run_cli([str(missing), "-n", "1"]) == 2


def test_run_cli_returns_0_on_real_directory(nif_dir, capsys) -> None:
    root, _ = nif_dir
    rc = run_cli([str(root), "-n", "2", "-w", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "nifblend" in out
    assert "Files/s" in out
