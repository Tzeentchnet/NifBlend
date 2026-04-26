"""Import operator for ``.kf`` keyframe-animation files (Phase 5 step 21).

A ``.kf`` is a standalone NIF whose footer roots are
:class:`~nifblend.format.generated.blocks.NiControllerSequence` blocks
(see :mod:`nifblend.io.kf`). This operator reads the file via the
existing :func:`nifblend.io.block_table.read_nif` pipeline, decodes each
root sequence with :func:`controller_sequence_to_animation_data`, and
materialises one ``bpy.types.Action`` per sequence. Actions are
*retargeted* onto a user-chosen armature: the active object is used by
default, the operator surfaces an enum so users can override that pick
in the file dialog. Bones present in the action but missing from the
target armature are reported but do not abort the import (Blender
accepts unresolved fcurve data paths and will start driving them the
moment the bone is added).

The ``rotation_mode`` enum (Phase 5 step 20) toggles between writing
quaternion fcurves verbatim and converting each rotation key to an
intrinsic XYZ Euler triple. When set to ``EULER`` the operator also
sets ``pose.bones[<name>].rotation_mode = 'XYZ'`` on every animated
bone so Blender's pose evaluator picks up the right channel.
"""

from __future__ import annotations

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from nifblend.bridge.animation_in import (
    ROTATION_MODES,
    animation_data_to_blender,
    apply_rotation_mode_to_armature,
    controller_sequence_to_animation_data,
)
from nifblend.bridge.animation_props import (
    apply_controlled_block_to_pose_bone,
    apply_sequence_metadata_to_action,
    apply_text_keys_to_action,
)
from nifblend.io.block_table import read_nif
from nifblend.io.kf import is_kf_file, kf_root_sequences

__all__ = ["NIFBLEND_OT_import_kf"]


def _armature_enum_items(_self: object, context: bpy.types.Context) -> list[tuple[str, str, str]]:
    """Populate the target-armature enum with every ARMATURE object in the scene.

    ``("", "<None found>", ...)`` is returned when the scene has no
    armatures so the dialog renders cleanly; the operator's ``execute``
    treats an empty selection as "no target" and reports an error.
    """
    items: list[tuple[str, str, str]] = []
    if context is not None and context.scene is not None:
        for obj in context.scene.objects:
            if getattr(obj, "type", None) == "ARMATURE":
                items.append((obj.name, obj.name, f"Retarget onto {obj.name!r}"))
    if not items:
        items.append(("", "<no armature in scene>", "Add an armature first"))
    return items


