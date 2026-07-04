"""Import operator wired to the Phase 2 BSTriShape bridge.

Also handles the legacy NiTriShape / NiTriStrips geometry pair used by
Morrowind, Oblivion, Fallout 3 / NV and any pre-Skyrim NIF (Phase 6 step
22). Strips are converted to indexed triangles in
:func:`nifblend.bridge.mesh_in.strips_to_triangles` before reaching Blender,
so the operator only deals in :class:`MeshData`.
"""

from __future__ import annotations

import contextlib

import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from nifblend.bridge.armature_in import (
    compute_world_transforms,
    import_armature,
    world_matrix_to_trs,
)
from nifblend.bridge.external_assets import (
    PrefsExternalAssetResolver,
)
from nifblend.bridge.games.starfield import (
    bsgeometry_skin_to_skin_data,
    find_starfield_material_path,
    load_bsgeometry_material,
    walk_bsgeometry_external,
)
from nifblend.bridge.material_in import (
    import_material,
    material_data_to_blender,
    niclassic_to_material_data,
)
from nifblend.bridge.material_props import set_starfield_material_path
from nifblend.bridge.mesh_in import (
    bsgeometry_mesh_refs,
    import_bstrishape,
    mesh_data_to_blender,
    nitrishape_to_mesh_data,
    nitristrips_to_mesh_data,
)
from nifblend.bridge.object_props import apply_profile_to_object
from nifblend.bridge.skin_in import (
    apply_skin_to_object,
    bstrishape_skin_to_skin_data,
    niskin_to_skin_data,
)
from nifblend.format.generated.blocks import (
    BSGeometry,
    BSTriShape,
    NiAlphaProperty,
    NiMaterialProperty,
    NiNode,
    NiTexturingProperty,
    NiTriShape,
    NiTriShapeData,
    NiTriStrips,
    NiTriStripsData,
)
from nifblend.format.versions import GameProfile, detect_profile
from nifblend.io.block_table import read_nif
from nifblend.preferences import data_root_for, get_prefs

_NULL_REF = 0xFFFFFFFF


def _valid_ref(ref: object) -> int | None:
    """Return ``ref`` as a non-negative ``int``, or ``None`` when it's a null sentinel."""
    if ref is None:
        return None
    idx = int(ref)
    if idx < 0 or idx == _NULL_REF:
        return None
    return idx


def _resolve_block(table, ref: object):
    """Resolve a raw block-table ref into its block, or ``None``."""
    idx = _valid_ref(ref)
    if idx is None or idx >= len(table.blocks):
        return None
    return table.blocks[idx]


def _resolve_skin_ref(shape: object) -> int | None:
    """Return a shape's skin-instance block index, or ``None`` when unset.

    Classic ``NiGeometry``-family shapes (``NiTriShape`` / ``NiTriStrips``)
    populate ``skin_instance``; ``BSTriShape`` populates ``skin``. Both
    field names exist on the generated dataclass (the schema emits both
    across its version-gated read branches) but only one is ever
    meaningfully populated for a given file's version, so checking
    ``skin_instance`` first and falling back to ``skin`` covers both
    without needing an ``isinstance`` check.
    """
    for attr in ("skin_instance", "skin"):
        idx = _valid_ref(getattr(shape, attr, None))
        if idx is not None:
            return idx
    return None


def _decode_shape_skin(shape: object, skin_ref: int, table):
    """Decode ``shape``'s skin into ``(SkinData, skeleton_root_index)``."""
    skin_instance = table.blocks[skin_ref]
    skeleton_root = _valid_ref(getattr(skin_instance, "skeleton_root", None))
    if hasattr(shape, "vertex_data"):
        skin = bstrishape_skin_to_skin_data(table, shape)
    else:
        skin = niskin_to_skin_data(table, skin_ref)
    return skin, skeleton_root


