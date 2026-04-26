"""Phase 10 step 10e — :mod:`nifblend.bridge.animation_out` tests.

Inverse-side of :mod:`test_animation_in.py`. Exercises:

* fcurve grouping by bone + channel,
* per-block builders (NiTransformData / NiTransformInterpolator /
  ControlledBlock / NiControllerSequence / NiTextKeyExtraData),
* string-table allocator,
* full ``Action → block list → write_nif → read_nif → AnimationData``
  round-trip with the import-side decoder.
"""

from __future__ import annotations

import io
import math
from types import SimpleNamespace

import numpy as np
import pytest

from nifblend.bridge.animation_in import (
    AnimationData,
    BoneTrack,
    BoneTrackMetadata,
    controller_sequence_to_animation_data,
)
from nifblend.bridge.animation_out import (
    NULL_REF,
    animation_data_from_blender,
    animation_data_to_controller_sequence,
    assemble_kf_block_table,
    bone_track_to_controlled_block,
    bone_track_to_ni_transform_data,
    bone_track_to_ni_transform_interpolator,
    build_text_key_extra_data,
)
from nifblend.bridge.animation_props import (
    apply_controlled_block_to_pose_bone,
    apply_sequence_metadata_to_action,
    apply_text_keys_to_action,
)
from nifblend.format.generated.blocks import (
    NiControllerSequence,
    NiTextKeyExtraData,
    NiTransformData,
)
from nifblend.format.generated.enums import CycleType, KeyType
from nifblend.format.generated.structs import ControlledBlock
from nifblend.io.block_table import read_nif, write_nif

# ---- fcurve fakes --------------------------------------------------------


class _FakeKF:
    """One keyframe point with ``co=(frame, value)`` + interpolation string."""

    def __init__(self, frame: float, value: float, interpolation: str = "LINEAR"):
        self.co = (float(frame), float(value))
        self.interpolation = interpolation


class _FakeKeyframePoints(list):
    def foreach_get(self, attr: str, out: np.ndarray) -> None:
        if attr != "co":
            raise ValueError(f"unsupported attr {attr!r}")
        for i, kf in enumerate(self):
            out[2 * i] = float(kf.co[0])
            out[2 * i + 1] = float(kf.co[1])


class _FakeFCurve:
    def __init__(
        self,
        data_path: str,
        array_index: int,
        keyframes: list[tuple[float, float]] | None = None,
        interpolation: str = "LINEAR",
    ):
        self.data_path = data_path
        self.array_index = array_index
        kf = _FakeKeyframePoints()
        for frame, value in keyframes or []:
            kf.append(_FakeKF(frame, value, interpolation))
        self.keyframe_points = kf


def _fake_action(name: str, fcurves: list[_FakeFCurve], frame_range=(0.0, 60.0)) -> SimpleNamespace:
    return SimpleNamespace(name=name, fcurves=fcurves, frame_range=frame_range)


# ---- animation_data_from_blender -----------------------------------------


def test_from_blender_groups_translation_fcurves_per_bone() -> None:
    action = _fake_action(
        "walk",
        [
            _FakeFCurve('pose.bones["Bip01"].location', 0, [(0, 0.0), (30, 1.0)]),
            _FakeFCurve('pose.bones["Bip01"].location', 1, [(0, 0.0), (30, 2.0)]),
            _FakeFCurve('pose.bones["Bip01"].location', 2, [(0, 0.0), (30, 3.0)]),
        ],
    )
    anim = animation_data_from_blender(action, fps=30.0)

    assert len(anim.tracks) == 1
    track = anim.tracks[0]
    assert track.bone_name == "Bip01"
    assert track.translation.shape == (2, 4)
    np.testing.assert_allclose(track.translation[1], [30.0, 1.0, 2.0, 3.0])


def test_from_blender_picks_quaternion_when_present() -> None:
    fcurves = [
        _FakeFCurve('pose.bones["B"].rotation_quaternion', i, [(0, v)])
        for i, v in enumerate([1.0, 0.0, 0.0, 0.0])
    ]
    fcurves += [
        _FakeFCurve('pose.bones["B"].rotation_euler', 0, [(0, 0.5)]),
    ]
    anim = animation_data_from_blender(_fake_action("a", fcurves), fps=30.0)
    track = anim.tracks[0]
    assert track.rotation_quaternion.shape == (1, 5)
    # Euler ignored when quaternion is present.
    for axis in track.rotation_euler:
        assert axis.shape == (0, 2)


