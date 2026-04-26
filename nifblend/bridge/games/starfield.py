"""Phase 9d: bridge between :class:`BSGeometry` external mesh refs and Blender.

Walks each non-empty LOD slot on a :class:`BSGeometry` block, resolves
its :attr:`mesh_path` via an injected :class:`ExternalAssetResolver`,
decodes the loose ``.mesh`` file with the Phase 9b decoder, and adapts
the result into the existing :class:`~nifblend.bridge.mesh_in.MeshData`
dataclass so downstream materialisation works unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from nifblend.bridge.external_assets import ExternalAssetResolver
from nifblend.bridge.games.starfield_material import (
    StarfieldMaterialError,
    load_starfield_material,
)
from nifblend.bridge.material_in import MaterialData
from nifblend.bridge.mesh_in import BSGeometryMeshRef, MeshData, bsgeometry_mesh_refs
from nifblend.bridge.skin_in import SkinData, _resolve_bone_names
from nifblend.format.generated.blocks import BSGeometry, BSSkinInstance
from nifblend.format.starfield_mesh import (
    StarfieldMeshData,
    read_starfield_mesh,
)

__all__ = [
    "StarfieldExternalMeshError",
    "StarfieldLODImport",
    "bsgeometry_skin_to_skin_data",
    "decode_external_mesh",
    "find_starfield_material_path",
    "load_bsgeometry_material",
    "resolve_bsgeometry_bone_palette",
    "starfield_mesh_to_mesh_data",
    "walk_bsgeometry_external",
]

_NULL_REF = 0xFFFFFFFF


class StarfieldExternalMeshError(RuntimeError):
    """Raised when a referenced external ``.mesh`` cannot be loaded."""


@dataclass(slots=True)
class StarfieldLODImport:
    """One materialisable LOD level's contents."""

    lod_index: int
    mesh_path: str
    mesh: MeshData


def starfield_mesh_to_mesh_data(
    src: StarfieldMeshData, *, name: str
) -> MeshData:
    """Adapt a :class:`StarfieldMeshData` into the bridge's :class:`MeshData`.

    Bone-weight / bone-index widths are preserved verbatim; downstream
    skinning callers must accept the per-vertex K-wide layout.
    """
    bone_indices_u8 = (
        src.bone_indices.astype(np.uint8, copy=False)
        if src.bone_indices is not None
        else None
    )
    return MeshData(
        name=name,
        positions=src.positions.astype(np.float32, copy=False),
        triangles=src.triangles.astype(np.uint32, copy=False),
        normals=src.normals,
        tangents=src.tangents,
        bitangents=None,
        uv=src.uv,
        vertex_colors=src.colors,
        bone_weights=src.bone_weights,
        bone_indices=bone_indices_u8,
    )


def decode_external_mesh(
    ref: BSGeometryMeshRef,
    *,
    resolver: ExternalAssetResolver,
    name_prefix: str = "",
) -> StarfieldLODImport:
    """Resolve and decode one :class:`BSGeometryMeshRef`.

    Raises :class:`StarfieldExternalMeshError` when the resolver returns
    ``None`` or the on-disk file fails to decode. Empty / unpopulated
    LOD slots (``has_mesh=False``) should be filtered by the caller
    before calling this — passing one in raises immediately.
    """
    if not ref.has_mesh or not ref.mesh_path:
        raise StarfieldExternalMeshError(
            f"LOD{ref.lod_index} has no mesh reference"
        )

    abs_path = resolver.resolve_mesh(ref.mesh_path)
    if abs_path is None:
        raise StarfieldExternalMeshError(
            f"unresolved mesh path: {ref.mesh_path!r}"
        )

    try:
        with Path(abs_path).open("rb") as fh:
            decoded = read_starfield_mesh(fh)
    except (OSError, ValueError, EOFError) as exc:
        raise StarfieldExternalMeshError(
            f"failed to decode {abs_path}: {exc}"
        ) from exc

    name = f"{name_prefix}LOD{ref.lod_index}" if name_prefix else f"LOD{ref.lod_index}"
    return StarfieldLODImport(
        lod_index=ref.lod_index,
        mesh_path=ref.mesh_path,
        mesh=starfield_mesh_to_mesh_data(decoded, name=name),
    )


