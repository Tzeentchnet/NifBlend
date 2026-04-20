"""Run the NifBlend test suite inside Blender.

Usage (from repo root):
    blender --background --python-exit-code 1 -P scripts/run_tests.py

Outside Blender, just use `pytest` directly — the smoke test stubs `bpy`.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    import pytest

    return pytest.main(["-v", str(REPO_ROOT / "nifblend" / "tests")])


if __name__ == "__main__":
    sys.exit(main())
