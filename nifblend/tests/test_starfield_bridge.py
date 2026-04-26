"""Phase 9d tests: Starfield ``BSGeometry`` external-mesh bridge."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.external_assets import StaticExternalAssetResolver
from nifblend.bridge.games.starfield import (
    StarfieldExternalMeshError,
    decode_external_mesh,
    find_starfield_material_path,
    load_bsgeometry_material,
    starfield_mesh_to_mesh_data,
)
from nifblend.bridge.mesh_in import BSGeometryMeshRef
from nifblend.format.starfield_mesh import (
    StarfieldMeshData,
    StarfieldMeshLOD,
    write_starfield_mesh,
)


def _write_temp_mesh(tmp_path: Path, name: str = "test.mesh") -> tuple[Path, StarfieldMeshData]:
    src = StarfieldMeshData(
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32
        ),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        uv=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        lods=[StarfieldMeshLOD(start_index=0, num_indices=3, distance=50.0)],
    )
    path = tmp_path / name
    buf = BytesIO()
    write_starfield_mesh(buf, src)
    path.write_bytes(buf.getvalue())
    return path, src


def test_starfield_mesh_to_mesh_data_preserves_arrays() -> None:
    src = StarfieldMeshData(
        positions=np.array([[1.0, 2.0, 3.0]], dtype=np.float32),
        triangles=np.array([[0, 0, 0]], dtype=np.uint32),
        uv=np.array([[0.5, 0.5]], dtype=np.float32),
    )
    md = starfield_mesh_to_mesh_data(src, name="X")
    assert md.name == "X"
    np.testing.assert_array_equal(md.positions, src.positions)
    np.testing.assert_array_equal(md.triangles, src.triangles)
    assert md.uv is not None
    np.testing.assert_array_equal(md.uv, src.uv)


def test_decode_external_mesh_resolves_and_decodes(tmp_path: Path) -> None:
    mesh_path, _ = _write_temp_mesh(tmp_path)
    resolver = StaticExternalAssetResolver(
        meshes={"meshes/foo.mesh": mesh_path},
    )
    ref = BSGeometryMeshRef(lod_index=0, has_mesh=True, mesh_path="meshes/foo.mesh")
    imp = decode_external_mesh(ref, resolver=resolver, name_prefix="bar_")
    assert imp.lod_index == 0
    assert imp.mesh_path == "meshes/foo.mesh"
    assert imp.mesh.name == "bar_LOD0"
    assert imp.mesh.positions.shape == (3, 3)
    assert imp.mesh.triangles.shape == (1, 3)


def test_decode_external_mesh_rejects_empty_slot() -> None:
    ref = BSGeometryMeshRef(lod_index=0, has_mesh=False, mesh_path="")
    resolver = StaticExternalAssetResolver(meshes={})
    with pytest.raises(StarfieldExternalMeshError, match="no mesh reference"):
        decode_external_mesh(ref, resolver=resolver)


def test_decode_external_mesh_unresolved_path_raises() -> None:
    ref = BSGeometryMeshRef(lod_index=2, has_mesh=True, mesh_path="meshes/missing.mesh")
    resolver = StaticExternalAssetResolver(meshes={})
    with pytest.raises(StarfieldExternalMeshError, match="unresolved"):
        decode_external_mesh(ref, resolver=resolver)


def test_decode_external_mesh_corrupt_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mesh"
    bad.write_bytes(b"\xff\xff\xff\xff")
    resolver = StaticExternalAssetResolver(meshes={"bad.mesh": bad})
    ref = BSGeometryMeshRef(lod_index=0, has_mesh=True, mesh_path="bad.mesh")
    with pytest.raises(StarfieldExternalMeshError, match="failed to decode"):
        decode_external_mesh(ref, resolver=resolver)


# ---------- Phase 9g: BSGeometry → .mat material wiring -------------------

from types import SimpleNamespace  # noqa: E402

_MAT_PAYLOAD = (
    b'{"Type":"Material","Name":"X","BaseColor":[0.1,0.2,0.3],'
    b'"Roughness":0.4,"Metalness":0.5}'
)


def _name_obj(idx: int) -> SimpleNamespace:
    """Fake the codegen ``string`` shape (index-into-string-table form)."""
    return SimpleNamespace(index=idx, string=None)


def _string_entry(text: str) -> SimpleNamespace:
    return SimpleNamespace(value=text.encode("latin-1"))


def _table(strings: list[SimpleNamespace | None], blocks: list[Any] | None = None):
    return SimpleNamespace(
        header=SimpleNamespace(strings=strings),
        blocks=blocks or [],
    )


def test_find_material_path_via_shader_property() -> None:
    shader = SimpleNamespace(name=_name_obj(1))
    geom = SimpleNamespace(name=_name_obj(0), shader_property=0)
    table = _table(
        strings=[_string_entry("BSGeometry"), _string_entry("materials/foo.mat")],
        blocks=[shader],
    )
    assert find_starfield_material_path(geom, table) == "materials/foo.mat"


def test_find_material_path_falls_back_to_block_name() -> None:
    geom = SimpleNamespace(
        name=_name_obj(0),
        shader_property=0xFFFFFFFF,
    )
    table = _table(strings=[_string_entry("materials/bar.mat")])
    assert find_starfield_material_path(geom, table) == "materials/bar.mat"


def test_find_material_path_returns_none_when_no_mat_anywhere() -> None:
    geom = SimpleNamespace(
        name=_name_obj(0),
        shader_property=0xFFFFFFFF,
    )
    table = _table(strings=[_string_entry("just-a-mesh-name")])
    assert find_starfield_material_path(geom, table) is None


def test_find_material_path_tolerates_bad_shader_ref() -> None:
    geom = SimpleNamespace(
        name=_name_obj(0),
        shader_property=99,  # out of range
    )
    table = _table(strings=[_string_entry("materials/baz.mat")])
    assert find_starfield_material_path(geom, table) == "materials/baz.mat"


def test_load_bsgeometry_material_resolves_and_decodes(tmp_path: Path) -> None:
    mat_path = tmp_path / "x.mat"
    mat_path.write_bytes(_MAT_PAYLOAD)
    resolver = StaticExternalAssetResolver(
        meshes={}, materials={"materials/x.mat": mat_path}
    )
    geom = SimpleNamespace(name=_name_obj(0), shader_property=0xFFFFFFFF)
    table = _table(strings=[_string_entry("materials/x.mat")])

    data, warning = load_bsgeometry_material(geom, table, resolver=resolver)

    assert warning is None
    assert data is not None
    assert data.name == "x"
    assert data.base_color[:3] == pytest.approx((0.1, 0.2, 0.3))


def test_load_bsgeometry_material_no_path_returns_none_no_warning() -> None:
    geom = SimpleNamespace(name=_name_obj(0), shader_property=0xFFFFFFFF)
    table = _table(strings=[_string_entry("not-a-material-path")])
    resolver = StaticExternalAssetResolver(meshes={}, materials={})

    data, warning = load_bsgeometry_material(geom, table, resolver=resolver)

    assert data is None
    assert warning is None


def test_load_bsgeometry_material_unresolved_returns_warning() -> None:
    geom = SimpleNamespace(name=_name_obj(0), shader_property=0xFFFFFFFF)
    table = _table(strings=[_string_entry("materials/missing.mat")])
    resolver = StaticExternalAssetResolver(meshes={}, materials={})

    data, warning = load_bsgeometry_material(geom, table, resolver=resolver)

    assert data is None
    assert warning is not None
    assert "unresolved" in warning


# ---------- Phase 9h: Starfield skinning ---------------------------------

from nifblend.bridge.games.starfield import (  # noqa: E402
    bsgeometry_skin_to_skin_data,
    resolve_bsgeometry_bone_palette,
)
from nifblend.bridge.mesh_in import MeshData  # noqa: E402
from nifblend.bridge.skin_in import apply_skin_to_object  # noqa: E402


class _FakeVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[list[int], float, str]] = []

    def add(self, indices: list[int], weight: float, mode: str) -> None:
        self.calls.append((list(indices), float(weight), mode))


class _FakeVertexGroups:
    def __init__(self) -> None:
        self.created: list[_FakeVertexGroup] = []

    def new(self, *, name: str) -> _FakeVertexGroup:
        vg = _FakeVertexGroup(name)
        self.created.append(vg)
        return vg


class _FakeObject:
    def __init__(self) -> None:
        self.vertex_groups = _FakeVertexGroups()


def _ninode_named(name: str) -> SimpleNamespace:
    """Fake an :class:`NiNode` for palette resolution.

    ``isinstance(_, NiNode)`` is the gate, so we need a real instance.
    """
    from nifblend.format.generated.blocks import NiNode

    node = NiNode()
    node.name = _name_obj(_NINODE_FAKE.string_index_for(name))
    return node


class _StringIndexAllocator:
    """Track inserted strings so multiple NiNode fakes share one table."""

    def __init__(self) -> None:
        self.strings: list[SimpleNamespace] = []
        self._index: dict[str, int] = {}

    def string_index_for(self, text: str) -> int:
        if text not in self._index:
            self._index[text] = len(self.strings)
            self.strings.append(_string_entry(text))
        return self._index[text]


_NINODE_FAKE = _StringIndexAllocator()


def _bsgeometry_with_skin(skin_ref: int) -> Any:
    """Minimal :class:`BSGeometry` carrying just a ``skin`` ref."""
    from nifblend.format.generated.blocks import BSGeometry

    geom = BSGeometry()
    geom.skin = skin_ref
    return geom


def _bsskin_instance(bone_refs: list[int]) -> Any:
    from nifblend.format.generated.blocks import BSSkinInstance

    inst = BSSkinInstance()
    inst.bones = list(bone_refs)
    return inst


def test_resolve_bone_palette_returns_none_when_no_skin() -> None:
    geom = _bsgeometry_with_skin(0xFFFFFFFF)
    table = _table(strings=[], blocks=[])
    assert resolve_bsgeometry_bone_palette(geom, table) is None


def test_resolve_bone_palette_returns_none_for_non_bsskininstance_target() -> None:
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=[], blocks=[SimpleNamespace()])
    assert resolve_bsgeometry_bone_palette(geom, table) is None


def test_resolve_bone_palette_resolves_ninode_names() -> None:
    alloc = _StringIndexAllocator()
    from nifblend.format.generated.blocks import NiNode

    node_a = NiNode()
    node_a.name = _name_obj(alloc.string_index_for("Bip01_Spine"))
    node_b = NiNode()
    node_b.name = _name_obj(alloc.string_index_for("Bip01_Head"))
    inst = _bsskin_instance(bone_refs=[1, 2])
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=alloc.strings, blocks=[inst, node_a, node_b])

    palette = resolve_bsgeometry_bone_palette(geom, table)

    assert palette == ["Bip01_Spine", "Bip01_Head"]


def test_resolve_bone_palette_falls_back_for_bad_refs() -> None:
    inst = _bsskin_instance(bone_refs=[99, 0xFFFFFFFF])
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=[], blocks=[inst])

    palette = resolve_bsgeometry_bone_palette(geom, table)

    assert palette == ["Bone.0", "Bone.1"]


def test_bsgeometry_skin_to_skin_data_returns_none_for_rigid_mesh() -> None:
    geom = _bsgeometry_with_skin(0xFFFFFFFF)
    table = _table(strings=[], blocks=[])
    mesh = MeshData(
        name="rigid",
        positions=np.zeros((1, 3), dtype=np.float32),
        triangles=np.zeros((0, 3), dtype=np.uint32),
    )
    assert bsgeometry_skin_to_skin_data(geom, table, mesh) is None


def test_bsgeometry_skin_to_skin_data_returns_none_when_mesh_has_no_weights() -> None:
    inst = _bsskin_instance(bone_refs=[])
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=[], blocks=[inst])
    mesh = MeshData(
        name="m",
        positions=np.zeros((1, 3), dtype=np.float32),
        triangles=np.zeros((0, 3), dtype=np.uint32),
    )
    assert bsgeometry_skin_to_skin_data(geom, table, mesh) is None


def test_bsgeometry_skin_to_skin_data_flattens_per_vertex_influences() -> None:
    alloc = _StringIndexAllocator()
    from nifblend.format.generated.blocks import NiNode

    node_a = NiNode()
    node_a.name = _name_obj(alloc.string_index_for("Spine"))
    node_b = NiNode()
    node_b.name = _name_obj(alloc.string_index_for("Head"))
    inst = _bsskin_instance(bone_refs=[1, 2])
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=alloc.strings, blocks=[inst, node_a, node_b])

    # 3 vertices, K=2 influences/vertex; one zero-weight slot to verify drop.
    mesh = MeshData(
        name="m",
        positions=np.zeros((3, 3), dtype=np.float32),
        triangles=np.zeros((0, 3), dtype=np.uint32),
        bone_indices=np.array(
            [[0, 1], [0, 1], [1, 0]], dtype=np.uint8
        ),
        bone_weights=np.array(
            [[1.0, 0.0], [0.5, 0.5], [0.25, 0.75]], dtype=np.float32
        ),
    )

    skin = bsgeometry_skin_to_skin_data(geom, table, mesh)

    assert skin is not None
    assert skin.bone_names == ["Spine", "Head"]
    # Five non-zero influences: vertex 0 -> Spine 1.0, vertex 1 -> Spine/Head 0.5,
    # vertex 2 -> Head 0.25, vertex 2 -> Spine 0.75.
    assert skin.vertex_indices.size == 5
    assert skin.bone_indices.size == 5
    assert skin.weights.size == 5
    np.testing.assert_array_equal(skin.weights > 0.0, np.ones(5, dtype=bool))


def test_bsgeometry_skin_apply_to_object_creates_vertex_groups() -> None:
    alloc = _StringIndexAllocator()
    from nifblend.format.generated.blocks import NiNode

    node_a = NiNode()
    node_a.name = _name_obj(alloc.string_index_for("Spine"))
    node_b = NiNode()
    node_b.name = _name_obj(alloc.string_index_for("Head"))
    inst = _bsskin_instance(bone_refs=[1, 2])
    geom = _bsgeometry_with_skin(0)
    table = _table(strings=alloc.strings, blocks=[inst, node_a, node_b])

    mesh = MeshData(
        name="m",
        positions=np.zeros((2, 3), dtype=np.float32),
        triangles=np.zeros((0, 3), dtype=np.uint32),
        bone_indices=np.array([[0, 1], [1, 0]], dtype=np.uint8),
        bone_weights=np.array([[0.7, 0.3], [0.4, 0.6]], dtype=np.float32),
    )
    skin = bsgeometry_skin_to_skin_data(geom, table, mesh)
    assert skin is not None

    obj = _FakeObject()
    apply_skin_to_object(skin, obj)
    by_name = {vg.name: vg for vg in obj.vertex_groups.created}
    assert set(by_name) == {"Spine", "Head"}
    # Every group should have at least one .add() call.
    assert all(vg.calls for vg in by_name.values())
