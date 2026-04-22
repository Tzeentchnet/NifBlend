"""Import side of the NiNode-tree ↔ Blender Armature bridge (Phase 4 step 14).

NIF stores the skeleton as a tree of :class:`~nifblend.format.generated.blocks.NiNode`
blocks linked by ``children`` u32 references into the
:class:`~nifblend.io.block_table.BlockTable`. Each node carries a local
transform — :class:`~nifblend.format.generated.structs.Vector3` translation,
:class:`~nifblend.format.generated.structs.Matrix33` rotation, and a uniform
``scale`` scalar — which together form a 4x4 local bind matrix.

The bridge is split in two so the heavy lifting stays testable headlessly:

* :func:`ninode_tree_to_armature_data` -- pure function that walks the
  :class:`NiNode` tree starting at a root index and returns a flat
  :class:`ArmatureData` whose :class:`BoneData` entries hold parent
  pointers, local 4x4 matrices, and pre-composed world 4x4 matrices.
  No ``bpy`` dependency.
* :func:`armature_data_to_blender` -- thin wrapper that materialises an
  :class:`ArmatureData` as a ``bpy.types.Object`` of type ``'ARMATURE'``
  with one EditBone per :class:`BoneData`. The full local 4x4 is stamped
  onto each bone's ``nifblend`` :class:`PropertyGroup`
  (:mod:`nifblend.bridge.armature_props`) so the lossy
  ``(head, tail, roll)`` reduction Blender forces on us is always
  recoverable on export.

Why preserve the full 4x4? Bone roll alone discards any rotation that
doesn't align the bone's local Y-axis with the parent → child vector,
and it cannot represent NIF's per-node uniform scale at all. Storing the
local matrix verbatim sidesteps both losses; armature_out (step 16) can
re-derive head/tail/roll from the PropertyGroup matrix.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.generated.blocks import NiNode

from .armature_props import apply_bind_matrix_to_props

if TYPE_CHECKING:  # pragma: no cover - typing only
    from nifblend.io.block_table import BlockTable


__all__ = [
    "ArmatureData",
    "BoneData",
    "armature_data_to_blender",
    "import_armature",
    "ninode_tree_to_armature_data",
]


#: Fallback bone length when a bone has no children to point its tail at.
DEFAULT_BONE_LENGTH = 0.1


@dataclass(slots=True)
class BoneData:
    """One bone in an :class:`ArmatureData`."""

    name: str
    #: Index into :attr:`ArmatureData.bones` of the parent bone, or
    #: ``-1`` for a root bone. Roots are valid; armatures may have
    #: multiple if the source NIF has multiple top-level NiNode children
    #: under the scene root.
    parent: int = -1
    #: Local 4x4 bind transform from the parent bone (homogeneous,
    #: row-major). Identity for a node with zero rotation, zero
    #: translation, and unit scale.
    local_matrix: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.eye(4, dtype=np.float32)
    )
    #: World-space bind transform, equal to
    #: ``parent.world_matrix @ local_matrix`` (or ``local_matrix`` for a
    #: root bone). Pre-composed during the tree walk so the Blender
    #: wrapper can place head/tail without redoing the recursion.
    world_matrix: npt.NDArray[np.float32] = field(
        default_factory=lambda: np.eye(4, dtype=np.float32)
    )
    #: Index in the source :class:`BlockTable` of the originating
    #: :class:`NiNode`, useful for cross-referencing skin instances in
    #: step 15.
    source_block_index: int = -1


@dataclass(slots=True)
class ArmatureData:
    """Dense representation of a NIF skeleton, ready for Blender.

    ``bones`` is a flat, parent-before-child topologically sorted list
    so a single forward pass over it produces a valid Blender armature
    (every bone's parent has already been created when its turn comes).
    """

    name: str
    bones: list[BoneData] = field(default_factory=list)


# ---- block tree → ArmatureData -------------------------------------------


def ninode_tree_to_armature_data(
    table: BlockTable,
    root_index: int,
    *,
    name: str | None = None,
    skip_root: bool = False,
) -> ArmatureData:
    """Walk the NiNode tree rooted at ``table.blocks[root_index]``.

    ``skip_root`` excludes the root node itself from the bone list (the
    typical Bethesda layout puts a single ``Scene Root`` NiNode at the
    top whose only purpose is to host children — it shouldn't appear as
    a bone). Setting ``skip_root=False`` keeps the root and treats it as
    bone 0 with ``parent=-1``.

    Non-:class:`NiNode` children (geometry shapes, controllers, …) are
    silently skipped — this bridge produces *bones*, not the full scene
    graph.
    """
    root_block = table.blocks[root_index]
    if not isinstance(root_block, NiNode):
        raise TypeError(
            f"block {root_index} is {type(root_block).__name__}, not NiNode"
        )
    armature_name = name if name is not None else _resolve_name(root_block, table)
    armature = ArmatureData(name=armature_name)

    if skip_root:
        root_world = _node_local_matrix(root_block)
        for child_idx in _ninode_children(root_block, table):
            _walk(table, child_idx, parent_bone=-1, parent_world=root_world, armature=armature)
    else:
        _walk(table, root_index, parent_bone=-1, parent_world=np.eye(4, dtype=np.float32), armature=armature)

    return armature


def _walk(
    table: BlockTable,
    block_index: int,
    *,
    parent_bone: int,
    parent_world: npt.NDArray[np.float32],
    armature: ArmatureData,
) -> None:
    block = table.blocks[block_index]
    local = _node_local_matrix(block)
    world = parent_world @ local
    bone_index = len(armature.bones)
    armature.bones.append(
        BoneData(
            name=_resolve_name(block, table),
            parent=parent_bone,
            local_matrix=local,
            world_matrix=world,
            source_block_index=block_index,
        )
    )
    for child_idx in _ninode_children(block, table):
        _walk(
            table,
            child_idx,
            parent_bone=bone_index,
            parent_world=world,
            armature=armature,
        )


# ---- ArmatureData → bpy.types.Object -------------------------------------


def armature_data_to_blender(
    data: ArmatureData,
    *,
    bpy: Any = None,
    context: Any = None,
) -> Any:
    """Materialise ``data`` as a Blender Armature Object.

    ``bpy`` is injected so headless tests can pass a fake module;
    production callers leave it as ``None`` and we import the real
    ``bpy`` lazily. ``context`` is forwarded to the Blender mode-switch
    operator; when ``None`` we fall back to ``bpy.context``.

    The Blender armature is built in three phases:

    1. Create the Armature data-block and link it into a fresh Object.
    2. Enter ``EDIT`` mode and add one EditBone per :class:`BoneData`,
       laid out from the world matrix (head = world translation;
       tail = head + length x world Y-axis; length = distance to first
       child or :data:`DEFAULT_BONE_LENGTH`).
    3. Leave edit mode and stamp the local 4x4 onto each
       :class:`bpy.types.Bone`'s ``nifblend`` PropertyGroup so the
       lossy edit-bone reduction is always recoverable.
    """
    if bpy is None:
        import bpy as bpy  # (lazy import; keep name local)

    armature_data = bpy.data.armatures.new(data.name)
    obj = bpy.data.objects.new(data.name, armature_data)

    # Link the new object into the active scene/collection so the
    # mode-switch operator below has something to operate on. Real
    # Blender requires this; the test fakes can no-op.
    _link_object(bpy, obj, context)
    _set_active_object(bpy, obj, context)

    bone_lengths = _bone_lengths(data)

    _enter_edit_mode(bpy, context)
    edit_bones = armature_data.edit_bones
    edit_bone_handles: list[Any] = []
    for i, bone in enumerate(data.bones):
        eb = edit_bones.new(bone.name)
        head = bone.world_matrix[:3, 3]
        # Y-axis of the world basis (column 1), normalised — falls back
        # to +Z if the basis is degenerate (zero scale).
        y_axis = bone.world_matrix[:3, 1]
        norm = float(np.linalg.norm(y_axis))
        direction = (
            np.array([0.0, 0.0, 1.0], dtype=np.float32)
            if norm < 1e-8
            else y_axis / norm
        )
        length = bone_lengths[i]
        tail = head + direction * length
        eb.head = (float(head[0]), float(head[1]), float(head[2]))
        eb.tail = (float(tail[0]), float(tail[1]), float(tail[2]))
        if bone.parent >= 0:
            eb.parent = edit_bone_handles[bone.parent]
        edit_bone_handles.append(eb)
    _exit_edit_mode(bpy, context)

    # Stamp the lossless local 4x4 onto each data-bone's PropertyGroup.
    for bone in data.bones:
        data_bone = armature_data.bones.get(bone.name) if hasattr(armature_data.bones, "get") else armature_data.bones[bone.name]
        if data_bone is not None:
            apply_bind_matrix_to_props(data_bone, bone.local_matrix)

    return obj


# ---- top-level convenience ------------------------------------------------


def import_armature(
    table: BlockTable,
    root_index: int,
    *,
    name: str | None = None,
    skip_root: bool = False,
    bpy: Any = None,
    context: Any = None,
) -> Any:
    """Convert a NiNode tree into a Blender Armature in one call."""
    data = ninode_tree_to_armature_data(
        table, root_index, name=name, skip_root=skip_root
    )
    return armature_data_to_blender(data, bpy=bpy, context=context)


# ---- private helpers ------------------------------------------------------


def _node_local_matrix(block: NiNode) -> npt.NDArray[np.float32]:
    """Compose ``block``'s translation + Matrix33 + scale into a 4x4."""
    out = np.eye(4, dtype=np.float32)
    rot = block.rotation
    if rot is not None:
        out[0, 0] = rot.m11
        out[0, 1] = rot.m12
        out[0, 2] = rot.m13
        out[1, 0] = rot.m21
        out[1, 1] = rot.m22
        out[1, 2] = rot.m23
        out[2, 0] = rot.m31
        out[2, 1] = rot.m32
        out[2, 2] = rot.m33
    scale = float(block.scale) if block.scale else 1.0
    if scale != 1.0:
        out[:3, :3] *= scale
    tr = block.translation
    if tr is not None:
        out[0, 3] = tr.x
        out[1, 3] = tr.y
        out[2, 3] = tr.z
    return out


def _ninode_children(block: NiNode, table: BlockTable) -> list[int]:
    """Return the indices of ``block``'s children that are NiNode subclasses."""
    out: list[int] = []
    for ref in block.children or []:
        idx = int(ref)
        if idx < 0 or idx == 0xFFFFFFFF or idx >= len(table.blocks):
            continue
        child = table.blocks[idx]
        if isinstance(child, NiNode):
            out.append(idx)
    return out


def _bone_lengths(data: ArmatureData) -> list[float]:
    """Pick a sensible tail length for each bone.

    Heuristic: distance to the first child bone in world space; falls
    back to :data:`DEFAULT_BONE_LENGTH` when a bone has no children
    (leaf joints).
    """
    children: list[list[int]] = [[] for _ in data.bones]
    for i, bone in enumerate(data.bones):
        if bone.parent >= 0:
            children[bone.parent].append(i)

    lengths: list[float] = []
    for i, bone in enumerate(data.bones):
        if not children[i]:
            lengths.append(DEFAULT_BONE_LENGTH)
            continue
        first_child = data.bones[children[i][0]]
        head = bone.world_matrix[:3, 3]
        child_head = first_child.world_matrix[:3, 3]
        length = float(np.linalg.norm(child_head - head))
        lengths.append(length if length > 1e-6 else DEFAULT_BONE_LENGTH)
    return lengths


def _resolve_name(block: NiNode, table: BlockTable | None) -> str:
    """Resolve ``block.name`` (string-table index or inline) to ``str``.

    Mirrors :func:`nifblend.bridge.mesh_in._resolve_name`; kept local so
    the two bridges stay independent.
    """
    name_obj = block.name
    if name_obj is None:
        return type(block).__name__
    inline = getattr(name_obj, "string", None)
    if inline is not None:
        try:
            return bytes(inline.value).decode("latin-1")
        except (AttributeError, ValueError):
            pass
    idx_attr = getattr(name_obj, "index", None)
    idx = idx_attr if idx_attr is not None else name_obj
    try:
        idx = int(idx)
    except (TypeError, ValueError):
        return type(block).__name__
    if idx < 0 or idx == 0xFFFFFFFF or table is None:
        return type(block).__name__
    strings = table.header.strings
    if idx >= len(strings):
        return type(block).__name__
    s = strings[idx]
    if s is None:
        return type(block).__name__
    return bytes(s.value).decode("latin-1")


# ---- Blender mode-switching shims ----------------------------------------
#
# Real Blender requires entering EDIT mode on the active armature object
# before ``armature_data.edit_bones`` is populated, and the test fakes
# don't model the operator surface. These helpers degrade gracefully on
# both ends.


def _link_object(bpy: Any, obj: Any, context: Any) -> None:
    ctx = context if context is not None else getattr(bpy, "context", None)
    if ctx is None:
        return
    collection = getattr(getattr(ctx, "collection", None), "objects", None)
    if collection is not None and hasattr(collection, "link"):
        with contextlib.suppress(RuntimeError, TypeError, ValueError):
            collection.link(obj)


def _set_active_object(bpy: Any, obj: Any, context: Any) -> None:
    ctx = context if context is not None else getattr(bpy, "context", None)
    if ctx is None:
        return
    view_layer = getattr(ctx, "view_layer", None)
    active = getattr(view_layer, "objects", None)
    if active is not None and hasattr(active, "active"):
        with contextlib.suppress(AttributeError, TypeError):
            active.active = obj


def _enter_edit_mode(bpy: Any, context: Any) -> None:
    ops = getattr(bpy, "ops", None)
    obj_ops = getattr(ops, "object", None) if ops is not None else None
    mode_set = getattr(obj_ops, "mode_set", None) if obj_ops is not None else None
    if mode_set is None:
        return
    with contextlib.suppress(RuntimeError, TypeError):
        mode_set(mode="EDIT")


def _exit_edit_mode(bpy: Any, context: Any) -> None:
    ops = getattr(bpy, "ops", None)
    obj_ops = getattr(ops, "object", None) if ops is not None else None
    mode_set = getattr(obj_ops, "mode_set", None) if obj_ops is not None else None
    if mode_set is None:
        return
    with contextlib.suppress(RuntimeError, TypeError):
        mode_set(mode="OBJECT")
