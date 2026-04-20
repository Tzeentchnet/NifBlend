"""Smoke tests for the generated NIF schema layer.

Verifies that `python -m tools.codegen` output imports cleanly, that every
seed type listed in `tools.codegen.whitelist.SEED_TYPES` shows up in the
relevant `__all__`, and that `python -m tools.codegen --check` reports no
drift between the committed files and a fresh regeneration.

These tests guard against:

- Codegen changes (cond compiler, emit pipeline) that produce syntactically
  invalid Python — caught by the import.
- Forgetting to commit a regeneration after editing the emitter or the
  schema — caught by the `--check` drift test.
- Whitelist additions that silently drop out of the closure walker.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.codegen.whitelist import SEED_TYPES

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_generated_modules_import() -> None:
    from nifblend.format.generated import bitfields, blocks, enums, structs

    assert blocks.__all__, "blocks.__all__ should be non-empty"
    assert structs.__all__, "structs.__all__ should be non-empty"
    assert enums.__all__, "enums.__all__ should be non-empty"
    assert bitfields.__all__, "bitfields.__all__ should be non-empty"


def test_seed_types_present_in_closure() -> None:
    """Every seed type should land in either blocks or structs after closure
    expansion. Catches whitelist entries the parser silently drops."""
    from nifblend.format.generated import blocks, structs
    from tools.codegen.emit import _class_name

    emitted = set(blocks.__all__) | set(structs.__all__)
    missing = [name for name in SEED_TYPES if _class_name(name) not in emitted]
    assert not missing, f"seed types missing from generated output: {missing}"


def test_codegen_check_no_drift() -> None:
    """Re-running codegen must produce byte-identical output to what's
    committed. Forces contributors to regenerate after editing the emitter."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.codegen", "--check"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            "codegen --check reported drift; run `python -m tools.codegen` "
            f"and commit the result.\nstderr:\n{result.stderr}"
        )
