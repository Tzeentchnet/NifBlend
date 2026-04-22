"""Phase 8d: Skyrim-specific operators (LE ↔ SE conversions).

Pure logic in :mod:`nifblend.bridge.games.skyrim`; this module is
the Blender wrapper. Operators are gated on
``nifblend.read_profile_from_object(obj) in {SKYRIM_LE, SKYRIM_SE}``
via the sidebar panel's ``poll()``.
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from nifblend.bridge.games.skyrim import (
    convert_shader_flags_le_to_se,
    convert_shader_flags_se_to_le,
)
from nifblend.bridge.material_props import PROP_ATTR
from nifblend.bridge.object_props import (
    apply_profile_to_object,
    read_profile_from_object,
)
from nifblend.format.versions import GameProfile

__all__ = [
    "NIFBLEND_OT_skyrim_le_to_se",
    "NIFBLEND_OT_skyrim_se_to_le",
]


def _convert_selected(
    context: bpy.types.Context,
    converter,
    target_profile: GameProfile,
) -> tuple[int, int]:
    """Apply ``converter`` to every material of every selected object.

    Returns ``(materials_touched, objects_touched)``.
    """
    mats_touched = 0
    objs_touched = 0
    seen_mats: set[int] = set()
    for obj in context.selected_objects or []:
        if getattr(obj, "type", "") != "MESH":
            continue
        objs_touched += 1
        for slot in getattr(obj, "material_slots", []) or []:
            mat = getattr(slot, "material", None)
            if mat is None or id(mat) in seen_mats:
                continue
            seen_mats.add(id(mat))
            props = getattr(mat, PROP_ATTR, None)
            if props is None:
                continue
            f1 = int(getattr(props, "shader_flags_1", 0))
            f2 = int(getattr(props, "shader_flags_2", 0))
            new1, new2 = converter(f1, f2)
            if new1 != f1:
                props.shader_flags_1 = new1
            if new2 != f2:
                props.shader_flags_2 = new2
            mats_touched += 1
        # update stamp
        apply_profile_to_object(
            obj,
            profile=target_profile,
            nif_version=int(getattr(obj.nifblend, "nif_version", 0)) if hasattr(obj, "nifblend") else 0,
            user_version=int(getattr(obj.nifblend, "user_version", 0)) if hasattr(obj, "nifblend") else 0,
            bs_version=100 if target_profile == GameProfile.SKYRIM_SE else 83,
            source_path=str(getattr(obj.nifblend, "source_path", "")) if hasattr(obj, "nifblend") else "",
            block_origin=str(getattr(obj.nifblend, "block_origin", "")) if hasattr(obj, "nifblend") else "",
        )
    return mats_touched, objs_touched


class NIFBLEND_OT_skyrim_le_to_se(Operator):
    """Convert selected Skyrim LE materials/objects to Skyrim SE."""

    bl_idname = "nifblend.skyrim_le_to_se"
    bl_label = "Convert LE → SE"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return any(
            read_profile_from_object(o) == GameProfile.SKYRIM_LE
            for o in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        mats, objs = _convert_selected(
            context, convert_shader_flags_le_to_se, GameProfile.SKYRIM_SE
        )
        self.report({"INFO"}, f"Converted {mats} material(s) on {objs} object(s) → SSE")
        return {"FINISHED"}


class NIFBLEND_OT_skyrim_se_to_le(Operator):
    """Convert selected Skyrim SE materials/objects back to Skyrim LE."""

    bl_idname = "nifblend.skyrim_se_to_le"
    bl_label = "Convert SE → LE"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return any(
            read_profile_from_object(o) == GameProfile.SKYRIM_SE
            for o in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        mats, objs = _convert_selected(
            context, convert_shader_flags_se_to_le, GameProfile.SKYRIM_LE
        )
        self.report({"INFO"}, f"Converted {mats} material(s) on {objs} object(s) → LE")
        return {"FINISHED"}
