"""Phase 8a: extension-wide AddonPreferences.

Centralises settings that every operator can fall back to: per-game
``Data/`` folder roots used by texture-path resolution, default game
profile when a NIF lacks an identifying header, batch worker count,
KF rotation default, and cell-import defaults.

Pure registration / unregistration mirrors the existing PropertyGroup
modules (``material_props``, ``armature_props``, ``skin_props``).
The actual draw layout is split into collapsible per-game sub-sections
to keep the addon-prefs page compact (decision: option B from the plan).
"""

from __future__ import annotations

import contextlib
import os

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from .format.versions import GameProfile

__all__ = [
    "ADDON_PACKAGE",
    "GAME_PROFILE_ITEMS",
    "NIFBLEND_AddonPreferences",
    "get_prefs",
    "register",
    "unregister",
]


#: Package name registered with Blender's addon manager. Used by
#: :func:`get_prefs` to look the preferences instance up at runtime.
ADDON_PACKAGE = __name__.rsplit(".", 1)[0]


def _profile_items() -> list[tuple[str, str, str]]:
    labels = {
        GameProfile.UNKNOWN: ("Unknown / Auto-detect", "Use header-detected profile"),
        GameProfile.MORROWIND: ("Morrowind", "TES III Morrowind"),
        GameProfile.OBLIVION: ("Oblivion", "TES IV Oblivion"),
        GameProfile.FALLOUT_3_NV: ("Fallout 3 / NV", "Fallout 3 / Fallout New Vegas"),
        GameProfile.SKYRIM_LE: ("Skyrim LE", "TES V Skyrim Legendary Edition"),
        GameProfile.SKYRIM_SE: ("Skyrim SE", "TES V Skyrim Special Edition"),
        GameProfile.FALLOUT_4: ("Fallout 4", "Fallout 4"),
        GameProfile.FALLOUT_76: ("Fallout 76", "Fallout 76"),
        GameProfile.STARFIELD: ("Starfield", "Starfield (read-only in v1.0)"),
    }
    return [(p.value, labels[p][0], labels[p][1]) for p in GameProfile]


#: ``(value, label, description)`` triples for the EnumProperty over
#: :class:`GameProfile`. Exposed at module level so ops/UI can reuse it.
GAME_PROFILE_ITEMS: list[tuple[str, str, str]] = _profile_items()


_TEXTURE_RESOLUTION_ITEMS = [
    ("STRICT", "Strict", "Path must match on disk verbatim"),
    (
        "CASE_INSENSITIVE",
        "Case-insensitive",
        "Match path components case-insensitively (Windows-style)",
    ),
    (
        "FUZZY_LOOSEN_ROOT",
        "Loosen root",
        "Try every Data root in turn; first hit wins",
    ),
]

_KF_ROTATION_ITEMS = [
    ("QUATERNION", "Quaternion", "Lossless; native NIF rotation representation"),
    ("EULER", "Euler XYZ", "Convert to intrinsic XYZ Euler on import"),
]


def _data_root_prop(label: str, desc: str) -> object:
    return StringProperty(
        name=label,
        description=f"Filesystem path to the {desc} Data/ folder",
        subtype="DIR_PATH",
        default="",
    )


