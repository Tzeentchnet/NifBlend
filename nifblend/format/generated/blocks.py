"""Generated NIF block (niobject) types.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.base import Block, ReadContext
from nifblend.format.primitives import (
    read_array_f32,
    read_array_u16,
    read_array_u32,
    read_bool,
    read_f16,
    read_f32,
    read_i8,
    read_i16,
    read_i32,
    read_i64,
    read_sized_string,
    read_u8,
    read_u16,
    read_u32,
    read_u64,
    read_vec2_array,
    read_vec3_array,
    write_array_f32,
    write_array_u16,
    write_array_u32,
    write_bool,
    write_f16,
    write_f32,
    write_i8,
    write_i16,
    write_i32,
    write_i64,
    write_sized_string,
    write_u8,
    write_u16,
    write_u32,
    write_u64,
    write_vec2_array,
    write_vec3_array,
)
from nifblend.format.versions import pack_version

__all__ = ['AbstractAdditionalGeometryData', 'BSAnimNote', 'BSAnimNotes', 'BSDismemberSkinInstance', 'BSDynamicTriShape', 'BSEffectShaderProperty', 'BSGeometry', 'BSLODTriShape', 'BSLightingShaderProperty', 'BSMeshLODTriShape', 'BSShaderLightingProperty', 'BSShaderPPLightingProperty', 'BSShaderProperty', 'BSShaderTextureSet', 'BSSkinBoneData', 'BSSkinInstance', 'BSSubIndexTriShape', 'BSTriShape', 'BSXFlags', 'NiAVObject', 'NiAVObjectPalette', 'NiAlphaProperty', 'NiBillboardNode', 'NiBinaryExtraData', 'NiBlendInterpolator', 'NiCollisionObject', 'NiControllerManager', 'NiControllerSequence', 'NiDefaultAVObjectPalette', 'NiDynamicEffect', 'NiExtraData', 'NiGeometry', 'NiGeometryData', 'NiImage', 'NiIntegerExtraData', 'NiInterpController', 'NiInterpolator', 'NiKeyBasedInterpolator', 'NiKeyframeController', 'NiKeyframeData', 'NiLODData', 'NiLODNode', 'NiMaterialProperty', 'NiNode', 'NiObject', 'NiObjectNET', 'NiPixelFormat', 'NiProperty', 'NiRawImageData', 'NiSequence', 'NiShadeProperty', 'NiSingleInterpController', 'NiSkinData', 'NiSkinInstance', 'NiSkinPartition', 'NiSourceTexture', 'NiStringExtraData', 'NiStringPalette', 'NiSwitchNode', 'NiTextKeyExtraData', 'NiTexture', 'NiTexturingProperty', 'NiTimeController', 'NiTransformController', 'NiTransformData', 'NiTransformInterpolator', 'NiTriBasedGeom', 'NiTriBasedGeomData', 'NiTriShape', 'NiTriShapeData', 'NiTriStrips', 'NiTriStripsData']
from .structs import AVObject, BSGeometryPerSegmentSharedData, BSGeometrySegmentData, BSGeometrySegmentSharedData, BSGeometrySubSegment, BSMesh, BSMeshArray, BSSPLuminanceParams, BSSPTranslucencyParams, BSSPWetnessParams, BSSkinBoneTrans, BSStreamHeader, BSTextureArray, BSVertexData, BSVertexDataSSE, BodyPartList, BoneData, BoneVertData, BoundingVolume, BoxBV, ByteArray, ByteColor3, ByteColor4, ByteVector3, CapsuleBV, Color3, Color4, ControlledBlock, ExportString, FilePath, Footer, FormatPrefs, HalfSpaceBV, HalfTexCoord, HalfVector3, Header, InterpBlendItem, Key, KeyGroup, LODRange, LegacyExtraData, MatchGroup, MaterialData, Matrix22, Matrix33, NiBound, NiBoundAABB, NiPlane, NiQuatTransform, NiTransform, PixelFormatComponent, QuatKey, Quaternion, ShaderTexDesc, SizedString, SizedString16, SkinPartition, StringPalette, TBC, TexCoord, TexDesc, Triangle, UnionBV, Vector3, Vector4, string
from .bitfields import AlphaFlags, BSGeometryDataFlags, BSVertexDesc, NiGeometryDataFlags, TexturingFlags, TexturingMapFlags, TimeControllerFlags
from .enums import AccumFlags, AlphaFormat, AlphaFunction, AnimNoteType, AnimType, ApplyMode, BSDismemberBodyPartType, BSLightingShaderType, BSPartFlag, BSShaderCRC32, BSShaderFlags, BSShaderFlags2, BSShaderType, BSShaderType155, BillboardMode, BoundVolumeType, ConsistencyType, CycleType, EndianType, Fallout4ShaderPropertyFlags1, Fallout4ShaderPropertyFlags2, ImageType, InterpBlendFlags, KeyType, MipMapFormat, NiNBTMethod, NiSwitchFlags, PixelComponent, PixelFormat, PixelLayout, PixelRepresentation, PixelTiling, ShadeFlags, SkyrimShaderPropertyFlags1, SkyrimShaderPropertyFlags2, TestFunction, TexClampMode, TexFilterMode, TransformMethod, VertexAttribute


@dataclass(slots=True)
class AbstractAdditionalGeometryData(Block):
    pass


@dataclass(slots=True)
class BSAnimNote(Block):
    """Bethesda-specific object."""

    type: int = 0
    time: float = 0.0
    arm: int = 0
    gain: float = 0.0
    state: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSAnimNote:
        self = cls()
        self.type = read_u32(stream)
        self.time = read_f32(stream)
        if self.type == 1:
            self.arm = read_u32(stream)
        if self.type == 2:
            self.gain = read_f32(stream)
        if self.type == 2:
            self.state = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.type)
        write_f32(stream, self.time)
        if self.type == 1:
            write_u32(stream, self.arm)
        if self.type == 2:
            write_f32(stream, self.gain)
        if self.type == 2:
            write_u32(stream, self.state)


@dataclass(slots=True)
class BSAnimNotes(Block):
    """Bethesda-specific object."""

    num_anim_notes: int = 0
    anim_notes: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSAnimNotes:
        self = cls()
        self.num_anim_notes = read_u16(stream)
        self.anim_notes = [read_i32(stream) for _ in range(int(self.num_anim_notes))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.num_anim_notes)
        for __v in self.anim_notes:
            write_i32(stream, __v)


@dataclass(slots=True)
class BSDismemberSkinInstance(Block):
    """Bethesda-specific skin instance."""

    data: int = 0
    skin_partition: int = 0
    skeleton_root: int = 0
    num_bones: int = 0
    bones: list[int] = field(default_factory=list)
    num_partitions: int = 0
    partitions: list[BodyPartList | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSDismemberSkinInstance:
        self = cls()
        self.data = read_i32(stream)
        if ctx.version >= pack_version(10, 1, 0, 101):
            self.skin_partition = read_i32(stream)
        self.skeleton_root = read_i32(stream)
        self.num_bones = read_u32(stream)
        self.bones = [read_i32(stream) for _ in range(int(self.num_bones))]
        self.num_partitions = read_u32(stream)
        self.partitions = [BodyPartList.read(stream, ctx) for _ in range(int(self.num_partitions))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.data)
        if ctx.version >= pack_version(10, 1, 0, 101):
            write_i32(stream, self.skin_partition)
        write_i32(stream, self.skeleton_root)
        write_u32(stream, self.num_bones)
        for __v in self.bones:
            write_i32(stream, __v)
        write_u32(stream, self.num_partitions)
        for __v in self.partitions:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSDynamicTriShape(Block):
    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    shader_property: int = 0
    alpha_property: int = 0
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    num_triangles: int = 0
    num_triangles: int = 0
    num_vertices: int = 0
    data_size: int = 0
    vertex_data: list[BSVertexData | None] = field(default_factory=list)
    vertex_data: list[BSVertexDataSSE | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    particle_data_size: int = 0
    particle_vertices: list[HalfVector3 | None] = field(default_factory=list)
    particle_normals: list[HalfVector3 | None] = field(default_factory=list)
    particle_triangles: list[Triangle | None] = field(default_factory=list)
    dynamic_data_size: int = 0
    vertices: list[Vector4 | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSDynamicTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.bound_min_max = read_array_f32(stream, 6)
        self.skin = read_i32(stream)
        self.shader_property = read_i32(stream)
        self.alpha_property = read_i32(stream)
        self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.num_triangles = read_u32(stream)
        if (ctx.bs_version < 130):
            self.num_triangles = read_u16(stream)
        self.num_vertices = read_u16(stream)
        self.data_size = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexData.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexDataSSE.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.bs_version == 100):
            self.particle_data_size = read_u32(stream)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_vertices = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_normals = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        self.dynamic_data_size = read_u32(stream)
        self.vertices = [Vector4.read(stream, ctx) for _ in range(int(self.dynamic_data_size / 16))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        self.bounding_sphere.write(stream, ctx)
        if (ctx.bs_version >= 155):
            write_array_f32(stream, self.bound_min_max)
        write_i32(stream, self.skin)
        write_i32(stream, self.shader_property)
        write_i32(stream, self.alpha_property)
        self.vertex_desc.write(stream, ctx)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.num_triangles)
        if (ctx.bs_version < 130):
            write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_vertices)
        write_u32(stream, self.data_size)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.bs_version == 100):
            write_u32(stream, self.particle_data_size)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_vertices:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_normals:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_triangles:
                __v.write(stream, ctx)
        write_u32(stream, self.dynamic_data_size)
        for __v in self.vertices:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSEffectShaderProperty(Block):
    """Bethesda effect shader property for Skyrim and later."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    shader_type: int = 0
    shader_flags: int = 0
    shader_flags_2: int = 0
    environment_map_scale: float = 0.0
    shader_flags_1: int = 0
    shader_flags_2: int = 0
    shader_flags_1: int = 0
    shader_flags_2: int = 0
    num_sf1: int = 0
    num_sf2: int = 0
    sf1: list[int] = field(default_factory=list)
    sf2: list[int] = field(default_factory=list)
    uv_offset: TexCoord | None = None
    uv_scale: TexCoord | None = None
    source_texture: SizedString | None = None
    unk_float: float = 0.0
    texture_clamp_mode: int = 0
    lighting_influence: int = 0
    env_map_min_lod: int = 0
    unused_byte: int = 0
    falloff_start_angle: float = 0.0
    falloff_stop_angle: float = 0.0
    falloff_start_opacity: float = 0.0
    falloff_stop_opacity: float = 0.0
    refraction_power: float = 0.0
    base_color: Color4 | None = None
    base_color_scale: float = 0.0
    soft_falloff_depth: float = 0.0
    greyscale_texture: SizedString | None = None
    env_map_texture: SizedString | None = None
    normal_texture: SizedString | None = None
    env_mask_texture: SizedString | None = None
    environment_map_scale: float = 0.0
    reflectance_texture: SizedString | None = None
    lighting_texture: SizedString | None = None
    emittance_color: Color3 | None = None
    emit_gradient_texture: SizedString | None = None
    luminance: BSSPLuminanceParams | None = None
    unknown_bytes: list[int] = field(default_factory=list)
    unknown_floats: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_byte: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSEffectShaderProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        if (ctx.bs_version <= 34):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.environment_map_scale = read_f32(stream)
        if (ctx.bs_version < 130):
            self.shader_flags_1 = read_u32(stream)
        if (ctx.bs_version < 130):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version == 130):
            self.shader_flags_1 = read_u32(stream)
        if (ctx.bs_version == 130):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version >= 132):
            self.num_sf1 = read_u32(stream)
        if (ctx.bs_version >= 152):
            self.num_sf2 = read_u32(stream)
        if (ctx.bs_version >= 132):
            self.sf1 = [read_u32(stream) for _ in range(int(self.num_sf1))]
        if (ctx.bs_version >= 152):
            self.sf2 = [read_u32(stream) for _ in range(int(self.num_sf2))]
        self.uv_offset = TexCoord.read(stream, ctx)
        self.uv_scale = TexCoord.read(stream, ctx)
        self.source_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 172):
            self.unk_float = read_f32(stream)
        self.texture_clamp_mode = read_u8(stream)
        self.lighting_influence = read_u8(stream)
        self.env_map_min_lod = read_u8(stream)
        self.unused_byte = read_u8(stream)
        self.falloff_start_angle = read_f32(stream)
        self.falloff_stop_angle = read_f32(stream)
        self.falloff_start_opacity = read_f32(stream)
        self.falloff_stop_opacity = read_f32(stream)
        if (ctx.bs_version == 155):
            self.refraction_power = read_f32(stream)
        self.base_color = Color4.read(stream, ctx)
        self.base_color_scale = read_f32(stream)
        self.soft_falloff_depth = read_f32(stream)
        self.greyscale_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.env_map_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.normal_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.env_mask_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.environment_map_scale = read_f32(stream)
        if (ctx.bs_version >= 155):
            self.reflectance_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.lighting_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.emittance_color = Color3.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.emit_gradient_texture = SizedString.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.luminance = BSSPLuminanceParams.read(stream, ctx)
        if (ctx.bs_version >= 172):
            self.unknown_bytes = [read_u8(stream) for _ in range(7)]
        if (ctx.bs_version >= 172):
            self.unknown_floats = read_array_f32(stream, 6)
        if (ctx.bs_version >= 172):
            self.unknown_byte = read_u8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version <= 34):
            write_f32(stream, self.environment_map_scale)
        if (ctx.bs_version < 130):
            write_u32(stream, self.shader_flags_1)
        if (ctx.bs_version < 130):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version == 130):
            write_u32(stream, self.shader_flags_1)
        if (ctx.bs_version == 130):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version >= 132):
            write_u32(stream, self.num_sf1)
        if (ctx.bs_version >= 152):
            write_u32(stream, self.num_sf2)
        if (ctx.bs_version >= 132):
            for __v in self.sf1:
                write_u32(stream, __v)
        if (ctx.bs_version >= 152):
            for __v in self.sf2:
                write_u32(stream, __v)
        self.uv_offset.write(stream, ctx)
        self.uv_scale.write(stream, ctx)
        self.source_texture.write(stream, ctx)
        if (ctx.bs_version >= 172):
            write_f32(stream, self.unk_float)
        write_u8(stream, self.texture_clamp_mode)
        write_u8(stream, self.lighting_influence)
        write_u8(stream, self.env_map_min_lod)
        write_u8(stream, self.unused_byte)
        write_f32(stream, self.falloff_start_angle)
        write_f32(stream, self.falloff_stop_angle)
        write_f32(stream, self.falloff_start_opacity)
        write_f32(stream, self.falloff_stop_opacity)
        if (ctx.bs_version == 155):
            write_f32(stream, self.refraction_power)
        self.base_color.write(stream, ctx)
        write_f32(stream, self.base_color_scale)
        write_f32(stream, self.soft_falloff_depth)
        self.greyscale_texture.write(stream, ctx)
        if (ctx.bs_version >= 130):
            self.env_map_texture.write(stream, ctx)
        if (ctx.bs_version >= 130):
            self.normal_texture.write(stream, ctx)
        if (ctx.bs_version >= 130):
            self.env_mask_texture.write(stream, ctx)
        if (ctx.bs_version >= 130):
            write_f32(stream, self.environment_map_scale)
        if (ctx.bs_version >= 155):
            self.reflectance_texture.write(stream, ctx)
        if (ctx.bs_version >= 155):
            self.lighting_texture.write(stream, ctx)
        if (ctx.bs_version >= 155):
            self.emittance_color.write(stream, ctx)
        if (ctx.bs_version >= 155):
            self.emit_gradient_texture.write(stream, ctx)
        if (ctx.bs_version >= 155):
            self.luminance.write(stream, ctx)
        if (ctx.bs_version >= 172):
            for __v in self.unknown_bytes:
                write_u8(stream, __v)
        if (ctx.bs_version >= 172):
            write_array_f32(stream, self.unknown_floats)
        if (ctx.bs_version >= 172):
            write_u8(stream, self.unknown_byte)


