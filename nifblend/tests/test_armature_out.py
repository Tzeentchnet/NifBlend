"""Unit tests for :mod:`nifblend.bridge.armature_out` (Phase 4 step 16)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from nifblend.bridge.armature_out import (
    BoneLimits,
    bone_limits_for,
    build_ni_skin_data,
    build_ni_skin_instance,
    build_skin_partitions,
    skin_partitions_to_block,
)
from nifblend.bridge.skin_in import (
    SkinData,
    bstrishape_skin_to_skin_data,
    niskin_to_skin_data,
)
from nifblend.format.generated.blocks import (
    BSDismemberSkinInstance,
    NiNode,
    NiSkinData,
    NiSkinInstance,
    NiSkinPartition,
)
from nifblend.format.generated.structs import (
    SizedString,
    Vector3,
)
from nifblend.format.generated.structs import string as nif_string
from nifblend.format.versions import GameProfile

# ---- helpers --------------------------------------------------------------


def _skin(
    bone_names: list[str],
    triples: list[tuple[int, int, float]],
) -> SkinData:
    """Build a SkinData from a flat (vertex, bone, weight) triple list."""
    if triples:
        verts = np.asarray([t[0] for t in triples], dtype=np.uint32)
        bones = np.asarray([t[1] for t in triples], dtype=np.uint32)
        weights = np.asarray([t[2] for t in triples], dtype=np.float32)
    else:
        verts = np.empty(0, dtype=np.uint32)
        bones = np.empty(0, dtype=np.uint32)
        weights = np.empty(0, dtype=np.float32)
    return SkinData(
        bone_names=list(bone_names),
        vertex_indices=verts,
        bone_indices=bones,
        weights=weights,
    )


# ---- bone_limits_for -----------------------------------------------------


@pytest.mark.parametrize(
    "profile,expected_bones,expected_weights",
    [
        (GameProfile.SKYRIM_LE, 80, 4),
        (GameProfile.SKYRIM_SE, 80, 4),
        (GameProfile.FALLOUT_4, 80, 8),
        (GameProfile.FALLOUT_76, 100, 8),
        (GameProfile.OBLIVION, 18, 4),
        (GameProfile.MORROWIND, 4, 4),
        (GameProfile.UNKNOWN, 80, 4),  # conservative SSE default
    ],
)
def test_bone_limits_for_known_profiles(
    profile: GameProfile, expected_bones: int, expected_weights: int
) -> None:
    limits = bone_limits_for(profile)
    assert limits.max_bones_per_partition == expected_bones
    assert limits.max_weights_per_vertex == expected_weights


# ---- build_skin_partitions: packing & limits -----------------------------


def test_single_triangle_under_caps_yields_one_partition() -> None:
    skin = _skin(["A", "B"], [(0, 0, 1.0), (1, 0, 0.5), (1, 1, 0.5), (2, 1, 1.0)])
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2]],
        num_vertices=3,
        limits=BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    )
    assert len(parts) == 1
    p = parts[0]
    np.testing.assert_array_equal(p.vertex_map, [0, 1, 2])
    np.testing.assert_array_equal(p.triangles, [[0, 1, 2]])
    np.testing.assert_array_equal(p.bones, [0, 1])
    # bone slots: v0 -> A only, v1 -> A+B, v2 -> B only.
    assert p.bone_indices.shape == (3, 4)
    assert p.vertex_weights.shape == (3, 4)
    np.testing.assert_array_almost_equal(p.vertex_weights[:, 0], [1.0, 0.5, 1.0])


def test_partition_split_when_bone_cap_exceeded() -> None:
    # Triangle 0 uses bones {0,1,2}; triangle 1 uses bones {3,4,5}.
    # With cap=3 they cannot share a partition.
    skin = _skin(
        ["b0", "b1", "b2", "b3", "b4", "b5"],
        [
            (0, 0, 1.0),
            (1, 1, 1.0),
            (2, 2, 1.0),
            (3, 3, 1.0),
            (4, 4, 1.0),
            (5, 5, 1.0),
        ],
    )
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2], [3, 4, 5]],
        num_vertices=6,
        limits=BoneLimits(max_bones_per_partition=3, max_weights_per_vertex=4),
    )
    assert len(parts) == 2
    np.testing.assert_array_equal(parts[0].bones, [0, 1, 2])
    np.testing.assert_array_equal(parts[1].bones, [3, 4, 5])
    np.testing.assert_array_equal(parts[0].vertex_map, [0, 1, 2])
    np.testing.assert_array_equal(parts[1].vertex_map, [3, 4, 5])


def test_partition_packs_compatible_triangles_together() -> None:
    # Both triangles share the same 3 bones -> single partition.
    skin = _skin(
        ["a", "b", "c"],
        [
            (0, 0, 1.0),
            (1, 1, 1.0),
            (2, 2, 1.0),
            (3, 0, 1.0),
            (4, 1, 1.0),
            (5, 2, 1.0),
        ],
    )
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2], [3, 4, 5]],
        num_vertices=6,
        limits=BoneLimits(max_bones_per_partition=3, max_weights_per_vertex=4),
    )
    assert len(parts) == 1
    p = parts[0]
    assert p.triangles.shape == (2, 3)
    np.testing.assert_array_equal(p.bones, [0, 1, 2])
    # vertex_map enumerates the union of vertices
    np.testing.assert_array_equal(sorted(p.vertex_map.tolist()), [0, 1, 2, 3, 4, 5])


def test_triangle_exceeding_cap_raises() -> None:
    skin = _skin(
        ["a", "b", "c", "d"],
        [(0, 0, 1.0), (1, 1, 1.0), (2, 2, 1.0)],  # tri 0 needs {0,1,2}
    )
    with pytest.raises(ValueError, match="exceeds per-partition cap"):
        build_skin_partitions(
            skin,
            triangles=[[0, 1, 2]],
            num_vertices=3,
            limits=BoneLimits(max_bones_per_partition=2, max_weights_per_vertex=4),
        )


def test_invalid_limits_raise() -> None:
    skin = _skin(["a"], [(0, 0, 1.0)])
    with pytest.raises(ValueError, match="num_vertices must be positive"):
        build_skin_partitions(
            skin, triangles=[[0, 0, 0]], num_vertices=0,
            limits=BoneLimits(max_bones_per_partition=4, max_weights_per_vertex=4),
        )
    with pytest.raises(ValueError, match="max_bones_per_partition"):
        build_skin_partitions(
            skin, triangles=[[0, 0, 0]], num_vertices=1,
            limits=BoneLimits(max_bones_per_partition=0, max_weights_per_vertex=4),
        )
    with pytest.raises(ValueError, match="max_weights_per_vertex"):
        build_skin_partitions(
            skin, triangles=[[0, 0, 0]], num_vertices=1,
            limits=BoneLimits(max_bones_per_partition=4, max_weights_per_vertex=0),
        )


def test_empty_triangles_returns_empty_list() -> None:
    skin = _skin([], [])
    assert build_skin_partitions(
        skin,
        triangles=np.empty((0, 3), dtype=np.uint16),
        num_vertices=1,
        limits=BoneLimits(max_bones_per_partition=4, max_weights_per_vertex=4),
    ) == []


# ---- per-vertex influence pruning + renormalisation ----------------------


def test_extra_influences_pruned_and_renormalised() -> None:
    # vertex 0 sees 5 bones; max_weights=4 -> drop the lowest, renormalise.
    skin = _skin(
        ["a", "b", "c", "d", "e"],
        [
            (0, 0, 0.4),
            (0, 1, 0.3),
            (0, 2, 0.2),
            (0, 3, 0.05),
            (0, 4, 0.05),  # lowest, should be dropped
            (1, 0, 1.0),
            (2, 0, 1.0),
        ],
    )
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2]],
        num_vertices=3,
        limits=BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    )
    assert len(parts) == 1
    p = parts[0]
    # vertex 0 is local index 0 (vertex_map sorted 0,1,2)
    v0_weights = p.vertex_weights[0]
    # lowest of the 5 (0.05 on bone 4) was dropped; survivors renormalised
    assert pytest.approx(float(v0_weights.sum()), rel=1e-5) == 1.0
    # bone 4 should not be in the local palette for v0 (it kept top 4)
    used_local = p.bone_indices[0, v0_weights > 0]
    used_global = p.bones[used_local]
    assert 4 not in used_global.tolist()


# ---- skin_partitions_to_block --------------------------------------------


def test_skin_partitions_to_block_populates_compound_fields() -> None:
    skin = _skin(["a", "b"], [(0, 0, 1.0), (1, 1, 1.0), (2, 0, 1.0)])
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2]],
        num_vertices=3,
        limits=BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    )
    block = skin_partitions_to_block(parts, num_weights_per_vertex=4)
    assert isinstance(block, NiSkinPartition)
    assert block.num_partitions == 1
    sp = block.partitions[0]
    assert sp.num_vertices == 3
    assert sp.num_triangles == 1
    assert sp.num_bones == 2
    assert sp.num_weights_per_vertex == 4
    assert sp.has_vertex_map is True
    assert sp.has_vertex_weights is True
    assert sp.has_bone_indices is True
    assert sp.has_faces is True
    np.testing.assert_array_equal(sp.bones, [0, 1])
    np.testing.assert_array_equal(sp.vertex_map, [0, 1, 2])
    # flat weights = N * num_weights_per_vertex
    assert sp.vertex_weights.size == 3 * 4
    assert len(sp.bone_indices) == 3 * 4
    assert len(sp.triangles) == 1
    t = sp.triangles[0]
    assert (t.v1, t.v2, t.v3) == (0, 1, 2)


# ---- build_ni_skin_data: round-trip through skin_in ----------------------


def _named_node(name_idx: int) -> NiNode:
    n = NiNode()
    n.name = nif_string(index=name_idx)
    n.translation = Vector3(0.0, 0.0, 0.0)
    n.scale = 1.0
    n.children = []
    n.num_children = 0
    return n


def _table(blocks: list, names: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        blocks=blocks,
        header=SimpleNamespace(
            strings=[
                SizedString(length=len(s), value=list(s.encode("latin-1")))
                for s in names
            ],
        ),
    )


def test_build_ni_skin_data_inverse_of_niskin_decoder() -> None:
    skin = _skin(
        ["BoneA", "BoneB"],
        [(0, 0, 1.0), (1, 0, 0.5), (1, 1, 0.5), (2, 1, 1.0)],
    )
    block = build_ni_skin_data(skin)
    assert isinstance(block, NiSkinData)
    assert block.num_bones == 2
    assert block.has_vertex_weights is True
    assert len(block.bone_list) == 2

    # bone 0 has v0 (1.0), v1 (0.5); bone 1 has v1 (0.5), v2 (1.0)
    assert block.bone_list[0].num_vertices == 2
    assert [(v.index, v.weight) for v in block.bone_list[0].vertex_weights] == [
        (0, 1.0),
        (1, 0.5),
    ]
    assert [(v.index, v.weight) for v in block.bone_list[1].vertex_weights] == [
        (1, 0.5),
        (2, 1.0),
    ]

    # Plug into a fake table and roundtrip back through niskin_to_skin_data.
    bone_a = _named_node(0)
    bone_b = _named_node(1)
    inst = build_ni_skin_instance(skin, data_ref=3, bone_block_refs=[0, 1])
    table = _table([bone_a, bone_b, SimpleNamespace(), block, inst], ["BoneA", "BoneB"])
    decoded = niskin_to_skin_data(table, 4)
    assert decoded.bone_names == ["BoneA", "BoneB"]
    np.testing.assert_array_equal(decoded.vertex_indices, [0, 1, 1, 2])
    np.testing.assert_array_equal(decoded.bone_indices, [0, 0, 1, 1])
    np.testing.assert_array_almost_equal(decoded.weights, [1.0, 0.5, 0.5, 1.0])


def test_build_ni_skin_data_empty_palette() -> None:
    block = build_ni_skin_data(_skin([], []))
    assert block.num_bones == 0
    assert block.bone_list == []


def test_build_ni_skin_data_keeps_empty_bone_slot() -> None:
    # Bone B has no weights but must still occupy palette slot 1.
    skin = _skin(["A", "B"], [(0, 0, 1.0)])
    block = build_ni_skin_data(skin)
    assert block.num_bones == 2
    assert block.bone_list[0].num_vertices == 1
    assert block.bone_list[1].num_vertices == 0
    assert block.bone_list[1].vertex_weights == []


# ---- build_ni_skin_instance ----------------------------------------------


def test_build_ni_skin_instance_default_refs_are_null() -> None:
    skin = _skin(["a", "b"], [])
    inst = build_ni_skin_instance(skin)
    assert isinstance(inst, NiSkinInstance)
    assert inst.data == 0xFFFFFFFF
    assert inst.skin_partition == 0xFFFFFFFF
    assert inst.skeleton_root == 0xFFFFFFFF
    assert inst.num_bones == 2
    assert inst.bones == [0xFFFFFFFF, 0xFFFFFFFF]


def test_build_ni_skin_instance_dismember_variant() -> None:
    skin = _skin(["a"], [])
    inst = build_ni_skin_instance(
        skin, data_ref=1, partition_ref=2, skeleton_root_ref=0,
        bone_block_refs=[5], dismember=True,
    )
    assert isinstance(inst, BSDismemberSkinInstance)
    assert inst.data == 1
    assert inst.skin_partition == 2
    assert inst.skeleton_root == 0
    assert inst.bones == [5]
    assert inst.num_partitions == 0
    assert inst.partitions == []


def test_build_ni_skin_instance_ref_count_mismatch_raises() -> None:
    skin = _skin(["a", "b", "c"], [])
    with pytest.raises(ValueError, match="length 2 != bone palette size 3"):
        build_ni_skin_instance(skin, bone_block_refs=[0, 1])


# ---- end-to-end: build partitions + decode SSE-style per-vertex ----------


def test_partitions_round_trip_through_sse_per_vertex_decoder() -> None:
    """build_skin_partitions output -> per-vertex bone_indices/bone_weights
    arrays mimicking BSVertexDataSSE -> bstrishape_skin_to_skin_data."""
    skin = _skin(
        ["A", "B", "C"],
        [
            (0, 0, 1.0),
            (1, 0, 0.5),
            (1, 1, 0.5),
            (2, 1, 1.0),
            (3, 2, 1.0),
        ],
    )
    parts = build_skin_partitions(
        skin,
        triangles=[[0, 1, 2], [1, 2, 3]],
        num_vertices=4,
        limits=BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    )
    assert len(parts) == 1
    p = parts[0]
    # Synthesise BSVertexDataSSE-shaped per-vertex records using the
    # global bone palette indices (what the SSE decoder expects).
    global_bone_idx = p.bones[p.bone_indices]  # (N, 4) global ids
    vertex_data: list[SimpleNamespace] = []
    # The partition's vertex_map ordering may not match the original
    # vertex order; rebuild a dense (num_vertices, 4) table indexed by
    # original vertex id.
    dense_idx = np.zeros((4, 4), dtype=np.uint32)
    dense_wt = np.zeros((4, 4), dtype=np.float32)
    for local_v, global_v in enumerate(p.vertex_map.tolist()):
        dense_idx[global_v] = global_bone_idx[local_v]
        dense_wt[global_v] = p.vertex_weights[local_v]
    for i in range(4):
        vertex_data.append(
            SimpleNamespace(
                bone_indices=dense_idx[i].tolist(),
                bone_weights=dense_wt[i].tolist(),
            )
        )

    bone_a, bone_b, bone_c = _named_node(0), _named_node(1), _named_node(2)
    inst = build_ni_skin_instance(skin, bone_block_refs=[0, 1, 2])
    shape = SimpleNamespace(skin=4, vertex_data=vertex_data)
    table = _table(
        [bone_a, bone_b, bone_c, SimpleNamespace(), inst],
        ["A", "B", "C"],
    )
    decoded = bstrishape_skin_to_skin_data(table, shape)
    assert decoded.bone_names == ["A", "B", "C"]
    # Reconstruct (vertex, bone, weight) set from decoded arrays and
    # compare against the input triples (order-independent).
    decoded_set = {
        (int(v), int(b), round(float(w), 5))
        for v, b, w in zip(
            decoded.vertex_indices,
            decoded.bone_indices,
            decoded.weights,
            strict=True,
        )
    }
    expected_set = {
        (0, 0, 1.0),
        (1, 0, 0.5),
        (1, 1, 0.5),
        (2, 1, 1.0),
        (3, 2, 1.0),
    }
    assert decoded_set == expected_set
