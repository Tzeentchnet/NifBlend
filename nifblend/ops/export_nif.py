"""Export operator wired to the Phase 2 BSTriShape bridge.

Walks every selected mesh object in the scene, converts each to a
:class:`~nifblend.format.generated.blocks.BSTriShape` via the bridge, and
writes them as a fresh NIF (Skyrim SE-shaped header by default).

Phase 5 orchestration: :func:`build_export_table` additionally carries
over each object's own transform (translation/rotation/uniform-scale),
attaches a material (shader property + optional texture set + optional
alpha property) when the mesh has one, and -- when the mesh is parented
to (or driven by an Armature modifier targeting) an armature -- builds
that armature's bone hierarchy once (shared across every mesh using it)
and a skin (per-vertex bone weights baked into the packed vertex data,
plus a classic-shaped ``NiSkinData`` + ``NiSkinInstance`` for
compatibility with tools that read it). ``NiSkinPartition`` (a
GPU-skinning hint the read side doesn't consume for BSTriShape -- see
``nifblend/bridge/skin_in.py``) is intentionally left unbuilt to keep
this pass's scope bounded; real-game hardware-skinning partitioning
remains a follow-on item. Classic (Morrowind/Oblivion/FO3-NV) geometry
export stays out of scope too -- no ``NiTriShape`` builder exists yet
(mesh_out.py only builds ``BSTriShape``), so this operator targets
Skyrim LE/SE-family profiles.
"""

from __future__ import annotations

import math
from typing import Any

import bpy
import numpy as np
import numpy.typing as npt
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from nifblend.bridge.armature_out import (
    build_ni_skin_data,
    build_ni_skin_instance,
    build_ninode_tree,
)
from nifblend.bridge.material_out import (
    build_alpha_property,
    build_texture_set,
    export_material,
    material_data_from_blender,
)
from nifblend.bridge.mesh_out import mesh_data_from_blender, mesh_data_to_bstrishape
from nifblend.bridge.skin_in import SkinData, skin_data_from_vertex_groups
from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
    Matrix33,
    SizedString,
    Vector3,
)
from nifblend.format.generated.structs import string as nif_string
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif

__all__ = ["NIFBLEND_OT_export_nif", "build_export_table"]

_NULL_REF = 0xFFFFFFFF
#: Null sentinel for signed-i32 block cross-refs (shader_property, skin,
#: skeleton_root, ...) -- distinct from ``_NULL_REF``, which is the u32
#: string-table "no string" sentinel. Conflating the two overflows
#: ``write_i32`` (which requires a value in ``[-2**31, 2**31-1]``).
_NULL_BLOCK_REF = -1


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_header() -> tuple[Header, ReadContext]:
    """Return a minimal SSE-shaped header + matching ReadContext."""
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,  # filled in by write_nif
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
        num_block_types=0,
        block_types=[],
        block_type_index=[],
        num_strings=0,
        max_string_length=0,
        strings=[],
        num_groups=0,
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return h, ctx


class _StringTable:
    """Allocates one ``SizedString`` entry per unique string.

    Mirrors :mod:`nifblend.bridge.animation_out`'s private ``_StringTable``
    (same contract: empty strings collapse to the ``0xFFFFFFFF`` null-string
    sentinel rather than a zero-length payload).
    """

    def __init__(self) -> None:
        self._index: dict[str, int] = {}
        self._strings: list[SizedString] = []

    def add(self, value: str | None) -> int:
        if not value:
            return _NULL_REF
        idx = self._index.get(value)
        if idx is None:
            idx = len(self._strings)
            payload = value.encode("latin-1")
            self._strings.append(SizedString(length=len(payload), value=list(payload)))
            self._index[value] = idx
        return idx

    @property
    def strings(self) -> list[SizedString]:
        return self._strings


# ---- object transform -> NIF translation/rotation/scale ------------------


def _euler_xyz_to_matrix3(rx: float, ry: float, rz: float) -> npt.NDArray[np.float64]:
    """Intrinsic XYZ Euler -> 3x3 rotation matrix (``R = Rz @ Ry @ Rx``).

    Matches the convention :func:`nifblend.bridge.armature_in.quaternion_stream_to_euler_streams`
    decodes *from* on import, so an unedited round-trip recomposes the
    identical matrix.
    """
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    rot_y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    rot_z = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return rot_z @ rot_y @ rot_x


def _quaternion_to_matrix3(w: float, x: float, y: float, z: float) -> npt.NDArray[np.float64]:
    """Standard unit-quaternion -> 3x3 rotation matrix formula."""
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def _matrix3_to_matrix33(rot: npt.NDArray[np.float64]) -> Matrix33:
    return Matrix33(
        m11=float(rot[0, 0]),
        m12=float(rot[0, 1]),
        m13=float(rot[0, 2]),
        m21=float(rot[1, 0]),
        m22=float(rot[1, 1]),
        m23=float(rot[1, 2]),
        m31=float(rot[2, 0]),
        m32=float(rot[2, 1]),
        m33=float(rot[2, 2]),
    )


