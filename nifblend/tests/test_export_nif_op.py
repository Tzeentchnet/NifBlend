"""Phase 5 -- ``ops/export_nif.py`` orchestration tests.

Until this test module landed, the export operator's orchestration was
covered only indirectly through the pre-existing bare-geometry round-trip
tests (see docs/REVIEW_2026-07.md findings 1 + 2). Covers the new pieces:

* Object transform -> NIF translation/rotation/scale
  (``object_transform_to_shape_trs``), verified by round-tripping through
  the *import*-side decomposition (``armature_in.world_matrix_to_trs``)
  so the two directions are proven consistent with each other.
* Sparse ``SkinData`` -> dense per-vertex ``(N, 4)`` arrays
  (``_sparse_skin_to_dense``).
* Armature discovery (``_find_armature``).
* ``build_export_table``: rigid mesh (no material/armature), mesh with a
  material, and mesh with skin + shared armature (two meshes on one
  armature build it exactly once) -- each verified with a real
  ``write_nif`` -> ``read_nif`` byte round-trip.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.mesh_in import MeshData
from nifblend.bridge.skin_in import SkinData
from nifblend.format.generated.blocks import (
    BSLightingShaderProperty,
    NiSkinInstance,
    NiTriShape,
)
from nifblend.io.block_table import read_nif
from nifblend.ops import export_nif as export_nif_mod
from nifblend.ops.export_nif import (
    NIFBLEND_OT_export_nif,
    _euler_xyz_to_matrix3,
    _find_armature,
    _quaternion_to_matrix3,
    _sparse_skin_to_dense,
    build_export_table,
    object_transform_to_shape_trs,
)

# ---------------------------------------------------------------------------
# object_transform_to_shape_trs (round-tripped against the import-side
# decomposition so both directions are proven mutually consistent)
# ---------------------------------------------------------------------------


def test_object_transform_identity() -> None:
    obj = SimpleNamespace(
        location=(0.0, 0.0, 0.0),
        rotation_mode="XYZ",
        rotation_euler=(0.0, 0.0, 0.0),
        scale=(1.0, 1.0, 1.0),
    )
    translation, rotation, scale = object_transform_to_shape_trs(obj)
    assert (translation.x, translation.y, translation.z) == (0.0, 0.0, 0.0)
    assert scale == pytest.approx(1.0)
    assert rotation.m11 == pytest.approx(1.0)
    assert rotation.m22 == pytest.approx(1.0)
    assert rotation.m33 == pytest.approx(1.0)


def test_object_transform_round_trips_through_import_decomposition() -> None:
    from nifblend.bridge.armature_in import world_matrix_to_trs

    obj = SimpleNamespace(
        location=(1.0, 2.0, 3.0),
        rotation_mode="XYZ",
        rotation_euler=(0.3, -0.2, 0.6),
        scale=(2.0, 2.0, 2.0),
    )
    translation, rotation, scale = object_transform_to_shape_trs(obj)

    m = np.eye(4, dtype=np.float32)
    m[0, 0], m[0, 1], m[0, 2] = rotation.m11, rotation.m12, rotation.m13
    m[1, 0], m[1, 1], m[1, 2] = rotation.m21, rotation.m22, rotation.m23
    m[2, 0], m[2, 1], m[2, 2] = rotation.m31, rotation.m32, rotation.m33
    m[:3, :3] *= scale
    m[0, 3], m[1, 3], m[2, 3] = translation.x, translation.y, translation.z

    loc2, euler2, scale2 = world_matrix_to_trs(m)
    assert loc2 == pytest.approx((1.0, 2.0, 3.0))
    assert scale2 == pytest.approx(2.0)
    np.testing.assert_allclose(euler2, (0.3, -0.2, 0.6), atol=1e-4)


def test_object_transform_quaternion_mode() -> None:
    # 90-degree rotation about Z as a quaternion.
    half = math.pi / 4
    obj = SimpleNamespace(
        location=(0.0, 0.0, 0.0),
        rotation_mode="QUATERNION",
        rotation_quaternion=(math.cos(half), 0.0, 0.0, math.sin(half)),
        scale=(1.0, 1.0, 1.0),
    )
    _translation, rotation, _scale = object_transform_to_shape_trs(obj)
    expected = _euler_xyz_to_matrix3(0.0, 0.0, math.pi / 2)
    np.testing.assert_allclose(
        [
            [rotation.m11, rotation.m12, rotation.m13],
            [rotation.m21, rotation.m22, rotation.m23],
            [rotation.m31, rotation.m32, rotation.m33],
        ],
        expected,
        atol=1e-5,
    )


def test_object_transform_missing_attrs_default_to_identity() -> None:
    translation, rotation, scale = object_transform_to_shape_trs(SimpleNamespace())
    assert (translation.x, translation.y, translation.z) == (0.0, 0.0, 0.0)
    assert scale == pytest.approx(1.0)
    assert rotation.m11 == pytest.approx(1.0)


def test_quaternion_to_matrix3_identity() -> None:
    m = _quaternion_to_matrix3(1.0, 0.0, 0.0, 0.0)
    np.testing.assert_allclose(m, np.eye(3), atol=1e-8)


# ---------------------------------------------------------------------------
# _sparse_skin_to_dense
# ---------------------------------------------------------------------------


def test_sparse_skin_to_dense_basic() -> None:
    skin = SkinData(
        bone_names=["A", "B"],
        vertex_indices=np.array([0, 0, 1], dtype=np.uint32),
        bone_indices=np.array([0, 1, 0], dtype=np.uint32),
        weights=np.array([0.5, 0.5, 1.0], dtype=np.float32),
    )
    idx, wt = _sparse_skin_to_dense(skin, num_vertices=2)
    assert idx.shape == (2, 4)
    assert wt.shape == (2, 4)
    assert wt[0].sum() == pytest.approx(1.0)
    assert wt[1, 0] == pytest.approx(1.0)


def test_sparse_skin_to_dense_prunes_beyond_four_and_renormalises() -> None:
    skin = SkinData(
        bone_names=["A", "B", "C", "D", "E"],
        vertex_indices=np.zeros(5, dtype=np.uint32),
        bone_indices=np.array([0, 1, 2, 3, 4], dtype=np.uint32),
        weights=np.array([0.1, 0.5, 0.05, 0.3, 0.05], dtype=np.float32),
    )
    idx, wt = _sparse_skin_to_dense(skin, num_vertices=1)
    assert wt[0].sum() == pytest.approx(1.0)
    # The lowest two weights (0.05, 0.05) get pruned; bone 1 (0.5) survives.
    assert 1 in idx[0].tolist()


def test_sparse_skin_to_dense_empty_skin() -> None:
    idx, wt = _sparse_skin_to_dense(SkinData(), num_vertices=3)
    assert idx.shape == (3, 4)
    assert not wt.any()


# ---------------------------------------------------------------------------
# _find_armature
# ---------------------------------------------------------------------------


def test_find_armature_via_parent() -> None:
    rig = SimpleNamespace(type="ARMATURE")
    obj = SimpleNamespace(parent=rig, modifiers=[])
    assert _find_armature(obj) is rig


def test_find_armature_via_modifier() -> None:
    rig = SimpleNamespace(type="ARMATURE")
    obj = SimpleNamespace(parent=None, modifiers=[SimpleNamespace(type="ARMATURE", object=rig)])
    assert _find_armature(obj) is rig


def test_find_armature_none_when_absent() -> None:
    obj = SimpleNamespace(parent=None, modifiers=[])
    assert _find_armature(obj) is None


# ---------------------------------------------------------------------------
# build_export_table -- end-to-end fixtures
# ---------------------------------------------------------------------------


class _FakeMeshDataHolder:
    """Stand-in for ``bpy.types.Mesh``: carries a pre-built MeshData payload
    plus whatever else ``build_export_table`` reads off ``obj.data``
    directly (materials, per-vertex groups for skin harvesting)."""

    def __init__(
        self,
        payload: MeshData,
        *,
        materials: list[Any] | None = None,
        vertices: list[Any] | None = None,
    ) -> None:
        self.payload = payload
        self.materials = materials or []
        self.vertices = vertices or []


@pytest.fixture(autouse=True)
def _patch_mesh_data_from_blender(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake(data: Any, *, name: str | None = None) -> MeshData:
        if isinstance(data, _FakeMeshDataHolder):
            return data.payload
        raise AssertionError("expected a _FakeMeshDataHolder in tests")

    monkeypatch.setattr(export_nif_mod, "mesh_data_from_blender", _fake)


def _triangle_mesh_data(name: str) -> MeshData:
    return MeshData(
        name=name,
        positions=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
    )


def _fake_object(
    name: str,
    *,
    materials: list[Any] | None = None,
    vertices: list[Any] | None = None,
    parent: Any = None,
    vertex_groups: list[Any] | None = None,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> SimpleNamespace:
    return SimpleNamespace(
        type="MESH",
        name=name,
        data=_FakeMeshDataHolder(_triangle_mesh_data(name), materials=materials, vertices=vertices),
        location=location,
        rotation_mode="XYZ",
        rotation_euler=(0.0, 0.0, 0.0),
        scale=(1.0, 1.0, 1.0),
        parent=parent,
        modifiers=[],
        vertex_groups=vertex_groups or [],
    )


def test_build_export_table_rigid_mesh_single_block() -> None:
    obj = _fake_object("Rock", location=(5.0, 0.0, 0.0))
    table = build_export_table([obj])
    assert len(table.blocks) == 1
    assert isinstance(table.blocks[0], NiTriShape) is False  # BSTriShape, not classic
    assert table.footer.roots == [0]


def test_build_export_table_non_mesh_objects_are_skipped() -> None:
    not_mesh = SimpleNamespace(type="EMPTY", name="Helper")
    obj = _fake_object("Rock")
    table = build_export_table([not_mesh, obj])
    assert len(table.blocks) == 1


def test_build_export_table_writes_and_rereads_transform(tmp_path: Any) -> None:
    import io

    from nifblend.io.block_table import write_nif

    obj = _fake_object("Rock", location=(5.0, 2.0, 1.0))
    table = build_export_table([obj])
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))
    shape = parsed.blocks[0]
    assert shape.translation.x == pytest.approx(5.0)
    assert shape.translation.y == pytest.approx(2.0)
    assert shape.translation.z == pytest.approx(1.0)


def test_build_export_table_with_material_sets_shader_property() -> None:
    mat = SimpleNamespace(name="Mat", use_nodes=False, blend_method="OPAQUE")
    obj = _fake_object("Rock", materials=[mat])
    table = build_export_table([obj])
    assert len(table.blocks) == 2  # shader property + shape
    shape = table.blocks[-1]
    assert shape.shader_property == 0
    assert isinstance(table.blocks[0], BSLightingShaderProperty)


class _FakeBone:
    def __init__(self, name: str, parent: Any = None) -> None:
        self.name = name
        self.parent = parent
        self.children: list[_FakeBone] = []
        self.nifblend = SimpleNamespace(
            has_bind_matrix=True,
            bind_matrix=tuple(np.eye(4, dtype=np.float32).reshape(-1).tolist()),
        )


class _FakeVertex:
    def __init__(self, index: int, groups: list[SimpleNamespace]) -> None:
        self.index = index
        self.groups = groups


def _fake_armature(name: str, bone_names: list[str]) -> SimpleNamespace:
    bones = [_FakeBone(bone_names[0])]
    for n in bone_names[1:]:
        bones.append(_FakeBone(n, parent=bones[0]))
        bones[0].children.append(bones[-1])
    return SimpleNamespace(type="ARMATURE", name=name, data=SimpleNamespace(bones=bones))


def test_build_export_table_skinned_mesh_builds_armature_and_skin() -> None:
    rig = _fake_armature("Rig", ["Root"])
    vg = SimpleNamespace(name="Root")
    vertices = [
        _FakeVertex(0, [SimpleNamespace(group=0, weight=1.0)]),
        _FakeVertex(1, [SimpleNamespace(group=0, weight=1.0)]),
        _FakeVertex(2, [SimpleNamespace(group=0, weight=1.0)]),
    ]
    obj = _fake_object("Rock", parent=rig, vertex_groups=[vg], vertices=vertices)

    table = build_export_table([obj])

    shape = table.blocks[-1]
    assert shape.skin != -1
    skin_inst = table.blocks[shape.skin]
    assert isinstance(skin_inst, NiSkinInstance)
    assert skin_inst.skeleton_root != -1
    # Root bone block + skin data + skin instance + shape == 4 blocks.
    assert len(table.blocks) == 4


def test_build_export_table_shared_armature_built_once() -> None:
    rig = _fake_armature("Rig", ["Root"])
    vg = SimpleNamespace(name="Root")
    vertices = [_FakeVertex(i, [SimpleNamespace(group=0, weight=1.0)]) for i in range(3)]
    obj_a = _fake_object("A", parent=rig, vertex_groups=[vg], vertices=vertices)
    obj_b = _fake_object("B", parent=rig, vertex_groups=[vg], vertices=vertices)

    table = build_export_table([obj_a, obj_b])

    root_nodes = [
        b for b in table.blocks if getattr(b, "name", None) is not None and hasattr(b, "children")
    ]
    # Exactly one NiNode (the shared armature root) even though two shapes
    # reference it.
    assert len(root_nodes) == 1
    assert len(root_nodes[0].children) == 2  # both shapes parented under it


def test_build_export_table_full_round_trip_with_skin_and_material(tmp_path: Any) -> None:
    import io

    from nifblend.io.block_table import write_nif

    rig = _fake_armature("Rig", ["Root"])
    vg = SimpleNamespace(name="Root")
    vertices = [_FakeVertex(i, [SimpleNamespace(group=0, weight=1.0)]) for i in range(3)]
    mat = SimpleNamespace(name="Mat", use_nodes=False, blend_method="OPAQUE")
    obj = _fake_object(
        "Rock",
        parent=rig,
        vertex_groups=[vg],
        vertices=vertices,
        materials=[mat],
        location=(1.0, 0.0, 0.0),
    )

    table = build_export_table([obj])
    sink = io.BytesIO()
    write_nif(sink, table)
    parsed = read_nif(io.BytesIO(sink.getvalue()))

    shape = next(b for b in parsed.blocks if hasattr(b, "vertex_desc"))
    assert shape.translation.x == pytest.approx(1.0)
    assert shape.shader_property != -1
    assert shape.skin != -1
    skin_inst = parsed.blocks[shape.skin]
    assert skin_inst.skeleton_root != -1


# ---------------------------------------------------------------------------
# operator-level execute()
# ---------------------------------------------------------------------------


def test_execute_rejects_no_mesh_selection() -> None:
    op = NIFBLEND_OT_export_nif()
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]
    ctx = SimpleNamespace(selected_objects=[])
    assert op.execute(ctx) == {"CANCELLED"}
    assert any("Select at least one mesh" in msg for _, msg in reports)


def test_execute_happy_path_writes_file(tmp_path: Any) -> None:
    obj = _fake_object("Rock")
    op = NIFBLEND_OT_export_nif()
    op.filepath = str(tmp_path / "rock.nif")
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]
    ctx = SimpleNamespace(selected_objects=[obj])

    assert op.execute(ctx) == {"FINISHED"}
    assert (tmp_path / "rock.nif").exists()
    assert any("Exported 1 mesh" in msg for _, msg in reports)
