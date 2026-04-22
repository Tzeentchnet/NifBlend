"""Phase 8i: pure helpers for texture-path resolution against game ``Data/`` roots.

NIF-relative texture paths are stored verbatim from the source file
(``textures\\foo\\bar_d.dds`` on Windows-authored content). The
operator layer (:mod:`nifblend.ops.textures`) resolves them against the
active :class:`~nifblend.format.versions.GameProfile`'s ``Data/`` root
configured in :class:`~nifblend.preferences.NIFBLEND_AddonPreferences`.

The resolution strategy mirrors the
``texture_resolution_mode`` enum on the AddonPreferences:

* ``STRICT`` -- ``Path(data_root) / nif_relative`` must exist verbatim.
* ``CASE_INSENSITIVE`` -- walk path components case-insensitively
  (Windows-style); useful on Linux/macOS where the source NIF capitalises
  ``Textures\\Foo`` but the on-disk folders are ``textures/foo``.
* ``FUZZY_LOOSEN_ROOT`` -- try ``data_root`` first, then each
  ``extra_roots`` entry in turn; first hit wins. Each root is resolved
  case-insensitively. Useful when a modder has multiple Data/ folders
  layered (e.g. base game + Mod Organizer overwrite).

All helpers are filesystem-only (no ``bpy``) so the test suite runs
headlessly. Inject ``listdir`` / ``isdir`` / ``isfile`` for tests that
want to fake the filesystem.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

__all__ = [
    "RESOLUTION_MODES",
    "TextureAuditEntry",
    "audit_image_paths",
    "normalize_nif_relative",
    "relative_to_data_root",
    "resolve_texture_path",
]


#: Resolution modes accepted by :func:`resolve_texture_path`. Mirrors
#: the ``texture_resolution_mode`` enum on the AddonPreferences.
RESOLUTION_MODES: tuple[str, ...] = ("STRICT", "CASE_INSENSITIVE", "FUZZY_LOOSEN_ROOT")


def normalize_nif_relative(path: str) -> str:
    """Normalise a NIF-stored texture path into POSIX form.

    Strips any leading ``data\\`` / ``data/`` prefix (case-insensitive --
    NIFs sometimes embed it, sometimes don't, and the resolver always
    starts from the configured ``Data/`` root) and converts backslashes
    to forward slashes. Leading slashes are also stripped so the result
    is always a relative POSIX path.

    Empty input returns ``""``.
    """
    if not path:
        return ""
    # Accept either separator: parse via PureWindowsPath (handles both)
    parts = list(PureWindowsPath(path).parts)
    # Drop drive / leading separator entries.
    while parts and parts[0] in ("\\", "/", ""):
        parts.pop(0)
    if parts and parts[0].lower() == "data":
        parts.pop(0)
    return str(PurePosixPath(*parts)) if parts else ""


def _resolve_case_insensitive(
    root: Path,
    components: Sequence[str],
    *,
    listdir: Callable[[str], list[str]],
    isdir: Callable[[str], bool],
    isfile: Callable[[str], bool],
) -> Path | None:
    """Walk ``components`` under ``root`` doing per-level case-insensitive matching."""
    if not isdir(str(root)):
        return None
    current = root
    for idx, comp in enumerate(components):
        is_last = idx == len(components) - 1
        # Fast path: exact match.
        candidate = current / comp
        if is_last and isfile(str(candidate)):
            return candidate
        if not is_last and isdir(str(candidate)):
            current = candidate
            continue
        # Slow path: list and compare case-folded.
        try:
            entries = listdir(str(current))
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            return None
        target = comp.casefold()
        for entry in entries:
            if entry.casefold() != target:
                continue
            candidate = current / entry
            if is_last:
                if isfile(str(candidate)):
                    return candidate
            elif isdir(str(candidate)):
                current = candidate
                break
        else:
            return None
    return None


def resolve_texture_path(
    nif_relative: str,
    *,
    data_root: str | os.PathLike[str],
    mode: str = "CASE_INSENSITIVE",
    extra_roots: Sequence[str | os.PathLike[str]] = (),
    listdir: Callable[[str], list[str]] = os.listdir,
    isdir: Callable[[str], bool] = os.path.isdir,
    isfile: Callable[[str], bool] = os.path.isfile,
) -> Path | None:
    """Resolve a NIF-relative texture path to an absolute on-disk file.

    Returns ``None`` when no resolution succeeds. ``mode`` must be one
    of :data:`RESOLUTION_MODES`; an unknown mode raises ``ValueError``.

    The ``listdir`` / ``isdir`` / ``isfile`` injection points exist for
    headless tests; production callers should leave them at the defaults.
    """
    if mode not in RESOLUTION_MODES:
        raise ValueError(f"unknown resolution mode: {mode!r}")

    rel = normalize_nif_relative(nif_relative)
    if not rel:
        return None

    components = list(PurePosixPath(rel).parts)
    if not components:
        return None

    roots: list[Path] = []
    if data_root:
        roots.append(Path(os.fspath(data_root)))
    if mode == "FUZZY_LOOSEN_ROOT":
        for extra in extra_roots:
            if extra:
                roots.append(Path(os.fspath(extra)))
    if not roots:
        return None

    if mode == "STRICT":
        candidate = roots[0] / Path(*components)
        return candidate if isfile(str(candidate)) else None

    for root in roots:
        hit = _resolve_case_insensitive(
            root, components, listdir=listdir, isdir=isdir, isfile=isfile,
        )
        if hit is not None:
            return hit
    return None


def relative_to_data_root(
    absolute_path: str | os.PathLike[str],
    data_root: str | os.PathLike[str],
) -> str | None:
    """Return ``absolute_path`` re-expressed relative to ``data_root``.

    Comparison is case-insensitive (Windows-style) so ``D:\\Skyrim\\Data``
    matches ``d:\\skyrim\\data\\textures\\foo.dds``. Returns the
    POSIX-form relative string on hit, ``None`` when the absolute path
    is not under the root.

    Empty inputs return ``None``.
    """
    if not absolute_path or not data_root:
        return None
    abs_path = Path(os.fspath(absolute_path))
    root = Path(os.fspath(data_root))
    abs_parts = [p.casefold() for p in abs_path.parts]
    root_parts = [p.casefold() for p in root.parts]
    if len(abs_parts) <= len(root_parts):
        return None
    if abs_parts[: len(root_parts)] != root_parts:
        return None
    rel_parts = abs_path.parts[len(root_parts):]
    return str(PurePosixPath(*rel_parts)) if rel_parts else None


@dataclass(frozen=True, slots=True)
class TextureAuditEntry:
    """One ``bpy.data.images`` entry's resolution result."""

    image_name: str
    original_filepath: str
    nif_relative: str
    resolved: str | None
    found: bool


