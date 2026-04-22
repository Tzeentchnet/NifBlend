"""Unit tests for :mod:`nifblend.bridge.animation_in` (Phase 5 step 19).

The decoder operates on hand-built :class:`NiControllerSequence` /
:class:`NiTransformInterpolator` / :class:`NiTransformData` graphs --
real ``.kf`` file decoding still depends on the ``#T#`` template gap on
:class:`Key` / :class:`QuatKey` (ROADMAP step 2f). These tests pin down
the bridge's contract so the end-to-end path lights up the moment the
codegen widening lands.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.animation_in import (
    DEFAULT_FPS,
    AnimationData,
    BoneTrack,
    animation_data_to_blender,
    controller_sequence_to_animation_data,
)
from nifblend.format.generated.blocks import (
    NiControllerSequence,
    NiTransformData,
    NiTransformInterpolator,
)
from nifblend.format.generated.enums import KeyType
from nifblend.format.generated.structs import (
    ControlledBlock,
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

# ---- helpers --------------------------------------------------------------


def _table(blocks: list[Any], names: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        blocks=blocks,
        header=SimpleNamespace(
            strings=[
                SizedString(length=len(s), value=list(s.encode("latin-1")))
                for s in names
            ],
        ),
    )


def _vec3_key(time: float, x: float, y: float, z: float) -> Key:
    return Key(time=time, value=Vector3(x=x, y=y, z=z))


def _scalar_key(time: float, value: float) -> Key:
    return Key(time=time, value=value)


def _quat_key(time: float, w: float, x: float, y: float, z: float) -> QuatKey:
    return QuatKey(time=time, value=Quaternion(w=w, x=x, y=y, z=z))


def _vec3_group(keys: list[Key], *, interp: int = int(KeyType.LINEAR_KEY)) -> KeyGroup:
    return KeyGroup(num_keys=len(keys), interpolation=interp, keys=keys)


def _scalar_group(keys: list[Key], *, interp: int = int(KeyType.LINEAR_KEY)) -> KeyGroup:
    return KeyGroup(num_keys=len(keys), interpolation=interp, keys=keys)


def _identity_quat_transform() -> NiQuatTransform:
    return NiQuatTransform(
        translation=Vector3(x=0.0, y=0.0, z=0.0),
        rotation=Quaternion(w=1.0, x=0.0, y=0.0, z=0.0),
        scale=1.0,
    )


def _build_sequence(
    *,
    name: str,
    bone_name_idx_pairs: list[tuple[str, NiTransformData]],
    sequence_name_idx: int = 0,
    extra_strings: list[str] | None = None,
) -> tuple[SimpleNamespace, int]:
    """Wire up a controller sequence + per-bone interpolator/data chains.

    Returns ``(table, sequence_index)`` ready to feed
    :func:`controller_sequence_to_animation_data`.
    """
    strings = [name] + (extra_strings or [])
    blocks: list[Any] = [None]  # placeholder; sequence goes here

    controlled: list[ControlledBlock] = []
    for bone_name, data in bone_name_idx_pairs:
        if bone_name not in strings:
            strings.append(bone_name)
        bone_str_idx = strings.index(bone_name)

        data_idx = len(blocks)
        blocks.append(data)

        interp = NiTransformInterpolator(transform=_identity_quat_transform(), data=data_idx)
        interp_idx = len(blocks)
        blocks.append(interp)

        controlled.append(
            ControlledBlock(
                interpolator=interp_idx,
                controller=-1,
                node_name=nif_string(index=bone_str_idx),
                priority=0,
            )
        )

    seq = NiControllerSequence(
        name=nif_string(index=sequence_name_idx),
        num_controlled_blocks=len(controlled),
        array_grow_by=0,
        controlled_blocks=controlled,
        weight=0.5,
        text_keys=-1,
        cycle_type=2,  # CYCLE_CLAMP
        frequency=2.0,
        start_time=0.0,
        stop_time=1.0,
        manager=-1,
        accum_root_name=nif_string(index=0xFFFFFFFF),
        accum_flags=0,
        num_anim_note_arrays=0,
        anim_note_arrays=[],
    )
    blocks[0] = seq
    return _table(blocks, strings), 0


# ---- decoder: sequence-level metadata -------------------------------------


def test_empty_sequence_decodes_to_empty_animation_data() -> None:
    table, idx = _build_sequence(name="Idle", bone_name_idx_pairs=[])
    anim = controller_sequence_to_animation_data(table, idx)  # type: ignore[arg-type]

    assert isinstance(anim, AnimationData)
    assert anim.name == "Idle"
    assert anim.tracks == []
    assert anim.fps == DEFAULT_FPS
    assert anim.cycle_type == 2
    assert anim.frequency == pytest.approx(2.0)
    assert anim.weight == pytest.approx(0.5)


def test_decoder_rejects_non_sequence_block() -> None:
    table = _table([NiTransformData()], ["x"])
    with pytest.raises(TypeError, match="NiControllerSequence"):
        controller_sequence_to_animation_data(table, 0)  # type: ignore[arg-type]


# ---- decoder: translation channel -----------------------------------------


def test_translation_keys_pack_into_n_by_4_array() -> None:
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.LINEAR_KEY),
        quaternion_keys=[],
        translations=_vec3_group(
            [
                _vec3_key(0.0, 1.0, 2.0, 3.0),
                _vec3_key(0.5, 4.0, 5.0, 6.0),
            ]
        ),
        scales=_scalar_group([]),
    )
    table, idx = _build_sequence(
        name="Walk", bone_name_idx_pairs=[("Bip01", data)]
    )

    anim = controller_sequence_to_animation_data(table, idx, fps=30.0)  # type: ignore[arg-type]

    assert len(anim.tracks) == 1
    track = anim.tracks[0]
    assert track.bone_name == "Bip01"
    assert track.translation.shape == (2, 4)
    # frame = time * fps
    np.testing.assert_allclose(track.translation[:, 0], [0.0, 15.0])
    np.testing.assert_allclose(track.translation[:, 1:], [[1, 2, 3], [4, 5, 6]])
    assert track.translation_interp == int(KeyType.LINEAR_KEY)
    # No rotation/scale keys -> empty arrays.
    assert track.rotation_quaternion.shape == (0, 5)
    assert track.scale.shape == (0, 2)


def test_fps_scales_time_to_frame() -> None:
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.LINEAR_KEY),
        translations=_vec3_group([_vec3_key(1.0, 0, 0, 0)]),
        scales=_scalar_group([]),
    )
    table, idx = _build_sequence(name="A", bone_name_idx_pairs=[("B", data)])

    anim = controller_sequence_to_animation_data(table, idx, fps=24.0)  # type: ignore[arg-type]

    assert anim.tracks[0].translation[0, 0] == pytest.approx(24.0)


# ---- decoder: rotation channel --------------------------------------------


def test_quaternion_keys_pack_into_n_by_5_array_in_wxyz_order() -> None:
    data = NiTransformData(
        num_rotation_keys=2,
        rotation_type=int(KeyType.LINEAR_KEY),
        quaternion_keys=[
            _quat_key(0.0, 1.0, 0.0, 0.0, 0.0),
            _quat_key(0.5, 0.7071, 0.0, 0.7071, 0.0),
        ],
        translations=_vec3_group([]),
        scales=_scalar_group([]),
    )
    table, idx = _build_sequence(name="A", bone_name_idx_pairs=[("Bone", data)])

    anim = controller_sequence_to_animation_data(table, idx, fps=30.0)  # type: ignore[arg-type]

    track = anim.tracks[0]
    assert track.rotation_quaternion.shape == (2, 5)
    # NIF Quaternion is (w, x, y, z) -- Blender quaternion matches.
    np.testing.assert_allclose(track.rotation_quaternion[0], [0.0, 1.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(
        track.rotation_quaternion[1], [15.0, 0.7071, 0.0, 0.7071, 0.0], atol=1e-4
    )
    assert track.rotation_interp == int(KeyType.LINEAR_KEY)
    # XYZ Euler arrays must stay empty when quaternion keys are present.
    for axis in track.rotation_euler:
        assert axis.shape == (0, 2)


def test_xyz_rotation_type_populates_per_axis_euler_arrays() -> None:
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.XYZ_ROTATION_KEY),
        quaternion_keys=[],
        xyz_rotations=[
            _scalar_group([_scalar_key(0.0, 0.1), _scalar_key(0.5, 0.2)]),
            _scalar_group([_scalar_key(0.0, 0.3)]),
            _scalar_group([], interp=int(KeyType.CONST_KEY)),
        ],
        translations=_vec3_group([]),
        scales=_scalar_group([]),
    )
    table, idx = _build_sequence(name="A", bone_name_idx_pairs=[("B", data)])

    anim = controller_sequence_to_animation_data(table, idx, fps=30.0)  # type: ignore[arg-type]

    track = anim.tracks[0]
    # Quaternion path stays empty when rotation_type == XYZ_ROTATION_KEY.
    assert track.rotation_quaternion.shape == (0, 5)
    x_axis, y_axis, z_axis = track.rotation_euler
    assert x_axis.shape == (2, 2)
    np.testing.assert_allclose(x_axis[:, 0], [0.0, 15.0])
    np.testing.assert_allclose(x_axis[:, 1], [0.1, 0.2])
    assert y_axis.shape == (1, 2)
    np.testing.assert_allclose(y_axis[0], [0.0, 0.3])
    assert z_axis.shape == (0, 2)
    assert track.rotation_euler_interp[0] == int(KeyType.LINEAR_KEY)
    assert track.rotation_euler_interp[2] == int(KeyType.CONST_KEY)


# ---- decoder: scale + skip behaviour --------------------------------------


def test_scale_keys_pack_into_n_by_2_array() -> None:
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.LINEAR_KEY),
        translations=_vec3_group([]),
        scales=_scalar_group([_scalar_key(0.0, 1.0), _scalar_key(1.0, 1.5)]),
    )
    table, idx = _build_sequence(name="A", bone_name_idx_pairs=[("B", data)])

    anim = controller_sequence_to_animation_data(table, idx, fps=30.0)  # type: ignore[arg-type]
    track = anim.tracks[0]
    assert track.scale.shape == (2, 2)
    np.testing.assert_allclose(track.scale, [[0.0, 1.0], [30.0, 1.5]])
    assert track.scale_interp == int(KeyType.LINEAR_KEY)


def test_controlled_block_with_missing_interpolator_is_skipped() -> None:
    seq = NiControllerSequence(
        name=nif_string(index=0),
        num_controlled_blocks=1,
        array_grow_by=0,
        controlled_blocks=[
            ControlledBlock(interpolator=-1, controller=-1, priority=0,
                            node_name=nif_string(index=1))
        ],
        weight=1.0, text_keys=-1, cycle_type=0, frequency=1.0,
        start_time=0.0, stop_time=0.0, manager=-1,
        accum_root_name=nif_string(index=0xFFFFFFFF), accum_flags=0,
        num_anim_note_arrays=0, anim_note_arrays=[],
    )
    table = _table([seq], ["A", "Bone"])

    anim = controller_sequence_to_animation_data(table, 0)  # type: ignore[arg-type]
    assert anim.tracks == []


def test_controlled_block_with_no_data_block_is_skipped() -> None:
    """An interpolator carrying only a static transform (no data ref)
    contributes no fcurves -- it's a bind pose, not an animation."""
    interp = NiTransformInterpolator(transform=_identity_quat_transform(), data=-1)
    seq = NiControllerSequence(
        name=nif_string(index=0),
        num_controlled_blocks=1,
        array_grow_by=0,
        controlled_blocks=[
            ControlledBlock(interpolator=2, controller=-1, priority=0,
                            node_name=nif_string(index=1)),
        ],
        weight=1.0, text_keys=-1, cycle_type=0, frequency=1.0,
        start_time=0.0, stop_time=0.0, manager=-1,
        accum_root_name=nif_string(index=0xFFFFFFFF), accum_flags=0,
        num_anim_note_arrays=0, anim_note_arrays=[],
    )
    # Layout: [seq, <unused>, interp]
    table = _table([seq, None, interp], ["A", "Bone"])

    anim = controller_sequence_to_animation_data(table, 0)  # type: ignore[arg-type]
    assert anim.tracks == []


