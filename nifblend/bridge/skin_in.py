"""Import side of the NIF skin ↔ Blender vertex-group bridge (Phase 4 step 15).

NIF stores skin weights three different ways depending on the game era:

* **Classic NiSkinInstance + NiSkinData** (Morrowind .. Skyrim LE,
  also Oblivion / Fallout 3 / NV). The skin instance carries a flat
  bone-palette (``bones[i]`` -> NiNode block index) plus a ``data`` ref
  to a :class:`~nifblend.format.generated.blocks.NiSkinData` block whose
  ``bone_list[i].vertex_weights`` is a sparse ``[(vertex_index, weight)]``
  list per bone.  ``BSDismemberSkinInstance`` is the Bethesda variant that
  adds body-part partitions on top -- partition handling lives in step 17;
  for weight extraction it is structurally identical and we duck-type on
  ``.bones`` / ``.data``.

* **BSTriShape (SSE)** stores skin weights inline in the per-vertex
  records -- :class:`~nifblend.format.generated.structs.BSVertexDataSSE`
  has fixed-size ``bone_indices[4]`` / ``bone_weights[4]`` palette
  indices into the ``NiSkinInstance.bones`` flat palette. The
  :class:`~nifblend.format.generated.blocks.NiSkinPartition` block is a
  GPU-skinning hint, not the source of truth for weights.

* **BSSkinInstance + BSSkinBoneData (Fallout 4 / 76)** mirrors the SSE
  layout: weights live in :class:`BSSubIndexTriShape`'s vertex records
  and ``BSSkinInstance.bones`` is the global palette. We accept any
  shape whose vertex data exposes ``bone_indices`` / ``bone_weights``,
  so the SSE path covers FO4 too.

The bridge is split, like every other NifBlend bridge, into a pure
decoder (no ``bpy``) and a Blender wrapper:

* :func:`niskin_to_skin_data` -- handles the classic NiSkinData layout.
* :func:`bstrishape_skin_to_skin_data` -- handles the SSE/FO4 layout
  where weights live in the shape's vertex records and the skin
  instance only supplies the bone palette.
* :func:`apply_skin_to_object` -- thin wrapper that creates one Blender
  vertex group per palette bone and pushes the (vertex, weight) pairs in.
  Iterating per ``vertex_group.add`` call is unavoidable (Blender's API
  takes a single weight scalar per call), but the *decode* from sparse
  NIF records into the dense ``(vertex_index, bone_index, weight)``
  triple of numpy arrays is fully vectorised -- no per-vertex Python
  loop walks the NIF block lists.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.blocks import NiNode, NiSkinData

from .armature_in import _resolve_name as _resolve_node_name

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.io.block_table import BlockTable


__all__ = [
    "SkinData",
    "apply_skin_to_object",
    "bstrishape_skin_to_skin_data",
    "niskin_to_skin_data",
]


#: Marker that a ``ref``/``ptr`` u32 is the schema's "no link" sentinel.
_NULL_REF = 0xFFFFFFFF


@dataclass(slots=True)
class SkinData:
    """Sparse skin weights ready to materialise as Blender vertex groups.

    The arrays are parallel: the ``k``-th weight assigns
    ``weights[k]`` of vertex ``vertex_indices[k]`` to the bone whose
    name is ``bone_names[bone_indices[k]]``. Zero-weight entries are
    filtered out by the decoders so the wrapper never wastes a Blender
    API call on a no-op.
    """

    #: Positional bone names; index ``i`` corresponds to slot ``i`` of
    #: the source skin instance's bone palette. Names are resolved from
    #: the referenced NiNode blocks via the header string table; bones
    #: that fail to resolve fall back to ``"Bone.{i}"`` so the resulting
    #: vertex group is always nameable.
    bone_names: list[str] = field(default_factory=list)
    #: Target vertex indices, ``(K,)`` u32.
    vertex_indices: npt.NDArray[np.uint32] = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    #: Bone palette indices into :attr:`bone_names`, ``(K,)`` u32.
    bone_indices: npt.NDArray[np.uint32] = field(
        default_factory=lambda: np.empty(0, dtype=np.uint32)
    )
    #: Per-influence weights, ``(K,)`` float32. Always > 0 after decode.
    weights: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.empty(0, dtype=np.float32)
    )


# ---- decoders -------------------------------------------------------------


def niskin_to_skin_data(
    table: BlockTable,
    skin_instance_index: int,
) -> SkinData:
    """Decode a classic NiSkinInstance (+ NiSkinData) into a :class:`SkinData`.

    Works for plain :class:`~nifblend.format.generated.blocks.NiSkinInstance`
    and for :class:`~nifblend.format.generated.blocks.BSDismemberSkinInstance`
    (it duck-types on ``.bones`` / ``.data``).
    """
    skin_inst = table.blocks[skin_instance_index]
    bone_refs = list(getattr(skin_inst, "bones", []) or [])
    data_ref = int(getattr(skin_inst, "data", _NULL_REF))
    skin_data = _resolve_block(table, data_ref, NiSkinData)

    bone_names = _resolve_bone_names(table, bone_refs)

    if skin_data is None or not skin_data.bone_list:
        return SkinData(bone_names=bone_names)

    # Per-bone sparse weight lists -> three flat numpy arrays. We size
    # the destination once with the total count to avoid python-level
    # appends during the main loop.
    per_bone_lengths = [
        len(getattr(b, "vertex_weights", []) or []) for b in skin_data.bone_list
    ]
    total = int(sum(per_bone_lengths))
    if total == 0:
        return SkinData(bone_names=bone_names)

    vertex_indices = np.empty(total, dtype=np.uint32)
    bone_indices = np.empty(total, dtype=np.uint32)
    weights = np.empty(total, dtype=np.float32)

    cursor = 0
    for bi, bone in enumerate(skin_data.bone_list):
        vw = getattr(bone, "vertex_weights", None)
        if not vw:
            continue
        n = len(vw)
        # ``vw`` is a list of BoneVertData dataclasses; pull out the two
        # scalars in one numpy.fromiter pass per attribute. fromiter is
        # the right call here -- it preallocates without round-tripping
        # through a Python list.
        vertex_indices[cursor : cursor + n] = np.fromiter(
            (int(v.index) for v in vw), dtype=np.uint32, count=n
        )
        weights[cursor : cursor + n] = np.fromiter(
            (float(v.weight) for v in vw), dtype=np.float32, count=n
        )
        bone_indices[cursor : cursor + n] = bi
        cursor += n

    # Drop zero-weight entries -- Blender treats a 0.0 weight as
    # "remove from group", not "no influence", so leaking them in would
    # silently corrupt round-trips on bones that legitimately list a
    # vertex with weight 1.0 elsewhere.
    nonzero = weights > 0.0
    if not nonzero.all():
        vertex_indices = vertex_indices[nonzero]
        bone_indices = bone_indices[nonzero]
        weights = weights[nonzero]

    return SkinData(
        bone_names=bone_names,
        vertex_indices=vertex_indices,
        bone_indices=bone_indices,
        weights=weights,
    )


def bstrishape_skin_to_skin_data(
    table: BlockTable,
    shape: Any,
) -> SkinData:
    """Decode SSE/FO4-style per-vertex weights into a :class:`SkinData`.

    ``shape`` must expose ``vertex_data`` (a list whose elements have
    ``bone_indices`` and ``bone_weights`` lists, i.e. BSVertexDataSSE)
    and ``skin`` (the u32 ref to a NiSkinInstance / BSSkinInstance whose
    ``bones`` palette names the influences). Vertex records that have
    no weights or are ``None`` are silently skipped.
    """
    skin_ref = int(getattr(shape, "skin", _NULL_REF))
    skin_inst = _resolve_optional(table, skin_ref)
    bone_refs = (
        list(getattr(skin_inst, "bones", []) or []) if skin_inst is not None else []
    )
    bone_names = _resolve_bone_names(table, bone_refs)

    vertex_data = list(getattr(shape, "vertex_data", []) or [])
    if not vertex_data:
        return SkinData(bone_names=bone_names)

    n = len(vertex_data)
    # Decode into dense (N, 4) arrays first; this is the same access
    # pattern the mesh bridge uses for normals/colors so we keep the
    # python-side iteration to a single pass.
    raw_idx = np.zeros((n, 4), dtype=np.uint32)
    raw_wt = np.zeros((n, 4), dtype=np.float32)
    for i, v in enumerate(vertex_data):
        if v is None:
            continue
        bi = getattr(v, "bone_indices", None) or ()
        bw = getattr(v, "bone_weights", None) or ()
        for slot in range(min(4, len(bi), len(bw))):
            raw_idx[i, slot] = int(bi[slot])
            raw_wt[i, slot] = float(bw[slot])

    # Flatten and drop zero-weight slots vectorially. The vertex index
    # for each (i, slot) pair is just ``i``, broadcast across slots.
    vertex_grid = np.repeat(np.arange(n, dtype=np.uint32), 4)
    flat_idx = raw_idx.reshape(-1)
    flat_wt = raw_wt.reshape(-1)
    keep = flat_wt > 0.0
    return SkinData(
        bone_names=bone_names,
        vertex_indices=vertex_grid[keep],
        bone_indices=flat_idx[keep],
        weights=flat_wt[keep],
    )


# ---- Blender wrapper ------------------------------------------------------


def apply_skin_to_object(
    skin: SkinData,
    obj: Any,
    *,
    bpy: Any = None,
) -> dict[str, Any]:
    """Create vertex groups on ``obj`` for every bone in ``skin``.

    Returns a ``{bone_name: vertex_group}`` dict so callers (and tests)
    can introspect the result without re-walking ``obj.vertex_groups``.
    Empty bones still get a group created -- the armature_out side of
    Phase 4 will rely on the group existing to round-trip the palette,
    even when every weight on a bone happens to be zero.
    """
    del bpy  # The Blender API surface here is ``obj.vertex_groups`` only.
    groups: dict[str, Any] = {}
    for name in skin.bone_names:
        groups[name] = obj.vertex_groups.new(name=name)

    if skin.weights.size == 0:
        return groups

    # Bucket by bone so we issue one Blender call per (bone, weight)
    # rather than per (bone, vertex). The decoders already filtered
    # zero weights, so every call here moves real data.
    order = np.argsort(skin.bone_indices, kind="stable")
    sorted_bones = skin.bone_indices[order]
    sorted_verts = skin.vertex_indices[order]
    sorted_weights = skin.weights[order]
    # Boundaries between bone runs in the sorted arrays.
    boundaries = np.concatenate(
        ([0], np.flatnonzero(np.diff(sorted_bones)) + 1, [sorted_bones.size])
    )

    for start, end in pairwise(boundaries):
        bone_idx = int(sorted_bones[start])
        if bone_idx >= len(skin.bone_names):
            continue  # palette index out of range -- skip silently
        group = groups[skin.bone_names[bone_idx]]
        run_verts = sorted_verts[start:end]
        run_weights = sorted_weights[start:end]
        # Within a bone, group vertices that share an exact weight so
        # we issue one ``add`` call per unique weight value rather than
        # one per vertex. ``return_inverse`` gives us the bucket id for
        # each entry without a second pass.
        unique_weights, inverse = np.unique(run_weights, return_inverse=True)
        for bucket, w in enumerate(unique_weights):
            verts = run_verts[inverse == bucket]
            group.add(verts.tolist(), float(w), "REPLACE")

    return groups


# ---- private helpers ------------------------------------------------------


def _resolve_block(
    table: BlockTable, ref: int, expected: type[Any]
) -> Any | None:
    block = _resolve_optional(table, ref)
    if block is None or not isinstance(block, expected):
        return None
    return block


def _resolve_optional(table: BlockTable, ref: int) -> Any | None:
    if ref < 0 or ref == _NULL_REF or ref >= len(table.blocks):
        return None
    return table.blocks[ref]


def _resolve_bone_names(table: BlockTable, bone_refs: list[int]) -> list[str]:
    """Resolve a list of NiNode block refs to their string-table names.

    Bones that fail to resolve (out-of-range refs, refs to non-NiNode
    blocks, or blocks with no name) get a positional placeholder so the
    palette index stays meaningful and downstream code never has to
    handle a ``None`` slot.
    """
    out: list[str] = []
    for i, ref_obj in enumerate(bone_refs):
        with contextlib.suppress(TypeError, ValueError):
            ref = int(ref_obj)
            if 0 <= ref < len(table.blocks) and ref != _NULL_REF:
                block = table.blocks[ref]
                if isinstance(block, NiNode):
                    out.append(_resolve_node_name(block, table))
                    continue
        out.append(f"Bone.{i}")
    return out
