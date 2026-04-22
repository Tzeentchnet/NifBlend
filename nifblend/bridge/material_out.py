"""Material export bridge (Phase 3 step 12).

Inverse of :mod:`nifblend.bridge.material_in`:

* :func:`material_data_from_blender` reads a ``bpy.types.Material`` (or
  duck-typed equivalent) and produces a :class:`MaterialData`. It looks
  for the small node graph the import side builds (Principled BSDF +
  optional Image / NormalMap nodes) and falls back to default
  :class:`MaterialData` values when the graph is absent.
* :func:`material_data_to_bslighting` and
  :func:`material_data_to_bseffect` build the corresponding codegen
  block, mirroring the import-side decoders field-for-field. Cross-block
  references (``texture_set``, ``shader_property``, ``alpha_property``,
  the ``name`` string-table index) are left as ``-1`` /
  ``0xFFFFFFFF``; the operator is responsible for allocating string
  entries and patching block refs (same contract as the mesh bridge).
* :func:`build_texture_set` is exposed so the operator can spin up a
  matching :class:`BSShaderTextureSet` block without re-reading the
  texture dict.
* :func:`export_material` is a one-call convenience that picks the right
  output block based on ``MaterialData.origin``.

Bone-weight / skin-instance bookkeeping is out of scope for materials
(handled by Phase 4); the alpha-property block is built separately by
:func:`build_alpha_property` so the operator can decide whether to
allocate one based on Blender's ``blend_method``.
"""

from __future__ import annotations

import contextlib
from typing import Any

from nifblend.format.generated.bitfields import AlphaFlags
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
from nifblend.format.generated.structs import (
    Color3,
    Color4,
    FilePath,
    FormatPrefs,
    SizedString,
    TexCoord,
    TexDesc,
)

from .material_in import CLASSIC_TEXTURE_SLOT_NAMES, TEXTURE_SLOT_NAMES, MaterialData

__all__ = [
    "build_alpha_property",
    "build_classic_material_blocks",
    "build_ni_source_texture",
    "build_pp_texture_set",
    "build_texture_set",
    "export_material",
    "material_data_from_blender",
    "material_data_to_bseffect",
    "material_data_to_bslighting",
    "material_data_to_bsshaderpplighting",
    "material_data_to_nimaterial",
    "material_data_to_nitexturing",
]


_NULL_REF = 0xFFFFFFFF


# ---- Blender → MaterialData ----------------------------------------------


def material_data_from_blender(mat: Any) -> MaterialData:
    """Read a Blender material into :class:`MaterialData`.

    The reader expects the predictable graph the import side produces
    (Principled BSDF reachable from the Material Output's ``Surface``
    socket, optionally fed by Image Texture / NormalMap nodes). When the
    graph deviates -- a hand-authored material, no nodes at all -- the
    reader falls back to per-field defaults so export still produces a
    usable shader property rather than crashing.
    """
    data = MaterialData(name=mat.name)

    if not getattr(mat, "use_nodes", False):
        data.alpha_blend = _is_blend(getattr(mat, "blend_method", "OPAQUE"))
        data.alpha_test = _is_clip(getattr(mat, "blend_method", "OPAQUE"))
        data.alpha_threshold = int(round(_alpha_threshold(mat) * 255.0))
        return data

    tree = getattr(mat, "node_tree", None)
    bsdf = _find_bsdf(tree)
    if bsdf is not None:
        _read_principled(data, bsdf)

    # Alpha state from the material itself (mirrors what the import side wrote).
    data.alpha_blend = _is_blend(getattr(mat, "blend_method", "OPAQUE"))
    data.alpha_test = _is_clip(getattr(mat, "blend_method", "OPAQUE"))
    data.alpha_threshold = int(round(_alpha_threshold(mat) * 255.0))

    # Layer NIF-only state from the typed PropertyGroup on top, so flags
    # / texture slots Blender can't represent survive the round-trip.
    from .material_props import read_material_data_from_props

    read_material_data_from_props(mat, data)
    return data


# ---- MaterialData → block ------------------------------------------------