def test_keys_with_none_value_are_silently_dropped() -> None:
    """Codegen template gap may leave Key.value at ``None``; the decoder
    must skip that row rather than crash."""
    data = NiTransformData(
        num_rotation_keys=0,
        rotation_type=int(KeyType.LINEAR_KEY),
        translations=_vec3_group(
            [_vec3_key(0.0, 1, 2, 3), Key(time=0.5, value=None), _vec3_key(1.0, 4, 5, 6)]
        ),
        scales=_scalar_group([]),
    )
    table, idx = _build_sequence(name="A", bone_name_idx_pairs=[("B", data)])

    anim = controller_sequence_to_animation_data(table, idx, fps=30.0)  # type: ignore[arg-type]
    track = anim.tracks[0]
    assert track.translation.shape == (2, 4)
    np.testing.assert_allclose(track.translation[:, 0], [0.0, 30.0])


# ---- Blender wrapper ------------------------------------------------------


class _FakeKeyframePoints:
    def __init__(self) -> None:
        self.added: int = 0
        self.co: list[float] | None = None
        self.interpolation: list[int] | None = None

    def add(self, n: int) -> None:
        self.added += n

    def foreach_set(self, attr: str, values: Any) -> None:
        flat = list(values)
        if attr == "co":
            self.co = flat
        elif attr == "interpolation":
            self.interpolation = flat