def object_transform_to_shape_trs(obj: Any) -> tuple[Vector3, Matrix33, float]:
    """Read ``obj``'s local transform into NIF's translation/rotation/scale triad.

    Non-uniform ``obj.scale`` (NIF's ``NiAVObject.scale`` is a single
    uniform float) takes the average of the three axes and leaves the
    per-axis variance for the vertex data itself to absorb -- callers
    exporting a non-uniformly-scaled object should bake scale into mesh
    data before export for a lossless result; this keeps the common
    (uniform-scale) case exact without erroring on the rare case.

    Every attribute is read via ``getattr`` with an identity-transform
    fallback so a minimal test fake (or a bare mesh-only object with no
    transform of its own) exports at the origin rather than erroring.
    """
    loc = getattr(obj, "location", None) or (0.0, 0.0, 0.0)
    translation = Vector3(float(loc[0]), float(loc[1]), float(loc[2]))

    mode = str(getattr(obj, "rotation_mode", "XYZ") or "XYZ")
    if mode == "QUATERNION":
        w, x, y, z = getattr(obj, "rotation_quaternion", None) or (1.0, 0.0, 0.0, 0.0)
        rot3 = _quaternion_to_matrix3(float(w), float(x), float(y), float(z))
    else:
        ex, ey, ez = getattr(obj, "rotation_euler", None) or (0.0, 0.0, 0.0)
        rot3 = _euler_xyz_to_matrix3(float(ex), float(ey), float(ez))

    scale_xyz = tuple(float(c) for c in (getattr(obj, "scale", None) or (1.0, 1.0, 1.0)))
    scale = sum(scale_xyz) / 3.0
    return translation, _matrix3_to_matrix33(rot3), scale


# ---- sparse SkinData -> dense per-vertex (N, 4) arrays --------------------


def _sparse_skin_to_dense(
    skin: SkinData, num_vertices: int
) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.float32]]:
    """Bake a sparse :class:`SkinData` into BSVertexDataSSE's fixed 4-influence shape.

    Extra influences beyond 4 are pruned (lowest weight first) and the
    survivors renormalised to sum to 1.0, mirroring
    :mod:`nifblend.bridge.armature_out`'s partition-builder convention.
    """
    dense_idx = np.zeros((num_vertices, 4), dtype=np.uint8)
    dense_wt = np.zeros((num_vertices, 4), dtype=np.float32)
    if skin.weights.size == 0:
        return dense_idx, dense_wt

    per_vertex: dict[int, list[tuple[int, float]]] = {}
    for v, b, w in zip(
        skin.vertex_indices.tolist(),
        skin.bone_indices.tolist(),
        skin.weights.tolist(),
        strict=True,
    ):
        if 0 <= v < num_vertices:
            per_vertex.setdefault(v, []).append((b, w))

    for v, pairs in per_vertex.items():
        pairs.sort(key=lambda p: p[1], reverse=True)
        top = pairs[:4]
        total = sum(w for _, w in top) or 1.0
        for slot, (b, w) in enumerate(top):
            dense_idx[v, slot] = b
            dense_wt[v, slot] = w / total

    return dense_idx, dense_wt


# ---- armature + object discovery ------------------------------------------


def _find_armature(obj: Any) -> Any | None:
    """Return the armature driving ``obj`` (parent, or an Armature modifier)."""
    parent = getattr(obj, "parent", None)
    if parent is not None and getattr(parent, "type", None) == "ARMATURE":
        return parent
    for mod in getattr(obj, "modifiers", None) or ():
        if getattr(mod, "type", None) == "ARMATURE":
            target = getattr(mod, "object", None)
            if target is not None:
                return target
    return None


# ---- main orchestrator -----------------------------------------------------