@dataclass(slots=True)
class BSGeometry(Block):
    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    shader_property: int = 0
    alpha_property: int = 0
    meshes: list[BSMeshArray | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometry:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.bound_min_max = read_array_f32(stream, 6)
        self.skin = read_i32(stream)
        self.shader_property = read_i32(stream)
        self.alpha_property = read_i32(stream)
        self.meshes = [BSMeshArray.read(stream, ctx) for _ in range(4)]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        self.bounding_sphere.write(stream, ctx)
        write_array_f32(stream, self.bound_min_max)
        write_i32(stream, self.skin)
        write_i32(stream, self.shader_property)
        write_i32(stream, self.alpha_property)
        for __v in self.meshes:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSLODTriShape(Block):
    """A variation on NiTriShape, for visibility control over vertex groups."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    data: int = 0
    data: int = 0
    skin_instance: int = 0
    skin_instance: int = 0
    material_data: MaterialData | None = None
    material_data: MaterialData | None = None
    shader_property: int = 0
    alpha_property: int = 0
    lod0_size: int = 0
    lod1_size: int = 0
    lod2_size: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSLODTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            self.bound_min_max = read_array_f32(stream, 6)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin = read_i32(stream)
        if (ctx.bs_version < 100):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.shader_property = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.alpha_property = read_i32(stream)
        self.lod0_size = read_u32(stream)
        self.lod1_size = read_u32(stream)
        self.lod2_size = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            write_array_f32(stream, self.bound_min_max)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin)
        if (ctx.bs_version < 100):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.shader_property)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.alpha_property)
        write_u32(stream, self.lod0_size)
        write_u32(stream, self.lod1_size)
        write_u32(stream, self.lod2_size)


@dataclass(slots=True)
class BSLightingShaderProperty(Block):
    """Bethesda shader property for Skyrim and later."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    shader_type: int = 0
    shader_flags: int = 0
    shader_flags_2: int = 0
    environment_map_scale: float = 0.0
    shader_flags_1: int = 0
    shader_flags_2: int = 0
    shader_flags_1: int = 0
    shader_flags_2: int = 0
    shader_type: int = 0
    num_sf1: int = 0
    num_sf2: int = 0
    sf1: list[int] = field(default_factory=list)
    sf2: list[int] = field(default_factory=list)
    uv_offset: TexCoord | None = None
    uv_scale: TexCoord | None = None
    texture_set: int = 0
    emissive_color: Color3 | None = None
    emissive_multiple: float = 0.0
    root_material: int = 0
    unk_float: float = 0.0
    texture_clamp_mode: int = 0
    alpha: float = 0.0
    refraction_strength: float = 0.0
    glossiness: float = 0.0
    smoothness: float = 0.0
    specular_color: Color3 | None = None
    specular_strength: float = 0.0
    lighting_effect_1: float = 0.0
    lighting_effect_2: float = 0.0
    subsurface_rolloff: float = 0.0
    rimlight_power: float = 0.0
    backlight_power: float = 0.0
    grayscale_to_palette_scale: float = 0.0
    fresnel_power: float = 0.0
    wetness: BSSPWetnessParams | None = None
    luminance: BSSPLuminanceParams | None = None
    do_translucency: bool = False
    translucency: BSSPTranslucencyParams | None = None
    has_texture_arrays: bool = False
    num_texture_arrays: int = 0
    texture_arrays: list[BSTextureArray | None] = field(default_factory=list)
    unk_float_1: float = 0.0
    unk_float_2: float = 0.0
    unk_short_1: int = 0
    environment_map_scale: float = 0.0
    use_screen_space_reflections: bool = False
    wetness_control_use_ssr: bool = False
    skin_tint_color: Color4 | None = None
    hair_tint_color: Color3 | None = None
    skin_tint_color: Color3 | None = None
    skin_tint_alpha: float = 0.0
    hair_tint_color: Color3 | None = None
    max_passes: float = 0.0
    scale: float = 0.0
    parallax_inner_layer_thickness: float = 0.0
    parallax_refraction_scale: float = 0.0
    parallax_inner_layer_texture_scale: TexCoord | None = None
    parallax_envmap_strength: float = 0.0
    sparkle_parameters: Vector4 | None = None
    eye_cubemap_scale: float = 0.0
    left_eye_reflection_center: Vector3 | None = None
    right_eye_reflection_center: Vector3 | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSLightingShaderProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        if (ctx.bs_version <= 34):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.environment_map_scale = read_f32(stream)
        if (ctx.bs_version < 130):
            self.shader_flags_1 = read_u32(stream)
        if (ctx.bs_version < 130):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version == 130):
            self.shader_flags_1 = read_u32(stream)
        if (ctx.bs_version == 130):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version >= 155):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version >= 132):
            self.num_sf1 = read_u32(stream)
        if (ctx.bs_version >= 152):
            self.num_sf2 = read_u32(stream)
        if (ctx.bs_version >= 132):
            self.sf1 = [read_u32(stream) for _ in range(int(self.num_sf1))]
        if (ctx.bs_version >= 152):
            self.sf2 = [read_u32(stream) for _ in range(int(self.num_sf2))]
        self.uv_offset = TexCoord.read(stream, ctx)
        self.uv_scale = TexCoord.read(stream, ctx)
        self.texture_set = read_i32(stream)
        self.emissive_color = Color3.read(stream, ctx)
        self.emissive_multiple = read_f32(stream)
        if (ctx.bs_version >= 130):
            self.root_material = read_u32(stream)
        if (ctx.bs_version >= 172):
            self.unk_float = read_f32(stream)
        self.texture_clamp_mode = read_u32(stream)
        self.alpha = read_f32(stream)
        self.refraction_strength = read_f32(stream)
        if (ctx.bs_version < 130):
            self.glossiness = read_f32(stream)
        if (ctx.bs_version >= 130):
            self.smoothness = read_f32(stream)
        self.specular_color = Color3.read(stream, ctx)
        self.specular_strength = read_f32(stream)
        if (ctx.bs_version < 130):
            self.lighting_effect_1 = read_f32(stream)
        if (ctx.bs_version < 130):
            self.lighting_effect_2 = read_f32(stream)
        if ((ctx.bs_version >= 130) and (ctx.bs_version <= 139)):
            self.subsurface_rolloff = read_f32(stream)
        if ((ctx.bs_version >= 130) and (ctx.bs_version <= 139)):
            self.rimlight_power = read_f32(stream)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and ((self.rimlight_power >= 3.402823466e+38) and (self.rimlight_power < float('inf'))):
            self.backlight_power = read_f32(stream)
        if (ctx.bs_version >= 130):
            self.grayscale_to_palette_scale = read_f32(stream)
        if (ctx.bs_version >= 130):
            self.fresnel_power = read_f32(stream)
        if (ctx.bs_version >= 130):
            self.wetness = BSSPWetnessParams.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.luminance = BSSPLuminanceParams.read(stream, ctx)
        if (ctx.bs_version == 155):
            self.do_translucency = read_bool(stream)
        if ((ctx.bs_version == 155)) and (self.do_translucency):
            self.translucency = BSSPTranslucencyParams.read(stream, ctx)
        if (ctx.bs_version == 155):
            self.has_texture_arrays = read_bool(stream)
        if ((ctx.bs_version == 155)) and (self.has_texture_arrays):
            self.num_texture_arrays = read_u32(stream)
        if ((ctx.bs_version == 155)) and (self.has_texture_arrays):
            self.texture_arrays = [BSTextureArray.read(stream, ctx) for _ in range(int(self.num_texture_arrays))]
        if (ctx.bs_version >= 172):
            self.unk_float_1 = read_f32(stream)
        if (ctx.bs_version >= 172):
            self.unk_float_2 = read_f32(stream)
        if (ctx.bs_version >= 172):
            self.unk_short_1 = read_u16(stream)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 1):
            self.environment_map_scale = read_f32(stream)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 1):
            self.use_screen_space_reflections = read_bool(stream)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 1):
            self.wetness_control_use_ssr = read_bool(stream)
        if ((ctx.bs_version >= 155)) and (self.shader_type == 4):
            self.skin_tint_color = Color4.read(stream, ctx)
        if ((ctx.bs_version >= 155)) and (self.shader_type == 5):
            self.hair_tint_color = Color3.read(stream, ctx)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 5):
            self.skin_tint_color = Color3.read(stream, ctx)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 5):
            self.skin_tint_alpha = read_f32(stream)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 6):
            self.hair_tint_color = Color3.read(stream, ctx)
        if self.shader_type == 7:
            self.max_passes = read_f32(stream)
        if self.shader_type == 7:
            self.scale = read_f32(stream)
        if self.shader_type == 11:
            self.parallax_inner_layer_thickness = read_f32(stream)
        if self.shader_type == 11:
            self.parallax_refraction_scale = read_f32(stream)
        if self.shader_type == 11:
            self.parallax_inner_layer_texture_scale = TexCoord.read(stream, ctx)
        if self.shader_type == 11:
            self.parallax_envmap_strength = read_f32(stream)
        if self.shader_type == 14:
            self.sparkle_parameters = Vector4.read(stream, ctx)
        if self.shader_type == 16:
            self.eye_cubemap_scale = read_f32(stream)
        if self.shader_type == 16:
            self.left_eye_reflection_center = Vector3.read(stream, ctx)
        if self.shader_type == 16:
            self.right_eye_reflection_center = Vector3.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version <= 34):
            write_f32(stream, self.environment_map_scale)
        if (ctx.bs_version < 130):
            write_u32(stream, self.shader_flags_1)
        if (ctx.bs_version < 130):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version == 130):
            write_u32(stream, self.shader_flags_1)
        if (ctx.bs_version == 130):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version >= 155):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version >= 132):
            write_u32(stream, self.num_sf1)
        if (ctx.bs_version >= 152):
            write_u32(stream, self.num_sf2)
        if (ctx.bs_version >= 132):
            for __v in self.sf1:
                write_u32(stream, __v)
        if (ctx.bs_version >= 152):
            for __v in self.sf2:
                write_u32(stream, __v)
        self.uv_offset.write(stream, ctx)
        self.uv_scale.write(stream, ctx)
        write_i32(stream, self.texture_set)
        self.emissive_color.write(stream, ctx)
        write_f32(stream, self.emissive_multiple)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.root_material)
        if (ctx.bs_version >= 172):
            write_f32(stream, self.unk_float)
        write_u32(stream, self.texture_clamp_mode)
        write_f32(stream, self.alpha)
        write_f32(stream, self.refraction_strength)
        if (ctx.bs_version < 130):
            write_f32(stream, self.glossiness)
        if (ctx.bs_version >= 130):
            write_f32(stream, self.smoothness)
        self.specular_color.write(stream, ctx)
        write_f32(stream, self.specular_strength)
        if (ctx.bs_version < 130):
            write_f32(stream, self.lighting_effect_1)
        if (ctx.bs_version < 130):
            write_f32(stream, self.lighting_effect_2)
        if ((ctx.bs_version >= 130) and (ctx.bs_version <= 139)):
            write_f32(stream, self.subsurface_rolloff)
        if ((ctx.bs_version >= 130) and (ctx.bs_version <= 139)):
            write_f32(stream, self.rimlight_power)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and ((self.rimlight_power >= 3.402823466e+38) and (self.rimlight_power < float('inf'))):
            write_f32(stream, self.backlight_power)
        if (ctx.bs_version >= 130):
            write_f32(stream, self.grayscale_to_palette_scale)
        if (ctx.bs_version >= 130):
            write_f32(stream, self.fresnel_power)
        if (ctx.bs_version >= 130):
            self.wetness.write(stream, ctx)
        if (ctx.bs_version >= 155):
            self.luminance.write(stream, ctx)
        if (ctx.bs_version == 155):
            write_bool(stream, self.do_translucency)
        if ((ctx.bs_version == 155)) and (self.do_translucency):
            self.translucency.write(stream, ctx)
        if (ctx.bs_version == 155):
            write_bool(stream, self.has_texture_arrays)
        if ((ctx.bs_version == 155)) and (self.has_texture_arrays):
            write_u32(stream, self.num_texture_arrays)
        if ((ctx.bs_version == 155)) and (self.has_texture_arrays):
            for __v in self.texture_arrays:
                __v.write(stream, ctx)
        if (ctx.bs_version >= 172):
            write_f32(stream, self.unk_float_1)
        if (ctx.bs_version >= 172):
            write_f32(stream, self.unk_float_2)
        if (ctx.bs_version >= 172):
            write_u16(stream, self.unk_short_1)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 1):
            write_f32(stream, self.environment_map_scale)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 1):
            write_bool(stream, self.use_screen_space_reflections)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 1):
            write_bool(stream, self.wetness_control_use_ssr)
        if ((ctx.bs_version >= 155)) and (self.shader_type == 4):
            self.skin_tint_color.write(stream, ctx)
        if ((ctx.bs_version >= 155)) and (self.shader_type == 5):
            self.hair_tint_color.write(stream, ctx)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 5):
            self.skin_tint_color.write(stream, ctx)
        if (((ctx.bs_version >= 130) and (ctx.bs_version <= 139))) and (self.shader_type == 5):
            write_f32(stream, self.skin_tint_alpha)
        if ((ctx.bs_version <= 139)) and (self.shader_type == 6):
            self.hair_tint_color.write(stream, ctx)
        if self.shader_type == 7:
            write_f32(stream, self.max_passes)
        if self.shader_type == 7:
            write_f32(stream, self.scale)
        if self.shader_type == 11:
            write_f32(stream, self.parallax_inner_layer_thickness)
        if self.shader_type == 11:
            write_f32(stream, self.parallax_refraction_scale)
        if self.shader_type == 11:
            self.parallax_inner_layer_texture_scale.write(stream, ctx)
        if self.shader_type == 11:
            write_f32(stream, self.parallax_envmap_strength)
        if self.shader_type == 14:
            self.sparkle_parameters.write(stream, ctx)
        if self.shader_type == 16:
            write_f32(stream, self.eye_cubemap_scale)
        if self.shader_type == 16:
            self.left_eye_reflection_center.write(stream, ctx)
        if self.shader_type == 16:
            self.right_eye_reflection_center.write(stream, ctx)


