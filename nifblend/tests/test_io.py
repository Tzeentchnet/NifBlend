"""Unit tests for :mod:`nifblend.io.reader` and :mod:`nifblend.io.writer`.

The reader/writer wrap stdlib buffered streams and only need to satisfy the
``IO[bytes]`` shape consumed by :mod:`nifblend.format.primitives`. We verify
the wrapper invariants here, plus the NIF-specific extras (``size``,
``remaining``, ``peek``, ``patch_u32``).
"""

from __future__ import annotations

import io
import struct

import pytest

from nifblend.format import primitives as p
from nifblend.io import NifReader, NifWriter, open_nif, open_nif_writer

# ---- NifReader ------------------------------------------------------------


def test_open_nif_from_bytes() -> None:
    data = b"NIF\x00\x01\x02\x03"
    with open_nif(data) as r:
        assert r.size == len(data)
        assert r.remaining == len(data)
        assert r.read(4) == b"NIF\x00"
        assert r.tell() == 4
        assert r.remaining == 3
        assert not r.at_eof()
        assert r.read(3) == b"\x01\x02\x03"
        assert r.at_eof()


def test_open_nif_from_path(tmp_path) -> None:
    payload = bytes(range(256))
    path = tmp_path / "sample.nif"
    path.write_bytes(payload)

    with open_nif(path) as r:
        assert r.path == path
        assert r.size == 256
        assert r.read(8) == payload[:8]


def test_open_nif_from_stream_does_not_close() -> None:
    raw = io.BytesIO(b"abcdef")
    r = open_nif(raw)
    r.read(2)
    r.close()
    # Caller-owned stream stays usable after the wrapper is closed.
    assert raw.read(2) == b"cd"


def test_peek_does_not_advance() -> None:
    with open_nif(b"abcdef") as r:
        assert r.peek(3) == b"abc"
        assert r.tell() == 0
        assert r.read(3) == b"abc"


def test_expect_short_read_raises() -> None:
    with open_nif(b"ab") as r, pytest.raises(EOFError):
        r.expect(4)


def test_skip_advances_cursor() -> None:
    with open_nif(b"abcdef") as r:
        r.skip(3)
        assert r.read(3) == b"def"


def test_seek_and_tell_cooperate() -> None:
    with open_nif(b"0123456789") as r:
        r.seek(5)
        assert r.tell() == 5
        assert r.read(2) == b"56"


def test_reader_rejects_non_seekable() -> None:
    class _NoSeek:
        def readable(self) -> bool:
            return True

        def seekable(self) -> bool:
            return False

    with pytest.raises(ValueError, match="seekable"):
        NifReader(_NoSeek())  # type: ignore[arg-type]


def test_reader_rejects_unreadable() -> None:
    class _NoRead:
        def readable(self) -> bool:
            return False

        def seekable(self) -> bool:
            return True

    with pytest.raises(ValueError, match="readable"):
        NifReader(_NoRead())  # type: ignore[arg-type]


def test_reader_feeds_primitives() -> None:
    """Smoke-check that the reader is a drop-in for primitives.read_*."""
    payload = struct.pack("<IHf", 0xDEADBEEF, 0xCAFE, 1.5)
    with open_nif(payload) as r:
        assert p.read_u32(r) == 0xDEADBEEF
        assert p.read_u16(r) == 0xCAFE
        assert p.read_f32(r) == pytest.approx(1.5)


# ---- NifWriter ------------------------------------------------------------


def test_open_nif_writer_to_path(tmp_path) -> None:
    path = tmp_path / "out.nif"
    with open_nif_writer(path) as w:
        assert w.path == path
        w.write(b"hello")
    assert path.read_bytes() == b"hello"


def test_writer_feeds_primitives(tmp_path) -> None:
    path = tmp_path / "scalars.bin"
    with open_nif_writer(path) as w:
        p.write_u32(w, 0xDEADBEEF)
        p.write_u16(w, 0xCAFE)
        p.write_f32(w, 1.5)
    assert path.read_bytes() == struct.pack("<IHf", 0xDEADBEEF, 0xCAFE, 1.5)


def test_reserve_and_patch_u32_roundtrip() -> None:
    """Reserve a placeholder, write a payload, back-fill its size."""
    sink = io.BytesIO()
    w = NifWriter(sink, owned=False)
    w.write(b"HEAD")
    size_off = w.reserve_u32()
    payload_start = w.tell()
    w.write(b"BLOCKBODY")
    payload_end = w.tell()
    w.patch_u32(size_off, payload_end - payload_start)
    # Cursor must be restored to end-of-stream after the patch.
    assert w.tell() == payload_end

    out = sink.getvalue()
    assert out[:4] == b"HEAD"
    (block_size,) = struct.unpack("<I", out[4:8])
    assert block_size == len(b"BLOCKBODY")
    assert out[8:] == b"BLOCKBODY"


def test_writer_rejects_non_seekable() -> None:
    class _NoSeek:
        def writable(self) -> bool:
            return True

        def seekable(self) -> bool:
            return False

    with pytest.raises(ValueError, match="seekable"):
        NifWriter(_NoSeek())  # type: ignore[arg-type]


def test_writer_rejects_unwritable() -> None:
    class _NoWrite:
        def writable(self) -> bool:
            return False

        def seekable(self) -> bool:
            return True

    with pytest.raises(ValueError, match="writable"):
        NifWriter(_NoWrite())  # type: ignore[arg-type]


# ---- end-to-end: reader + writer + primitives -----------------------------


def test_reader_writer_array_roundtrip(tmp_path) -> None:
    import numpy as np

    src = np.arange(1024, dtype=np.float32) * 0.5
    path = tmp_path / "verts.bin"

    with open_nif_writer(path) as w:
        p.write_array_f32(w, src)

    with open_nif(path) as r:
        out = p.read_array_f32(r, len(src))
        assert r.at_eof()

    assert np.array_equal(out, src)
