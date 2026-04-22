"""Generated NIF compound structs.

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import IO, Any

import numpy as np
import numpy.typing as npt

from nifblend.format.base import Compound, ReadContext
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

__all__ = ['AVObject', 'BSGeometryPerSegmentSharedData', 'BSGeometrySegmentData', 'BSGeometrySegmentSharedData', 'BSGeometrySubSegment', 'BSMesh', 'BSMeshArray', 'BSSPLuminanceParams', 'BSSPTranslucencyParams', 'BSSPWetnessParams', 'BSSkinBoneTrans', 'BSStreamHeader', 'BSTextureArray', 'BSVertexData', 'BSVertexDataSSE', 'BodyPartList', 'BoneData', 'BoneVertData', 'BoundingVolume', 'BoxBV', 'ByteArray', 'ByteColor3', 'ByteColor4', 'ByteVector3', 'CapsuleBV', 'Color3', 'Color4', 'ControlledBlock', 'ExportString', 'FilePath', 'Footer', 'FormatPrefs', 'HalfSpaceBV', 'HalfTexCoord', 'HalfVector3', 'Header', 'InterpBlendItem', 'Key', 'KeyGroup', 'LODRange', 'LegacyExtraData', 'MatchGroup', 'MaterialData', 'Matrix22', 'Matrix33', 'NiBound', 'NiBoundAABB', 'NiPlane', 'NiQuatTransform', 'NiTransform', 'PixelFormatComponent', 'QuatKey', 'Quaternion', 'ShaderTexDesc', 'SizedString', 'SizedString16', 'SkinPartition', 'StringPalette', 'TBC', 'TexCoord', 'TexDesc', 'Triangle', 'UnionBV', 'Vector3', 'Vector4', 'string']
from .bitfields import AlphaFlags, BSGeometryDataFlags, BSVertexDesc, NiGeometryDataFlags, TexturingFlags, TexturingMapFlags, TimeControllerFlags
from .enums import AccumFlags, AlphaFormat, AlphaFunction, AnimNoteType, AnimType, ApplyMode, BSDismemberBodyPartType, BSLightingShaderType, BSPartFlag, BSShaderCRC32, BSShaderFlags, BSShaderFlags2, BSShaderType, BSShaderType155, BillboardMode, BoundVolumeType, ConsistencyType, CycleType, EndianType, Fallout4ShaderPropertyFlags1, Fallout4ShaderPropertyFlags2, ImageType, InterpBlendFlags, KeyType, MipMapFormat, NiNBTMethod, NiSwitchFlags, PixelComponent, PixelFormat, PixelLayout, PixelRepresentation, PixelTiling, ShadeFlags, SkyrimShaderPropertyFlags1, SkyrimShaderPropertyFlags2, TestFunction, TexClampMode, TexFilterMode, TransformMethod, VertexAttribute


@dataclass(slots=True)
class AVObject(Compound):
    """Used in NiDefaultAVObjectPalette."""

    name: SizedString | None = None
    av_object: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> AVObject:
        self = cls()
        self.name = SizedString.read(stream, ctx)
        self.av_object = read_i32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.name.write(stream, ctx)
        write_i32(stream, self.av_object)


@dataclass(slots=True)
class BSGeometryPerSegmentSharedData(Compound):
    user_index: int = 0
    bone_id: int = 0
    num_cut_offsets: int = 0
    cut_offsets: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometryPerSegmentSharedData:
        self = cls()
        self.user_index = read_u32(stream)
        self.bone_id = read_u32(stream)
        self.num_cut_offsets = read_u32(stream)
        self.cut_offsets = read_array_f32(stream, int(self.num_cut_offsets))
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.user_index)
        write_u32(stream, self.bone_id)
        write_u32(stream, self.num_cut_offsets)
        write_array_f32(stream, self.cut_offsets)


@dataclass(slots=True)
class BSGeometrySegmentData(Compound):
    """Bethesda-specific. Describes groups of triangles either segmented in a grid (for LOD) or by body part for skinned FO4 meshes."""

    flags: int = 0
    start_index: int = 0
    num_primitives: int = 0
    parent_array_index: int = 0
    num_sub_segments: int = 0
    sub_segment: list[BSGeometrySubSegment | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometrySegmentData:
        self = cls()
        if (ctx.bs_version < 130):
            self.flags = read_u8(stream)
        self.start_index = read_u32(stream)
        self.num_primitives = read_u32(stream)
        if (ctx.bs_version >= 130):
            self.parent_array_index = read_u32(stream)
        if (ctx.bs_version >= 130):
            self.num_sub_segments = read_u32(stream)
        if (ctx.bs_version >= 130):
            self.sub_segment = [BSGeometrySubSegment.read(stream, ctx) for _ in range(int(self.num_sub_segments))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.bs_version < 130):
            write_u8(stream, self.flags)
        write_u32(stream, self.start_index)
        write_u32(stream, self.num_primitives)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.parent_array_index)
        if (ctx.bs_version >= 130):
            write_u32(stream, self.num_sub_segments)
        if (ctx.bs_version >= 130):
            for __v in self.sub_segment:
                __v.write(stream, ctx)


@dataclass(slots=True)
class BSGeometrySegmentSharedData(Compound):
    num_segments: int = 0
    total_segments: int = 0
    segment_starts: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    per_segment_data: list[BSGeometryPerSegmentSharedData | None] = field(default_factory=list)
    ssf_file: SizedString16 | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometrySegmentSharedData:
        self = cls()
        self.num_segments = read_u32(stream)
        self.total_segments = read_u32(stream)
        self.segment_starts = read_array_u32(stream, int(self.num_segments))
        self.per_segment_data = [BSGeometryPerSegmentSharedData.read(stream, ctx) for _ in range(int(self.total_segments))]
        self.ssf_file = SizedString16.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_segments)
        write_u32(stream, self.total_segments)
        write_array_u32(stream, self.segment_starts)
        for __v in self.per_segment_data:
            __v.write(stream, ctx)
        self.ssf_file.write(stream, ctx)


@dataclass(slots=True)
class BSGeometrySubSegment(Compound):
    """This is only defined because of recursion issues."""

    start_index: int = 0
    num_primitives: int = 0
    parent_array_index: int = 0
    unused: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometrySubSegment:
        self = cls()
        self.start_index = read_u32(stream)
        self.num_primitives = read_u32(stream)
        self.parent_array_index = read_u32(stream)
        self.unused = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.start_index)
        write_u32(stream, self.num_primitives)
        write_u32(stream, self.parent_array_index)
        write_u32(stream, self.unused)


@dataclass(slots=True)
class BSMesh(Compound):
    indices_size: int = 0
    num_verts: int = 0
    flags: int = 0
    mesh_path: SizedString | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSMesh:
        self = cls()
        self.indices_size = read_u32(stream)
        self.num_verts = read_u32(stream)
        self.flags = read_u32(stream)
        self.mesh_path = SizedString.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.indices_size)
        write_u32(stream, self.num_verts)
        write_u32(stream, self.flags)
        self.mesh_path.write(stream, ctx)


@dataclass(slots=True)
class BSMeshArray(Compound):
    has_mesh: int = 0
    mesh: BSMesh | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSMeshArray:
        self = cls()
        self.has_mesh = read_u8(stream)
        if self.has_mesh == 1:
            self.mesh = BSMesh.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.has_mesh)
        if self.has_mesh == 1:
            self.mesh.write(stream, ctx)


@dataclass(slots=True)
class BSSPLuminanceParams(Compound):
    lum_emittance: float = 0.0
    exposure_offset: float = 0.0
    final_exposure_min: float = 0.0
    final_exposure_max: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSPLuminanceParams:
        self = cls()
        self.lum_emittance = read_f32(stream)
        self.exposure_offset = read_f32(stream)
        self.final_exposure_min = read_f32(stream)
        self.final_exposure_max = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.lum_emittance)
        write_f32(stream, self.exposure_offset)
        write_f32(stream, self.final_exposure_min)
        write_f32(stream, self.final_exposure_max)


@dataclass(slots=True)
class BSSPTranslucencyParams(Compound):
    subsurface_color: Color3 | None = None
    transmissive_scale: float = 0.0
    turbulence: float = 0.0
    thick_object: bool = False
    mix_albedo: bool = False

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSPTranslucencyParams:
        self = cls()
        self.subsurface_color = Color3.read(stream, ctx)
        self.transmissive_scale = read_f32(stream)
        self.turbulence = read_f32(stream)
        self.thick_object = read_bool(stream)
        self.mix_albedo = read_bool(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.subsurface_color.write(stream, ctx)
        write_f32(stream, self.transmissive_scale)
        write_f32(stream, self.turbulence)
        write_bool(stream, self.thick_object)
        write_bool(stream, self.mix_albedo)


@dataclass(slots=True)
class BSSPWetnessParams(Compound):
    spec_scale: float = 0.0
    spec_power: float = 0.0
    min_var: float = 0.0
    env_map_scale: float = 0.0
    fresnel_power: float = 0.0
    metalness: float = 0.0
    unknown_1: float = 0.0
    unknown_2: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSPWetnessParams:
        self = cls()
        self.spec_scale = read_f32(stream)
        self.spec_power = read_f32(stream)
        self.min_var = read_f32(stream)
        if (ctx.bs_version == 130):
            self.env_map_scale = read_f32(stream)
        self.fresnel_power = read_f32(stream)
        self.metalness = read_f32(stream)
        if (ctx.bs_version > 130):
            self.unknown_1 = read_f32(stream)
        if (ctx.bs_version >= 155):
            self.unknown_2 = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.spec_scale)
        write_f32(stream, self.spec_power)
        write_f32(stream, self.min_var)
        if (ctx.bs_version == 130):
            write_f32(stream, self.env_map_scale)
        write_f32(stream, self.fresnel_power)
        write_f32(stream, self.metalness)
        if (ctx.bs_version > 130):
            write_f32(stream, self.unknown_1)
        if (ctx.bs_version >= 155):
            write_f32(stream, self.unknown_2)


@dataclass(slots=True)
class BSSkinBoneTrans(Compound):
    """Fallout 4 Bone Transform"""

    bounding_sphere: NiBound | None = None
    rotation: Matrix33 | None = None
    translation: Vector3 | None = None
    scale: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSSkinBoneTrans:
        self = cls()
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.rotation = Matrix33.read(stream, ctx)
        self.translation = Vector3.read(stream, ctx)
        self.scale = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.bounding_sphere.write(stream, ctx)
        self.rotation.write(stream, ctx)
        self.translation.write(stream, ctx)
        write_f32(stream, self.scale)


@dataclass(slots=True)
class BSStreamHeader(Compound):
    """Information about how the file was exported"""

    bs_version: int = 0
    author: ExportString | None = None
    unknown_int: int = 0
    process_script: ExportString | None = None
    export_script: ExportString | None = None
    max_filepath: ExportString | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSStreamHeader:
        self = cls()
        self.bs_version = read_u32(stream)
        self.author = ExportString.read(stream, ctx)
        if self.bs_version > 130:
            self.unknown_int = read_u32(stream)
        if self.bs_version < 131:
            self.process_script = ExportString.read(stream, ctx)
        self.export_script = ExportString.read(stream, ctx)
        if self.bs_version >= 103:
            self.max_filepath = ExportString.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.bs_version)
        self.author.write(stream, ctx)
        if self.bs_version > 130:
            write_u32(stream, self.unknown_int)
        if self.bs_version < 131:
            self.process_script.write(stream, ctx)
        self.export_script.write(stream, ctx)
        if self.bs_version >= 103:
            self.max_filepath.write(stream, ctx)


@dataclass(slots=True)
class BSTextureArray(Compound):
    texture_array_width: int = 0
    texture_array: list[SizedString | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSTextureArray:
        self = cls()
        self.texture_array_width = read_u32(stream)
        self.texture_array = [SizedString.read(stream, ctx) for _ in range(int(self.texture_array_width))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.texture_array_width)
        for __v in self.texture_array:
            __v.write(stream, ctx)


@dataclass(slots=True)
class BSVertexData(Compound):
    """Byte fields for normal, tangent and bitangent map [0, 255] to [-1, 1]."""

    vertex: Vector3 | None = None
    bitangent_x: float = 0.0
    unused_w: int = 0
    vertex: HalfVector3 | None = None
    bitangent_x: float = 0.0
    unused_w: int = 0
    uv: HalfTexCoord | None = None
    normal: ByteVector3 | None = None
    bitangent_y: int = 0
    tangent: ByteVector3 | None = None
    bitangent_z: int = 0
    vertex_colors: ByteColor4 | None = None
    bone_weights: list[float] = field(default_factory=list)
    bone_indices: list[int] = field(default_factory=list)
    eye_data: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSVertexData:
        self = cls()
        if (ctx.arg & 0x401) == 0x401:
            self.vertex = Vector3.read(stream, ctx)
        if (ctx.arg & 0x411) == 0x411:
            self.bitangent_x = read_f32(stream)
        if (ctx.arg & 0x411) == 0x401:
            self.unused_w = read_u32(stream)
        if (ctx.arg & 0x401) == 0x1:
            self.vertex = HalfVector3.read(stream, ctx)
        if (ctx.arg & 0x411) == 0x11:
            self.bitangent_x = read_f16(stream)
        if (ctx.arg & 0x411) == 0x1:
            self.unused_w = read_u16(stream)
        if (ctx.arg & 0x2) != 0:
            self.uv = HalfTexCoord.read(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.normal = ByteVector3.read(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.bitangent_y = read_u8(stream)
        if (ctx.arg & 0x18) == 0x18:
            self.tangent = ByteVector3.read(stream, ctx)
        if (ctx.arg & 0x18) == 0x18:
            self.bitangent_z = read_u8(stream)
        if (ctx.arg & 0x20) != 0:
            self.vertex_colors = ByteColor4.read(stream, ctx)
        if (ctx.arg & 0x40) != 0:
            self.bone_weights = [read_f16(stream) for _ in range(4)]
        if (ctx.arg & 0x40) != 0:
            self.bone_indices = [read_u8(stream) for _ in range(4)]
        if (ctx.arg & 0x100) != 0:
            self.eye_data = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.arg & 0x401) == 0x401:
            self.vertex.write(stream, ctx)
        if (ctx.arg & 0x411) == 0x411:
            write_f32(stream, self.bitangent_x)
        if (ctx.arg & 0x411) == 0x401:
            write_u32(stream, self.unused_w)
        if (ctx.arg & 0x401) == 0x1:
            self.vertex.write(stream, ctx)
        if (ctx.arg & 0x411) == 0x11:
            write_f16(stream, self.bitangent_x)
        if (ctx.arg & 0x411) == 0x1:
            write_u16(stream, self.unused_w)
        if (ctx.arg & 0x2) != 0:
            self.uv.write(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.normal.write(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            write_u8(stream, self.bitangent_y)
        if (ctx.arg & 0x18) == 0x18:
            self.tangent.write(stream, ctx)
        if (ctx.arg & 0x18) == 0x18:
            write_u8(stream, self.bitangent_z)
        if (ctx.arg & 0x20) != 0:
            self.vertex_colors.write(stream, ctx)
        if (ctx.arg & 0x40) != 0:
            for __v in self.bone_weights:
                write_f16(stream, __v)
        if (ctx.arg & 0x40) != 0:
            for __v in self.bone_indices:
                write_u8(stream, __v)
        if (ctx.arg & 0x100) != 0:
            write_f32(stream, self.eye_data)


@dataclass(slots=True)
class BSVertexDataSSE(Compound):
    vertex: Vector3 | None = None
    bitangent_x: float = 0.0
    unused_w: int = 0
    uv: HalfTexCoord | None = None
    normal: ByteVector3 | None = None
    bitangent_y: int = 0
    tangent: ByteVector3 | None = None
    bitangent_z: int = 0
    vertex_colors: ByteColor4 | None = None
    bone_weights: list[float] = field(default_factory=list)
    bone_indices: list[int] = field(default_factory=list)
    eye_data: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSVertexDataSSE:
        self = cls()
        if (ctx.arg & 0x1) != 0:
            self.vertex = Vector3.read(stream, ctx)
        if (ctx.arg & 0x11) == 0x11:
            self.bitangent_x = read_f32(stream)
        if (ctx.arg & 0x11) == 0x1:
            self.unused_w = read_u32(stream)
        if (ctx.arg & 0x2) != 0:
            self.uv = HalfTexCoord.read(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.normal = ByteVector3.read(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.bitangent_y = read_u8(stream)
        if (ctx.arg & 0x18) == 0x18:
            self.tangent = ByteVector3.read(stream, ctx)
        if (ctx.arg & 0x18) == 0x18:
            self.bitangent_z = read_u8(stream)
        if (ctx.arg & 0x20) != 0:
            self.vertex_colors = ByteColor4.read(stream, ctx)
        if (ctx.arg & 0x40) != 0:
            self.bone_weights = [read_f16(stream) for _ in range(4)]
        if (ctx.arg & 0x40) != 0:
            self.bone_indices = [read_u8(stream) for _ in range(4)]
        if (ctx.arg & 0x100) != 0:
            self.eye_data = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.arg & 0x1) != 0:
            self.vertex.write(stream, ctx)
        if (ctx.arg & 0x11) == 0x11:
            write_f32(stream, self.bitangent_x)
        if (ctx.arg & 0x11) == 0x1:
            write_u32(stream, self.unused_w)
        if (ctx.arg & 0x2) != 0:
            self.uv.write(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            self.normal.write(stream, ctx)
        if (ctx.arg & 0x8) != 0:
            write_u8(stream, self.bitangent_y)
        if (ctx.arg & 0x18) == 0x18:
            self.tangent.write(stream, ctx)
        if (ctx.arg & 0x18) == 0x18:
            write_u8(stream, self.bitangent_z)
        if (ctx.arg & 0x20) != 0:
            self.vertex_colors.write(stream, ctx)
        if (ctx.arg & 0x40) != 0:
            for __v in self.bone_weights:
                write_f16(stream, __v)
        if (ctx.arg & 0x40) != 0:
            for __v in self.bone_indices:
                write_u8(stream, __v)
        if (ctx.arg & 0x100) != 0:
            write_f32(stream, self.eye_data)


@dataclass(slots=True)
class BodyPartList(Compound):
    """Body part list for DismemberSkinInstance"""

    part_flag: int = 0
    body_part: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BodyPartList:
        self = cls()
        self.part_flag = read_u16(stream)
        self.body_part = read_u16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.part_flag)
        write_u16(stream, self.body_part)


@dataclass(slots=True)
class BoneData(Compound):
    """NiSkinData::BoneData. Skinning data component."""

    skin_transform: NiTransform | None = None
    bounding_sphere: NiBound | None = None
    num_vertices: int = 0
    vertex_weights: list[BoneVertData | None] = field(default_factory=list)
    vertex_weights: list[BoneVertData | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BoneData:
        self = cls()
        self.skin_transform = NiTransform.read(stream, ctx)
        self.bounding_sphere = NiBound.read(stream, ctx)
        self.num_vertices = read_u16(stream)
        if ctx.version <= pack_version(4, 2, 1, 0):
            self.vertex_weights = [BoneVertData.read(stream, ctx) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(4, 2, 2, 0)) and (ctx.arg != 0):
            self.vertex_weights = [BoneVertData.read(stream, ctx) for _ in range(int(self.num_vertices))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.skin_transform.write(stream, ctx)
        self.bounding_sphere.write(stream, ctx)
        write_u16(stream, self.num_vertices)
        if ctx.version <= pack_version(4, 2, 1, 0):
            for __v in self.vertex_weights:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(4, 2, 2, 0)) and (ctx.arg != 0):
            for __v in self.vertex_weights:
                __v.write(stream, ctx)


@dataclass(slots=True)
class BoneVertData(Compound):
    """NiSkinData::BoneVertData. A vertex and its weight."""

    index: int = 0
    weight: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BoneVertData:
        self = cls()
        self.index = read_u16(stream)
        self.weight = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.index)
        write_f32(stream, self.weight)


@dataclass(slots=True)
class BoundingVolume(Compound):
    collision_type: int = 0
    sphere: NiBound | None = None
    box: BoxBV | None = None
    capsule: CapsuleBV | None = None
    union_bv: UnionBV | None = None
    half_space: HalfSpaceBV | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BoundingVolume:
        self = cls()
        self.collision_type = read_u32(stream)
        if self.collision_type == 0:
            self.sphere = NiBound.read(stream, ctx)
        if self.collision_type == 1:
            self.box = BoxBV.read(stream, ctx)
        if self.collision_type == 2:
            self.capsule = CapsuleBV.read(stream, ctx)
        if self.collision_type == 4:
            self.union_bv = UnionBV.read(stream, ctx)
        if self.collision_type == 5:
            self.half_space = HalfSpaceBV.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.collision_type)
        if self.collision_type == 0:
            self.sphere.write(stream, ctx)
        if self.collision_type == 1:
            self.box.write(stream, ctx)
        if self.collision_type == 2:
            self.capsule.write(stream, ctx)
        if self.collision_type == 4:
            self.union_bv.write(stream, ctx)
        if self.collision_type == 5:
            self.half_space.write(stream, ctx)


@dataclass(slots=True)
class BoxBV(Compound):
    """Box Bounding Volume"""

    center: Vector3 | None = None
    axis: list[Vector3 | None] = field(default_factory=list)
    extent: Vector3 | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BoxBV:
        self = cls()
        self.center = Vector3.read(stream, ctx)
        self.axis = [Vector3.read(stream, ctx) for _ in range(3)]
        self.extent = Vector3.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.center.write(stream, ctx)
        for __v in self.axis:
            __v.write(stream, ctx)
        self.extent.write(stream, ctx)


@dataclass(slots=True)
class ByteArray(Compound):
    """An array of bytes."""

    data_size: int = 0
    data: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ByteArray:
        self = cls()
        self.data_size = read_u32(stream)
        self.data = [read_u8(stream) for _ in range(int(self.data_size))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.data_size)
        for __v in self.data:
            write_u8(stream, __v)


@dataclass(slots=True)
class ByteColor3(Compound):
    """A color without alpha (red, green, blue)."""

    r: int = 0
    g: int = 0
    b: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ByteColor3:
        self = cls()
        self.r = read_u8(stream)
        self.g = read_u8(stream)
        self.b = read_u8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.r)
        write_u8(stream, self.g)
        write_u8(stream, self.b)


@dataclass(slots=True)
class ByteColor4(Compound):
    """A color with alpha (red, green, blue, alpha)."""

    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ByteColor4:
        self = cls()
        self.r = read_u8(stream)
        self.g = read_u8(stream)
        self.b = read_u8(stream)
        self.a = read_u8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.r)
        write_u8(stream, self.g)
        write_u8(stream, self.b)
        write_u8(stream, self.a)


@dataclass(slots=True)
class ByteVector3(Compound):
    """A vector in 3D space (x,y,z)."""

    x: int = 0
    y: int = 0
    z: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ByteVector3:
        self = cls()
        self.x = read_u8(stream)
        self.y = read_u8(stream)
        self.z = read_u8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.x)
        write_u8(stream, self.y)
        write_u8(stream, self.z)


@dataclass(slots=True)
class CapsuleBV(Compound):
    """Capsule Bounding Volume"""

    center: Vector3 | None = None
    origin: Vector3 | None = None
    extent: float = 0.0
    radius: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> CapsuleBV:
        self = cls()
        self.center = Vector3.read(stream, ctx)
        self.origin = Vector3.read(stream, ctx)
        self.extent = read_f32(stream)
        self.radius = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.center.write(stream, ctx)
        self.origin.write(stream, ctx)
        write_f32(stream, self.extent)
        write_f32(stream, self.radius)


@dataclass(slots=True)
class Color3(Compound):
    """A color without alpha (red, green, blue)."""

    r: float = 0.0
    g: float = 0.0
    b: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Color3:
        self = cls()
        self.r = read_f32(stream)
        self.g = read_f32(stream)
        self.b = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.r)
        write_f32(stream, self.g)
        write_f32(stream, self.b)


@dataclass(slots=True)
class Color4(Compound):
    """A color with alpha (red, green, blue, alpha)."""

    r: float = 0.0
    g: float = 0.0
    b: float = 0.0
    a: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Color4:
        self = cls()
        self.r = read_f32(stream)
        self.g = read_f32(stream)
        self.b = read_f32(stream)
        self.a = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.r)
        write_f32(stream, self.g)
        write_f32(stream, self.b)
        write_f32(stream, self.a)


@dataclass(slots=True)
class ControlledBlock(Compound):
    """In a .kf file, this links to a controllable object, via its name (or for version 10.2.0.0 and up, a link and offset to a NiStringPalette that contains the name), and a sequence of interpolators that apply to this controllable object, via links.
        For Controller ID, NiInterpController::GetCtlrID() virtual function returns a string formatted specifically for the derived type.
        For Interpolator ID, NiInterpController::GetInterpolatorID() virtual function returns a string formatted specifically for the derived type.
        The string formats are documented on the relevant niobject blocks."""

    target_name: SizedString | None = None
    interpolator: int = 0
    controller: int = 0
    blend_interpolator: int = 0
    blend_index: int = 0
    priority: int = 0
    node_name: string | None = None
    property_type: string | None = None
    controller_type: string | None = None
    controller_id: string | None = None
    interpolator_id: string | None = None
    string_palette: int = 0
    node_name_offset: int = 0
    property_type_offset: int = 0
    controller_type_offset: int = 0
    controller_id_offset: int = 0
    interpolator_id_offset: int = 0
    node_name: string | None = None
    property_type: string | None = None
    controller_type: string | None = None
    controller_id: string | None = None
    interpolator_id: string | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ControlledBlock:
        self = cls()
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.target_name = SizedString.read(stream, ctx)
        if ctx.version >= pack_version(10, 1, 0, 106):
            self.interpolator = read_i32(stream)
        if ctx.version <= pack_version(20, 5, 0, 0):
            self.controller = read_i32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 110)):
            self.blend_interpolator = read_i32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 110)):
            self.blend_index = read_u16(stream)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and ((ctx.bs_version > 0)):
            self.priority = read_u8(stream)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.node_name = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.property_type = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.controller_type = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.controller_id = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.interpolator_id = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.string_palette = read_i32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.node_name_offset = read_u32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.property_type_offset = read_u32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.controller_type_offset = read_u32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.controller_id_offset = read_u32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            self.interpolator_id_offset = read_u32(stream)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.node_name = string.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.property_type = string.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.controller_type = string.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.controller_id = string.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.interpolator_id = string.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version <= pack_version(10, 1, 0, 103):
            self.target_name.write(stream, ctx)
        if ctx.version >= pack_version(10, 1, 0, 106):
            write_i32(stream, self.interpolator)
        if ctx.version <= pack_version(20, 5, 0, 0):
            write_i32(stream, self.controller)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 110)):
            write_i32(stream, self.blend_interpolator)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 110)):
            write_u16(stream, self.blend_index)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and ((ctx.bs_version > 0)):
            write_u8(stream, self.priority)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.node_name.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.property_type.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.controller_type.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.controller_id.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 104)) and (ctx.version <= pack_version(10, 1, 0, 113)):
            self.interpolator_id.write(stream, ctx)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_i32(stream, self.string_palette)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_u32(stream, self.node_name_offset)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_u32(stream, self.property_type_offset)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_u32(stream, self.controller_type_offset)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_u32(stream, self.controller_id_offset)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(20, 1, 0, 0)):
            write_u32(stream, self.interpolator_id_offset)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.node_name.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.property_type.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.controller_type.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.controller_id.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.interpolator_id.write(stream, ctx)


@dataclass(slots=True)
class ExportString(Compound):
    """Specific to Bethesda-specific header export strings."""

    length: int = 0
    value: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ExportString:
        self = cls()
        self.length = read_u8(stream)
        self.value = [read_u8(stream) for _ in range(int(self.length))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u8(stream, self.length)
        for __v in self.value:
            write_u8(stream, __v)


@dataclass(slots=True)
class FilePath(Compound):
    """A string that contains the path to a file."""

    string: SizedString | None = None
    index: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> FilePath:
        self = cls()
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.string = SizedString.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 3):
            self.index = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.string.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 3):
            write_u32(stream, self.index)


@dataclass(slots=True)
class Footer(Compound):
    """The NIF file footer."""

    num_roots: int = 0
    roots: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Footer:
        self = cls()
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.num_roots = read_u32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.roots = [read_i32(stream) for _ in range(int(self.num_roots))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_u32(stream, self.num_roots)
        if ctx.version >= pack_version(3, 3, 0, 13):
            for __v in self.roots:
                write_i32(stream, __v)


@dataclass(slots=True)
class FormatPrefs(Compound):
    """NiTexture::FormatPrefs. These preferences are a request to the renderer to use a format the most closely matches the settings and may be ignored."""

    pixel_layout: int = 0
    use_mipmaps: int = 0
    alpha_format: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> FormatPrefs:
        self = cls()
        self.pixel_layout = read_u32(stream)
        self.use_mipmaps = read_u32(stream)
        self.alpha_format = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.pixel_layout)
        write_u32(stream, self.use_mipmaps)
        write_u32(stream, self.alpha_format)


@dataclass(slots=True)
class HalfSpaceBV(Compound):
    plane: NiPlane | None = None
    center: Vector3 | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> HalfSpaceBV:
        self = cls()
        self.plane = NiPlane.read(stream, ctx)
        self.center = Vector3.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.plane.write(stream, ctx)
        self.center.write(stream, ctx)


@dataclass(slots=True)
class HalfTexCoord(Compound):
    """Texture coordinates (u,v)."""

    u: float = 0.0
    v: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> HalfTexCoord:
        self = cls()
        self.u = read_f16(stream)
        self.v = read_f16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f16(stream, self.u)
        write_f16(stream, self.v)


@dataclass(slots=True)
class HalfVector3(Compound):
    """A vector in 3D space (x,y,z)."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> HalfVector3:
        self = cls()
        self.x = read_f16(stream)
        self.y = read_f16(stream)
        self.z = read_f16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f16(stream, self.x)
        write_f16(stream, self.y)
        write_f16(stream, self.z)


