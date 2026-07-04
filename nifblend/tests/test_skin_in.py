"""Unit tests for :mod:`nifblend.bridge.skin_in` (Phase 4 step 15)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np

from nifblend.bridge.skin_in import (
    SkinData,
    apply_skin_to_object,
    bstrishape_skin_to_skin_data,
    niskin_to_skin_data,
    skin_data_from_vertex_groups,
)
from nifblend.format.generated.blocks import (
    BSDismemberSkinInstance,
    NiNode,
    NiSkinData,
    NiSkinInstance,
)
from nifblend.format.generated.structs import BoneData as NifBoneData
from nifblend.format.generated.structs import (
    BoneVertData,
    SizedString,
    Vector3,
)
from nifblend.format.generated.structs import string as nif_string

# ---- helpers --------------------------------------------------------------


def _named_node(name_idx: int) -> NiNode:
    n = NiNode()
    n.name = nif_string(index=name_idx)
    n.translation = Vector3(0.0, 0.0, 0.0)
    n.scale = 1.0
    n.children = []
    n.num_children = 0
    return n


def _bone_data(weights: list[tuple[int, float]]) -> NifBoneData:
    bd = NifBoneData()
    bd.num_vertices = len(weights)
    bd.vertex_weights = [BoneVertData(index=int(i), weight=float(w)) for i, w in weights]
    return bd


def _skin_data(per_bone: list[list[tuple[int, float]]]) -> NiSkinData:
    sd = NiSkinData()
    sd.num_bones = len(per_bone)
    sd.has_vertex_weights = True
    sd.bone_list = [_bone_data(w) for w in per_bone]
    return sd


def _table(blocks: list[Any], names: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        blocks=blocks,
        header=SimpleNamespace(
            strings=[SizedString(length=len(s), value=list(s.encode("latin-1"))) for s in names],
        ),
    )


# ---- decoder: classic NiSkinData -----------------------------------------


def test_niskin_decodes_per_bone_weights_into_flat_arrays() -> None:
    bone_a = _named_node(0)
    bone_b = _named_node(1)
    skin_data = _skin_data(
        [
            [(0, 1.0), (1, 0.5)],  # bone 0 -> v0 (full), v1 (half)
            [(1, 0.5), (2, 1.0)],  # bone 1 -> v1 (half), v2 (full)
        ]
    )
    skin_inst = NiSkinInstance()
    skin_inst.data = 3
    skin_inst.bones = [0, 1]
    skin_inst.num_bones = 2
    table = _table([bone_a, bone_b, SimpleNamespace(), skin_data], ["BoneA", "BoneB"])
    table.blocks.append(skin_inst)
    inst_idx = len(table.blocks) - 1

    skin = niskin_to_skin_data(table, inst_idx)  # type: ignore[arg-type]

    assert skin.bone_names == ["BoneA", "BoneB"]
    # Order: bone 0's two entries, then bone 1's two entries.
    np.testing.assert_array_equal(skin.vertex_indices, [0, 1, 1, 2])
    np.testing.assert_array_equal(skin.bone_indices, [0, 0, 1, 1])
    np.testing.assert_array_almost_equal(skin.weights, [1.0, 0.5, 0.5, 1.0])


def test_niskin_drops_zero_weight_entries() -> None:
    bone = _named_node(0)
    skin_data = _skin_data([[(0, 1.0), (1, 0.0), (2, 0.25)]])
    skin_inst = NiSkinInstance()
    skin_inst.data = 1
    skin_inst.bones = [0]
    skin_inst.num_bones = 1
    table = _table([bone, skin_data, skin_inst], ["Bone"])

    skin = niskin_to_skin_data(table, 2)  # type: ignore[arg-type]

    np.testing.assert_array_equal(skin.vertex_indices, [0, 2])
    np.testing.assert_array_almost_equal(skin.weights, [1.0, 0.25])


def test_niskin_handles_missing_data_block() -> None:
    bone = _named_node(0)
    skin_inst = NiSkinInstance()
    skin_inst.data = -1
    skin_inst.bones = [0]
    skin_inst.num_bones = 1
    table = _table([bone, skin_inst], ["Bone"])

    skin = niskin_to_skin_data(table, 1)  # type: ignore[arg-type]

    assert skin.bone_names == ["Bone"]
    assert skin.vertex_indices.size == 0
    assert skin.bone_indices.size == 0
    assert skin.weights.size == 0


def test_niskin_falls_back_to_placeholder_for_unresolvable_bones() -> None:
    # Bone ref 99 is out of range; ref 0 points to a non-NiNode placeholder.
    skin_data = _skin_data([[(0, 1.0)], []])
    skin_inst = NiSkinInstance()
    skin_inst.data = 1
    skin_inst.bones = [0, 99]
    skin_inst.num_bones = 2
    table = _table([SimpleNamespace(), skin_data, skin_inst], [])

    skin = niskin_to_skin_data(table, 2)  # type: ignore[arg-type]

    assert skin.bone_names == ["Bone.0", "Bone.1"]


def test_niskin_accepts_bsdismember_skin_instance() -> None:
    bone = _named_node(0)
    skin_data = _skin_data([[(0, 1.0)]])
    inst = BSDismemberSkinInstance()
    inst.data = 1
    inst.bones = [0]
    inst.num_bones = 1
    inst.partitions = []
    table = _table([bone, skin_data, inst], ["Bone"])

    skin = niskin_to_skin_data(table, 2)  # type: ignore[arg-type]

    assert skin.bone_names == ["Bone"]
    np.testing.assert_array_equal(skin.vertex_indices, [0])


# ---- decoder: SSE/FO4 per-vertex weights ---------------------------------


def _vertex(indices: list[int], weights: list[float]) -> SimpleNamespace:
    return SimpleNamespace(bone_indices=indices, bone_weights=weights)


def test_bstrishape_skin_decodes_per_vertex_weights() -> None:
    bone_a = _named_node(0)
    bone_b = _named_node(1)
    skin_inst = NiSkinInstance()
    skin_inst.bones = [0, 1]
    skin_inst.num_bones = 2
    skin_inst.data = -1
    table = _table([bone_a, bone_b, skin_inst], ["BoneA", "BoneB"])

    shape = SimpleNamespace(
        skin=2,
        vertex_data=[
            _vertex([0, 1, 0, 0], [0.75, 0.25, 0.0, 0.0]),
            _vertex([1, 0, 0, 0], [1.0, 0.0, 0.0, 0.0]),
        ],
    )

    skin = bstrishape_skin_to_skin_data(table, shape)  # type: ignore[arg-type]

    assert skin.bone_names == ["BoneA", "BoneB"]
    # v0: 0.75 -> bone 0, 0.25 -> bone 1
    # v1: 1.0  -> bone 1
    np.testing.assert_array_equal(skin.vertex_indices, [0, 0, 1])
    np.testing.assert_array_equal(skin.bone_indices, [0, 1, 1])
    np.testing.assert_array_almost_equal(skin.weights, [0.75, 0.25, 1.0])


def test_bstrishape_skin_with_no_skin_instance_returns_empty_palette() -> None:
    shape = SimpleNamespace(
        skin=-1,
        vertex_data=[_vertex([0, 0, 0, 0], [1.0, 0.0, 0.0, 0.0])],
    )
    table = _table([], [])
    skin = bstrishape_skin_to_skin_data(table, shape)  # type: ignore[arg-type]
    # Vertex weights are still present (palette index 0), but no names
    # are resolved; the wrapper would skip the orphaned weights.
    assert skin.bone_names == []
    np.testing.assert_array_equal(skin.bone_indices, [0])


def test_bstrishape_skin_handles_empty_vertex_data() -> None:
    table = _table([], [])
    skin = bstrishape_skin_to_skin_data(
        table,  # type: ignore[arg-type]
        SimpleNamespace(skin=-1, vertex_data=[]),
    )
    assert skin.weights.size == 0


# ---- Blender wrapper ------------------------------------------------------


class _FakeVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[list[int], float, str]] = []

    def add(self, indices: list[int], weight: float, mode: str) -> None:
        self.calls.append((list(indices), float(weight), mode))


class _FakeVertexGroups:
    def __init__(self) -> None:
        self.created: list[_FakeVertexGroup] = []

    def new(self, *, name: str) -> _FakeVertexGroup:
        vg = _FakeVertexGroup(name)
        self.created.append(vg)
        return vg


class _FakeObject:
    def __init__(self) -> None:
        self.vertex_groups = _FakeVertexGroups()


def test_apply_skin_creates_one_group_per_bone_even_when_empty() -> None:
    obj = _FakeObject()
    skin = SkinData(bone_names=["BoneA", "BoneB", "BoneC"])

    groups = apply_skin_to_object(skin, obj)

    assert list(groups) == ["BoneA", "BoneB", "BoneC"]
    assert [vg.name for vg in obj.vertex_groups.created] == [
        "BoneA",
        "BoneB",
        "BoneC",
    ]
    assert all(not vg.calls for vg in obj.vertex_groups.created)


def test_apply_skin_buckets_vertices_by_unique_weight_per_bone() -> None:
    obj = _FakeObject()
    skin = SkinData(
        bone_names=["BoneA", "BoneB"],
        vertex_indices=np.array([0, 1, 2, 3, 4], dtype=np.uint32),
        bone_indices=np.array([0, 0, 1, 1, 1], dtype=np.uint32),
        weights=np.array([1.0, 1.0, 0.5, 1.0, 0.5], dtype=np.float32),
    )

    apply_skin_to_object(skin, obj)

    by_name = {vg.name: vg for vg in obj.vertex_groups.created}
    # Bone A: both verts share weight 1.0 -> one ``add`` call.
    assert by_name["BoneA"].calls == [([0, 1], 1.0, "REPLACE")]
    # Bone B: weights {0.5, 1.0} bucketed; numpy.unique sorts ascending
    # so 0.5 bucket comes first.
    assert by_name["BoneB"].calls == [
        ([2, 4], 0.5, "REPLACE"),
        ([3], 1.0, "REPLACE"),
    ]


def test_apply_skin_skips_palette_indices_out_of_range() -> None:
    obj = _FakeObject()
    skin = SkinData(
        bone_names=["BoneA"],
        vertex_indices=np.array([0, 1], dtype=np.uint32),
        bone_indices=np.array([0, 5], dtype=np.uint32),
        weights=np.array([1.0, 1.0], dtype=np.float32),
    )

    apply_skin_to_object(skin, obj)

    assert obj.vertex_groups.created[0].calls == [([0], 1.0, "REPLACE")]


# ---- end-to-end: decode + apply ------------------------------------------


def test_niskin_decode_and_apply_round_trip_into_vertex_groups() -> None:
    bone_a = _named_node(0)
    bone_b = _named_node(1)
    skin_data = _skin_data(
        [
            [(0, 1.0), (1, 0.5)],
            [(1, 0.5), (2, 1.0)],
        ]
    )
    skin_inst = NiSkinInstance()
    skin_inst.data = 2
    skin_inst.bones = [0, 1]
    skin_inst.num_bones = 2
    table = _table([bone_a, bone_b, skin_data, skin_inst], ["BoneA", "BoneB"])

    skin = niskin_to_skin_data(table, 3)  # type: ignore[arg-type]
    obj = _FakeObject()
    apply_skin_to_object(skin, obj)

    by_name = {vg.name: vg for vg in obj.vertex_groups.created}
    assert sorted(by_name) == ["BoneA", "BoneB"]
    assert by_name["BoneA"].calls == [
        ([1], 0.5, "REPLACE"),
        ([0], 1.0, "REPLACE"),
    ]
    assert by_name["BoneB"].calls == [
        ([1], 0.5, "REPLACE"),
        ([2], 1.0, "REPLACE"),
    ]


# ---- skin_data_from_vertex_groups (Phase 5 step 16, export direction) ----


class _FakeExportVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeGroupElement:
    def __init__(self, group: int, weight: float) -> None:
        self.group = group
        self.weight = weight


class _FakeVertex:
    def __init__(self, index: int, groups: list[_FakeGroupElement]) -> None:
        self.index = index
        self.groups = groups


class _FakeExportObject:
    def __init__(self, vertex_group_names: list[str], vertices: list[_FakeVertex]) -> None:
        self.vertex_groups = [_FakeExportVertexGroup(n) for n in vertex_group_names]
        self.data = SimpleNamespace(vertices=vertices)


def test_skin_data_from_vertex_groups_harvests_named_groups_only() -> None:
    obj = _FakeExportObject(
        vertex_group_names=["BoneA", "BoneB", "NotABone"],
        vertices=[
            _FakeVertex(0, [_FakeGroupElement(0, 1.0)]),
            _FakeVertex(1, [_FakeGroupElement(0, 0.5), _FakeGroupElement(1, 0.5)]),
            _FakeVertex(2, [_FakeGroupElement(2, 1.0)]),  # "NotABone" -- excluded
        ],
    )

    skin = skin_data_from_vertex_groups(obj, ["BoneA", "BoneB"])

    assert skin.bone_names == ["BoneA", "BoneB"]
    triples = {
        (int(v), int(b), round(float(w), 5))
        for v, b, w in zip(skin.vertex_indices, skin.bone_indices, skin.weights, strict=True)
    }
    assert triples == {(0, 0, 1.0), (1, 0, 0.5), (1, 1, 0.5)}


def test_skin_data_from_vertex_groups_drops_zero_and_negative_weights() -> None:
    obj = _FakeExportObject(
        vertex_group_names=["BoneA"],
        vertices=[
            _FakeVertex(0, [_FakeGroupElement(0, 0.0)]),
            _FakeVertex(1, [_FakeGroupElement(0, -0.1)]),
            _FakeVertex(2, [_FakeGroupElement(0, 1.0)]),
        ],
    )
    skin = skin_data_from_vertex_groups(obj, ["BoneA"])
    assert skin.vertex_indices.tolist() == [2]
    assert skin.weights.tolist() == [1.0]


def test_skin_data_from_vertex_groups_empty_when_no_bone_names_match() -> None:
    obj = _FakeExportObject(
        vertex_group_names=["Unrelated"],
        vertices=[_FakeVertex(0, [_FakeGroupElement(0, 1.0)])],
    )
    skin = skin_data_from_vertex_groups(obj, ["BoneA"])
    assert skin.bone_names == ["BoneA"]
    assert skin.vertex_indices.size == 0


def test_skin_data_from_vertex_groups_round_trips_through_apply() -> None:
    """apply_skin_to_object -> skin_data_from_vertex_groups should recover
    the same (vertex, bone, weight) triples that were applied."""
    original = SkinData(
        bone_names=["BoneA", "BoneB"],
        vertex_indices=np.array([0, 1, 2], dtype=np.uint32),
        bone_indices=np.array([0, 0, 1], dtype=np.uint32),
        weights=np.array([1.0, 0.5, 1.0], dtype=np.float32),
    )
    obj = _FakeObject()
    apply_skin_to_object(original, obj)

    # Adapt the apply-side fake into the shape skin_data_from_vertex_groups
    # expects (obj.data.vertices with per-vertex .groups).
    vg_names = [vg.name for vg in obj.vertex_groups.created]
    name_to_index = {n: i for i, n in enumerate(vg_names)}
    per_vertex: dict[int, list[_FakeGroupElement]] = {}
    for vg in obj.vertex_groups.created:
        gi = name_to_index[vg.name]
        for indices, weight, _mode in vg.calls:
            for vi in indices:
                per_vertex.setdefault(vi, []).append(_FakeGroupElement(gi, weight))
    export_obj = _FakeExportObject(
        vertex_group_names=vg_names,
        vertices=[_FakeVertex(vi, groups) for vi, groups in sorted(per_vertex.items())],
    )

    recovered = skin_data_from_vertex_groups(export_obj, vg_names)
    original_set = {
        (int(v), int(b), round(float(w), 5))
        for v, b, w in zip(
            original.vertex_indices, original.bone_indices, original.weights, strict=True
        )
    }
    recovered_set = {
        (int(v), int(b), round(float(w), 5))
        for v, b, w in zip(
            recovered.vertex_indices, recovered.bone_indices, recovered.weights, strict=True
        )
    }
    assert recovered_set == original_set
