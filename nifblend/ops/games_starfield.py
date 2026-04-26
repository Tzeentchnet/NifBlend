"""Phase 9d: Starfield-specific operators wired through the bridge.

* :class:`NIFBLEND_OT_starfield_reload_external_mesh` re-runs the
  Phase 9b decoder for the active object's referenced ``.mesh`` file
  using the configured Starfield Data root, replacing the active
  mesh's vertex / triangle data in place.
* :class:`NIFBLEND_OT_starfield_reload_material` (Phase 9i) re-resolves
  and re-decodes the Starfield ``.mat`` JSON manifest stamped on the
  active object's first material slot, rebuilding its Principled-BSDF
  graph in place. Pairs with the reload-mesh op above so a Data-root
  reconfiguration (or a manifest edit on disk) takes effect without a
  full re-import.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.types import Operator

from nifblend.bridge.external_assets import PrefsExternalAssetResolver
from nifblend.bridge.games.starfield import (
    StarfieldExternalMeshError,
    decode_external_mesh,
)
from nifblend.bridge.games.starfield_material import (
    StarfieldMaterialError,
    load_starfield_material,
)
from nifblend.bridge.material_in import material_data_to_blender
from nifblend.bridge.material_props import (
    get_starfield_material_path,
    set_starfield_material_path,
)
from nifblend.bridge.mesh_in import BSGeometryMeshRef, mesh_data_to_blender
from nifblend.bridge.object_props import object_profile
from nifblend.format.versions import GameProfile
from nifblend.preferences import data_root_for, get_prefs

__all__ = [
    "NIFBLEND_OT_starfield_reload_external_mesh",
    "NIFBLEND_OT_starfield_reload_material",
]


class NIFBLEND_OT_starfield_reload_external_mesh(Operator):
    """Re-decode the active mesh's Starfield ``.mesh`` reference."""

    bl_idname = "nifblend.starfield_reload_external_mesh"
    bl_label = "Reload External Mesh"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = getattr(context, "active_object", None)
        if obj is None or getattr(obj, "type", "") != "MESH":
            return False
        return object_profile(obj) == GameProfile.STARFIELD

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        shape = getattr(obj.data, "nifblend_shape", None)
        slots = list(getattr(shape, "fo76_slots", []) or []) if shape is not None else []
        active_idx = int(getattr(shape, "num_primitives", 0) or 0) if shape is not None else 0
        if not slots or active_idx >= len(slots):
            self.report({"WARNING"}, "No external mesh slot selected on active object")
            return {"CANCELLED"}

        slot = slots[active_idx]
        rel_path = str(getattr(slot, "mesh_path", "") or "")
        if not rel_path:
            self.report({"WARNING"}, "Active slot has no mesh_path")
            return {"CANCELLED"}

        prefs = get_prefs(context)
        data_root = data_root_for(GameProfile.STARFIELD, prefs)
        if not data_root:
            self.report({"ERROR"}, "Starfield Data root is not configured in preferences")
            return {"CANCELLED"}

        mode = str(getattr(prefs, "texture_resolution_mode", "CASE_INSENSITIVE") or "CASE_INSENSITIVE")
        resolver = PrefsExternalAssetResolver(data_root=data_root, mode=mode)
        ref = BSGeometryMeshRef(
            lod_index=int(getattr(slot, "lod_index", active_idx) or 0),
            has_mesh=True,
            mesh_path=rel_path,
        )
        try:
            imp = decode_external_mesh(ref, resolver=resolver, name_prefix=Path(rel_path).stem)
        except StarfieldExternalMeshError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        new_mesh = mesh_data_to_blender(imp.mesh)
        old = obj.data
        obj.data = new_mesh
        if old is not None and getattr(old, "users", 0) == 0:
            with _suppress(AttributeError):
                bpy.data.meshes.remove(old)

        self.report({"INFO"}, f"Reloaded {rel_path} (LOD{imp.lod_index})")
        return {"FINISHED"}


class NIFBLEND_OT_starfield_reload_material(Operator):
    """Re-decode the active object's Starfield ``.mat`` manifest in place.

    The ``.mat`` rel-path is the one stamped onto
    :attr:`material.nifblend.starfield_material_path` by the Phase 9g
    importer. The operator re-resolves it through the configured
    Starfield ``Data/`` root, rebuilds a fresh Principled-BSDF graph via
    :func:`material_data_to_blender`, and swaps the result into the
    active object's first material slot. Texture paths inside the
    rebuilt graph are resolved through the same
    ``STRICT`` / ``CASE_INSENSITIVE`` / ``FUZZY_LOOSEN_ROOT`` mode the
    importer uses, so a Data-root edit takes effect without a full
    re-import.
    """

    bl_idname = "nifblend.starfield_reload_material"
    bl_label = "Reload Starfield Material"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = getattr(context, "active_object", None)
        if obj is None or getattr(obj, "type", "") != "MESH":
            return False
        if object_profile(obj) != GameProfile.STARFIELD:
            return False
        slots = list(getattr(obj.data, "materials", []) or [])
        return any(
            slot is not None and get_starfield_material_path(slot) for slot in slots
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        slots = list(getattr(obj.data, "materials", []) or [])
        target_index: int | None = None
        rel_path = ""
        for idx, slot in enumerate(slots):
            if slot is None:
                continue
            stamp = get_starfield_material_path(slot)
            if stamp:
                target_index = idx
                rel_path = stamp
                break
        if target_index is None:
            self.report(
                {"WARNING"},
                "No material slot carries a Starfield .mat path stamp",
            )
            return {"CANCELLED"}

        prefs = get_prefs(context)
        data_root = data_root_for(GameProfile.STARFIELD, prefs)
        if not data_root:
            self.report({"ERROR"}, "Starfield Data root is not configured in preferences")
            return {"CANCELLED"}

        mode = str(
            getattr(prefs, "texture_resolution_mode", "CASE_INSENSITIVE")
            or "CASE_INSENSITIVE"
        )
        resolver = PrefsExternalAssetResolver(data_root=data_root, mode=mode)
        try:
            mat_data = load_starfield_material(rel_path, resolver=resolver)
        except StarfieldMaterialError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        try:
            new_material = material_data_to_blender(
                mat_data,
                bpy=bpy,
                resolve_texture=resolver.resolve_texture,
            )
        except (AttributeError, RuntimeError, TypeError) as exc:
            self.report(
                {"ERROR"},
                f"Failed to materialise Starfield material: {exc}",
            )
            return {"CANCELLED"}

        # Re-stamp the rel-path on the freshly built material so a
        # second reload still finds it.
        with _suppress(AttributeError, RuntimeError, TypeError):
            set_starfield_material_path(new_material, rel_path)

        old = obj.data.materials[target_index]
        obj.data.materials[target_index] = new_material
        if old is not None and getattr(old, "users", 0) == 0:
            with _suppress(AttributeError):
                bpy.data.materials.remove(old)

        self.report({"INFO"}, f"Reloaded {rel_path}")
        return {"FINISHED"}


class _suppress:
    """Local copy of ``contextlib.suppress`` (avoids one extra import line)."""

    def __init__(self, *exc: type[BaseException]) -> None:
        self._exc = exc

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return exc_type is not None and issubclass(exc_type, self._exc)
