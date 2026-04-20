"""Buffered NIF file writer.

Mirror of :mod:`nifblend.io.reader`. Wraps :class:`io.BufferedWriter` and
provides the minimal ``IO[bytes]`` surface the generated ``Block.write``
methods (and :mod:`nifblend.format.primitives`) require, plus a couple of
NIF-specific helpers used by the block-table writer (``patch_u32`` for
back-filling block sizes once a block is fully serialised).
"""

from __future__ import annotations

import io
import os
import struct
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Final

__all__ = ["NifWriter", "open_nif_writer"]


_DEFAULT_BUFFER: Final[int] = 1 << 20
_U32 = struct.Struct("<I")


class NifWriter:
    """Buffered, seekable, bytes-only sink for NIF output."""

    __slots__ = ("_owned", "_path", "_stream")

    def __init__(
        self,
        stream: BinaryIO,
        *,
        owned: bool = False,
        path: Path | None = None,
    ) -> None:
        if not stream.writable():
            raise ValueError("NifWriter requires a writable binary stream")
        if not stream.seekable():
            raise ValueError("NifWriter requires a seekable stream (block-size patching)")
        self._stream = stream
        self._owned = owned
        self._path = path

    # ---- IO[bytes] surface used by primitives / codegen --------------------

    def write(self, data: bytes) -> int:
        return self._stream.write(data)

    def tell(self) -> int:
        return self._stream.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        return self._stream.seek(offset, whence)

    def flush(self) -> None:
        self._stream.flush()

    # ---- NIF-specific helpers ---------------------------------------------

    @property
    def path(self) -> Path | None:
        return self._path

    def reserve_u32(self) -> int:
        """Write a placeholder u32 and return its absolute offset.

        Used by the block-table writer: emit a zero where the block size
        belongs, serialise the block, then call :meth:`patch_u32` to back-fill
        the real size.
        """
        offset = self._stream.tell()
        self._stream.write(b"\x00\x00\x00\x00")
        return offset

    def patch_u32(self, offset: int, value: int) -> None:
        """Overwrite four bytes at ``offset`` with little-endian u32 ``value``.

        Cursor is restored to its pre-call position so streaming writes
        continue uninterrupted.
        """
        cur = self._stream.tell()
        self._stream.seek(offset, os.SEEK_SET)
        self._stream.write(_U32.pack(value))
        self._stream.seek(cur, os.SEEK_SET)

    def close(self) -> None:
        if self._owned:
            self._stream.close()

    # ---- context manager ---------------------------------------------------

    def __enter__(self) -> NifWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            self._stream.flush()
        finally:
            self.close()


def open_nif_writer(
    target: str | os.PathLike[str] | BinaryIO,
    *,
    buffer_size: int = _DEFAULT_BUFFER,
) -> NifWriter:
    """Open a NIF for writing.

    A path opens (and owns) a buffered file. An already-open stream is wrapped
    without taking ownership. Writers always need seek (we patch block sizes
    after the fact); a non-seekable stream is rejected at construction time.
    """
    if isinstance(target, (str, os.PathLike)):
        path = Path(os.fspath(target))
        raw = path.open("wb")
        try:
            buffered = io.BufferedWriter(raw, buffer_size=buffer_size)  # type: ignore[arg-type]
        except Exception:
            raw.close()
            raise
        return NifWriter(buffered, owned=True, path=path)
    return NifWriter(target, owned=False)
