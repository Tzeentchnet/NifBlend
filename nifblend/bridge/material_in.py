"""Material side of the NIF ↔ Blender bridge (Phase 3 step 11, import).

Decodes Bethesda shader properties (Skyrim SE focus: ``bs_version == 100``)
into a plain :class:`MaterialData` dataclass, then materialises that into a
``bpy.types.Material`` with a small, predictable Principled BSDF node graph.

The split mirrors :mod:`nifblend.bridge.mesh_in`:

* :func:`bslighting_to_material_data` and :func:`bseffect_to_material_data`
  are pure functions over the codegen-emitted block dataclasses; they need
  the surrounding :class:`~nifblend.io.block_table.BlockTable` only to
  resolve the ``texture_set`` u32 ref into a
  :class:`~nifblend.format.generated.blocks.BSShaderTextureSet`.
* :func:`material_data_to_blender` builds the ``bpy.types.Material``,
  taking ``bpy`` as a kwarg so the wrapper is testable headlessly.

Texture *path resolution* against the user's per-game Data root is
deliberately outside this module — it's a preferences concern. Callers
pass a ``resolve_texture: Callable[[str], str | None]`` that turns a
NIF-relative path (``textures/foo/bar_d.dds``) into an absolute disk
path; the bridge falls back to using the raw NIF-relative string as the
image name when the callable returns ``None`` (or isn't supplied), which
is what we want for headless tests and missing-asset modder workflows.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from nifblend.format.generated.blocks import (
    BSEffectShaderProperty,
    BSLightingShaderProperty,
    BSShaderPPLightingProperty,
    BSShaderTextureSet,
    NiAlphaProperty,
    NiMaterialProperty,
    NiSourceTexture,
    NiTexturingProperty,
)
from nifblend.io.block_table import BlockTable

__all__ = [
    "CLASSIC_TEXTURE_SLOT_NAMES",
    "TEXTURE_SLOT_NAMES",
    "MaterialData",
    "bseffect_to_material_data",
    "bslighting_to_material_data",
    "bsshaderpplighting_to_material_data",
    "import_material",
    "material_data_to_blender",
    "niclassic_to_material_data",
]


# Slot ordering for BSShaderTextureSet.textures on Skyrim SE / FO4
# (bs_version >= 83). The list is exactly 9 entries on Fallout 4 and 8
# on Skyrim; we treat anything past index 7 as "extension slots" that
# round-trip but don't get plugged into the shader graph by default.
TEXTURE_SLOT_NAMES: tuple[str, ...] = (
    "diffuse",      # 0
    "normal",       # 1
    "glow",         # 2 (also "skin tint" / subsurface for SLSF1_Facegen)
    "height",       # 3 parallax / heightmap
    "environment",  # 4 cubemap
    "env_mask",     # 5
    "subsurface",   # 6 / "tint" on SLSF1_Skin_Tint
    "backlight",    # 7 (specular on FO4 / SF)
)


# Slot ordering for the classic Morrowind / Oblivion ``NiTexturingProperty``
# (one ``TexDesc`` field per slot). The slot names are aligned with
# :data:`TEXTURE_SLOT_NAMES` where the meaning overlaps so a single
# ``MaterialData.textures`` dict can describe either lineage.
CLASSIC_TEXTURE_SLOT_NAMES: tuple[str, ...] = (
    "diffuse",      # base_texture
    "dark",         # dark_texture
    "detail",       # detail_texture
    "gloss",        # gloss_texture
    "glow",         # glow_texture
    "bump",         # bump_map_texture
    "normal",       # normal_texture (>= 20.2.0.5)
    "height",       # parallax_texture (>= 20.2.0.5)
    "decal0",       # decal_0_texture
    "decal1",       # decal_1_texture
    "decal2",       # decal_2_texture
    "decal3",       # decal_3_texture
)


# Sentinel for "no block referenced" in NIF u32 cross-refs. The schema
# uses both ``-1`` (signed view) and ``0xFFFFFFFF`` (unsigned view); the
# generated dataclasses keep them as plain ints, so we accept either.
_NULL_REF = 0xFFFFFFFF


@dataclass(slots=True)
class MaterialData:
    """Bridge-layer description of a single NIF material.

    Mirrors the shape of :class:`~nifblend.bridge.mesh_in.MeshData`: pure
    Python (no Blender imports), every NIF-side concept reduced to a
    small set of typed fields. Anything that doesn't map cleanly to a
    Principled BSDF input — shader flags, the raw ``shader_type`` enum,
    the unparsed alpha-property bitfield — is kept here verbatim so the
    Phase 3 step 13 ``PropertyGroup`` can preserve it round-trip.
    """

    name: str
    # Origin: which shader-property class produced this MaterialData. Used by
    # the export side (Phase 3 step 12) to pick the right output block.
    origin: str = "BSLightingShaderProperty"

    # Albedo / colour layer.
    base_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    emissive_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    emissive_multiple: float = 0.0
    specular_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    specular_strength: float = 1.0

    # Surface shape.
    alpha: float = 1.0
    glossiness: float = 80.0
    smoothness: float = 1.0  # SSE-and-later equivalent

    # UV transform (TexCoord on the NIF side; Blender plugs into a
    # Mapping node).
    uv_offset: tuple[float, float] = (0.0, 0.0)
    uv_scale: tuple[float, float] = (1.0, 1.0)

    # Texture paths, indexed by `TEXTURE_SLOT_NAMES`. Stored as raw NIF
    # path strings (``textures/...``) — resolution to a disk file is a
    # preferences concern handled in `material_data_to_blender`.
    textures: dict[str, str] = field(default_factory=dict)

    # Alpha state from a sibling NiAlphaProperty.
    alpha_blend: bool = False
    alpha_test: bool = False
    alpha_threshold: int = 0

    # Preserved verbatim for round-trip even though Blender can't represent them.
    shader_type: int = 0
    shader_flags_1: int = 0
    shader_flags_2: int = 0

    # FO3/NV BSShaderPPLightingProperty extras (preserved verbatim; meaningless
    # for the SSE BSLighting/BSEffect paths, which leave them at defaults).
    # ``flags`` is the legacy u16 :class:`BSShaderFlags` word that lives on
    # ``BSShaderPPLightingProperty`` *in addition* to the 32-bit ``shader_flags``
    # / ``shader_flags_2`` pair (hence not the same field as ``shader_flags_1``).
    pp_flags: int = 0
    environment_map_scale: float = 1.0
    texture_clamp_mode: int = 0
    refraction_strength: float = 0.0
    refraction_fire_period: int = 0
    parallax_max_passes: float = 0.0
    parallax_scale: float = 0.0

    # Classic Morrowind / Oblivion (``NiMaterialProperty`` +
    # ``NiTexturingProperty``) extras. Preserved verbatim for round-trip
    # so the legacy stack survives a Blender edit cycle even though
    # Principled BSDF can't represent ambient/diffuse-as-separate-fields
    # or the legacy apply mode.
    ambient_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    diffuse_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    texturing_apply_mode: int = 2  # APPLY_MODULATE — Morrowind default
    texturing_flags: int = 0  # raw u16 NiTexturingProperty.flags
    texture_count: int = 7  # NiTexturingProperty.texture_count classic default


# ---- decoders -------------------------------------------------------------


def bslighting_to_material_data(
    block: BSLightingShaderProperty,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    alpha: NiAlphaProperty | None = None,
) -> MaterialData:
    """Decode a :class:`BSLightingShaderProperty` into a :class:`MaterialData`."""
    resolved_name = name if name is not None else _resolve_name(block, table)
    data = MaterialData(name=resolved_name, origin="BSLightingShaderProperty")

    data.shader_type = int(block.shader_type)
    data.shader_flags_1 = int(block.shader_flags_1)
    data.shader_flags_2 = int(block.shader_flags_2)

    if block.emissive_color is not None:
        data.emissive_color = (
            float(block.emissive_color.r),
            float(block.emissive_color.g),
            float(block.emissive_color.b),
        )
    data.emissive_multiple = float(block.emissive_multiple)

    if block.specular_color is not None:
        data.specular_color = (
            float(block.specular_color.r),
            float(block.specular_color.g),
            float(block.specular_color.b),
        )
    data.specular_strength = float(block.specular_strength)

    data.alpha = float(block.alpha)
    data.glossiness = float(block.glossiness)
    data.smoothness = float(block.smoothness)

    _apply_uv_xform(data, block.uv_offset, block.uv_scale)

    # Resolve the BSShaderTextureSet if the table is available.
    texture_set = _resolve_texture_set(block.texture_set, table)
    if texture_set is not None:
        _populate_textures(data, texture_set)

    _apply_alpha_property(data, alpha)
    return data


def bseffect_to_material_data(
    block: BSEffectShaderProperty,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    alpha: NiAlphaProperty | None = None,
) -> MaterialData:
    """Decode a :class:`BSEffectShaderProperty` into a :class:`MaterialData`."""
    resolved_name = name if name is not None else _resolve_name(block, table)
    data = MaterialData(name=resolved_name, origin="BSEffectShaderProperty")

    data.shader_type = int(block.shader_type)
    data.shader_flags_1 = int(block.shader_flags_1)
    data.shader_flags_2 = int(block.shader_flags_2)

    if block.base_color is not None:
        data.base_color = (
            float(block.base_color.r),
            float(block.base_color.g),
            float(block.base_color.b),
            float(block.base_color.a),
        )
    if block.emittance_color is not None:
        data.emissive_color = (
            float(block.emittance_color.r),
            float(block.emittance_color.g),
            float(block.emittance_color.b),
        )
    # BSEffect uses base_color_scale as the emissive multiplier in-game.
    data.emissive_multiple = float(block.base_color_scale)

    _apply_uv_xform(data, block.uv_offset, block.uv_scale)

    # Effect shaders carry their textures inline rather than via a TextureSet.
    for slot, attr in (
        ("diffuse", "source_texture"),
        ("environment", "env_map_texture"),
        ("env_mask", "env_mask_texture"),
        ("normal", "normal_texture"),
        ("glow", "emit_gradient_texture"),
    ):
        path = _sized_string_to_str(getattr(block, attr, None))
        if path:
            data.textures[slot] = path

    _apply_alpha_property(data, alpha)
    return data


def bsshaderpplighting_to_material_data(
    block: BSShaderPPLightingProperty,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    alpha: NiAlphaProperty | None = None,
) -> MaterialData:
    """Decode a :class:`BSShaderPPLightingProperty` (FO3 / FNV) into MaterialData.

    The pre-Skyrim Bethesda lighting shader carries a different field
    layout than :class:`BSLightingShaderProperty`: a single 32-bit
    ``shader_flags`` (no ``shader_flags_2``), a u16 :class:`BSShaderFlags`
    ``flags`` word, ``environment_map_scale`` / ``texture_clamp_mode``
    constants, refraction + parallax scalars (gated on ``bs_version >
    14`` and ``> 24`` respectively), and a ``texture_set`` u32 ref to a
    :class:`BSShaderTextureSet` whose slot ordering matches the first
    six of :data:`TEXTURE_SLOT_NAMES` (diffuse, normal, glow, height,
    environment, env_mask).

    Fields that don't survive Blender's Principled BSDF natively are
    preserved on the typed PropertyGroup (Phase 3 step 13) so an
    ``import → edit → export`` round-trip stays lossless.
    """
    resolved_name = name if name is not None else _resolve_name(block, table)
    data = MaterialData(name=resolved_name, origin="BSShaderPPLightingProperty")

    data.shader_type = int(block.shader_type)
    data.shader_flags_1 = int(block.shader_flags)
    # No second 32-bit word in the FO3/NV layout; keep ``shader_flags_2``
    # at its codegen default. ``shader_flags_2`` on the schema is a
    # *separate* u32 here, but we surface it on the same PropertyGroup
    # slot the SSE path uses so a single editor field covers both.
    data.shader_flags_2 = int(block.shader_flags_2)

    data.pp_flags = int(block.flags) & 0xFFFF
    data.environment_map_scale = float(block.environment_map_scale)
    data.texture_clamp_mode = int(block.texture_clamp_mode)
    data.refraction_strength = float(block.refraction_strength)
    data.refraction_fire_period = int(block.refraction_fire_period)
    data.parallax_max_passes = float(block.parallax_max_passes)
    data.parallax_scale = float(block.parallax_scale)

    if block.emissive_color is not None:
        data.emissive_color = (
            float(block.emissive_color.r),
            float(block.emissive_color.g),
            float(block.emissive_color.b),
        )
        # FO3 uses the alpha channel of the inline emissive Color4 as
        # the emissive multiplier (no separate ``emissive_multiple``).
        data.emissive_multiple = float(block.emissive_color.a)

    texture_set = _resolve_texture_set(block.texture_set, table)
    if texture_set is not None:
        _populate_textures(data, texture_set)

    _apply_alpha_property(data, alpha)
    return data


def niclassic_to_material_data(
    material: NiMaterialProperty | None,
    texturing: NiTexturingProperty | None,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    alpha: NiAlphaProperty | None = None,
) -> MaterialData:
    """Decode the classic Morrowind / Oblivion material stack.

    The pre-Skyrim NIF lineage attaches up to three sibling property
    blocks to a :class:`NiTriShape`:

    * :class:`NiMaterialProperty` — ambient / diffuse / specular /
      emissive colours, glossiness, alpha. Optional.
    * :class:`NiTexturingProperty` — per-slot :class:`TexDesc`
      references into :class:`NiSourceTexture` blocks. Optional.
    * :class:`NiAlphaProperty` — same shape Phase 3 already handles.

    Either property block may be absent (a mesh with only a texturing
    property is legal); when both are missing this is essentially a
    no-op that still records ``alpha`` state. Texture paths are pulled
    from the referenced :class:`NiSourceTexture` ``file_name`` (a
    :class:`FilePath` compound), which carries a :class:`SizedString`
    for ``ctx.version <= 20.0.0.5`` (Morrowind / Oblivion / FO3 / NV)
    and a string-table index for the modern path.
    """
    resolved_name = name
    if resolved_name is None:
        if material is not None:
            resolved_name = _resolve_name(material, table)
        elif texturing is not None:
            resolved_name = _resolve_name(texturing, table)
        else:
            resolved_name = "NiMaterialProperty"

    data = MaterialData(name=resolved_name, origin="NiMaterialProperty")

    if material is not None:
        data.shader_type = int(material.shader_type)
        if material.ambient_color is not None:
            data.ambient_color = (
                float(material.ambient_color.r),
                float(material.ambient_color.g),
                float(material.ambient_color.b),
            )
        if material.diffuse_color is not None:
            data.diffuse_color = (
                float(material.diffuse_color.r),
                float(material.diffuse_color.g),
                float(material.diffuse_color.b),
            )
            r, g, b = data.diffuse_color
            data.base_color = (r, g, b, float(material.alpha))
        if material.specular_color is not None:
            data.specular_color = (
                float(material.specular_color.r),
                float(material.specular_color.g),
                float(material.specular_color.b),
            )
        if material.emissive_color is not None:
            data.emissive_color = (
                float(material.emissive_color.r),
                float(material.emissive_color.g),
                float(material.emissive_color.b),
            )
        data.glossiness = float(material.glossiness)
        data.alpha = float(material.alpha)
        data.emissive_multiple = float(material.emissive_mult)

    if texturing is not None:
        data.texturing_apply_mode = int(texturing.apply_mode)
        data.texturing_flags = int(texturing.flags) & 0xFFFF if isinstance(
            texturing.flags, int
        ) else 0
        data.texture_count = int(texturing.texture_count)
        for slot, attr in (
            ("diffuse", "base_texture"),
            ("dark", "dark_texture"),
            ("detail", "detail_texture"),
            ("gloss", "gloss_texture"),
            ("glow", "glow_texture"),
            ("bump", "bump_map_texture"),
            ("normal", "normal_texture"),
            ("height", "parallax_texture"),
            ("decal0", "decal_0_texture"),
            ("decal1", "decal_1_texture"),
            ("decal2", "decal_2_texture"),
            ("decal3", "decal_3_texture"),
        ):
            tex_desc = getattr(texturing, attr, None)
            if tex_desc is None:
                continue
            path = _resolve_source_texture_path(tex_desc.source, table)
            if path:
                data.textures[slot] = path

    _apply_alpha_property(data, alpha)
    return data


# ---- Blender wrapper ------------------------------------------------------


def material_data_to_blender(
    data: MaterialData,
    *,
    bpy: Any = None,
    resolve_texture: Callable[[str], str | None] | None = None,
) -> Any:
    """Build a ``bpy.types.Material`` with a Principled BSDF graph.

    The graph is intentionally small and predictable so the export side
    (Phase 3 step 12) can inspect it deterministically:

        Image(diffuse) → Principled.Base Color
        Image(normal)  → Normal Map → Principled.Normal
        Image(glow)    → Principled.Emission
        constants for base_color, alpha, roughness (= 1 - smoothness),
            metallic (= specular_strength)

    Texture paths are resolved through ``resolve_texture`` if given;
    otherwise the raw NIF-relative path is used as the image's
    ``filepath`` and ``name`` so subsequent reload picks up whatever the
    user wires up via preferences.
    """
    if bpy is None:
        import bpy as _bpy

        bpy = _bpy

    mat = bpy.data.materials.new(name=data.name)
    mat.use_nodes = True
    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Constants the shader-property carries directly.
    bsdf.inputs["Base Color"].default_value = data.base_color
    bsdf.inputs["Alpha"].default_value = data.alpha
    # Smoothness in [0,1] → roughness via 1 - smoothness; clamp to [0,1].
    roughness = max(0.0, min(1.0, 1.0 - data.smoothness))
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = roughness
    # Specular strength in NIF is roughly the metallic equivalent for SSE.
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = max(
            0.0, min(1.0, data.specular_strength)
        )
    # Emission colour × multiplier.
    em_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
    if em_input is not None:
        r, g, b = data.emissive_color
        em_input.default_value = (r, g, b, 1.0)
    em_strength = bsdf.inputs.get("Emission Strength")
    if em_strength is not None:
        em_strength.default_value = data.emissive_multiple

    # Texture nodes for the slots the shader graph cares about.
    _hook_texture(bpy, tree, bsdf, data, "diffuse", "Base Color", resolve_texture, y=300)
    _hook_normal_map(bpy, tree, bsdf, data, resolve_texture, y=0)
    _hook_texture(bpy, tree, bsdf, data, "glow", "Emission Color", resolve_texture, y=-300)

    # Alpha-property routing. Blender's blend modes map cleanly onto NIF semantics.
    if data.alpha_blend:
        mat.blend_method = "BLEND"
    elif data.alpha_test:
        mat.blend_method = "CLIP"
        mat.alpha_threshold = data.alpha_threshold / 255.0

    # Stash NIF-only state on the typed PropertyGroup so export can
    # restore exactly what Blender's Principled BSDF can't represent.
    from .material_props import apply_material_data_to_props

    apply_material_data_to_props(mat, data)

    return mat


def import_material(
    block: BSLightingShaderProperty | BSEffectShaderProperty | BSShaderPPLightingProperty,
    table: BlockTable | None = None,
    *,
    name: str | None = None,
    alpha: NiAlphaProperty | None = None,
    bpy: Any = None,
    resolve_texture: Callable[[str], str | None] | None = None,
) -> Any:
    """Convenience: decode + materialise in one call."""
    if isinstance(block, BSLightingShaderProperty):
        data = bslighting_to_material_data(block, table, name=name, alpha=alpha)
    elif isinstance(block, BSEffectShaderProperty):
        data = bseffect_to_material_data(block, table, name=name, alpha=alpha)
    elif isinstance(block, BSShaderPPLightingProperty):
        data = bsshaderpplighting_to_material_data(block, table, name=name, alpha=alpha)
    else:
        raise TypeError(
            f"unsupported shader property block type: {type(block).__name__!r}"
        )
    return material_data_to_blender(data, bpy=bpy, resolve_texture=resolve_texture)


# ---- private helpers ------------------------------------------------------


def _resolve_name(
    block: BSLightingShaderProperty | BSEffectShaderProperty | BSShaderPPLightingProperty,
    table: BlockTable | None,
) -> str:
    """Resolve the shader-property's ``name`` into a Python string.

    Identical strategy to :func:`nifblend.bridge.mesh_in._resolve_name` —
    handle both the modern (>= 20.1.0.3) string-table-index form and the
    legacy inline ``SizedString``.
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
    if idx < 0 or idx == _NULL_REF or table is None:
        return type(block).__name__
    strings = table.header.strings
    if idx >= len(strings):
        return type(block).__name__
    s = strings[idx]
    if s is None:
        return type(block).__name__
    return bytes(s.value).decode("latin-1")


