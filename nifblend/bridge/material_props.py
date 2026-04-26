"""Phase 3 step 13: typed ``PropertyGroup`` on ``bpy.types.Material``.

Stores the subset of :class:`~nifblend.bridge.material_in.MaterialData`
that Blender's Principled BSDF can't represent natively, so a NifBlend
material can round-trip through *import → edit → export* without losing
NIF-only state. Concretely: the raw ``shader_type`` enum, the two 32-bit
shader-flag bitfields, the legacy ``glossiness`` / ``specular_color``
pair, the inline UV transform (``uv_offset`` / ``uv_scale``), the
``alpha_threshold`` byte (Blender stores a 0..1 float instead),
``origin`` (which shader-property class produced the material), and
*any* texture slots beyond the diffuse / normal / glow that the
Principled-BSDF graph plugs in (height, environment, env_mask,
subsurface, backlight, …).

The module exposes two layers:

* :class:`NifBlendMaterialTextureSlot` and
  :class:`NifBlendMaterialProperties` — the actual ``PropertyGroup``
  classes registered against the live ``bpy`` module. Decorated with
  ``bpy.props.*Property`` annotations the way Blender expects.
* :func:`apply_material_data_to_props` and
  :func:`read_material_data_from_props` — duck-typed helpers used by
  :mod:`nifblend.bridge.material_in` / :mod:`material_out`. They work
  against either a real ``PointerProperty``-backed PropertyGroup or any
  attribute-bearing fake (the test suite uses ``SimpleNamespace``).

Registration is wired by :func:`register` / :func:`unregister`, called
from the addon entry point. The ``bpy.types.Material.nifblend``
PointerProperty is the public surface — everything else is an internal
storage detail.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from typing import Any

import bpy

from .material_in import MaterialData

__all__ = [
    "PROP_ATTR",
    "NifBlendMaterialProperties",
    "NifBlendMaterialTextureSlot",
    "apply_material_data_to_props",
    "get_starfield_material_path",
    "read_material_data_from_props",
    "register",
    "set_starfield_material_path",
    "unregister",
]


#: Attribute name on ``bpy.types.Material`` that carries the PropertyGroup.
PROP_ATTR = "nifblend"


# Field tables driving the apply/read helpers. Keeping them as plain
# tuples (rather than introspecting the PropertyGroup) means the helpers
# work just as well against a SimpleNamespace fake in unit tests.
_INT_FIELDS: tuple[str, ...] = (
    "shader_type",
    "shader_flags_1",
    "shader_flags_2",
    "alpha_threshold",
    "pp_flags",
    "texture_clamp_mode",
    "refraction_fire_period",
    "texturing_apply_mode",
    "texturing_flags",
    "texture_count",
)
_FLOAT_FIELDS: tuple[str, ...] = (
    "emissive_multiple",
    "glossiness",
    "specular_strength",
    "environment_map_scale",
    "refraction_strength",
    "parallax_max_passes",
    "parallax_scale",
)
_VEC2_FIELDS: tuple[str, ...] = ("uv_offset", "uv_scale")
_VEC3_FIELDS: tuple[str, ...] = ("specular_color", "ambient_color", "diffuse_color")
_STR_FIELDS: tuple[str, ...] = ("origin",)
#: Phase 9i: Starfield ``.mat`` rel-path stamped at import so a reload
#: operator can re-resolve the manifest later. Carried separately from
#: ``_STR_FIELDS`` because it lives outside :class:`MaterialData` -- the
#: operator writes / reads it directly via the helpers below.
_STARFIELD_MATERIAL_PATH_ATTR = "starfield_material_path"


# ---- PropertyGroup classes -----------------------------------------------


class NifBlendMaterialTextureSlot(bpy.types.PropertyGroup):
    """One row in :attr:`NifBlendMaterialProperties.textures`.

    ``slot`` is the symbolic name from
    :data:`nifblend.bridge.material_in.TEXTURE_SLOT_NAMES`; ``path`` is
    the raw NIF-relative path (``textures/foo/bar_d.dds``).
    """

    slot: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Slot",
        description="Symbolic NIF texture-slot name (diffuse, normal, glow, …)",
        default="",
    )
    path: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Path",
        description="NIF-relative texture path (resolved against the Data root at import time)",
        default="",
        subtype="FILE_PATH",
    )


class NifBlendMaterialProperties(bpy.types.PropertyGroup):
    """NIF-only material state attached to ``bpy.types.Material.nifblend``."""

    origin: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Origin",
        description="Which Bethesda shader-property class produced this material",
        default="BSLightingShaderProperty",
    )
    shader_type: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Shader Type",
        description="Raw BSLightingShaderType / BSEffectShaderType enum value",
        default=0,
    )
    shader_flags_1: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Shader Flags 1",
        description="Raw SkyrimShaderPropertyFlags1 bitfield (preserved verbatim)",
        default=0,
        subtype="UNSIGNED",
    )
    shader_flags_2: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Shader Flags 2",
        description="Raw SkyrimShaderPropertyFlags2 bitfield (preserved verbatim)",
        default=0,
        subtype="UNSIGNED",
    )
    alpha_threshold: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Alpha Threshold",
        description="NiAlphaProperty.threshold (0..255 byte)",
        default=0,
        min=0,
        max=255,
    )
    emissive_multiple: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Emissive Multiple",
        description="Emissive scalar (separate from Principled BSDF Emission Strength)",
        default=0.0,
    )
    glossiness: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Glossiness",
        description="Legacy specular exponent (Skyrim LE / pre-SSE)",
        default=80.0,
    )
    specular_strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Specular Strength",
        description="NIF specular strength (separate from Principled BSDF Metallic)",
        default=1.0,
    )
    specular_color: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Specular Color",
        size=3,
        default=(1.0, 1.0, 1.0),
        subtype="COLOR",
        min=0.0,
        max=1.0,
    )
    uv_offset: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="UV Offset",
        size=2,
        default=(0.0, 0.0),
    )
    uv_scale: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="UV Scale",
        size=2,
        default=(1.0, 1.0),
    )
    textures: bpy.props.CollectionProperty(  # type: ignore[valid-type]
        name="Texture Slots",
        type=NifBlendMaterialTextureSlot,
    )

    # FO3 / Fallout NV (BSShaderPPLightingProperty) extras. These have
    # no Principled-BSDF analogue and are preserved verbatim for
    # round-trip; SSE materials leave them at their default values.
    pp_flags: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="PP Flags",
        description="BSShaderFlags u16 word from BSShaderPPLightingProperty",
        default=0,
        min=0,
        max=0xFFFF,
        subtype="UNSIGNED",
    )
    environment_map_scale: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Environment Map Scale",
        description="BSShaderPPLightingProperty.environment_map_scale (FO3/NV)",
        default=1.0,
    )
    texture_clamp_mode: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Texture Clamp Mode",
        description="BSShaderPPLightingProperty.texture_clamp_mode (FO3/NV)",
        default=0,
        subtype="UNSIGNED",
    )
    refraction_strength: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Refraction Strength",
        description="BSShaderPPLightingProperty.refraction_strength (bs_version > 14)",
        default=0.0,
    )
    refraction_fire_period: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Refraction Fire Period",
        description="BSShaderPPLightingProperty.refraction_fire_period (bs_version > 14)",
        default=0,
    )
    parallax_max_passes: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Parallax Max Passes",
        description="BSShaderPPLightingProperty.parallax_max_passes (bs_version > 24)",
        default=0.0,
    )
    parallax_scale: bpy.props.FloatProperty(  # type: ignore[valid-type]
        name="Parallax Scale",
        description="BSShaderPPLightingProperty.parallax_scale (bs_version > 24)",
        default=0.0,
    )

    # Classic Morrowind / Oblivion (NiMaterialProperty + NiTexturingProperty)
    # extras. Preserved verbatim so the legacy stack survives a Blender
    # edit cycle even though the Principled-BSDF graph can't represent
    # ambient / diffuse-as-separate-fields or the legacy apply mode.
    ambient_color: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Ambient Color",
        size=3,
        default=(1.0, 1.0, 1.0),
        subtype="COLOR",
        min=0.0,
        max=1.0,
    )
    diffuse_color: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Diffuse Color",
        size=3,
        default=(1.0, 1.0, 1.0),
        subtype="COLOR",
        min=0.0,
        max=1.0,
    )
    texturing_apply_mode: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Texturing Apply Mode",
        description="NiTexturingProperty.apply_mode (Morrowind / Oblivion)",
        default=2,
    )
    texturing_flags: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Texturing Flags",
        description="NiTexturingProperty.flags (raw u16, ctx.version <= 10.0.1.2)",
        default=0,
        min=0,
        max=0xFFFF,
        subtype="UNSIGNED",
    )
    texture_count: bpy.props.IntProperty(  # type: ignore[valid-type]
        name="Texture Count",
        description="NiTexturingProperty.texture_count (gates classic optional slots)",
        default=7,
        min=0,
    )

    # Phase 9i — Starfield: rel-path of the ``.mat`` JSON manifest this
    # material was imported from, so the reload operator can re-resolve
    # and rebuild the Principled-BSDF graph in place. Empty for any
    # non-Starfield material.
    starfield_material_path: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="Starfield Material Path",
        description="NIF-relative path to the source Starfield .mat manifest",
        default="",
        subtype="FILE_PATH",
    )


_REGISTERED_CLASSES: tuple[type, ...] = (
    NifBlendMaterialTextureSlot,
    NifBlendMaterialProperties,
)


# ---- duck-typed helpers --------------------------------------------------


def apply_material_data_to_props(mat: Any, data: MaterialData) -> None:
    """Copy NIF-only fields out of ``data`` into ``mat.nifblend``.

    No-op when neither the real PropertyGroup nor a writable fallback
    attribute is reachable on ``mat`` (e.g. a stripped-down test
    object). The Principled BSDF graph remains the source of truth for
    fields Blender can natively represent (base color, alpha, roughness,
    metallic, emission color/strength, the diffuse/normal/glow images);
    this helper only records the *extra* NIF state.
    """
    props = _get_or_create_props(mat)
    if props is None:
        return

    for f in _INT_FIELDS:
        _set_attr(props, f, int(getattr(data, f)))
    for f in _FLOAT_FIELDS:
        _set_attr(props, f, float(getattr(data, f)))
    for f in _VEC2_FIELDS:
        v = getattr(data, f)
        _set_attr(props, f, (float(v[0]), float(v[1])))
    for f in _VEC3_FIELDS:
        v = getattr(data, f)
        _set_attr(props, f, (float(v[0]), float(v[1]), float(v[2])))
    for f in _STR_FIELDS:
        _set_attr(props, f, str(getattr(data, f)))

    _write_textures(props, data.textures)


def read_material_data_from_props(mat: Any, data: MaterialData) -> None:
    """Merge NIF-only fields from ``mat.nifblend`` back into ``data``.

    Called *after* the Principled-BSDF reader has populated whatever
    Blender can represent natively, so that edits made through the
    standard shader graph win. Texture slots from the PropertyGroup are
    merged via :py:meth:`dict.setdefault`, preserving any image already
    found via the node graph.
    """
    props = _get_props(mat)
    if props is None:
        return

    for f in _INT_FIELDS:
        v = _get_attr(props, f)
        if v is not None:
            setattr(data, f, int(v))
    for f in _FLOAT_FIELDS:
        v = _get_attr(props, f)
        if v is not None:
            setattr(data, f, float(v))
    for f in _VEC2_FIELDS:
        v = _get_attr(props, f)
        if v is not None and len(v) >= 2:
            setattr(data, f, (float(v[0]), float(v[1])))
    for f in _VEC3_FIELDS:
        v = _get_attr(props, f)
        if v is not None and len(v) >= 3:
            setattr(data, f, (float(v[0]), float(v[1]), float(v[2])))
    for f in _STR_FIELDS:
        v = _get_attr(props, f)
        if v:
            setattr(data, f, str(v))

    for slot, path in _read_textures(props).items():
        data.textures.setdefault(slot, path)


def set_starfield_material_path(mat: Any, rel_path: str) -> None:
    """Stamp the Starfield ``.mat`` rel-path onto ``mat.nifblend``.

    No-op when the PropertyGroup can't be reached (e.g. test fakes that
    refuse arbitrary attribute writes). Empty / ``None`` clears the
    existing stamp.
    """
    props = _get_or_create_props(mat)
    if props is None:
        return
    _set_attr(props, _STARFIELD_MATERIAL_PATH_ATTR, str(rel_path or ""))


def get_starfield_material_path(mat: Any) -> str:
    """Return the Starfield ``.mat`` rel-path stamp, or ``""`` if unset."""
    props = _get_props(mat)
    if props is None:
        return ""
    value = _get_attr(props, _STARFIELD_MATERIAL_PATH_ATTR)
    return str(value) if value else ""


# ---- registration --------------------------------------------------------


def register() -> None:
    """Register the PropertyGroup classes and attach the PointerProperty."""
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Material.nifblend = bpy.props.PointerProperty(
        type=NifBlendMaterialProperties,
        name="NifBlend",
        description="NIF-only material state preserved across import/export",
    )


def unregister() -> None:
    """Inverse of :func:`register`. Tolerant of partial registration."""
    if hasattr(bpy.types.Material, "nifblend"):
        with contextlib.suppress(AttributeError, TypeError):
            del bpy.types.Material.nifblend
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)


# ---- private -------------------------------------------------------------


def _get_props(mat: Any) -> Any:
    return getattr(mat, PROP_ATTR, None)


def _get_or_create_props(mat: Any) -> Any:
    """Return ``mat.nifblend`` or, in tests, attach a SimpleNamespace.

    In real Blender the PointerProperty is auto-created on first access
    and can't be reassigned, so the ``getattr`` branch always wins.
    """
    props = _get_props(mat)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace()
        setattr(mat, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _set_attr(props: Any, name: str, value: Any) -> None:
    with contextlib.suppress(AttributeError, TypeError):
        setattr(props, name, value)


def _get_attr(props: Any, name: str) -> Any:
    return getattr(props, name, None)


def _write_textures(props: Any, textures: dict[str, str]) -> None:
    coll = getattr(props, "textures", None)
    if coll is None:
        # Fall back to a plain dict for skeletal test fakes.
        with contextlib.suppress(AttributeError, TypeError):
            props.textures = dict(textures)
        return
    if isinstance(coll, dict):
        coll.clear()
        coll.update(textures)
        return
    # Real Blender CollectionProperty (or any list-like with clear/add).
    clear = getattr(coll, "clear", None)
    if clear is not None:
        clear()
    add = getattr(coll, "add", None)
    if add is None:
        return
    for slot, path in textures.items():
        item = add()
        try:
            item.slot = slot
            item.path = path
        except (AttributeError, TypeError):
            continue


def _read_textures(props: Any) -> dict[str, str]:
    coll = getattr(props, "textures", None)
    if coll is None:
        return {}
    if isinstance(coll, dict):
        return {str(k): str(v) for k, v in coll.items() if v}
    out: dict[str, str] = {}
    try:
        for item in coll:
            slot = getattr(item, "slot", None)
            path = getattr(item, "path", None)
            if slot and path:
                out[str(slot)] = str(path)
    except TypeError:
        return {}
    return out
