"""Smoke test — verifies the package imports and exposes `register`/`unregister`.

The `bpy` stub is installed by `tests/conftest.py` so this runs without
Blender. Real Blender-integration tests are marked `@pytest.mark.blender` and
run via `scripts/run_tests.py`.
"""

from __future__ import annotations


def test_package_imports() -> None:
    import nifblend

    assert hasattr(nifblend, "register")
    assert hasattr(nifblend, "unregister")


def test_register_unregister_roundtrip() -> None:
    import nifblend

    nifblend.register()
    nifblend.unregister()
