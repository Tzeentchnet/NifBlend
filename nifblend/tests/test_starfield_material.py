"""Phase 9e tests: Starfield ``.mat`` JSON decoder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nifblend.bridge.external_assets import StaticExternalAssetResolver
from nifblend.bridge.games.starfield_material import (
    StarfieldMaterialError,
    decode_starfield_material,
    get_starfield_extras,
    load_starfield_material,
    starfield_material_textures,
)


def _payload() -> dict:
    return {
        "Type": "Material",
        "Name": "TestMaterial",
        "BaseColor": [0.8, 0.4, 0.2],
        "EmissiveColor": [0.1, 0.0, 0.0],
        "EmissiveIntensity": 2.5,
        "Roughness": 0.25,
        "Metalness": 0.75,
        "Textures": {
            "BaseColor": "textures/foo_base.dds",
            "Normal": "textures/foo_normal.dds",
            "Emissive": "textures/foo_em.dds",
            "Custom": "textures/foo_custom.dds",
        },
        "UnknownKey": [1, 2, 3],
    }


def test_decode_minimal_payload_uses_defaults() -> None:
    data = decode_starfield_material({})
    assert data.origin == "StarfieldMaterial"
    assert data.name == "StarfieldMaterial"
    assert data.base_color == (1.0, 1.0, 1.0, 1.0)
    assert data.smoothness == 0.5  # 1 - default roughness 0.5
    assert data.textures == {}


def test_decode_full_payload_maps_channels() -> None:
    data = decode_starfield_material(_payload())
    assert data.name == "TestMaterial"
    assert data.base_color[:3] == (0.8, 0.4, 0.2)
    assert data.emissive_color == (0.1, 0.0, 0.0)
    assert data.emissive_multiple == pytest.approx(2.5)
    assert data.smoothness == pytest.approx(0.75)
    assert data.specular_strength == pytest.approx(0.75)
    # Channel map: BaseColor->diffuse, Normal->normal, Emissive->glow.
    assert data.textures["diffuse"] == "textures/foo_base.dds"
    assert data.textures["normal"] == "textures/foo_normal.dds"
    assert data.textures["glow"] == "textures/foo_em.dds"
    # Unknown channel falls through verbatim under its lowercased key.
    assert data.textures["custom"] == "textures/foo_custom.dds"


def test_decode_preserves_unknown_keys_as_extras() -> None:
    data = decode_starfield_material(_payload())
    extras = get_starfield_extras(data)
    assert "UnknownKey" in extras
    assert extras["UnknownKey"] == [1, 2, 3]
    # Known keys are NOT in extras.
    assert "BaseColor" not in extras
    assert "Textures" not in extras


def test_decode_rejects_non_dict_payload() -> None:
    with pytest.raises(StarfieldMaterialError, match="JSON object"):
        decode_starfield_material([1, 2, 3])  # type: ignore[arg-type]


def test_decode_clamps_smoothness_for_degenerate_roughness() -> None:
    data = decode_starfield_material({"Roughness": 2.0})
    assert data.smoothness == 0.0
    data = decode_starfield_material({"Roughness": -1.0})
    assert data.smoothness == 1.0


def test_decode_drops_non_string_texture_paths() -> None:
    data = decode_starfield_material(
        {"Textures": {"BaseColor": "ok.dds", "Normal": 42, "Emissive": ""}}
    )
    assert data.textures == {"diffuse": "ok.dds"}


def test_starfield_material_textures_yields_pairs() -> None:
    data = decode_starfield_material(
        {"Textures": {"BaseColor": "a.dds", "Normal": "b.dds"}}
    )
    pairs = dict(starfield_material_textures(data))
    assert pairs == {"diffuse": "a.dds", "normal": "b.dds"}


def test_load_via_resolver_round_trips(tmp_path: Path) -> None:
    mat_path = tmp_path / "materials" / "foo.mat"
    mat_path.parent.mkdir(parents=True)
    mat_path.write_text(json.dumps(_payload()), encoding="utf-8")
    resolver = StaticExternalAssetResolver(
        meshes={},
        materials={"materials/foo.mat": mat_path},
    )
    data = load_starfield_material("materials/foo.mat", resolver=resolver)
    assert data.name == "foo"
    assert data.textures["diffuse"] == "textures/foo_base.dds"


def test_load_unresolved_path_raises() -> None:
    resolver = StaticExternalAssetResolver(meshes={}, materials={})
    with pytest.raises(StarfieldMaterialError, match="unresolved"):
        load_starfield_material("missing.mat", resolver=resolver)


def test_load_empty_path_raises() -> None:
    resolver = StaticExternalAssetResolver(meshes={}, materials={})
    with pytest.raises(StarfieldMaterialError, match="empty material path"):
        load_starfield_material("", resolver=resolver)


def test_load_malformed_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mat"
    bad.write_text("not json", encoding="utf-8")
    resolver = StaticExternalAssetResolver(
        meshes={}, materials={"bad.mat": bad}
    )
    with pytest.raises(StarfieldMaterialError, match="failed to read"):
        load_starfield_material("bad.mat", resolver=resolver)