class _FakeFCurve:
    def __init__(self, data_path: str, index: int, group: str | None) -> None:
        self.data_path = data_path
        self.array_index = index
        self.group = group
        self.keyframe_points = _FakeKeyframePoints()


class _FakeFCurves:
    def __init__(self) -> None:
        self.created: list[_FakeFCurve] = []

    def new(self, *, data_path: str, index: int, action_group: str | None = None) -> _FakeFCurve:
        fc = _FakeFCurve(data_path, index, action_group)
        self.created.append(fc)
        return fc


class _FakeAction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.fcurves = _FakeFCurves()


class _FakeActions:
    def __init__(self) -> None:
        self.created: list[_FakeAction] = []

    def new(self, name: str) -> _FakeAction:
        action = _FakeAction(name)
        self.created.append(action)
        return action


@pytest.fixture
def fake_bpy() -> SimpleNamespace:
    return SimpleNamespace(data=SimpleNamespace(actions=_FakeActions()))


def test_wrapper_creates_action_named_after_data(fake_bpy: SimpleNamespace) -> None:
    data = AnimationData(name="Idle", tracks=[])
    action = animation_data_to_blender(data, bpy=fake_bpy)
    assert action.name == "Idle"
    assert action.fcurves.created == []


def test_wrapper_emits_three_translation_fcurves_one_per_axis(
    fake_bpy: SimpleNamespace,
) -> None:
    track = BoneTrack(
        bone_name="Bip01",
        translation=np.array(
            [[0.0, 1.0, 2.0, 3.0], [10.0, 4.0, 5.0, 6.0]], dtype=np.float32
        ),
        translation_interp=int(KeyType.LINEAR_KEY),
    )
    anim = AnimationData(name="Walk", tracks=[track])

    action = animation_data_to_blender(anim, bpy=fake_bpy)

    assert len(action.fcurves.created) == 3
    paths = {(fc.data_path, fc.array_index) for fc in action.fcurves.created}
    assert paths == {
        ('pose.bones["Bip01"].location', 0),
        ('pose.bones["Bip01"].location', 1),
        ('pose.bones["Bip01"].location', 2),
    }
    # Bulk insertion: each fcurve's keyframe_points.add(n) was called
    # exactly once with the full n, and ``co`` was stamped via
    # foreach_set with interleaved [frame, value] pairs.
    for fc in action.fcurves.created:
        assert fc.keyframe_points.added == 2
        assert fc.keyframe_points.co is not None
        assert len(fc.keyframe_points.co) == 4  # 2 keys * (frame, value)
        # Frame column matches the input.
        assert fc.keyframe_points.co[0] == pytest.approx(0.0)
        assert fc.keyframe_points.co[2] == pytest.approx(10.0)