@dataclass(slots=True)
class Header(Compound):
    """The NIF file header."""

    header_string: int = 0
    copyright: list[int] = field(default_factory=list)
    version: int = 0
    endian_type: int = 0
    user_version: int = 0
    num_blocks: int = 0
    bs_header: BSStreamHeader | None = None
    metadata: ByteArray | None = None
    num_block_types: int = 0
    block_types: list[SizedString | None] = field(default_factory=list)
    block_type_hashes: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    block_type_index: list[int] = field(default_factory=list)
    block_size: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    num_strings: int = 0
    max_string_length: int = 0
    strings: list[SizedString | None] = field(default_factory=list)
    num_groups: int = 0
    groups: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Header:
        self = cls()
        # CODEGEN-TODO: unsupported basic type 'HeaderString' for 'Header String'
        if ctx.version <= pack_version(3, 1, 0, 0):
            # CODEGEN-TODO: unsupported basic array type 'LineString'
            pass
        if ctx.version >= pack_version(3, 1, 0, 1):
            self.version = read_u32(stream)
        if ctx.version >= pack_version(20, 0, 0, 3):
            self.endian_type = read_u8(stream)
        if ctx.version >= pack_version(10, 0, 1, 8):
            self.user_version = read_u32(stream)
        if ctx.version >= pack_version(3, 1, 0, 1):
            self.num_blocks = read_u32(stream)
        if (ctx.version == pack_version(10, 0, 1, 2)) or ((ctx.version == pack_version(20, 2, 0, 7)) or (ctx.version == pack_version(20, 0, 0, 5)) or ((ctx.version >= pack_version(10, 1, 0, 0)) and (ctx.version <= pack_version(20, 0, 0, 4)) and (ctx.user_version <= 11))) and (ctx.user_version >= 3):
            self.bs_header = BSStreamHeader.read(stream, ctx)
        if ctx.version >= pack_version(30, 0, 0, 0):
            self.metadata = ByteArray.read(stream, ctx)
        if ctx.version >= pack_version(5, 0, 0, 1):
            self.num_block_types = read_u16(stream)
        if (ctx.version >= pack_version(5, 0, 0, 1)) and (self.version != pack_version(20, 3, 1, 2)):
            self.block_types = [SizedString.read(stream, ctx) for _ in range(int(self.num_block_types))]
        if (ctx.version >= pack_version(20, 3, 1, 2)) and (ctx.version <= pack_version(20, 3, 1, 2)):
            self.block_type_hashes = read_array_u32(stream, int(self.num_block_types))
        if ctx.version >= pack_version(5, 0, 0, 1):
            self.block_type_index = [read_u16(stream) for _ in range(int(self.num_blocks))]
        if ctx.version >= pack_version(20, 2, 0, 5):
            self.block_size = read_array_u32(stream, int(self.num_blocks))
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.num_strings = read_u32(stream)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.max_string_length = read_u32(stream)
        if ctx.version >= pack_version(20, 1, 0, 1):
            self.strings = [SizedString.read(stream, ctx) for _ in range(int(self.num_strings))]
        if ctx.version >= pack_version(5, 0, 0, 6):
            self.num_groups = read_u32(stream)
        if ctx.version >= pack_version(5, 0, 0, 6):
            self.groups = read_array_u32(stream, int(self.num_groups))
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        # CODEGEN-TODO: unsupported basic write 'HeaderString'
        if ctx.version <= pack_version(3, 1, 0, 0):
            # CODEGEN-TODO: unsupported basic array write 'LineString'
            pass
        if ctx.version >= pack_version(3, 1, 0, 1):
            write_u32(stream, self.version)
        if ctx.version >= pack_version(20, 0, 0, 3):
            write_u8(stream, self.endian_type)
        if ctx.version >= pack_version(10, 0, 1, 8):
            write_u32(stream, self.user_version)
        if ctx.version >= pack_version(3, 1, 0, 1):
            write_u32(stream, self.num_blocks)
        if (ctx.version == pack_version(10, 0, 1, 2)) or ((ctx.version == pack_version(20, 2, 0, 7)) or (ctx.version == pack_version(20, 0, 0, 5)) or ((ctx.version >= pack_version(10, 1, 0, 0)) and (ctx.version <= pack_version(20, 0, 0, 4)) and (ctx.user_version <= 11))) and (ctx.user_version >= 3):
            self.bs_header.write(stream, ctx)
        if ctx.version >= pack_version(30, 0, 0, 0):
            self.metadata.write(stream, ctx)
        if ctx.version >= pack_version(5, 0, 0, 1):
            write_u16(stream, self.num_block_types)
        if (ctx.version >= pack_version(5, 0, 0, 1)) and (self.version != pack_version(20, 3, 1, 2)):
            for __v in self.block_types:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(20, 3, 1, 2)) and (ctx.version <= pack_version(20, 3, 1, 2)):
            write_array_u32(stream, self.block_type_hashes)
        if ctx.version >= pack_version(5, 0, 0, 1):
            for __v in self.block_type_index:
                write_u16(stream, __v)
        if ctx.version >= pack_version(20, 2, 0, 5):
            write_array_u32(stream, self.block_size)
        if ctx.version >= pack_version(20, 1, 0, 1):
            write_u32(stream, self.num_strings)
        if ctx.version >= pack_version(20, 1, 0, 1):
            write_u32(stream, self.max_string_length)
        if ctx.version >= pack_version(20, 1, 0, 1):
            for __v in self.strings:
                __v.write(stream, ctx)
        if ctx.version >= pack_version(5, 0, 0, 6):
            write_u32(stream, self.num_groups)
        if ctx.version >= pack_version(5, 0, 0, 6):
            write_array_u32(stream, self.groups)


