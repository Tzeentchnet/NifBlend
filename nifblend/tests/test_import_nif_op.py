"""Phase 4 -- ``ops/import_nif.py`` orchestration tests.

Until this test module landed, ``NIFBLEND_OT_import_nif`` had zero
dedicated coverage even though it's the addon's primary import path (see
docs/REVIEW_2026-07.md findings 1 + 2). Covers the new orchestration
helpers added to close those gaps:

* Per-shape world-transform placement (``_apply_shape_transform``).
* Modern (``shader_property``/``alpha_property``) and classic
  (``.properties`` list) material resolution + sharing
  (``_resolve_shape_material``).
* Skin-ref resolution across the ``skin`` / ``skin_instance`` field-name
  split (``_resolve_skin_ref``) and skeleton-once-per-file armature
  building (``_ensure_armature``).
* End-to-end ``execute()`` smoke tests for both the modern BSTriShape
  path (skin + material + armature, two shapes sharing one skeleton) and
  the classic NiTriShape path (``.properties``-list material).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from nifblend.bridge.material_in import MaterialData
from nifblend.bridge.material_out import material_data_to_bslighting
from nifblend.bridge.mesh_in import MeshData
from nifblend.bridge.mesh_out import mesh_data_to_bstrishape
from nifblend.format.generated.blocks import (
    BSLightingShaderProperty,
    NiMaterialProperty,
    NiNode,
    NiSkinInstance,
    NiTexturingProperty,
    NiTriShape,
    NiTriShapeData,
)
from nifblend.format.generated.structs import Color3, Matrix33, SizedString, Vector3
from nifblend.format.generated.structs import MaterialData as NifStructMaterialData
from nifblend.format.generated.structs import string as nif_string
from nifblend.ops import import_nif as import_nif_mod
from nifblend.ops.import_nif import NIFBLEND_OT_import_nif


def _dual_name(value: str = "") -> Any:
    """Build a ``string`` compound valid for *either* pre- or post-20.1.0.3
    NIFs -- populates both the inline ``SizedString`` and the string-table
    index so a single fixture writes cleanly under any header version.
    """
    payload = value.encode("latin-1")
    return nif_string(
        string=SizedString(length=len(payload), value=list(payload)), index=0xFFFFFFFF
    )


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


def _identity_rot() -> Matrix33:
    return Matrix33(m11=1.0, m12=0.0, m13=0.0, m21=0.0, m22=1.0, m23=0.0, m31=0.0, m32=0.0, m33=1.0)


def _node(
    *, translation: tuple[float, float, float] = (0.0, 0.0, 0.0), children: list[int] | None = None
) -> NiNode:
    n = NiNode()
    n.name = _dual_name()
    n.translation = Vector3(*translation)
    n.rotation = _identity_rot()
    n.scale = 1.0
    n.children = children or []
    n.num_children = len(n.children)
    return n


class _FakeVertexGroup:
    def __init__(self, name: str) -> None:
        self.name = name
        self.adds: list[tuple[list[int], float, str]] = []

    def add(self, indices: list[int], weight: float, mode: str) -> None:
        self.adds.append((list(indices), weight, mode))


class _FakeVertexGroups:
    def __init__(self) -> None:
        self._items: dict[str, _FakeVertexGroup] = {}

    def new(self, *, name: str) -> _FakeVertexGroup:
        vg = _FakeVertexGroup(name)
        self._items[name] = vg
        return vg

    def __iter__(self):
        return iter(self._items.values())

    def __getitem__(self, name: str) -> _FakeVertexGroup:
        return self._items[name]


class _FakeModifier:
    def __init__(self, name: str, type_: str) -> None:
        self.name = name
        self.type = type_
        self.object: Any = None


class _FakeModifiers:
    def __init__(self) -> None:
        self.created: list[_FakeModifier] = []

    def new(self, *, name: str, type: str) -> _FakeModifier:
        mod = _FakeModifier(name, type)
        self.created.append(mod)
        return mod


class _FakeMesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.materials: list[Any] = []
        self.vertices = SimpleNamespace(add=lambda *_a: None)

    def from_pydata(self, _verts: Any, _edges: Any, _faces: Any) -> None:
        return None

    def update(self) -> None:
        return None


class _FakeObject:
    def __init__(self, name: str, data: Any) -> None:
        self.name = name
        self.data = data
        self.location: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.rotation_mode = "XYZ"
        self.rotation_euler: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
        self.parent: Any = None
        self.vertex_groups = _FakeVertexGroups()
        self.modifiers = _FakeModifiers()


class _FakeCollection:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.linked: list[Any] = []
        self.child_collections: list[_FakeCollection] = []
        self.objects = SimpleNamespace(link=self.linked.append)
        self.children = SimpleNamespace(link=self.child_collections.append)


class _FakeArmatureData:
    def __init__(self, name: str) -> None:
        self.name = name
        self.edit_bones = SimpleNamespace(
            new=lambda name: SimpleNamespace(name=name, head=(0, 0, 0), tail=(0, 0, 1), parent=None)
        )
        self.bones = SimpleNamespace(get=lambda name: SimpleNamespace(name=name))


class _FakeArmatures:
    def __init__(self) -> None:
        self.created: list[_FakeArmatureData] = []

    def new(self, name: str) -> _FakeArmatureData:
        a = _FakeArmatureData(name)
        self.created.append(a)
        return a


class _FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.use_nodes = False
        self.node_tree = SimpleNamespace(nodes=_FakeNodes(), links=_FakeLinks())
        self.blend_method = "OPAQUE"
        self.alpha_threshold = 0.0


class _FakeInput:
    def __init__(self, name: str) -> None:
        self.name = name
        self.default_value: Any = None


class _FakeOutput:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeInputs:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: _FakeInput(n) for n in names}

    def __contains__(self, k: str) -> bool:
        return k in self._items

    def __getitem__(self, k: str) -> _FakeInput:
        return self._items[k]

    def get(self, k: str, default: Any = None) -> Any:
        return self._items.get(k, default)


class _FakeOutputs:
    def __init__(self, names: list[str]) -> None:
        self._items = {n: _FakeOutput(n) for n in names}

    def __getitem__(self, k: str) -> _FakeOutput:
        return self._items[k]


class _FakeShaderNode:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.location: tuple[float, float] = (0.0, 0.0)
        self.image: Any = None
        if kind == "ShaderNodeBsdfPrincipled":
            self.inputs = _FakeInputs(
                [
                    "Base Color",
                    "Alpha",
                    "Roughness",
                    "Metallic",
                    "Emission Color",
                    "Emission Strength",
                    "Normal",
                ]
            )
            self.outputs = _FakeOutputs(["BSDF"])
        elif kind == "ShaderNodeOutputMaterial":
            self.inputs = _FakeInputs(["Surface"])
            self.outputs = _FakeOutputs([])
        elif kind == "ShaderNodeTexImage":
            self.inputs = _FakeInputs([])
            self.outputs = _FakeOutputs(["Color", "Alpha"])
        elif kind == "ShaderNodeNormalMap":
            self.inputs = _FakeInputs(["Color"])
            self.outputs = _FakeOutputs(["Normal"])
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown fake node kind: {kind!r}")


class _FakeNodes:
    def __init__(self) -> None:
        self._items: list[_FakeShaderNode] = []

    def new(self, kind: str) -> _FakeShaderNode:
        n = _FakeShaderNode(kind)
        self._items.append(n)
        return n

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self):
        return iter(self._items)


class _FakeLinks:
    def __init__(self) -> None:
        self._items: list[tuple[_FakeOutput, _FakeInput]] = []

    def new(self, src: _FakeOutput, dst: _FakeInput) -> None:
        self._items.append((src, dst))


class _FakeMaterials:
    def __init__(self) -> None:
        self.created: list[_FakeMaterial] = []

    def new(self, name: str) -> _FakeMaterial:
        m = _FakeMaterial(name)
        self.created.append(m)
        return m


class _FakeImages:
    def load(self, filepath: str, check_existing: bool = True) -> Any:
        return SimpleNamespace(name=filepath, filepath=filepath)

    def get(self, _name: str) -> Any | None:
        return None

    def new(self, *, name: str, width: int, height: int) -> Any:
        return SimpleNamespace(name=name)


class _FakeMeshes:
    def __init__(self) -> None:
        self.created: list[_FakeMesh] = []

    def new(self, name: str) -> _FakeMesh:
        m = _FakeMesh(name)
        self.created.append(m)
        return m


class _FakeObjects:
    def __init__(self) -> None:
        self.created: list[_FakeObject] = []

    def new(self, name: str, data: Any) -> _FakeObject:
        o = _FakeObject(name, data)
        self.created.append(o)
        return o


class _FakeCollections:
    def new(self, name: str) -> _FakeCollection:
        return _FakeCollection(name)


@pytest.fixture
def fake_bpy(monkeypatch: pytest.MonkeyPatch) -> Any:
    bpy = import_nif_mod.bpy
    fake_data = SimpleNamespace(
        objects=_FakeObjects(),
        materials=_FakeMaterials(),
        images=_FakeImages(),
        armatures=_FakeArmatures(),
        collections=_FakeCollections(),
        meshes=_FakeMeshes(),
    )
    monkeypatch.setattr(bpy, "data", fake_data, raising=False)
    monkeypatch.setattr(
        bpy, "context", SimpleNamespace(collection=None, view_layer=None), raising=False
    )
    monkeypatch.setattr(bpy, "ops", None, raising=False)
    return bpy


def _op_context(collection: _FakeCollection) -> SimpleNamespace:
    return SimpleNamespace(collection=collection, scene=None)


# ---------------------------------------------------------------------------
# _valid_ref / _resolve_block
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ref", [None, -1, 0xFFFFFFFF])
def test_valid_ref_rejects_null_sentinels(ref: object) -> None:
    assert import_nif_mod._valid_ref(ref) is None


def test_valid_ref_accepts_zero_and_positive() -> None:
    assert import_nif_mod._valid_ref(0) == 0
    assert import_nif_mod._valid_ref(5) == 5


def test_resolve_block_out_of_range_returns_none() -> None:
    table = SimpleNamespace(blocks=[1, 2])
    assert import_nif_mod._resolve_block(table, 5) is None
    assert import_nif_mod._resolve_block(table, None) is None


def test_resolve_block_returns_the_block() -> None:
    table = SimpleNamespace(blocks=["a", "b"])
    assert import_nif_mod._resolve_block(table, 1) == "b"


# ---------------------------------------------------------------------------
# _resolve_skin_ref
# ---------------------------------------------------------------------------


def test_resolve_skin_ref_prefers_skin_instance() -> None:
    shape = SimpleNamespace(skin_instance=3, skin=0xFFFFFFFF)
    assert import_nif_mod._resolve_skin_ref(shape) == 3


def test_resolve_skin_ref_falls_back_to_skin() -> None:
    shape = SimpleNamespace(skin=7)  # no skin_instance attribute at all
    assert import_nif_mod._resolve_skin_ref(shape) == 7


def test_resolve_skin_ref_none_when_both_unset() -> None:
    shape = SimpleNamespace(skin=-1, skin_instance=0xFFFFFFFF)
    assert import_nif_mod._resolve_skin_ref(shape) is None


# ---------------------------------------------------------------------------
# _apply_shape_transform
# ---------------------------------------------------------------------------


def test_apply_shape_transform_places_object_from_world_matrix() -> None:
    obj = _FakeObject("Shape", _FakeMesh("Shape"))
    world = np.eye(4, dtype=np.float32)
    world[0, 3], world[1, 3], world[2, 3] = 3.0, 4.0, 5.0
    import_nif_mod._apply_shape_transform(obj, 0, {0: world})
    assert obj.location == pytest.approx((3.0, 4.0, 5.0))
    assert obj.rotation_euler == pytest.approx((0.0, 0.0, 0.0), abs=1e-5)
    assert obj.scale == pytest.approx((1.0, 1.0, 1.0))


def test_apply_shape_transform_no_op_when_block_unreachable() -> None:
    obj = _FakeObject("Shape", _FakeMesh("Shape"))
    import_nif_mod._apply_shape_transform(obj, 99, {})
    assert obj.location == (0.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# _resolve_shape_material
# ---------------------------------------------------------------------------


def test_resolve_shape_material_modern_path_shares_cache(fake_bpy: Any) -> None:
    shader = BSLightingShaderProperty()
    shader.name = nif_string(index=0xFFFFFFFF)
    table = SimpleNamespace(blocks=[shader], header=SimpleNamespace(strings=[]))
    # Dispatch is isinstance(shape, BSTriShape)-based (not ref-value-based --
    # see docs/REVIEW_2026-07.md / the _resolve_shape_material docstring for
    # why), so the fake shape must actually be a BSTriShape here.
    mesh_data = MeshData(
        name="x",
        positions=np.zeros((0, 3), dtype=np.float32),
        triangles=np.empty((0, 3), dtype=np.uint32),
    )
    shape_a = mesh_data_to_bstrishape(mesh_data)
    shape_a.shader_property = 0
    shape_a.alpha_property = 0xFFFFFFFF
    shape_b = mesh_data_to_bstrishape(mesh_data)
    shape_b.shader_property = 0
    shape_b.alpha_property = 0xFFFFFFFF
    cache: dict[Any, Any] = {}

    mat_a = import_nif_mod._resolve_shape_material(
        shape_a, table, resolve_texture=None, cache=cache
    )
    mat_b = import_nif_mod._resolve_shape_material(
        shape_b, table, resolve_texture=None, cache=cache
    )
    assert mat_a is not None
    assert mat_a is mat_b  # shared shader_property -> one Material, not two
    assert len(fake_bpy.data.materials.created) == 1


def test_resolve_shape_material_classic_path_from_properties_list(fake_bpy: Any) -> None:
    mat_block = NiMaterialProperty()
    mat_block.diffuse_color = SimpleNamespace(r=0.5, g=0.5, b=0.5)
    tex_block = NiTexturingProperty()
    table = SimpleNamespace(blocks=[mat_block, tex_block], header=SimpleNamespace(strings=[]))
    shape = SimpleNamespace(properties=[0, 1])

    material = import_nif_mod._resolve_shape_material(shape, table, resolve_texture=None, cache={})
    assert material is not None
    assert len(fake_bpy.data.materials.created) == 1


def test_resolve_shape_material_returns_none_when_nothing_to_resolve() -> None:
    shape = SimpleNamespace(shader_property=-1, properties=[])
    table = SimpleNamespace(blocks=[])
    assert (
        import_nif_mod._resolve_shape_material(shape, table, resolve_texture=None, cache={}) is None
    )


# ---------------------------------------------------------------------------
# _ensure_armature
# ---------------------------------------------------------------------------


def test_ensure_armature_builds_once_and_caches(fake_bpy: Any) -> None:
    root = _node()
    table = SimpleNamespace(
        blocks=[root], header=SimpleNamespace(strings=[]), footer=SimpleNamespace(roots=[0])
    )
    cache: dict[int, Any] = {}
    first = import_nif_mod._ensure_armature(0, table, None, cache)
    second = import_nif_mod._ensure_armature(0, table, None, cache)
    assert first is not None
    assert first is second
    assert len(fake_bpy.data.armatures.created) == 1


def test_ensure_armature_returns_none_for_non_ninode_root() -> None:
    table = SimpleNamespace(blocks=[SimpleNamespace()])
    assert import_nif_mod._ensure_armature(0, table, None, {}) is None


def test_ensure_armature_returns_none_when_skeleton_root_is_none() -> None:
    assert import_nif_mod._ensure_armature(None, SimpleNamespace(blocks=[]), None, {}) is None


# ---------------------------------------------------------------------------
# end-to-end execute()
# ---------------------------------------------------------------------------


def _write_table_to_tempfile(table: Any) -> str:
    import io
    import tempfile

    from nifblend.io.block_table import write_nif

    sink = io.BytesIO()
    write_nif(sink, table)
    with tempfile.NamedTemporaryFile(suffix=".nif", delete=False) as fh:
        fh.write(sink.getvalue())
        return fh.name


def _sse_header_and_ctx():
    from nifblend.format.base import ReadContext
    from nifblend.format.generated.structs import BSStreamHeader, ExportString, Header
    from nifblend.format.versions import pack_version

    empty = ExportString(length=0, value=[])
    h = Header(
        version=pack_version(20, 2, 0, 7),
        endian_type=1,
        user_version=12,
        num_blocks=0,
        bs_header=BSStreamHeader(
            bs_version=100, author=empty, process_script=empty, export_script=empty
        ),
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return h, ctx


def _oblivion_header_and_ctx():
    """Header shaped like Oblivion (20.0.0.5) -- the version range where
    NiTriShape's ``.properties`` list is populated and modern-only fields
    (e.g. ``bounding_sphere``, gated on ``bs_version >= 100``) stay absent.
    """
    from nifblend.format.base import ReadContext
    from nifblend.format.generated.structs import Header
    from nifblend.format.versions import pack_version

    h = Header(
        version=pack_version(20, 0, 0, 5),
        endian_type=1,
        user_version=0,
        num_blocks=0,
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=0)
    return h, ctx


def test_execute_modern_path_wires_transform_material_skin_and_armature(
    tmp_path: Any, fake_bpy: Any
) -> None:
    from nifblend.format.generated.structs import Footer
    from nifblend.io.block_table import BlockTable

    bone_root = _node(translation=(2.0, 0.0, 0.0))
    scene_root = _node(translation=(0.0, 0.0, 0.0), children=[0, 2, 3])
    # scene_root ends up at index 1 (added after bone_root); shapes at 2, 3.

    mesh_data = MeshData(
        name="Blade",
        positions=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        bone_weights=np.array([[1.0, 0.0, 0.0, 0.0]] * 3, dtype=np.float32),
        bone_indices=np.array([[0, 0, 0, 0]] * 3, dtype=np.uint8),
    )
    shape_a = mesh_data_to_bstrishape(mesh_data, full_precision=True)
    shape_a.name = _dual_name("Blade")
    shape_a.translation = Vector3(5.0, 0.0, 0.0)

    mesh_data_b = MeshData(
        name="Hilt",
        positions=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32),
        triangles=np.array([[0, 1, 2]], dtype=np.uint32),
        bone_weights=np.array([[1.0, 0.0, 0.0, 0.0]] * 3, dtype=np.float32),
        bone_indices=np.array([[0, 0, 0, 0]] * 3, dtype=np.uint8),
    )
    shape_b = mesh_data_to_bstrishape(mesh_data_b, full_precision=True)
    shape_b.name = _dual_name("Hilt")

    shader = material_data_to_bslighting(MaterialData(name="Shader"), name_index=0xFFFFFFFF)

    skin_inst = NiSkinInstance()
    skin_inst.bones = [0]
    skin_inst.num_bones = 1
    skin_inst.skeleton_root = 0
    skin_inst.data = -1

    # Block order: 0 bone_root, 1 scene_root, 2 shape_a, 3 shape_b,
    # 4 skin_inst, 5 shader. scene_root.children references 0 (bone_root),
    # 2 (shape_a), 3 (shape_b) by index.
    shape_a.skin = 4
    shape_a.shader_property = 5
    shape_b.skin = 4
    shape_b.shader_property = 5

    header, ctx = _sse_header_and_ctx()
    table = BlockTable(
        header=header,
        blocks=[bone_root, scene_root, shape_a, shape_b, skin_inst, shader],
        footer=Footer(num_roots=1, roots=[1]),
        ctx=ctx,
    )
    path = _write_table_to_tempfile(table)

    op = NIFBLEND_OT_import_nif()
    op.filepath = path
    reports: list[tuple[set[str], str]] = []
    op.report = lambda level, msg: reports.append((level, msg))  # type: ignore[assignment]

    collection = _FakeCollection()
    result = op.execute(_op_context(collection))

    assert result == {"FINISHED"}
    created_objects = fake_bpy.data.objects.created
    mesh_objects = [o for o in created_objects if isinstance(o.data, _FakeMesh)]
    assert len(mesh_objects) == 2

    # SSE-versioned names only round-trip via the header string table (the
    # inline `.string` form never survives a >= 20.1.0.3 write/read cycle),
    # which this minimal fixture doesn't populate -- identify the shape by
    # its known transform instead of by name.
    shape_obj = next(o for o in mesh_objects if o.location == pytest.approx((5.0, 0.0, 0.0)))
    assert shape_obj.location == pytest.approx((5.0, 0.0, 0.0))
    assert len(shape_obj.data.materials) == 1
    # Vertex group named after the resolved bone name exists with a weight-1 add.
    assert len(list(shape_obj.vertex_groups)) == 1
    assert shape_obj.parent is not None
    assert len(shape_obj.modifiers.created) == 1
    assert shape_obj.modifiers.created[0].type == "ARMATURE"

    # Both shapes share the same skeleton_root -> exactly one Armature built.
    assert len(fake_bpy.data.armatures.created) == 1
    # Both shapes share the same shader_property -> exactly one Material built.
    assert len(fake_bpy.data.materials.created) == 1


def test_execute_classic_path_wires_properties_list_material(tmp_path: Any, fake_bpy: Any) -> None:
    from nifblend.format.generated.structs import Footer, NiBound, Triangle
    from nifblend.io.block_table import BlockTable

    scene_root = _node(children=[1])

    tri_data = NiTriShapeData()
    tri_data.bounding_sphere = NiBound(center=Vector3(0.0, 0.0, 0.0), radius=1.0)
    tri_data.num_vertices = 3
    tri_data.has_vertices = True
    tri_data.vertices = [Vector3(0, 0, 0), Vector3(1, 0, 0), Vector3(0, 1, 0)]
    tri_data.num_triangles = 1
    tri_data.has_triangles = True
    tri_data.triangles = [Triangle(0, 1, 2)]
    tri_data.has_normals = False
    tri_data.normals = []
    tri_data.has_vertex_colors = False
    tri_data.vertex_colors = []
    tri_data.has_uv = False
    tri_data.uv_sets = []

    mat_block = NiMaterialProperty()
    mat_block.name = _dual_name("Mat")
    mat_block.ambient_color = Color3(0.1, 0.1, 0.1)
    mat_block.diffuse_color = Color3(0.2, 0.3, 0.4)
    mat_block.specular_color = Color3(0.0, 0.0, 0.0)
    mat_block.emissive_color = Color3(0.0, 0.0, 0.0)
    tex_block = NiTexturingProperty()
    tex_block.name = _dual_name("Tex")

    shape = NiTriShape()
    shape.name = _dual_name("Shape")
    shape.translation = Vector3(1.0, 2.0, 3.0)
    shape.rotation = _identity_rot()
    shape.scale = 1.0
    shape.material_data = NifStructMaterialData()

    header, ctx = _oblivion_header_and_ctx()
    table = BlockTable(
        header=header,
        blocks=[scene_root, shape, tri_data, mat_block, tex_block],
        footer=Footer(num_roots=1, roots=[0]),
        ctx=ctx,
    )
    # Block order: 0 scene_root, 1 shape, 2 tri_data, 3 mat_block, 4 tex_block.
    shape.data = 2
    shape.properties = [3, 4]
    shape.num_properties = 2
    path = _write_table_to_tempfile(table)

    op = NIFBLEND_OT_import_nif()
    op.filepath = path
    op.report = lambda *_a, **_kw: None  # type: ignore[assignment]

    collection = _FakeCollection()
    result = op.execute(_op_context(collection))

    assert result == {"FINISHED"}
    created_objects = fake_bpy.data.objects.created
    assert len(created_objects) == 1
    obj = created_objects[0]
    assert obj.location == pytest.approx((1.0, 2.0, 3.0))
    assert len(obj.data.materials) == 1