def _resolve_texture_set(
    ref: int,
    table: BlockTable | None,
) -> BSShaderTextureSet | None:
    """Look up a BSShaderTextureSet by raw u32 block ref, defensively."""
    if table is None:
        return None
    try:
        ref_int = int(ref)
    except (TypeError, ValueError):
        return None
    if ref_int < 0 or ref_int == _NULL_REF or ref_int >= len(table.blocks):
        return None
    candidate = table.blocks[ref_int]
    if isinstance(candidate, BSShaderTextureSet):
        return candidate
    return None


def _resolve_source_texture_path(
    ref: int,
    table: BlockTable | None,
) -> str:
    """Resolve a ``TexDesc.source`` i32 ref into a NIF-relative path string.

    Returns ``""`` when ``table`` is missing, the ref is null
    (``-1`` / ``0xFFFFFFFF``), out of range, or the target block isn't
    a :class:`NiSourceTexture` (defensive — a corrupt NIF could point
    elsewhere). The :class:`NiSourceTexture.file_name` is a
    :class:`FilePath` compound that carries either an inline
    :class:`SizedString` (legacy ``ctx.version <= 20.0.0.5``) or a
    string-table index (modern); both shapes are handled by walking
    ``.string`` first then falling back to ``.index`` against the
    header's string table.
    """
    if table is None:
        return ""
    try:
        ref_int = int(ref)
    except (TypeError, ValueError):
        return ""
    if ref_int < 0 or ref_int == _NULL_REF or ref_int >= len(table.blocks):
        return ""
    src = table.blocks[ref_int]
    if not isinstance(src, NiSourceTexture):
        return ""
    fp = src.file_name
    if fp is None:
        return ""
    inline = getattr(fp, "string", None)
    if inline is not None:
        try:
            return bytes(inline.value).decode("latin-1")
        except (AttributeError, ValueError):
            pass
    idx = getattr(fp, "index", None)
    if idx is None:
        return ""
    try:
        idx_int = int(idx)
    except (TypeError, ValueError):
        return ""
    if idx_int < 0 or idx_int == _NULL_REF:
        return ""
    strings = table.header.strings
    if idx_int >= len(strings):
        return ""
    s = strings[idx_int]
    if s is None:
        return ""
    return bytes(s.value).decode("latin-1")