@dataclass(slots=True)
class InterpBlendItem(Compound):
    """Interpolator item for array in NiBlendInterpolator."""

    interpolator: int = 0
    weight: float = 0.0
    normalized_weight: float = 0.0
    priority: int = 0
    priority: int = 0
    ease_spinner: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> InterpBlendItem:
        self = cls()
        self.interpolator = read_i32(stream)
        self.weight = read_f32(stream)
        self.normalized_weight = read_f32(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.priority = read_i32(stream)
        if ctx.version >= pack_version(10, 1, 0, 110):
            self.priority = read_u8(stream)
        self.ease_spinner = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_i32(stream, self.interpolator)
        write_f32(stream, self.weight)
        write_f32(stream, self.normalized_weight)
        if ctx.version <= pack_version(10, 1, 0, 109):
            write_i32(stream, self.priority)
        if ctx.version >= pack_version(10, 1, 0, 110):
            write_u8(stream, self.priority)
        write_f32(stream, self.ease_spinner)


@dataclass(slots=True)
class Key(Compound):
    """A generic key with support for interpolation. Type 1 is normal linear interpolation, type 2 has forward and backward tangents, and type 3 has tension, bias and continuity arguments. Note that color4 and byte always seem to be of type 1."""

    time: float = 0.0
    value: Any = None
    forward: Any = None
    backward: Any = None
    tbc: TBC | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Key:
        self = cls()
        self.time = read_f32(stream)
        # CODEGEN-TODO: unknown type '#T#' for field 'Value'
        if ctx.arg == 2:
            # CODEGEN-TODO: unknown type '#T#' for field 'Forward'
            pass
        if ctx.arg == 2:
            # CODEGEN-TODO: unknown type '#T#' for field 'Backward'
            pass
        if ctx.arg == 3:
            self.tbc = TBC.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.time)
        # CODEGEN-TODO: unknown type write '#T#'
        if ctx.arg == 2:
            # CODEGEN-TODO: unknown type write '#T#'
            pass
        if ctx.arg == 2:
            # CODEGEN-TODO: unknown type write '#T#'
            pass
        if ctx.arg == 3:
            self.tbc.write(stream, ctx)