def walk_bsgeometry_external(
    block: BSGeometry,
    *,
    resolver: ExternalAssetResolver,
    name_prefix: str = "",
) -> tuple[list[StarfieldLODImport], list[str]]:
    """Decode every populated LOD slot on a :class:`BSGeometry`.

    Returns a ``(successes, warnings)`` tuple. Per-slot decode failures
    are caught and surfaced as warning strings rather than aborting the
    whole walk — mirrors the per-block error handling pattern in
    :mod:`nifblend.ops.import_nif`.
    """
    successes: list[StarfieldLODImport] = []
    warnings: list[str] = []
    for ref in bsgeometry_mesh_refs(block):
        if not ref.has_mesh or not ref.mesh_path:
            continue
        try:
            successes.append(
                decode_external_mesh(ref, resolver=resolver, name_prefix=name_prefix)
            )
        except StarfieldExternalMeshError as exc:
            warnings.append(str(exc))
    return successes, warnings


def _resolve_block_name(block: Any, table: Any) -> str | None:
    """Resolve a generated-block ``name`` field into a Python string.

    Mirrors :func:`nifblend.bridge.material_in._resolve_name` but stays
    type-loose so it can apply to any block exposing the schema's
    ``string`` substrate (``BSGeometry``, ``BSLightingShaderProperty``,
    etc.). Returns ``None`` when the name can't be resolved (null ref,
    out-of-range index, missing string table) so callers can decide
    between fallback strategies.
    """
    name_obj = getattr(block, "name", None)
    if name_obj is None:
        return None

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
        return None
    if idx < 0 or idx == _NULL_REF or table is None:
        return None
    strings = getattr(getattr(table, "header", None), "strings", None)
    if not strings or idx >= len(strings):
        return None
    s = strings[idx]
    if s is None:
        return None
    try:
        return bytes(s.value).decode("latin-1")
    except (AttributeError, ValueError):
        return None


def _looks_like_mat_path(value: str | None) -> bool:
    """True when ``value`` is a plausible Starfield ``.mat`` JSON path."""
    if not value:
        return False
    return value.lower().endswith(".mat")


def find_starfield_material_path(
    block: BSGeometry, table: Any
) -> str | None:
    """Discover the ``.mat`` JSON path attached to a Starfield ``BSGeometry``.

    Strategy: follow ``block.shader_property`` to its target block (typically
    a ``BSLightingShaderProperty``), pull the ``name`` field through the
    string-table resolver, and accept it if it ends in ``.mat``. Falls back
    to ``BSGeometry.name`` itself when the shader-property arm yields
    nothing usable. Returns ``None`` when no candidate looks like a
    material path -- callers should treat that as "no material to load"
    rather than an error.
    """
    blocks = getattr(table, "blocks", None) if table is not None else None

    shader_ref = getattr(block, "shader_property", None)
    try:
        ref_int = int(shader_ref) if shader_ref is not None else -1
    except (TypeError, ValueError):
        ref_int = -1
    if blocks is not None and 0 <= ref_int != _NULL_REF and ref_int < len(blocks):
        candidate = _resolve_block_name(blocks[ref_int], table)
        if _looks_like_mat_path(candidate):
            return candidate

    own_name = _resolve_block_name(block, table)
    if _looks_like_mat_path(own_name):
        return own_name
    return None


