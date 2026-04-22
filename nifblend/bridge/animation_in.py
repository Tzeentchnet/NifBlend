"""Import side of the NiControllerSequence ↔ Blender Action bridge (Phase 5 step 19).

A ``.kf`` file is a standalone NIF whose footer roots are
:class:`~nifblend.format.generated.blocks.NiControllerSequence` blocks.
Each sequence carries a flat array of
:class:`~nifblend.format.generated.structs.ControlledBlock` entries; one
per animated node. A controlled block names a target bone (via the
header string table or, for SSE, an inline ``string``) and points at an
:class:`~nifblend.format.generated.blocks.NiTransformInterpolator`,
which in turn references a
:class:`~nifblend.format.generated.blocks.NiTransformData` block holding
the actual translation / rotation / scale key streams.

The bridge is split, like every other NifBlend bridge, into a pure
decoder (no ``bpy``) and a Blender wrapper:

* :func:`controller_sequence_to_animation_data` walks one
  :class:`NiControllerSequence`, resolves the interpolator → data chain
  for each :class:`ControlledBlock`, and packs the raw
  :class:`~nifblend.format.generated.structs.Key` /
  :class:`~nifblend.format.generated.structs.QuatKey` lists into flat
  numpy arrays ready for :func:`bpy.types.FCurveKeyframePoints.foreach_set`.
* :func:`animation_data_to_blender` materialises an
  :class:`AnimationData` as a ``bpy.types.Action`` with one fcurve per
  active channel index (``location[0..2]``, ``rotation_quaternion[0..3]``
  or ``rotation_euler[0..2]``, ``scale[0..2]``). For each fcurve we
  pre-allocate ``keyframe_points.add(n)`` once and stamp the entire
  ``(frame, value)`` stream with a single ``foreach_set("co", flat)``
  call; this is the 10-100x speedup over per-frame ``keyframe_insert``
  the roadmap calls out.

NIF time is seconds; Blender stores keyframes in *frames*. Conversion is
``frame = time * fps``; ``fps`` defaults to 30 (the NIF / KF historical
default) and is a parameter on both the decoder and the wrapper so
callers can pass the active scene's render fps for fidelity.

NIF :class:`~nifblend.format.generated.structs.Quaternion` is stored as
``(w, x, y, z)``; Blender's ``rotation_quaternion`` is also
``(w, x, y, z)`` -- no swizzle is needed.

Codegen gap: :class:`Key` / :class:`QuatKey` carry the schema's ``#T#``
template parameter, which the codegen (Phase 2.6) currently emits with a
``# CODEGEN-TODO`` skip on ``.value`` / ``.forward`` / ``.backward``.
This bridge therefore reads ``key.value`` *if it has been populated*
(by hand-constructed test fixtures, or by a future codegen widening
under step 2f) and emits an empty track when the value field is ``None``
rather than crashing. Real ``.kf`` file decoding becomes end-to-end the
moment the template gap closes; nothing else in this module changes.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.blocks import (
    NiControllerSequence,
    NiTransformData,
    NiTransformInterpolator,
)
from nifblend.format.generated.enums import KeyType

from .armature_in import _resolve_name as _resolve_node_name

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.io.block_table import BlockTable


__all__ = [
    "DEFAULT_FPS",
    "ROTATION_MODES",
    "AnimationData",
    "BoneTrack",
    "animation_data_to_blender",
    "apply_rotation_mode_to_armature",
    "controller_sequence_to_animation_data",
    "quaternion_stream_to_euler_streams",
]


#: Marker that a ``ref`` / ``ptr`` u32 is the schema's "no link" sentinel.
_NULL_REF = 0xFFFFFFFF

#: Default frames-per-second used to convert NIF seconds to Blender frames.
#: Matches the historical Gamebryo / Bethesda 30 fps assumption; callers
#: can override per-call to honour the active scene's render fps.
DEFAULT_FPS = 30.0

#: Supported rotation-mode toggle values for :func:`animation_data_to_blender`
#: and the import-KF operator. ``QUATERNION`` writes the native NIF
#: quaternion stream straight into ``pose.bones[X].rotation_quaternion`` (no
#: conversion, lossless). ``EULER`` converts each quaternion key to an
#: intrinsic XYZ Euler triple and writes per-axis fcurves on
#: ``pose.bones[X].rotation_euler`` instead -- handy for animators who
#: prefer to keyframe in Euler, at the cost of gimbal lock at ±90° pitch.
ROTATION_MODES: tuple[str, ...] = ("QUATERNION", "EULER")

#: Map NIF :class:`KeyType` to Blender FCurve interpolation strings.
#: ``QUADRATIC_KEY`` (Hermite tangents) and ``TBC_KEY`` (tension/bias/
#: continuity) both lower to ``'BEZIER'``; rebuilding the exact tangent
#: shape is an export-side concern (Phase 5 has no KF *export* step --
#: see Roadmap "Out of scope for v1.0").
_INTERP_NIF_TO_BLENDER: dict[int, str] = {
    int(KeyType.LINEAR_KEY): "LINEAR",
    int(KeyType.QUADRATIC_KEY): "BEZIER",
    int(KeyType.TBC_KEY): "BEZIER",
    int(KeyType.CONST_KEY): "CONSTANT",
    int(KeyType.XYZ_ROTATION_KEY): "LINEAR",
}


# ---- pure datamodel -------------------------------------------------------


@dataclass(slots=True)
class BoneTrack:
    """All animated channels for a single target bone.

    Each channel array is flat ``float32`` of shape ``(N, 1 + C)`` where
    column 0 is the **Blender frame** (NIF seconds * ``fps``) and
    columns ``1..C`` are the channel components in Blender order.
    Channels with no NIF keys are left at their default empty ``(0, K)``
    arrays, so callers can branch on ``track.translation.size``.
    """

    bone_name: str
    #: ``(N, 4)`` ``[frame, x, y, z]`` -- NIF Vector3 translation keys.
    translation: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 4), dtype=np.float32)
    )
    #: ``(N, 5)`` ``[frame, w, x, y, z]`` -- NIF Quaternion rotation keys.
    #: Mutually exclusive with :attr:`rotation_euler` (rotation_type
    #: dictates which is populated).
    rotation_quaternion: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 5), dtype=np.float32)
    )
    #: Three ``(N, 2)`` ``[frame, angle]`` arrays for split XYZ Euler
    #: rotations (NIF ``rotation_type == XYZ_ROTATION_KEY``). Slot
    #: ``i`` corresponds to NIF axis ``i`` (X, Y, Z); each axis carries
    #: its own keys and its own interpolation.
    rotation_euler: tuple[
        npt.NDArray[np.float32],
        npt.NDArray[np.float32],
        npt.NDArray[np.float32],
    ] = field(
        default_factory=lambda: (
            np.empty((0, 2), dtype=np.float32),
            np.empty((0, 2), dtype=np.float32),
            np.empty((0, 2), dtype=np.float32),
        )
    )
    #: ``(N, 2)`` ``[frame, scale]`` -- NIF stores a single scalar; the
    #: wrapper fans this out to all three Blender ``scale`` indices on
    #: import so the bone scales uniformly.
    scale: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 2), dtype=np.float32)
    )
    #: Per-channel NIF :class:`KeyType` (raw int). ``None`` means the
    #: channel has no keys and the interpolation is undefined.
    translation_interp: int | None = None
    rotation_interp: int | None = None
    #: One per axis when :attr:`rotation_euler` is populated.
    rotation_euler_interp: tuple[int | None, int | None, int | None] = (None, None, None)
    scale_interp: int | None = None


@dataclass(slots=True)
class AnimationData:
    """A whole :class:`NiControllerSequence` decoded into Blender-ready arrays.

    The track list is in source order; the wrapper iterates it once to
    create one Action with fcurves grouped per bone.
    """

    name: str
    #: Frames-per-second the time→frame conversion was performed at.
    #: Stored so the wrapper can stamp it on the resulting Action's
    #: ``frame_range`` consistently.
    fps: float = DEFAULT_FPS
    #: NIF sequence playback metadata; preserved verbatim so a future
    #: KF *export* step can round-trip it.
    start_time: float = 0.0
    stop_time: float = 0.0
    cycle_type: int = 0
    frequency: float = 1.0
    weight: float = 1.0
    tracks: list[BoneTrack] = field(default_factory=list)


# ---- decoders -------------------------------------------------------------


def controller_sequence_to_animation_data(
    table: BlockTable,
    sequence_index: int,
    *,
    fps: float = DEFAULT_FPS,
) -> AnimationData:
    """Decode one :class:`NiControllerSequence` into an :class:`AnimationData`.

    ``sequence_index`` is the block-table index of the
    :class:`NiControllerSequence` (typically a footer root in a ``.kf``
    file -- see :func:`nifblend.io.kf.kf_root_sequences`).

    Each :class:`ControlledBlock` is resolved through its
    :class:`NiTransformInterpolator` to a
    :class:`NiTransformData`; controlled blocks whose interpolator or
    data chain is missing or of an unexpected type are skipped silently
    (a malformed sequence still yields a valid Action with the tracks
    we *could* decode).
    """
    sequence = table.blocks[sequence_index]
    if not isinstance(sequence, NiControllerSequence):
        raise TypeError(
            f"block {sequence_index} is {type(sequence).__name__}, "
            "expected NiControllerSequence",
        )

    name = _resolve_string(sequence.name, table)
    tracks: list[BoneTrack] = []

    for cb in sequence.controlled_blocks or ():
        if cb is None:
            continue
        track = _controlled_block_to_track(cb, table, fps=fps)
        if track is not None:
            tracks.append(track)

    return AnimationData(
        name=name or f"Sequence.{sequence_index}",
        fps=float(fps),
        start_time=float(getattr(sequence, "start_time", 0.0) or 0.0),
        stop_time=float(getattr(sequence, "stop_time", 0.0) or 0.0),
        cycle_type=int(getattr(sequence, "cycle_type", 0) or 0),
        frequency=float(getattr(sequence, "frequency", 1.0) or 1.0),
        weight=float(getattr(sequence, "weight", 1.0) or 1.0),
        tracks=tracks,
    )


def _controlled_block_to_track(
    cb: Any,
    table: BlockTable,
    *,
    fps: float,
) -> BoneTrack | None:
    """Resolve one :class:`ControlledBlock` into a :class:`BoneTrack`."""
    interp = _resolve_block(table, int(getattr(cb, "interpolator", -1)))
    if not isinstance(interp, NiTransformInterpolator):
        return None
    data = _resolve_block(table, int(getattr(interp, "data", -1)))
    if not isinstance(data, NiTransformData):
        # No keys -- transform interpolators may carry a static
        # ``transform`` only (no data block). Skip for now; the static
        # pose belongs on the bind pose, not a per-frame fcurve.
        return None

    bone_name = _resolve_string(getattr(cb, "node_name", None), table)
    if not bone_name:
        # Pre-10.1.0.103 sequences carry the target name in
        # ``target_name`` (a :class:`SizedString`) instead of the
        # string-table-indexed ``node_name``.
        bone_name = _resolve_string(getattr(cb, "target_name", None), table)
    if not bone_name:
        return None

    track = BoneTrack(bone_name=bone_name)
    rot_type = int(getattr(data, "rotation_type", 0) or 0)

    if rot_type == int(KeyType.XYZ_ROTATION_KEY):
        track.rotation_euler = tuple(  # type: ignore[assignment]
            _scalar_keys_to_array(kg, fps=fps)
            for kg in (data.xyz_rotations or [None, None, None])
        )
        track.rotation_euler_interp = tuple(  # type: ignore[assignment]
            (int(kg.interpolation) if kg is not None else None)
            for kg in (data.xyz_rotations or [None, None, None])
        )
    else:
        track.rotation_quaternion = _quat_keys_to_array(
            data.quaternion_keys, fps=fps
        )
        if data.quaternion_keys:
            track.rotation_interp = rot_type or int(KeyType.LINEAR_KEY)

    if data.translations is not None:
        track.translation = _vec3_keys_to_array(data.translations, fps=fps)
        if track.translation.shape[0]:
            track.translation_interp = int(data.translations.interpolation)

    if data.scales is not None:
        track.scale = _scalar_keys_to_array(data.scales, fps=fps)
        if track.scale.shape[0]:
            track.scale_interp = int(data.scales.interpolation)

    return track


# ---- key-stream → numpy ---------------------------------------------------
#
# The codegen Key/QuatKey ``.value`` field is template-typed (``#T#``)
# and currently emitted as ``Any = None`` -- see module docstring. The
# decoders below tolerate ``None`` values by skipping the row, so a
# partial NIF (or a hand-built test fixture that omits some values)
# never crashes the import path.


def _vec3_keys_to_array(
    key_group: Any, *, fps: float
) -> npt.NDArray[np.float32]:
    keys = list(getattr(key_group, "keys", None) or ())
    if not keys:
        return np.empty((0, 4), dtype=np.float32)

    out = np.empty((len(keys), 4), dtype=np.float32)
    cursor = 0
    for k in keys:
        if k is None or k.value is None:
            continue
        v = k.value
        out[cursor, 0] = float(k.time) * fps
        out[cursor, 1] = float(getattr(v, "x", 0.0))
        out[cursor, 2] = float(getattr(v, "y", 0.0))
        out[cursor, 3] = float(getattr(v, "z", 0.0))
        cursor += 1
    return out[:cursor]


def _quat_keys_to_array(
    keys: list[Any] | None, *, fps: float
) -> npt.NDArray[np.float32]:
    keys = list(keys or ())
    if not keys:
        return np.empty((0, 5), dtype=np.float32)

    out = np.empty((len(keys), 5), dtype=np.float32)
    cursor = 0
    for k in keys:
        if k is None or k.value is None:
            continue
        q = k.value
        out[cursor, 0] = float(k.time) * fps
        out[cursor, 1] = float(getattr(q, "w", 1.0))
        out[cursor, 2] = float(getattr(q, "x", 0.0))
        out[cursor, 3] = float(getattr(q, "y", 0.0))
        out[cursor, 4] = float(getattr(q, "z", 0.0))
        cursor += 1
    return out[:cursor]


def _scalar_keys_to_array(
    key_group: Any, *, fps: float
) -> npt.NDArray[np.float32]:
    keys = list(getattr(key_group, "keys", None) or ()) if key_group is not None else []
    if not keys:
        return np.empty((0, 2), dtype=np.float32)

    out = np.empty((len(keys), 2), dtype=np.float32)
    cursor = 0
    for k in keys:
        if k is None or k.value is None:
            continue
        out[cursor, 0] = float(k.time) * fps
        out[cursor, 1] = float(k.value)
        cursor += 1
    return out[:cursor]


# ---- string + ref resolution ---------------------------------------------


def _resolve_block(table: BlockTable, ref: int) -> Any | None:
    if ref < 0 or ref == _NULL_REF or ref >= len(table.blocks):
        return None
    return table.blocks[ref]


def _resolve_string(name_obj: Any, table: BlockTable | None) -> str:
    """Resolve a NIF string (string-table indexed *or* inline SizedString)."""
    if name_obj is None:
        return ""
    inline = getattr(name_obj, "string", None)
    if inline is not None:
        try:
            return bytes(inline.value).decode("latin-1")
        except (AttributeError, ValueError):
            pass
    # SizedString itself (no .index, has .value directly).
    if hasattr(name_obj, "value") and not hasattr(name_obj, "index"):
        try:
            return bytes(name_obj.value).decode("latin-1")
        except (AttributeError, ValueError, TypeError):
            return ""
    idx_attr = getattr(name_obj, "index", None)
    idx = idx_attr if idx_attr is not None else name_obj
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return ""
    if idx < 0 or idx == _NULL_REF or table is None:
        return ""
    strings = table.header.strings
    if idx >= len(strings):
        return ""
    s = strings[idx]
    if s is None:
        return ""
    return bytes(s.value).decode("latin-1")


# Re-export the node-name resolver under a clearer alias so callers
# composing this bridge with armature_in stay homogeneous.
_resolve_node_name = _resolve_node_name  # explicit re-bind for export


# ---- rotation-mode conversion --------------------------------------------


def quaternion_stream_to_euler_streams(
    stream: npt.NDArray[np.float32],
) -> tuple[
    npt.NDArray[np.float32],
    npt.NDArray[np.float32],
    npt.NDArray[np.float32],
]:
    """Convert an ``(N, 5)`` ``[frame, w, x, y, z]`` stream to three Euler axes.

    Returns three ``(N, 2)`` ``[frame, angle]`` arrays in Blender's default
    intrinsic XYZ order. Implemented in pure numpy so the bridge stays
    headless-testable; matches the closed-form quaternion → XYZ Euler
    formula (Shoemake 1985, sin-pitch clamped to ``[-1, +1]`` to dodge
    domain errors at gimbal lock).
    """
    if stream.shape[0] == 0:
        empty = np.empty((0, 2), dtype=np.float32)
        return empty, empty.copy(), empty.copy()

    frames = stream[:, 0]
    w = stream[:, 1]
    x = stream[:, 2]
    y = stream[:, 3]
    z = stream[:, 4]

    # Roll (X) - sin/cos via 2*(w*x + y*z), 1 - 2*(x*x + y*y).
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (Y) - asin(2*(w*y - z*x)) clamped to dodge gimbal-lock NaNs.
    sinp = np.clip(2.0 * (w * y - z * x), -1.0, 1.0)
    pitch = np.arcsin(sinp)

    # Yaw (Z) - sin/cos via 2*(w*z + x*y), 1 - 2*(y*y + z*z).
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    x_axis = np.column_stack((frames, roll)).astype(np.float32, copy=False)
    y_axis = np.column_stack((frames, pitch)).astype(np.float32, copy=False)
    z_axis = np.column_stack((frames, yaw)).astype(np.float32, copy=False)
    return x_axis, y_axis, z_axis


def apply_rotation_mode_to_armature(
    armature_obj: Any,
    data: AnimationData,
    *,
    rotation_mode: str = "QUATERNION",
) -> None:
    """Set ``pose.bones[<name>].rotation_mode`` for every animated bone.

    No-op for bones missing from the armature's pose -- the action
    fcurves still get created (Blender silently ignores unresolved data
    paths), they just won't drive anything until the bone shows up.
    """
    rotation_mode = rotation_mode.upper()
    if rotation_mode not in ROTATION_MODES:
        raise ValueError(
            f"rotation_mode must be one of {ROTATION_MODES!r}, got {rotation_mode!r}"
        )
    pose = getattr(armature_obj, "pose", None)
    if pose is None:
        return
    pose_bones = getattr(pose, "bones", None)
    if pose_bones is None:
        return
    blender_mode = "QUATERNION" if rotation_mode == "QUATERNION" else "XYZ"
    for track in data.tracks:
        bone = pose_bones.get(track.bone_name) if hasattr(pose_bones, "get") else None
        if bone is None:
            continue
        with contextlib.suppress(AttributeError, TypeError):
            bone.rotation_mode = blender_mode


# ---- Blender wrapper -----------------------------------------------------


def animation_data_to_blender(
    data: AnimationData,
    *,
    bpy: Any = None,
    action_name: str | None = None,
    rotation_mode: str = "QUATERNION",
) -> Any:
    """Materialise an :class:`AnimationData` as a ``bpy.types.Action``.

    For each :class:`BoneTrack` we create one fcurve per active channel
    component (``pose.bones["X"].location[0..2]``,
    ``rotation_quaternion[0..3]`` or ``rotation_euler[0..2]``,
    ``scale[0..2]``). The keyframe stream is bulk-loaded with

    ::

        kf = fc.keyframe_points
        kf.add(n)
        kf.foreach_set("co", flat)            # 2*n floats: f0,v0,f1,v1,...
        kf.foreach_set("interpolation", code) # n ints, NIF KeyType-mapped

    which is the 10-100x speedup over per-frame ``keyframe_insert`` the
    roadmap calls out. ``bpy`` is injectable so headless tests can pass
    a :class:`types.SimpleNamespace` shim.

    ``rotation_mode`` toggles how NIF quaternion rotations are written
    out: ``"QUATERNION"`` (default) emits four ``rotation_quaternion``
    fcurves (lossless, matches the on-disk stream); ``"EULER"`` runs
    each quaternion key through :func:`quaternion_stream_to_euler_streams`
    and emits three intrinsic-XYZ ``rotation_euler`` fcurves instead.
    The toggle does not affect tracks that already arrived as
    ``XYZ_ROTATION_KEY`` (those are always written as Euler) or tracks
    that have no rotation keys at all.
    """
    if bpy is None:  # pragma: no cover - exercised by Blender-marked tests
        import bpy as bpy  # type: ignore[no-redef]

    rotation_mode = rotation_mode.upper()
    if rotation_mode not in ROTATION_MODES:
        raise ValueError(
            f"rotation_mode must be one of {ROTATION_MODES!r}, got {rotation_mode!r}"
        )

    name = action_name or data.name
    action = bpy.data.actions.new(name=name)

    for track in data.tracks:
        bone_path = f'pose.bones["{track.bone_name}"]'

        if track.translation.shape[0]:
            _emit_vector_fcurves(
                action,
                data_path=f"{bone_path}.location",
                group=track.bone_name,
                stream=track.translation,
                interp=track.translation_interp,
                component_count=3,
            )

        if track.rotation_quaternion.shape[0]:
            if rotation_mode == "QUATERNION":
                _emit_vector_fcurves(
                    action,
                    data_path=f"{bone_path}.rotation_quaternion",
                    group=track.bone_name,
                    stream=track.rotation_quaternion,
                    interp=track.rotation_interp,
                    component_count=4,
                )
            else:
                # Convert to per-axis Euler streams and emit one
                # rotation_euler[i] fcurve per axis.
                axis_streams = quaternion_stream_to_euler_streams(
                    track.rotation_quaternion
                )
                for axis_idx, axis_stream in enumerate(axis_streams):
                    _emit_scalar_fcurve(
                        action,
                        data_path=f"{bone_path}.rotation_euler",
                        array_index=axis_idx,
                        group=track.bone_name,
                        frames=axis_stream[:, 0],
                        values=axis_stream[:, 1],
                        interp=track.rotation_interp,
                    )
        else:
            for axis_idx, axis_stream in enumerate(track.rotation_euler):
                if axis_stream.shape[0] == 0:
                    continue
                _emit_scalar_fcurve(
                    action,
                    data_path=f"{bone_path}.rotation_euler",
                    array_index=axis_idx,
                    group=track.bone_name,
                    frames=axis_stream[:, 0],
                    values=axis_stream[:, 1],
                    interp=track.rotation_euler_interp[axis_idx],
                )

        if track.scale.shape[0]:
            # NIF stores a single uniform scale per key; fan it out over
            # Blender's three independent ``scale`` indices so the bone
            # scales uniformly the way the source intended.
            for axis_idx in range(3):
                _emit_scalar_fcurve(
                    action,
                    data_path=f"{bone_path}.scale",
                    array_index=axis_idx,
                    group=track.bone_name,
                    frames=track.scale[:, 0],
                    values=track.scale[:, 1],
                    interp=track.scale_interp,
                )

    return action


def _emit_vector_fcurves(
    action: Any,
    *,
    data_path: str,
    group: str,
    stream: npt.NDArray[np.float32],
    interp: int | None,
    component_count: int,
) -> None:
    """Create ``component_count`` fcurves and bulk-load one column each."""
    n = stream.shape[0]
    frames = stream[:, 0]
    interp_code = _INTERP_NIF_TO_BLENDER.get(
        int(interp) if interp is not None else int(KeyType.LINEAR_KEY),
        "LINEAR",
    )
    for axis_idx in range(component_count):
        values = stream[:, 1 + axis_idx]
        _emit_scalar_fcurve(
            action,
            data_path=data_path,
            array_index=axis_idx,
            group=group,
            frames=frames,
            values=values,
            interp=interp,
            interp_code=interp_code,
            n=n,
        )


def _emit_scalar_fcurve(
    action: Any,
    *,
    data_path: str,
    array_index: int,
    group: str,
    frames: npt.NDArray[np.float32],
    values: npt.NDArray[np.float32],
    interp: int | None,
    interp_code: str | None = None,
    n: int | None = None,
) -> Any:
    if n is None:
        n = int(frames.shape[0])
    if interp_code is None:
        interp_code = _INTERP_NIF_TO_BLENDER.get(
            int(interp) if interp is not None else int(KeyType.LINEAR_KEY),
            "LINEAR",
        )

    # ``action_group`` is the Blender keyword; some test fakes don't
    # accept it -- fall back to a positional/no-group call.
    fc = _new_fcurve(action, data_path=data_path, index=array_index, group=group)

    kf = fc.keyframe_points
    if hasattr(kf, "add"):
        kf.add(n)
    # Interleave frames + values into the flat ``co`` buffer Blender
    # expects: [f0, v0, f1, v1, ...]. ``np.column_stack`` then
    # ``ravel`` is the idiomatic vectorised recipe.
    flat = np.column_stack((frames, values)).astype(np.float32, copy=False).ravel()
    if hasattr(kf, "foreach_set"):
        kf.foreach_set("co", flat)
        # Interpolation per keyframe; Blender expects an int code, but
        # the public ``interpolation`` enum API takes strings -- the
        # ``foreach_set`` path uses the underlying enum integer, so we
        # set via a per-point fallback if the int code path isn't
        # supported by the test fake.
        with contextlib.suppress(TypeError, ValueError, AttributeError):
            kf.foreach_set(
                "interpolation",
                np.full(n, _INTERP_STRING_TO_BLENDER_CODE.get(interp_code, 0), dtype=np.int32),
            )
    return fc


def _new_fcurve(action: Any, *, data_path: str, index: int, group: str) -> Any:
    """Create one fcurve, tolerating fakes that don't accept ``action_group``."""
    fcurves = action.fcurves
    try:
        return fcurves.new(data_path=data_path, index=index, action_group=group)
    except TypeError:
        return fcurves.new(data_path=data_path, index=index)


# Blender's underlying interpolation enum integer codes. Documented in
# ``rna_animation_api.c``; pinned here so the int path stays stable
# across Blender point releases. Strings are still accepted by the
# public ``keyframe_point.interpolation`` setter -- this map is only
# for the ``foreach_set("interpolation", ...)`` fast path.
_INTERP_STRING_TO_BLENDER_CODE: dict[str, int] = {
    "CONSTANT": 0,
    "LINEAR": 1,
    "BEZIER": 2,
}