def test_wrapper_emits_four_quaternion_fcurves(fake_bpy: SimpleNamespace) -> None:
    track = BoneTrack(
        bone_name="Bone",
        rotation_quaternion=np.array(
            [[0.0, 1.0, 0.0, 0.0, 0.0]], dtype=np.float32
        ),
        rotation_interp=int(KeyType.LINEAR_KEY),
    )
    anim = AnimationData(name="A", tracks=[track])

    action = animation_data_to_blender(anim, bpy=fake_bpy)

    indices = sorted(
        fc.array_index for fc in action.fcurves.created
        if fc.data_path == 'pose.bones["Bone"].rotation_quaternion'
    )
    assert indices == [0, 1, 2, 3]


def test_wrapper_emits_per_axis_euler_fcurves(fake_bpy: SimpleNamespace) -> None:
    track = BoneTrack(
        bone_name="Bone",
        rotation_euler=(
            np.array([[0.0, 0.1]], dtype=np.float32),
            np.empty((0, 2), dtype=np.float32),  # Y axis: no keys -> no fcurve
            np.array([[0.0, 0.3], [10.0, 0.4]], dtype=np.float32),
        ),
        rotation_euler_interp=(int(KeyType.LINEAR_KEY), None, int(KeyType.CONST_KEY)),
    )
    anim = AnimationData(name="A", tracks=[track])

    action = animation_data_to_blender(anim, bpy=fake_bpy)

    euler_fcurves = {
        fc.array_index: fc
        for fc in action.fcurves.created
        if fc.data_path == 'pose.bones["Bone"].rotation_euler'
    }
    assert set(euler_fcurves.keys()) == {0, 2}  # Y axis was skipped
    assert euler_fcurves[2].keyframe_points.added == 2