def test_from_blender_routes_euler_when_no_quaternion() -> None:
    fcurves = [
        _FakeFCurve('pose.bones["B"].rotation_euler', 0, [(0, 0.1), (30, 0.2)]),
        _FakeFCurve('pose.bones["B"].rotation_euler', 2, [(0, 0.3)]),
    ]
    anim = animation_data_from_blender(_fake_action("a", fcurves), fps=30.0)
    track = anim.tracks[0]
    x, y, z = track.rotation_euler
    assert x.shape == (2, 2)
    assert y.shape == (0, 2)
    assert z.shape == (1, 2)


def test_from_blender_collapses_uniform_scale() -> None:
    fcurves = [
        _FakeFCurve('pose.bones["B"].scale', i, [(0, 1.0), (30, 2.0)])
        for i in range(3)
    ]
    anim = animation_data_from_blender(_fake_action("a", fcurves), fps=30.0)
    track = anim.tracks[0]
    assert track.scale.shape == (2, 2)
    np.testing.assert_allclose(track.scale[:, 1], [1.0, 2.0])


def test_from_blender_warns_on_non_uniform_scale(caplog: pytest.LogCaptureFixture) -> None:
    fcurves = [
        _FakeFCurve('pose.bones["B"].scale', 0, [(0, 1.0), (30, 2.0)]),
        _FakeFCurve('pose.bones["B"].scale', 1, [(0, 1.0), (30, 3.0)]),
        _FakeFCurve('pose.bones["B"].scale', 2, [(0, 1.0), (30, 2.0)]),
    ]
    with caplog.at_level("WARNING"):
        anim = animation_data_from_blender(_fake_action("a", fcurves), fps=30.0)
    assert any("non-uniform" in rec.message for rec in caplog.records)
    track = anim.tracks[0]
    np.testing.assert_allclose(track.scale[:, 1], [1.0, 2.0])  # axis 0 wins


def test_from_blender_skips_non_pose_bone_fcurves() -> None:
    fcurves = [
        _FakeFCurve("location", 0, [(0, 0.0)]),
        _FakeFCurve('pose.bones["X"].location', 0, [(0, 0.0)]),
    ]
    anim = animation_data_from_blender(_fake_action("a", fcurves))
    assert {t.bone_name for t in anim.tracks} == {"X"}


def test_from_blender_reads_propertygroup_metadata() -> None:
    action = _fake_action("walk", [])
    apply_sequence_metadata_to_action(
        action,
        weight=0.5,
        frequency=2.0,
        start_time=0.25,
        stop_time=1.5,
        cycle_type=int(CycleType.CYCLE_LOOP),
        accum_root_name="NPC Root [Root]",
        accum_flags=0xDEAD,
        phase=0.125,
        play_backwards=True,
    )
    apply_text_keys_to_action(action, [(0.0, "start"), (1.5, "end")])

    anim = animation_data_from_blender(action, fps=30.0)
    assert anim.weight == pytest.approx(0.5)
    assert anim.frequency == pytest.approx(2.0)
    assert anim.start_time == pytest.approx(0.25)
    assert anim.stop_time == pytest.approx(1.5)
    assert anim.cycle_type == int(CycleType.CYCLE_LOOP)
    assert anim.accum_root_name == "NPC Root [Root]"
    assert anim.accum_flags == 0xDEAD
    assert anim.phase == pytest.approx(0.125)
    assert anim.play_backwards is True
    assert anim.text_keys == [(0.0, "start"), (1.5, "end")]


def test_from_blender_falls_back_to_frame_range_for_stop_time() -> None:
    action = _fake_action("walk", [], frame_range=(0.0, 60.0))
    # No PropertyGroup at all.
    anim = animation_data_from_blender(action, fps=30.0)
    assert anim.start_time == pytest.approx(0.0)
    assert anim.stop_time == pytest.approx(2.0)


