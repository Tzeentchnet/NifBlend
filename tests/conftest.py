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

    def _prop_factory(**_kw):  # - test stub
        return None

    for _name in (
        "StringProperty",
        "IntProperty",
        "FloatProperty",
        "BoolProperty",
        "FloatVectorProperty",
        "IntVectorProperty",
        "EnumProperty",
        "CollectionProperty",
        "PointerProperty",
    ):
        setattr(bpy.props, _name, _prop_factory)

    bpy.types = types.ModuleType("bpy.types")
    bpy.types.Operator = type("Operator", (), {})  # type: ignore[attr-defined]
    bpy.types.Panel = type("Panel", (), {})  # type: ignore[attr-defined]
    bpy.types.Menu = type("Menu", (), {})  # type: ignore[attr-defined]
    bpy.types.UIList = type("UIList", (), {})  # type: ignore[attr-defined]
    bpy.types.Context = type("Context", (), {})  # type: ignore[attr-defined]
    bpy.types.PropertyGroup = type("PropertyGroup", (), {})  # type: ignore[attr-defined]
    bpy.types.AddonPreferences = type("AddonPreferences", (), {})  # type: ignore[attr-defined]
    bpy.types.Material = type("Material", (), {})  # type: ignore[attr-defined]
    bpy.types.Bone = type("Bone", (), {})  # type: ignore[attr-defined]
    bpy.types.EditBone = type("EditBone", (), {})  # type: ignore[attr-defined]
    bpy.types.Object = type("Object", (), {})  # type: ignore[attr-defined]
    bpy.types.Armature = type("Armature", (), {})  # type: ignore[attr-defined]
    bpy.types.VertexGroup = type("VertexGroup", (), {})  # type: ignore[attr-defined]
    bpy.types.Mesh = type("Mesh", (), {})  # type: ignore[attr-defined]
    bpy.types.UILayout = type("UILayout", (), {})  # type: ignore[attr-defined]
    bpy.types.Scene = type("Scene", (), {})  # type: ignore[attr-defined]
    bpy.types.Action = type("Action", (), {})  # type: ignore[attr-defined]
    bpy.types.PoseBone = type("PoseBone", (), {})  # type: ignore[attr-defined]

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
