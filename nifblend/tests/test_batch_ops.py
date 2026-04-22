"""Phase 7 step 27 — batch import / export operator tests.

Drives the parallel parse+decode and parallel write helpers against
real on-disk NIFs (synthesised in-memory via the Phase 2 round-trip
fixture) so the threading path is actually exercised. ``bpy`` is the
conftest stub; we pass a fake ``bpy`` to :func:`materialise_batch_results`
so the headless suite never touches Blender APIs.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from nifblend.bridge.mesh_in import MeshData
from nifblend.bridge.mesh_out import mesh_data_to_bstrishape
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import BSTriShape
from nifblend.format.generated.structs import BSStreamHeader, ExportString, Footer, Header
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable, write_nif
from nifblend.ops.export_batch import (
    build_tables,
    write_tables,
)
from nifblend.ops.import_batch import (
    discover_nif_files,
    materialise_batch_results,
    parse_and_decode,
    parse_and_decode_many,
)

# ---- fixtures -------------------------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _sse_table(blocks: list[BSTriShape]) -> BlockTable:
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100,
            author=_empty_export_string(),
            process_script=_empty_export_string(),
            export_script=_empty_export_string(),
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return BlockTable(header=h, blocks=list(blocks), footer=Footer(), ctx=ctx)


def _triangle(name: str) -> MeshData:
    return MeshData(
        name=name,
        positions=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            dtype=np.float32,
        ),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        normals=np.array([[0.0, 0.0, 1.0]] * 3, dtype=np.float32),
        uv=np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )


def _write_nif_to(path: Path, mdata: MeshData) -> None:
    table = _sse_table([mesh_data_to_bstrishape(mdata, full_precision=True)])
    sink = io.BytesIO()
    write_nif(sink, table)
    path.write_bytes(sink.getvalue())


@pytest.fixture
def nif_folder(tmp_path: Path) -> Path:
    """A folder with three valid NIFs and one bogus file."""
    (tmp_path / "sub").mkdir()
    _write_nif_to(tmp_path / "a.nif", _triangle("a_mesh"))
    _write_nif_to(tmp_path / "b.nif", _triangle("b_mesh"))
    _write_nif_to(tmp_path / "sub" / "c.nif", _triangle("c_mesh"))
    (tmp_path / "junk.nif").write_bytes(b"not a real NIF, header will fail")
    (tmp_path / "ignored.txt").write_text("ignore me")
    return tmp_path


# ---- discover_nif_files ---------------------------------------------------


def test_discover_recursive_finds_every_nif(nif_folder: Path) -> None:
    found = discover_nif_files(nif_folder, recursive=True)
    names = sorted(p.name for p in found)
    assert names == ["a.nif", "b.nif", "c.nif", "junk.nif"]


def test_discover_non_recursive_skips_subdirs(nif_folder: Path) -> None:
    found = discover_nif_files(nif_folder, recursive=False)
    names = sorted(p.name for p in found)
    assert names == ["a.nif", "b.nif", "junk.nif"]


def test_discover_rejects_non_directory(tmp_path: Path) -> None:
    f = tmp_path / "x.nif"
    f.write_bytes(b"")
    with pytest.raises(NotADirectoryError):
        discover_nif_files(f)


# ---- parse_and_decode -----------------------------------------------------


def test_parse_and_decode_returns_meshdata(nif_folder: Path) -> None:
    res = parse_and_decode(nif_folder / "a.nif")
    assert res.error is None
    assert len(res.meshes) == 1
    # Names round-trip through the BSTriShape string table is a Phase 2.9
    # follow-up; for now the bridge falls back to the block type name.
    assert res.meshes[0].name in {"a_mesh", "BSTriShape"}
    assert res.skipped == []


def test_parse_and_decode_captures_error_on_bad_file(nif_folder: Path) -> None:
    res = parse_and_decode(nif_folder / "junk.nif")
    assert res.error is not None
    assert "read failed" in res.error
    assert res.meshes == []


def test_parse_and_decode_many_preserves_order(nif_folder: Path) -> None:
    paths = [nif_folder / "b.nif", nif_folder / "a.nif", nif_folder / "junk.nif"]
    results = parse_and_decode_many(paths, max_workers=2)
    assert [r.path for r in results] == paths
    assert len(results[0].meshes) == 1
    assert len(results[1].meshes) == 1
    assert results[2].error is not None


def test_parse_and_decode_many_empty_input() -> None:
    assert parse_and_decode_many([]) == []


# ---- materialise_batch_results -------------------------------------------


class _FakeMesh:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeObj:
    def __init__(self, mesh: _FakeMesh) -> None:
        self.name = mesh.name
        self.data = mesh


class _FakeCollection:
    def __init__(self, name: str = "Scene") -> None:
        self.name = name
        self.objects = SimpleNamespace(linked=[], link=lambda o: self.objects.linked.append(o))
        self.children = SimpleNamespace(linked=[], link=lambda c: self.children.linked.append(c))


class _FakeMeshes:
    def new(self, name: str) -> _FakeMesh:
        return _FakeMesh(name)


class _FakeObjects:
    def new(self, name: str, data: _FakeMesh) -> _FakeObj:
        return _FakeObj(data)


class _FakeCollections:
    def __init__(self) -> None:
        self.created: list[_FakeCollection] = []

    def new(self, name: str) -> _FakeCollection:
        c = _FakeCollection(name)
        self.created.append(c)
        return c


def _fake_bpy_for_materialise() -> SimpleNamespace:
    """Build a stand-in for ``bpy`` that satisfies materialise_batch_results.

    Only the surface :func:`mesh_data_to_blender` and
    :func:`materialise_batch_results` actually touch is implemented.
    """
    scene_collection = _FakeCollection("Scene")
    scene = SimpleNamespace(collection=scene_collection)
    return SimpleNamespace(
        context=SimpleNamespace(scene=scene),
        data=SimpleNamespace(
            meshes=_FakeMeshes(),
            objects=_FakeObjects(),
            collections=_FakeCollections(),
        ),
    )


def test_materialise_creates_one_collection_per_file(nif_folder: Path) -> None:
    results = parse_and_decode_many(
        [nif_folder / "a.nif", nif_folder / "b.nif"], max_workers=2
    )
    fake = _fake_bpy_for_materialise()
    # mesh_data_to_blender expects a richer mesh API; stub it out.
    fake.data.meshes = SimpleNamespace(
        new=lambda name: _StubMesh(name)
    )
    imported, errors = materialise_batch_results(results, bpy=fake)
    assert imported == 2
    assert errors == []
    assert [c.name for c in fake.data.collections.created] == ["a", "b"]
    # Each collection received exactly one object.
    assert all(len(c.objects.linked) == 1 for c in fake.data.collections.created)


def test_materialise_aggregates_errors(nif_folder: Path) -> None:
    results = parse_and_decode_many([nif_folder / "junk.nif"])
    fake = _fake_bpy_for_materialise()
    fake.data.meshes = SimpleNamespace(new=lambda name: _StubMesh(name))
    imported, errors = materialise_batch_results(results, bpy=fake)
    assert imported == 0
    assert len(errors) == 1
    assert "junk.nif" in errors[0]


# ---- export side: build_tables + write_tables ----------------------------


class _StubMesh:
    """Stand-in for ``bpy.types.Mesh`` that exposes ``mesh_data_to_blender``'s API."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.uv_layers = SimpleNamespace(new=lambda **kw: SimpleNamespace(
            data=SimpleNamespace(foreach_set=lambda *a, **kw: None)
        ))
        self.color_attributes = SimpleNamespace(new=lambda **kw: SimpleNamespace(
            data=SimpleNamespace(foreach_set=lambda *a, **kw: None)
        ))

    def from_pydata(self, *_a, **_kw) -> None: ...
    def normals_split_custom_set(self, *_a, **_kw) -> None: ...
    def update(self) -> None: ...


