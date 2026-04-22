"""Phase 5 step 20 -- rotation_mode toggle on the animation bridge.

Pinpoints the QUATERNION (default) vs EULER paths through
:func:`animation_data_to_blender` and the standalone
:func:`quaternion_stream_to_euler_streams` helper.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.animation_in import (
    AnimationData,
    BoneTrack,
    animation_data_to_blender,
    apply_rotation_mode_to_armature,
    quaternion_stream_to_euler_streams,
)
from nifblend.format.generated.enums import KeyType

# ---- fakes ----------------------------------------------------------------


class _FakeKeyframePoints:
    def __init__(self) -> None:
        self.added: int = 0
        self.co: list[float] | None = None

    def add(self, n: int) -> None:
        self.added += n

    def foreach_set(self, attr: str, values: Any) -> None:
        flat = list(values)
        if attr == "co":
            self.co = flat


class _FakeFCurve:
    def __init__(self, data_path: str, index: int, group: str | None) -> None:
        self.data_path = data_path
        self.array_index = index
        self.group = group
        self.keyframe_points = _FakeKeyframePoints()


class _FakeFCurves:
    def __init__(self) -> None:
        self.created: list[_FakeFCurve] = []

    def new(
        self, *, data_path: str, index: int, action_group: str | None = None
    ) -> _FakeFCurve:
        fc = _FakeFCurve(data_path, index, action_group)
        self.created.append(fc)
        return fc


class _FakeAction:
    def __init__(self, name: str) -> None:
        self.name = name
        self.fcurves = _FakeFCurves()


class _FakeActions:
    def new(self, name: str) -> _FakeAction:
        return _FakeAction(name)


@pytest.fixture
def fake_bpy() -> SimpleNamespace:
    return SimpleNamespace(data=SimpleNamespace(actions=_FakeActions()))


# ---- quaternion_stream_to_euler_streams ----------------------------------


def test_identity_quaternion_yields_zero_euler() -> None:
    stream = np.array([[0.0, 1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
    x, y, z = quaternion_stream_to_euler_streams(stream)
    assert x.shape == y.shape == z.shape == (1, 2)
    np.testing.assert_allclose(x[:, 1], [0.0], atol=1e-6)
    np.testing.assert_allclose(y[:, 1], [0.0], atol=1e-6)
    np.testing.assert_allclose(z[:, 1], [0.0], atol=1e-6)


def test_known_axis_angle_round_trips() -> None:
    # Quaternion for a 90 deg rotation around Z axis.
    half = math.pi / 4.0
    w, x, y, z = math.cos(half), 0.0, 0.0, math.sin(half)
    stream = np.array([[10.0, w, x, y, z]], dtype=np.float32)
    ax, ay, az = quaternion_stream_to_euler_streams(stream)
    # X axis (roll) and Y axis (pitch) are zero, Z axis (yaw) is pi/2.
    assert ax[0, 1] == pytest.approx(0.0, abs=1e-5)
    assert ay[0, 1] == pytest.approx(0.0, abs=1e-5)
    assert az[0, 1] == pytest.approx(math.pi / 2.0, abs=1e-5)
    # Frames passed through unchanged.
    assert ax[0, 0] == pytest.approx(10.0)
    assert az[0, 0] == pytest.approx(10.0)


def test_empty_stream_returns_empty_arrays() -> None:
    stream = np.empty((0, 5), dtype=np.float32)
    x, y, z = quaternion_stream_to_euler_streams(stream)
    assert x.shape == (0, 2) and y.shape == (0, 2) and z.shape == (0, 2)


def test_pitch_is_clipped_at_gimbal_lock() -> None:
    """sin(pitch) input clipped to [-1, +1] dodges arcsin domain errors."""
    # Quaternion (w=cos(pi/4), y=sin(pi/4)) = 90 deg pitch around Y.
    half = math.pi / 4.0
    stream = np.array(
        [[0.0, math.cos(half), 0.0, math.sin(half), 0.0]], dtype=np.float32
    )
    _, y, _ = quaternion_stream_to_euler_streams(stream)
    assert y[0, 1] == pytest.approx(math.pi / 2.0, abs=1e-3)
    # No NaNs.
    assert not math.isnan(float(y[0, 1]))


# ---- animation_data_to_blender: rotation_mode toggle ---------------------


def _track_with_quat() -> BoneTrack:
    half = math.pi / 4.0
    w, x, y, z = math.cos(half), 0.0, 0.0, math.sin(half)
    return BoneTrack(
        bone_name="Bone",
        rotation_quaternion=np.array(
            [[0.0, 1.0, 0.0, 0.0, 0.0], [10.0, w, x, y, z]], dtype=np.float32
        ),
        rotation_interp=int(KeyType.LINEAR_KEY),
    )


def test_default_rotation_mode_emits_quaternion_fcurves(
    fake_bpy: SimpleNamespace,
) -> None:
    anim = AnimationData(name="A", tracks=[_track_with_quat()])
    action = animation_data_to_blender(anim, bpy=fake_bpy)
    paths = sorted(
        (fc.data_path, fc.array_index) for fc in action.fcurves.created
    )
    assert paths == [
        ('pose.bones["Bone"].rotation_quaternion', 0),
        ('pose.bones["Bone"].rotation_quaternion', 1),
        ('pose.bones["Bone"].rotation_quaternion', 2),
        ('pose.bones["Bone"].rotation_quaternion', 3),
    ]


def test_rotation_mode_euler_emits_three_axis_fcurves(
    fake_bpy: SimpleNamespace,
) -> None:
    anim = AnimationData(name="A", tracks=[_track_with_quat()])
    action = animation_data_to_blender(anim, bpy=fake_bpy, rotation_mode="EULER")
    paths = sorted(
        (fc.data_path, fc.array_index) for fc in action.fcurves.created
    )
    assert paths == [
        ('pose.bones["Bone"].rotation_euler', 0),
        ('pose.bones["Bone"].rotation_euler', 1),
        ('pose.bones["Bone"].rotation_euler', 2),
    ]
    # Each axis fcurve carries the full key count.
    for fc in action.fcurves.created:
        assert fc.keyframe_points.added == 2
    # Z-axis carries the converted yaw on the second keyframe (pi/2).
    z_fc = next(
        fc for fc in action.fcurves.created if fc.array_index == 2
    )
    co = z_fc.keyframe_points.co
    assert co is not None
    # co = [f0, v0, f1, v1] -- v1 is yaw at frame 10.
    assert co[3] == pytest.approx(math.pi / 2.0, abs=1e-5)


def test_rotation_mode_lowercase_is_normalised(fake_bpy: SimpleNamespace) -> None:
    anim = AnimationData(name="A", tracks=[_track_with_quat()])
    action = animation_data_to_blender(anim, bpy=fake_bpy, rotation_mode="euler")
    assert all(
        fc.data_path.endswith("rotation_euler") for fc in action.fcurves.created
    )


def test_rotation_mode_invalid_raises(fake_bpy: SimpleNamespace) -> None:
    anim = AnimationData(name="A", tracks=[])
    with pytest.raises(ValueError, match="rotation_mode"):
        animation_data_to_blender(anim, bpy=fake_bpy, rotation_mode="ZYX")


def test_xyz_rotation_track_unaffected_by_quaternion_toggle(
    fake_bpy: SimpleNamespace,
) -> None:
    """Tracks that arrived as XYZ_ROTATION_KEY are always Euler-emitted."""
    track = BoneTrack(
        bone_name="B",
        rotation_euler=(
            np.array([[0.0, 0.1]], dtype=np.float32),
            np.empty((0, 2), dtype=np.float32),
            np.array([[0.0, 0.3]], dtype=np.float32),
        ),
        rotation_euler_interp=(int(KeyType.LINEAR_KEY), None, int(KeyType.LINEAR_KEY)),
    )
    anim = AnimationData(name="A", tracks=[track])
    # Even with QUATERNION mode set, Euler keys still go to rotation_euler.
    action = animation_data_to_blender(anim, bpy=fake_bpy, rotation_mode="QUATERNION")
    indices = sorted(
        fc.array_index
        for fc in action.fcurves.created
        if fc.data_path == 'pose.bones["B"].rotation_euler'
    )
    assert indices == [0, 2]


# ---- apply_rotation_mode_to_armature -------------------------------------


class _FakePoseBone:
    def __init__(self) -> None:
        self.rotation_mode = "QUATERNION"


class _FakePoseBones:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: _FakePoseBone() for n in names}

    def get(self, name: str) -> _FakePoseBone | None:
        return self._items.get(name)


def test_apply_rotation_mode_sets_xyz_when_euler() -> None:
    armature = SimpleNamespace(
        pose=SimpleNamespace(bones=_FakePoseBones(["A", "B"]))
    )
    anim = AnimationData(
        name="x",
        tracks=[BoneTrack(bone_name="A"), BoneTrack(bone_name="B")],
    )
    apply_rotation_mode_to_armature(armature, anim, rotation_mode="EULER")
    assert armature.pose.bones.get("A").rotation_mode == "XYZ"
    assert armature.pose.bones.get("B").rotation_mode == "XYZ"


def test_apply_rotation_mode_sets_quaternion_when_default() -> None:
    armature = SimpleNamespace(
        pose=SimpleNamespace(bones=_FakePoseBones(["A"]))
    )
    armature.pose.bones.get("A").rotation_mode = "XYZ"  # start in Euler
    anim = AnimationData(name="x", tracks=[BoneTrack(bone_name="A")])
    apply_rotation_mode_to_armature(armature, anim, rotation_mode="QUATERNION")
    assert armature.pose.bones.get("A").rotation_mode == "QUATERNION"


def test_apply_rotation_mode_skips_missing_bones() -> None:
    """A track for a bone that's not on the armature is silently skipped."""
    armature = SimpleNamespace(
        pose=SimpleNamespace(bones=_FakePoseBones(["A"]))
    )
    anim = AnimationData(
        name="x",
        tracks=[BoneTrack(bone_name="A"), BoneTrack(bone_name="GHOST")],
    )
    # Should not raise.
    apply_rotation_mode_to_armature(armature, anim, rotation_mode="EULER")
    assert armature.pose.bones.get("A").rotation_mode == "XYZ"


def test_apply_rotation_mode_no_pose_is_noop() -> None:
    armature = SimpleNamespace()  # no .pose attr
    anim = AnimationData(name="x", tracks=[BoneTrack(bone_name="A")])
    apply_rotation_mode_to_armature(armature, anim, rotation_mode="EULER")  # no raise


def test_apply_rotation_mode_invalid_value_raises() -> None:
    with pytest.raises(ValueError, match="rotation_mode"):
        apply_rotation_mode_to_armature(
            SimpleNamespace(), AnimationData(name="x"), rotation_mode="ZYX"
        )