def material_data_to_bslighting(
    data: MaterialData,
    *,
    name_index: int = _NULL_REF,
    texture_set_ref: int = -1,
) -> BSLightingShaderProperty:
    """Build a Skyrim SE-shaped BSLightingShaderProperty from MaterialData.

    ``name_index`` is the u32 string-table slot the operator allocated;
    ``texture_set_ref`` is the block-table index of the matching
    :class:`BSShaderTextureSet` (use ``-1`` for "no texture set").
    """
    blk = BSLightingShaderProperty()
    _populate_common_block(blk, data, name_index)

    blk.shader_type = data.shader_type
    blk.shader_flags_1 = data.shader_flags_1
    blk.shader_flags_2 = data.shader_flags_2
    # Inverse SSE-only fields from material_in's BSLightingShaderProperty
    # write path.
    blk.uv_offset = TexCoord(*data.uv_offset)
    blk.uv_scale = TexCoord(*data.uv_scale)
    blk.texture_set = int(texture_set_ref)
    blk.emissive_color = Color3(*data.emissive_color)
    blk.emissive_multiple = data.emissive_multiple
    blk.specular_color = Color3(*data.specular_color)
    blk.specular_strength = data.specular_strength
    blk.alpha = data.alpha
    blk.glossiness = data.glossiness
    blk.smoothness = data.smoothness
    # Required scalars that the codegen always writes (no vercond guard).
    blk.refraction_strength = 0.0
    blk.texture_clamp_mode = 0
    return blk


def material_data_to_bseffect(
    data: MaterialData,
    *,
    name_index: int = _NULL_REF,
) -> BSEffectShaderProperty:
    """Build a Skyrim SE-shaped BSEffectShaderProperty from MaterialData."""
    blk = BSEffectShaderProperty()
    _populate_common_block(blk, data, name_index)

    blk.shader_type = data.shader_type
    blk.shader_flags_1 = data.shader_flags_1
    blk.shader_flags_2 = data.shader_flags_2

    blk.uv_offset = TexCoord(*data.uv_offset)
    blk.uv_scale = TexCoord(*data.uv_scale)

    blk.base_color = Color4(*data.base_color)
    blk.base_color_scale = data.emissive_multiple
    blk.emittance_color = Color3(*data.emissive_color)

    # Textures live inline on BSEffect, not in a TextureSet.
    blk.source_texture = _str_to_sized(data.textures.get("diffuse", ""))
    blk.normal_texture = _str_to_sized(data.textures.get("normal", ""))
    blk.env_map_texture = _str_to_sized(data.textures.get("environment", ""))
    blk.env_mask_texture = _str_to_sized(data.textures.get("env_mask", ""))
    blk.greyscale_texture = _str_to_sized(data.textures.get("subsurface", ""))
    blk.emit_gradient_texture = _str_to_sized(data.textures.get("glow", ""))

    # Required scalars (codegen unconditional writes on the SSE path).
    blk.texture_clamp_mode = 0
    blk.lighting_influence = 0
    blk.env_map_min_lod = 0
    blk.unused_byte = 0
    blk.falloff_start_angle = 0.0
    blk.falloff_stop_angle = 0.0
    blk.falloff_start_opacity = 0.0
    blk.falloff_stop_opacity = 0.0
    blk.soft_falloff_depth = 0.0
    return blk


def material_data_to_bsshaderpplighting(
    data: MaterialData,
    *,
    name_index: int = _NULL_REF,
    texture_set_ref: int = -1,
) -> BSShaderPPLightingProperty:
    """Build a Fallout 3 / NV-shaped :class:`BSShaderPPLightingProperty`.

    Inverse of :func:`bsshaderpplighting_to_material_data`. ``name_index``
    is the u32 string-table slot the operator allocated; ``texture_set_ref``
    is the block-table index of the matching :class:`BSShaderTextureSet`
    (use ``-1`` for "no texture set").

    The codegen unconditionally writes ``texture_set`` plus the ``bs_version
    > 14`` refraction scalars and the ``> 24`` parallax scalars; ``bs_version
    > 34`` (post-FO3) would also write ``emissive_color`` -- harmless to
    populate at default since the SSE BSLightingShaderProperty path takes
    over above bs_version 34.
    """
    blk = BSShaderPPLightingProperty()
    _populate_common_block(blk, data, name_index)

    blk.flags = int(data.pp_flags) & 0xFFFF
    blk.shader_type = data.shader_type
    blk.shader_flags = data.shader_flags_1
    blk.shader_flags_2 = data.shader_flags_2
    blk.environment_map_scale = data.environment_map_scale
    blk.texture_clamp_mode = data.texture_clamp_mode

    blk.texture_set = int(texture_set_ref)

    blk.refraction_strength = data.refraction_strength
    blk.refraction_fire_period = data.refraction_fire_period
    blk.parallax_max_passes = data.parallax_max_passes
    blk.parallax_scale = data.parallax_scale

    # Emissive is only persisted when the writer takes the bs > 34 branch
    # (post-FO3). Populate it from the bridge-side (color, multiplier-as-alpha)
    # tuple anyway so the dataclass is fully formed even if the caller
    # later promotes the block to a higher bs_version.
    r, g, b = data.emissive_color
    blk.emissive_color = Color4(r=r, g=g, b=b, a=float(data.emissive_multiple))

    return blk


