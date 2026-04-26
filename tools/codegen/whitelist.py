"""Explicit whitelist of NIF schema types to emit.

The full schema has ~563 niobjects + ~162 structs + ~111 enums; emitting
all of it is wasteful for a v1.0 scope (Skyrim LE/SE, FO3/NV/4/76, Morrowind,
Oblivion). This module declares the **seed set** the bridge layer actually
needs; the emitter walks the dependency closure (inheritance + field types
+ template params) automatically.

Adding a new block: add its name here, regenerate, commit. The drift test
catches missed regenerations.

Out of scope (not whitelisted): `bhk*` collision blocks, all `NiPSys*`
particle-system blocks beyond the bare minimum, `EGM`/`TRI` morph blocks.
See [`ROADMAP.md`](../../docs/ROADMAP.md) for the canonical scope.
"""

from __future__ import annotations

__all__ = ["SEED_TYPES"]


SEED_TYPES: frozenset[str] = frozenset(
    {
        # ---- core scene graph --------------------------------------------
        "NiObject",
        "NiObjectNET",
        "NiAVObject",
        "NiNode",
        "NiSwitchNode",
        "NiLODNode",
        "NiBillboardNode",
        # ---- header / footer --------------------------------------------
        # Schema spells these without the `Ni` prefix; they are <struct>s,
        # not niobjects.
        "Header",
        "Footer",
        # ---- legacy & shared geometry -----------------------------------
        "NiGeometry",
        "NiGeometryData",
        "NiTriBasedGeom",
        "NiTriBasedGeomData",
        "NiTriShape",
        "NiTriShapeData",
        "NiTriStrips",
        "NiTriStripsData",
        # ---- Bethesda geometry ------------------------------------------
        "BSTriShape",
        "BSDynamicTriShape",
        "BSSubIndexTriShape",
        "BSLODTriShape",
        "BSMeshLODTriShape",
        "BSGeometry",
        # ---- materials / shaders ----------------------------------------
        "NiProperty",
        "NiMaterialProperty",
        "NiTexturingProperty",
        "NiSourceTexture",
        "NiAlphaProperty",
        "BSShaderProperty",
        "BSShaderTextureSet",
        "BSLightingShaderProperty",
        "BSEffectShaderProperty",
        "BSShaderPPLightingProperty",
        # ---- skinning ----------------------------------------------------
        "NiSkinInstance",
        "NiSkinData",
        "NiSkinPartition",
        "BSDismemberSkinInstance",
        # FO4/F76 skinning niobjects use `::` in the schema name.
        "BSSkin::Instance",
        "BSSkin::BoneData",
        # ---- animation (KF import) --------------------------------------
        "NiTimeController",
        "NiInterpolator",
        "NiControllerSequence",
        "NiControllerManager",
        "NiTransformController",
        "NiTransformInterpolator",
        "NiTransformData",
        "NiKeyframeData",
        "NiTextKeyExtraData",
        # ---- extra-data --------------------------------------------------
        "NiExtraData",
        "NiStringExtraData",
        "NiIntegerExtraData",
        "NiBinaryExtraData",
        "BSXFlags",
    }
)