def build_export_table(objects: list[Any]) -> BlockTable:
    """Build a complete, ready-to-write SSE-shaped :class:`BlockTable`.

    One :class:`~nifblend.format.generated.blocks.BSTriShape` per mesh
    object in ``objects`` (non-mesh objects are silently skipped), each
    carrying its own transform, material (when the mesh has one), and
    skin + shared armature (when parented to / driven by one). Meshes
    that share the same armature object build its bone hierarchy exactly
    once. Footer roots are every armature's root bone plus every
    unparented (rigid) shape, so every exported object stays reachable
    from :func:`nifblend.bridge.armature_in.compute_world_transforms` on
    re-import.
    """
    strings = _StringTable()
    blocks: list[Any] = []
    roots: list[int] = []
    # id(armature_obj) -> (root_block_index, {bone_name: block_index})
    armature_cache: dict[int, tuple[int, dict[str, int]]] = {}

    for obj in objects:
        if getattr(obj, "type", None) != "MESH":
            continue

        armature_obj = _find_armature(obj)
        skeleton_root_index = _NULL_BLOCK_REF
        bone_index_by_name: dict[str, int] = {}
        if armature_obj is not None:
            key = id(armature_obj)
            if key not in armature_cache:
                built = build_ninode_tree(armature_obj)
                offset = len(blocks)
                root_index = _NULL_BLOCK_REF
                for i, bn in enumerate(built):
                    node = bn.block
                    node.name = nif_string(index=strings.add(bn.name))
                    node.children = [c + offset for c in node.children]
                    node.num_children = len(node.children)
                    blocks.append(node)
                    if bn.parent_index == -1 and root_index == _NULL_BLOCK_REF:
                        root_index = offset + i
                name_map = {bn.name: offset + i for i, bn in enumerate(built)}
                armature_cache[key] = (root_index, name_map)
                if root_index != _NULL_BLOCK_REF:
                    roots.append(root_index)
            skeleton_root_index, bone_index_by_name = armature_cache[key]

        mesh_data = mesh_data_from_blender(obj.data, name=obj.name)

        # Material (shader property + optional texture set + optional alpha).
        shader_ref = _NULL_BLOCK_REF
        alpha_ref = _NULL_BLOCK_REF
        materials = list(getattr(obj.data, "materials", None) or [])
        mat = materials[0] if materials else None
        if mat is not None:
            mat_data = material_data_from_blender(mat)
            texture_set_ref = -1
            ts_block = build_texture_set(mat_data)
            if ts_block is not None:
                texture_set_ref = len(blocks)
                blocks.append(ts_block)
            name_idx = strings.add(mat_data.name)
            shader_block = export_material(
                mat, name_index=name_idx, texture_set_ref=texture_set_ref
            )
            shader_ref = len(blocks)
            blocks.append(shader_block)
            alpha_block = build_alpha_property(mat_data)
            if alpha_block is not None:
                alpha_ref = len(blocks)
                blocks.append(alpha_block)

        # Skin: bake dense per-vertex weights into the shape's own vertex
        # data, plus a classic-shaped NiSkinData + NiSkinInstance so tools
        # that expect them still find a well-formed skin chain.
        skin_ref = _NULL_BLOCK_REF
        if armature_obj is not None and bone_index_by_name:
            bone_names = list(bone_index_by_name.keys())
            skin = skin_data_from_vertex_groups(obj, bone_names)
            if skin.weights.size > 0:
                dense_idx, dense_wt = _sparse_skin_to_dense(skin, mesh_data.positions.shape[0])
                mesh_data.bone_indices = dense_idx
                mesh_data.bone_weights = dense_wt

                data_block = build_ni_skin_data(skin)
                data_ref = len(blocks)
                blocks.append(data_block)

                bone_block_refs = [bone_index_by_name[n] for n in skin.bone_names]
                inst_block = build_ni_skin_instance(
                    skin,
                    data_ref=data_ref,
                    partition_ref=_NULL_BLOCK_REF,
                    skeleton_root_ref=skeleton_root_index,
                    bone_block_refs=bone_block_refs,
                )
                skin_ref = len(blocks)
                blocks.append(inst_block)

        # Geometry + transform.
        name_idx = strings.add(obj.name)
        # full_precision=True: works around the pre-existing half-precision
        # BSVertexData(SSE) codec bug documented in
        # docs/REVIEW_2026-07.md finding 9 (the per-record read path
        # ignores the descriptor's full-precision flag and always reads a
        # full Vector3, corrupting every default-mode round-trip). Revert
        # to the smaller half-precision default once that codegen fix lands.
        shape_block = mesh_data_to_bstrishape(mesh_data, name_index=name_idx, full_precision=True)
        translation, rotation, scale = object_transform_to_shape_trs(obj)
        shape_block.translation = translation
        shape_block.rotation = rotation
        shape_block.scale = scale
        shape_block.shader_property = shader_ref
        shape_block.alpha_property = alpha_ref
        shape_block.skin = skin_ref

        shape_index = len(blocks)
        blocks.append(shape_block)
        if skeleton_root_index != _NULL_BLOCK_REF:
            root_node = blocks[skeleton_root_index]
            root_node.children.append(shape_index)
            root_node.num_children = len(root_node.children)
        else:
            roots.append(shape_index)

    header, ctx = _sse_header()
    header.strings = strings.strings
    header.num_strings = len(strings.strings)
    header.max_string_length = max((len(s.value) for s in strings.strings), default=0)
    return BlockTable(
        header=header, blocks=blocks, footer=Footer(num_roots=len(roots), roots=roots), ctx=ctx
    )


class NIFBLEND_OT_export_nif(Operator, ExportHelper):
    """Export selected mesh objects as a Skyrim SE-shaped NIF."""

    bl_idname = "nifblend.export_nif"
    bl_label = "Export NIF"
    bl_options = {"REGISTER"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        meshes = [obj for obj in context.selected_objects if getattr(obj, "type", None) == "MESH"]
        if not meshes:
            self.report({"WARNING"}, "Select at least one mesh object to export")
            return {"CANCELLED"}

        table = build_export_table(meshes)

        try:
            with open(self.filepath, "wb") as fh:
                write_nif(fh, table)
        except Exception as exc:  # - surface any write error to the user
            self.report({"ERROR"}, f"Failed to write {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported {len(meshes)} mesh(es) to {self.filepath!r}")
        return {"FINISHED"}