def _resolve_shape_material(
    shape: object,
    table,
    *,
    resolve_texture,
    cache: dict[object, object],
):
    """Resolve + materialise ``shape``'s material, sharing one Blender Material

    across every shape that references the same source block(s) --
    mirrors how a single ``BSLightingShaderProperty`` (or classic
    ``NiMaterialProperty`` / ``NiTexturingProperty`` pair) is commonly
    shared by several shapes in a real NIF.

    Dispatch is keyed on ``isinstance(shape, BSTriShape)``, not on
    whether ``shader_property`` merely looks like a valid ref: classic
    ``NiGeometry``-family shapes (``NiTriShape`` / ``NiTriStrips``)
    declare the same ``shader_property`` / ``alpha_property`` dataclass
    fields as ``BSTriShape`` (the codegen emits every version-gated
    field on one dataclass), but they're never populated by the
    read-side version guard for pre-Skyrim files -- they just sit at
    the dataclass default of ``0``, which is indistinguishable from a
    genuinely valid ref to block 0 if checked by value alone.
    """
    if isinstance(shape, BSTriShape):
        shader_idx = _valid_ref(getattr(shape, "shader_property", None))
        if shader_idx is None:
            return None
        key = ("modern", shader_idx)
        if key in cache:
            return cache[key]
        shader_block = _resolve_block(table, shader_idx)
        if shader_block is None:
            cache[key] = None
            return None
        alpha_block = _resolve_block(table, getattr(shape, "alpha_property", None))
        alpha = alpha_block if isinstance(alpha_block, NiAlphaProperty) else None
        try:
            material = import_material(
                shader_block, table, alpha=alpha, bpy=bpy, resolve_texture=resolve_texture
            )
        except TypeError:
            material = None
        cache[key] = material
        return material

    prop_refs = [
        idx
        for idx in (_valid_ref(r) for r in (getattr(shape, "properties", None) or []))
        if idx is not None
    ]
    if not prop_refs:
        return None
    key = ("classic", tuple(sorted(prop_refs)))
    if key in cache:
        return cache[key]

    material_block = texturing_block = alpha_block = None
    for ref in prop_refs:
        blk = _resolve_block(table, ref)
        if isinstance(blk, NiMaterialProperty) and material_block is None:
            material_block = blk
        elif isinstance(blk, NiTexturingProperty) and texturing_block is None:
            texturing_block = blk
        elif isinstance(blk, NiAlphaProperty) and alpha_block is None:
            alpha_block = blk

    if material_block is None and texturing_block is None:
        cache[key] = None
        return None
    data = niclassic_to_material_data(material_block, texturing_block, table, alpha=alpha_block)
    material = material_data_to_blender(data, bpy=bpy, resolve_texture=resolve_texture)
    cache[key] = material
    return material


def _ensure_armature(
    skeleton_root: int | None,
    table,
    context,
    armature_cache: dict[int, object],
):
    """Build (once) and cache the Blender Armature rooted at ``skeleton_root``."""
    if skeleton_root is None:
        return None
    if skeleton_root in armature_cache:
        return armature_cache[skeleton_root]
    root_block = table.blocks[skeleton_root] if skeleton_root < len(table.blocks) else None
    if not isinstance(root_block, NiNode):
        armature_cache[skeleton_root] = None
        return None
    armature_obj = import_armature(table, skeleton_root, bpy=bpy, context=context)
    armature_cache[skeleton_root] = armature_obj
    return armature_obj


def _apply_shape_transform(
    obj: object, block_index: int, world_transforms: dict[int, object]
) -> None:
    """Place ``obj`` at its NIF-authored world transform, when known.

    Falls back to leaving Blender's newly-created-object default (world
    origin, identity rotation/scale) when the shape wasn't reachable from
    any footer root -- matches prior behaviour for those edge cases
    rather than guessing.
    """
    world = world_transforms.get(block_index)
    if world is None:
        return
    location, euler, scale = world_matrix_to_trs(world)
    with contextlib.suppress(AttributeError, RuntimeError, TypeError):
        obj.location = location
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = euler
        obj.scale = (scale, scale, scale)


def _apply_shape_material_and_skin(
    obj: object,
    shape: object,
    table,
    *,
    resolve_texture,
    material_cache: dict[object, object],
    armature_cache: dict[int, object],
    collection,
    context,
) -> None:
    """Attach material + (skin -> vertex groups + armature parenting) to ``obj``."""
    material = _resolve_shape_material(
        shape, table, resolve_texture=resolve_texture, cache=material_cache
    )
    if material is not None:
        with contextlib.suppress(AttributeError, RuntimeError, TypeError):
            obj.data.materials.append(material)

    skin_ref = _resolve_skin_ref(shape)
    if skin_ref is None:
        return
    skin, skeleton_root = _decode_shape_skin(shape, skin_ref, table)
    with contextlib.suppress(AttributeError, RuntimeError, TypeError):
        apply_skin_to_object(skin, obj)

    armature_obj = _ensure_armature(skeleton_root, table, context, armature_cache)
    if armature_obj is None:
        return
    with contextlib.suppress(AttributeError, RuntimeError, TypeError):
        obj.parent = armature_obj
        modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = armature_obj