@dataclass(slots=True)
class BSMeshLODTriShape(Block):
    """Fallout 4 LOD Tri Shape"""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    shader_property: int = 0
    alpha_property: int = 0
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    num_triangles: int = 0
    num_triangles: int = 0
    num_vertices: int = 0
    data_size: int = 0
    vertex_data: list[BSVertexData | None] = field(default_factory=list)
    vertex_data: list[BSVertexDataSSE | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    particle_data_size: int = 0
    particle_vertices: list[HalfVector3 | None] = field(default_factory=list)
    particle_normals: list[HalfVector3 | None] = field(default_factory=list)
    particle_triangles: list[Triangle | None] = field(default_factory=list)
    lod0_size: int = 0
    lod1_size: int = 0
    lod2_size: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSMeshLODTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.bound_min_max = read_array_f32(stream, 6)
        self.skin = read_i32(stream)
        self.shader_property = read_i32(stream)
        self.alpha_property = read_i32(stream)
        self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.num_triangles = read_u32(stream)
        if (ctx.bs_version < 130):
            self.num_triangles = read_u16(stream)
        self.num_vertices = read_u16(stream)
        self.data_size = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexData.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexDataSSE.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.bs_version == 100):
            self.particle_data_size = read_u32(stream)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_vertices = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_normals = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        self.lod0_size = read_u32(stream)
        self.lod1_size = read_u32(stream)
        self.lod2_size = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        self.bounding_sphere.write(stream, ctx)
        if (ctx.bs_version >= 155):
            write_array_f32(stream, self.bound_min_max)
        write_i32(stream, self.skin)
        write_i32(stream, self.shader_property)
        write_i32(stream, self.alpha_property)
        self.vertex_desc.write(stream, ctx)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.num_triangles)
        if (ctx.bs_version < 130):
            write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_vertices)
        write_u32(stream, self.data_size)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.bs_version == 100):
            write_u32(stream, self.particle_data_size)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_vertices:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_normals:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_triangles:
                __v.write(stream, ctx)
        write_u32(stream, self.lod0_size)
        write_u32(stream, self.lod1_size)
        write_u32(stream, self.lod2_size)


@dataclass(slots=True)
class BSShaderLightingProperty(Block):
    """Bethesda-specific property."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    shader_type: int = 0
    shader_flags: int = 0
    shader_flags_2: int = 0
    environment_map_scale: float = 0.0
    texture_clamp_mode: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSShaderLightingProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        if (ctx.bs_version <= 34):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.environment_map_scale = read_f32(stream)
        if (ctx.bs_version <= 34):
            self.texture_clamp_mode = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version <= 34):
            write_f32(stream, self.environment_map_scale)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.texture_clamp_mode)


@dataclass(slots=True)
class BSShaderPPLightingProperty(Block):
    """Bethesda-specific property."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    shader_type: int = 0
    shader_flags: int = 0
    shader_flags_2: int = 0
    environment_map_scale: float = 0.0
    texture_clamp_mode: int = 0
    texture_set: int = 0
    refraction_strength: float = 0.0
    refraction_fire_period: int = 0
    parallax_max_passes: float = 0.0
    parallax_scale: float = 0.0
    emissive_color: Color4 | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSShaderPPLightingProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        if (ctx.bs_version <= 34):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.environment_map_scale = read_f32(stream)
        if (ctx.bs_version <= 34):
            self.texture_clamp_mode = read_u32(stream)
        self.texture_set = read_i32(stream)
        if ctx.bs_version > 14:
            self.refraction_strength = read_f32(stream)
        if ctx.bs_version > 14:
            self.refraction_fire_period = read_i32(stream)
        if ctx.bs_version > 24:
            self.parallax_max_passes = read_f32(stream)
        if ctx.bs_version > 24:
            self.parallax_scale = read_f32(stream)
        if (ctx.bs_version > 34):
            self.emissive_color = Color4.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version <= 34):
            write_f32(stream, self.environment_map_scale)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.texture_clamp_mode)
        write_i32(stream, self.texture_set)
        if ctx.bs_version > 14:
            write_f32(stream, self.refraction_strength)
        if ctx.bs_version > 14:
            write_i32(stream, self.refraction_fire_period)
        if ctx.bs_version > 24:
            write_f32(stream, self.parallax_max_passes)
        if ctx.bs_version > 24:
            write_f32(stream, self.parallax_scale)
        if (ctx.bs_version > 34):
            self.emissive_color.write(stream, ctx)


@dataclass(slots=True)
class BSShaderProperty(Block):
    """Bethesda-specific property."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    shader_type: int = 0
    shader_flags: int = 0
    shader_flags_2: int = 0
    environment_map_scale: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSShaderProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        if (ctx.bs_version <= 34):
            self.shader_type = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.shader_flags_2 = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.environment_map_scale = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_type)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.shader_flags_2)
        if (ctx.bs_version <= 34):
            write_f32(stream, self.environment_map_scale)


@dataclass(slots=True)
class BSShaderTextureSet(Block):
    """Bethesda-specific Texture Set."""

    num_textures: int = 0
    textures: list[SizedString | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSShaderTextureSet:
        self = cls()
        self.num_textures = read_u32(stream)
        self.textures = [SizedString.read(stream, ctx) for _ in range(int(self.num_textures))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_textures)
        for __v in self.textures:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSSkinBoneData(Block):
    """Fallout 4 Bone Data"""

    num_bones: int = 0
    bone_list: list[BSSkinBoneTrans | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSkinBoneData:
        self = cls()
        self.num_bones = read_u32(stream)
        self.bone_list = [BSSkinBoneTrans.read(stream, ctx) for _ in range(int(self.num_bones))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_bones)
        for __v in self.bone_list:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSSkinInstance(Block):
    """Fallout 4 Skin Instance"""

    skeleton_root: int = 0
    data: int = 0
    num_bones: int = 0
    bones: list[int] = field(default_factory=list)
    num_scales: int = 0
    scales: list[Vector3 | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSkinInstance:
        self = cls()
        self.skeleton_root = read_i32(stream)
        self.data = read_i32(stream)
        self.num_bones = read_u32(stream)
        self.bones = [read_i32(stream) for _ in range(int(self.num_bones))]
        self.num_scales = read_u32(stream)
        self.scales = [Vector3.read(stream, ctx) for _ in range(int(self.num_scales))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.skeleton_root)
        write_i32(stream, self.data)
        write_u32(stream, self.num_bones)
        for __v in self.bones:
            write_i32(stream, __v)
        write_u32(stream, self.num_scales)
        for __v in self.scales:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSSubIndexTriShape(Block):
    """Fallout 4 Sub-Index Tri Shape"""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    shader_property: int = 0
    alpha_property: int = 0
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    num_triangles: int = 0
    num_triangles: int = 0
    num_vertices: int = 0
    data_size: int = 0
    vertex_data: list[BSVertexData | None] = field(default_factory=list)
    vertex_data: list[BSVertexDataSSE | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    particle_data_size: int = 0
    particle_vertices: list[HalfVector3 | None] = field(default_factory=list)
    particle_normals: list[HalfVector3 | None] = field(default_factory=list)
    particle_triangles: list[Triangle | None] = field(default_factory=list)
    num_primitives: int = 0
    num_segments: int = 0
    total_segments: int = 0
    segment: list[BSGeometrySegmentData | None] = field(default_factory=list)
    segment_data: BSGeometrySegmentSharedData | None = None
    num_segments: int = 0
    segment: list[BSGeometrySegmentData | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSubIndexTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.bound_min_max = read_array_f32(stream, 6)
        self.skin = read_i32(stream)
        self.shader_property = read_i32(stream)
        self.alpha_property = read_i32(stream)
        self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.num_triangles = read_u32(stream)
        if (ctx.bs_version < 130):
            self.num_triangles = read_u16(stream)
        self.num_vertices = read_u16(stream)
        self.data_size = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexData.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexDataSSE.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.bs_version == 100):
            self.particle_data_size = read_u32(stream)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_vertices = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_normals = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            self.num_primitives = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            self.num_segments = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            self.total_segments = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            self.segment = [BSGeometrySegmentData.read(stream, ctx) for _ in range(int(self.num_segments))]
        if ((ctx.bs_version >= 130)) and ((self.num_segments < self.total_segments) and (self.data_size > 0)):
            self.segment_data = BSGeometrySegmentSharedData.read(stream, ctx)
        if (ctx.bs_version == 100):
            self.num_segments = read_u32(stream)
        if (ctx.bs_version == 100):
            self.segment = [BSGeometrySegmentData.read(stream, ctx) for _ in range(int(self.num_segments))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        self.bounding_sphere.write(stream, ctx)
        if (ctx.bs_version >= 155):
            write_array_f32(stream, self.bound_min_max)
        write_i32(stream, self.skin)
        write_i32(stream, self.shader_property)
        write_i32(stream, self.alpha_property)
        self.vertex_desc.write(stream, ctx)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.num_triangles)
        if (ctx.bs_version < 130):
            write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_vertices)
        write_u32(stream, self.data_size)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.bs_version == 100):
            write_u32(stream, self.particle_data_size)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_vertices:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_normals:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_triangles:
                __v.write(stream, ctx)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            write_u32(stream, self.num_primitives)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            write_u32(stream, self.num_segments)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            write_u32(stream, self.total_segments)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            for __v in self.segment:
                __v.write(stream, ctx)
        if ((ctx.bs_version >= 130)) and ((self.num_segments < self.total_segments) and (self.data_size > 0)):
            self.segment_data.write(stream, ctx)
        if (ctx.bs_version == 100):
            write_u32(stream, self.num_segments)
        if (ctx.bs_version == 100):
            for __v in self.segment:
                __v.write(stream, ctx)


@dataclass(slots=True)
class BSTriShape(Block):
    """Fallout 4 Tri Shape"""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    shader_property: int = 0
    alpha_property: int = 0
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    num_triangles: int = 0
    num_triangles: int = 0
    num_vertices: int = 0
    data_size: int = 0
    vertex_data: list[BSVertexData | None] = field(default_factory=list)
    vertex_data: list[BSVertexDataSSE | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    particle_data_size: int = 0
    particle_vertices: list[HalfVector3 | None] = field(default_factory=list)
    particle_normals: list[HalfVector3 | None] = field(default_factory=list)
    particle_triangles: list[Triangle | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.bs_version >= 155):
            self.bound_min_max = read_array_f32(stream, 6)
        self.skin = read_i32(stream)
        self.shader_property = read_i32(stream)
        self.alpha_property = read_i32(stream)
        self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.bs_version >= 130):
            self.num_triangles = read_u32(stream)
        if (ctx.bs_version < 130):
            self.num_triangles = read_u16(stream)
        self.num_vertices = read_u16(stream)
        self.data_size = read_u32(stream)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexData.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexDataSSE.read(stream, ctx) for _ in range(int(self.num_vertices))]
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.bs_version == 100):
            self.particle_data_size = read_u32(stream)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_vertices = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_normals = [HalfVector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            self.particle_triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        self.bounding_sphere.write(stream, ctx)
        if (ctx.bs_version >= 155):
            write_array_f32(stream, self.bound_min_max)
        write_i32(stream, self.skin)
        write_i32(stream, self.shader_property)
        write_i32(stream, self.alpha_property)
        self.vertex_desc.write(stream, ctx)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.num_triangles)
        if (ctx.bs_version < 130):
            write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_vertices)
        write_u32(stream, self.data_size)
        if ((ctx.bs_version >= 130)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if self.data_size > 0:
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.bs_version == 100):
            write_u32(stream, self.particle_data_size)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_vertices:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_normals:
                __v.write(stream, ctx)
        if ((ctx.bs_version == 100)) and (self.particle_data_size > 0):
            for __v in self.particle_triangles:
                __v.write(stream, ctx)


@dataclass(slots=True)
class BSXFlags(Block):
    """Controls animation and collision.  Integer holds flags:
        Bit 0 : enable havok, bAnimated(Skyrim)
        Bit 1 : enable collision, bHavok(Skyrim)
        Bit 2 : is skeleton nif?, bRagdoll(Skyrim)
        Bit 3 : enable animation, bComplex(Skyrim)
        Bit 4 : FlameNodes present, bAddon(Skyrim)
        Bit 5 : EditorMarkers present, bEditorMarker(Skyrim)
        Bit 6 : bDynamic(Skyrim)
        Bit 7 : bArticulated(Skyrim)
        Bit 8 : bIKTarget(Skyrim)/needsTransformUpdates
        Bit 9 : bExternalEmit(Skyrim)
        Bit 10: bMagicShaderParticles(Skyrim)
        Bit 11: bLights(Skyrim)
        Bit 12: bBreakable(Skyrim)
        Bit 13: bSearchedBreakable(Skyrim) .. Runtime only?"""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0
    integer_data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSXFlags:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        self.integer_data = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)
        write_u32(stream, self.integer_data)


@dataclass(slots=True)
class NiAVObject(Block):
    """Abstract audio-visual base class from which all of Gamebryo's scene graph objects inherit."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiAVObject:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)