class NIFBLEND_AddonPreferences(bpy.types.AddonPreferences):
    """Top-level NifBlend preferences."""

    bl_idname = ADDON_PACKAGE

    # ---- per-game Data/ roots (option B from plan: collapsible) ----------
    morrowind_data: _data_root_prop("Morrowind Data", "Morrowind")  # type: ignore[valid-type]
    oblivion_data: _data_root_prop("Oblivion Data", "Oblivion")  # type: ignore[valid-type]
    fonv_data: _data_root_prop("Fallout NV Data", "Fallout New Vegas")  # type: ignore[valid-type]
    fo3_data: _data_root_prop("Fallout 3 Data", "Fallout 3")  # type: ignore[valid-type]
    skyrim_le_data: _data_root_prop("Skyrim LE Data", "Skyrim Legendary Edition")  # type: ignore[valid-type]
    skyrim_se_data: _data_root_prop("Skyrim SE Data", "Skyrim Special Edition")  # type: ignore[valid-type]
    fo4_data: _data_root_prop("Fallout 4 Data", "Fallout 4")  # type: ignore[valid-type]
    fo76_data: _data_root_prop("Fallout 76 Data", "Fallout 76")  # type: ignore[valid-type]

    default_profile: EnumProperty(  # type: ignore[valid-type]
        name="Default Game Profile",
        description="Used for export when the source has no detectable profile",
        items=GAME_PROFILE_ITEMS,
        default=GameProfile.SKYRIM_SE.value,
    )
    texture_resolution_mode: EnumProperty(  # type: ignore[valid-type]
        name="Texture Path Resolution",
        description="How NIF-relative texture paths are resolved against Data roots",
        items=_TEXTURE_RESOLUTION_ITEMS,
        default="CASE_INSENSITIVE",
    )
    worker_count: IntProperty(  # type: ignore[valid-type]
        name="Batch Worker Count",
        description="Threads used by batch import/export (0 = auto)",
        default=0,
        min=0,
        max=64,
    )
    kf_rotation_default: EnumProperty(  # type: ignore[valid-type]
        name="KF Rotation Mode",
        description="Default rotation representation for KF imports",
        items=_KF_ROTATION_ITEMS,
        default="QUATERNION",
    )
    auto_stamp_profile: BoolProperty(  # type: ignore[valid-type]
        name="Stamp Game Profile on Import",
        description=(
            "Detect the game profile from the NIF header and store it on "
            "each imported object so game-specific UI can self-gate"
        ),
        default=True,
    )

    # ---- cell-layout (NifCity port) defaults -----------------------------
    cell_default_mesh_root: StringProperty(  # type: ignore[valid-type]
        name="Cell Mesh Root",
        description="Default mesh folder used by the Cell Layout importer",
        subtype="DIR_PATH",
        default="",
    )
    cell_normalize_location: BoolProperty(  # type: ignore[valid-type]
        name="Normalize Cell Location",
        description="Recenter the cell average position on the world origin",
        default=True,
    )
    cell_instance_duplicates: BoolProperty(  # type: ignore[valid-type]
        name="Instance Duplicate References",
        description=(
            "When the same NIF appears in multiple CSV rows, share one mesh "
            "datablock across all object instances (instead of re-decoding)"
        ),
        default=True,
    )
    cell_exclude_prefixes: StringProperty(  # type: ignore[valid-type]
        name="Exclude Prefixes",
        description="Comma-separated basename prefixes to skip during cell import",
        default="marker,fx",
    )

    def draw(self, context: bpy.types.Context) -> None:  # pragma: no cover - UI
        layout = self.layout

        col = layout.column(align=True)
        col.label(text="Defaults", icon="PREFERENCES")
        col.prop(self, "default_profile")
        col.prop(self, "texture_resolution_mode")
        col.prop(self, "worker_count")
        col.prop(self, "kf_rotation_default")
        col.prop(self, "auto_stamp_profile")

        box = layout.box()
        box.label(text="Game Data Roots", icon="FILE_FOLDER")
        for prop in (
            "morrowind_data",
            "oblivion_data",
            "fo3_data",
            "fonv_data",
            "skyrim_le_data",
            "skyrim_se_data",
            "fo4_data",
            "fo76_data",
        ):
            box.prop(self, prop)

        cell = layout.box()
        cell.label(text="Cell Layout Import", icon="WORLD_DATA")
        cell.prop(self, "cell_default_mesh_root")
        cell.prop(self, "cell_normalize_location")
        cell.prop(self, "cell_instance_duplicates")
        cell.prop(self, "cell_exclude_prefixes")


_DATA_ROOT_BY_PROFILE: dict[GameProfile, str] = {
    GameProfile.MORROWIND: "morrowind_data",
    GameProfile.OBLIVION: "oblivion_data",
    GameProfile.FALLOUT_3_NV: "fonv_data",
    GameProfile.SKYRIM_LE: "skyrim_le_data",
    GameProfile.SKYRIM_SE: "skyrim_se_data",
    GameProfile.FALLOUT_4: "fo4_data",
    GameProfile.FALLOUT_76: "fo76_data",
}


def get_prefs(context: bpy.types.Context | None = None) -> NIFBLEND_AddonPreferences | None:
    """Return the live :class:`NIFBLEND_AddonPreferences` instance.

    Returns ``None`` outside of a registered Blender session (the headless
    test stub has no preferences API). Callers must tolerate ``None``.
    """
    ctx = context if context is not None else getattr(bpy, "context", None)
    if ctx is None:
        return None
    addons = getattr(getattr(ctx, "preferences", None), "addons", None)
    if addons is None:
        return None
    addon = addons.get(ADDON_PACKAGE)
    if addon is None:
        return None
    return getattr(addon, "preferences", None)


def data_root_for(profile: GameProfile, prefs: NIFBLEND_AddonPreferences | None) -> str:
    """Return the configured Data/ root for ``profile``, or ``""`` when unset."""
    if prefs is None:
        return ""
    attr = _DATA_ROOT_BY_PROFILE.get(profile)
    if attr is None:
        return ""
    return str(getattr(prefs, attr, "") or "")


def resolve_worker_count(prefs: NIFBLEND_AddonPreferences | None) -> int:
    """Resolve the configured worker count, falling back to ``os.cpu_count()``."""
    n = int(getattr(prefs, "worker_count", 0) or 0) if prefs is not None else 0
    if n > 0:
        return n
    return min(32, (os.cpu_count() or 1) + 4)


def register() -> None:
    bpy.utils.register_class(NIFBLEND_AddonPreferences)


def unregister() -> None:
    with contextlib.suppress(RuntimeError, ValueError):
        bpy.utils.unregister_class(NIFBLEND_AddonPreferences)
