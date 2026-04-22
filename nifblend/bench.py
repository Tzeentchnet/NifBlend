"""Performance benchmark harness (Phase 7 step 29).

Times NifBlend's parse + decode path against the reference
``blender_niftools_addon`` when the latter is importable. The harness
is split into pure helpers so the test suite can drive it on
synthesised in-memory NIFs without shelling out:

* :func:`time_nifblend_parse` runs the
  :func:`nifblend.ops.import_batch.parse_and_decode_many` pipeline N
  times over a list of paths and returns timing statistics.
* :func:`time_reference_parse` does the same for
  :mod:`blender_niftools_addon`'s ``NifFormat.Data().read`` if
  available, else returns ``None``.
* :func:`compare` returns a :class:`BenchmarkComparison` rolling both
  sides up with a speedup ratio.

The :func:`run_cli` entry point makes ``scripts/bench.py`` a thin
shim — it discovers ``*.nif`` files under ``tests/data/perf`` (or a
caller-supplied path) and prints a Markdown summary table.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nifblend.ops.import_batch import parse_and_decode_many

__all__ = [
    "BenchmarkComparison",
    "BenchmarkResult",
    "compare",
    "format_markdown_summary",
    "run_cli",
    "time_nifblend_parse",
    "time_reference_parse",
]


@dataclass(slots=True)
class BenchmarkResult:
    label: str
    iterations: int
    file_count: int
    samples_seconds: list[float]

    @property
    def best(self) -> float:
        return min(self.samples_seconds)

    @property
    def median(self) -> float:
        return statistics.median(self.samples_seconds)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.samples_seconds)

    @property
    def files_per_second(self) -> float:
        if self.best == 0:
            return float("inf")
        return self.file_count / self.best


@dataclass(slots=True)
class BenchmarkComparison:
    nifblend: BenchmarkResult
    reference: BenchmarkResult | None
    speedup: float | None  # reference.best / nifblend.best (>1 = NifBlend faster)


# ---- timing primitives ----------------------------------------------------


def _time_callable(fn: Callable[[], object], iterations: int) -> list[float]:
    """Run ``fn`` ``iterations`` times and return the per-iteration seconds."""
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def time_nifblend_parse(
    paths: list[Path],
    *,
    iterations: int = 3,
    max_workers: int | None = None,
) -> BenchmarkResult:
    """Time NifBlend's parallel parse+decode over ``paths``.

    The thread pool is created fresh per iteration so pool-warmup time is
    counted (matches what a one-shot operator invocation would pay).
    """
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    def _one() -> None:
        parse_and_decode_many(paths, max_workers=max_workers)

    samples = _time_callable(_one, iterations)
    return BenchmarkResult(
        label="nifblend",
        iterations=iterations,
        file_count=len(paths),
        samples_seconds=samples,
    )


def time_reference_parse(
    paths: list[Path], *, iterations: int = 3
) -> BenchmarkResult | None:
    """Time ``blender_niftools_addon``'s ``NifFormat.Data().read`` if importable.

    Returns ``None`` when the reference addon isn't on the import path
    (the common case in CI / local headless dev).
    """
    reader = _resolve_reference_reader()
    if reader is None:
        return None
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    def _one() -> None:
        for path in paths:
            with open(path, "rb") as fh:
                reader(fh)

    samples = _time_callable(_one, iterations)
    return BenchmarkResult(
        label="blender_niftools_addon",
        iterations=iterations,
        file_count=len(paths),
        samples_seconds=samples,
    )


def _resolve_reference_reader() -> Callable[[Any], object] | None:
    """Return a one-arg callable that reads a NIF stream, or ``None``."""
    try:
        # The reference addon ships its parser as ``NifFormat`` from
        # ``nifgen.formats.nif``; ``Data().read(stream)`` is the
        # canonical entry point per pyffi conventions.
        from nifgen.formats.nif import NifFormat  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - exercised only when addon is installed
        return None

    def _read(stream: Any) -> object:
        data = NifFormat.Data()
        data.read(stream)
        return data

    return _read


# ---- comparison ----------------------------------------------------------


def compare(
    paths: list[Path],
    *,
    iterations: int = 3,
    max_workers: int | None = None,
) -> BenchmarkComparison:
    """Time both pipelines over the same files and roll up a speedup ratio."""
    nb = time_nifblend_parse(paths, iterations=iterations, max_workers=max_workers)
    ref = time_reference_parse(paths, iterations=iterations)
    speedup: float | None = None
    if ref is not None and nb.best > 0:
        speedup = ref.best / nb.best
    return BenchmarkComparison(nifblend=nb, reference=ref, speedup=speedup)


def format_markdown_summary(cmp: BenchmarkComparison) -> str:
    """Render a comparison as a Markdown table fit for CI logs."""
    lines = [
        "| Pipeline | Files | Iters | Best (s) | Median (s) | Files/s |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in (cmp.nifblend, cmp.reference):
        if r is None:
            lines.append(
                "| blender_niftools_addon | — | — | _not installed_ | — | — |"
            )
            continue
        lines.append(
            f"| {r.label} | {r.file_count} | {r.iterations} | "
            f"{r.best:.4f} | {r.median:.4f} | {r.files_per_second:.1f} |"
        )
    if cmp.speedup is not None:
        lines.append("")
        marker = "OK" if cmp.speedup >= 3.0 else "warn"
        lines.append(
            f"**NifBlend speedup vs reference: {cmp.speedup:.2f}x** "
            f"(target: >=3x — {marker})"
        )
    return "\n".join(lines)


# ---- CLI -----------------------------------------------------------------


def run_cli(argv: list[str] | None = None) -> int:
    """Entry point used by ``scripts/bench.py``."""
    import argparse

    parser = argparse.ArgumentParser(description="NifBlend parse/decode benchmark")
    parser.add_argument(
        "path",
        nargs="?",
        default="nifblend/tests/data/perf",
        help="Folder of .nif files to time (default: nifblend/tests/data/perf)",
    )
    parser.add_argument(
        "--iterations", "-n", type=int, default=5, help="Iterations per pipeline"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=0, help="Worker threads (0 = auto)"
    )
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"error: {root!r} is not a directory")
        return 2
    paths = sorted(root.rglob("*.nif"))
    if not paths:
        print(f"error: no .nif files found under {root!r}")
        return 2

    cmp = compare(paths, iterations=args.iterations, max_workers=args.workers or None)
    print(format_markdown_summary(cmp))
    return 0