def test_build_tables_emits_one_per_selected_mesh(tmp_path: Path) -> None:
    a = SimpleNamespace(
        type="MESH",
        name="alpha",
        data=_make_export_meshdata("alpha"),
    )
    b = SimpleNamespace(
        type="MESH",
        name="beta",
        data=_make_export_meshdata("beta"),
    )
    not_mesh = SimpleNamespace(type="ARMATURE", name="rig", data=None)
    items = build_tables([a, not_mesh, b], tmp_path)
    assert [i.path.name for i in items] == ["alpha.nif", "beta.nif"]
    assert all(isinstance(i.table, BlockTable) for i in items)
    assert all(len(i.table.blocks) == 1 for i in items)


def test_write_tables_writes_files_in_parallel(tmp_path: Path) -> None:
    a = SimpleNamespace(type="MESH", name="alpha", data=_make_export_meshdata("alpha"))
    b = SimpleNamespace(type="MESH", name="beta", data=_make_export_meshdata("beta"))
    items = build_tables([a, b], tmp_path)
    results = write_tables(items, max_workers=2)
    assert all(r.error is None for r in results)
    assert all(r.bytes_written > 0 for r in results)
    assert (tmp_path / "alpha.nif").is_file()
    assert (tmp_path / "beta.nif").is_file()
    # Round-trip the freshly-written files through the import side.
    re_results = parse_and_decode_many(
        [tmp_path / "alpha.nif", tmp_path / "beta.nif"], max_workers=2
    )
    # Two single-mesh files round-tripped successfully; name preservation
    # through the string table is a known Phase 2.9 follow-up.
    assert all(len(r.meshes) == 1 for r in re_results)
    assert all(r.error is None for r in re_results)