class NIFBLEND_OT_import_kf(Operator, ImportHelper):
    """Import a KF (keyframe-animation) file onto a selected armature."""

    bl_idname = "nifblend.import_kf"
    bl_label = "Import KF"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".kf"
    filter_glob: StringProperty(default="*.kf", options={"HIDDEN"})  # type: ignore[valid-type]

    rotation_mode: EnumProperty(  # type: ignore[valid-type]
        name="Rotation Mode",
        description=(
            "How to write NIF quaternion rotations to Blender fcurves. "
            "QUATERNION is lossless; EULER converts to intrinsic XYZ "
            "Euler (handy for animators, gimbal-locks at +/-90 pitch)."
        ),
        items=tuple((m, m.title(), "") for m in ROTATION_MODES),
        default="QUATERNION",
    )

    target_armature: EnumProperty(  # type: ignore[valid-type]
        name="Target Armature",
        description="Armature object the imported actions are retargeted onto",
        items=_armature_enum_items,
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            with open(self.filepath, "rb") as fh:
                table = read_nif(fh)
        except Exception as exc:  # surface any parse error to the user
            self.report({"ERROR"}, f"Failed to read {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        if not is_kf_file(table):
            self.report(
                {"ERROR"},
                f"{self.filepath!r} is not a KF file (footer root is not a "
                "NiControllerSequence)",
            )
            return {"CANCELLED"}

        target = self._resolve_target(context)
        if target is None:
            self.report(
                {"ERROR"},
                "Select an armature object before importing a KF file",
            )
            return {"CANCELLED"}

        sequences = kf_root_sequences(table)
        roots = list(table.footer.roots)
        created = 0
        unresolved_bones: set[str] = set()

        for raw_idx, _seq in zip(roots, sequences, strict=True):
            anim = controller_sequence_to_animation_data(table, int(raw_idx))
            action = animation_data_to_blender(
                anim, rotation_mode=self.rotation_mode
            )
            apply_rotation_mode_to_armature(
                target, anim, rotation_mode=self.rotation_mode
            )
            self._assign_action(target, action)
            self._stamp_action_metadata(action, anim)
            self._stamp_pose_bone_metadata(target, anim)
            unresolved_bones.update(self._unresolved_bones(target, anim))
            created += 1

        if unresolved_bones:
            self.report(
                {"WARNING"},
                f"Imported {created} action(s); {len(unresolved_bones)} bone "
                f"track(s) not present on {target.name!r}: "
                f"{sorted(unresolved_bones)}",
            )
        else:
            self.report(
                {"INFO"},
                f"Imported {created} action(s) onto {target.name!r}",
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

    def _assign_action(self, armature_obj: bpy.types.Object, action: object) -> None:
        """Assign ``action`` to the armature's animation_data (creating it if needed)."""
        anim_data = armature_obj.animation_data
        if anim_data is None:
            anim_data = armature_obj.animation_data_create()
        anim_data.action = action

    def _unresolved_bones(
        self, armature_obj: bpy.types.Object, anim: object
    ) -> list[str]:
        """Return the names of bones in ``anim`` missing from the armature pose."""
        pose = getattr(armature_obj, "pose", None)
        pose_bones = getattr(pose, "bones", None) if pose is not None else None
        if pose_bones is None:
            return [t.bone_name for t in anim.tracks]  # type: ignore[attr-defined]
        return [
            track.bone_name
            for track in anim.tracks  # type: ignore[attr-defined]
            if pose_bones.get(track.bone_name) is None
        ]

    def _stamp_action_metadata(self, action: object, anim: object) -> None:
        """Stamp NiControllerSequence metadata + text keys onto ``action.nifblend``.

        Step 10d back-fill: gives the Phase 10 export side a faithful
        source for ``weight`` / ``frequency`` / ``cycle_type`` /
        ``start_time`` / ``stop_time`` / ``accum_root_name`` /
        ``accum_flags`` / ``phase`` / ``play_backwards`` plus the
        resolved :class:`NiTextKeyExtraData` rows.
        """
        apply_sequence_metadata_to_action(
            action,
            weight=getattr(anim, "weight", 1.0),
            frequency=getattr(anim, "frequency", 1.0),
            start_time=getattr(anim, "start_time", 0.0),
            stop_time=getattr(anim, "stop_time", 0.0),
            cycle_type=getattr(anim, "cycle_type", 0),
            accum_root_name=getattr(anim, "accum_root_name", ""),
            accum_flags=getattr(anim, "accum_flags", 0),
            phase=getattr(anim, "phase", 0.0),
            play_backwards=getattr(anim, "play_backwards", False),
        )
        text_keys = getattr(anim, "text_keys", None) or []
        if text_keys:
            apply_text_keys_to_action(action, text_keys)

    def _stamp_pose_bone_metadata(
        self, armature_obj: bpy.types.Object, anim: object
    ) -> None:
        """Stamp per-bone :class:`ControlledBlock` metadata onto matching pose bones.

        Step 10d back-fill: pose bones missing from the armature pose are
        skipped silently (the same bones are already reported via
        :meth:`_unresolved_bones`).
        """
        pose = getattr(armature_obj, "pose", None)
        pose_bones = getattr(pose, "bones", None) if pose is not None else None
        if pose_bones is None:
            return
        for track in anim.tracks:  # type: ignore[attr-defined]
            metadata = getattr(track, "metadata", None)
            if metadata is None:
                continue
            bone = pose_bones.get(track.bone_name)
            if bone is None:
                continue
            apply_controlled_block_to_pose_bone(
                bone,
                priority=metadata.priority,
                controller_type=metadata.controller_type,
                controller_id=metadata.controller_id,
                interpolator_id=metadata.interpolator_id,
                property_type=metadata.property_type,
            )
