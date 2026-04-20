"""Low-level binary I/O for NIF/KF files.

Public surface:

- :class:`NifReader` / :func:`open_nif` -- buffered, seekable byte stream wrapper
- :class:`NifWriter` / :func:`open_nif_writer` -- writer counterpart with
  ``patch_u32`` for back-filling block sizes
- :func:`read_nif_header` / :func:`write_nif_header` -- magic line + header struct
- :class:`BlockTable` / :func:`read_nif` / :func:`write_nif` -- end-to-end
  file-level read/write loop driven by the generated ``Block.read`` /
  ``Block.write`` methods
"""

from __future__ import annotations

from .block_table import BlockTable, read_nif, write_nif
from .header import read_nif_header, write_nif_header
from .reader import NifReader, open_nif
from .writer import NifWriter, open_nif_writer

__all__ = [
    "BlockTable",
    "NifReader",
    "NifWriter",
    "open_nif",
    "open_nif_writer",
    "read_nif",
    "read_nif_header",
    "write_nif",
    "write_nif_header",
]
