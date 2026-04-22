"""Phase 8g: Morrowind operator (classic material split).

Stamps the active object's material(s) with the classic-property
``origin`` so :func:`nifblend.bridge.material_out.build_classic_material_blocks`
is chosen at export, and reports a dry-run preview of the blocks that
would be emitted.
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from nifblend.bridge.games.morrowind import preview_classic_split
from nifblend.bridge.material_in import CLASSIC_TEXTURE_SLOT_NAMES, MaterialData
from nifblend.bridge.material_props import (
    PROP_ATTR,
    read_material_data_from_props,
)
from nifblend.bridge.object_props import read_profile_from_object
from nifblend.format.versions import GameProfile

__all__ = ["NIFBLEND_OT_morrowind_split_classic_props"]


_MORROWIND_PROFILES = {
    GameProfile.MORROWIND,
    GameProfile.OBLIVION,
}


def _material_data_from(mat: bpy.types.Material) -> MaterialData:
    data = MaterialData(name=mat.name)
    props = getattr(mat, PROP_ATTR, None)
    if props is not None:
        read_material_data_from_props(mat, data)
    # Seed textures from props.textures if any slot was populated.
    if not data.textures and props is not None:
        for slot_row in getattr(props, "textures", []) or []:
            slot = str(getattr(slot_row, "slot", "") or "")
            path = str(getattr(slot_row, "path", "") or "")
            if slot and path and slot in CLASSIC_TEXTURE_SLOT_NAMES:
                data.textures[slot] = path
    return data


class NIFBLEND_OT_morrowind_split_classic_props(Operator):
    """Mark selected materials for classic (``NiMaterialProperty`` / ``NiTexturingProperty``) export."""

    bl_idname = "nifblend.morrowind_split_classic_props"
    bl_label = "Split Classic Props"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return any(
            read_profile_from_object(o) in _MORROWIND_PROFILES
            for o in (context.selected_objects or [])
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        touched: list[str] = []
        slot_rows = 0
        for obj in context.selected_objects or []:
            if getattr(obj, "type", "") != "MESH":
                continue
            for slot in getattr(obj, "material_slots", []) or []:
                mat = getattr(slot, "material", None)
                if mat is None:
                    continue
                props = getattr(mat, PROP_ATTR, None)
                if props is None:
                    continue
                props.origin = "NiMaterialProperty"
                data = _material_data_from(mat)
                preview = preview_classic_split(data)
                slot_rows += preview.source_texture_count
                touched.append(mat.name)
        self.report(
            {"INFO"},
            f"Stamped {len(set(touched))} material(s); "
            f"{slot_rows} classic texture slot(s) would be emitted.",
        )
        return {"FINISHED"}
