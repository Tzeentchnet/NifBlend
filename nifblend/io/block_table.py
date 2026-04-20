"""High-level NIF read/write loop: header + block table + footer.

Reads / writes a complete NIF as a flat :class:`BlockTable` -- the header
dataclass, an ordered list of decoded :class:`Block` instances, and the
trailing :class:`Footer`. Block references between blocks are preserved as
raw u32 indices into ``BlockTable.blocks``; resolving them into Blender
semantics is the bridge layer's job (Phase 2 step 8+).

Why a flat table and not a tree?

NIF blocks form a graph (with cycles, in pathological cases involving
controller chains). Holding the on-disk u32 indices unmodified keeps
round-tripping byte-faithful: the writer can re-emit ``block_size`` /
``block_type_index`` arrays without re-deriving any cross-references.

Why a two-pass write?

The header carries a ``block_size`` array (from version 20.2.0.5) that
stores each block's serialised size. We don't know those sizes until each
block is actually written. Easiest correct fix: serialise each block to an
in-memory buffer first, *then* write the header (now with finalised
``block_size`` values) followed by the concatenated payload. NIF files
are bounded by mod-author authoring tool limits (a few hundred MiB at the
extreme end), so the temporary memory cost is acceptable.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import IO

import numpy as np

from nifblend.format import generated as _gen
from nifblend.format.base import Block, ReadContext
from nifblend.format.generated.structs import Footer, Header, SizedString

from .header import read_nif_header, write_nif_header

__all__ = ["BlockTable", "read_nif", "write_nif"]


@dataclass(slots=True)
class BlockTable:
    """Flat representation of a parsed NIF file.

    ``blocks[i]`` corresponds to header.block_type_index[i]; raw u32 cross-
    references inside blocks (e.g. ``BSTriShape.skin``) index into this list
    as-is.
    """

    header: Header
    blocks: list[Block] = field(default_factory=list)
    footer: Footer = field(default_factory=Footer)
    ctx: ReadContext = field(default_factory=ReadContext)

    def block_type_name(self, index: int) -> str:
        """Return the on-disk schema name for the block at ``index``."""
        type_idx = self.header.block_type_index[index]
        return _sized_string_to_str(self.header.block_types[type_idx])


# ---- helpers ---------------------------------------------------------------


def _sized_string_to_str(s: SizedString | None) -> str:
    """Decode a SizedString's byte payload into a Python ``str``.

    NIF block-type strings are 7-bit ASCII; ``latin-1`` is a safe superset
    that round-trips arbitrary bytes losslessly so we don't lose data on a
    file with garbled metadata.
    """
    if s is None:
        raise ValueError("SizedString is None")
    return bytes(s.value).decode("latin-1")


def _str_to_sized_string(value: str) -> SizedString:
    payload = value.encode("latin-1")
    return SizedString(length=len(payload), value=list(payload))


def _resolve_block_class(name: str) -> type[Block]:
    """Resolve an on-disk block-type name to a generated :class:`Block` subclass.

    Mirrors the codegen's name-collapsing rule: ``BSSkin::Instance`` on disk
    becomes the Python class ``BSSkinInstance``. See ``tools/codegen/emit.py``.
    """
    py_name = name.replace("::", "")
    cls = getattr(_gen, py_name, None)
    if cls is None:
        raise KeyError(
            f"block type {name!r} (Python class {py_name!r}) is not in the "
            f"generated schema layer; widen the codegen whitelist or extend "
            f"the closure walker"
        )
    if not isinstance(cls, type) or not issubclass(cls, Block):
        raise TypeError(f"{py_name!r} resolved to {cls!r}, not a Block subclass")
    return cls


# ---- read ------------------------------------------------------------------


def read_nif(stream: IO[bytes]) -> BlockTable:
    """Parse a complete NIF file from ``stream`` into a :class:`BlockTable`."""
    header, ctx = read_nif_header(stream)

    blocks: list[Block] = []
    for i in range(header.num_blocks):
        type_name = _sized_string_to_str(header.block_types[header.block_type_index[i]])
        cls = _resolve_block_class(type_name)
        start = stream.tell()
        blk = cls.read(stream, ctx)
        # Cross-check against the header's recorded block_size when present.
        # This is the recovery hook called out in ROADMAP step 6 ("block-size
        # table tells us where each block ends, so we can recover from a
        # malformed block"). For now we surface a hard error -- silent
        # recovery requires tests we don't have yet.
        if header.block_size.size:
            consumed = stream.tell() - start
            expected = int(header.block_size[i])
            if consumed != expected:
                raise ValueError(
                    f"block {i} ({type_name!r}) read {consumed} bytes; "
                    f"header.block_size[{i}] expected {expected}"
                )
        blocks.append(blk)

    footer = Footer.read(stream, ctx)
    return BlockTable(header=header, blocks=blocks, footer=footer, ctx=ctx)


# ---- write -----------------------------------------------------------------


def _serialise_block(block: Block, ctx: ReadContext) -> bytes:
    buf = io.BytesIO()
    block.write(buf, ctx)
    return buf.getvalue()


def write_nif(stream: IO[bytes], table: BlockTable) -> None:
    """Serialise ``table`` to ``stream``.

    Re-derives ``header.num_blocks``, ``header.block_types``,
    ``header.num_block_types``, ``header.block_type_index`` and
    ``header.block_size`` from the ``blocks`` list so callers can mutate
    blocks freely without keeping the bookkeeping arrays in sync. Other
    header fields (``user_version``, ``bs_header``, ``strings``, ...) are
    written verbatim.
    """
    ctx = table.ctx
    header = table.header

    # ---- pass 1: serialise every block, learn sizes & dedup type names ----
    payloads: list[bytes] = []
    type_index_per_block: list[int] = []
    type_name_to_idx: dict[str, int] = {}
    block_types: list[SizedString] = []

    for blk in table.blocks:
        # Class name → schema name (inverse of `_resolve_block_class`).
        # The codegen collapses ``::`` so we cannot recover the original
        # namespaced form from the class name alone. Use the on-disk strings
        # already in ``header.block_types`` whenever we can; for newly
        # appended blocks fall back to the Python class name (acceptable for
        # every type emitted today since only ``BSSkin::Instance`` had ``::``
        # on disk and round-trips happen via the original strings).
        py_name = type(blk).__name__

        idx = type_name_to_idx.get(py_name)
        if idx is None:
            # Prefer an existing on-disk spelling if it collapses to the same
            # Python class (preserves ``BSSkin::Instance``-style namespaces).
            preserved = _find_disk_name(header, py_name)
            disk_name = preserved if preserved is not None else py_name
            idx = len(block_types)
            type_name_to_idx[py_name] = idx
            block_types.append(_str_to_sized_string(disk_name))
        type_index_per_block.append(idx)
        payloads.append(_serialise_block(blk, ctx))

    header.num_blocks = len(table.blocks)
    header.num_block_types = len(block_types)
    header.block_types = list(block_types)
    header.block_type_index = type_index_per_block
    header.block_size = np.asarray([len(p) for p in payloads], dtype=np.uint32)

    # ---- pass 2: write header + payloads + footer -------------------------
    write_nif_header(stream, header, ctx)
    for payload in payloads:
        stream.write(payload)
    table.footer.write(stream, ctx)


def _find_disk_name(header: Header, py_name: str) -> str | None:
    """Look up ``header.block_types`` for an entry that collapses to ``py_name``.

    Lets the writer preserve ``BSSkin::Instance`` (and any future
    namespaced types) on round-trip without forcing the BlockTable to
    carry a parallel "original disk name" array.
    """
    for s in header.block_types:
        if s is None:
            continue
        try:
            disk = _sized_string_to_str(s)
        except ValueError:
            continue
        if disk.replace("::", "") == py_name:
            return disk
    return None