def _populate_textures(data: MaterialData, texture_set: BSShaderTextureSet) -> None:
    """Copy non-empty BSShaderTextureSet slots into MaterialData.textures."""
    for i, sized in enumerate(texture_set.textures):
        if i >= len(TEXTURE_SLOT_NAMES):
            break
        path = _sized_string_to_str(sized)
        if path:
            data.textures[TEXTURE_SLOT_NAMES[i]] = path


def _apply_uv_xform(data: MaterialData, offset: Any, scale: Any) -> None:
    if offset is not None:
        data.uv_offset = (float(offset.u), float(offset.v))
    if scale is not None:
        data.uv_scale = (float(scale.u), float(scale.v))


def _apply_alpha_property(data: MaterialData, alpha: NiAlphaProperty | None) -> None:
    if alpha is None:
        return
    flags = alpha.flags
    flags_int = int(flags) if flags is not None else 0
    # Per the schema's AlphaFlags bitfield: bit 0 = alpha-blend, bit 9 = alpha-test.
    data.alpha_blend = bool(flags_int & 0x0001)
    data.alpha_test = bool(flags_int & 0x0200)
    data.alpha_threshold = int(alpha.threshold)


def _sized_string_to_str(s: Any) -> str:
    """Decode a SizedString-shaped value (or the codegen ``string`` Compound)."""
    if s is None:
        return ""
    # Inline SizedString or "string" with `.string` SizedString.
    inner = getattr(s, "string", None)
    target = inner if inner is not None else s
    value = getattr(target, "value", None)
    if value is None:
        return ""
    try:
        return bytes(value).decode("latin-1")
    except (TypeError, ValueError):
        return ""


