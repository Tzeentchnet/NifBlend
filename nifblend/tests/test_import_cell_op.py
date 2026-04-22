"""Phase 8j: cell-importer mesh-instancing test.

The headline win over NifCity is that a 50-row CSV that references
**one** ``.nif`` file produces exactly **one** ``bpy.data.meshes``
datablock and 50 objects that all share it (when
``instance_duplicates=True``). With the toggle off, every row gets its
own ``mesh.copy()``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import bpy
import pytest

import nifblend.ops.import_cell as import_cell_mod
from nifblend.ops.import_batch import BatchFileResult
from nifblend.ops.import_cell import NIFBLEND_OT_import_cell

# ---- fake bpy data layer ------------------------------------------------


class _FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.linked_objects: list[Any] = []
        self.children_collections: list[_FakeCollection] = []
        self.objects = SimpleNamespace(link=self.linked_objects.append)
        self.children = SimpleNamespace(link=self.children_collections.append)


class _FakeMesh:
    """Stand-in for a ``bpy.types.Mesh`` datablock created by the bridge."""

    _counter = 0

    def __init__(self, name: str) -> None:
        type(self)._counter += 1
        self.name = name
        self.id = type(self)._counter

    def copy(self) -> _FakeMesh:
        return _FakeMesh(f"{self.name}.copy{type(self)._counter}")


class _FakeObject:
    def __init__(self, name: str, data: Any) -> None:
        self.name = name
        self.data = data
        self.location = (0.0, 0.0, 0.0)
        self.rotation_mode = "XYZ"
        self.rotation_euler = (0.0, 0.0, 0.0)
        self.scale = (1.0, 1.0, 1.0)


@pytest.fixture
def fake_bpy(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Wire the minimum ``bpy.data`` surface the cell importer touches."""

    created_collections: list[_FakeCollection] = []
    created_objects: list[_FakeObject] = []

    def _new_collection(name: str) -> _FakeCollection:
        coll = _FakeCollection(name)
        created_collections.append(coll)
        return coll

    def _new_object(name: str, data: Any) -> _FakeObject:
        obj = _FakeObject(name, data)
        created_objects.append(obj)
        return obj

    monkeypatch.setattr(
        bpy,
        "data",
        SimpleNamespace(
            collections=SimpleNamespace(new=_new_collection),
            objects=SimpleNamespace(new=_new_object),
        ),
        raising=False,
    )
    return SimpleNamespace(collections=created_collections, objects=created_objects)


def _ctx() -> SimpleNamespace:
    scene_collection = _FakeCollection("Scene")
    scene = SimpleNamespace(collection=scene_collection)
    return SimpleNamespace(scene=scene, collection=scene_collection)


def _write_cell_csv(path: Path, model_relpath: str, rows: int) -> None:
    lines = ["# model,x,y,z,rx,ry,rz,scale"]
    for i in range(rows):
        lines.append(f"{model_relpath},{i * 10.0},{i * 5.0},{i},0,0,0,1.0")
    path.write_text("\n".join(lines), encoding="utf-8")


def _patch_parse_and_decode(
    monkeypatch: pytest.MonkeyPatch, full_path: Path
) -> list[_FakeMesh]:
    """Return a list that records every mesh datablock the bridge produced."""
    produced: list[_FakeMesh] = []

    fake_mesh_data = object()  # opaque marker -- bridge stub returns a fresh _FakeMesh

    def _fake_parse_many(paths: list[Path], *, max_workers: int | None = None):
        return [
            BatchFileResult(path=Path(p), meshes=[fake_mesh_data]) for p in paths
        ]

    def _fake_mesh_data_to_blender(_mdata: Any) -> _FakeMesh:
        m = _FakeMesh(full_path.stem)
        produced.append(m)
        return m

    monkeypatch.setattr(import_cell_mod, "parse_and_decode_many", _fake_parse_many)
    monkeypatch.setattr(
        import_cell_mod, "mesh_data_to_blender", _fake_mesh_data_to_blender
    )
    return produced


# ---- the headline test --------------------------------------------------


def test_50_rows_one_nif_produces_one_mesh_and_50_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy: SimpleNamespace,
) -> None:
    mesh_root = tmp_path / "Meshes"
    mesh_root.mkdir()
    nif_relpath = "stone.nif"
    nif_full = mesh_root / nif_relpath
    nif_full.write_bytes(b"\x00")  # Path.exists() must return True

    csv_path = tmp_path / "cell.csv"
    _write_cell_csv(csv_path, nif_relpath, rows=50)

    produced_meshes = _patch_parse_and_decode(monkeypatch, nif_full)

    op = NIFBLEND_OT_import_cell()
    op.filepath = str(csv_path)
    op.mesh_root = str(mesh_root)
    op.normalize_location = False
    op.instance_duplicates = True
    op.exclude_prefixes = ""
    op.worker_count = 0
    op.report = lambda *_a, **_kw: None

    assert op.execute(_ctx()) == {"FINISHED"}

    # One unique path → one decode → one Blender mesh datablock.
    assert len(produced_meshes) == 1
    # 50 rows → 50 objects.
    assert len(fake_bpy.objects) == 50
    # All objects share the same mesh data (the headline NifCity fix).
    shared = produced_meshes[0]
    assert all(obj.data is shared for obj in fake_bpy.objects)
    # All 50 went into the cell collection nested under the scene.
    cell_coll = fake_bpy.collections[0]
    assert len(cell_coll.linked_objects) == 50