def test_wrapper_fans_uniform_scale_to_three_axes(fake_bpy: SimpleNamespace) -> None:
    track = BoneTrack(
        bone_name="Bone",
        scale=np.array([[0.0, 1.0], [30.0, 1.5]], dtype=np.float32),
        scale_interp=int(KeyType.LINEAR_KEY),
    )
    anim = AnimationData(name="A", tracks=[track])

    action = animation_data_to_blender(anim, bpy=fake_bpy)

    scale_indices = sorted(
        fc.array_index for fc in action.fcurves.created
        if fc.data_path == 'pose.bones["Bone"].scale'
    )
    assert scale_indices == [0, 1, 2]
    # All three axes carry the same uniform scale stream.
    streams = [
        fc.keyframe_points.co
        for fc in action.fcurves.created
        if fc.data_path == 'pose.bones["Bone"].scale'
    ]
    assert streams[0] == streams[1] == streams[2]


def test_wrapper_uses_action_name_override(fake_bpy: SimpleNamespace) -> None:
    anim = AnimationData(name="Original", tracks=[])
    action = animation_data_to_blender(anim, bpy=fake_bpy, action_name="Override")
    assert action.name == "Override"


def test_end_to_end_decoder_then_wrapper(fake_bpy: SimpleNamespace) -> None:
    """Smoke test: a sequence with one bone, all three channels."""
    data = NiTransformData(
        num_rotation_keys=1,
        rotation_type=int(KeyType.LINEAR_KEY),
        quaternion_keys=[_quat_key(0.0, 1.0, 0.0, 0.0, 0.0)],
        translations=_vec3_group([_vec3_key(0.0, 0.0, 0.0, 0.0)]),
        scales=_scalar_group([_scalar_key(0.0, 1.0)]),
    )
    table, idx = _build_sequence(
        name="Idle", bone_name_idx_pairs=[("Bip01", data)]
    )

    anim = controller_sequence_to_animation_data(table, idx)  # type: ignore[arg-type]
    action = animation_data_to_blender(anim, bpy=fake_bpy)

    paths = {fc.data_path for fc in action.fcurves.created}
    assert paths == {
        'pose.bones["Bip01"].location',
        'pose.bones["Bip01"].rotation_quaternion',
        'pose.bones["Bip01"].scale',
    }
    # 3 location + 4 quaternion + 3 scale = 10 fcurves.
    assert len(action.fcurves.created) == 10