def _hook_texture(
    bpy: Any,
    tree: Any,
    bsdf: Any,
    data: MaterialData,
    slot: str,
    bsdf_input: str,
    resolve_texture: Callable[[str], str | None] | None,
    *,
    y: float,
) -> None:
    """Wire an Image Texture node into a Principled BSDF input if the slot is set."""
    path = data.textures.get(slot)
    if not path:
        return
    target_input = bsdf.inputs.get(bsdf_input)
    if target_input is None:
        return
    image = _make_image(bpy, path, resolve_texture)
    node = tree.nodes.new("ShaderNodeTexImage")
    node.location = (-300, y)
    node.image = image
    tree.links.new(node.outputs["Color"], target_input)


def _hook_normal_map(
    bpy: Any,
    tree: Any,
    bsdf: Any,
    data: MaterialData,
    resolve_texture: Callable[[str], str | None] | None,
    *,
    y: float,
) -> None:
    path = data.textures.get("normal")
    if not path:
        return
    target_input = bsdf.inputs.get("Normal")
    if target_input is None:
        return
    image = _make_image(bpy, path, resolve_texture)
    if hasattr(image, "colorspace_settings"):
        image.colorspace_settings.name = "Non-Color"
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.location = (-500, y)
    tex.image = image
    nm = tree.nodes.new("ShaderNodeNormalMap")
    nm.location = (-150, y)
    tree.links.new(tex.outputs["Color"], nm.inputs["Color"])
    tree.links.new(nm.outputs["Normal"], target_input)


def _make_image(
    bpy: Any,
    nif_path: str,
    resolve_texture: Callable[[str], str | None] | None,
) -> Any:
    """Create or fetch a ``bpy.types.Image`` for the given NIF-relative path."""
    images = bpy.data.images
    existing = images.get(nif_path)
    if existing is not None:
        return existing
    abs_path: str | None = None
    if resolve_texture is not None:
        abs_path = resolve_texture(nif_path)
    if abs_path:
        # `load` mirrors `bpy.data.images.load`; we set check_existing so a
        # second material referencing the same texture re-uses the image.
        try:
            return images.load(abs_path, check_existing=True)
        except (RuntimeError, OSError):
            pass
    # Fall back to a placeholder image whose name == the NIF path so the
    # user can later bind it manually.
    return images.new(name=nif_path, width=1, height=1)