def build_pp_texture_set(data: MaterialData, *, num_slots: int = 6) -> BSShaderTextureSet | None:
    """:class:`BSShaderTextureSet` for the FO3/NV layout (6-slot default).

    Pre-Skyrim Bethesda titles allocate exactly six texture slots
    (diffuse / normal / glow / height / environment / env_mask -- the
    first six entries of :data:`TEXTURE_SLOT_NAMES`). FO4+ widens to 9;
    Skyrim SE uses 8 (handled by :func:`build_texture_set`). Returns
    ``None`` when no slot is populated so the caller can pass ``-1`` as
    ``texture_set_ref``.
    """
    slots = TEXTURE_SLOT_NAMES[:num_slots]
    if not any(data.textures.get(s) for s in slots):
        return None
    ts = BSShaderTextureSet()
    ts.textures = [_str_to_sized(data.textures.get(s, "")) for s in slots]
    ts.num_textures = len(ts.textures)
    return ts


def build_texture_set(data: MaterialData) -> BSShaderTextureSet | None:
    """Build a :class:`BSShaderTextureSet` from the named slots in ``data``.

    Returns ``None`` when no slot is populated (caller should pass
    ``-1`` as the ``texture_set_ref`` to
    :func:`material_data_to_bslighting`). The slot order matches
    :data:`TEXTURE_SLOT_NAMES`; empty slots are emitted as zero-length
    SizedStrings so downstream readers see a stable index layout.
    """
    if not any(data.textures.get(slot) for slot in TEXTURE_SLOT_NAMES):
        return None
    ts = BSShaderTextureSet()
    ts.textures = [_str_to_sized(data.textures.get(slot, "")) for slot in TEXTURE_SLOT_NAMES]
    ts.num_textures = len(ts.textures)
    return ts


def build_alpha_property(data: MaterialData) -> NiAlphaProperty | None:
    """Build a :class:`NiAlphaProperty` if the material needs one.

    Returns ``None`` for opaque materials so the operator can skip
    allocating a block-table slot.
    """
    if not (data.alpha_blend or data.alpha_test):
        return None
    blk = NiAlphaProperty()
    blk.flags = AlphaFlags(
        alpha_blend=1 if data.alpha_blend else 0,
        alpha_test=1 if data.alpha_test else 0,
    )
    blk.threshold = int(max(0, min(255, data.alpha_threshold)))
    return blk


def export_material(
    mat: Any,
    *,
    origin: str | None = None,
    name_index: int = _NULL_REF,
    texture_set_ref: int = -1,
) -> BSLightingShaderProperty | BSEffectShaderProperty | BSShaderPPLightingProperty:
    """One-call convenience: read a Blender material, build a shader-property block.

    ``origin`` overrides the Blender-derived
    :attr:`MaterialData.origin` (which defaults to BSLightingShaderProperty).

    The classic Morrowind / Oblivion stack (``NiMaterialProperty`` +
    ``NiTexturingProperty`` + N × ``NiSourceTexture``) is multi-block and
    therefore can't fit this single-block convenience signature; callers
    that need it use :func:`build_classic_material_blocks` directly.
    """
    data = material_data_from_blender(mat)
    if origin is not None:
        data.origin = origin
    if data.origin == "BSEffectShaderProperty":
        return material_data_to_bseffect(data, name_index=name_index)
    if data.origin == "BSShaderPPLightingProperty":
        return material_data_to_bsshaderpplighting(
            data, name_index=name_index, texture_set_ref=texture_set_ref
        )
    return material_data_to_bslighting(
        data, name_index=name_index, texture_set_ref=texture_set_ref
    )