@dataclass(slots=True)
class NiAVObjectPalette(Block):
    """Abstract base class for indexing NiAVObject by name."""

    pass


@dataclass(slots=True)
class NiAlphaProperty(Block):
    """Transparency. Flags 0x00ED."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: AlphaFlags | None = field(default_factory=AlphaFlags)
    threshold: int = 0
    unknown_short_1: int = 0
    unknown_int_2: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiAlphaProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        self.flags = AlphaFlags.read(stream, ctx)
        self.threshold = read_u8(stream)
        if ctx.version <= pack_version(2, 3):
            self.unknown_short_1 = read_u16(stream)
        if ctx.version <= pack_version(2, 3):
            self.unknown_int_2 = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        self.flags.write(stream, ctx)
        write_u8(stream, self.threshold)
        if ctx.version <= pack_version(2, 3):
            write_u16(stream, self.unknown_short_1)
        if ctx.version <= pack_version(2, 3):
            write_u32(stream, self.unknown_int_2)


@dataclass(slots=True)
class NiBillboardNode(Block):
    """These nodes will always be rotated to face the camera creating a billboard effect for any attached objects.

        In pre-10.1.0.0 the Flags field is used for BillboardMode.
        Bit 0: hidden
        Bits 1-2: collision mode
        Bit 3: unknown (set in most official meshes)
        Bits 5-6: billboard mode

        Collision modes:
        00 NONE
        01 USE_TRIANGLES
        10 USE_OBBS
        11 CONTINUE

        Billboard modes:
        00 ALWAYS_FACE_CAMERA
        01 ROTATE_ABOUT_UP
        10 RIGID_FACE_CAMERA
        11 ALWAYS_FACE_CENTER"""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    num_children: int = 0
    children: list[int] = field(default_factory=list)
    num_effects: int = 0
    effects: list[int] = field(default_factory=list)
    billboard_mode: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiBillboardNode:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.num_children = read_u32(stream)
        self.children = [read_i32(stream) for _ in range(int(self.num_children))]
        if (ctx.bs_version < 130):
            self.num_effects = read_u32(stream)
        if (ctx.bs_version < 130):
            self.effects = [read_i32(stream) for _ in range(int(self.num_effects))]
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.billboard_mode = read_u16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        write_u32(stream, self.num_children)
        for __v in self.children:
            write_i32(stream, __v)
        if (ctx.bs_version < 130):
            write_u32(stream, self.num_effects)
        if (ctx.bs_version < 130):
            for __v in self.effects:
                write_i32(stream, __v)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u16(stream, self.billboard_mode)


@dataclass(slots=True)
class NiBinaryExtraData(Block):
    """Binary extra data object. Used to store tangents and bitangents in Oblivion."""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0
    binary_data: ByteArray | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiBinaryExtraData:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        self.binary_data = ByteArray.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)
        self.binary_data.write(stream, ctx)


@dataclass(slots=True)
class NiBlendInterpolator(Block):
    """Abstract base class for all NiInterpolators that blend the results of sub-interpolators together to compute a final weighted value."""

    flags: int = 0
    array_size: int = 0
    array_grow_by: int = 0
    array_size: int = 0
    weight_threshold: float = 0.0
    interp_count: int = 0
    single_index: int = 0
    high_priority: int = 0
    next_high_priority: int = 0
    single_time: float = 0.0
    high_weights_sum: float = 0.0
    next_high_weights_sum: float = 0.0
    high_ease_spinner: float = 0.0
    interp_array_items: list[InterpBlendItem | None] = field(default_factory=list)
    interp_array_items: list[InterpBlendItem | None] = field(default_factory=list)
    manager_controlled: bool = False
    weight_threshold: float = 0.0
    only_use_highest_weight: bool = False
    interp_count: int = 0
    single_index: int = 0
    interp_count: int = 0
    single_index: int = 0
    single_interpolator: int = 0
    single_time: float = 0.0
    high_priority: int = 0
    next_high_priority: int = 0
    high_priority: int = 0
    next_high_priority: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiBlendInterpolator:
        self = cls()
        if ctx.version >= pack_version(10, 1, 0, 112):
            self.flags = read_u8(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.array_size = read_u16(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.array_grow_by = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 110):
            self.array_size = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 112):
            self.weight_threshold = read_f32(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.interp_count = read_u8(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.single_index = read_u8(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.high_priority = read_i8(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.next_high_priority = read_i8(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.single_time = read_f32(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.high_weights_sum = read_f32(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.next_high_weights_sum = read_f32(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.high_ease_spinner = read_f32(stream)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            self.interp_array_items = [InterpBlendItem.read(stream, ctx) for _ in range(int(self.array_size))]
        if ctx.version <= pack_version(10, 1, 0, 111):
            self.interp_array_items = [InterpBlendItem.read(stream, ctx) for _ in range(int(self.array_size))]
        if ctx.version <= pack_version(10, 1, 0, 111):
            self.manager_controlled = read_bool(stream)
        if ctx.version <= pack_version(10, 1, 0, 111):
            self.weight_threshold = read_f32(stream)
        if ctx.version <= pack_version(10, 1, 0, 111):
            self.only_use_highest_weight = read_bool(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.interp_count = read_u16(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.single_index = read_u16(stream)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.interp_count = read_u8(stream)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.single_index = read_u8(stream)
        if (ctx.version >= pack_version(10, 1, 0, 108)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.single_interpolator = read_i32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 108)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.single_time = read_f32(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.high_priority = read_i32(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.next_high_priority = read_i32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.high_priority = read_i8(stream)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            self.next_high_priority = read_i8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 1, 0, 112):
            write_u8(stream, self.flags)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_u16(stream, self.array_size)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_u16(stream, self.array_grow_by)
        if ctx.version >= pack_version(10, 1, 0, 110):
            write_u8(stream, self.array_size)
        if ctx.version >= pack_version(10, 1, 0, 112):
            write_f32(stream, self.weight_threshold)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_u8(stream, self.interp_count)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_u8(stream, self.single_index)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_i8(stream, self.high_priority)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_i8(stream, self.next_high_priority)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_f32(stream, self.single_time)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_f32(stream, self.high_weights_sum)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_f32(stream, self.next_high_weights_sum)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            write_f32(stream, self.high_ease_spinner)
        if (
            (ctx.version >= pack_version(10, 1, 0, 112))
            and (
                False  # CODEGEN-TODO cond '!((Flags #BITAND# 1) != 0)'; unexpected operand '!'
            )
        ):
            for __v in self.interp_array_items:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 111):
            for __v in self.interp_array_items:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 111):
            write_bool(stream, self.manager_controlled)
        if ctx.version <= pack_version(10, 1, 0, 111):
            write_f32(stream, self.weight_threshold)
        if ctx.version <= pack_version(10, 1, 0, 111):
            write_bool(stream, self.only_use_highest_weight)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_u16(stream, self.interp_count)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_u16(stream, self.single_index)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_u8(stream, self.interp_count)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_u8(stream, self.single_index)
        if (ctx.version >= pack_version(10, 1, 0, 108)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_i32(stream, self.single_interpolator)
        if (ctx.version >= pack_version(10, 1, 0, 108)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_f32(stream, self.single_time)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_i32(stream, self.high_priority)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_i32(stream, self.next_high_priority)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_i8(stream, self.high_priority)
        if (ctx.version >= pack_version(10, 1, 0, 110)) and (ctx.version <= pack_version(10, 1, 0, 111)):
            write_i8(stream, self.next_high_priority)


@dataclass(slots=True)
class NiCollisionObject(Block):
    """This is the most common collision object found in NIF files. It acts as a real object that
        is visible and possibly (if the body allows for it) interactive. The node itself
        is simple, it only has three properties.
        For this type of collision object, bhkRigidBody or bhkRigidBodyT is generally used."""

    target: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiCollisionObject:
        self = cls()
        self.target = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.target)


@dataclass(slots=True)
class NiControllerManager(Block):
    """Controls animation sequences on a specific branch of the scene graph."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0
    cumulative: bool = False
    num_controller_sequences: int = 0
    controller_sequences: list[int] = field(default_factory=list)
    object_palette: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiControllerManager:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        self.cumulative = read_bool(stream)
        self.num_controller_sequences = read_u32(stream)
        self.controller_sequences = [read_i32(stream) for _ in range(int(self.num_controller_sequences))]
        self.object_palette = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)
        write_bool(stream, self.cumulative)
        write_u32(stream, self.num_controller_sequences)
        for __v in self.controller_sequences:
            write_i32(stream, __v)
        write_i32(stream, self.object_palette)


@dataclass(slots=True)
class NiControllerSequence(Block):
    """Root node in Gamebryo .kf files (version 10.0.1.0 and up)."""

    name: string | None = None
    accum_root_name: string | None = None
    text_keys: int = 0
    num_div2_ints: int = 0
    div2_ints: list[int] = field(default_factory=list)
    div2_ref: int = 0
    num_controlled_blocks: int = 0
    array_grow_by: int = 0
    controlled_blocks: list[ControlledBlock | None] = field(default_factory=list)
    weight: float = 0.0
    text_keys: int = 0
    cycle_type: int = 0
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    play_backwards: bool = False
    manager: int = 0
    accum_root_name: string | None = None
    accum_flags: int = 0
    string_palette: int = 0
    anim_notes: int = 0
    num_anim_note_arrays: int = 0
    anim_note_arrays: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiControllerSequence:
        self = cls()
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.accum_root_name = string.read(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.text_keys = read_i32(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.num_div2_ints = read_u32(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_ints = [read_i32(stream) for _ in range(int(self.num_div2_ints))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_ref = read_i32(stream)
        self.num_controlled_blocks = read_u32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.array_grow_by = read_u32(stream)
        self.controlled_blocks = [ControlledBlock.read(stream, ctx) for _ in range(int(self.num_controlled_blocks))]
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.weight = read_f32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.text_keys = read_i32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.cycle_type = read_u32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.frequency = read_f32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            self.phase = read_f32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.start_time = read_f32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.stop_time = read_f32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.version <= pack_version(10, 1, 0, 106)):
            self.play_backwards = read_bool(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.manager = read_i32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.accum_root_name = string.read(stream, ctx)
        if ctx.version >= pack_version(20, 3, 0, 8):
            self.accum_flags = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 113)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.string_palette = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 24) and (ctx.bs_version <= 28)):
            self.anim_notes = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.bs_version > 28):
            self.num_anim_note_arrays = read_u16(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.bs_version > 28):
            self.anim_note_arrays = [read_i32(stream) for _ in range(int(self.num_anim_note_arrays))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.accum_root_name.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            write_i32(stream, self.text_keys)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_u32(stream, self.num_div2_ints)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            for __v in self.div2_ints:
                write_i32(stream, __v)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_i32(stream, self.div2_ref)
        write_u32(stream, self.num_controlled_blocks)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_u32(stream, self.array_grow_by)
        for __v in self.controlled_blocks:
            __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_f32(stream, self.weight)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_i32(stream, self.text_keys)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_u32(stream, self.cycle_type)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_f32(stream, self.frequency)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            write_f32(stream, self.phase)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_f32(stream, self.start_time)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_f32(stream, self.stop_time)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.version <= pack_version(10, 1, 0, 106)):
            write_bool(stream, self.play_backwards)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_i32(stream, self.manager)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.accum_root_name.write(stream, ctx)
        if ctx.version >= pack_version(20, 3, 0, 8):
            write_u32(stream, self.accum_flags)
        if (ctx.version >= pack_version(10, 1, 0, 113)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_i32(stream, self.string_palette)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 24) and (ctx.bs_version <= 28)):
            write_i32(stream, self.anim_notes)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.bs_version > 28):
            write_u16(stream, self.num_anim_note_arrays)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.bs_version > 28):
            for __v in self.anim_note_arrays:
                write_i32(stream, __v)


@dataclass(slots=True)
class NiDefaultAVObjectPalette(Block):
    """NiAVObjectPalette implementation. Used to quickly look up objects by name."""

    scene: int = 0
    num_objs: int = 0
    objs: list[AVObject | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiDefaultAVObjectPalette:
        self = cls()
        self.scene = read_i32(stream)
        self.num_objs = read_u32(stream)
        self.objs = [AVObject.read(stream, ctx) for _ in range(int(self.num_objs))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.scene)
        write_u32(stream, self.num_objs)
        for __v in self.objs:
            __v.write(stream, ctx)


@dataclass(slots=True)
class NiDynamicEffect(Block):
    """Abstract base class for dynamic effects such as NiLights or projected texture effects."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    switch_state: bool = False
    num_affected_nodes: int = 0
    affected_nodes: list[int] = field(default_factory=list)
    affected_node_pointers: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    num_affected_nodes: int = 0
    affected_nodes: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiDynamicEffect:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and ((ctx.bs_version < 130)):
            self.switch_state = read_bool(stream)
        if ctx.version <= pack_version(4, 0, 0, 2):
            self.num_affected_nodes = read_u32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.affected_nodes = [read_i32(stream) for _ in range(int(self.num_affected_nodes))]
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 0, 0, 2)):
            self.affected_node_pointers = read_array_u32(stream, int(self.num_affected_nodes))
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((ctx.bs_version < 130)):
            self.num_affected_nodes = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((ctx.bs_version < 130)):
            self.affected_nodes = [read_i32(stream) for _ in range(int(self.num_affected_nodes))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and ((ctx.bs_version < 130)):
            write_bool(stream, self.switch_state)
        if ctx.version <= pack_version(4, 0, 0, 2):
            write_u32(stream, self.num_affected_nodes)
        if ctx.version <= pack_version(3, 3, 0, 13):
            for __v in self.affected_nodes:
                write_i32(stream, __v)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 0, 0, 2)):
            write_array_u32(stream, self.affected_node_pointers)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((ctx.bs_version < 130)):
            write_u32(stream, self.num_affected_nodes)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((ctx.bs_version < 130)):
            for __v in self.affected_nodes:
                write_i32(stream, __v)


@dataclass(slots=True)
class NiExtraData(Block):
    """A generic extra data object."""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiExtraData:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)


@dataclass(slots=True)
class NiGeometry(Block):
    """Describes a visible scene element with vertices like a mesh, a particle system, lines, etc.
            Bethesda 20.2.0.7 NIFs: NiGeometry was changed to BSGeometry.
            Most new blocks (e.g. BSTriShape) do not refer to NiGeometry except NiParticleSystem was changed to use BSGeometry.
            This causes massive inheritance problems so the rows below are doubled up to exclude NiParticleSystem for Bethesda Stream 100+
            and to add data exclusive to BSGeometry."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    data: int = 0
    data: int = 0
    skin_instance: int = 0
    skin_instance: int = 0
    material_data: MaterialData | None = None
    material_data: MaterialData | None = None
    shader_property: int = 0
    alpha_property: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiGeometry:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            self.bound_min_max = read_array_f32(stream, 6)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin = read_i32(stream)
        if (ctx.bs_version < 100):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.shader_property = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.alpha_property = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            write_array_f32(stream, self.bound_min_max)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin)
        if (ctx.bs_version < 100):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.shader_property)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.alpha_property)


