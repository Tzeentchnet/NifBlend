"""Export operator for ``.kf`` keyframe-animation files (Phase 10 step 10f).

Inverse of :class:`nifblend.ops.import_kf.NIFBLEND_OT_import_kf`. Picks
a target armature, harvests one or more :class:`bpy.types.Action`
instances from it, runs each through the
:func:`nifblend.bridge.animation_out.animation_data_from_blender`
encoder, and serialises the resulting block table via
:func:`nifblend.io.block_table.write_nif`. The version triplet
(``version`` / ``user_version`` / ``bs_version``) is resolved either
from the active armature's [`NifBlendObjectProperties`](nifblend/bridge/object_props.py)
``game_profile`` stamp (``AUTO``) or from a fixed preset selectable in
the file dialog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import bpy
from bpy.props import EnumProperty, FloatProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from nifblend.bridge.animation_out import (
    DEFAULT_FPS,
    animation_data_from_blender,
    assemble_kf_block_table,
)
from nifblend.bridge.object_props import read_profile_from_object
from nifblend.format.versions import GameProfile
from nifblend.io.block_table import write_nif

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.bridge.animation_out import AnimationData

__all__ = ["VERSION_PRESETS", "NIFBLEND_OT_export_kf"]


#: ``(version_tuple, user_version, bs_version)`` per preset key.
#: Mirrors the triplets the import-side header decoder lifts from real
#: vanilla files so a round-trip lands on byte-identical headers.
VERSION_PRESETS: dict[str, tuple[tuple[int, int, int, int], int, int]] = {
    "SKYRIM_SE": ((20, 2, 0, 7), 12, 100),
    "SKYRIM_LE": ((20, 2, 0, 7), 12, 83),
    "FALLOUT_4": ((20, 2, 0, 7), 12, 130),
}

#: ``GameProfile`` → preset key when ``version_preset == AUTO``.
_PROFILE_TO_PRESET: dict[GameProfile, str] = {
    GameProfile.SKYRIM_SE: "SKYRIM_SE",
    GameProfile.SKYRIM_LE: "SKYRIM_LE",
    GameProfile.FALLOUT_4: "FALLOUT_4",
}


def _armature_enum_items(_self: object, context: bpy.types.Context) -> list[tuple[str, str, str]]:
    """Populate the target-armature picker with every ARMATURE in the scene."""
    items: list[tuple[str, str, str]] = []
    if context is not None and context.scene is not None:
        for obj in context.scene.objects:
            if getattr(obj, "type", None) == "ARMATURE":
                items.append((obj.name, obj.name, f"Export actions from {obj.name!r}"))
    if not items:
        items.append(("", "<no armature in scene>", "Add an armature first"))
    return items


class NIFBLEND_OT_export_kf(Operator, ExportHelper):
    """Export one or more Blender Actions to a KF (keyframe-animation) file."""

    bl_idname = "nifblend.export_kf"
    bl_label = "Export KF"
    bl_options = {"REGISTER"}

    filename_ext = ".kf"
    filter_glob: StringProperty(default="*.kf", options={"HIDDEN"})  # type: ignore[valid-type]

    target_armature: EnumProperty(  # type: ignore[valid-type]
        name="Target Armature",
        description="Armature object the exported actions are sourced from",
        items=_armature_enum_items,
    )

    actions_mode: EnumProperty(  # type: ignore[valid-type]
        name="Actions",
        description="Which Action(s) to export",
        items=(
            ("ACTIVE", "Active Action", "Export only the armature's currently-assigned action"),
            (
                "ALL_FROM_ARMATURE",
                "All Linked Actions",
                "Export every Action that animates the target armature's pose bones",
            ),
        ),
        default="ACTIVE",
    )

    version_preset: EnumProperty(  # type: ignore[valid-type]
        name="Version Preset",
        description="NIF header triplet (version / user_version / bs_version)",
        items=(
            ("AUTO", "Auto (from armature)", "Use the GameProfile stamped on the target armature"),
            ("SKYRIM_SE", "Skyrim SE", "20.2.0.7 / 12 / 100"),
            ("SKYRIM_LE", "Skyrim LE", "20.2.0.7 / 12 / 83"),
            ("FALLOUT_4", "Fallout 4", "20.2.0.7 / 12 / 130"),
        ),
        default="AUTO",
    )

    fps: FloatProperty(  # type: ignore[valid-type]
        name="FPS",
        description="Frames-per-second used to convert Blender frames to NIF seconds",
        default=DEFAULT_FPS,
        min=1.0,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        target = self._resolve_target(context)
        if target is None:
            self.report(
                {"ERROR"},
                "Select an armature object before exporting a KF file",
            )
            return {"CANCELLED"}

        preset = self._resolve_preset(target)
        if preset is None:
            self.report(
                {"ERROR"},
                f"Unable to pick a KF version preset for {target.name!r}; "
                "stamp a GameProfile on the armature or pick an explicit "
                "preset in the export dialog",
            )
            return {"CANCELLED"}

        actions = self._collect_actions(target)
        if not actions:
            self.report(
                {"ERROR"},
                f"No Actions to export from {target.name!r}",
            )
            return {"CANCELLED"}

        anims: list[tuple[AnimationData, Any]] = []
        warnings: list[str] = []
        pose_bones = getattr(getattr(target, "pose", None), "bones", None)
        for action in actions:
            try:
                anim = animation_data_from_blender(
                    action, fps=float(self.fps), pose_bones=pose_bones
                )
            except Exception as exc:  # surface per-action failure
                warnings.append(f"{getattr(action, 'name', '?')!r}: {exc}")
                continue
            anims.append((anim, pose_bones))

        if not anims:
            self.report({"ERROR"}, "; ".join(warnings) or "All actions failed to encode")
            return {"CANCELLED"}

        version, user_version, bs_version = VERSION_PRESETS[preset]
        table = assemble_kf_block_table(
            anims,
            version=version,
            user_version=user_version,
            bs_version=bs_version,
        )

        try:
            with open(self.filepath, "wb") as fh:
                write_nif(fh, table)
        except OSError as exc:
            self.report({"ERROR"}, f"Failed to write {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        if warnings:
            self.report(
                {"WARNING"},
                f"Exported {len(anims)} action(s) to {self.filepath!r}; "
                f"{len(warnings)} skipped: {warnings}",
            )
        else:
            self.report(
                {"INFO"},
                f"Exported {len(anims)} action(s) to {self.filepath!r}",
            )
        return {"FINISHED"}

    # ---- private helpers ------------------------------------------------

    def _resolve_target(self, context: bpy.types.Context) -> bpy.types.Object | None:
        """Resolve the target armature: explicit pick wins, else active object."""
        scene = context.scene
        if self.target_armature and scene is not None:
            obj = scene.objects.get(self.target_armature)
            if obj is not None and getattr(obj, "type", None) == "ARMATURE":
                return obj
        active = getattr(context, "active_object", None)
        if active is not None and getattr(active, "type", None) == "ARMATURE":
            return active
        return None

    def _resolve_preset(self, target: bpy.types.Object) -> str | None:
        """Return the version preset key, or ``None`` when ``AUTO`` can't pick."""
        if self.version_preset != "AUTO":
            return str(self.version_preset)
        profile = read_profile_from_object(target)
        return _PROFILE_TO_PRESET.get(profile)

    def _collect_actions(self, target: bpy.types.Object) -> list[bpy.types.Action]:
        """Enumerate the actions to export, per :attr:`actions_mode`."""
        anim_data = getattr(target, "animation_data", None)
        active = getattr(anim_data, "action", None) if anim_data is not None else None

        if self.actions_mode == "ACTIVE":
            return [active] if active is not None else []

        # ALL_FROM_ARMATURE: every Action whose first fcurve targets a
        # pose bone present on this armature. Pure-Python walk; the
        # heavy lifting happens later in animation_data_from_blender.
        pose = getattr(target, "pose", None)
        pose_bones = getattr(pose, "bones", None) if pose is not None else None
        if pose_bones is None:
            return [active] if active is not None else []

        bone_names: set[str] = set()
        try:
            for b in pose_bones:
                bone_names.add(b.name)
        except TypeError:
            pass

        out: list[bpy.types.Action] = []
        actions = getattr(getattr(bpy, "data", None), "actions", None)
        if actions is None:
            return [active] if active is not None else []
        for action in actions:
            if _action_targets_armature(action, bone_names):
                out.append(action)
        if active is not None and active not in out:
            out.insert(0, active)
        return out


def _action_targets_armature(action: Any, bone_names: set[str]) -> bool:
    """Return ``True`` if ``action`` has at least one ``pose.bones["X"].*`` fcurve."""
    for fc in getattr(action, "fcurves", ()) or ():
        path = getattr(fc, "data_path", "") or ""
        if not path.startswith('pose.bones["'):
            continue
        # Extract bone name between the first pair of double quotes.
        try:
            start = path.index('"') + 1
            end = path.index('"', start)
        except ValueError:
            continue
        if path[start:end] in bone_names:
            return True
    return False