# ---- classic Morrowind / Oblivion builders -------------------------------


def material_data_to_nimaterial(
    data: MaterialData,
    *,
    name_index: int = _NULL_REF,
) -> NiMaterialProperty:
    """Build a classic :class:`NiMaterialProperty` from :class:`MaterialData`.

    ``name_index`` is the u32 string-table slot the operator allocated;
    older NIFs (``ctx.version < 20.1.0.3``) ignore the index and read
    an inline ``SizedString`` instead — the operator is responsible for
    swapping in an inline-string ``name`` when targeting Morrowind /
    Oblivion. The codegen ``string`` Compound carries both shapes; we
    populate the modern index path here and the legacy callers patch
    the inline ``string`` field as needed.
    """
    blk = NiMaterialProperty()
    _populate_classic_common(blk, data, name_index)

    blk.flags = 0  # u16 in classic versions, ignored on Skyrim+
    blk.ambient_color = Color3(*data.ambient_color)
    blk.diffuse_color = Color3(*data.diffuse_color)
    blk.specular_color = Color3(*data.specular_color)
    blk.emissive_color = Color3(*data.emissive_color)
    blk.glossiness = float(data.glossiness)
    blk.alpha = float(data.alpha)
    blk.emissive_mult = float(data.emissive_multiple)
    return blk


def material_data_to_nitexturing(
    data: MaterialData,
    *,
    name_index: int = _NULL_REF,
    source_refs: dict[str, int] | None = None,
) -> NiTexturingProperty:
    """Build a classic :class:`NiTexturingProperty` from :class:`MaterialData`.

    ``source_refs`` maps a slot name from
    :data:`CLASSIC_TEXTURE_SLOT_NAMES` to the block-table index of the
    matching :class:`NiSourceTexture`; missing / unset slots become
    null ``-1`` refs so the writer emits a zero ``has_*_texture``
    boolean for that slot. ``texture_count`` and ``apply_mode`` /
    ``flags`` are pulled from ``data`` (defaults are Morrowind-shaped:
    7 textures, ``APPLY_MODULATE``).
    """
    refs = source_refs or {}
    blk = NiTexturingProperty()
    _populate_classic_common(blk, data, name_index)

    blk.flags = int(data.texturing_flags) & 0xFFFF
    blk.apply_mode = int(data.texturing_apply_mode)
    blk.texture_count = int(data.texture_count)

    for slot, has_attr, tex_attr in (
        ("diffuse", "has_base_texture", "base_texture"),
        ("dark", "has_dark_texture", "dark_texture"),
        ("detail", "has_detail_texture", "detail_texture"),
        ("gloss", "has_gloss_texture", "gloss_texture"),
        ("glow", "has_glow_texture", "glow_texture"),
        ("bump", "has_bump_map_texture", "bump_map_texture"),
        ("normal", "has_normal_texture", "normal_texture"),
        ("height", "has_parallax_texture", "parallax_texture"),
        ("decal0", "has_decal_0_texture", "decal_0_texture"),
        ("decal1", "has_decal_1_texture", "decal_1_texture"),
        ("decal2", "has_decal_2_texture", "decal_2_texture"),
        ("decal3", "has_decal_3_texture", "decal_3_texture"),
    ):
        ref = refs.get(slot)
        if ref is None or int(ref) < 0:
            setattr(blk, has_attr, False)
            setattr(blk, tex_attr, None)
            continue
        setattr(blk, has_attr, True)
        td = TexDesc()
        td.source = int(ref)
        td.clamp_mode = 3  # WRAP_S_WRAP_T (default)
        td.filter_mode = 2  # FILTER_TRILERP
        td.uv_set = 0
        td.has_texture_transform = False
        setattr(blk, tex_attr, td)

    # Bump map ancillary scalars stay at their zero defaults; modders
    # who care can populate them via the typed PropertyGroup later.
    blk.bump_map_luma_scale = 0.0
    blk.bump_map_luma_offset = 0.0
    blk.parallax_offset = 0.0
    return blk