@dataclass(slots=True)
class NiGeometryData(Block):
    """Mesh data: vertices, vertex normals, etc.
            Bethesda 20.2.0.7 NIFs: NiParticlesData no longer inherits from NiGeometryData and inherits NiObject directly.
            "Num Vertices" is renamed to "BS Max Vertices" for Bethesda 20.2 because Vertices, Normals, Tangents, Colors, and UV arrays
            do not have length for NiPSysData regardless of "Num" or booleans."""

    group_id: int = 0
    num_vertices: int = 0
    num_vertices: int = 0
    bs_max_vertices: int = 0
    keep_flags: int = 0
    compress_flags: int = 0
    has_vertices: bool = False
    vertices: list[Vector3 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    bs_data_flags: BSGeometryDataFlags | None = field(default_factory=BSGeometryDataFlags)
    material_crc: int = 0
    has_normals: bool = False
    normals: list[Vector3 | None] = field(default_factory=list)
    tangents: list[Vector3 | None] = field(default_factory=list)
    bitangents: list[Vector3 | None] = field(default_factory=list)
    has_div2_floats: bool = False
    div2_floats: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    bounding_sphere: NiBound | None = None
    has_vertex_colors: bool = False
    vertex_colors: list[Color4 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    has_uv: bool = False
    uv_sets: list[Any] = field(default_factory=list)
    consistency_flags: int = 0
    additional_data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiGeometryData:
        self = cls()
        if ctx.version >= pack_version(10, 1, 0, 114):
            self.group_id = read_i32(stream)
        self.num_vertices = read_u16(stream)
        if (ctx.bs_version < 34):
            self.num_vertices = read_u16(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            self.bs_max_vertices = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.keep_flags = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.compress_flags = read_u8(stream)
        self.has_vertices = read_bool(stream)
        if self.has_vertices:
            self.vertices = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags = BSGeometryDataFlags.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.material_crc = read_u32(stream)
        self.has_normals = read_bool(stream)
        if self.has_normals:
            self.normals = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.tangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.bitangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.has_div2_floats = read_bool(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            self.div2_floats = read_array_f32(stream, int(self.num_vertices))
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.has_vertex_colors = read_bool(stream)
        if self.has_vertex_colors:
            self.vertex_colors = [Color4.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            self.has_uv = read_bool(stream)
        self.uv_sets = [[TexCoord.read(stream, ctx) for _ in range(int(self.num_vertices))] for _ in range(int(((self.data_flags & 63) | (self.bs_data_flags & 1))))]
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.consistency_flags = read_u16(stream)
        if ctx.version >= pack_version(20, 0, 0, 4):
            self.additional_data = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 1, 0, 114):
            write_i32(stream, self.group_id)
        write_u16(stream, self.num_vertices)
        if (ctx.bs_version < 34):
            write_u16(stream, self.num_vertices)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            write_u16(stream, self.bs_max_vertices)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.keep_flags)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.compress_flags)
        write_bool(stream, self.has_vertices)
        if self.has_vertices:
            for __v in self.vertices:
                __v.write(stream, ctx)
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags.write(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_u32(stream, self.material_crc)
        write_bool(stream, self.has_normals)
        if self.has_normals:
            for __v in self.normals:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.tangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.bitangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_bool(stream, self.has_div2_floats)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            write_array_f32(stream, self.div2_floats)
        self.bounding_sphere.write(stream, ctx)
        write_bool(stream, self.has_vertex_colors)
        if self.has_vertex_colors:
            for __v in self.vertex_colors:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags.write(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            write_bool(stream, self.has_uv)
        for __row in self.uv_sets:
            for __v in __row:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u16(stream, self.consistency_flags)
        if ctx.version >= pack_version(20, 0, 0, 4):
            write_i32(stream, self.additional_data)


@dataclass(slots=True)
class NiImage(Block):
    """LEGACY (pre-10.1)"""

    use_external: int = 0
    file_name: FilePath | None = None
    image_data: int = 0
    unknown_int: int = 0
    unknown_float: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiImage:
        self = cls()
        self.use_external = read_u8(stream)
        if self.use_external != 0:
            self.file_name = FilePath.read(stream, ctx)
        if self.use_external == 0:
            self.image_data = read_i32(stream)
        self.unknown_int = read_u32(stream)
        if ctx.version >= pack_version(3, 1):
            self.unknown_float = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.use_external)
        if self.use_external != 0:
            self.file_name.write(stream, ctx)
        if self.use_external == 0:
            write_i32(stream, self.image_data)
        write_u32(stream, self.unknown_int)
        if ctx.version >= pack_version(3, 1):
            write_f32(stream, self.unknown_float)


@dataclass(slots=True)
class NiIntegerExtraData(Block):
    """Extra integer data."""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0
    integer_data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiIntegerExtraData:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        self.integer_data = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)
        write_u32(stream, self.integer_data)


@dataclass(slots=True)
class NiInterpController(Block):
    """Abstract base class for all NiTimeController objects using NiInterpolator objects to animate their target objects."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0
    manager_controlled: bool = False

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiInterpController:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            self.manager_controlled = read_bool(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            write_bool(stream, self.manager_controlled)


@dataclass(slots=True)
class NiInterpolator(Block):
    """Abstract base class for all interpolators of bool, float, NiQuaternion, NiPoint3, NiColorA, and NiQuatTransform data."""

    pass


@dataclass(slots=True)
class NiKeyBasedInterpolator(Block):
    """Abstract base class for interpolators that use NiAnimationKeys (Key, KeyGrp) for interpolation."""

    pass


@dataclass(slots=True)
class NiKeyframeController(Block):
    """DEPRECATED (10.2), RENAMED (10.2) to NiTransformController
        A time controller object for animation key frames."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0
    manager_controlled: bool = False
    interpolator: int = 0
    data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiKeyframeController:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            self.manager_controlled = read_bool(stream)
        if ctx.version >= pack_version(10, 1, 0, 104):
            self.interpolator = read_i32(stream)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.data = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            write_bool(stream, self.manager_controlled)
        if ctx.version >= pack_version(10, 1, 0, 104):
            write_i32(stream, self.interpolator)
        if ctx.version <= pack_version(10, 1, 0, 103):
            write_i32(stream, self.data)


@dataclass(slots=True)
class NiKeyframeData(Block):
    """DEPRECATED (10.2), RENAMED (10.2) to NiTransformData.
        Wrapper for transformation animation keys."""

    num_rotation_keys: int = 0
    rotation_type: int = 0
    quaternion_keys: list[QuatKey | None] = field(default_factory=list)
    order: float = 0.0
    xyz_rotations: list[KeyGroup | None] = field(default_factory=list)
    translations: KeyGroup | None = None
    scales: KeyGroup | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiKeyframeData:
        self = cls()
        self.num_rotation_keys = read_u32(stream)
        if self.num_rotation_keys != 0:
            self.rotation_type = read_u32(stream)
        if self.rotation_type != 4:
            ctx.push_arg(self.rotation_type)
            try:
                self.quaternion_keys = [QuatKey.read(stream, ctx) for _ in range(int(self.num_rotation_keys))]
            finally:
                ctx.pop_arg()
        if (ctx.version <= pack_version(10, 1, 0, 0)) and (self.rotation_type == 4):
            self.order = read_f32(stream)
        if self.rotation_type == 4:
            self.xyz_rotations = [KeyGroup.read(stream, ctx) for _ in range(3)]
        self.translations = KeyGroup.read(stream, ctx)
        self.scales = KeyGroup.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_rotation_keys)
        if self.num_rotation_keys != 0:
            write_u32(stream, self.rotation_type)
        if self.rotation_type != 4:
            ctx.push_arg(self.rotation_type)
            try:
                for __v in self.quaternion_keys:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if (ctx.version <= pack_version(10, 1, 0, 0)) and (self.rotation_type == 4):
            write_f32(stream, self.order)
        if self.rotation_type == 4:
            for __v in self.xyz_rotations:
                __v.write(stream, ctx)
        self.translations.write(stream, ctx)
        self.scales.write(stream, ctx)


@dataclass(slots=True)
class NiLODData(Block):
    """Abstract class used for different types of LOD selections."""

    pass


@dataclass(slots=True)
class NiLODNode(Block):
    """Level of detail selector. Links to different levels of detail of the same model, used to switch a geometry at a specified distance."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    num_children: int = 0
    children: list[int] = field(default_factory=list)
    num_effects: int = 0
    effects: list[int] = field(default_factory=list)
    switch_node_flags: int = 0
    index: int = 0
    lod_center: Vector3 | None = None
    num_lod_levels: int = 0
    lod_levels: list[LODRange | None] = field(default_factory=list)
    lod_level_data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiLODNode:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.num_children = read_u32(stream)
        self.children = [read_i32(stream) for _ in range(int(self.num_children))]
        if (ctx.bs_version < 130):
            self.num_effects = read_u32(stream)
        if (ctx.bs_version < 130):
            self.effects = [read_i32(stream) for _ in range(int(self.num_effects))]
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.switch_node_flags = read_u16(stream)
        self.index = read_u32(stream)
        if (ctx.version >= pack_version(4, 0, 0, 2)) and (ctx.version <= pack_version(10, 0, 1, 0)):
            self.lod_center = Vector3.read(stream, ctx)
        if ctx.version <= pack_version(10, 0, 1, 0):
            self.num_lod_levels = read_u32(stream)
        if ctx.version <= pack_version(10, 0, 1, 0):
            self.lod_levels = [LODRange.read(stream, ctx) for _ in range(int(self.num_lod_levels))]
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.lod_level_data = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        write_u32(stream, self.num_children)
        for __v in self.children:
            write_i32(stream, __v)
        if (ctx.bs_version < 130):
            write_u32(stream, self.num_effects)
        if (ctx.bs_version < 130):
            for __v in self.effects:
                write_i32(stream, __v)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u16(stream, self.switch_node_flags)
        write_u32(stream, self.index)
        if (ctx.version >= pack_version(4, 0, 0, 2)) and (ctx.version <= pack_version(10, 0, 1, 0)):
            self.lod_center.write(stream, ctx)
        if ctx.version <= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_lod_levels)
        if ctx.version <= pack_version(10, 0, 1, 0):
            for __v in self.lod_levels:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_i32(stream, self.lod_level_data)


@dataclass(slots=True)
class NiMaterialProperty(Block):
    """Describes the surface properties of an object e.g. translucency, ambient color, diffuse color, emissive color, and specular color."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    ambient_color: Color3 | None = None
    diffuse_color: Color3 | None = None
    specular_color: Color3 | None = None
    emissive_color: Color3 | None = None
    glossiness: float = 0.0
    alpha: float = 0.0
    emissive_mult: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiMaterialProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(10, 0, 1, 2)):
            self.flags = read_u16(stream)
        if ctx.bs_version < 26:
            self.ambient_color = Color3.read(stream, ctx)
        if ctx.bs_version < 26:
            self.diffuse_color = Color3.read(stream, ctx)
        self.specular_color = Color3.read(stream, ctx)
        self.emissive_color = Color3.read(stream, ctx)
        self.glossiness = read_f32(stream)
        self.alpha = read_f32(stream)
        if ctx.bs_version > 21:
            self.emissive_mult = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(10, 0, 1, 2)):
            write_u16(stream, self.flags)
        if ctx.bs_version < 26:
            self.ambient_color.write(stream, ctx)
        if ctx.bs_version < 26:
            self.diffuse_color.write(stream, ctx)
        self.specular_color.write(stream, ctx)
        self.emissive_color.write(stream, ctx)
        write_f32(stream, self.glossiness)
        write_f32(stream, self.alpha)
        if ctx.bs_version > 21:
            write_f32(stream, self.emissive_mult)


@dataclass(slots=True)
class NiNode(Block):
    """Generic node object for grouping."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    num_children: int = 0
    children: list[int] = field(default_factory=list)
    num_effects: int = 0
    effects: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiNode:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.num_children = read_u32(stream)
        self.children = [read_i32(stream) for _ in range(int(self.num_children))]
        if (ctx.bs_version < 130):
            self.num_effects = read_u32(stream)
        if (ctx.bs_version < 130):
            self.effects = [read_i32(stream) for _ in range(int(self.num_effects))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        write_u32(stream, self.num_children)
        for __v in self.children:
            write_i32(stream, __v)
        if (ctx.bs_version < 130):
            write_u32(stream, self.num_effects)
        if (ctx.bs_version < 130):
            for __v in self.effects:
                write_i32(stream, __v)


@dataclass(slots=True)
class NiObject(Block):
    """Abstract object type."""

    pass


@dataclass(slots=True)
class NiObjectNET(Block):
    """Abstract base class for NiObjects that support names, extra data, and time controllers."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiObjectNET:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)