def load_bsgeometry_material(
    block: BSGeometry,
    table: Any,
    *,
    resolver: ExternalAssetResolver,
    name: str | None = None,
) -> tuple[MaterialData | None, str | None]:
    """Resolve and load the ``.mat`` for a Starfield ``BSGeometry``.

    Returns a ``(material_data, warning)`` tuple. ``material_data`` is
    ``None`` when no material path is discoverable on the block (not an
    error -- some BSGeometry blocks legitimately ship without one) or
    when the load fails. ``warning`` carries a user-visible reason when
    the load was *attempted but failed*; otherwise it is ``None``.
    """
    rel_path = find_starfield_material_path(block, table)
    if rel_path is None:
        return None, None
    try:
        data = load_starfield_material(rel_path, resolver=resolver, name=name)
    except StarfieldMaterialError as exc:
        return None, str(exc)
    return data, None


# ---- Phase 9h: skinning -------------------------------------------------


def resolve_bsgeometry_bone_palette(
    block: BSGeometry, table: Any
) -> list[str] | None:
    """Resolve ``BSGeometry.skin`` to its bone-name palette.

    Returns the positional bone-name list (NiNode names from the
    skeleton-root subtree, with ``"Bone.{i}"`` placeholders for refs
    that fail to resolve), or ``None`` when the geometry has no skin
    instance attached (rigid mesh).
    """
    skin_ref_obj = getattr(block, "skin", None)
    try:
        skin_ref = int(skin_ref_obj) if skin_ref_obj is not None else _NULL_REF
    except (TypeError, ValueError):
        return None
    if skin_ref < 0 or skin_ref == _NULL_REF:
        return None
    blocks = getattr(table, "blocks", None) if table is not None else None
    if not blocks or skin_ref >= len(blocks):
        return None
    skin_inst = blocks[skin_ref]
    if not isinstance(skin_inst, BSSkinInstance):
        return None
    bone_refs = list(getattr(skin_inst, "bones", []) or [])
    return _resolve_bone_names(table, bone_refs)


def bsgeometry_skin_to_skin_data(
    block: BSGeometry,
    table: Any,
    mesh: MeshData,
) -> SkinData | None:
    """Build a :class:`SkinData` from per-vertex influences on a Starfield LOD.

    The Starfield ``.mesh`` decoder fills ``mesh.bone_indices`` /
    ``mesh.bone_weights`` as dense ``(N, K)`` arrays (where ``K`` is
    the file's ``num_weights_per_vertex``). The bone-name palette
    lives on the parent :class:`BSGeometry`'s ``BSSkinInstance``;
    this helper combines both into the sparse :class:`SkinData` shape
    that :func:`apply_skin_to_object` consumes.

    Returns ``None`` when the mesh carries no per-vertex weights or
    when the geometry has no skin instance — caller should treat that
    as "rigid mesh, skip skinning" rather than an error.
    """
    if mesh.bone_indices is None or mesh.bone_weights is None:
        return None
    bone_names = resolve_bsgeometry_bone_palette(block, table)
    if bone_names is None:
        return None

    raw_idx = np.asarray(mesh.bone_indices)
    raw_wt = np.asarray(mesh.bone_weights, dtype=np.float32)
    if raw_idx.size == 0 or raw_wt.size == 0:
        return SkinData(bone_names=bone_names)

    if raw_idx.ndim == 1:
        raw_idx = raw_idx.reshape(-1, 1)
    if raw_wt.ndim == 1:
        raw_wt = raw_wt.reshape(-1, 1)
    n, k = raw_idx.shape
    if raw_wt.shape != (n, k):
        # Mismatched widths -- treat as no skin rather than crash.
        return SkinData(bone_names=bone_names)

    vertex_grid = np.repeat(np.arange(n, dtype=np.uint32), k)
    flat_idx = raw_idx.reshape(-1).astype(np.uint32, copy=False)
    flat_wt = raw_wt.reshape(-1)
    keep = flat_wt > 0.0
    return SkinData(
        bone_names=bone_names,
        vertex_indices=vertex_grid[keep],
        bone_indices=flat_idx[keep],
        weights=flat_wt[keep],
    )
