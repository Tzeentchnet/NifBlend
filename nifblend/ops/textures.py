"""Phase 8i: texture-path utilities tied to per-game ``Data/`` roots.

Two operators:

* :class:`NIFBLEND_OT_relink_textures_against_data_root` walks every
  ``bpy.data.images`` entry, re-resolves its filepath against the
  active :class:`~nifblend.format.versions.GameProfile`'s configured
  Data/ root, and updates ``image.filepath`` on hit. Misses are stashed
  on ``scene.nifblend_texture_misses`` so the sidebar UIList can
  surface them.
* :class:`NIFBLEND_OT_bake_diffuse_to_texture` bakes the active
  material's Principled BSDF result to a fresh image. Standard Blender
  bake setup; mostly a convenience to keep modders inside one tab.

Pure resolution helpers live in :mod:`nifblend.bridge.textures`; this
module is the Blender-state-coupled wrapper layer.
"""

from __future__ import annotations

import contextlib

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy.types import Operator, PropertyGroup

from nifblend.bridge.textures import audit_image_paths
from nifblend.format.versions import GameProfile
from nifblend.preferences import data_root_for, get_prefs

__all__ = [
    "NIFBLEND_OT_bake_diffuse_to_texture",
    "NIFBLEND_OT_relink_textures_against_data_root",
    "NIFBLEND_PG_texture_miss",
    "register",
    "unregister",
]


def _profile_from_context(context: bpy.types.Context) -> GameProfile:
    """Pick a GameProfile from the active object, falling back to prefs default."""
    obj = getattr(context, "active_object", None)
    if obj is not None and hasattr(obj, "nifblend"):
        try:
            return GameProfile(obj.nifblend.game_profile)
        except (ValueError, AttributeError):
            pass
    prefs = get_prefs(context)
    if prefs is not None:
        try:
            return GameProfile(prefs.default_profile)
        except (ValueError, AttributeError):
            pass
    return GameProfile.UNKNOWN


class NIFBLEND_PG_texture_miss(PropertyGroup):
    """One unresolved-image entry surfaced by the relink operator."""

    image_name: StringProperty(name="Image")  # type: ignore[valid-type]
    nif_relative: StringProperty(name="NIF-relative path")  # type: ignore[valid-type]
    original_filepath: StringProperty(name="Original filepath")  # type: ignore[valid-type]


_RESOLUTION_ITEMS = [
    ("STRICT", "Strict", "Path must match on disk verbatim"),
    ("CASE_INSENSITIVE", "Case-insensitive", "Walk components case-insensitively"),
    ("FUZZY_LOOSEN_ROOT", "Loosen root", "Try every Data root in turn; first hit wins"),
]