def build_ni_source_texture(path: str) -> NiSourceTexture:
    """Build a classic :class:`NiSourceTexture` referencing an external file.

    The legacy file_name shape (``ctx.version <= 20.0.0.5``) carries an
    inline :class:`SizedString`; the modern shape uses a string-table
    index. We populate ``file_name`` with both an inline string *and*
    a zero index so either codegen branch picks up a sensible value
    (older readers see the SizedString, newer readers see index 0 —
    callers targeting modern NIFs should patch the index).
    """
    src = NiSourceTexture()
    src.controller = -1
    src.use_external = 1
    fp = FilePath()
    fp.string = _str_to_sized(path)
    fp.index = 0
    src.file_name = fp
    src.format_prefs = FormatPrefs(
        pixel_layout=5,  # PALETTISED_4 default; renderer is free to ignore
        use_mipmaps=2,   # MIP_FMT_DEFAULT
        alpha_format=3,  # ALPHA_DEFAULT
    )
    src.is_static = 1
    return src


def build_classic_material_blocks(
    data: MaterialData,
    *,
    material_name_index: int = _NULL_REF,
    texturing_name_index: int = _NULL_REF,
) -> tuple[NiMaterialProperty | None, NiTexturingProperty | None, list[NiSourceTexture]]:
    """Orchestrator that assembles the classic property stack.

    Returns a triple of ``(material_property, texturing_property,
    source_textures)`` with the texturing property pre-wired to point
    at the source textures by their *positional* index in the returned
    list. The operator is responsible for inserting the source
    textures into the block table first, computing their absolute
    indices, and re-running :func:`material_data_to_nitexturing` with
    the patched ``source_refs`` mapping if the positional indices
    don't match the final block-table layout.

    A ``NiMaterialProperty`` is always emitted (even if every colour /
    glossiness is at default — Morrowind requires the block); the
    texturing property is omitted when ``data.textures`` is empty so
    the operator can elide it.
    """
    sources: list[NiSourceTexture] = []
    source_refs: dict[str, int] = {}
    for slot in CLASSIC_TEXTURE_SLOT_NAMES:
        path = data.textures.get(slot)
        if not path:
            continue
        source_refs[slot] = len(sources)
        sources.append(build_ni_source_texture(path))

    mat_blk = material_data_to_nimaterial(data, name_index=material_name_index)
    tex_blk: NiTexturingProperty | None = None
    if sources:
        tex_blk = material_data_to_nitexturing(
            data,
            name_index=texturing_name_index,
            source_refs=source_refs,
        )

    return mat_blk, tex_blk, sources


# ---- private helpers -----------------------------------------------------


def _str_to_sized(value: str) -> SizedString:
    payload = value.encode("latin-1") if value else b""
    return SizedString(length=len(payload), value=list(payload))


def _populate_common_block(
    blk: BSLightingShaderProperty | BSEffectShaderProperty | BSShaderPPLightingProperty,
    data: MaterialData,
    name_index: int,
) -> None:
    """Set the fields the codegen writes unconditionally on the SSE branch."""
    # BSLighting/BSEffect both use the codegen `string` Compound for `name`.
    # Assign a string-table-index form (the modern >= 20.1.0.3 shape).
    from nifblend.format.generated.structs import string as nif_string

    blk.name = nif_string(index=int(name_index) & 0xFFFFFFFF)
    blk.controller = -1


def _populate_classic_common(
    blk: NiMaterialProperty | NiTexturingProperty,
    data: MaterialData,
    name_index: int,
) -> None:
    """Set the fields shared by every classic ``NiObjectNET`` subclass.

    Mirrors :func:`_populate_common_block` but for the Morrowind /
    Oblivion property blocks (which inherit ``name`` + ``controller``
    from ``NiObjectNET`` the same way the BS shaders do).
    """
    from nifblend.format.generated.structs import string as nif_string

    blk.name = nif_string(index=int(name_index) & 0xFFFFFFFF)
    blk.controller = -1
    blk.shader_type = int(getattr(data, "shader_type", 0))


# Blender mode constants. These are strings in real bpy; we keep them as
# constants here so the helpers stay tolerant of the duck-typed test fakes.
def _is_blend(method: str) -> bool:
    return method == "BLEND"


def _is_clip(method: str) -> bool:
    return method == "CLIP"


