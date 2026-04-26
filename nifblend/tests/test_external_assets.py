"""Phase 9c tests: external-asset resolver protocol + helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from nifblend.bridge.external_assets import (
    PrefsExternalAssetResolver,
    StaticExternalAssetResolver,
    collect_extra_roots,
)


def test_static_resolver_round_trips_meshes() -> None:
    resolver = StaticExternalAssetResolver(
        meshes={"meshes/abc/foo.mesh": Path("/disk/foo.mesh")},
    )
    assert resolver.resolve_mesh("meshes/abc/foo.mesh") == Path("/disk/foo.mesh")
    assert resolver.resolve_mesh("missing.mesh") is None
    assert resolver.resolve_material("anything.mat") is None
    assert resolver.resolve_texture("anything.dds") is None


def test_static_resolver_normalises_separators_and_case() -> None:
    resolver = StaticExternalAssetResolver(meshes={"meshes/foo.mesh": Path("/d/x")})
    assert resolver.resolve_mesh("MESHES\\Foo.Mesh") == Path("/d/x")


def test_static_resolver_handles_empty_path() -> None:
    resolver = StaticExternalAssetResolver(meshes={"x": Path("/y")})
    assert resolver.resolve_mesh("") is None


def test_prefs_resolver_unconfigured_root_returns_none() -> None:
    resolver = PrefsExternalAssetResolver(data_root="")
    assert resolver.resolve_mesh("meshes/foo.mesh") is None


def test_prefs_resolver_finds_file_via_filesystem(tmp_path: Path) -> None:
    target = tmp_path / "meshes" / "foo.mesh"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    resolver = PrefsExternalAssetResolver(data_root=str(tmp_path))
    found = resolver.resolve_mesh("meshes/foo.mesh")
    assert found is not None
    assert Path(found).resolve() == target.resolve()


def test_prefs_resolver_case_insensitive_match(tmp_path: Path) -> None:
    target = tmp_path / "meshes" / "foo.mesh"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    resolver = PrefsExternalAssetResolver(
        data_root=str(tmp_path), mode="CASE_INSENSITIVE"
    )
    found = resolver.resolve_mesh("MESHES/FOO.MESH")
    assert found is not None
    assert Path(found).resolve() == target.resolve()


def test_prefs_resolver_strict_mode_requires_exact_path(tmp_path: Path) -> None:
    target = tmp_path / "meshes" / "foo.mesh"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    resolver = PrefsExternalAssetResolver(data_root=str(tmp_path), mode="STRICT")
    # STRICT mode does no walking; a missing path stays missing even when a
    # case-insensitive walk would have hit it.
    assert resolver.resolve_mesh("meshes/missing.mesh") is None
    found = resolver.resolve_mesh("meshes/foo.mesh")
    assert found is not None


def test_prefs_resolver_fuzzy_falls_back_to_extra_roots(tmp_path: Path) -> None:
    extra = tmp_path / "mod_overwrite"
    target = extra / "meshes" / "foo.mesh"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    resolver = PrefsExternalAssetResolver(
        data_root=str(tmp_path / "vanilla"),
        mode="FUZZY_LOOSEN_ROOT",
        extra_roots=(str(extra),),
    )
    found = resolver.resolve_mesh("meshes/foo.mesh")
    assert found is not None
    assert Path(found).resolve() == target.resolve()


@pytest.mark.parametrize(
    ("primary", "candidates", "expected"),
    [
        ("/a", ["/a", "/b", ""], ("/b",)),
        ("/a", ["/A", "/b"], ("/b",)),
        ("", ["/a", "/b"], ("/a", "/b")),
        ("/a", [], ()),
    ],
)
def test_collect_extra_roots(
    primary: str, candidates: list[str], expected: tuple[str, ...]
) -> None:
    assert collect_extra_roots(primary, candidates) == expected
