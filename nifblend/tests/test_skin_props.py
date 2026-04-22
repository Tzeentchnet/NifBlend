"""Unit tests for :mod:`nifblend.bridge.skin_props` (Phase 4 step 17)."""

from __future__ import annotations

from types import SimpleNamespace

from nifblend.bridge.skin_props import (
    PROP_ATTR,
    apply_partition_to_props,
    bodypart_lists_to_vertex_groups,
    clear_partition_on_props,
    read_partition_from_props,
    vertex_groups_to_bodypart_lists,
)
from nifblend.format.generated.structs import BodyPartList

# ---- fakes ---------------------------------------------------------------


class _FakeVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeVertexGroups:
    def __init__(self) -> None:
        self.created: list[_FakeVertexGroup] = []

    def new(self, *, name: str) -> _FakeVertexGroup:
        vg = _FakeVertexGroup(name)
        self.created.append(vg)
        return vg

    def __iter__(self):
        return iter(self.created)


class _FakeObject:
    def __init__(self) -> None:
        self.vertex_groups = _FakeVertexGroups()


# ---- apply / read --------------------------------------------------------


def test_apply_then_read_round_trips_pair() -> None:
    vg = SimpleNamespace(name="BP_0_30")
    apply_partition_to_props(vg, part_flag=0xABCD, body_part=30)

    pair = read_partition_from_props(vg)
    assert pair == (0xABCD, 30)
    props = getattr(vg, PROP_ATTR)
    assert props.is_partition is True
    assert props.part_flag == 0xABCD
    assert props.body_part == 30


def test_read_returns_none_when_not_a_partition() -> None:
    vg = SimpleNamespace(name="BoneA", nifblend=SimpleNamespace(is_partition=False))
    assert read_partition_from_props(vg) is None


def test_read_returns_none_when_no_propertygroup() -> None:
    assert read_partition_from_props(SimpleNamespace(name="x")) is None


def test_clear_resets_partition_marker() -> None:
    vg = SimpleNamespace(name="x")
    apply_partition_to_props(vg, part_flag=1, body_part=2)
    clear_partition_on_props(vg)
    assert read_partition_from_props(vg) is None
    assert getattr(vg, PROP_ATTR).part_flag == 0
    assert getattr(vg, PROP_ATTR).body_part == 0


def test_apply_clamps_to_u16() -> None:
    vg = SimpleNamespace(name="x")
    apply_partition_to_props(vg, part_flag=0x1_FFFF, body_part=0x2_0042)
    pair = read_partition_from_props(vg)
    assert pair == (0xFFFF, 0x0042)


# ---- end-to-end converters ----------------------------------------------


def test_bodypart_lists_to_vertex_groups_creates_one_group_per_partition() -> None:
    obj = _FakeObject()
    parts = [
        BodyPartList(part_flag=0x0010, body_part=30),
        BodyPartList(part_flag=0x0020, body_part=31),
    ]

    groups = bodypart_lists_to_vertex_groups(parts, obj)

    assert list(groups) == ["BP_0_30", "BP_1_31"]
    assert [vg.name for vg in obj.vertex_groups.created] == ["BP_0_30", "BP_1_31"]
    assert read_partition_from_props(groups["BP_0_30"]) == (0x0010, 30)
    assert read_partition_from_props(groups["BP_1_31"]) == (0x0020, 31)


def test_bodypart_lists_to_vertex_groups_skips_none_entries() -> None:
    obj = _FakeObject()
    parts = [BodyPartList(part_flag=1, body_part=2), None]
    groups = bodypart_lists_to_vertex_groups(parts, obj)
    assert list(groups) == ["BP_0_2"]


def test_vertex_groups_to_bodypart_lists_round_trips() -> None:
    obj = _FakeObject()
    parts_in = [
        BodyPartList(part_flag=0x0001, body_part=30),
        BodyPartList(part_flag=0x0002, body_part=32),
        BodyPartList(part_flag=0x0004, body_part=33),
    ]
    bodypart_lists_to_vertex_groups(parts_in, obj)
    # Add a non-partition bone-weight group; it must be skipped.
    obj.vertex_groups.new(name="BoneA")

    parts_out = vertex_groups_to_bodypart_lists(obj.vertex_groups)

    assert len(parts_out) == 3
    assert [(p.part_flag, p.body_part) for p in parts_out] == [
        (0x0001, 30),
        (0x0002, 32),
        (0x0004, 33),
    ]


def test_vertex_groups_to_bodypart_lists_accepts_mapping() -> None:
    obj = _FakeObject()
    groups = bodypart_lists_to_vertex_groups(
        [BodyPartList(part_flag=5, body_part=6)], obj
    )
    parts = vertex_groups_to_bodypart_lists(groups)
    assert len(parts) == 1
    assert (parts[0].part_flag, parts[0].body_part) == (5, 6)


def test_vertex_groups_to_bodypart_lists_returns_empty_for_no_partitions() -> None:
    obj = _FakeObject()
    obj.vertex_groups.new(name="BoneA")
    obj.vertex_groups.new(name="BoneB")
    assert vertex_groups_to_bodypart_lists(obj.vertex_groups) == []
