"""Phase 8d: Oblivion-specific operators (triangle ↔ strip conversion)."""

from __future__ import annotations

import bpy
from bpy.types import Operator

from nifblend.bridge.games.oblivion import triangles_to_strips
from nifblend.bridge.object_props import read_profile_from_object
from nifblend.format.versions import GameProfile

__all__ = ["NIFBLEND_OT_oblivion_stripify"]


_STRIPIFIABLE_PROFILES = {
    GameProfile.MORROWIND,
    GameProfile.OBLIVION,
    GameProfile.FALLOUT_3_NV,
}


class NIFBLEND_OT_oblivion_stripify(Operator):
    """Generate triangle-strip metadata for the active mesh.

    The actual ``NiTriStrips`` block is built at export time; this
    operator stores the strip layout as a custom property on the mesh
    so the export operator can prefer it over a fresh stripification
    (deterministic re-export of edited meshes).
    """

    bl_idname = "nifblend.oblivion_stripify"
    bl_label = "Stripify Active Mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            return False
        return read_profile_from_object(obj) in _STRIPIFIABLE_PROFILES

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        if obj is None:
            return {"CANCELLED"}
        mesh = obj.data
        triangles: list[tuple[int, int, int]] = []
        for poly in mesh.polygons:
            verts = list(poly.vertices)
            if len(verts) == 3:
                triangles.append((verts[0], verts[1], verts[2]))
            elif len(verts) == 4:
                triangles.append((verts[0], verts[1], verts[2]))
                triangles.append((verts[0], verts[2], verts[3]))
        strips = triangles_to_strips(triangles)
        mesh["nifblend_strips"] = [list(s) for s in strips]
        self.report({"INFO"}, f"Built {len(strips)} strip(s) covering {len(triangles)} triangle(s)")
        return {"FINISHED"}
