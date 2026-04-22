"""Generated NIF enums and bitflag types.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag

__all__ = ['AccumFlags', 'AlphaFormat', 'AlphaFunction', 'AnimNoteType', 'AnimType', 'ApplyMode', 'BSDismemberBodyPartType', 'BSLightingShaderType', 'BSPartFlag', 'BSShaderCRC32', 'BSShaderFlags', 'BSShaderFlags2', 'BSShaderType', 'BSShaderType155', 'BillboardMode', 'BoundVolumeType', 'ConsistencyType', 'CycleType', 'EndianType', 'Fallout4ShaderPropertyFlags1', 'Fallout4ShaderPropertyFlags2', 'ImageType', 'InterpBlendFlags', 'KeyType', 'MipMapFormat', 'NiNBTMethod', 'NiSwitchFlags', 'PixelComponent', 'PixelFormat', 'PixelLayout', 'PixelRepresentation', 'PixelTiling', 'ShadeFlags', 'SkyrimShaderPropertyFlags1', 'SkyrimShaderPropertyFlags2', 'TestFunction', 'TexClampMode', 'TexFilterMode', 'TransformMethod', 'VertexAttribute']


class AlphaFormat(IntEnum):
    """Describes how transparency is handled in an NiTexture."""

    ALPHA_NONE = 0
    ALPHA_BINARY = 1
    ALPHA_SMOOTH = 2
    ALPHA_DEFAULT = 3


class AlphaFunction(IntEnum):
    """Describes alpha blend modes for NiAlphaProperty."""

    ONE = 0
    ZERO = 1
    SRC_COLOR = 2
    INV_SRC_COLOR = 3
    DEST_COLOR = 4
    INV_DEST_COLOR = 5
    SRC_ALPHA = 6
    INV_SRC_ALPHA = 7
    DEST_ALPHA = 8
    INV_DEST_ALPHA = 9
    SRC_ALPHA_SATURATE = 10


class AnimNoteType(IntEnum):
    """Anim note types."""

    ANT_INVALID = 0
    ANT_GRABIK = 1
    ANT_LOOKIK = 2


class AnimType(IntEnum):
    APP_TIME = 0
    APP_INIT = 1


class ApplyMode(IntEnum):
    """Describes how the vertex colors are blended with the filtered texture color."""

    APPLY_REPLACE = 0
    APPLY_DECAL = 1
    APPLY_MODULATE = 2
    APPLY_HILIGHT = 3
    APPLY_HILIGHT2 = 4


class BSDismemberBodyPartType(IntEnum):
    """Biped bodypart data used for visibility control of triangles.  Options are Fallout 3, except where marked for Skyrim (uses SBP prefix)
        Skyrim BP names are listed only for vanilla names, different creatures have different defnitions for naming."""

    BP_TORSO = 0
    BP_HEAD = 1
    BP_HEAD2 = 2
    BP_LEFTARM = 3
    BP_LEFTARM2 = 4
    BP_RIGHTARM = 5
    BP_RIGHTARM2 = 6
    BP_LEFTLEG = 7
    BP_LEFTLEG2 = 8
    BP_LEFTLEG3 = 9
    BP_RIGHTLEG = 10
    BP_RIGHTLEG2 = 11
    BP_RIGHTLEG3 = 12
    BP_BRAIN = 13
    SBP_30_HEAD = 30
    SBP_31_HAIR = 31
    SBP_32_BODY = 32
    SBP_33_HANDS = 33
    SBP_34_FOREARMS = 34
    SBP_35_AMULET = 35
    SBP_36_RING = 36
    SBP_37_FEET = 37
    SBP_38_CALVES = 38
    SBP_39_SHIELD = 39
    SBP_40_TAIL = 40
    SBP_41_LONGHAIR = 41
    SBP_42_CIRCLET = 42
    SBP_43_EARS = 43
    SBP_44_DRAGON_BLOODHEAD_OR_MOD_MOUTH = 44
    SBP_45_DRAGON_BLOODWINGL_OR_MOD_NECK = 45
    SBP_46_DRAGON_BLOODWINGR_OR_MOD_CHEST_PRIMARY = 46
    SBP_47_DRAGON_BLOODTAIL_OR_MOD_BACK = 47
    SBP_48_MOD_MISC1 = 48
    SBP_49_MOD_PELVIS_PRIMARY = 49
    SBP_50_DECAPITATEDHEAD = 50
    SBP_51_DECAPITATE = 51
    SBP_52_MOD_PELVIS_SECONDARY = 52
    SBP_53_MOD_LEG_RIGHT = 53
    SBP_54_MOD_LEG_LEFT = 54
    SBP_55_MOD_FACE_JEWELRY = 55
    SBP_56_MOD_CHEST_SECONDARY = 56
    SBP_57_MOD_SHOULDER = 57
    SBP_58_MOD_ARM_LEFT = 58
    SBP_59_MOD_ARM_RIGHT = 59
    SBP_60_MOD_MISC2 = 60
    SBP_61_FX01 = 61
    BP_SECTIONCAP_HEAD = 101
    BP_SECTIONCAP_HEAD2 = 102
    BP_SECTIONCAP_LEFTARM = 103
    BP_SECTIONCAP_LEFTARM2 = 104
    BP_SECTIONCAP_RIGHTARM = 105
    BP_SECTIONCAP_RIGHTARM2 = 106
    BP_SECTIONCAP_LEFTLEG = 107
    BP_SECTIONCAP_LEFTLEG2 = 108
    BP_SECTIONCAP_LEFTLEG3 = 109
    BP_SECTIONCAP_RIGHTLEG = 110
    BP_SECTIONCAP_RIGHTLEG2 = 111
    BP_SECTIONCAP_RIGHTLEG3 = 112
    BP_SECTIONCAP_BRAIN = 113
    SBP_130_HEAD = 130
    SBP_131_HAIR = 131
    SBP_132_HAIR = 132
    SBP_141_LONGHAIR = 141
    SBP_142_CIRCLET = 142
    SBP_143_EARS = 143
    SBP_150_DECAPITATEDHEAD = 150
    BP_TORSOCAP_HEAD = 201
    BP_TORSOCAP_HEAD2 = 202
    BP_TORSOCAP_LEFTARM = 203
    BP_TORSOCAP_LEFTARM2 = 204
    BP_TORSOCAP_RIGHTARM = 205
    BP_TORSOCAP_RIGHTARM2 = 206
    BP_TORSOCAP_LEFTLEG = 207
    BP_TORSOCAP_LEFTLEG2 = 208
    BP_TORSOCAP_LEFTLEG3 = 209
    BP_TORSOCAP_RIGHTLEG = 210
    BP_TORSOCAP_RIGHTLEG2 = 211
    BP_TORSOCAP_RIGHTLEG3 = 212
    BP_TORSOCAP_BRAIN = 213
    SBP_230_HEAD = 230
    BP_TORSOSECTION_HEAD = 1000
    BP_TORSOSECTION_HEAD2 = 2000
    BP_TORSOSECTION_LEFTARM = 3000
    BP_TORSOSECTION_LEFTARM2 = 4000
    BP_TORSOSECTION_RIGHTARM = 5000
    BP_TORSOSECTION_RIGHTARM2 = 6000
    BP_TORSOSECTION_LEFTLEG = 7000
    BP_TORSOSECTION_LEFTLEG2 = 8000
    BP_TORSOSECTION_LEFTLEG3 = 9000
    BP_TORSOSECTION_RIGHTLEG = 10000
    BP_TORSOSECTION_RIGHTLEG2 = 11000
    BP_TORSOSECTION_RIGHTLEG3 = 12000
    BP_TORSOSECTION_BRAIN = 13000


class BSLightingShaderType(IntEnum):
    """Values for configuring the shader type in a BSLightingShaderProperty"""

    Default = 0
    Environment_Map = 1
    Glow_Shader = 2
    Parallax = 3
    Face_Tint = 4
    Skin_Tint = 5
    Hair_Tint = 6
    Parallax_Occ = 7
    Multitexture_Landscape = 8
    LOD_Landscape = 9
    Snow = 10
    MultiLayer_Parallax = 11
    Tree_Anim = 12
    LOD_Objects = 13
    Sparkle_Snow = 14
    LOD_Objects_HD = 15
    Eye_Envmap = 16
    Cloud = 17
    LOD_Landscape_Noise = 18
    Multitexture_Landscape_LOD_Blend = 19
    FO4_Dismemberment = 20


class BSShaderCRC32(IntEnum):
    CAST_SHADOWS = 1563274220
    ZBUFFER_TEST = 1740048692
    ZBUFFER_WRITE = 3166356979
    TWO_SIDED = 759557230
    VERTEXCOLORS = 348504749
    PBR = 731263983
    SKINNED = 3744563888
    ENVMAP = 2893749418
    VERTEX_ALPHA = 2333069810
    FACE = 314919375
    GRAYSCALE_TO_PALETTE_COLOR = 442246519
    DECAL = 3849131744
    DYNAMIC_DECAL = 1576614759
    HAIRTINT = 1264105798
    SKIN_TINT = 1483897208
    EMIT_ENABLED = 2262553490
    GLOWMAP = 2399422528
    REFRACTION = 1957349758
    REFRACTION_FALLOFF = 902349195
    NOFADE = 2994043788
    INVERTED_FADE_PATTERN = 3030867718
    RGB_FALLOFF = 3448946507
    EXTERNAL_EMITTANCE = 2150459555
    MODELSPACENORMALS = 2548465567
    TRANSFORM_CHANGED = 3196772338
    EFFECT_LIGHTING = 3473438218
    FALLOFF = 3980660124
    SOFT_EFFECT = 3503164976
    GRAYSCALE_TO_PALETTE_ALPHA = 2901038324
    WEAPON_BLOOD = 2078326675
    LOD_OBJECTS = 2896726515
    NO_EXPOSURE = 3707406987


class BSShaderType(IntEnum):
    """FO3 Shader Type"""

    SHADER_TALL_GRASS = 0
    SHADER_DEFAULT = 1
    SHADER_SKY = 10
    SHADER_SKIN = 14
    SHADER_UNKNOWN = 15
    SHADER_WATER = 17
    SHADER_LIGHTING30 = 29
    SHADER_TILE = 32
    SHADER_NOLIGHTING = 33


class BSShaderType155(IntEnum):
    """Values for configuring the shader type in a BSLightingShaderProperty"""

    Default = 0
    Glow = 2
    Face_Tint = 3
    Skin_Tint = 4
    Hair_Tint = 5
    Eye_Envmap = 12
    Terrain = 17


class BillboardMode(IntEnum):
    """Determines the way the billboard will react to the camera.
        Billboard mode is stored in lowest 3 bits although Oblivion vanilla nifs uses values higher than 7."""

    ALWAYS_FACE_CAMERA = 0
    ROTATE_ABOUT_UP = 1
    RIGID_FACE_CAMERA = 2
    ALWAYS_FACE_CENTER = 3
    RIGID_FACE_CENTER = 4
    BSROTATE_ABOUT_UP = 5
    ROTATE_ABOUT_UP2 = 9
    UNKNOWN_8 = 8
    UNKNOWN_10 = 10
    UNKNOWN_11 = 11
    UNKNOWN_12 = 12


class BoundVolumeType(IntEnum):
    BASE_BV = 4294967295
    SPHERE_BV = 0
    BOX_BV = 1
    CAPSULE_BV = 2
    UNION_BV = 4
    HALFSPACE_BV = 5


class ConsistencyType(IntEnum):
    """Used by NiGeometryData to control the volatility of the mesh.
        Consistency Type is masked to only the upper 4 bits (0xF000). Dirty mask is the lower 12 (0x0FFF) but only used at runtime."""

    CT_MUTABLE = 0
    CT_STATIC = 16384
    CT_VOLATILE = 32768


class CycleType(IntEnum):
    """The animation cyle behavior."""

    CYCLE_LOOP = 0
    CYCLE_REVERSE = 1
    CYCLE_CLAMP = 2


class EndianType(IntEnum):
    ENDIAN_BIG = 0
    ENDIAN_LITTLE = 1


class ImageType(IntEnum):
    """Determines how the raw image data is stored in NiRawImageData."""

    RGB = 1
    RGBA = 2


class KeyType(IntEnum):
    """The type of animation interpolation (blending) that will be used on the associated key frames."""

    LINEAR_KEY = 1
    QUADRATIC_KEY = 2
    TBC_KEY = 3
    XYZ_ROTATION_KEY = 4
    CONST_KEY = 5


class MipMapFormat(IntEnum):
    """Describes how mipmaps are handled in an NiTexture."""

    MIP_FMT_NO = 0
    MIP_FMT_YES = 1
    MIP_FMT_DEFAULT = 2


class NiNBTMethod(IntEnum):
    NBT_METHOD_NONE = 0
    NBT_METHOD_NDL = 1
    NBT_METHOD_MAX = 2
    NBT_METHOD_ATI = 3


class PixelComponent(IntEnum):
    """Describes the pixel format used by the NiPixelData object to store a texture."""

    COMP_RED = 0
    COMP_GREEN = 1
    COMP_BLUE = 2
    COMP_ALPHA = 3
    COMP_COMPRESSED = 4
    COMP_OFFSET_U = 5
    COMP_OFFSET_V = 6
    COMP_OFFSET_W = 7
    COMP_OFFSET_Q = 8
    COMP_LUMA = 9
    COMP_HEIGHT = 10
    COMP_VECTOR_X = 11
    COMP_VECTOR_Y = 12
    COMP_VECTOR_Z = 13
    COMP_PADDING = 14
    COMP_INTENSITY = 15
    COMP_INDEX = 16
    COMP_DEPTH = 17
    COMP_STENCIL = 18
    COMP_EMPTY = 19


class PixelFormat(IntEnum):
    """Describes the pixel format used by the NiPixelData object to store a texture."""

    FMT_RGB = 0
    FMT_RGBA = 1
    FMT_PAL = 2
    FMT_PALA = 3
    FMT_DXT1 = 4
    FMT_DXT3 = 5
    FMT_DXT5 = 6
    FMT_RGB24NONINT = 7
    FMT_BUMP = 8
    FMT_BUMPLUMA = 9
    FMT_RENDERSPEC = 10
    FMT_1CH = 11
    FMT_2CH = 12
    FMT_3CH = 13
    FMT_4CH = 14
    FMT_DEPTH_STENCIL = 15
    FMT_UNKNOWN = 16


class PixelLayout(IntEnum):
    """Describes the color depth in an NiTexture."""

    LAY_PALETTIZED_8 = 0
    LAY_HIGH_COLOR_16 = 1
    LAY_TRUE_COLOR_32 = 2
    LAY_COMPRESSED = 3
    LAY_BUMPMAP = 4
    LAY_PALETTIZED_4 = 5
    LAY_DEFAULT = 6
    LAY_SINGLE_COLOR_8 = 7
    LAY_SINGLE_COLOR_16 = 8
    LAY_SINGLE_COLOR_32 = 9
    LAY_DOUBLE_COLOR_32 = 10
    LAY_DOUBLE_COLOR_64 = 11
    LAY_FLOAT_COLOR_32 = 12
    LAY_FLOAT_COLOR_64 = 13
    LAY_FLOAT_COLOR_128 = 14
    LAY_SINGLE_COLOR_4 = 15
    LAY_DEPTH_24_X8 = 16


class PixelRepresentation(IntEnum):
    """Describes how each pixel should be accessed on NiPixelFormat."""

    REP_NORM_INT = 0
    REP_HALF = 1
    REP_FLOAT = 2
    REP_INDEX = 3
    REP_COMPRESSED = 4
    REP_UNKNOWN = 5
    REP_INT = 6


class PixelTiling(IntEnum):
    """Describes whether pixels have been tiled from their standard row-major format to a format optimized for a particular platform."""

    TILE_NONE = 0
    TILE_XENON = 1
    TILE_WII = 2
    TILE_NV_SWIZZLED = 3


class ShadeFlags(IntEnum):
    """Flags for NiShadeProperty"""

    SHADING_HARD = 0
    SHADING_SMOOTH = 1


class TestFunction(IntEnum):
    """Describes Z-buffer test modes for NiZBufferProperty.
        "Less than" = closer to camera, "Greater than" = further from camera."""

    TEST_ALWAYS = 0
    TEST_LESS = 1
    TEST_EQUAL = 2
    TEST_LESS_EQUAL = 3
    TEST_GREATER = 4
    TEST_NOT_EQUAL = 5
    TEST_GREATER_EQUAL = 6
    TEST_NEVER = 7


class TexClampMode(IntEnum):
    """Describes the availiable texture clamp modes, i.e. the behavior of UV mapping outside the [0,1] range."""

    CLAMP_S_CLAMP_T = 0
    CLAMP_S_WRAP_T = 1
    WRAP_S_CLAMP_T = 2
    WRAP_S_WRAP_T = 3


class TexFilterMode(IntEnum):
    """Describes the availiable texture filter modes, i.e. the way the pixels in a texture are displayed on screen."""

    FILTER_NEAREST = 0
    FILTER_BILERP = 1
    FILTER_TRILERP = 2
    FILTER_NEAREST_MIPNEAREST = 3
    FILTER_NEAREST_MIPLERP = 4
    FILTER_BILERP_MIPNEAREST = 5
    FILTER_ANISOTROPIC = 6


class TransformMethod(IntEnum):
    """Describes the order of scaling and rotation matrices. Translate, Scale, Rotation, Center are from TexDesc.
        Back = inverse of Center. FromMaya = inverse of the V axis with a positive translation along V of 1 unit."""

    Maya_Deprecated = 0
    Max = 1
    Maya = 2


class AccumFlags(IntFlag):
    """Describes the options for the accum root on NiControllerSequence."""

    ACCUM_X_TRANS = 1 << 0
    ACCUM_Y_TRANS = 1 << 1
    ACCUM_Z_TRANS = 1 << 2
    ACCUM_X_ROT = 1 << 3
    ACCUM_Y_ROT = 1 << 4
    ACCUM_Z_ROT = 1 << 5
    ACCUM_X_FRONT = 1 << 6
    ACCUM_Y_FRONT = 1 << 7
    ACCUM_Z_FRONT = 1 << 8
    ACCUM_NEG_FRONT = 1 << 9


class BSPartFlag(IntFlag):
    """Editor flags for the Body Partitions."""

    PF_EDITOR_VISIBLE = 1 << 0
    PF_START_NET_BONESET = 1 << 8


class BSShaderFlags(IntFlag):
    """Shader Property Flags"""

    Specular = 1 << 0
    Skinned = 1 << 1
    LowDetail = 1 << 2
    Vertex_Alpha = 1 << 3
    Unknown_1 = 1 << 4
    Single_Pass = 1 << 5
    Empty = 1 << 6
    Environment_Mapping = 1 << 7
    Alpha_Texture = 1 << 8
    Unknown_2 = 1 << 9
    FaceGen = 1 << 10
    Parallax_Shader_Index_15 = 1 << 11
    Unknown_3 = 1 << 12
    Non_Projective_Shadows = 1 << 13
    Unknown_4 = 1 << 14
    Refraction = 1 << 15
    Fire_Refraction = 1 << 16
    Eye_Environment_Mapping = 1 << 17
    Hair = 1 << 18
    Dynamic_Alpha = 1 << 19
    Localmap_Hide_Secret = 1 << 20
    Window_Environment_Mapping = 1 << 21
    Tree_Billboard = 1 << 22
    Shadow_Frustum = 1 << 23
    Multiple_Textures = 1 << 24
    Remappable_Textures = 1 << 25
    Decal_Single_Pass = 1 << 26
    Dynamic_Decal_Single_Pass = 1 << 27
    Parallax_Occulsion = 1 << 28
    External_Emittance = 1 << 29
    Shadow_Map = 1 << 30
    ZBuffer_Test = 1 << 31


class BSShaderFlags2(IntFlag):
    """Shader Property Flags 2"""

    ZBuffer_Write = 1 << 0
    LOD_Landscape = 1 << 1
    LOD_Building = 1 << 2
    No_Fade = 1 << 3
    Refraction_Tint = 1 << 4
    Vertex_Colors = 1 << 5
    Unknown1 = 1 << 6
    First_Light_is_Point_Light = 1 << 7
    Second_Light = 1 << 8
    Third_Light = 1 << 9
    Vertex_Lighting = 1 << 10
    Uniform_Scale = 1 << 11
    Fit_Slope = 1 << 12
    Billboard_and_Envmap_Light_Fade = 1 << 13
    No_LOD_Land_Blend = 1 << 14
    Envmap_Light_Fade = 1 << 15
    Wireframe = 1 << 16
    VATS_Selection = 1 << 17
    Show_in_Local_Map = 1 << 18
    Premult_Alpha = 1 << 19
    Skip_Normal_Maps = 1 << 20
    Alpha_Decal = 1 << 21
    No_Transparecny_Multisampling = 1 << 22
    Unknown2 = 1 << 23
    Unknown3 = 1 << 24
    Unknown4 = 1 << 25
    Unknown5 = 1 << 26
    Unknown6 = 1 << 27
    Unknown7 = 1 << 28
    Unknown8 = 1 << 29
    Unknown9 = 1 << 30
    Unknown10 = 1 << 31


class Fallout4ShaderPropertyFlags1(IntFlag):
    """Fallout 4 Shader Property Flags 1"""

    Specular = 1 << 0
    Skinned = 1 << 1
    Temp_Refraction = 1 << 2
    Vertex_Alpha = 1 << 3
    GreyscaleToPalette_Color = 1 << 4
    GreyscaleToPalette_Alpha = 1 << 5
    Use_Falloff = 1 << 6
    Environment_Mapping = 1 << 7
    RGB_Falloff = 1 << 8
    Cast_Shadows = 1 << 9
    Face = 1 << 10
    UI_Mask_Rects = 1 << 11
    Model_Space_Normals = 1 << 12
    Non_Projective_Shadows = 1 << 13
    Landscape = 1 << 14
    Refraction = 1 << 15
    Fire_Refraction = 1 << 16
    Eye_Environment_Mapping = 1 << 17
    Hair = 1 << 18
    Screendoor_Alpha_Fade = 1 << 19
    Localmap_Hide_Secret = 1 << 20
    Skin_Tint = 1 << 21
    Own_Emit = 1 << 22
    Projected_UV = 1 << 23
    Multiple_Textures = 1 << 24
    Tessellate = 1 << 25
    Decal = 1 << 26
    Dynamic_Decal = 1 << 27
    Character_Lighting = 1 << 28
    External_Emittance = 1 << 29
    Soft_Effect = 1 << 30
    ZBuffer_Test = 1 << 31


class Fallout4ShaderPropertyFlags2(IntFlag):
    """Fallout 4 Shader Property Flags 2"""

    ZBuffer_Write = 1 << 0
    LOD_Landscape = 1 << 1
    LOD_Objects = 1 << 2
    No_Fade = 1 << 3
    Double_Sided = 1 << 4
    Vertex_Colors = 1 << 5
    Glow_Map = 1 << 6
    Transform_Changed = 1 << 7
    Dismemberment_Meatcuff = 1 << 8
    Tint = 1 << 9
    Grass_Vertex_Lighting = 1 << 10
    Grass_Uniform_Scale = 1 << 11
    Grass_Fit_Slope = 1 << 12
    Grass_Billboard = 1 << 13
    No_LOD_Land_Blend = 1 << 14
    Dismemberment = 1 << 15
    Wireframe = 1 << 16
    Weapon_Blood = 1 << 17
    Hide_On_Local_Map = 1 << 18
    Premult_Alpha = 1 << 19
    VATS_Target = 1 << 20
    Anisotropic_Lighting = 1 << 21
    Skew_Specular_Alpha = 1 << 22
    Menu_Screen = 1 << 23
    Multi_Layer_Parallax = 1 << 24
    Alpha_Test = 1 << 25
    Gradient_Remap = 1 << 26
    VATS_Target_Draw_All = 1 << 27
    Pipboy_Screen = 1 << 28
    Tree_Anim = 1 << 29
    Effect_Lighting = 1 << 30
    Refraction_Writes_Depth = 1 << 31


class InterpBlendFlags(IntFlag):
    """Flags for NiBlendInterpolator"""

    Manager_Controlled = 1 << 0
    Use_Only_Highest_Weight = 1 << 1


class NiSwitchFlags(IntFlag):
    """Flags for NiSwitchNode."""

    UpdateOnlyActiveChild = 1 << 0
    UpdateControllers = 1 << 1


class SkyrimShaderPropertyFlags1(IntFlag):
    """Skyrim Shader Property Flags 1"""

    Specular = 1 << 0
    Skinned = 1 << 1
    Temp_Refraction = 1 << 2
    Vertex_Alpha = 1 << 3
    Greyscale_To_PaletteColor = 1 << 4
    Greyscale_To_PaletteAlpha = 1 << 5
    Use_Falloff = 1 << 6
    Environment_Mapping = 1 << 7
    Recieve_Shadows = 1 << 8
    Cast_Shadows = 1 << 9
    Facegen_Detail_Map = 1 << 10
    Parallax = 1 << 11
    Model_Space_Normals = 1 << 12
    Non_Projective_Shadows = 1 << 13
    Landscape = 1 << 14
    Refraction = 1 << 15
    Fire_Refraction = 1 << 16
    Eye_Environment_Mapping = 1 << 17
    Hair_Soft_Lighting = 1 << 18
    Screendoor_Alpha_Fade = 1 << 19
    Localmap_Hide_Secret = 1 << 20
    FaceGen_RGB_Tint = 1 << 21
    Own_Emit = 1 << 22
    Projected_UV = 1 << 23
    Multiple_Textures = 1 << 24
    Remappable_Textures = 1 << 25
    Decal = 1 << 26
    Dynamic_Decal = 1 << 27
    Parallax_Occlusion = 1 << 28
    External_Emittance = 1 << 29
    Soft_Effect = 1 << 30
    ZBuffer_Test = 1 << 31


class SkyrimShaderPropertyFlags2(IntFlag):
    """Skyrim Shader Property Flags 2"""

    ZBuffer_Write = 1 << 0
    LOD_Landscape = 1 << 1
    LOD_Objects = 1 << 2
    No_Fade = 1 << 3
    Double_Sided = 1 << 4
    Vertex_Colors = 1 << 5
    Glow_Map = 1 << 6
    Assume_Shadowmask = 1 << 7
    Packed_Tangent = 1 << 8
    Multi_Index_Snow = 1 << 9
    Vertex_Lighting = 1 << 10
    Uniform_Scale = 1 << 11
    Fit_Slope = 1 << 12
    Billboard = 1 << 13
    No_LOD_Land_Blend = 1 << 14
    EnvMap_Light_Fade = 1 << 15
    Wireframe = 1 << 16
    Weapon_Blood = 1 << 17
    Hide_On_Local_Map = 1 << 18
    Premult_Alpha = 1 << 19
    Cloud_LOD = 1 << 20
    Anisotropic_Lighting = 1 << 21
    No_Transparency_Multisampling = 1 << 22
    Unused01 = 1 << 23
    Multi_Layer_Parallax = 1 << 24
    Soft_Lighting = 1 << 25
    Rim_Lighting = 1 << 26
    Back_Lighting = 1 << 27
    Unused02 = 1 << 28
    Tree_Anim = 1 << 29
    Effect_Lighting = 1 << 30
    HD_LOD_Objects = 1 << 31


class VertexAttribute(IntFlag):
    """The bits of BSVertexDesc that describe the enabled vertex attributes."""

    Vertex = 1 << 0
    UVs = 1 << 1
    UVs_2 = 1 << 2
    Normals = 1 << 3
    Tangents = 1 << 4
    Vertex_Colors = 1 << 5
    Skinned = 1 << 6
    Land_Data = 1 << 7
    Eye_Data = 1 << 8
    Instance = 1 << 9
    Full_Precision = 1 << 10