class NIFBLEND_OT_import_nif(Operator, ImportHelper):
    """Import a NIF file (BSTriShape + legacy NiTriShape / NiTriStrips meshes)."""

    bl_idname = "nifblend.import_nif"
    bl_label = "Import NIF"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".nif"
    filter_glob: StringProperty(default="*.nif", options={"HIDDEN"})  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        try:
            with open(self.filepath, "rb") as fh:
                table = read_nif(fh)
        except Exception as exc:  # - surface any parse error to the user
            self.report({"ERROR"}, f"Failed to read {self.filepath!r}: {exc}")
            return {"CANCELLED"}

        collection = context.collection
        ctx = table.ctx
        profile = detect_profile(
            int(getattr(ctx, "version", 0)),
            int(getattr(ctx, "user_version", 0)),
            int(getattr(ctx, "bs_version", 0)),
        )

        def _stamp(obj, origin: str) -> None:
            apply_profile_to_object(
                obj,
                profile=profile,
                nif_version=int(getattr(ctx, "version", 0)),
                user_version=int(getattr(ctx, "user_version", 0)),
                bs_version=int(getattr(ctx, "bs_version", 0)),
                source_path=str(self.filepath),
                block_origin=origin,
            )

        # Phase 4: one-time, whole-file setup shared across every shape --
        # world-space placement for every reachable scene-graph block, a
        # texture resolver bound to the detected game's configured Data
        # root, and caches so shapes sharing one material/skeleton block
        # don't rebuild it per shape.
        world_transforms = compute_world_transforms(table)
        prefs = get_prefs(bpy.context)
        data_root = data_root_for(profile, prefs) if prefs is not None else ""
        resolve_texture = None
        if data_root:
            mode = str(
                getattr(prefs, "texture_resolution_mode", "CASE_INSENSITIVE") or "CASE_INSENSITIVE"
            )
            resolve_texture = PrefsExternalAssetResolver(
                data_root=data_root, mode=mode
            ).resolve_texture
        material_cache: dict[object, object] = {}
        armature_cache: dict[int, object] = {}

        imported = 0
        skipped: list[str] = []
        for block_index, block in enumerate(table.blocks):
            if isinstance(block, BSTriShape):
                mesh = import_bstrishape(block, table)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, type(block).__name__)
                _apply_shape_transform(obj, block_index, world_transforms)
                _apply_shape_material_and_skin(
                    obj,
                    block,
                    table,
                    resolve_texture=resolve_texture,
                    material_cache=material_cache,
                    armature_cache=armature_cache,
                    collection=collection,
                    context=context,
                )
                imported += 1
            elif isinstance(block, NiTriShape):
                data = _resolve_geometry_data(table, block.data, NiTriShapeData)
                if data is None:
                    skipped.append("NiTriShape (missing data)")
                    continue
                mdata = nitrishape_to_mesh_data(block, data, table)
                mesh = mesh_data_to_blender(mdata)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, "NiTriShape")
                _apply_shape_transform(obj, block_index, world_transforms)
                _apply_shape_material_and_skin(
                    obj,
                    block,
                    table,
                    resolve_texture=resolve_texture,
                    material_cache=material_cache,
                    armature_cache=armature_cache,
                    collection=collection,
                    context=context,
                )
                imported += 1
            elif isinstance(block, NiTriStrips):
                data = _resolve_geometry_data(table, block.data, NiTriStripsData)
                if data is None:
                    skipped.append("NiTriStrips (missing data)")
                    continue
                mdata = nitristrips_to_mesh_data(block, data, table)
                mesh = mesh_data_to_blender(mdata)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, "NiTriStrips")
                _apply_shape_transform(obj, block_index, world_transforms)
                _apply_shape_material_and_skin(
                    obj,
                    block,
                    table,
                    resolve_texture=resolve_texture,
                    material_cache=material_cache,
                    armature_cache=armature_cache,
                    collection=collection,
                    context=context,
                )
                imported += 1
            elif isinstance(block, BSGeometry):
                imported += self._import_bsgeometry(
                    block,
                    block_index,
                    table,
                    profile,
                    collection,
                    _stamp,
                    skipped,
                    world_transforms=world_transforms,
                )
            else:
                skipped.append(type(block).__name__)

        if not imported:
            self.report(
                {"WARNING"},
                f"No geometry blocks in {self.filepath!r}; skipped: {sorted(set(skipped))}",
            )
            return {"CANCELLED"}

        self.report(
            {"INFO"},
            f"Imported {imported} mesh(es); skipped {len(skipped)} other block(s)",
        )
        return {"FINISHED"}

    def _import_bsgeometry(
        self,
        block: BSGeometry,
        block_index: int,
        table,
        profile: GameProfile,
        collection,
        stamp,
        skipped: list[str],
        *,
        world_transforms: dict[int, object],
    ) -> int:
        """Materialise every populated LOD slot on a Starfield ``BSGeometry``.

        For non-Starfield contexts (FO76 ``BSGeometry`` without a configured
        Data root, etc.) the slots are surfaced as skip reasons rather than
        attempted decodes -- the bridge layer needs an
        :class:`ExternalAssetResolver` to do anything meaningful, and we
        do not want to silently miss assets.
        """
        refs = bsgeometry_mesh_refs(block)
        populated = [r for r in refs if r.has_mesh and r.mesh_path]
        if not populated:
            skipped.append("BSGeometry (no LOD slots populated)")
            return 0

        if profile != GameProfile.STARFIELD:
            skipped.append(f"BSGeometry ({len(populated)} LOD slot(s); non-Starfield context)")
            return 0

        prefs = get_prefs(bpy.context)
        data_root = data_root_for(GameProfile.STARFIELD, prefs)
        if not data_root:
            self.report(
                {"WARNING"},
                "BSGeometry encountered but Starfield Data root is not configured",
            )
            skipped.append(f"BSGeometry ({len(populated)} LOD slot(s); no data root)")
            return 0

        mode = str(
            getattr(prefs, "texture_resolution_mode", "CASE_INSENSITIVE") or "CASE_INSENSITIVE"
        )
        resolver = PrefsExternalAssetResolver(data_root=data_root, mode=mode)
        successes, warnings = walk_bsgeometry_external(
            block, resolver=resolver, name_prefix="BSGeometry_"
        )
        for warning in warnings:
            self.report({"WARNING"}, warning)

        # Phase 9g: resolve and load the matching .mat material once per
        # BSGeometry block (it's shared across LOD slots).
        material = None
        mat_rel_path = find_starfield_material_path(block, table)
        mat_data, mat_warning = load_bsgeometry_material(block, table, resolver=resolver)
        if mat_warning:
            self.report({"WARNING"}, mat_warning)
        if mat_data is not None:
            try:
                material = material_data_to_blender(
                    mat_data,
                    bpy=bpy,
                    resolve_texture=resolver.resolve_texture,
                )
            except (AttributeError, RuntimeError, TypeError) as exc:
                self.report(
                    {"WARNING"},
                    f"Failed to materialise Starfield material: {exc}",
                )
                material = None
        # Phase 9i: stamp the .mat rel-path so the reload operator can
        # re-resolve the manifest later. Stamped even when the load
        # failed so the user can fix the Data root and retry.
        if material is not None and mat_rel_path:
            with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                set_starfield_material_path(material, mat_rel_path)

        try:
            parent_collection = bpy.data.collections.new("BSGeometry")
            collection.children.link(parent_collection)
            target_collection = parent_collection
        except (AttributeError, RuntimeError, TypeError):
            target_collection = collection
        imported = 0
        for imp in successes:
            mesh = mesh_data_to_blender(imp.mesh)
            if material is not None:
                with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                    mesh.materials.append(material)
            obj = bpy.data.objects.new(mesh.name, mesh)
            target_collection.objects.link(obj)
            stamp(obj, "BSGeometry")
            # Phase 4: place the LOD object at the BSGeometry block's own
            # NIF-authored world transform (all LOD levels share it).
            _apply_shape_transform(obj, block_index, world_transforms)
            # Phase 9h: per-vertex bone influences -> Blender vertex groups.
            skin = bsgeometry_skin_to_skin_data(block, table, imp.mesh)
            if skin is not None:
                with contextlib.suppress(AttributeError, RuntimeError, TypeError):
                    apply_skin_to_object(skin, obj)
            imported += 1
        if not imported and not warnings:
            skipped.append(f"BSGeometry ({len(populated)} LOD slot(s); no decodes)")
        return imported


def _resolve_geometry_data(table, ref: int, expected_type):
    """Resolve a ``NiTriShape``/``NiTriStrips`` data ref into the data block.

    Returns ``None`` when the ref is unset (negative / 0xFFFFFFFF) or points
    at a block of the wrong type — the caller skips that shape with a
    user-visible message rather than crashing the import.
    """
    if ref is None or ref < 0 or ref == 0xFFFFFFFF:
        return None
    if ref >= len(table.blocks):
        return None
    block = table.blocks[ref]
    if not isinstance(block, expected_type):
        return None
    return block