@dataclass(slots=True)
class NiPixelFormat(Block):
    """NiPixelFormat is not the parent to NiPixelData/NiPersistentSrcTextureRendererData,
        but actually a member class loaded at the top of each. The two classes are not related.
        However, faking this inheritance is useful for several things."""

    pixel_format: int = 0
    red_mask: int = 0
    green_mask: int = 0
    blue_mask: int = 0
    alpha_mask: int = 0
    bits_per_pixel: int = 0
    old_fast_compare: list[int] = field(default_factory=list)
    tiling: int = 0
    bits_per_pixel: int = 0
    renderer_hint: int = 0
    extra_data: int = 0
    flags: int = 0
    tiling: int = 0
    srgb_space: bool = False
    channels: list[PixelFormatComponent | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiPixelFormat:
        self = cls()
        self.pixel_format = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.red_mask = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.green_mask = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.blue_mask = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.alpha_mask = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.bits_per_pixel = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.old_fast_compare = [read_u8(stream) for _ in range(8)]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            self.tiling = read_u32(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.bits_per_pixel = read_u8(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.renderer_hint = read_u32(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.extra_data = read_u32(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.flags = read_u8(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.tiling = read_u32(stream)
        if ctx.version >= pack_version(20, 3, 0, 4):
            self.srgb_space = read_bool(stream)
        if ctx.version >= pack_version(10, 4, 0, 2):
            self.channels = [PixelFormatComponent.read(stream, ctx) for _ in range(4)]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.pixel_format)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_u32(stream, self.red_mask)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_u32(stream, self.green_mask)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_u32(stream, self.blue_mask)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_u32(stream, self.alpha_mask)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_u32(stream, self.bits_per_pixel)
        if ctx.version <= pack_version(10, 4, 0, 1):
            for __v in self.old_fast_compare:
                write_u8(stream, __v)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            write_u32(stream, self.tiling)
        if ctx.version >= pack_version(10, 4, 0, 2):
            write_u8(stream, self.bits_per_pixel)
        if ctx.version >= pack_version(10, 4, 0, 2):
            write_u32(stream, self.renderer_hint)
        if ctx.version >= pack_version(10, 4, 0, 2):
            write_u32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 4, 0, 2):
            write_u8(stream, self.flags)
        if ctx.version >= pack_version(10, 4, 0, 2):
            write_u32(stream, self.tiling)
        if ctx.version >= pack_version(20, 3, 0, 4):
            write_bool(stream, self.srgb_space)
        if ctx.version >= pack_version(10, 4, 0, 2):
            for __v in self.channels:
                __v.write(stream, ctx)


@dataclass(slots=True)
class NiProperty(Block):
    """Abstract base class representing all rendering properties. Subclasses are attached to NiAVObjects to control their rendering."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)


@dataclass(slots=True)
class NiRawImageData(Block):
    """LEGACY (pre-10.1)
        Raw image data."""

    width: int = 0
    height: int = 0
    image_type: int = 0
    rgb_image_data: list[Any] = field(default_factory=list)
    rgba_image_data: list[Any] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiRawImageData:
        self = cls()
        self.width = read_u32(stream)
        self.height = read_u32(stream)
        self.image_type = read_u32(stream)
        if self.image_type == 1:
            self.rgb_image_data = [[ByteColor3.read(stream, ctx) for _ in range(int(self.height))] for _ in range(int(self.width))]
        if self.image_type == 2:
            self.rgba_image_data = [[ByteColor4.read(stream, ctx) for _ in range(int(self.height))] for _ in range(int(self.width))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.width)
        write_u32(stream, self.height)
        write_u32(stream, self.image_type)
        if self.image_type == 1:
            for __row in self.rgb_image_data:
                for __v in __row:
                    __v.write(stream, ctx)
        if self.image_type == 2:
            for __row in self.rgba_image_data:
                for __v in __row:
                    __v.write(stream, ctx)


@dataclass(slots=True)
class NiSequence(Block):
    """Root node in NetImmerse .kf files (until version 10.0)."""

    name: string | None = None
    accum_root_name: string | None = None
    text_keys: int = 0
    num_div2_ints: int = 0
    div2_ints: list[int] = field(default_factory=list)
    div2_ref: int = 0
    num_controlled_blocks: int = 0
    array_grow_by: int = 0
    controlled_blocks: list[ControlledBlock | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSequence:
        self = cls()
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.accum_root_name = string.read(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.text_keys = read_i32(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.num_div2_ints = read_u32(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_ints = [read_i32(stream) for _ in range(int(self.num_div2_ints))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_ref = read_i32(stream)
        self.num_controlled_blocks = read_u32(stream)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.array_grow_by = read_u32(stream)
        self.controlled_blocks = [ControlledBlock.read(stream, ctx) for _ in range(int(self.num_controlled_blocks))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.accum_root_name.write(stream, ctx)
        if ctx.version <= pack_version(10, 1, 0, 103):
            write_i32(stream, self.text_keys)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_u32(stream, self.num_div2_ints)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            for __v in self.div2_ints:
                write_i32(stream, __v)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_i32(stream, self.div2_ref)
        write_u32(stream, self.num_controlled_blocks)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_u32(stream, self.array_grow_by)
        for __v in self.controlled_blocks:
            __v.write(stream, ctx)


@dataclass(slots=True)
class NiShadeProperty(Block):
    """Determines whether flat shading or smooth shading is used on a shape."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiShadeProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if (ctx.bs_version <= 34):
            self.flags = read_u16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if (ctx.bs_version <= 34):
            write_u16(stream, self.flags)


@dataclass(slots=True)
class NiSingleInterpController(Block):
    """Uses a single NiInterpolator to animate its target value."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0
    manager_controlled: bool = False
    interpolator: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSingleInterpController:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            self.manager_controlled = read_bool(stream)
        if ctx.version >= pack_version(10, 1, 0, 104):
            self.interpolator = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            write_bool(stream, self.manager_controlled)
        if ctx.version >= pack_version(10, 1, 0, 104):
            write_i32(stream, self.interpolator)


@dataclass(slots=True)
class NiSkinData(Block):
    """Skinning data."""

    skin_transform: NiTransform | None = None
    num_bones: int = 0
    skin_partition: int = 0
    has_vertex_weights: bool = False
    bone_list: list[BoneData | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSkinData:
        self = cls()
        self.skin_transform = NiTransform.read(stream, ctx)
        self.num_bones = read_u32(stream)
        if (ctx.version >= pack_version(4, 0, 0, 2)) and (ctx.version <= pack_version(10, 1, 0, 0)):
            self.skin_partition = read_i32(stream)
        if ctx.version >= pack_version(4, 2, 1, 0):
            self.has_vertex_weights = read_bool(stream)
        ctx.push_arg(self.has_vertex_weights)
        try:
            self.bone_list = [BoneData.read(stream, ctx) for _ in range(int(self.num_bones))]
        finally:
            ctx.pop_arg()
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.skin_transform.write(stream, ctx)
        write_u32(stream, self.num_bones)
        if (ctx.version >= pack_version(4, 0, 0, 2)) and (ctx.version <= pack_version(10, 1, 0, 0)):
            write_i32(stream, self.skin_partition)
        if ctx.version >= pack_version(4, 2, 1, 0):
            write_bool(stream, self.has_vertex_weights)
        ctx.push_arg(self.has_vertex_weights)
        try:
            for __v in self.bone_list:
                __v.write(stream, ctx)
        finally:
            ctx.pop_arg()


@dataclass(slots=True)
class NiSkinInstance(Block):
    """Skinning instance."""

    data: int = 0
    skin_partition: int = 0
    skeleton_root: int = 0
    num_bones: int = 0
    bones: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSkinInstance:
        self = cls()
        self.data = read_i32(stream)
        if ctx.version >= pack_version(10, 1, 0, 101):
            self.skin_partition = read_i32(stream)
        self.skeleton_root = read_i32(stream)
        self.num_bones = read_u32(stream)
        self.bones = [read_i32(stream) for _ in range(int(self.num_bones))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.data)
        if ctx.version >= pack_version(10, 1, 0, 101):
            write_i32(stream, self.skin_partition)
        write_i32(stream, self.skeleton_root)
        write_u32(stream, self.num_bones)
        for __v in self.bones:
            write_i32(stream, __v)


@dataclass(slots=True)
class NiSkinPartition(Block):
    """Skinning data, optimized for hardware skinning. The mesh is partitioned in submeshes such that each vertex of a submesh is influenced only by a limited and fixed number of bones."""

    num_partitions: int = 0
    data_size: int = 0
    vertex_size: int = 0
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    vertex_data: list[BSVertexDataSSE | None] = field(default_factory=list)
    partitions: list[SkinPartition | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSkinPartition:
        self = cls()
        self.num_partitions = read_u32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.data_size = read_u32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.vertex_size = read_u32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                self.vertex_data = [BSVertexDataSSE.read(stream, ctx) for _ in range(int(self.data_size / self.vertex_size))]
            finally:
                ctx.pop_arg()
        self.partitions = [SkinPartition.read(stream, ctx) for _ in range(int(self.num_partitions))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_partitions)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            write_u32(stream, self.data_size)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            write_u32(stream, self.vertex_size)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.vertex_desc.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)) and (self.data_size > 0):
            ctx.push_arg(self.vertex_desc >> 44)
            try:
                for __v in self.vertex_data:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        for __v in self.partitions:
            __v.write(stream, ctx)


@dataclass(slots=True)
class NiSourceTexture(Block):
    """Describes texture source and properties."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    use_external: int = 0
    use_internal: int = 0
    file_name: FilePath | None = None
    file_name: FilePath | None = None
    pixel_data: int = 0
    pixel_data: int = 0
    pixel_data: int = 0
    format_prefs: FormatPrefs | None = None
    is_static: int = 0
    direct_render: bool = False
    persist_render_data: bool = False

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSourceTexture:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        self.use_external = read_u8(stream)
        if (ctx.version <= pack_version(10, 0, 1, 3)) and (self.use_external == 0):
            self.use_internal = read_u8(stream)
        if self.use_external == 1:
            self.file_name = FilePath.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.use_external == 0):
            self.file_name = FilePath.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.use_external == 1):
            self.pixel_data = read_i32(stream)
        if (ctx.version <= pack_version(10, 0, 1, 3)) and (self.use_external == 0 and self.use_internal == 1):
            self.pixel_data = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 4)) and (self.use_external == 0):
            self.pixel_data = read_i32(stream)
        self.format_prefs = FormatPrefs.read(stream, ctx)
        self.is_static = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 103):
            self.direct_render = read_bool(stream)
        if ctx.version >= pack_version(20, 2, 0, 4):
            self.persist_render_data = read_bool(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        write_u8(stream, self.use_external)
        if (ctx.version <= pack_version(10, 0, 1, 3)) and (self.use_external == 0):
            write_u8(stream, self.use_internal)
        if self.use_external == 1:
            self.file_name.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.use_external == 0):
            self.file_name.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.use_external == 1):
            write_i32(stream, self.pixel_data)
        if (ctx.version <= pack_version(10, 0, 1, 3)) and (self.use_external == 0 and self.use_internal == 1):
            write_i32(stream, self.pixel_data)
        if (ctx.version >= pack_version(10, 0, 1, 4)) and (self.use_external == 0):
            write_i32(stream, self.pixel_data)
        self.format_prefs.write(stream, ctx)
        write_u8(stream, self.is_static)
        if ctx.version >= pack_version(10, 1, 0, 103):
            write_bool(stream, self.direct_render)
        if ctx.version >= pack_version(20, 2, 0, 4):
            write_bool(stream, self.persist_render_data)


@dataclass(slots=True)
class NiStringExtraData(Block):
    """Extra data in the form of text.
        Used in various official or user-defined ways, e.g. preventing optimization on objects ("NiOptimizeKeep", "sgoKeep")."""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0
    string_data: string | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiStringExtraData:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        if ctx.version >= pack_version(4, 0, 0, 0):
            self.string_data = string.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)
        if ctx.version >= pack_version(4, 0, 0, 0):
            self.string_data.write(stream, ctx)


@dataclass(slots=True)
class NiStringPalette(Block):
    """List of 0x00-seperated strings, which are names of controlled objects and controller types. Used in .kf files in conjunction with NiControllerSequence."""

    palette: StringPalette | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiStringPalette:
        self = cls()
        self.palette = StringPalette.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.palette.write(stream, ctx)


@dataclass(slots=True)
class NiSwitchNode(Block):
    """Represents groups of multiple scenegraph subtrees, only one of which (the "active child") is drawn at any given time."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    num_children: int = 0
    children: list[int] = field(default_factory=list)
    num_effects: int = 0
    effects: list[int] = field(default_factory=list)
    switch_node_flags: int = 0
    index: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiSwitchNode:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        self.num_children = read_u32(stream)
        self.children = [read_i32(stream) for _ in range(int(self.num_children))]
        if (ctx.bs_version < 130):
            self.num_effects = read_u32(stream)
        if (ctx.bs_version < 130):
            self.effects = [read_i32(stream) for _ in range(int(self.num_effects))]
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.switch_node_flags = read_u16(stream)
        self.index = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        write_u32(stream, self.num_children)
        for __v in self.children:
            write_i32(stream, __v)
        if (ctx.bs_version < 130):
            write_u32(stream, self.num_effects)
        if (ctx.bs_version < 130):
            for __v in self.effects:
                write_i32(stream, __v)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u16(stream, self.switch_node_flags)
        write_u32(stream, self.index)


@dataclass(slots=True)
class NiTextKeyExtraData(Block):
    """Extra data that holds an array of NiTextKey objects for use in animation sequences."""

    name: string | None = None
    next_extra_data: int = 0
    extra_data: ByteArray | None = None
    num_bytes: int = 0
    num_text_keys: int = 0
    text_keys: list[Key | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTextKeyExtraData:
        self = cls()
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.next_extra_data = read_i32(stream)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data = ByteArray.read(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.num_bytes = read_u32(stream)
        self.num_text_keys = read_u32(stream)
        ctx.push_arg(1)
        try:
            self.text_keys = [Key.read(stream, ctx) for _ in range(int(self.num_text_keys))]
        finally:
            ctx.pop_arg()
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.name.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            write_i32(stream, self.next_extra_data)
        if ctx.version <= pack_version(3, 3, 0, 13):
            self.extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(4, 0, 0, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_u32(stream, self.num_bytes)
        write_u32(stream, self.num_text_keys)
        ctx.push_arg(1)
        try:
            for __v in self.text_keys:
                __v.write(stream, ctx)
        finally:
            ctx.pop_arg()


@dataclass(slots=True)
class NiTexture(Block):
    """A texture."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTexture:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)


