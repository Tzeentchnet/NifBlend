"""Buffered NIF file reader.

Thin wrapper around ``io.BufferedReader`` that exposes the binary-stream
interface the generated ``Block.read(stream, ctx)`` classmethods (and every
helper in :mod:`nifblend.format.primitives`) consume.

Why not just hand callers an open file? Two reasons:

1. We want a *single* place to enforce buffering and (later) memory-mapped
   reads for very large meshes; today that is just :class:`io.BufferedReader`,
   tomorrow it might be ``mmap`` for the vertex/index payload.
2. NIF's block-table parsing needs absolute seeks (block-size table tells us
   where each block ends, so we can recover from a malformed block) and EOF
   detection. Centralising those behind :class:`NifReader` keeps the rest of
   the I/O layer free of ``f.tell()`` / ``f.seek()`` boilerplate.

The class intentionally implements the ``IO[bytes]`` protocol attributes the
primitives use (``read``, ``tell``, ``seek``) instead of subclassing
``BufferedReader`` -- that subclass surface is large and brittle, and the
generated code only ever calls ``stream.read(n)``.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Final

__all__ = ["NifReader", "open_nif"]


_DEFAULT_BUFFER: Final[int] = 1 << 20  # 1 MiB; tuned for typical SSE NIFs.


class NifReader:
    """Buffered, seekable, bytes-only stream over a NIF file.

    Implements just enough of the ``IO[bytes]`` protocol for
    :mod:`nifblend.format.primitives` and the codegen output. Use
    :func:`open_nif` (or the class as a context manager) to construct one.
    """

    __slots__ = ("_owned", "_path", "_size", "_stream")

    def __init__(
        self,
        stream: BinaryIO,
        *,
        size: int | None = None,
        owned: bool = False,
        path: Path | None = None,
    ) -> None:
        if not stream.readable():
            raise ValueError("NifReader requires a readable binary stream")
        if not stream.seekable():
            raise ValueError("NifReader requires a seekable stream")
        self._stream = stream
        self._owned = owned
        self._path = path
        if size is None:
            cur = stream.tell()
            stream.seek(0, os.SEEK_END)
            size = stream.tell()
            stream.seek(cur, os.SEEK_SET)
        self._size = size

    # ---- IO[bytes] surface used by primitives / codegen --------------------

    def read(self, n: int = -1) -> bytes:
        return self._stream.read(n)

    def tell(self) -> int:
        return self._stream.tell()

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        return self._stream.seek(offset, whence)

    # ---- NIF-specific helpers ---------------------------------------------

    @property
    def size(self) -> int:
        """Total file size in bytes (cached at open time)."""
        return self._size

    @property
    def remaining(self) -> int:
        """Bytes from the current position to EOF."""
        return self._size - self._stream.tell()

    @property
    def path(self) -> Path | None:
        """Source path, if the reader was opened from one."""
        return self._path

    def at_eof(self) -> bool:
        return self._stream.tell() >= self._size

    def peek(self, n: int) -> bytes:
        """Look at the next ``n`` bytes without advancing the cursor.

        Used by the header parser to sniff the magic line before committing
        to a full ``read``.
        """
        cur = self._stream.tell()
        data = self._stream.read(n)
        self._stream.seek(cur, os.SEEK_SET)
        return data

    def expect(self, n: int) -> bytes:
        """Read exactly ``n`` bytes, raising :class:`EOFError` on short read."""
        data = self._stream.read(n)
        if len(data) != n:
            raise EOFError(
                f"unexpected EOF: wanted {n} bytes at offset {self._stream.tell() - len(data)}, got {len(data)}"
            )
        return data

    def skip(self, n: int) -> None:
        """Advance the cursor by ``n`` bytes (no read)."""
        self._stream.seek(n, os.SEEK_CUR)

    def close(self) -> None:
        if self._owned:
            self._stream.close()

    # ---- context manager ---------------------------------------------------

    def __enter__(self) -> NifReader:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def open_nif(
    source: str | os.PathLike[str] | BinaryIO | bytes | bytearray | memoryview,
    *,
    buffer_size: int = _DEFAULT_BUFFER,
) -> NifReader:
    """Open a NIF for reading.

    Accepts a filesystem path, an already-open binary stream, or an in-memory
    buffer (``bytes``/``bytearray``/``memoryview`` -- handy for tests). When
    a path is given the underlying file handle is owned by the reader and
    closed when it is closed.
    """
    if isinstance(source, bytes | bytearray | memoryview):
        return NifReader(io.BytesIO(bytes(source)), size=len(source), owned=True)
    if isinstance(source, str | os.PathLike):
        path = Path(os.fspath(source))
        raw = path.open("rb")
        try:
            buffered = io.BufferedReader(raw, buffer_size=buffer_size)
        except Exception:
            raw.close()
            raise
        return NifReader(buffered, size=path.stat().st_size, owned=True, path=path)
    # Already-open stream: caller retains ownership.
    return NifReader(_as_binary(source), owned=False)


def _as_binary(stream: object) -> BinaryIO:
    # ``IO[bytes]`` is structural; trust the caller to pass something that
    # works. We only need read/tell/seek, all checked in NifReader.__init__.
    return stream  # type: ignore[return-value]
