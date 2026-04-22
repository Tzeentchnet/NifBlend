"""Export side of the skin / skeleton bridge (Phase 4 step 16).

This module turns a :class:`~nifblend.bridge.skin_in.SkinData` (the
sparse vertex-group representation produced on import) plus a triangle
list back into NIF skin blocks:

* :func:`build_ni_skin_data` -- classic Morrowind .. Skyrim LE layout
  with per-bone ``BoneVertData`` lists. Inverse of
  :func:`nifblend.bridge.skin_in.niskin_to_skin_data`.
* :func:`build_ni_skin_instance` -- builds the ``NiSkinInstance`` (or
  ``BSDismemberSkinInstance`` / ``BSSkinInstance`` shell) carrying the
  bone palette and refs to data + partition + skeleton root.
* :func:`build_skin_partitions` and :func:`skin_partitions_to_block`
  -- the heart of step 16. Greedy-pack triangles into hardware-skinning
  partitions whose bone-union and per-vertex weight count respect the
  per-game limits returned by :func:`bone_limits_for`.

The module is pure (no ``bpy`` import) -- callers further up the export
pipeline (the operator) are responsible for cross-block ref patching
and for harvesting the upstream :class:`SkinData` from Blender vertex
groups via :mod:`nifblend.bridge.skin_in` / :mod:`mesh_out`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.blocks import (
    BSDismemberSkinInstance,
    NiSkinData,
    NiSkinInstance,
    NiSkinPartition,
)
from nifblend.format.generated.structs import (
    BoneVertData,
    Matrix33,
    NiBound,
    NiTransform,
    SkinPartition,
    Triangle,
    Vector3,
)
from nifblend.format.versions import GameProfile

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.bridge.skin_in import SkinData

__all__ = [
    "BoneLimits",
    "PartitionBuild",
    "bone_limits_for",
    "build_ni_skin_data",
    "build_ni_skin_instance",
    "build_skin_partitions",
    "skin_partitions_to_block",
]


_NULL_REF = 0xFFFFFFFF


# ---- per-game limits -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoneLimits:
    """Hardware-skinning limits for one game target.

    ``max_bones_per_partition`` caps the size of the bone palette used
    by any single :class:`SkinPartition`. ``max_weights_per_vertex``
    caps the number of (bone, weight) influences kept per vertex --
    extra influences are pruned by lowest weight and the surviving
    weights are renormalised.
    """

    max_bones_per_partition: int
    max_weights_per_vertex: int


#: Default per-game limits. Values match the conventions used by
#: NifSkope / pyffi / blender_niftools_addon. Skyrim LE / SSE share an
#: 80-bone partition cap with 4 weights/vertex; Fallout 4 / 76 raise
#: the partition cap to support the much larger creature skeletons.
_LIMITS: dict[GameProfile, BoneLimits] = {
    GameProfile.MORROWIND: BoneLimits(max_bones_per_partition=4, max_weights_per_vertex=4),
    GameProfile.OBLIVION: BoneLimits(max_bones_per_partition=18, max_weights_per_vertex=4),
    GameProfile.FALLOUT_3_NV: BoneLimits(max_bones_per_partition=18, max_weights_per_vertex=4),
    GameProfile.SKYRIM_LE: BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    GameProfile.SKYRIM_SE: BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4),
    GameProfile.FALLOUT_4: BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=8),
    GameProfile.FALLOUT_76: BoneLimits(max_bones_per_partition=100, max_weights_per_vertex=8),
}

#: Conservative fallback for unknown profiles -- matches Skyrim SE.
_DEFAULT_LIMITS = BoneLimits(max_bones_per_partition=80, max_weights_per_vertex=4)


def bone_limits_for(profile: GameProfile) -> BoneLimits:
    """Return the :class:`BoneLimits` recommended for ``profile``.

    Unknown profiles fall back to a conservative SSE-shaped default.
    """
    return _LIMITS.get(profile, _DEFAULT_LIMITS)


# ---- partition builder ---------------------------------------------------


@dataclass(slots=True)
class PartitionBuild:
    """One submesh ready to be serialised as a :class:`SkinPartition`.

    ``vertex_map`` is the global-vertex index for each local slot (so
    ``num_vertices = len(vertex_map)``). ``triangles`` are remapped into
    the local 0..num_vertices-1 space. ``bones`` is the palette of
    *global* bone indices (into the parent :class:`SkinData` palette);
    ``bone_indices[v, k]`` is a position in this local palette.
    """

    vertex_map: npt.NDArray[np.uint16] = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    triangles: npt.NDArray[np.uint16] = field(
        default_factory=lambda: np.empty((0, 3), dtype=np.uint16)
    )
    bones: npt.NDArray[np.uint16] = field(
        default_factory=lambda: np.empty(0, dtype=np.uint16)
    )
    #: ``(num_vertices, num_weights_per_vertex)`` u8 -- index into ``bones``.
    bone_indices: npt.NDArray[np.uint8] = field(
        default_factory=lambda: np.empty((0, 0), dtype=np.uint8)
    )
    #: ``(num_vertices, num_weights_per_vertex)`` f32 -- weights, sum == 1.0.
    vertex_weights: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 0), dtype=np.float32)
    )


def build_skin_partitions(
    skin: SkinData,
    triangles: npt.ArrayLike,
    num_vertices: int,
    *,
    limits: BoneLimits,
) -> list[PartitionBuild]:
    """Pack ``triangles`` into partitions respecting ``limits``.

    Algorithm: build a per-vertex (bone, weight) table capped at
    ``limits.max_weights_per_vertex`` (lowest weights pruned, survivors
    renormalised); collect the bone-set each triangle requires; greedy
    first-fit pack triangles into partitions whose union-bone-set stays
    within ``limits.max_bones_per_partition``. A single triangle whose
    own bone-set exceeds the cap raises :class:`ValueError`.
    """
    tris = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    if tris.size == 0:
        return []
    if num_vertices <= 0:
        raise ValueError(f"num_vertices must be positive (got {num_vertices})")
    if limits.max_bones_per_partition < 1:
        raise ValueError("max_bones_per_partition must be >= 1")
    if limits.max_weights_per_vertex < 1:
        raise ValueError("max_weights_per_vertex must be >= 1")

    per_vertex = _per_vertex_influences(
        skin, num_vertices, limits.max_weights_per_vertex
    )
    triangle_bones: list[frozenset[int]] = [
        frozenset(per_vertex[v1].keys() | per_vertex[v2].keys() | per_vertex[v3].keys())
        for v1, v2, v3 in tris.tolist()
    ]

    # Reject impossible triangles up-front so the packer can assume the
    # invariant holds for every candidate.
    cap = limits.max_bones_per_partition
    for ti, bones in enumerate(triangle_bones):
        if len(bones) > cap:
            raise ValueError(
                f"triangle {ti} touches {len(bones)} bones, exceeds "
                f"per-partition cap of {cap}"
            )

    # Greedy first-fit. Open partitions are kept as (mutable bone-set,
    # list-of-triangle-indices). For typical Bethesda meshes (a few
    # dozen to a few hundred triangles per partition) this is plenty
    # fast and produces tight packings; the optimal MIS-style packer
    # is overkill until profiling proves otherwise.
    open_parts: list[tuple[set[int], list[int]]] = []
    for ti, bones in enumerate(triangle_bones):
        placed = False
        for pset, ptris in open_parts:
            if len(pset | bones) <= cap:
                pset |= bones
                ptris.append(ti)
                placed = True
                break
        if not placed:
            open_parts.append((set(bones), [ti]))

    return [
        _materialise_partition(
            tris,
            triangle_indices=ptris,
            bone_set=pset,
            per_vertex=per_vertex,
            num_weights_per_vertex=limits.max_weights_per_vertex,
        )
        for pset, ptris in open_parts
    ]


def skin_partitions_to_block(
    parts: list[PartitionBuild],
    *,
    num_weights_per_vertex: int,
) -> NiSkinPartition:
    """Wrap :class:`PartitionBuild` instances in a :class:`NiSkinPartition`.

    The block is shaped for Skyrim LE (``vertex_data`` left empty since
    the GPU vertex buffer lives on the shape, not the partition). For
    Skyrim SE / FO4 callers should additionally populate
    :attr:`NiSkinPartition.vertex_desc` / ``vertex_data`` / ``data_size``
    / ``vertex_size`` from the corresponding :class:`BSTriShape` -- this
    function deliberately does not touch those fields so the partition
    builder stays game-neutral.
    """
    block = NiSkinPartition()
    block.num_partitions = len(parts)
    block.partitions = [
        _build_skin_partition_compound(p, num_weights_per_vertex=num_weights_per_vertex)
        for p in parts
    ]
    return block


# ---- classic NiSkinData / NiSkinInstance --------------------------------


def build_ni_skin_data(
    skin: SkinData,
    *,
    skin_transform: NiTransform | None = None,
) -> NiSkinData:
    """Build an :class:`NiSkinData` from ``skin``.

    The output is the inverse of :func:`niskin_to_skin_data`: per-bone
    ``vertex_weights`` lists are reconstructed by bucketing
    ``skin.bone_indices`` and emitting one :class:`BoneVertData` per
    non-zero weight. Empty bones get an empty ``vertex_weights`` list,
    not pruned -- the palette index has to line up with the parent
    :class:`NiSkinInstance.bones`.
    """
    block = NiSkinData()
    block.skin_transform = skin_transform if skin_transform is not None else _identity_transform()
    block.num_bones = len(skin.bone_names)
    block.has_vertex_weights = True
    block.skin_partition = _NULL_REF

    bone_lists: list[list[BoneVertData | None]] = [
        [] for _ in skin.bone_names
    ]
    if skin.weights.size:
        # numpy.argsort is stable and runs in C; the per-bone slicing
        # below avoids any python-level "find indices for bone i" loop.
        order = np.argsort(skin.bone_indices, kind="stable")
        sorted_bones = skin.bone_indices[order]
        sorted_verts = skin.vertex_indices[order]
        sorted_weights = skin.weights[order]
        boundaries = np.concatenate(
            ([0], np.flatnonzero(np.diff(sorted_bones)) + 1, [sorted_bones.size])
        )
        for k in range(boundaries.size - 1):
            start, end = int(boundaries[k]), int(boundaries[k + 1])
            bi = int(sorted_bones[start])
            if bi >= len(bone_lists):
                continue
            bone_lists[bi] = [
                BoneVertData(index=int(v), weight=float(w))
                for v, w in zip(
                    sorted_verts[start:end].tolist(),
                    sorted_weights[start:end].tolist(),
                    strict=True,
                )
            ]

    block.bone_list = []
    for entries in bone_lists:
        bd = _empty_bone_data()
        bd.num_vertices = len(entries)
        bd.vertex_weights = entries
        block.bone_list.append(bd)
    return block


def build_ni_skin_instance(
    skin: SkinData,
    *,
    data_ref: int = _NULL_REF,
    partition_ref: int = _NULL_REF,
    skeleton_root_ref: int = _NULL_REF,
    bone_block_refs: list[int] | None = None,
    dismember: bool = False,
) -> NiSkinInstance:
    """Build a :class:`NiSkinInstance` (or :class:`BSDismemberSkinInstance`).

    ``bone_block_refs`` should be the block-table indices of the
    :class:`NiNode` blocks corresponding positionally to
    ``skin.bone_names``. When omitted, every slot is filled with the
    null sentinel -- the operator is expected to patch them.

    ``dismember=True`` returns a :class:`BSDismemberSkinInstance` shell
    with an empty body-part partition list (step 17 fills that in).
    """
    refs = (
        list(bone_block_refs)
        if bone_block_refs is not None
        else [_NULL_REF] * len(skin.bone_names)
    )
    if len(refs) != len(skin.bone_names):
        raise ValueError(
            f"bone_block_refs length {len(refs)} != bone palette size "
            f"{len(skin.bone_names)}"
        )

    block: NiSkinInstance
    if dismember:
        block = BSDismemberSkinInstance()
        block.num_partitions = 0
        block.partitions = []
    else:
        block = NiSkinInstance()
    block.data = data_ref
    block.skin_partition = partition_ref
    block.skeleton_root = skeleton_root_ref
    block.num_bones = len(skin.bone_names)
    block.bones = refs
    return block


# ---- private helpers -----------------------------------------------------


def _per_vertex_influences(
    skin: SkinData,
    num_vertices: int,
    max_weights: int,
) -> list[dict[int, float]]:
    """Bucket sparse weights into ``[{bone: weight} per vertex]`` table.

    Influences past ``max_weights`` are pruned (smallest first) and the
    survivors renormalised so each vertex's weight sum is 1.0.
    """
    table: list[dict[int, float]] = [{} for _ in range(num_vertices)]
    if skin.weights.size:
        # Vectorised filter; per-vertex assembly is unavoidable because
        # output rows have different cardinality.
        verts = skin.vertex_indices.astype(np.int64, copy=False)
        bones = skin.bone_indices.astype(np.int64, copy=False)
        weights = skin.weights.astype(np.float32, copy=False)
        in_range = (verts >= 0) & (verts < num_vertices)
        for v, b, w in zip(
            verts[in_range].tolist(),
            bones[in_range].tolist(),
            weights[in_range].tolist(),
            strict=True,
        ):
            if w <= 0.0:
                continue
            # Last-write-wins on duplicate (vertex, bone) pairs --
            # matches Blender vertex_group.add(..., 'REPLACE').
            table[v][b] = float(w)

    for v, infl in enumerate(table):
        if len(infl) > max_weights:
            top = sorted(infl.items(), key=lambda kv: kv[1], reverse=True)[:max_weights]
            infl = dict(top)
            table[v] = infl
        total = sum(infl.values())
        if total > 0.0 and abs(total - 1.0) > 1e-6:
            for b in list(infl.keys()):
                infl[b] = infl[b] / total
    return table


def _materialise_partition(
    triangles: npt.NDArray[np.int64],
    *,
    triangle_indices: list[int],
    bone_set: set[int],
    per_vertex: list[dict[int, float]],
    num_weights_per_vertex: int,
) -> PartitionBuild:
    """Turn a packed (bone-set, triangle-indices) bundle into a :class:`PartitionBuild`."""
    sub_tris = triangles[triangle_indices]
    unique_verts, inverse = np.unique(sub_tris.reshape(-1), return_inverse=True)
    local_tris = inverse.reshape(-1, 3).astype(np.uint16, copy=False)

    # Local bone palette: order is deterministic (sorted) so output is
    # stable across runs and easy to assert against in tests.
    sorted_bones = sorted(bone_set)
    bone_to_local = {b: i for i, b in enumerate(sorted_bones)}

    n = unique_verts.size
    bone_indices = np.zeros((n, num_weights_per_vertex), dtype=np.uint8)
    vertex_weights = np.zeros((n, num_weights_per_vertex), dtype=np.float32)
    for local_v, global_v in enumerate(unique_verts.tolist()):
        infl = per_vertex[global_v]
        ranked = sorted(infl.items(), key=lambda kv: kv[1], reverse=True)
        for slot, (bone_global, weight) in enumerate(ranked[:num_weights_per_vertex]):
            bone_indices[local_v, slot] = bone_to_local[bone_global]
            vertex_weights[local_v, slot] = weight

    return PartitionBuild(
        vertex_map=unique_verts.astype(np.uint16, copy=False),
        triangles=local_tris,
        bones=np.asarray(sorted_bones, dtype=np.uint16),
        bone_indices=bone_indices,
        vertex_weights=vertex_weights,
    )


def _build_skin_partition_compound(
    p: PartitionBuild,
    *,
    num_weights_per_vertex: int,
) -> SkinPartition:
    """Build the codegen-emitted :class:`SkinPartition` from a packed build."""
    sp = SkinPartition()
    sp.num_vertices = int(p.vertex_map.size)
    sp.num_triangles = int(p.triangles.shape[0])
    sp.num_bones = int(p.bones.size)
    sp.num_strips = 0
    sp.num_weights_per_vertex = int(num_weights_per_vertex)
    sp.bones = p.bones.astype(np.uint16, copy=False)
    sp.has_vertex_map = True
    sp.vertex_map = p.vertex_map
    sp.has_vertex_weights = True
    # SkinPartition stores weights as flat (N * num_weights_per_vertex) f32.
    sp.vertex_weights = p.vertex_weights.reshape(-1).astype(np.float32, copy=False)
    sp.strip_lengths = np.empty(0, dtype=np.uint16)
    sp.has_faces = True
    sp.strips = np.empty(0, dtype=np.uint16)
    sp.triangles = [
        Triangle(v1=int(t[0]), v2=int(t[1]), v3=int(t[2]))
        for t in p.triangles.tolist()
    ]
    sp.has_bone_indices = True
    sp.bone_indices = p.bone_indices.reshape(-1).astype(np.uint8, copy=False).tolist()
    sp.lod_level = 0
    sp.global_vb = False
    sp.triangles_copy = []
    return sp


def _identity_matrix33() -> Matrix33:
    return Matrix33(m11=1.0, m22=1.0, m33=1.0)


def _identity_transform() -> NiTransform:
    return NiTransform(
        rotation=_identity_matrix33(),
        translation=Vector3(x=0.0, y=0.0, z=0.0),
        scale=1.0,
    )


def _empty_bone_data() -> object:
    # Imported lazily so this module does not pull the structs symbol
    # into its public surface (the codegen-emitted ``BoneData`` shadows
    # the bridge's :class:`nifblend.bridge.armature_in.BoneData`).
    from nifblend.format.generated.structs import BoneData as NifBoneData

    bd = NifBoneData()
    bd.skin_transform = _identity_transform()
    bd.bounding_sphere = NiBound(center=Vector3(x=0.0, y=0.0, z=0.0), radius=0.0)
    return bd
