"""Thin CLI shim around :func:`nifblend.bench.run_cli` (Phase 7 step 29).

Run from the repo root:

    python scripts/bench.py [path-to-nif-folder] [--iterations N] [--workers N]

Times NifBlend's parse + decode pipeline against
``blender_niftools_addon`` (when importable) and prints a Markdown
summary table. The ``>=3x`` speedup target gates Phase 7 in the
roadmap's verification matrix.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow ``python scripts/bench.py`` from the repo root without an install.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from nifblend.bench import run_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_cli())