def test_from_blender_reads_pose_bone_metadata() -> None:
    fcurves = [_FakeFCurve('pose.bones["B"].location', 0, [(0, 0.0)])]
    action = _fake_action("a", fcurves)

    bone = SimpleNamespace()
    apply_controlled_block_to_pose_bone(
        bone,
        priority=42,
        controller_type="NiTransformController",
        controller_id="cid",
        interpolator_id="iid",
        property_type="pt",
    )
    pose_bones = SimpleNamespace(get=lambda name: bone if name == "B" else None)

    anim = animation_data_from_blender(action, pose_bones=pose_bones)
    track = anim.tracks[0]
    assert track.metadata is not None
    assert track.metadata.priority == 42
    assert track.metadata.controller_type == "NiTransformController"


# ---- per-block builders --------------------------------------------------


def test_bone_track_to_ni_transform_data_translation() -> None:
    track = BoneTrack(
        bone_name="B",
        translation=np.array([[0.0, 1.0, 2.0, 3.0], [30.0, 4.0, 5.0, 6.0]], dtype=np.float32),
        translation_interp=int(KeyType.LINEAR_KEY),
    )
    data = bone_track_to_ni_transform_data(track, fps=30.0)
    assert isinstance(data, NiTransformData)
    assert data.translations.num_keys == 2
    k0, k1 = data.translations.keys
    assert k0.time == pytest.approx(0.0)
    assert (k0.value.x, k0.value.y, k0.value.z) == (1.0, 2.0, 3.0)
    assert k1.time == pytest.approx(1.0)


def test_bone_track_to_ni_transform_data_quaternion() -> None:
    track = BoneTrack(
        bone_name="B",
        rotation_quaternion=np.array(
            [[0.0, 1.0, 0.0, 0.0, 0.0], [60.0, 0.7071, 0.0, 0.7071, 0.0]],
            dtype=np.float32,
        ),
        rotation_interp=int(KeyType.LINEAR_KEY),
    )
    data = bone_track_to_ni_transform_data(track, fps=30.0)
    assert data.num_rotation_keys == 2
    assert data.rotation_type == int(KeyType.LINEAR_KEY)
    q0, q1 = data.quaternion_keys
    assert q0.value.w == pytest.approx(1.0)
    assert q1.time == pytest.approx(2.0)


def test_bone_track_to_ni_transform_data_xyz_rotation() -> None:
    empty = np.empty((0, 2), dtype=np.float32)
    track = BoneTrack(
        bone_name="B",
        rotation_euler=(
            np.array([[0.0, 0.1], [30.0, 0.2]], dtype=np.float32),
            empty,
            np.array([[0.0, 0.3]], dtype=np.float32),
        ),
        rotation_euler_interp=(int(KeyType.LINEAR_KEY), None, int(KeyType.CONST_KEY)),
    )
    data = bone_track_to_ni_transform_data(track, fps=30.0)
    assert data.rotation_type == int(KeyType.XYZ_ROTATION_KEY)
    assert data.num_rotation_keys == 2
    x_kg, y_kg, z_kg = data.xyz_rotations
    assert x_kg.num_keys == 2
    assert y_kg.num_keys == 0
    assert z_kg.num_keys == 1
    assert z_kg.interpolation == int(KeyType.CONST_KEY)


def test_interpolator_uses_null_data_when_track_is_empty() -> None:
    track = BoneTrack(bone_name="B")
    interp = bone_track_to_ni_transform_interpolator(track, data_ref=42)
    assert interp.data == NULL_REF


def test_interpolator_uses_data_ref_when_track_has_keys() -> None:
    track = BoneTrack(
        bone_name="B",
        translation=np.array([[0.0, 1.0, 2.0, 3.0]], dtype=np.float32),
    )
    interp = bone_track_to_ni_transform_interpolator(track, data_ref=42)
    assert interp.data == 42


def test_controlled_block_routes_priority_from_metadata() -> None:
    track = BoneTrack(
        bone_name="B",
        metadata=BoneTrackMetadata(priority=42),
    )
    cb = bone_track_to_controlled_block(
        track, interpolator_ref=7, name_index=3
    )
    assert isinstance(cb, ControlledBlock)
    assert cb.interpolator == 7
    assert cb.priority == 42
    assert cb.node_name.index == 3


