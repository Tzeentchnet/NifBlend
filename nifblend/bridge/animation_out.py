"""Export side of the NiControllerSequence ↔ Blender Action bridge (Phase 10 step 10e).

Inverse of :mod:`nifblend.bridge.animation_in`. The encoder is split,
like every other NifBlend bridge, into a pure layer (no ``bpy`` import
outside helper signatures) and an orchestrator:

* :func:`animation_data_from_blender` walks a Blender ``Action``,
  groups its ``pose.bones["X"].(location|rotation_quaternion|
  rotation_euler|scale)`` fcurves by bone, bulk-extracts the
  ``keyframe_points.co`` buffers via numpy ``foreach_get`` (mirror of
  the import-side ``foreach_set`` fast path), and reassembles the
  per-channel ``(N, K)`` arrays the
  :class:`~nifblend.bridge.animation_in.BoneTrack` decoder produced.
  Sequence-level metadata is read from the
  :attr:`bpy.types.Action.nifblend` PointerProperty (the Phase 10c
  storage layer); falls back to the Action's ``frame_range`` for
  ``stop_time`` when the PropertyGroup is unset.
* :func:`bone_track_to_ni_transform_data` builds one
  :class:`~nifblend.format.generated.blocks.NiTransformData` per
  animated bone. Routes through ``KeyGroup<Vector3>`` for translation,
  ``QuatKey<Quaternion>`` list for quaternion rotation (or three
  ``KeyGroup<float>`` for ``XYZ_ROTATION_KEY`` Euler streams), and
  ``KeyGroup<float>`` for uniform scale.
* :func:`bone_track_to_ni_transform_interpolator` emits an identity
  static-transform :class:`NiQuatTransform` plus the data ref.
* :func:`bone_track_to_controlled_block` emits the SSE-shaped
  (v20.2.0.7) :class:`ControlledBlock` variant with direct string-table
  refs; per-bone metadata sourced from
  :attr:`~nifblend.bridge.animation_in.BoneTrack.metadata` (populated
  in step 10d).
* :func:`animation_data_to_controller_sequence` packs the scalar
  sequence metadata.
* :func:`build_text_key_extra_data` synthesises
  :class:`NiTextKeyExtraData` from the Action PropertyGroup's text-key
  collection.
* :func:`assemble_kf_block_table` orchestrates the whole shebang:
  allocates one string-table entry per unique string across the entire
  table, lays blocks out in canonical KF order
  (``NiTextKeyExtraData[]`` first, then for each sequence:
  ``NiTransformData[]`` → ``NiTransformInterpolator[]`` →
  ``NiControllerSequence``), sets footer roots to the sequence indices,
  returns a ready-for-:func:`nifblend.io.block_table.write_nif`
  :class:`BlockTable`.

NIF time is seconds; Blender stores keyframes in *frames*.  Inverse of
the import: ``time = frame / fps``; ``fps`` defaults to 30.

NIF :class:`Quaternion` is stored as ``(w, x, y, z)`` — Blender's
``rotation_quaternion`` matches; no swizzle.

Non-uniform animated scale: NIF carries one scalar per scale key.  When
all three Blender ``scale`` fcurves are within ``1e-6`` of each other
they collapse to that single channel; otherwise channel 0 is taken and
:func:`logging.getLogger` warns once per bone (the contract documented
in the Phase 10 roadmap).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from nifblend.bridge.animation_in import (
    DEFAULT_FPS,
    AnimationData,
    BoneTrack,
    BoneTrackMetadata,
)
from nifblend.bridge.animation_props import (
    read_controlled_block_from_pose_bone,
    read_sequence_metadata_from_action,
    read_text_keys_from_action,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import (
    NiControllerSequence,
    NiTextKeyExtraData,
    NiTransformData,
    NiTransformInterpolator,
)
from nifblend.format.generated.enums import CycleType, KeyType
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ControlledBlock,
    ExportString,
    Footer,
    Header,
    Key,
    KeyGroup,
    NiQuatTransform,
    Quaternion,
    QuatKey,
    SizedString,
    Vector3,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

__all__ = [
    "DEFAULT_FPS",
    "DEFAULT_VERSION",
    "NULL_REF",
    "animation_data_from_blender",
    "animation_data_to_controller_sequence",
    "assemble_kf_block_table",
    "bone_track_to_controlled_block",
    "bone_track_to_ni_transform_data",
    "bone_track_to_ni_transform_interpolator",
    "build_text_key_extra_data",
]


_LOG = logging.getLogger(__name__)

#: Sentinel u32 for "no link" used by NIF ref/ptr fields.
NULL_REF: int = -1

#: Default header triplet — Skyrim SE / FO4 family. Caller can override.
DEFAULT_VERSION: tuple[int, int, int, int] = (20, 2, 0, 7)
DEFAULT_USER_VERSION: int = 12
DEFAULT_BS_VERSION: int = 100

#: Tolerance for collapsing per-axis Blender scale fcurves into a NIF
#: uniform scalar. Phase 10 contract.
_UNIFORM_SCALE_ATOL: float = 1e-6

#: Regex extracting the bone name from a pose-bone fcurve data path:
#: ``pose.bones["Bone Name"].(location|rotation_quaternion|...)``.
_BONE_PATH_RE = re.compile(r'^pose\.bones\["(?P<name>[^"]+)"\]\.(?P<attr>\w+)$')

#: Recognised pose-bone channel attributes.
_TRANSLATION = "location"
_ROTATION_QUAT = "rotation_quaternion"
_ROTATION_EULER = "rotation_euler"
_SCALE = "scale"


# ---- Blender Action → AnimationData --------------------------------------


@dataclass(slots=True)
class _ChannelStream:
    """Working bucket for one (bone, channel) pair during fcurve grouping."""

    # fcurve per array_index (None when that index is missing).
    by_index: dict[int, Any] = field(default_factory=dict)


def animation_data_from_blender(
    action: Any,
    *,
    fps: float = DEFAULT_FPS,
    pose_bones: Any = None,
) -> AnimationData:
    """Walk ``action.fcurves`` and reconstruct an :class:`AnimationData`.

    ``pose_bones`` is an optional ``armature.pose.bones`` mapping (or
    ``SimpleNamespace`` fake) used to harvest per-bone
    :class:`ControlledBlock` metadata stamped onto
    ``pose_bone.nifblend`` by step 10d. When omitted, every track gets
    a default-shaped :class:`BoneTrackMetadata`.

    Returned :class:`BoneTrack` arrays carry **Blender frames** in
    column 0 (matching the import-side convention); the
    seconds-conversion is deferred to
    :func:`bone_track_to_ni_transform_data` so the same datamodel
    survives a round-trip without doubly-scaling time.
    """
    metadata = read_sequence_metadata_from_action(action)
    text_keys = read_text_keys_from_action(action)

    # Group fcurves by (bone_name, attr, array_index).
    grouped: dict[str, dict[str, _ChannelStream]] = {}
    for fc in getattr(action, "fcurves", ()) or ():
        match = _BONE_PATH_RE.match(getattr(fc, "data_path", "") or "")
        if match is None:
            continue
        attr = match.group("attr")
        if attr not in {_TRANSLATION, _ROTATION_QUAT, _ROTATION_EULER, _SCALE}:
            continue
        bone_name = match.group("name")
        bucket = grouped.setdefault(bone_name, {})
        stream = bucket.setdefault(attr, _ChannelStream())
        stream.by_index[int(getattr(fc, "array_index", 0))] = fc

    tracks: list[BoneTrack] = []
    for bone_name in sorted(grouped):
        track = _bone_track_from_streams(bone_name, grouped[bone_name])
        track.metadata = _read_bone_metadata(pose_bones, bone_name)
        tracks.append(track)

    inv_fps = 1.0 / float(fps)
    if metadata is not None:
        accum_root_name = metadata["accum_root_name"]
        accum_flags = metadata["accum_flags"]
        weight = metadata["weight"]
        frequency = metadata["frequency"]
        cycle_type = metadata["cycle_type"]
        phase = metadata["phase"]
        play_backwards = metadata["play_backwards"]
        start_time = metadata["start_time"]
        stop_time = metadata["stop_time"]
        # ``stop_time == start_time == 0`` is the unset PropertyGroup
        # default. Fall back to the Action's frame_range so brand-new
        # in-Blender Actions get a sensible NIF window.
        if start_time == 0.0 and stop_time == 0.0:
            start_time, stop_time = _action_time_range(action, inv_fps=inv_fps)
    else:
        weight = 1.0
        frequency = 1.0
        cycle_type = int(CycleType.CYCLE_CLAMP)
        accum_root_name = ""
        accum_flags = 0
        phase = 0.0
        play_backwards = False
        start_time, stop_time = _action_time_range(action, inv_fps=inv_fps)

    return AnimationData(
        name=str(getattr(action, "name", "") or ""),
        fps=float(fps),
        start_time=float(start_time),
        stop_time=float(stop_time),
        cycle_type=int(cycle_type),
        frequency=float(frequency),
        weight=float(weight),
        accum_root_name=str(accum_root_name),
        accum_flags=int(accum_flags) & 0xFFFFFFFF,
        phase=float(phase),
        play_backwards=bool(play_backwards),
        text_keys=list(text_keys),
        tracks=tracks,
    )


def _bone_track_from_streams(
    bone_name: str, channels: dict[str, _ChannelStream]
) -> BoneTrack:
    track = BoneTrack(bone_name=bone_name)

    if _TRANSLATION in channels:
        stream, interp = _stack_vector_channel(
            channels[_TRANSLATION], component_count=3
        )
        if stream.shape[0]:
            track.translation = stream
            track.translation_interp = interp

    if _ROTATION_QUAT in channels:
        stream, interp = _stack_vector_channel(
            channels[_ROTATION_QUAT], component_count=4
        )
        if stream.shape[0]:
            track.rotation_quaternion = stream
            track.rotation_interp = interp
    elif _ROTATION_EULER in channels:
        axes: list[npt.NDArray[np.float32]] = []
        interps: list[int | None] = []
        for axis_idx in range(3):
            fc = channels[_ROTATION_EULER].by_index.get(axis_idx)
            if fc is None:
                axes.append(np.empty((0, 2), dtype=np.float32))
                interps.append(None)
                continue
            arr, interp = _scalar_fcurve_to_array(fc)
            axes.append(arr)
            interps.append(interp)
        track.rotation_euler = (axes[0], axes[1], axes[2])
        track.rotation_euler_interp = (interps[0], interps[1], interps[2])

    if _SCALE in channels:
        scale, interp = _scale_channel_to_uniform(
            channels[_SCALE], bone_name=bone_name
        )
        if scale.shape[0]:
            track.scale = scale
            track.scale_interp = interp

    return track


def _stack_vector_channel(
    channel: _ChannelStream, *, component_count: int
) -> tuple[npt.NDArray[np.float32], int | None]:
    """Combine ``component_count`` per-axis fcurves into ``(N, 1+component_count)``.

    Frames are taken from axis 0; any axis missing a key for an axis-0
    frame contributes ``0.0``.  The shared interpolation is taken from
    the first present axis (NIF stores one ``interpolation`` per
    KeyGroup; per-component variation isn't representable).
    """
    axis_streams: dict[int, tuple[npt.NDArray[np.float32], int | None]] = {}
    for idx in range(component_count):
        fc = channel.by_index.get(idx)
        if fc is None:
            continue
        axis_streams[idx] = _scalar_fcurve_to_array(fc)

    if not axis_streams:
        return np.empty((0, 1 + component_count), dtype=np.float32), None

    base_idx = min(axis_streams)
    base_frames = axis_streams[base_idx][0][:, 0]
    n = base_frames.shape[0]
    out = np.zeros((n, 1 + component_count), dtype=np.float32)
    out[:, 0] = base_frames
    interp: int | None = axis_streams[base_idx][1]
    for i in range(component_count):
        stream = axis_streams.get(i)
        if stream is None:
            continue
        arr, _ = stream
        if arr.shape[0] == n:
            out[:, 1 + i] = arr[:, 1]
        else:
            # Different keyframe count on this axis; sample at base
            # frames via numpy.interp (NIF can only carry one
            # consolidated keyset per channel).
            out[:, 1 + i] = np.interp(
                base_frames, arr[:, 0], arr[:, 1]
            ).astype(np.float32, copy=False)
    return out, interp


def _scalar_fcurve_to_array(
    fc: Any,
) -> tuple[npt.NDArray[np.float32], int | None]:
    """Bulk-extract one fcurve's keyframe stream as ``(N, 2)`` ``[frame, value]``.

    Column 0 is the **Blender frame** (matches
    :class:`BoneTrack`'s import-side convention); the seconds
    conversion is deferred to NIF emission.
    """
    kf = getattr(fc, "keyframe_points", None)
    n = len(kf) if kf is not None else 0
    out = np.zeros((n, 2), dtype=np.float32)
    interp: int | None = None
    if n:
        flat = np.zeros(2 * n, dtype=np.float32)
        if hasattr(kf, "foreach_get"):
            kf.foreach_get("co", flat)
        else:
            for i, point in enumerate(kf):
                co = getattr(point, "co", (0.0, 0.0))
                flat[2 * i] = float(co[0])
                flat[2 * i + 1] = float(co[1])
        out = flat.reshape(n, 2)
        # Pick interpolation from the first keyframe (NIF carries one
        # per KeyGroup; per-keyframe variation isn't representable).
        try:
            first = next(iter(kf))
            interp_str = str(getattr(first, "interpolation", "LINEAR") or "LINEAR")
            interp = _BLENDER_TO_NIF_INTERP.get(
                interp_str.upper(), int(KeyType.LINEAR_KEY)
            )
        except (StopIteration, AttributeError, TypeError):
            interp = int(KeyType.LINEAR_KEY)
    return out, interp


def _scale_channel_to_uniform(
    channel: _ChannelStream, *, bone_name: str
) -> tuple[npt.NDArray[np.float32], int | None]:
    """Collapse the three Blender scale fcurves to NIF's single uniform scalar.

    Channel 0 is taken when axes diverge beyond
    :data:`_UNIFORM_SCALE_ATOL`; the divergence is logged once.
    """
    axis_arrays: dict[int, npt.NDArray[np.float32]] = {}
    interp: int | None = None
    for axis_idx in range(3):
        fc = channel.by_index.get(axis_idx)
        if fc is None:
            continue
        arr, ax_interp = _scalar_fcurve_to_array(fc)
        axis_arrays[axis_idx] = arr
        if interp is None:
            interp = ax_interp

    if not axis_arrays:
        return np.empty((0, 2), dtype=np.float32), None

    base_idx = min(axis_arrays)
    base = axis_arrays[base_idx]
    diverged = False
    for idx, arr in axis_arrays.items():
        if idx == base_idx:
            continue
        if arr.shape != base.shape or not np.allclose(
            arr[:, 1], base[:, 1], atol=_UNIFORM_SCALE_ATOL
        ):
            diverged = True
            break
    if diverged:
        _LOG.warning(
            "non-uniform animated scale on bone %r; NIF only carries a "
            "single scale scalar per key — taking axis 0",
            bone_name,
        )
    return base, interp


def _action_time_range(action: Any, *, inv_fps: float) -> tuple[float, float]:
    """Fallback ``(start_time, stop_time)`` from the Action's ``frame_range``.

    Returns ``(0.0, 0.0)`` when the Action exposes no usable range.
    """
    fr = getattr(action, "frame_range", None)
    if fr is None:
        return 0.0, 0.0
    try:
        start, stop = float(fr[0]), float(fr[1])
    except (TypeError, ValueError, IndexError):
        return 0.0, 0.0
    return start * inv_fps, stop * inv_fps


def _read_bone_metadata(pose_bones: Any, bone_name: str) -> BoneTrackMetadata:
    """Pull :class:`BoneTrackMetadata` off ``pose_bones[bone_name].nifblend``."""
    if pose_bones is None:
        return BoneTrackMetadata()
    bone = None
    if hasattr(pose_bones, "get"):
        bone = pose_bones.get(bone_name)
    if bone is None:
        return BoneTrackMetadata()
    raw = read_controlled_block_from_pose_bone(bone)
    if raw is None:
        return BoneTrackMetadata()
    return BoneTrackMetadata(
        priority=int(raw["priority"]),
        controller_type=str(raw["controller_type"]),
        controller_id=str(raw["controller_id"]),
        interpolator_id=str(raw["interpolator_id"]),
        property_type=str(raw["property_type"]),
    )


# ---- per-block builders --------------------------------------------------


_BLENDER_TO_NIF_INTERP: dict[str, int] = {
    "CONSTANT": int(KeyType.CONST_KEY),
    "LINEAR": int(KeyType.LINEAR_KEY),
    "BEZIER": int(KeyType.QUADRATIC_KEY),
}


def bone_track_to_ni_transform_data(
    track: BoneTrack, *, fps: float = DEFAULT_FPS
) -> NiTransformData:
    """Build one :class:`NiTransformData` carrying ``track``'s key streams.

    ``fps`` divides the ``BoneTrack`` column-0 frames into NIF seconds.
    """
    inv_fps = 1.0 / float(fps)
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.LINEAR_KEY),
        quaternion_keys=[],
        xyz_rotations=[],
        translations=KeyGroup(num_keys=0, interpolation=0, keys=[]),
        scales=KeyGroup(num_keys=0, interpolation=0, keys=[]),
    )

    # Translation
    trans = track.translation
    if trans.shape[0]:
        keys = [
            Key(
                time=float(trans[i, 0]) * inv_fps,
                value=Vector3(
                    x=float(trans[i, 1]),
                    y=float(trans[i, 2]),
                    z=float(trans[i, 3]),
                ),
            )
            for i in range(trans.shape[0])
        ]
        data.translations = KeyGroup(
            num_keys=len(keys),
            interpolation=int(track.translation_interp or int(KeyType.LINEAR_KEY)),
            keys=keys,
        )

    # Rotation
    if track.rotation_quaternion.shape[0]:
        rot = track.rotation_quaternion
        rot_interp = int(track.rotation_interp or int(KeyType.LINEAR_KEY))
        data.num_rotation_keys = rot.shape[0]
        data.rotation_type = rot_interp
        data.quaternion_keys = [
            QuatKey(
                time=float(rot[i, 0]) * inv_fps,
                value=Quaternion(
                    w=float(rot[i, 1]),
                    x=float(rot[i, 2]),
                    y=float(rot[i, 3]),
                    z=float(rot[i, 4]),
                ),
            )
            for i in range(rot.shape[0])
        ]
    elif any(axis.shape[0] for axis in track.rotation_euler):
        data.num_rotation_keys = max(
            axis.shape[0] for axis in track.rotation_euler
        )
        data.rotation_type = int(KeyType.XYZ_ROTATION_KEY)
        xyz: list[KeyGroup | None] = []
        for axis_idx, axis in enumerate(track.rotation_euler):
            keys = [
                Key(
                    time=float(axis[i, 0]) * inv_fps,
                    value=float(axis[i, 1]),
                )
                for i in range(axis.shape[0])
            ]
            interp = (
                track.rotation_euler_interp[axis_idx]
                if track.rotation_euler_interp[axis_idx] is not None
                else int(KeyType.LINEAR_KEY)
            )
            xyz.append(
                KeyGroup(num_keys=len(keys), interpolation=int(interp), keys=keys)
            )
        data.xyz_rotations = xyz

    # Scale
    if track.scale.shape[0]:
        scale = track.scale
        keys = [
            Key(
                time=float(scale[i, 0]) * inv_fps,
                value=float(scale[i, 1]),
            )
            for i in range(scale.shape[0])
        ]
        data.scales = KeyGroup(
            num_keys=len(keys),
            interpolation=int(track.scale_interp or int(KeyType.LINEAR_KEY)),
            keys=keys,
        )

    return data


def bone_track_to_ni_transform_interpolator(
    track: BoneTrack, *, data_ref: int
) -> NiTransformInterpolator:
    """Identity-static-transform :class:`NiTransformInterpolator`.

    When ``track`` has zero keys on every channel the FO4 idle-pose
    pattern applies: ``data=-1`` and the static :class:`NiQuatTransform`
    holds the bind-pose transform. We can't recover the bind pose from
    a :class:`BoneTrack` alone (callers wire that through), so emit an
    identity transform — the operator layer can override before write.
    """
    has_keys = (
        track.translation.shape[0]
        or track.rotation_quaternion.shape[0]
        or any(axis.shape[0] for axis in track.rotation_euler)
        or track.scale.shape[0]
    )
    return NiTransformInterpolator(
        transform=NiQuatTransform(
            translation=Vector3(x=0.0, y=0.0, z=0.0),
            rotation=Quaternion(w=1.0, x=0.0, y=0.0, z=0.0),
            scale=1.0,
            trs_valid=[],
        ),
        data=int(data_ref) if has_keys else NULL_REF,
    )


def bone_track_to_controlled_block(
    track: BoneTrack,
    *,
    interpolator_ref: int,
    name_index: int,
    controller_type_index: int = 0xFFFFFFFF,
    controller_id_index: int = 0xFFFFFFFF,
    interpolator_id_index: int = 0xFFFFFFFF,
    property_type_index: int = 0xFFFFFFFF,
) -> ControlledBlock:
    """Emit the SSE-shaped (v20.2.0.7) :class:`ControlledBlock`.

    Reads ``priority`` from :attr:`BoneTrack.metadata` (defaults to 0
    when no metadata was harvested in step 10d).
    """
    priority = 0
    if track.metadata is not None:
        priority = int(track.metadata.priority) & 0xFF
    return ControlledBlock(
        interpolator=int(interpolator_ref),
        controller=NULL_REF,
        priority=priority,
        node_name=nif_string(index=int(name_index) & 0xFFFFFFFF),
        controller_type=nif_string(index=int(controller_type_index) & 0xFFFFFFFF),
        controller_id=nif_string(index=int(controller_id_index) & 0xFFFFFFFF),
        interpolator_id=nif_string(index=int(interpolator_id_index) & 0xFFFFFFFF),
        property_type=nif_string(index=int(property_type_index) & 0xFFFFFFFF),
    )


def animation_data_to_controller_sequence(
    anim: AnimationData,
    *,
    controlled_blocks: list[ControlledBlock],
    name_index: int,
    text_keys_ref: int = NULL_REF,
    manager_ref: int = NULL_REF,
    accum_root_name_index: int = 0xFFFFFFFF,
) -> NiControllerSequence:
    """Pack scalar metadata + the prebuilt ControlledBlock list."""
    return NiControllerSequence(
        name=nif_string(index=int(name_index) & 0xFFFFFFFF),
        num_controlled_blocks=len(controlled_blocks),
        array_grow_by=0,
        controlled_blocks=list(controlled_blocks),
        weight=float(anim.weight),
        text_keys=int(text_keys_ref),
        cycle_type=int(anim.cycle_type),
        frequency=float(anim.frequency),
        start_time=float(anim.start_time),
        stop_time=float(anim.stop_time),
        manager=int(manager_ref),
        accum_root_name=nif_string(index=int(accum_root_name_index) & 0xFFFFFFFF),
        accum_flags=int(anim.accum_flags) & 0xFFFFFFFF,
        num_anim_note_arrays=0,
        anim_note_arrays=[],
    )


def build_text_key_extra_data(
    events: Iterable[tuple[float, str]],
    *,
    name_index: int = 0xFFFFFFFF,
    string_indices: dict[str, int] | None = None,
) -> NiTextKeyExtraData:
    """Build :class:`NiTextKeyExtraData` from ``[(time, name), ...]`` events.

    Each text-key value is a ``string`` (string-table index). When
    ``string_indices`` is provided it must map every event name to its
    pre-allocated table index; otherwise placeholder ``0xFFFFFFFF``
    values are emitted (suitable only for tests / placeholder writes).
    """
    pairs = list(events)
    keys: list[Key | None] = []
    for time, text in pairs:
        if string_indices is not None and text in string_indices:
            value = nif_string(index=int(string_indices[text]) & 0xFFFFFFFF)
        else:
            value = nif_string(index=0xFFFFFFFF)
        keys.append(Key(time=float(time), value=value))
    return NiTextKeyExtraData(
        name=nif_string(index=int(name_index) & 0xFFFFFFFF),
        next_extra_data=NULL_REF,
        num_text_keys=len(keys),
        text_keys=keys,
    )


# ---- string-table allocator + orchestrator -------------------------------


class _StringTable:
    """Allocates one SizedString entry per unique string across the table.

    The orchestrator routes every unique sequence name, accum-root name,
    bone name, controller-type string, etc. through this allocator so the
    emitted header carries no duplicates (the contract documented in the
    Phase 10 roadmap).
    """

    def __init__(self) -> None:
        self._index: dict[str, int] = {}
        self._strings: list[SizedString] = []

    def add(self, value: str) -> int:
        """Return the table index for ``value``, allocating if new.

        Empty strings collapse to ``0xFFFFFFFF`` (the NIF "null string"
        sentinel) so the writer doesn't emit a zero-length payload for
        every unset name.
        """
        if not value:
            return 0xFFFFFFFF
        idx = self._index.get(value)
        if idx is None:
            idx = len(self._strings)
            self._strings.append(_str_to_sized_string(value))
            self._index[value] = idx
        return idx

    @property
    def strings(self) -> list[SizedString]:
        return self._strings


def _str_to_sized_string(value: str) -> SizedString:
    payload = value.encode("latin-1")
    return SizedString(length=len(payload), value=list(payload))


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def assemble_kf_block_table(
    actions: Iterable[tuple[AnimationData, Any | None]],
    *,
    version: tuple[int, int, int, int] = DEFAULT_VERSION,
    user_version: int = DEFAULT_USER_VERSION,
    bs_version: int = DEFAULT_BS_VERSION,
) -> BlockTable:
    """Compose a ready-to-write KF :class:`BlockTable` from one or more actions.

    ``actions`` is an iterable of ``(AnimationData, pose_bones)`` pairs.
    ``pose_bones`` is unused by the block builder (it was already
    consumed by :func:`animation_data_from_blender` to harvest
    metadata) but accepted for caller-side symmetry.

    The table layout, in order:

    1. (optional) one :class:`NiTextKeyExtraData` per sequence with
       text keys.
    2. for each sequence: every :class:`NiTransformData`, then every
       :class:`NiTransformInterpolator`, then the
       :class:`NiControllerSequence` itself.

    Footer roots = the index of every emitted
    :class:`NiControllerSequence`.
    """
    materialised = list(actions)
    strings = _StringTable()
    blocks: list[Any] = []
    sequence_indices: list[int] = []

    # Pre-pass 1: text-key extra data (one per sequence with events).
    text_key_refs: list[int] = []
    for anim, _pose_bones in materialised:
        if anim.text_keys:
            string_indices = {t: strings.add(t) for _, t in anim.text_keys}
            text_block = build_text_key_extra_data(
                anim.text_keys,
                string_indices=string_indices,
            )
            text_key_refs.append(len(blocks))
            blocks.append(text_block)
        else:
            text_key_refs.append(NULL_REF)

    for action_idx, (anim, _pose_bones) in enumerate(materialised):
        seq_name_idx = strings.add(anim.name)
        accum_idx = strings.add(anim.accum_root_name)

        # Per-bone NiTransformData
        data_refs: list[int] = []
        for track in anim.tracks:
            data = bone_track_to_ni_transform_data(track, fps=anim.fps)
            data_refs.append(len(blocks))
            blocks.append(data)

        # Per-bone NiTransformInterpolator
        interp_refs: list[int] = []
        for data_ref, track in zip(data_refs, anim.tracks, strict=True):
            interp = bone_track_to_ni_transform_interpolator(
                track, data_ref=data_ref
            )
            interp_refs.append(len(blocks))
            blocks.append(interp)

        # ControlledBlocks
        controlled: list[ControlledBlock] = []
        for interp_ref, track in zip(interp_refs, anim.tracks, strict=True):
            bone_name_idx = strings.add(track.bone_name)
            ct_idx = (
                strings.add(track.metadata.controller_type)
                if track.metadata is not None
                else 0xFFFFFFFF
            )
            cid_idx = (
                strings.add(track.metadata.controller_id)
                if track.metadata is not None
                else 0xFFFFFFFF
            )
            iid_idx = (
                strings.add(track.metadata.interpolator_id)
                if track.metadata is not None
                else 0xFFFFFFFF
            )
            pt_idx = (
                strings.add(track.metadata.property_type)
                if track.metadata is not None
                else 0xFFFFFFFF
            )
            controlled.append(
                bone_track_to_controlled_block(
                    track,
                    interpolator_ref=interp_ref,
                    name_index=bone_name_idx,
                    controller_type_index=ct_idx,
                    controller_id_index=cid_idx,
                    interpolator_id_index=iid_idx,
                    property_type_index=pt_idx,
                )
            )

        seq = animation_data_to_controller_sequence(
            anim,
            controlled_blocks=controlled,
            name_index=seq_name_idx,
            text_keys_ref=text_key_refs[action_idx],
            accum_root_name_index=accum_idx,
        )
        sequence_indices.append(len(blocks))
        blocks.append(seq)

    header = Header(
        version=pack_version(*version),
        endian_type=1,
        user_version=int(user_version),
        num_blocks=len(blocks),
        bs_header=BSStreamHeader(
            bs_version=int(bs_version),
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
        num_strings=len(strings.strings),
        strings=list(strings.strings),
        max_string_length=max(
            (s.length for s in strings.strings), default=0
        ),
    )
    ctx = ReadContext(
        version=header.version,
        user_version=header.user_version,
        bs_version=int(bs_version),
    )
    footer = Footer(
        num_roots=len(sequence_indices),
        roots=list(sequence_indices),
    )
    return BlockTable(header=header, blocks=blocks, footer=footer, ctx=ctx)