@dataclass(slots=True)
class KeyGroup(Compound):
    """Array of vector keys (anything that can be interpolated, except rotations)."""

    num_keys: int = 0
    interpolation: int = 0
    keys: list[Key | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> KeyGroup:
        self = cls()
        self.num_keys = read_u32(stream)
        if self.num_keys != 0:
            self.interpolation = read_u32(stream)
        ctx.push_arg(self.interpolation)
        try:
            self.keys = [Key.read(stream, ctx) for _ in range(int(self.num_keys))]
        finally:
            ctx.pop_arg()
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_keys)
        if self.num_keys != 0:
            write_u32(stream, self.interpolation)
        ctx.push_arg(self.interpolation)
        try:
            for __v in self.keys:
                __v.write(stream, ctx)
        finally:
            ctx.pop_arg()


@dataclass(slots=True)
class LODRange(Compound):
    """The distance range where a specific level of detail applies."""

    near_extent: float = 0.0
    far_extent: float = 0.0
    unknown_ints: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> LODRange:
        self = cls()
        self.near_extent = read_f32(stream)
        self.far_extent = read_f32(stream)
        if ctx.version <= pack_version(3, 1):
            self.unknown_ints = read_array_u32(stream, 3)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.near_extent)
        write_f32(stream, self.far_extent)
        if ctx.version <= pack_version(3, 1):
            write_array_u32(stream, self.unknown_ints)


