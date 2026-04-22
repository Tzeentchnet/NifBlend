"""Phase 8e: pure helpers for the NifCity-style cell-layout import.

Blender-free / unit-testable. The matching :mod:`nifblend.ops.import_cell`
operator wraps these helpers.

The CSV format is the one emitted by the bundled xEdit script
(:mod:`nifblend.scripts.blender_export`): one row per worldspace REFR /
ACHR / ... record, fields ``model_path,X,Y,Z,rotX,rotY,rotZ,scale``.
Rotation values are degrees in the Bethesda convention (clockwise about
each axis); :func:`bethesda_euler_to_blender` does the conversion to
Blender's intrinsic XYZ Euler.
"""

from __future__ import annotations

import csv
import io
import math
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CSV_HEADER_LINE",
    "CellPlacement",
    "bethesda_euler_to_blender",
    "compute_origin_offset",
    "parse_cell_csv",
    "should_skip",
]


#: Header row written by the xEdit ``.pas`` script. Recognised (and
#: skipped) on read; parser also tolerates files without a header.
CSV_HEADER_LINE = "# model,x,y,z,rx,ry,rz,scale"


@dataclass(frozen=True, slots=True)
class CellPlacement:
    """One CSV row's worth of placement data."""

    model_path: str
    location: tuple[float, float, float]
    rotation_deg: tuple[float, float, float]
    scale: float


def parse_cell_csv(
    source: str | Path | Iterable[str],
    *,
    header_present: bool = True,
) -> list[CellPlacement]:
    """Parse a NifCity-style CSV into :class:`CellPlacement` rows.

    ``source`` may be a path, a multi-line CSV text, or any iterable of
    raw CSV lines (the caller can pre-split). Tolerant of:

    * blank rows (skipped),
    * rows whose first cell starts with ``#`` (comment / header),
    * empty ``scale`` cell → defaults to ``1.0``,
    * malformed numeric cells → row skipped silently.

    Returned in source order. ``header_present`` is informational only --
    a ``# ...`` row is skipped regardless of this flag.
    """
    text_iter: Iterable[str]
    if isinstance(source, (str, Path)) and (
        isinstance(source, Path) or "\n" not in str(source)
    ):
        path = Path(source)
        if path.exists():
            text_iter = path.read_text(encoding="utf-8-sig").splitlines()
        else:
            # treat as raw text after all
            text_iter = str(source).splitlines()
    elif isinstance(source, str):
        text_iter = source.splitlines()
    else:
        text_iter = list(source)

    out: list[CellPlacement] = []
    reader = csv.reader(io.StringIO("\n".join(text_iter)))
    for row in reader:
        if not row:
            continue
        first = row[0].strip()
        if not first or first.startswith("#"):
            continue
        if len(row) < 7:
            continue
        try:
            x, y, z = float(row[1]), float(row[2]), float(row[3])
            rx, ry, rz = float(row[4]), float(row[5]), float(row[6])
        except (ValueError, IndexError):
            continue
        scale_raw = row[7].strip() if len(row) > 7 else ""
        try:
            scale = float(scale_raw) if scale_raw else 1.0
        except ValueError:
            scale = 1.0
        out.append(
            CellPlacement(
                model_path=first,
                location=(x, y, z),
                rotation_deg=(rx, ry, rz),
                scale=scale,
            )
        )
    return out


def compute_origin_offset(
    placements: Sequence[CellPlacement],
) -> tuple[float, float, float]:
    """Average all positions, integer-truncated per axis.

    Empty input → ``(0.0, 0.0, 0.0)``. Truncation matches NifCity (keeps
    the offset a round number so it can be shared / re-used between
    runs). The truncation is towards zero -- ``int(2.7)`` → ``2``,
    ``int(-2.7)`` → ``-2``.
    """
    if not placements:
        return (0.0, 0.0, 0.0)
    n = len(placements)
    sx = sum(p.location[0] for p in placements)
    sy = sum(p.location[1] for p in placements)
    sz = sum(p.location[2] for p in placements)
    return (float(int(sx / n)), float(int(sy / n)), float(int(sz / n)))


def should_skip(
    model_path: str,
    exclude_prefixes: Sequence[str] = ("marker", "fx"),
) -> bool:
    """True when the **basename** of ``model_path`` starts with any prefix.

    NifCity used a substring match, which false-positives on names like
    ``markette.nif`` or ``effects.nif``. We use a basename-prefix match
    instead (case-insensitive). Prefixes are matched against either the
    bare prefix or the prefix followed by ``_`` / ``-`` / digit / ``.``,
    so ``markersmall.nif`` is rejected (true skip) but ``markette.nif``
    is accepted.
    """
    if not model_path:
        return True
    basename = os.path.basename(model_path.replace("\\", "/")).lower()
    for prefix in exclude_prefixes:
        p = prefix.strip().lower()
        if not p:
            continue
        if basename == p or basename.startswith(p + "."):
            return True
        if basename.startswith(p):
            tail = basename[len(p):]
            # accept only tails that look like a continuation of a longer
            # word: a letter following the prefix means a different token
            # (markette → "tte" is letters, NOT a skip).
            if tail and (tail[0] in "._-" or tail[0].isdigit()):
                return True
    return False


def bethesda_euler_to_blender(
    rx_deg: float,
    ry_deg: float,
    rz_deg: float,
) -> tuple[float, float, float]:
    """Convert a Bethesda xEdit ``(rx, ry, rz)`` triple to Blender Euler radians.

    Bethesda stores rotation as degrees clockwise about each axis;
    Blender's Euler is right-hand intrinsic XYZ in radians. NifCity's
    formula:

    1. Negate each angle as ``360 - angle`` (CCW → CW conversion via
       complement).
    2. Convert each to radians.
    3. Compose by sequential intrinsic ``rotate_axis("X" → "Y" → "Z")``
       on a zero Euler.

    Steps (1) + (2) are pure scalar math; step (3) is mathematically
    identical to constructing an Euler with ``mode='XYZ'`` and the same
    radian triple, which is what we return. The operator wraps the
    result into a ``mathutils.Euler`` -- this helper stays pure.
    """
    return (
        math.radians(360.0 - float(rx_deg)),
        math.radians(360.0 - float(ry_deg)),
        math.radians(360.0 - float(rz_deg)),
    )