class NIFBLEND_OT_relink_textures_against_data_root(Operator):
    """Re-resolve every Blender image against the active game's Data/ root."""

    bl_idname = "nifblend.relink_textures_against_data_root"
    bl_label = "Relink Textures (Data Root)"
    bl_options = {"REGISTER", "UNDO"}

    mode: EnumProperty(  # type: ignore[valid-type]
        name="Resolution Mode",
        description="How to resolve NIF-relative paths against Data roots",
        items=_RESOLUTION_ITEMS,
        default="CASE_INSENSITIVE",
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        prefs = get_prefs(context)
        profile = _profile_from_context(context)
        data_root = data_root_for(profile, prefs)
        if not data_root:
            self.report(
                {"ERROR"},
                f"No Data root configured for {profile.value}; "
                f"set it in NifBlend addon preferences",
            )
            return {"CANCELLED"}

        # Layer in every other configured Data root for FUZZY mode.
        extra_roots: list[str] = []
        if self.mode == "FUZZY_LOOSEN_ROOT" and prefs is not None:
            for other in (
                GameProfile.MORROWIND,
                GameProfile.OBLIVION,
                GameProfile.FALLOUT_3_NV,
                GameProfile.SKYRIM_LE,
                GameProfile.SKYRIM_SE,
                GameProfile.FALLOUT_4,
                GameProfile.FALLOUT_76,
            ):
                if other == profile:
                    continue
                root = data_root_for(other, prefs)
                if root:
                    extra_roots.append(root)

        images = list(bpy.data.images)
        pairs = [(img.name, img.filepath or "") for img in images]
        results = audit_image_paths(
            pairs,
            data_root=data_root,
            mode=self.mode,
            extra_roots=extra_roots,
        )

        scene = context.scene
        misses_coll = getattr(scene, "nifblend_texture_misses", None)
        if misses_coll is not None:
            misses_coll.clear()

        relinked = 0
        for img, entry in zip(images, results, strict=True):
            if entry.found and entry.resolved and entry.resolved != img.filepath:
                img.filepath = entry.resolved
                relinked += 1
            elif not entry.found and misses_coll is not None:
                miss = misses_coll.add()
                miss.image_name = entry.image_name
                miss.nif_relative = entry.nif_relative
                miss.original_filepath = entry.original_filepath

        misses = sum(1 for r in results if not r.found)
        self.report(
            {"INFO" if misses == 0 else "WARNING"},
            f"Relinked {relinked} image(s); {misses} unresolved against {data_root!r}",
        )
        return {"FINISHED"}


_BAKE_TYPE_ITEMS = [
    ("DIFFUSE", "Diffuse", "Bake the diffuse colour pass"),
    ("EMIT", "Emission", "Bake the emission pass"),
    ("NORMAL", "Normal", "Bake the normal pass"),
    ("ROUGHNESS", "Roughness", "Bake the roughness pass"),
]


class NIFBLEND_OT_bake_diffuse_to_texture(Operator):
    """Bake the active material's Principled BSDF result to a fresh image."""

    bl_idname = "nifblend.bake_diffuse_to_texture"
    bl_label = "Bake Material to Texture"
    bl_options = {"REGISTER", "UNDO"}

    bake_type: EnumProperty(  # type: ignore[valid-type]
        name="Bake Pass",
        items=_BAKE_TYPE_ITEMS,
        default="DIFFUSE",
    )
    image_size: IntProperty(  # type: ignore[valid-type]
        name="Image Size",
        description="Width and height of the baked texture",
        default=1024,
        min=16,
        max=8192,
    )
    image_name: StringProperty(  # type: ignore[valid-type]
        name="Image Name",
        description="Name for the new image; defaults to <material>_<pass>",
        default="",
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        if obj is None or getattr(obj, "type", "") != "MESH":
            self.report({"ERROR"}, "Active object must be a mesh")
            return {"CANCELLED"}
        slot = obj.active_material
        if slot is None:
            self.report({"ERROR"}, "Active object has no material")
            return {"CANCELLED"}
        if not getattr(slot, "use_nodes", False):
            slot.use_nodes = True
        tree = slot.node_tree
        if tree is None:
            self.report({"ERROR"}, "Material has no node tree")
            return {"CANCELLED"}

        name = self.image_name or f"{slot.name}_{self.bake_type.lower()}"
        image = bpy.data.images.new(
            name=name,
            width=int(self.image_size),
            height=int(self.image_size),
            alpha=True,
        )
        # Insert a TEX_IMAGE node, set it active so bake() targets it.
        node = tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        node.label = name
        for n in tree.nodes:
            n.select = False
        node.select = True
        tree.nodes.active = node

        try:
            bpy.ops.object.bake(type=self.bake_type)
        except RuntimeError as exc:
            self.report({"ERROR"}, f"Bake failed: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Baked {self.bake_type} pass into image {name!r}")
        return {"FINISHED"}


class NIFBLEND_UL_texture_misses(bpy.types.UIList):
    """Read-only list of unresolved textures from the last relink op."""

    bl_idname = "NIFBLEND_UL_texture_misses"

    def draw_item(
        self,
        _context: bpy.types.Context,
        layout: bpy.types.UILayout,
        _data: object,
        item: object,
        _icon: int,
        _active_data: object,
        _active_propname: str,
        _index: int = 0,
    ) -> None:
        row = layout.row(align=True)
        row.label(text=getattr(item, "image_name", "") or "?", icon="IMAGE_DATA")
        row.label(text=getattr(item, "nif_relative", "") or "(no rel path)")


_CLASSES: tuple[type, ...] = (
    NIFBLEND_PG_texture_miss,
    NIFBLEND_OT_relink_textures_against_data_root,
    NIFBLEND_OT_bake_diffuse_to_texture,
    NIFBLEND_UL_texture_misses,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.nifblend_texture_misses = bpy.props.CollectionProperty(  # type: ignore[attr-defined]
        type=NIFBLEND_PG_texture_miss,
    )
    bpy.types.Scene.nifblend_texture_misses_active = bpy.props.IntProperty(  # type: ignore[attr-defined]
        name="Active Texture Miss",
        default=0,
    )


def unregister() -> None:
    with contextlib.suppress(AttributeError):
        del bpy.types.Scene.nifblend_texture_misses_active
    with contextlib.suppress(AttributeError):
        del bpy.types.Scene.nifblend_texture_misses
    for cls in reversed(_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)
