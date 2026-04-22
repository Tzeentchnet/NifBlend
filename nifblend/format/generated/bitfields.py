"""Generated NIF bitfields (multi-bit packed integers).

DO NOT EDIT — regenerate via `python -m tools.codegen`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import IO

from nifblend.format.base import Compound, ReadContext
from nifblend.format.primitives import (
    read_u8,
    read_u16,
    read_u32,
    read_u64,
    write_u8,
    write_u16,
    write_u32,
    write_u64,
)

__all__ = ['AlphaFlags', 'BSGeometryDataFlags', 'BSVertexDesc', 'NiGeometryDataFlags', 'TexturingFlags', 'TexturingMapFlags', 'TimeControllerFlags']


@dataclass(slots=True)
class AlphaFlags(Compound):
    """Flags for NiAlphaProperty"""

    alpha_blend: int = 0
    source_blend_mode: int = 0
    destination_blend_mode: int = 0
    alpha_test: int = 0
    test_func: int = 0
    no_sorter: int = 0
    clone_unique: int = 0
    editor_alpha_threshold: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> AlphaFlags:
        raw = read_u16(stream)
        return cls(
            alpha_blend=(raw >> 0) & 0x1,
            source_blend_mode=(raw >> 1) & 0xF,
            destination_blend_mode=(raw >> 5) & 0xF,
            alpha_test=(raw >> 9) & 0x1,
            test_func=(raw >> 10) & 0x7,
            no_sorter=(raw >> 13) & 0x1,
            clone_unique=(raw >> 14) & 0x1,
            editor_alpha_threshold=(raw >> 15) & 0x1,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.alpha_blend & 0x1) << 0
        raw |= (self.source_blend_mode & 0xF) << 1
        raw |= (self.destination_blend_mode & 0xF) << 5
        raw |= (self.alpha_test & 0x1) << 9
        raw |= (self.test_func & 0x7) << 10
        raw |= (self.no_sorter & 0x1) << 13
        raw |= (self.clone_unique & 0x1) << 14
        raw |= (self.editor_alpha_threshold & 0x1) << 15
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.alpha_blend & 0x1) << 0
        raw |= (self.source_blend_mode & 0xF) << 1
        raw |= (self.destination_blend_mode & 0xF) << 5
        raw |= (self.alpha_test & 0x1) << 9
        raw |= (self.test_func & 0x7) << 10
        raw |= (self.no_sorter & 0x1) << 13
        raw |= (self.clone_unique & 0x1) << 14
        raw |= (self.editor_alpha_threshold & 0x1) << 15
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class BSGeometryDataFlags(Compound):
    has_uv: int = 0
    havok_material: int = 0
    has_tangents: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSGeometryDataFlags:
        raw = read_u16(stream)
        return cls(
            has_uv=(raw >> 0) & 0x3F,
            havok_material=(raw >> 6) & 0x3F,
            has_tangents=(raw >> 12) & 0x1,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.has_uv & 0x3F) << 0
        raw |= (self.havok_material & 0x3F) << 6
        raw |= (self.has_tangents & 0x1) << 12
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.has_uv & 0x3F) << 0
        raw |= (self.havok_material & 0x3F) << 6
        raw |= (self.has_tangents & 0x1) << 12
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class BSVertexDesc(Compound):
    vertex_data_size: int = 0
    dynamic_vertex_size: int = 0
    uv1_offset: int = 0
    uv2_offset: int = 0
    normal_offset: int = 0
    tangent_offset: int = 0
    color_offset: int = 0
    skinning_data_offset: int = 0
    landscape_data_offset: int = 0
    eye_data_offset: int = 0
    unused_01: int = 0
    vertex_attributes: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> BSVertexDesc:
        raw = read_u64(stream)
        return cls(
            vertex_data_size=(raw >> 0) & 0xF,
            dynamic_vertex_size=(raw >> 4) & 0xF,
            uv1_offset=(raw >> 8) & 0xF,
            uv2_offset=(raw >> 12) & 0xF,
            normal_offset=(raw >> 16) & 0xF,
            tangent_offset=(raw >> 20) & 0xF,
            color_offset=(raw >> 24) & 0xF,
            skinning_data_offset=(raw >> 28) & 0xF,
            landscape_data_offset=(raw >> 32) & 0xF,
            eye_data_offset=(raw >> 36) & 0xF,
            unused_01=(raw >> 40) & 0xF,
            vertex_attributes=(raw >> 44) & 0xFFF,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.vertex_data_size & 0xF) << 0
        raw |= (self.dynamic_vertex_size & 0xF) << 4
        raw |= (self.uv1_offset & 0xF) << 8
        raw |= (self.uv2_offset & 0xF) << 12
        raw |= (self.normal_offset & 0xF) << 16
        raw |= (self.tangent_offset & 0xF) << 20
        raw |= (self.color_offset & 0xF) << 24
        raw |= (self.skinning_data_offset & 0xF) << 28
        raw |= (self.landscape_data_offset & 0xF) << 32
        raw |= (self.eye_data_offset & 0xF) << 36
        raw |= (self.unused_01 & 0xF) << 40
        raw |= (self.vertex_attributes & 0xFFF) << 44
        write_u64(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.vertex_data_size & 0xF) << 0
        raw |= (self.dynamic_vertex_size & 0xF) << 4
        raw |= (self.uv1_offset & 0xF) << 8
        raw |= (self.uv2_offset & 0xF) << 12
        raw |= (self.normal_offset & 0xF) << 16
        raw |= (self.tangent_offset & 0xF) << 20
        raw |= (self.color_offset & 0xF) << 24
        raw |= (self.skinning_data_offset & 0xF) << 28
        raw |= (self.landscape_data_offset & 0xF) << 32
        raw |= (self.eye_data_offset & 0xF) << 36
        raw |= (self.unused_01 & 0xF) << 40
        raw |= (self.vertex_attributes & 0xFFF) << 44
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class NiGeometryDataFlags(Compound):
    num_uv_sets: int = 0
    havok_material: int = 0
    nbt_method: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> NiGeometryDataFlags:
        raw = read_u16(stream)
        return cls(
            num_uv_sets=(raw >> 0) & 0x3F,
            havok_material=(raw >> 6) & 0x3F,
            nbt_method=(raw >> 12) & 0x3,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.num_uv_sets & 0x3F) << 0
        raw |= (self.havok_material & 0x3F) << 6
        raw |= (self.nbt_method & 0x3) << 12
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.num_uv_sets & 0x3F) << 0
        raw |= (self.havok_material & 0x3F) << 6
        raw |= (self.nbt_method & 0x3) << 12
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class TexturingFlags(Compound):
    """Flags for NiTexturingProperty"""

    multitexture: int = 0
    apply_mode: int = 0
    decal_count: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TexturingFlags:
        raw = read_u16(stream)
        return cls(
            multitexture=(raw >> 0) & 0x1,
            apply_mode=(raw >> 1) & 0x7,
            decal_count=(raw >> 4) & 0xFF,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.multitexture & 0x1) << 0
        raw |= (self.apply_mode & 0x7) << 1
        raw |= (self.decal_count & 0xFF) << 4
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.multitexture & 0x1) << 0
        raw |= (self.apply_mode & 0x7) << 1
        raw |= (self.decal_count & 0xFF) << 4
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class TexturingMapFlags(Compound):
    """Flags for NiTexturingProperty"""

    texture_index: int = 0
    filter_mode: int = 0
    clamp_mode: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TexturingMapFlags:
        raw = read_u16(stream)
        return cls(
            texture_index=(raw >> 0) & 0xFF,
            filter_mode=(raw >> 8) & 0xF,
            clamp_mode=(raw >> 12) & 0xF,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.texture_index & 0xFF) << 0
        raw |= (self.filter_mode & 0xF) << 8
        raw |= (self.clamp_mode & 0xF) << 12
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.texture_index & 0xFF) << 0
        raw |= (self.filter_mode & 0xF) << 8
        raw |= (self.clamp_mode & 0xF) << 12
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)


@dataclass(slots=True)
class TimeControllerFlags(Compound):
    """Flags for NiTimeController"""

    anim_type: int = 0
    cycle_type: int = 0
    active: int = 0
    play_backwards: int = 0
    manager_controlled: int = 0
    compute_scaled_time: int = 0
    forced_update: int = 0

    @classmethod
    def read(cls, stream: IO[bytes], ctx: ReadContext) -> TimeControllerFlags:
        raw = read_u16(stream)
        return cls(
            anim_type=(raw >> 0) & 0x1,
            cycle_type=(raw >> 1) & 0x3,
            active=(raw >> 3) & 0x1,
            play_backwards=(raw >> 4) & 0x1,
            manager_controlled=(raw >> 5) & 0x1,
            compute_scaled_time=(raw >> 6) & 0x1,
            forced_update=(raw >> 7) & 0x1,
        )

    def write(self, stream: IO[bytes], ctx: ReadContext) -> None:
        raw = 0
        raw |= (self.anim_type & 0x1) << 0
        raw |= (self.cycle_type & 0x3) << 1
        raw |= (self.active & 0x1) << 3
        raw |= (self.play_backwards & 0x1) << 4
        raw |= (self.manager_controlled & 0x1) << 5
        raw |= (self.compute_scaled_time & 0x1) << 6
        raw |= (self.forced_update & 0x1) << 7
        write_u16(stream, raw)

    def _packed(self) -> int:
        raw = 0
        raw |= (self.anim_type & 0x1) << 0
        raw |= (self.cycle_type & 0x3) << 1
        raw |= (self.active & 0x1) << 3
        raw |= (self.play_backwards & 0x1) << 4
        raw |= (self.manager_controlled & 0x1) << 5
        raw |= (self.compute_scaled_time & 0x1) << 6
        raw |= (self.forced_update & 0x1) << 7
        return raw

    def __int__(self) -> int:
        return self._packed()

    def __index__(self) -> int:
        return self._packed()

    def __rshift__(self, n: int) -> int:
        return self._packed() >> int(n)

    def __lshift__(self, n: int) -> int:
        return self._packed() << int(n)

    def __and__(self, n: int) -> int:
        return self._packed() & int(n)

    def __or__(self, n: int) -> int:
        return self._packed() | int(n)