def _alpha_threshold(mat: Any) -> float:
    raw = getattr(mat, "alpha_threshold", 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _find_bsdf(tree: Any) -> Any | None:
    """Locate a Principled BSDF node reachable from the Material Output."""
    if tree is None:
        return None
    nodes = getattr(tree, "nodes", None)
    if nodes is None:
        return None
    for n in nodes:
        if getattr(n, "kind", None) == "ShaderNodeBsdfPrincipled" or _is_principled(n):
            return n
        if _is_principled_bl_idname(n):
            return n
    return None


def _is_principled(node: Any) -> bool:
    return getattr(node, "type", None) == "BSDF_PRINCIPLED"


def _is_principled_bl_idname(node: Any) -> bool:
    return getattr(node, "bl_idname", None) == "ShaderNodeBsdfPrincipled"


def _input_value(bsdf: Any, name: str) -> Any:
    inputs = getattr(bsdf, "inputs", None)
    if inputs is None:
        return None
    sock = inputs.get(name) if hasattr(inputs, "get") else None
    if sock is None and name in (inputs if hasattr(inputs, "__contains__") else ()):
        sock = inputs[name]
    return sock


def _linked_image(socket: Any) -> tuple[str | None, str | None]:
    """Return ``(image_name, slot_hint)`` for an Image Texture feeding ``socket``.

    ``slot_hint`` is "normal" if the chain is Image → NormalMap → socket,
    else ``None``.
    """
    if socket is None:
        return None, None
    src = getattr(socket, "linked_from", None)
    if src is None:
        return None, None
    owner = getattr(src, "owner", None)
    if owner is None:
        return None, None
    kind = getattr(owner, "kind", None) or getattr(owner, "bl_idname", None)
    if kind == "ShaderNodeNormalMap":
        # Walk one more hop into the Image feeding "Color".
        nm_color = owner.inputs.get("Color") if hasattr(owner.inputs, "get") else None
        if nm_color is None:
            return None, "normal"
        nested = getattr(nm_color, "linked_from", None)
        if nested is None:
            return None, "normal"
        nested_owner = getattr(nested, "owner", None)
        img = getattr(nested_owner, "image", None) if nested_owner else None
        return (getattr(img, "name", None) if img else None), "normal"
    img = getattr(owner, "image", None)
    return (getattr(img, "name", None) if img else None), None


def _read_principled(data: MaterialData, bsdf: Any) -> None:
    """Pull constants + linked-image paths out of a Principled BSDF node."""
    bc = _input_value(bsdf, "Base Color")
    if bc is not None and getattr(bc, "default_value", None) is not None:
        v = bc.default_value
        with contextlib.suppress(TypeError, IndexError):
            data.base_color = (float(v[0]), float(v[1]), float(v[2]), float(v[3]))
        name, _ = _linked_image(bc)
        if name:
            data.textures["diffuse"] = name

    alpha = _input_value(bsdf, "Alpha")
    if alpha is not None and getattr(alpha, "default_value", None) is not None:
        with contextlib.suppress(TypeError, ValueError):
            data.alpha = float(alpha.default_value)

    rough = _input_value(bsdf, "Roughness")
    if rough is not None and getattr(rough, "default_value", None) is not None:
        with contextlib.suppress(TypeError, ValueError):
            data.smoothness = max(0.0, min(1.0, 1.0 - float(rough.default_value)))

    metallic = _input_value(bsdf, "Metallic")
    if metallic is not None and getattr(metallic, "default_value", None) is not None:
        with contextlib.suppress(TypeError, ValueError):
            data.specular_strength = float(metallic.default_value)

    em = _input_value(bsdf, "Emission Color") or _input_value(bsdf, "Emission")
    if em is not None:
        if getattr(em, "default_value", None) is not None:
            v = em.default_value
            with contextlib.suppress(TypeError, IndexError):
                data.emissive_color = (float(v[0]), float(v[1]), float(v[2]))
        name, _ = _linked_image(em)
        if name:
            data.textures["glow"] = name

    em_strength = _input_value(bsdf, "Emission Strength")
    if em_strength is not None and getattr(em_strength, "default_value", None) is not None:
        with contextlib.suppress(TypeError, ValueError):
            data.emissive_multiple = float(em_strength.default_value)

    nrm = _input_value(bsdf, "Normal")
    if nrm is not None:
        name, hint = _linked_image(nrm)
        if name and hint == "normal":
            data.textures["normal"] = name
