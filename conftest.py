"""Pytest fixtures + bootstrap.

Installs a minimal `bpy` / `bpy_extras` stub *before* any test module imports
the `nifblend` package, so unit tests can run without Blender. Real Blender
integration tests (marked `@pytest.mark.blender`) run via
`scripts/run_tests.py` inside Blender, where the real `bpy` is available.
"""

from __future__ import annotations

import sys
import types


def _install_bpy_stub() -> None:
    if "bpy" in sys.modules:
        return

    bpy = types.ModuleType("bpy")
    bpy.props = types.ModuleType("bpy.props")
    bpy.props.StringProperty = lambda **_kw: None  # type: ignore[attr-defined]
    bpy.types = types.ModuleType("bpy.types")
    bpy.types.Operator = type("Operator", (), {})  # type: ignore[attr-defined]
    bpy.types.Menu = type("Menu", (), {})  # type: ignore[attr-defined]
    bpy.types.Context = type("Context", (), {})  # type: ignore[attr-defined]

    class _MenuStub:
        @staticmethod
        def append(_f: object) -> None: ...
        @staticmethod
        def remove(_f: object) -> None: ...

    bpy.types.TOPBAR_MT_file_import = _MenuStub  # type: ignore[attr-defined]
    bpy.types.TOPBAR_MT_file_export = _MenuStub  # type: ignore[attr-defined]
    bpy.utils = types.ModuleType("bpy.utils")
    bpy.utils.register_class = lambda _c: None  # type: ignore[attr-defined]
    bpy.utils.unregister_class = lambda _c: None  # type: ignore[attr-defined]

    bpy_extras = types.ModuleType("bpy_extras")
    bpy_extras.io_utils = types.ModuleType("bpy_extras.io_utils")
    bpy_extras.io_utils.ImportHelper = type("ImportHelper", (), {})  # type: ignore[attr-defined]
    bpy_extras.io_utils.ExportHelper = type("ExportHelper", (), {})  # type: ignore[attr-defined]

    sys.modules["bpy"] = bpy
    sys.modules["bpy.props"] = bpy.props
    sys.modules["bpy.types"] = bpy.types
    sys.modules["bpy.utils"] = bpy.utils
    sys.modules["bpy_extras"] = bpy_extras
    sys.modules["bpy_extras.io_utils"] = bpy_extras.io_utils


_install_bpy_stub()