@dataclass(slots=True)
class LegacyExtraData(Compound):
    """Extra Data for pre-3.0 versions"""

    has_extra_data: bool = False
    extra_prop_name: SizedString | None = None
    extra_ref_id: int = 0
    extra_string: SizedString | None = None
    unknown_byte_1: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> LegacyExtraData:
        self = cls()
        self.has_extra_data = read_bool(stream)
        if self.has_extra_data:
            self.extra_prop_name = SizedString.read(stream, ctx)
        if self.has_extra_data:
            self.extra_ref_id = read_u32(stream)
        if self.has_extra_data:
            self.extra_string = SizedString.read(stream, ctx)
        self.unknown_byte_1 = read_u8(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_bool(stream, self.has_extra_data)
        if self.has_extra_data:
            self.extra_prop_name.write(stream, ctx)
        if self.has_extra_data:
            write_u32(stream, self.extra_ref_id)
        if self.has_extra_data:
            self.extra_string.write(stream, ctx)
        write_u8(stream, self.unknown_byte_1)


@dataclass(slots=True)
class MatchGroup(Compound):
    """Group of vertex indices of vertices that match."""

    num_vertices: int = 0
    vertex_indices: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> MatchGroup:
        self = cls()
        self.num_vertices = read_u16(stream)
        self.vertex_indices = read_array_u16(stream, int(self.num_vertices))
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.num_vertices)
        write_array_u16(stream, self.vertex_indices)