def test_write_tables_creates_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deeply" / "nested"
    a = SimpleNamespace(type="MESH", name="alpha", data=_make_export_meshdata("alpha"))
    items = build_tables([a], nested)
    results = write_tables(items)
    assert results[0].error is None
    assert (nested / "alpha.nif").is_file()


def test_write_tables_empty_input_returns_empty_list() -> None:
    assert write_tables([]) == []


# ---- export-side helpers --------------------------------------------------


def _make_export_meshdata(name: str) -> SimpleNamespace:
    """Build a fake ``bpy.types.Mesh`` matching what ``export_bstrishape`` reads.

    The export bridge consumes the mesh through the public ``foreach_get``
    API; rather than mock all of that, we pre-build a real ``MeshData``
    here and substitute the Blender side with a wrapper that returns it.

    The simpler and less brittle path: drive ``build_tables`` with a real
    mesh-shaped object whose ``data`` attribute is the source ``MeshData``
    converted directly to a ``BSTriShape`` outside the bridge. We rebind
    the bridge entry point on the local module for the test.
    """
    return _PreBuiltMeshData(_triangle(name))


class _PreBuiltMeshData:
    """Carries a MeshData payload that ``export_bstrishape`` won't touch.

    ``build_tables`` calls ``export_bstrishape(obj.data, name=obj.name)``;
    we replace ``export_bstrishape`` in the module under test below to
    pull the payload back out instead of running the full bridge (which
    would require a real bpy mesh).
    """

    def __init__(self, mdata: MeshData) -> None:
        self.payload = mdata


@pytest.fixture(autouse=True)
def _patch_export_bstrishape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route ``export_bstrishape`` through the pre-built MeshData payload."""
    from nifblend.bridge import mesh_out
    from nifblend.ops import export_batch

    def _fake(data: object, *, name: str) -> BSTriShape:
        if isinstance(data, _PreBuiltMeshData):
            return mesh_data_to_bstrishape(data.payload, full_precision=True)
        return mesh_out.export_bstrishape(data, name=name)

    monkeypatch.setattr(export_batch, "export_bstrishape", _fake)
