"""Phase 8i tests: pure texture-path resolution helpers.

Operator-level coverage (live ``bpy.data.images`` walk, real Blender
bake) is deferred to Phase 8j integration tests as called out in the
roadmap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nifblend.bridge.textures import (
    RESOLUTION_MODES,
    TextureAuditEntry,
    audit_image_paths,
    normalize_nif_relative,
    relative_to_data_root,
    resolve_texture_path,
)

# ---------------------------------------------------------------------------
# normalize_nif_relative
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("textures/foo/bar_d.dds", "textures/foo/bar_d.dds"),
        ("textures\\foo\\bar_d.dds", "textures/foo/bar_d.dds"),
        ("Data\\textures\\foo.dds", "textures/foo.dds"),
        ("data/textures/foo.dds", "textures/foo.dds"),
        ("DATA\\textures\\foo.dds", "textures/foo.dds"),
        ("\\textures\\foo.dds", "textures/foo.dds"),
        ("/textures/foo.dds", "textures/foo.dds"),
        ("", ""),
        ("data", ""),
    ],
)
def test_normalize_nif_relative(raw: str, expected: str) -> None:
    assert normalize_nif_relative(raw) == expected


# ---------------------------------------------------------------------------
# resolve_texture_path
# ---------------------------------------------------------------------------


def _build_fake_fs(paths: dict[str, bool]) -> tuple:
    """Build (listdir, isdir, isfile) callables over a dict of ``path → is_dir``."""

    def isdir(p: str) -> bool:
        return paths.get(p.replace("\\", "/").rstrip("/")) is True

    def isfile(p: str) -> bool:
        return paths.get(p.replace("\\", "/").rstrip("/")) is False

    def listdir(p: str) -> list[str]:
        norm = p.replace("\\", "/").rstrip("/")
        prefix = norm + "/"
        out: set[str] = set()
        for k in paths:
            if k.startswith(prefix):
                tail = k[len(prefix):].split("/", 1)[0]
                out.add(tail)
        return sorted(out)

    return listdir, isdir, isfile


def test_resolve_texture_path_strict_hit(tmp_path: Path) -> None:
    (tmp_path / "textures" / "foo").mkdir(parents=True)
    target = tmp_path / "textures" / "foo" / "bar.dds"
    target.write_bytes(b"")
    hit = resolve_texture_path(
        "textures/foo/bar.dds", data_root=tmp_path, mode="STRICT",
    )
    assert hit == target


def test_resolve_texture_path_strict_case_mismatch_misses(tmp_path: Path) -> None:
    (tmp_path / "textures" / "foo").mkdir(parents=True)
    (tmp_path / "textures" / "foo" / "bar.dds").write_bytes(b"")
    # STRICT is case-sensitive on case-sensitive filesystems and case-
    # insensitive on Windows — to keep the test portable, drive the
    # resolver with an injected fake FS where casing matters.
    fs = {
        "/data/textures": True,
        "/data/textures/foo": True,
        "/data/textures/foo/bar.dds": False,
    }
    listdir, isdir, isfile = _build_fake_fs(fs)
    assert resolve_texture_path(
        "Textures/Foo/Bar.dds",
        data_root="/data",
        mode="STRICT",
        listdir=listdir, isdir=isdir, isfile=isfile,
    ) is None
    assert resolve_texture_path(
        "textures/foo/bar.dds",
        data_root="/data",
        mode="STRICT",
        listdir=listdir, isdir=isdir, isfile=isfile,
    ) == Path("/data/textures/foo/bar.dds")


def test_resolve_texture_path_case_insensitive_walks_components() -> None:
    fs = {
        "/data": True,
        "/data/textures": True,
        "/data/textures/foo": True,
        "/data/textures/foo/bar.dds": False,
    }
    listdir, isdir, isfile = _build_fake_fs(fs)
    hit = resolve_texture_path(
        "Textures\\FOO\\BAR.dds",
        data_root="/data",
        mode="CASE_INSENSITIVE",
        listdir=listdir, isdir=isdir, isfile=isfile,
    )
    assert hit == Path("/data/textures/foo/bar.dds")


def test_resolve_texture_path_case_insensitive_missing_returns_none() -> None:
    fs = {"/data": True, "/data/textures": True}
    listdir, isdir, isfile = _build_fake_fs(fs)
    assert resolve_texture_path(
        "textures/foo/bar.dds",
        data_root="/data",
        mode="CASE_INSENSITIVE",
        listdir=listdir, isdir=isdir, isfile=isfile,
    ) is None


def test_resolve_texture_path_loosen_root_first_hit_wins() -> None:
    fs = {
        "/skyrim": True,
        "/skyrim/textures": True,
        "/mods": True,
        "/mods/textures": True,
        "/mods/textures/foo.dds": False,
    }
    listdir, isdir, isfile = _build_fake_fs(fs)
    hit = resolve_texture_path(
        "textures/foo.dds",
        data_root="/skyrim",
        mode="FUZZY_LOOSEN_ROOT",
        extra_roots=["/mods"],
        listdir=listdir, isdir=isdir, isfile=isfile,
    )
    assert hit == Path("/mods/textures/foo.dds")


def test_resolve_texture_path_loosen_root_no_extras_falls_back_to_data_root() -> None:
    fs = {"/skyrim": True, "/skyrim/textures": True, "/skyrim/textures/foo.dds": False}
    listdir, isdir, isfile = _build_fake_fs(fs)
    hit = resolve_texture_path(
        "textures/foo.dds",
        data_root="/skyrim",
        mode="FUZZY_LOOSEN_ROOT",
        listdir=listdir, isdir=isdir, isfile=isfile,
    )
    assert hit == Path("/skyrim/textures/foo.dds")


def test_resolve_texture_path_empty_inputs_return_none() -> None:
    assert resolve_texture_path("", data_root="/any") is None
    assert resolve_texture_path("textures/foo.dds", data_root="") is None


def test_resolve_texture_path_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown resolution mode"):
        resolve_texture_path("textures/foo.dds", data_root="/x", mode="BOGUS")


def test_resolution_modes_match_preferences() -> None:
    # Sanity: mode tuple matches the AddonPreferences enum.
    assert RESOLUTION_MODES == ("STRICT", "CASE_INSENSITIVE", "FUZZY_LOOSEN_ROOT")


def test_resolve_texture_path_strips_leading_data_prefix() -> None:
    fs = {
        "/skyrim": True,
        "/skyrim/textures": True,
        "/skyrim/textures/foo.dds": False,
    }
    listdir, isdir, isfile = _build_fake_fs(fs)
    hit = resolve_texture_path(
        "Data\\textures\\foo.dds",
        data_root="/skyrim",
        mode="CASE_INSENSITIVE",
        listdir=listdir, isdir=isdir, isfile=isfile,
    )
    assert hit == Path("/skyrim/textures/foo.dds")


# ---------------------------------------------------------------------------
# relative_to_data_root
# ---------------------------------------------------------------------------


def test_relative_to_data_root_basic() -> None:
    rel = relative_to_data_root(
        "/skyrim/data/textures/foo.dds", "/skyrim/data",
    )
    assert rel == "textures/foo.dds"


def test_relative_to_data_root_case_insensitive() -> None:
    rel = relative_to_data_root(
        "/Skyrim/Data/Textures/Foo.dds", "/skyrim/data",
    )
    assert rel == "Textures/Foo.dds"


def test_relative_to_data_root_outside_returns_none() -> None:
    assert relative_to_data_root(
        "/elsewhere/foo.dds", "/skyrim/data",
    ) is None


def test_relative_to_data_root_empty_inputs() -> None:
    assert relative_to_data_root("", "/x") is None
    assert relative_to_data_root("/x/y", "") is None


def test_relative_to_data_root_equal_paths_returns_none() -> None:
    # An absolute path that equals the root has no remainder; that's a miss.
    assert relative_to_data_root("/skyrim/data", "/skyrim/data") is None


# ---------------------------------------------------------------------------
# audit_image_paths
# ---------------------------------------------------------------------------


def test_audit_image_paths_resolves_relative_and_absolute() -> None:
    fs = {
        "/skyrim": True,
        "/skyrim/textures": True,
        "/skyrim/textures/foo.dds": False,
        "/skyrim/textures/bar.dds": False,
    }
    listdir, isdir, isfile = _build_fake_fs(fs)
    images = [
        ("foo", "textures/foo.dds"),                # NIF-relative
        ("bar", "/skyrim/textures/bar.dds"),         # absolute, under root
        ("missing", "textures/never.dds"),           # miss
        ("blank", ""),                               # empty filepath
    ]
    results = audit_image_paths(
        images,
        data_root="/skyrim",
        mode="CASE_INSENSITIVE",
        listdir=listdir, isdir=isdir, isfile=isfile,
    )
    assert len(results) == 4
    assert results[0].found and Path(results[0].resolved) == Path("/skyrim/textures/foo.dds")
    assert results[1].found and results[1].nif_relative == "textures/bar.dds"
    assert not results[2].found and results[2].resolved is None
    assert not results[3].found and results[3].nif_relative == ""


def test_audit_image_paths_returns_dataclass_entries() -> None:
    out = audit_image_paths(
        [("x", "")], data_root="/x",
    )
    assert isinstance(out[0], TextureAuditEntry)
    assert out[0].image_name == "x"
    assert out[0].found is False