@dataclass(slots=True)
class MaterialData(Compound):
    has_shader: bool = False
    shader_name: string | None = None
    shader_extra_data: int = 0
    num_materials: int = 0
    material_name: list[int] = field(default_factory=list)
    material_extra_data: list[int] = field(default_factory=list)
    active_material: int = 0
    cyanide_unknown: int = 0
    worldshift_unknown: int = 0
    material_needs_update: bool = False

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> MaterialData:
        self = cls()
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)):
            self.has_shader = read_bool(stream)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)) and (self.has_shader):
            self.shader_name = string.read(stream, ctx)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)) and (self.has_shader):
            self.shader_extra_data = read_i32(stream)
        if ctx.version >= pack_version(20, 2, 0, 5):
            self.num_materials = read_u32(stream)
        if ctx.version >= pack_version(20, 2, 0, 5):
            self.material_name = [read_u32(stream) for _ in range(int(self.num_materials))]
        if ctx.version >= pack_version(20, 2, 0, 5):
            self.material_extra_data = [read_i32(stream) for _ in range(int(self.num_materials))]
        if ctx.version >= pack_version(20, 2, 0, 5):
            self.active_material = read_i32(stream)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(10, 2, 0, 0)) and (ctx.user_version == 1):
            self.cyanide_unknown = read_u8(stream)
        if (ctx.version >= pack_version(10, 3, 0, 1)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            self.worldshift_unknown = read_i32(stream)
        if ctx.version >= pack_version(20, 2, 0, 7):
            self.material_needs_update = read_bool(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)):
            write_bool(stream, self.has_shader)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)) and (self.has_shader):
            self.shader_name.write(stream, ctx)
        if (ctx.version >= pack_version(10, 0, 1, 0)) and (ctx.version <= pack_version(20, 1, 0, 3)) and (self.has_shader):
            write_i32(stream, self.shader_extra_data)
        if ctx.version >= pack_version(20, 2, 0, 5):
            write_u32(stream, self.num_materials)
        if ctx.version >= pack_version(20, 2, 0, 5):
            for __v in self.material_name:
                write_u32(stream, __v)
        if ctx.version >= pack_version(20, 2, 0, 5):
            for __v in self.material_extra_data:
                write_i32(stream, __v)
        if ctx.version >= pack_version(20, 2, 0, 5):
            write_i32(stream, self.active_material)
        if (ctx.version >= pack_version(10, 2, 0, 0)) and (ctx.version <= pack_version(10, 2, 0, 0)) and (ctx.user_version == 1):
            write_u8(stream, self.cyanide_unknown)
        if (ctx.version >= pack_version(10, 3, 0, 1)) and (ctx.version <= pack_version(10, 4, 0, 1)):
            write_i32(stream, self.worldshift_unknown)
        if ctx.version >= pack_version(20, 2, 0, 7):
            write_bool(stream, self.material_needs_update)


@dataclass(slots=True)
class Matrix22(Compound):
    """A 2x2 matrix of float values.  Stored in OpenGL column-major format."""

    m11: float = 0.0
    m21: float = 0.0
    m12: float = 0.0
    m22: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Matrix22:
        self = cls()
        self.m11 = read_f32(stream)
        self.m21 = read_f32(stream)
        self.m12 = read_f32(stream)
        self.m22 = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.m11)
        write_f32(stream, self.m21)
        write_f32(stream, self.m12)
        write_f32(stream, self.m22)


@dataclass(slots=True)
class Matrix33(Compound):
    """A 3x3 rotation matrix; M^T M=identity, det(M)=1.    Stored in OpenGL column-major format."""

    m11: float = 0.0
    m21: float = 0.0
    m31: float = 0.0
    m12: float = 0.0
    m22: float = 0.0
    m32: float = 0.0
    m13: float = 0.0
    m23: float = 0.0
    m33: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Matrix33:
        self = cls()
        self.m11 = read_f32(stream)
        self.m21 = read_f32(stream)
        self.m31 = read_f32(stream)
        self.m12 = read_f32(stream)
        self.m22 = read_f32(stream)
        self.m32 = read_f32(stream)
        self.m13 = read_f32(stream)
        self.m23 = read_f32(stream)
        self.m33 = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.m11)
        write_f32(stream, self.m21)
        write_f32(stream, self.m31)
        write_f32(stream, self.m12)
        write_f32(stream, self.m22)
        write_f32(stream, self.m32)
        write_f32(stream, self.m13)
        write_f32(stream, self.m23)
        write_f32(stream, self.m33)


@dataclass(slots=True)
class NiBound(Compound):
    """A sphere."""

    center: Vector3 | None = None
    radius: float = 0.0
    div2_aabb: NiBoundAABB | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiBound:
        self = cls()
        self.center = Vector3.read(stream, ctx)
        self.radius = read_f32(stream)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_aabb = NiBoundAABB.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.center.write(stream, ctx)
        write_f32(stream, self.radius)
        if (ctx.version >= pack_version(20, 3, 0, 9)) and (ctx.version <= pack_version(20, 3, 0, 9)) and (((ctx.user_version == 0x20000) or (ctx.user_version == 0x30000))):
            self.div2_aabb.write(stream, ctx)


@dataclass(slots=True)
class NiBoundAABB(Compound):
    """Divinity 2 specific NiBound extension."""

    num_corners: int = 0
    corners: list[Vector3 | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiBoundAABB:
        self = cls()
        self.num_corners = read_u16(stream)
        self.corners = [Vector3.read(stream, ctx) for _ in range(2)]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.num_corners)
        for __v in self.corners:
            __v.write(stream, ctx)


@dataclass(slots=True)
class NiPlane(Compound):
    """A plane."""

    normal: Vector3 | None = None
    constant: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiPlane:
        self = cls()
        self.normal = Vector3.read(stream, ctx)
        self.constant = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.normal.write(stream, ctx)
        write_f32(stream, self.constant)