@dataclass(slots=True)
class NiTexturingProperty(Block):
    """Describes how a fragment shader should be configured for a given piece of geometry."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: TexturingFlags | None = field(default_factory=TexturingFlags)
    apply_mode: int = 0
    texture_count: int = 0
    has_base_texture: bool = False
    base_texture: TexDesc | None = None
    has_dark_texture: bool = False
    dark_texture: TexDesc | None = None
    has_detail_texture: bool = False
    detail_texture: TexDesc | None = None
    has_gloss_texture: bool = False
    gloss_texture: TexDesc | None = None
    has_glow_texture: bool = False
    glow_texture: TexDesc | None = None
    has_bump_map_texture: bool = False
    bump_map_texture: TexDesc | None = None
    bump_map_luma_scale: float = 0.0
    bump_map_luma_offset: float = 0.0
    bump_map_matrix: Matrix22 | None = None
    has_normal_texture: bool = False
    normal_texture: TexDesc | None = None
    has_parallax_texture: bool = False
    parallax_texture: TexDesc | None = None
    parallax_offset: float = 0.0
    has_decal_0_texture: bool = False
    has_decal_0_texture: bool = False
    decal_0_texture: TexDesc | None = None
    has_decal_1_texture: bool = False
    has_decal_1_texture: bool = False
    decal_1_texture: TexDesc | None = None
    has_decal_2_texture: bool = False
    has_decal_2_texture: bool = False
    decal_2_texture: TexDesc | None = None
    has_decal_3_texture: bool = False
    has_decal_3_texture: bool = False
    decal_3_texture: TexDesc | None = None
    num_shader_textures: int = 0
    shader_textures: list[ShaderTexDesc | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTexturingProperty:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.version <= pack_version(10, 0, 1, 2):
            self.flags = read_u16(stream)
        if ctx.version >= pack_version(20, 1, 0, 2):
            self.flags = TexturingFlags.read(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (ctx.version <= pack_version(20, 1, 0, 1)):
            self.apply_mode = read_u32(stream)
        self.texture_count = read_u32(stream)
        self.has_base_texture = read_bool(stream)
        if self.has_base_texture:
            self.base_texture = TexDesc.read(stream, ctx)
        self.has_dark_texture = read_bool(stream)
        if self.has_dark_texture:
            self.dark_texture = TexDesc.read(stream, ctx)
        self.has_detail_texture = read_bool(stream)
        if self.has_detail_texture:
            self.detail_texture = TexDesc.read(stream, ctx)
        self.has_gloss_texture = read_bool(stream)
        if self.has_gloss_texture:
            self.gloss_texture = TexDesc.read(stream, ctx)
        self.has_glow_texture = read_bool(stream)
        if self.has_glow_texture:
            self.glow_texture = TexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.texture_count > 5):
            self.has_bump_map_texture = read_bool(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_texture = TexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_luma_scale = read_f32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_luma_offset = read_f32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_matrix = Matrix22.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 6):
            self.has_normal_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_normal_texture):
            self.normal_texture = TexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 7):
            self.has_parallax_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_parallax_texture):
            self.parallax_texture = TexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_parallax_texture):
            self.parallax_offset = read_f32(stream)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 6):
            self.has_decal_0_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 8):
            self.has_decal_0_texture = read_bool(stream)
        if self.has_decal_0_texture:
            self.decal_0_texture = TexDesc.read(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 7):
            self.has_decal_1_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 9):
            self.has_decal_1_texture = read_bool(stream)
        if self.has_decal_1_texture:
            self.decal_1_texture = TexDesc.read(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 8):
            self.has_decal_2_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 10):
            self.has_decal_2_texture = read_bool(stream)
        if self.has_decal_2_texture:
            self.decal_2_texture = TexDesc.read(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 9):
            self.has_decal_3_texture = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 11):
            self.has_decal_3_texture = read_bool(stream)
        if self.has_decal_3_texture:
            self.decal_3_texture = TexDesc.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_shader_textures = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.shader_textures = [ShaderTexDesc.read(stream, ctx) for _ in range(int(self.num_shader_textures))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.version <= pack_version(10, 0, 1, 2):
            write_u16(stream, self.flags)
        if ctx.version >= pack_version(20, 1, 0, 2):
            self.flags.write(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (ctx.version <= pack_version(20, 1, 0, 1)):
            write_u32(stream, self.apply_mode)
        write_u32(stream, self.texture_count)
        write_bool(stream, self.has_base_texture)
        if self.has_base_texture:
            self.base_texture.write(stream, ctx)
        write_bool(stream, self.has_dark_texture)
        if self.has_dark_texture:
            self.dark_texture.write(stream, ctx)
        write_bool(stream, self.has_detail_texture)
        if self.has_detail_texture:
            self.detail_texture.write(stream, ctx)
        write_bool(stream, self.has_gloss_texture)
        if self.has_gloss_texture:
            self.gloss_texture.write(stream, ctx)
        write_bool(stream, self.has_glow_texture)
        if self.has_glow_texture:
            self.glow_texture.write(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.texture_count > 5):
            write_bool(stream, self.has_bump_map_texture)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_texture.write(stream, ctx)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            write_f32(stream, self.bump_map_luma_scale)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            write_f32(stream, self.bump_map_luma_offset)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and (self.has_bump_map_texture):
            self.bump_map_matrix.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 6):
            write_bool(stream, self.has_normal_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_normal_texture):
            self.normal_texture.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 7):
            write_bool(stream, self.has_parallax_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_parallax_texture):
            self.parallax_texture.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.has_parallax_texture):
            write_f32(stream, self.parallax_offset)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 6):
            write_bool(stream, self.has_decal_0_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 8):
            write_bool(stream, self.has_decal_0_texture)
        if self.has_decal_0_texture:
            self.decal_0_texture.write(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 7):
            write_bool(stream, self.has_decal_1_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 9):
            write_bool(stream, self.has_decal_1_texture)
        if self.has_decal_1_texture:
            self.decal_1_texture.write(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 8):
            write_bool(stream, self.has_decal_2_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 10):
            write_bool(stream, self.has_decal_2_texture)
        if self.has_decal_2_texture:
            self.decal_2_texture.write(stream, ctx)
        if (ctx.version <= pack_version(20, 2, 0, 4)) and (self.texture_count > 9):
            write_bool(stream, self.has_decal_3_texture)
        if (ctx.version >= pack_version(20, 2, 0, 5)) and (self.texture_count > 11):
            write_bool(stream, self.has_decal_3_texture)
        if self.has_decal_3_texture:
            self.decal_3_texture.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_shader_textures)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.shader_textures:
                __v.write(stream, ctx)


@dataclass(slots=True)
class NiTimeController(Block):
    """Abstract base class that provides the base timing and update functionality for all the Gamebryo animation controllers."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTimeController:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)


@dataclass(slots=True)
class NiTransformController(Block):
    """NiTransformController replaces NiKeyframeController."""

    next_controller: int = 0
    flags: TimeControllerFlags | None = field(default_factory=TimeControllerFlags)
    frequency: float = 0.0
    phase: float = 0.0
    start_time: float = 0.0
    stop_time: float = 0.0
    target: int = 0
    unknown_integer: int = 0
    manager_controlled: bool = False
    interpolator: int = 0
    data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTransformController:
        self = cls()
        self.next_controller = read_i32(stream)
        self.flags = TimeControllerFlags.read(stream, ctx)
        self.frequency = read_f32(stream)
        self.phase = read_f32(stream)
        self.start_time = read_f32(stream)
        self.stop_time = read_f32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.target = read_i32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_integer = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            self.manager_controlled = read_bool(stream)
        if ctx.version >= pack_version(10, 1, 0, 104):
            self.interpolator = read_i32(stream)
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.data = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.next_controller)
        self.flags.write(stream, ctx)
        write_f32(stream, self.frequency)
        write_f32(stream, self.phase)
        write_f32(stream, self.start_time)
        write_f32(stream, self.stop_time)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.target)
        if ctx.version <= pack_version(3, 1):
            write_u32(stream, self.unknown_integer)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 108)):
            write_bool(stream, self.manager_controlled)
        if ctx.version >= pack_version(10, 1, 0, 104):
            write_i32(stream, self.interpolator)
        if ctx.version <= pack_version(10, 1, 0, 103):
            write_i32(stream, self.data)


@dataclass(slots=True)
class NiTransformData(Block):
    """Wrapper for transformation animation keys."""

    num_rotation_keys: int = 0
    rotation_type: int = 0
    quaternion_keys: list[QuatKey | None] = field(default_factory=list)
    order: float = 0.0
    xyz_rotations: list[KeyGroup | None] = field(default_factory=list)
    translations: KeyGroup | None = None
    scales: KeyGroup | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTransformData:
        self = cls()
        self.num_rotation_keys = read_u32(stream)
        if self.num_rotation_keys != 0:
            self.rotation_type = read_u32(stream)
        if self.rotation_type != 4:
            ctx.push_arg(self.rotation_type)
            try:
                self.quaternion_keys = [QuatKey.read(stream, ctx) for _ in range(int(self.num_rotation_keys))]
            finally:
                ctx.pop_arg()
        if (ctx.version <= pack_version(10, 1, 0, 0)) and (self.rotation_type == 4):
            self.order = read_f32(stream)
        if self.rotation_type == 4:
            self.xyz_rotations = [KeyGroup.read(stream, ctx) for _ in range(3)]
        self.translations = KeyGroup.read(stream, ctx)
        self.scales = KeyGroup.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_rotation_keys)
        if self.num_rotation_keys != 0:
            write_u32(stream, self.rotation_type)
        if self.rotation_type != 4:
            ctx.push_arg(self.rotation_type)
            try:
                for __v in self.quaternion_keys:
                    __v.write(stream, ctx)
            finally:
                ctx.pop_arg()
        if (ctx.version <= pack_version(10, 1, 0, 0)) and (self.rotation_type == 4):
            write_f32(stream, self.order)
        if self.rotation_type == 4:
            for __v in self.xyz_rotations:
                __v.write(stream, ctx)
        self.translations.write(stream, ctx)
        self.scales.write(stream, ctx)


@dataclass(slots=True)
class NiTransformInterpolator(Block):
    """An interpolator for transform keyframes."""

    transform: NiQuatTransform | None = None
    data: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTransformInterpolator:
        self = cls()
        self.transform = NiQuatTransform.read(stream, ctx)
        self.data = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.transform.write(stream, ctx)
        write_i32(stream, self.data)


