"""Unit tests for :mod:`nifblend.bridge.armature_in` (Phase 4 step 14)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.armature_in import (
    DEFAULT_BONE_LENGTH,
    ArmatureData,
    BoneData,
    armature_data_to_blender,
    ninode_tree_to_armature_data,
)
from nifblend.bridge.armature_props import read_bind_matrix_from_props
from nifblend.format.generated.blocks import NiNode
from nifblend.format.generated.structs import (
    Matrix33,
    SizedString,
    Vector3,
)
from nifblend.format.generated.structs import (
    string as nif_string,
)

# ---- helpers --------------------------------------------------------------


def _identity_rot() -> Matrix33:
    return Matrix33(
        m11=1.0, m21=0.0, m31=0.0,
        m12=0.0, m22=1.0, m32=0.0,
        m13=0.0, m23=0.0, m33=1.0,
    )


def _node(
    *,
    name_idx: int,
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: Matrix33 | None = None,
    scale: float = 1.0,
    children: list[int] | None = None,
) -> NiNode:
    n = NiNode()
    n.name = nif_string(index=name_idx)
    n.translation = Vector3(*translation)
    n.rotation = rotation if rotation is not None else _identity_rot()
    n.scale = scale
    n.children = children or []
    n.num_children = len(n.children)
    return n


def _table(blocks: list[Any], names: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        blocks=blocks,
        header=SimpleNamespace(
            strings=[SizedString(length=len(s), value=list(s.encode("latin-1"))) for s in names],
        ),
    )


# ---- decoder: tree walk ---------------------------------------------------


def test_single_root_node_becomes_one_bone() -> None:
    root = _node(name_idx=0, translation=(1.0, 2.0, 3.0))
    table = _table([root], ["Root"])

    arm = ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]

    assert arm.name == "Root"
    assert len(arm.bones) == 1
    bone = arm.bones[0]
    assert bone.name == "Root"
    assert bone.parent == -1
    assert bone.source_block_index == 0
    np.testing.assert_array_almost_equal(bone.local_matrix[:3, 3], [1.0, 2.0, 3.0])
    np.testing.assert_array_almost_equal(bone.world_matrix, bone.local_matrix)


def test_parent_child_world_matrix_is_composed() -> None:
    # Root translates +X by 10; child translates +Y by 5 in its local frame.
    # Identity rotations everywhere, so the child's world translation is
    # (10, 5, 0).
    root = _node(name_idx=0, translation=(10.0, 0.0, 0.0), children=[1])
    child = _node(name_idx=1, translation=(0.0, 5.0, 0.0))
    table = _table([root, child], ["Root", "Child"])

    arm = ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]

    assert [b.name for b in arm.bones] == ["Root", "Child"]
    assert arm.bones[1].parent == 0
    np.testing.assert_array_almost_equal(
        arm.bones[1].world_matrix[:3, 3], [10.0, 5.0, 0.0]
    )
    # Local matrix is unchanged from the source NiNode.
    np.testing.assert_array_almost_equal(
        arm.bones[1].local_matrix[:3, 3], [0.0, 5.0, 0.0]
    )


def test_skip_root_drops_top_level_node_but_keeps_children() -> None:
    root = _node(name_idx=0, translation=(100.0, 0.0, 0.0), children=[1, 2])
    a = _node(name_idx=1, translation=(1.0, 0.0, 0.0))
    b = _node(name_idx=2, translation=(2.0, 0.0, 0.0))
    table = _table([root, a, b], ["SceneRoot", "BoneA", "BoneB"])

    arm = ninode_tree_to_armature_data(table, 0, skip_root=True)  # type: ignore[arg-type]

    assert [bone.name for bone in arm.bones] == ["BoneA", "BoneB"]
    assert all(bone.parent == -1 for bone in arm.bones)
    # Root translation still propagates into the children's world matrices
    # via parent_world.
    np.testing.assert_array_almost_equal(
        arm.bones[0].world_matrix[:3, 3], [101.0, 0.0, 0.0]
    )


def test_non_ninode_children_are_skipped() -> None:
    # A child reference that points at a non-NiNode block (here a bare
    # SimpleNamespace) is silently ignored — the bridge produces bones,
    # not the full scene graph.
    root = _node(name_idx=0, children=[1, 2])
    child = _node(name_idx=1)
    table = _table([root, child, SimpleNamespace()], ["Root", "Child", "Mesh"])

    arm = ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]

    assert [b.name for b in arm.bones] == ["Root", "Child"]


def test_invalid_child_refs_are_tolerated() -> None:
    root = _node(name_idx=0, children=[0xFFFFFFFF, -1, 99])
    table = _table([root], ["Root"])
    arm = ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]
    assert len(arm.bones) == 1


def test_root_must_be_ninode() -> None:
    table = _table([SimpleNamespace()], ["Mesh"])
    with pytest.raises(TypeError):
        ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]


def test_uniform_scale_lifted_into_local_matrix() -> None:
    root = _node(name_idx=0, scale=2.5)
    table = _table([root], ["Root"])
    arm = ninode_tree_to_armature_data(table, 0)  # type: ignore[arg-type]
    rot = arm.bones[0].local_matrix[:3, :3]
    np.testing.assert_array_almost_equal(rot, np.eye(3) * 2.5)


# ---- Blender wrapper ------------------------------------------------------


class _FakeEditBone:
    def __init__(self, name: str) -> None:
        self.name = name
        self.head: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.tail: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.parent: _FakeEditBone | None = None


class _FakeEditBones:
    def __init__(self) -> None:
        self.bones: list[_FakeEditBone] = []

    def new(self, name: str) -> _FakeEditBone:
        eb = _FakeEditBone(name)
        self.bones.append(eb)
        return eb


class _FakeBoneCollection:
    def __init__(self) -> None:
        self._items: dict[str, SimpleNamespace] = {}

    def get(self, name: str) -> SimpleNamespace | None:
        return self._items.setdefault(name, SimpleNamespace(name=name))

    def __getitem__(self, name: str) -> SimpleNamespace:
        return self.get(name)


class _FakeArmature:
    def __init__(self, name: str) -> None:
        self.name = name
        self.edit_bones = _FakeEditBones()
        self.bones = _FakeBoneCollection()


class _FakeArmatures:
    def __init__(self) -> None:
        self.created: list[_FakeArmature] = []

    def new(self, name: str) -> _FakeArmature:
        a = _FakeArmature(name)
        self.created.append(a)
        return a


class _FakeObject:
    def __init__(self, name: str, data: Any) -> None:
        self.name = name
        self.data = data


class _FakeObjects:
    def __init__(self) -> None:
        self.created: list[_FakeObject] = []

    def new(self, name: str, data: Any) -> _FakeObject:
        o = _FakeObject(name, data)
        self.created.append(o)
        return o


@pytest.fixture
def fake_bpy() -> SimpleNamespace:
    return SimpleNamespace(
        data=SimpleNamespace(
            armatures=_FakeArmatures(),
            objects=_FakeObjects(),
        ),
        context=SimpleNamespace(collection=None, view_layer=None),
        ops=None,
    )


def _simple_armature_data() -> ArmatureData:
    """Two-bone armature: root at origin, child translated along +Y by 1.5."""
    root_local = np.eye(4, dtype=np.float32)
    child_local = np.eye(4, dtype=np.float32)
    child_local[1, 3] = 1.5
    return ArmatureData(
        name="rig",
        bones=[
            BoneData(
                name="Root",
                parent=-1,
                local_matrix=root_local,
                world_matrix=root_local,
                source_block_index=0,
            ),
            BoneData(
                name="Child",
                parent=0,
                local_matrix=child_local,
                world_matrix=child_local,
                source_block_index=1,
            ),
        ],
    )


def test_blender_wrapper_creates_object_and_edit_bones(fake_bpy: Any) -> None:
    obj = armature_data_to_blender(_simple_armature_data(), bpy=fake_bpy)

    assert obj.name == "rig"
    assert obj.data.name == "rig"
    edit_bones = obj.data.edit_bones.bones
    assert [b.name for b in edit_bones] == ["Root", "Child"]
    assert edit_bones[1].parent is edit_bones[0]


def test_blender_wrapper_lays_out_head_and_tail_from_world_matrix(fake_bpy: Any) -> None:
    obj = armature_data_to_blender(_simple_armature_data(), bpy=fake_bpy)
    root, child = obj.data.edit_bones.bones

    # Root head sits at origin; tail extends along +Y by the distance to
    # the first child (= 1.5).
    assert root.head == pytest.approx((0.0, 0.0, 0.0))
    assert root.tail == pytest.approx((0.0, 1.5, 0.0))

    # Child has no children, so it falls back to DEFAULT_BONE_LENGTH.
    assert child.head == pytest.approx((0.0, 1.5, 0.0))
    assert child.tail == pytest.approx((0.0, 1.5 + DEFAULT_BONE_LENGTH, 0.0))


def test_blender_wrapper_stamps_bind_matrix_on_data_bones(fake_bpy: Any) -> None:
    data = _simple_armature_data()
    obj = armature_data_to_blender(data, bpy=fake_bpy)

    for bone in data.bones:
        data_bone = obj.data.bones[bone.name]
        stored = read_bind_matrix_from_props(data_bone)
        assert stored is not None
        np.testing.assert_array_equal(stored, bone.local_matrix)