@dataclass(slots=True)
class NiQuatTransform(Compound):
    translation: Vector3 | None = None
    rotation: Quaternion | None = None
    scale: float = 0.0
    trs_valid: list[bool] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiQuatTransform:
        self = cls()
        self.translation = Vector3.read(stream, ctx)
        self.rotation = Quaternion.read(stream, ctx)
        self.scale = read_f32(stream)
        if ctx.version <= pack_version(10, 1, 0, 109):
            self.trs_valid = [read_bool(stream) for _ in range(3)]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.translation.write(stream, ctx)
        self.rotation.write(stream, ctx)
        write_f32(stream, self.scale)
        if ctx.version <= pack_version(10, 1, 0, 109):
            for __v in self.trs_valid:
                write_bool(stream, __v)


@dataclass(slots=True)
class NiTransform(Compound):
    rotation: Matrix33 | None = None
    translation: Vector3 | None = None
    scale: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiTransform:
        self = cls()
        self.rotation = Matrix33.read(stream, ctx)
        self.translation = Vector3.read(stream, ctx)
        self.scale = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.rotation.write(stream, ctx)
        self.translation.write(stream, ctx)
        write_f32(stream, self.scale)


@dataclass(slots=True)
class PixelFormatComponent(Compound):
    type: int = 0
    convention: int = 0
    bits_per_channel: int = 0
    is_signed: bool = False

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> PixelFormatComponent:
        self = cls()
        self.type = read_u32(stream)
        self.convention = read_u32(stream)
        self.bits_per_channel = read_u8(stream)
        self.is_signed = read_bool(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.type)
        write_u32(stream, self.convention)
        write_u8(stream, self.bits_per_channel)
        write_bool(stream, self.is_signed)


@dataclass(slots=True)
class QuatKey(Compound):
    """A special version of the key type used for quaternions. Never has tangents. #T# should always be Quaternion."""

    time: float = 0.0
    time: float = 0.0
    value: Any = None
    tbc: TBC | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> QuatKey:
        self = cls()
        if ctx.version <= pack_version(10, 1, 0, 0):
            self.time = read_f32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.arg != 4):
            self.time = read_f32(stream)
        if ctx.arg != 4:
            # CODEGEN-TODO: unknown type '#T#' for field 'Value'
            pass
        if ctx.arg == 3:
            self.tbc = TBC.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version <= pack_version(10, 1, 0, 0):
            write_f32(stream, self.time)
        if (ctx.version >= pack_version(10, 1, 0, 106)) and (ctx.arg != 4):
            write_f32(stream, self.time)
        if ctx.arg != 4:
            # CODEGEN-TODO: unknown type write '#T#'
            pass
        if ctx.arg == 3:
            self.tbc.write(stream, ctx)


@dataclass(slots=True)
class Quaternion(Compound):
    """A quaternion."""

    w: float = 0.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Quaternion:
        self = cls()
        self.w = read_f32(stream)
        self.x = read_f32(stream)
        self.y = read_f32(stream)
        self.z = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.w)
        write_f32(stream, self.x)
        write_f32(stream, self.y)
        write_f32(stream, self.z)


@dataclass(slots=True)
class ShaderTexDesc(Compound):
    """NiTexturingProperty::ShaderMap. Shader texture description."""

    has_map: bool = False
    map: TexDesc | None = None
    map_id: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> ShaderTexDesc:
        self = cls()
        self.has_map = read_bool(stream)
        if self.has_map:
            self.map = TexDesc.read(stream, ctx)
        if self.has_map:
            self.map_id = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_bool(stream, self.has_map)
        if self.has_map:
            self.map.write(stream, ctx)
        if self.has_map:
            write_u32(stream, self.map_id)


@dataclass(slots=True)
class SizedString(Compound):
    """A string of given length."""

    length: int = 0
    value: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> SizedString:
        self = cls()
        self.length = read_u32(stream)
        self.value = [read_u8(stream) for _ in range(int(self.length))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.length)
        for __v in self.value:
            write_u8(stream, __v)


@dataclass(slots=True)
class SizedString16(Compound):
    """A string of given length, using a ushort to store string length."""

    length: int = 0
    value: list[int] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> SizedString16:
        self = cls()
        self.length = read_u16(stream)
        self.value = [read_u8(stream) for _ in range(int(self.length))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.length)
        for __v in self.value:
            write_u8(stream, __v)


@dataclass(slots=True)
class SkinPartition(Compound):
    """Skinning data for a submesh, optimized for hardware skinning. Part of NiSkinPartition."""

    num_vertices: int = 0
    num_triangles: int = 0
    num_bones: int = 0
    num_strips: int = 0
    num_weights_per_vertex: int = 0
    bones: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    has_vertex_map: bool = False
    vertex_map: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    vertex_map: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    has_vertex_weights: bool = False
    vertex_weights: list[Any] = field(default_factory=list)
    vertex_weights: list[Any] = field(default_factory=list)
    strip_lengths: npt.NDArray[Any] = field(default_factory=lambda: np.empty(0))
    has_faces: bool = False
    strips: list[Any] = field(default_factory=list)
    strips: list[Any] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    triangles: list[Triangle | None] = field(default_factory=list)
    has_bone_indices: bool = False
    bone_indices: list[Any] = field(default_factory=list)
    lod_level: int = 0
    global_vb: bool = False
    vertex_desc: BSVertexDesc | None = field(default_factory=BSVertexDesc)
    triangles_copy: list[Triangle | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> SkinPartition:
        self = cls()
        self.num_vertices = read_u16(stream)
        self.num_triangles = read_u16(stream)
        self.num_bones = read_u16(stream)
        self.num_strips = read_u16(stream)
        self.num_weights_per_vertex = read_u16(stream)
        self.bones = read_array_u16(stream, int(self.num_bones))
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.has_vertex_map = read_bool(stream)
        if ctx.version <= pack_version(10, 0, 1, 2):
            self.vertex_map = read_array_u16(stream, int(self.num_vertices))
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_vertex_map):
            self.vertex_map = read_array_u16(stream, int(self.num_vertices))
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.has_vertex_weights = read_bool(stream)
        if ctx.version <= pack_version(10, 0, 1, 2):
            self.vertex_weights = [read_array_f32(stream, int(self.num_weights_per_vertex)) for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_vertex_weights):
            self.vertex_weights = [read_array_f32(stream, int(self.num_weights_per_vertex)) for _ in range(int(self.num_vertices))]
        self.strip_lengths = read_array_u16(stream, int(self.num_strips))
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.has_faces = read_bool(stream)
        if (ctx.version <= pack_version(10, 0, 1, 2)) and (self.num_strips != 0):
            self.strips = [read_array_u16(stream, int(self.strip_lengths[__i])) for __i in range(int(self.num_strips))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_faces) and (self.num_strips != 0)):
            self.strips = [read_array_u16(stream, int(self.strip_lengths[__i])) for __i in range(int(self.num_strips))]
        if (ctx.version <= pack_version(10, 0, 1, 2)) and (self.num_strips == 0):
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_faces) and (self.num_strips == 0)):
            self.triangles = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        self.has_bone_indices = read_bool(stream)
        if self.has_bone_indices:
            self.bone_indices = [[read_u8(stream) for _ in range(int(self.num_weights_per_vertex))] for _ in range(int(self.num_vertices))]
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.lod_level = read_u8(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            self.global_vb = read_bool(stream)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.vertex_desc = BSVertexDesc.read(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.triangles_copy = [Triangle.read(stream, ctx) for _ in range(int(self.num_triangles))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.num_vertices)
        write_u16(stream, self.num_triangles)
        write_u16(stream, self.num_bones)
        write_u16(stream, self.num_strips)
        write_u16(stream, self.num_weights_per_vertex)
        write_array_u16(stream, self.bones)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_bool(stream, self.has_vertex_map)
        if ctx.version <= pack_version(10, 0, 1, 2):
            write_array_u16(stream, self.vertex_map)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_vertex_map):
            write_array_u16(stream, self.vertex_map)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_bool(stream, self.has_vertex_weights)
        if ctx.version <= pack_version(10, 0, 1, 2):
            for __row in self.vertex_weights:
                write_array_f32(stream, __row)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_vertex_weights):
            for __row in self.vertex_weights:
                write_array_f32(stream, __row)
        write_array_u16(stream, self.strip_lengths)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_bool(stream, self.has_faces)
        if (ctx.version <= pack_version(10, 0, 1, 2)) and (self.num_strips != 0):
            for __row in self.strips:
                write_array_u16(stream, __row)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_faces) and (self.num_strips != 0)):
            for __row in self.strips:
                write_array_u16(stream, __row)
        if (ctx.version <= pack_version(10, 0, 1, 2)) and (self.num_strips == 0):
            for __v in self.triangles:
                __v.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and ((self.has_faces) and (self.num_strips == 0)):
            for __v in self.triangles:
                __v.write(stream, ctx)
        write_bool(stream, self.has_bone_indices)
        if self.has_bone_indices:
            for __row in self.bone_indices:
                for __v in __row:
                    write_u8(stream, __v)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_u8(stream, self.lod_level)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version > 34)):
            write_bool(stream, self.global_vb)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            self.vertex_desc.write(stream, ctx)
        if (ctx.version >= pack_version(20, 2, 0, 7)) and (ctx.version <= pack_version(20, 2, 0, 7)) and ((ctx.bs_version == 100)):
            for __v in self.triangles_copy:
                __v.write(stream, ctx)