def audit_image_paths(
    images: Iterable[tuple[str, str]],
    *,
    data_root: str | os.PathLike[str],
    mode: str = "CASE_INSENSITIVE",
    extra_roots: Sequence[str | os.PathLike[str]] = (),
    listdir: Callable[[str], list[str]] = os.listdir,
    isdir: Callable[[str], bool] = os.path.isdir,
    isfile: Callable[[str], bool] = os.path.isfile,
) -> list[TextureAuditEntry]:
    """Resolve every ``(image_name, image_filepath)`` pair against ``data_root``.

    For each entry: try to derive a NIF-relative path either by stripping
    the ``data_root`` prefix from an already-absolute path, or by treating
    a non-absolute path as already-relative. Then resolve via
    :func:`resolve_texture_path`. Returns one :class:`TextureAuditEntry`
    per input row, in source order.
    """
    out: list[TextureAuditEntry] = []
    for image_name, filepath in images:
        if not filepath:
            out.append(TextureAuditEntry(image_name, filepath, "", None, False))
            continue
        rel = relative_to_data_root(filepath, data_root) if data_root else None
        if rel is None:
            rel = normalize_nif_relative(filepath)
        resolved = resolve_texture_path(
            rel,
            data_root=data_root,
            mode=mode,
            extra_roots=extra_roots,
            listdir=listdir,
            isdir=isdir,
            isfile=isfile,
        ) if rel else None
        out.append(
            TextureAuditEntry(
                image_name=image_name,
                original_filepath=filepath,
                nif_relative=rel,
                resolved=str(resolved) if resolved is not None else None,
                found=resolved is not None,
            )
        )
    return out
