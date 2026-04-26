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

from nifblend.bridge.external_assets import (
    PrefsExternalAssetResolver,
)
from nifblend.bridge.games.starfield import (
    bsgeometry_skin_to_skin_data,
    find_starfield_material_path,
    load_bsgeometry_material,
    walk_bsgeometry_external,
)
from nifblend.bridge.material_in import material_data_to_blender
from nifblend.bridge.material_props import set_starfield_material_path
from nifblend.bridge.mesh_in import (
    bsgeometry_mesh_refs,
    import_bstrishape,
    mesh_data_to_blender,
    nitrishape_to_mesh_data,
    nitristrips_to_mesh_data,
)
from nifblend.bridge.object_props import apply_profile_to_object
from nifblend.bridge.skin_in import apply_skin_to_object
from nifblend.format.generated.blocks import (
    BSGeometry,
    BSTriShape,
    NiTriShape,
    NiTriShapeData,
    NiTriStrips,
    NiTriStripsData,
)
from nifblend.format.versions import GameProfile, detect_profile
from nifblend.io.block_table import read_nif
from nifblend.preferences import data_root_for, get_prefs


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

        imported = 0
        skipped: list[str] = []
        for block in table.blocks:
            if isinstance(block, BSTriShape):
                mesh = import_bstrishape(block, table)
                obj = bpy.data.objects.new(mesh.name, mesh)
                collection.objects.link(obj)
                _stamp(obj, type(block).__name__)
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
                imported += 1
            elif isinstance(block, BSGeometry):
                imported += self._import_bsgeometry(
                    block, table, profile, collection, _stamp, skipped
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
        table,
        profile: GameProfile,
        collection,
        stamp,
        skipped: list[str],
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
            skipped.append(
                f"BSGeometry ({len(populated)} LOD slot(s); non-Starfield context)"
            )
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
            getattr(prefs, "texture_resolution_mode", "CASE_INSENSITIVE")
            or "CASE_INSENSITIVE"
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
        mat_data, mat_warning = load_bsgeometry_material(
            block, table, resolver=resolver
        )
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