@dataclass(slots=True)
class StringPalette(Compound):
    """A list of \\0 terminated strings."""

    palette: SizedString | None = None
    length: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> StringPalette:
        self = cls()
        self.palette = SizedString.read(stream, ctx)
        self.length = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        self.palette.write(stream, ctx)
        write_u32(stream, self.length)


@dataclass(slots=True)
class TBC(Compound):
    """Tension, bias, continuity."""

    t: float = 0.0
    b: float = 0.0
    c: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TBC:
        self = cls()
        self.t = read_f32(stream)
        self.b = read_f32(stream)
        self.c = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.t)
        write_f32(stream, self.b)
        write_f32(stream, self.c)


@dataclass(slots=True)
class TexCoord(Compound):
    """Texture coordinates (u,v). As in OpenGL; image origin is in the lower left corner."""

    u: float = 0.0
    v: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TexCoord:
        self = cls()
        self.u = read_f32(stream)
        self.v = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.u)
        write_f32(stream, self.v)


@dataclass(slots=True)
class TexDesc(Compound):
    """NiTexturingProperty::Map. Texture description."""

    image: int = 0
    source: int = 0
    clamp_mode: int = 0
    filter_mode: int = 0
    flags: TexturingMapFlags | None = field(default_factory=TexturingMapFlags)
    max_anisotropy: int = 0
    uv_set: int = 0
    ps2_l: int = 0
    ps2_k: int = 0
    unknown_short_1: int = 0
    has_texture_transform: bool = False
    translation: TexCoord | None = None
    scale: TexCoord | None = None
    rotation: float = 0.0
    transform_method: int = 0
    center: TexCoord | None = None

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TexDesc:
        self = cls()
        if ctx.version <= pack_version(3, 1):
            self.image = read_i32(stream)
        if ctx.version >= pack_version(3, 3, 0, 13):
            self.source = read_i32(stream)
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.clamp_mode = read_u32(stream)
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.filter_mode = read_u32(stream)
        if ctx.version >= pack_version(20, 1, 0, 3):
            self.flags = TexturingMapFlags.read(stream, ctx)
        if ctx.version >= pack_version(20, 5, 0, 4):
            self.max_anisotropy = read_u16(stream)
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.uv_set = read_u32(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.ps2_l = read_i16(stream)
        if ctx.version <= pack_version(10, 4, 0, 1):
            self.ps2_k = read_i16(stream)
        if ctx.version <= pack_version(4, 1, 0, 12):
            self.unknown_short_1 = read_u16(stream)
        if ctx.version >= pack_version(10, 1, 0, 0):
            self.has_texture_transform = read_bool(stream)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.translation = TexCoord.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.scale = TexCoord.read(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.rotation = read_f32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.transform_method = read_u32(stream)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.center = TexCoord.read(stream, ctx)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version <= pack_version(3, 1):
            write_i32(stream, self.image)
        if ctx.version >= pack_version(3, 3, 0, 13):
            write_i32(stream, self.source)
        if ctx.version <= pack_version(20, 0, 0, 5):
            write_u32(stream, self.clamp_mode)
        if ctx.version <= pack_version(20, 0, 0, 5):
            write_u32(stream, self.filter_mode)
        if ctx.version >= pack_version(20, 1, 0, 3):
            self.flags.write(stream, ctx)
        if ctx.version >= pack_version(20, 5, 0, 4):
            write_u16(stream, self.max_anisotropy)
        if ctx.version <= pack_version(20, 0, 0, 5):
            write_u32(stream, self.uv_set)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_i16(stream, self.ps2_l)
        if ctx.version <= pack_version(10, 4, 0, 1):
            write_i16(stream, self.ps2_k)
        if ctx.version <= pack_version(4, 1, 0, 12):
            write_u16(stream, self.unknown_short_1)
        if ctx.version >= pack_version(10, 1, 0, 0):
            write_bool(stream, self.has_texture_transform)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.translation.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.scale.write(stream, ctx)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            write_f32(stream, self.rotation)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            write_u32(stream, self.transform_method)
        if (ctx.version >= pack_version(10, 1, 0, 0)) and (self.has_texture_transform):
            self.center.write(stream, ctx)


@dataclass(slots=True)
class Triangle(Compound):
    """List of three vertex indices."""

    v1: int = 0
    v2: int = 0
    v3: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Triangle:
        self = cls()
        self.v1 = read_u16(stream)
        self.v2 = read_u16(stream)
        self.v3 = read_u16(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u16(stream, self.v1)
        write_u16(stream, self.v2)
        write_u16(stream, self.v3)


@dataclass(slots=True)
class UnionBV(Compound):
    num_bv: int = 0
    bounding_volumes: list[BoundingVolume | None] = field(default_factory=list)

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> UnionBV:
        self = cls()
        self.num_bv = read_u32(stream)
        self.bounding_volumes = [BoundingVolume.read(stream, ctx) for _ in range(int(self.num_bv))]
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_u32(stream, self.num_bv)
        for __v in self.bounding_volumes:
            __v.write(stream, ctx)


@dataclass(slots=True)
class Vector3(Compound):
    """A vector in 3D space (x,y,z)."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Vector3:
        self = cls()
        self.x = read_f32(stream)
        self.y = read_f32(stream)
        self.z = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.x)
        write_f32(stream, self.y)
        write_f32(stream, self.z)


@dataclass(slots=True)
class Vector4(Compound):
    """A 4-dimensional vector."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> Vector4:
        self = cls()
        self.x = read_f32(stream)
        self.y = read_f32(stream)
        self.z = read_f32(stream)
        self.w = read_f32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        write_f32(stream, self.x)
        write_f32(stream, self.y)
        write_f32(stream, self.z)
        write_f32(stream, self.w)


@dataclass(slots=True)
class string(Compound):
    """A string type."""

    string: SizedString | None = None
    index: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> string:
        self = cls()
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.string = SizedString.read(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 3):
            self.index = read_u32(stream)
        return self

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        if ctx.version <= pack_version(20, 0, 0, 5):
            self.string.write(stream, ctx)
        if ctx.version >= pack_version(20, 1, 0, 3):
            write_u32(stream, self.index)