@dataclass(slots=True)
class NiTriBasedGeom(Block):
    """Describes a mesh, built from triangles."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    data: int = 0
    data: int = 0
    skin_instance: int = 0
    skin_instance: int = 0
    material_data: MaterialData | None = None
    material_data: MaterialData | None = None
    shader_property: int = 0
    alpha_property: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriBasedGeom:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            self.bound_min_max = read_array_f32(stream, 6)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin = read_i32(stream)
        if (ctx.bs_version < 100):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.shader_property = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.alpha_property = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            write_array_f32(stream, self.bound_min_max)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin)
        if (ctx.bs_version < 100):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.shader_property)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.alpha_property)


@dataclass(slots=True)
class NiTriBasedGeomData(Block):
    """Describes a mesh, built from triangles."""

    group_id: int = 0
    num_vertices: int = 0
    num_vertices: int = 0
    bs_max_vertices: int = 0
    keep_flags: int = 0
    compress_flags: int = 0
    has_vertices: bool = False
    vertices: list[Vector3 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    bs_data_flags: BSGeometryDataFlags | None = field(default_factory=BSGeometryDataFlags)
    material_crc: int = 0
    has_normals: bool = False
    normals: list[Vector3 | None] = field(default_factory=list)
    tangents: list[Vector3 | None] = field(default_factory=list)
    bitangents: list[Vector3 | None] = field(default_factory=list)
    has_div2_floats: bool = False
    div2_floats: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    bounding_sphere: NiBound | None = None
    has_vertex_colors: bool = False
    vertex_colors: list[Color4 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    has_uv: bool = False
    uv_sets: list[Any] = field(default_factory=list)
    consistency_flags: int = 0
    additional_data: int = 0
    num_triangles: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriBasedGeomData:
        self = cls()
        if ctx.version >= pack_version(10, 1, 0, 114):
            self.group_id = read_i32(stream)
        self.num_vertices = read_u16(stream)
        if (ctx.bs_version < 34):
            self.num_vertices = read_u16(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            self.bs_max_vertices = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.keep_flags = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.compress_flags = read_u8(stream)
        self.has_vertices = read_bool(stream)
        if self.has_vertices:
            self.vertices = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags = BSGeometryDataFlags.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.material_crc = read_u32(stream)
        self.has_normals = read_bool(stream)
        if self.has_normals:
            self.normals = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.tangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.bitangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.has_div2_floats = read_bool(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            self.div2_floats = read_array_f32(stream, int(self.num_vertices))
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.has_vertex_colors = read_bool(stream)
        if self.has_vertex_colors:
            self.vertex_colors = [Color4.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            self.has_uv = read_bool(stream)
        self.uv_sets = [[TexCoord.read(stream, ctx) for _ in range(int(self.num_vertices))] for _ in range(int(((self.data_flags & 63) | (self.bs_data_flags & 1))))]
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.consistency_flags = read_u16(stream)
        if ctx.version >= pack_version(20, 0, 0, 4):
            self.additional_data = read_i32(stream)
        self.num_triangles = read_u16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 1, 0, 114):
            write_i32(stream, self.group_id)
        write_u16(stream, self.num_vertices)
        if (ctx.bs_version < 34):
            write_u16(stream, self.num_vertices)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            write_u16(stream, self.bs_max_vertices)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.keep_flags)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.compress_flags)
        write_bool(stream, self.has_vertices)
        if self.has_vertices:
            for __v in self.vertices:
                __v.write(stream, ctx)
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags.write(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_u32(stream, self.material_crc)
        write_bool(stream, self.has_normals)
        if self.has_normals:
            for __v in self.normals:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.tangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.bitangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_bool(stream, self.has_div2_floats)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            write_array_f32(stream, self.div2_floats)
        self.bounding_sphere.write(stream, ctx)
        write_bool(stream, self.has_vertex_colors)
        if self.has_vertex_colors:
            for __v in self.vertex_colors:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags.write(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            write_bool(stream, self.has_uv)
        for __row in self.uv_sets:
            for __v in __row:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u16(stream, self.consistency_flags)
        if ctx.version >= pack_version(20, 0, 0, 4):
            write_i32(stream, self.additional_data)
        write_u16(stream, self.num_triangles)


@dataclass(slots=True)
class NiTriShape(Block):
    """A shape node that refers to singular triangle data."""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    data: int = 0
    data: int = 0
    skin_instance: int = 0
    skin_instance: int = 0
    material_data: MaterialData | None = None
    material_data: MaterialData | None = None
    shader_property: int = 0
    alpha_property: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriShape:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            self.bound_min_max = read_array_f32(stream, 6)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin = read_i32(stream)
        if (ctx.bs_version < 100):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.shader_property = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.alpha_property = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            write_array_f32(stream, self.bound_min_max)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin)
        if (ctx.bs_version < 100):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.shader_property)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.alpha_property)


@dataclass(slots=True)
class NiTriShapeData(Block):
    """Holds mesh data using a list of singular triangles."""

    group_id: int = 0
    num_vertices: int = 0
    num_vertices: int = 0
    bs_max_vertices: int = 0
    keep_flags: int = 0
    compress_flags: int = 0
    has_vertices: bool = False
    vertices: list[Vector3 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    bs_data_flags: BSGeometryDataFlags | None = field(default_factory=BSGeometryDataFlags)
    material_crc: int = 0
    has_normals: bool = False
    normals: list[Vector3 | None] = field(default_factory=list)
    tangents: list[Vector3 | None] = field(default_factory=list)
    bitangents: list[Vector3 | None] = field(default_factory=list)
    has_div2_floats: bool = False
    div2_floats: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    bounding_sphere: NiBound | None = None
    has_vertex_colors: bool = False
    vertex_colors: list[Color4 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    has_uv: bool = False
    uv_sets: list[Any] = field(default_factory=list)
    consistency_flags: int = 0
    additional_data: int = 0
    num_triangles: int = 0
    num_triangle_points: int = 0
    has_triangles: bool = False
    triangles: list[Triangle | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    num_match_groups: int = 0
    match_groups: list[MatchGroup | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriShapeData:
        self = cls()
        if ctx.version >= pack_version(10, 1, 0, 114):
            self.group_id = read_i32(stream)
        self.num_vertices = read_u16(stream)
        if (ctx.bs_version < 34):
            self.num_vertices = read_u16(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            self.bs_max_vertices = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.keep_flags = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.compress_flags = read_u8(stream)
        self.has_vertices = read_bool(stream)
        if self.has_vertices:
            self.vertices = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags = BSGeometryDataFlags.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.material_crc = read_u32(stream)
        self.has_normals = read_bool(stream)
        if self.has_normals:
            self.normals = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.tangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.bitangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.has_div2_floats = read_bool(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            self.div2_floats = read_array_f32(stream, int(self.num_vertices))
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.has_vertex_colors = read_bool(stream)
        if self.has_vertex_colors:
            self.vertex_colors = [Color4.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            self.has_uv = read_bool(stream)
        self.uv_sets = [[TexCoord.read(stream, ctx) for _ in range(int(self.num_vertices))] for _ in range(int(((self.data_flags & 63) | (self.bs_data_flags & 1))))]
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.consistency_flags = read_u16(stream)
        if ctx.version >= pack_version(20, 0, 0, 4):
            self.additional_data = read_i32(stream)
        self.num_triangles = read_u16(stream)
        self.num_triangle_points = read_u32(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.has_triangles = read_bool(stream)
        if ctx.version <= pack_version(10, 0, 1, 2):
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.version >= pack_version(10, 0, 1, 3)) and (self.has_triangles):
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if ctx.version >= pack_version(3, 1):
            self.num_match_groups = read_u16(stream)
        if ctx.version >= pack_version(3, 1):
            self.match_groups = [MatchGroup.read(stream, ctx) for _ in range(int(self.num_match_groups))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 1, 0, 114):
            write_i32(stream, self.group_id)
        write_u16(stream, self.num_vertices)
        if (ctx.bs_version < 34):
            write_u16(stream, self.num_vertices)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            write_u16(stream, self.bs_max_vertices)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.keep_flags)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.compress_flags)
        write_bool(stream, self.has_vertices)
        if self.has_vertices:
            for __v in self.vertices:
                __v.write(stream, ctx)
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags.write(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_u32(stream, self.material_crc)
        write_bool(stream, self.has_normals)
        if self.has_normals:
            for __v in self.normals:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.tangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.bitangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_bool(stream, self.has_div2_floats)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            write_array_f32(stream, self.div2_floats)
        self.bounding_sphere.write(stream, ctx)
        write_bool(stream, self.has_vertex_colors)
        if self.has_vertex_colors:
            for __v in self.vertex_colors:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags.write(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            write_bool(stream, self.has_uv)
        for __row in self.uv_sets:
            for __v in __row:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u16(stream, self.consistency_flags)
        if ctx.version >= pack_version(20, 0, 0, 4):
            write_i32(stream, self.additional_data)
        write_u16(stream, self.num_triangles)
        write_u32(stream, self.num_triangle_points)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_bool(stream, self.has_triangles)
        if ctx.version <= pack_version(10, 0, 1, 2):
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 0, 1, 3)) and (self.has_triangles):
            for __v in self.triangles:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(3, 1):
            write_u16(stream, self.num_match_groups)
        if ctx.version >= pack_version(3, 1):
            for __v in self.match_groups:
                __v.write(stream, ctx)


@dataclass(slots=True)
class NiTriStrips(Block):
    """A shape node that refers to data organized into strips of triangles"""

    shader_type: int = 0
    name: string | None = None
    legacy_extra_data: LegacyExtraData | None = None
    extra_data: int = 0
    num_extra_data_list: int = 0
    extra_data_list: list[int] = field(default_factory=list)
    controller: int = 0
    flags: int = 0
    flags: int = 0
    translation: Vector3 | None = None
    rotation: Matrix33 | None = None
    scale: float = 0.0
    velocity: Vector3 | None = None
    num_properties: int = 0
    properties: list[int] = field(default_factory=list)
    unknown_1: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    unknown_2: int = 0
    has_bounding_volume: bool = False
    bounding_volume: BoundingVolume | None = None
    collision_object: int = 0
    bounding_sphere: NiBound | None = None
    bound_min_max: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    skin: int = 0
    data: int = 0
    data: int = 0
    skin_instance: int = 0
    skin_instance: int = 0
    material_data: MaterialData | None = None
    material_data: MaterialData | None = None
    shader_property: int = 0
    alpha_property: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriStrips:
        self = cls()
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            self.shader_type = read_u32(stream)
        self.name = string.read(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data = LegacyExtraData.read(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.extra_data = read_i32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.num_extra_data_list = read_u32(stream)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.extra_data_list = [read_i32(stream) for _ in range(int(self.num_extra_data_list))]
        if ctx.version >= pack_version(3, 0):
            self.controller = read_i32(stream)
        if ctx.bs_version > 26:
            self.flags = read_u32(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            self.flags = read_u16(stream)
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity = Vector3.read(stream, ctx)
        if (ctx.bs_version <= 34):
            self.num_properties = read_u32(stream)
        if (ctx.bs_version <= 34):
            self.properties = [read_i32(stream) for _ in range(int(self.num_properties))]
        if ctx.version <= pack_version(2, 3):
            self.unknown_1 = read_array_u32(stream, 4)
        if ctx.version <= pack_version(2, 3):
            self.unknown_2 = read_u8(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            self.has_bounding_volume = read_bool(stream)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume = BoundingVolume.read(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.collision_object = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere = NiBound.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            self.bound_min_max = read_array_f32(stream, 6)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin = read_i32(stream)
        if (ctx.bs_version < 100):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.data = read_i32(stream)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.skin_instance = read_i32(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data = MaterialData.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.shader_property = read_i32(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.alpha_property = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 83) and (ctx.bs_version <= 139)):
            write_u32(stream, self.shader_type)
        self.name.write(stream, ctx)
        if ctx.version <= pack_version(2, 3):
            self.legacy_extra_data.write(stream, ctx)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_i32(stream, self.extra_data)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u32(stream, self.num_extra_data_list)
        if ctx.version >= pack_version(10, 0, 1, 0):
            for __v in self.extra_data_list:
                write_i32(stream, __v)
        if ctx.version >= pack_version(3, 0):
            write_i32(stream, self.controller)
        if ctx.bs_version > 26:
            write_u32(stream, self.flags)
        if (ctx.version >= pack_version(3, 0)) and (ctx.bs_version <= 26):
            write_u16(stream, self.flags)
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.velocity.write(stream, ctx)
        if (ctx.bs_version <= 34):
            write_u32(stream, self.num_properties)
        if (ctx.bs_version <= 34):
            for __v in self.properties:
                write_i32(stream, __v)
        if ctx.version <= pack_version(2, 3):
            write_array_u32(stream, self.unknown_1)
        if ctx.version <= pack_version(2, 3):
            write_u8(stream, self.unknown_2)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)):
            write_bool(stream, self.has_bounding_volume)
        if (ctx.version >= pack_version(3, 0)) and (ctx.version <= pack_version(4, 2, 2, 0)) and (self.has_bounding_volume):
            self.bounding_volume.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_i32(stream, self.collision_object)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.bounding_sphere.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 155)):
            write_array_f32(stream, self.bound_min_max)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin)
        if (ctx.bs_version < 100):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.data)
        if (ctx.version >= pack_version(3, 3, 0, 13)) and ((ctx.bs_version < 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            write_i32(stream, self.skin_instance)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and ((ctx.bs_version < 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 100)):
            self.material_data.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.shader_property)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_i32(stream, self.alpha_property)


@dataclass(slots=True)
class NiTriStripsData(Block):
    """Holds mesh data using strips of triangles."""

    group_id: int = 0
    num_vertices: int = 0
    num_vertices: int = 0
    bs_max_vertices: int = 0
    keep_flags: int = 0
    compress_flags: int = 0
    has_vertices: bool = False
    vertices: list[Vector3 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    bs_data_flags: BSGeometryDataFlags | None = field(default_factory=BSGeometryDataFlags)
    material_crc: int = 0
    has_normals: bool = False
    normals: list[Vector3 | None] = field(default_factory=list)
    tangents: list[Vector3 | None] = field(default_factory=list)
    bitangents: list[Vector3 | None] = field(default_factory=list)
    has_div2_floats: bool = False
    div2_floats: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    bounding_sphere: NiBound | None = None
    has_vertex_colors: bool = False
    vertex_colors: list[Color4 | None] = field(default_factory=list)
    data_flags: NiGeometryDataFlags | None = field(default_factory=NiGeometryDataFlags)
    has_uv: bool = False
    uv_sets: list[Any] = field(default_factory=list)
    consistency_flags: int = 0
    additional_data: int = 0
    num_triangles: int = 0
    num_strips: int = 0
    strip_lengths: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    has_points: bool = False
    points: list[Any] = field(default_factory=list)
    points: list[Any] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTriStripsData:
        self = cls()
        if ctx.version >= pack_version(10, 1, 0, 114):
            self.group_id = read_i32(stream)
        self.num_vertices = read_u16(stream)
        if (ctx.bs_version < 34):
            self.num_vertices = read_u16(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            self.bs_max_vertices = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.keep_flags = read_u8(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.compress_flags = read_u8(stream)
        self.has_vertices = read_bool(stream)
        if self.has_vertices:
            self.vertices = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags = BSGeometryDataFlags.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.material_crc = read_u32(stream)
        self.has_normals = read_bool(stream)
        if self.has_normals:
            self.normals = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.tangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            self.bitangents = [Vector3.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.has_div2_floats = read_bool(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            self.div2_floats = read_array_f32(stream, int(self.num_vertices))
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.has_vertex_colors = read_bool(stream)
        if self.has_vertex_colors:
            self.vertex_colors = [Color4.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags = NiGeometryDataFlags.read(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            self.has_uv = read_bool(stream)
        self.uv_sets = [[TexCoord.read(stream, ctx) for _ in range(int(self.num_vertices))] for _ in range(int(((self.data_flags & 63) | (self.bs_data_flags & 1))))]
        if ctx.version >= pack_version(10, 0, 1, 0):
            self.consistency_flags = read_u16(stream)
        if ctx.version >= pack_version(20, 0, 0, 4):
            self.additional_data = read_i32(stream)
        self.num_triangles = read_u16(stream)
        self.num_strips = read_u16(stream)
        self.strip_lengths = read_array_u16(stream, int(self.num_strips))
        if ctx.version >= pack_version(10, 0, 1, 3):
            self.has_points = read_bool(stream)
        if ctx.version <= pack_version(10, 0, 1, 2):
            self.points = [read_array_u16(stream, int(self.strip_lengths[__i])) for __i in range(int(self.num_strips))]
        if (ctx.version >= pack_version(10, 0, 1, 3)) and (self.has_points):
            self.points = [read_array_u16(stream, int(self.strip_lengths[__i])) for __i in range(int(self.num_strips))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(10, 1, 0, 114):
            write_i32(stream, self.group_id)
        write_u16(stream, self.num_vertices)
        if (ctx.bs_version < 34):
            write_u16(stream, self.num_vertices)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version >= 34)):
            write_u16(stream, self.bs_max_vertices)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.keep_flags)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_u8(stream, self.compress_flags)
        write_bool(stream, self.has_vertices)
        if self.has_vertices:
            for __v in self.vertices:
                __v.write(stream, ctx)
        if (
            (ctx.version >= pack_version(10, 0, 1, 0))
            and (
                False  # CODEGEN-TODO vercond '!#BS202#'; unexpected operand '!'
            )
        ):
            self.data_flags.write(stream, ctx)
        if ((ctx.version == pack_version(20, 2, 0, 7)) and (ctx.bs_version > 0)):
            self.bs_data_flags.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_u32(stream, self.material_crc)
        write_bool(stream, self.has_normals)
        if self.has_normals:
            for __v in self.normals:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.tangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_normals) and (((self.data_flags | self.bs_data_flags) & 4096) != 0)):
            for __v in self.bitangents:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            write_bool(stream, self.has_div2_floats)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))) and (self.has_div2_floats):
            write_array_f32(stream, self.div2_floats)
        self.bounding_sphere.write(stream, ctx)
        write_bool(stream, self.has_vertex_colors)
        if self.has_vertex_colors:
            for __v in self.vertex_colors:
                __v.write(stream, ctx)
        if ctx.version <= pack_version(4, 2, 2, 0):
            self.data_flags.write(stream, ctx)
        if ctx.version <= pack_version(4, 0, 0, 2):
            write_bool(stream, self.has_uv)
        for __row in self.uv_sets:
            for __v in __row:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(10, 0, 1, 0):
            write_u16(stream, self.consistency_flags)
        if ctx.version >= pack_version(20, 0, 0, 4):
            write_i32(stream, self.additional_data)
        write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_strips)
        write_array_u16(stream, self.strip_lengths)
        if ctx.version >= pack_version(10, 0, 1, 3):
            write_bool(stream, self.has_points)
        if ctx.version <= pack_version(10, 0, 1, 2):
            for __row in self.points:
                write_array_u16(stream, __row)
        if (ctx.version >= pack_version(10, 0, 1, 3)) and (self.has_points):
            for __row in self.points:
                write_array_u16(stream, __row)