def test_animation_data_to_controller_sequence_metadata() -> None:
    anim = AnimationData(
        name="walk",
        weight=0.5,
        frequency=2.0,
        start_time=0.0,
        stop_time=1.5,
        cycle_type=int(CycleType.CYCLE_LOOP),
        accum_flags=0xDEAD,
    )
    seq = animation_data_to_controller_sequence(
        anim,
        controlled_blocks=[],
        name_index=4,
        text_keys_ref=12,
        accum_root_name_index=5,
    )
    assert isinstance(seq, NiControllerSequence)
    assert seq.name.index == 4
    assert seq.weight == pytest.approx(0.5)
    assert seq.frequency == pytest.approx(2.0)
    assert seq.cycle_type == int(CycleType.CYCLE_LOOP)
    assert seq.text_keys == 12
    assert seq.accum_root_name.index == 5
    assert seq.accum_flags == 0xDEAD


def test_build_text_key_extra_data_uses_string_indices() -> None:
    block = build_text_key_extra_data(
        [(0.0, "start"), (1.5, "end")],
        string_indices={"start": 1, "end": 2},
    )
    assert isinstance(block, NiTextKeyExtraData)
    assert block.num_text_keys == 2
    assert block.text_keys[0].value.index == 1
    assert block.text_keys[1].time == pytest.approx(1.5)


# ---- end-to-end round-trip ----------------------------------------------


def test_assemble_then_read_round_trips_one_action() -> None:
    """Action → AnimationData → block list → write_nif → read_nif →
    AnimationData round-trip with positions, quaternion rotations and
    scale surviving within 1e-5."""
    fcurves = []
    # Translation
    for i, axis_vals in enumerate([(0.0, 10.0), (0.0, 20.0), (0.0, 30.0)]):
        fcurves.append(
            _FakeFCurve(
                'pose.bones["Bip01"].location',
                i,
                [(0.0, 0.0), (30.0, axis_vals[1])],
            )
        )
    # Quaternion
    for i, val in enumerate([1.0, 0.0, 0.0, 0.0]):
        fcurves.append(
            _FakeFCurve(
                'pose.bones["Bip01"].rotation_quaternion',
                i,
                [(0.0, val), (30.0, val if i != 0 else 0.7071)],
            )
        )
    # Uniform scale
    for i in range(3):
        fcurves.append(
            _FakeFCurve(
                'pose.bones["Bip01"].scale', i, [(0.0, 1.0), (30.0, 1.5)]
            )
        )

    action = _fake_action("walk", fcurves, frame_range=(0.0, 30.0))
    anim = animation_data_from_blender(action, fps=30.0)

    table = assemble_kf_block_table([(anim, None)])
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    # Footer roots → NiControllerSequence.
    seq_idx = int(parsed.footer.roots[0])
    decoded = controller_sequence_to_animation_data(parsed, seq_idx, fps=30.0)

    assert decoded.name == "walk"
    assert len(decoded.tracks) == 1
    track = decoded.tracks[0]
    assert track.bone_name == "Bip01"

    np.testing.assert_allclose(
        track.translation, [[0.0, 0.0, 0.0, 0.0], [30.0, 10.0, 20.0, 30.0]],
        atol=1e-5,
    )
    np.testing.assert_allclose(
        track.rotation_quaternion,
        [[0.0, 1.0, 0.0, 0.0, 0.0], [30.0, 0.7071, 0.0, 0.0, 0.0]],
        atol=1e-4,
    )
    np.testing.assert_allclose(
        track.scale, [[0.0, 1.0], [30.0, 1.5]], atol=1e-5
    )


def test_assemble_then_read_round_trips_text_keys() -> None:
    action = _fake_action("idle", [])
    apply_text_keys_to_action(action, [(0.0, "start"), (math.pi, "end")])
    anim = animation_data_from_blender(action, fps=30.0)

    table = assemble_kf_block_table([(anim, None)])
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    seq_idx = int(parsed.footer.roots[0])
    decoded = controller_sequence_to_animation_data(parsed, seq_idx)

    assert decoded.text_keys == [(0.0, "start"), (pytest.approx(math.pi), "end")]


def test_assemble_handles_empty_action() -> None:
    action = _fake_action("empty", [])
    anim = animation_data_from_blender(action)
    table = assemble_kf_block_table([(anim, None)])
    assert len(table.footer.roots) == 1
    assert table.blocks[int(table.footer.roots[0])].num_controlled_blocks == 0