def test_instance_duplicates_off_copies_per_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy: SimpleNamespace,
) -> None:
    mesh_root = tmp_path / "Meshes"
    mesh_root.mkdir()
    nif_full = mesh_root / "stone.nif"
    nif_full.write_bytes(b"\x00")
    csv_path = tmp_path / "cell.csv"
    _write_cell_csv(csv_path, "stone.nif", rows=4)

    _patch_parse_and_decode(monkeypatch, nif_full)

    op = NIFBLEND_OT_import_cell()
    op.filepath = str(csv_path)
    op.mesh_root = str(mesh_root)
    op.normalize_location = False
    op.instance_duplicates = False
    op.exclude_prefixes = ""
    op.worker_count = 0
    op.report = lambda *_a, **_kw: None
    op.execute(_ctx())

    # 4 objects → 4 distinct mesh datablocks (no sharing).
    data_ids = {id(o.data) for o in fake_bpy.objects}
    assert len(fake_bpy.objects) == 4
    assert len(data_ids) == 4


def test_marker_and_fx_rows_are_skipped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy: SimpleNamespace,
) -> None:
    mesh_root = tmp_path / "Meshes"
    mesh_root.mkdir()
    keep = mesh_root / "stone.nif"
    keep.write_bytes(b"\x00")
    marker = mesh_root / "marker_arrow.nif"
    marker.write_bytes(b"\x00")
    fx = mesh_root / "fx_smoke.nif"
    fx.write_bytes(b"\x00")

    csv_path = tmp_path / "cell.csv"
    csv_path.write_text(
        "\n".join(
            [
                "# model,x,y,z,rx,ry,rz,scale",
                "stone.nif,0,0,0,0,0,0,1",
                "marker_arrow.nif,1,1,1,0,0,0,1",
                "fx_smoke.nif,2,2,2,0,0,0,1",
                "stone.nif,3,3,3,0,0,0,1",
            ]
        ),
        encoding="utf-8",
    )

    _patch_parse_and_decode(monkeypatch, keep)

    op = NIFBLEND_OT_import_cell()
    op.filepath = str(csv_path)
    op.mesh_root = str(mesh_root)
    op.normalize_location = False
    op.instance_duplicates = True
    op.exclude_prefixes = "marker,fx"
    op.worker_count = 0
    op.report = lambda *_a, **_kw: None
    op.execute(_ctx())

    # Only the two ``stone.nif`` rows survive the prefix filter.
    assert len(fake_bpy.objects) == 2


def test_missing_mesh_root_returns_cancelled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy: SimpleNamespace,
) -> None:
    mesh_root = tmp_path / "Meshes"
    mesh_root.mkdir()  # empty -- no .nif files exist
    csv_path = tmp_path / "cell.csv"
    _write_cell_csv(csv_path, "ghost.nif", rows=3)

    _patch_parse_and_decode(monkeypatch, mesh_root / "ghost.nif")

    op = NIFBLEND_OT_import_cell()
    op.filepath = str(csv_path)
    op.mesh_root = str(mesh_root)
    op.normalize_location = False
    op.instance_duplicates = True
    op.exclude_prefixes = ""
    op.worker_count = 0
    op.report = lambda *_a, **_kw: None
    assert op.execute(_ctx()) == {"CANCELLED"}
    assert fake_bpy.objects == []


def test_normalize_location_subtracts_centroid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_bpy: SimpleNamespace,
) -> None:
    mesh_root = tmp_path / "Meshes"
    mesh_root.mkdir()
    nif_full = mesh_root / "stone.nif"
    nif_full.write_bytes(b"\x00")
    csv_path = tmp_path / "cell.csv"
    csv_path.write_text(
        "\n".join(
            [
                "# model,x,y,z,rx,ry,rz,scale",
                "stone.nif,100,200,300,0,0,0,1",
                "stone.nif,200,300,400,0,0,0,1",
            ]
        ),
        encoding="utf-8",
    )

    _patch_parse_and_decode(monkeypatch, nif_full)

    op = NIFBLEND_OT_import_cell()
    op.filepath = str(csv_path)
    op.mesh_root = str(mesh_root)
    op.normalize_location = True
    op.instance_duplicates = True
    op.exclude_prefixes = ""
    op.worker_count = 0
    op.report = lambda *_a, **_kw: None
    op.execute(_ctx())

    # Centroid is (150, 250, 350); both rows should be re-centred symmetrically.
    locs = [o.location for o in fake_bpy.objects]
    assert locs == [(-50.0, -50.0, -50.0), (50.0, 50.0, 50.0)]
