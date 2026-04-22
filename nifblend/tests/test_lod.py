"""Phase 7 step 28 — LOD detection + materialisation tests.

Pure detection runs against synthesised in-memory ``BlockTable``s
(``NiLODNode``-rooted and ``BSLODTriShape`` shapes), and the
``materialise_lod_groups`` Blender wrapper runs against a hand-built
``bpy``-shaped fake so the headless suite never touches Blender.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from nifblend.bridge.lod import (
    LODGroup,
    LODLevel,
    TriangleSliceLevel,
    detect_lod_groups,
)
from nifblend.format.base import ReadContext
from nifblend.format.generated.blocks import (
    BSLODTriShape,
    NiLODNode,
    NiTriShape,
)
from nifblend.format.generated.structs import (
    BSStreamHeader,
    ExportString,
    Footer,
    Header,
    LODRange,
)
from nifblend.format.generated.structs import string as nif_string
from nifblend.format.versions import pack_version
from nifblend.io.block_table import BlockTable
from nifblend.ops.preview_lod import materialise_lod_groups

# ---- header / table helpers ----------------------------------------------


def _empty_export_string() -> ExportString:
    return ExportString(length=0, value=[])


def _table(blocks: list[Any], strings: list[str] | None = None) -> BlockTable:
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
        strings=strings or [],
        num_strings=len(strings) if strings else 0,
    )
    ctx = ReadContext(version=h.version, user_version=h.user_version, bs_version=100)
    return BlockTable(header=h, blocks=blocks, footer=Footer(), ctx=ctx)


def _name_index(idx: int) -> Any:
    return nif_string(index=idx)


def _lod_range(near: float, far: float) -> LODRange:
    return LODRange(near_extent=near, far_extent=far)


# ---- detect_lod_groups: NiLODNode ----------------------------------------


def test_nilodnode_three_children_three_levels() -> None:
    child0 = NiTriShape(name=_name_index(0xFFFFFFFF))
    child1 = NiTriShape(name=_name_index(0xFFFFFFFF))
    child2 = NiTriShape(name=_name_index(0xFFFFFFFF))
    parent = NiLODNode(
        name=_name_index(0),
        num_children=3,
        children=[1, 2, 3],
        num_lod_levels=3,
        lod_levels=[
            _lod_range(0.0, 100.0),
            _lod_range(100.0, 500.0),
            _lod_range(500.0, 5000.0),
        ],
    )
    table = _table([parent, child0, child1, child2], strings=["LODRoot"])
    groups = detect_lod_groups(table)
    assert len(groups) == 1
    g = groups[0]
    assert g.origin == "NiLODNode"
    assert g.parent_ref == 0
    assert g.name == "LODRoot"
    assert [lvl.block_ref for lvl in g.levels] == [1, 2, 3]
    assert g.levels[0].near_extent == 0.0
    assert g.levels[1].far_extent == 500.0


def test_nilodnode_drops_invalid_child_refs() -> None:
    child = NiTriShape(name=_name_index(0xFFFFFFFF))
    parent = NiLODNode(
        name=_name_index(0xFFFFFFFF),
        num_children=3,
        children=[1, 0xFFFFFFFF, 99],  # valid, sentinel, out-of-range
        num_lod_levels=3,
        lod_levels=[_lod_range(0, 1), _lod_range(1, 2), _lod_range(2, 3)],
    )
    table = _table([parent, child])
    groups = detect_lod_groups(table)
    assert len(groups) == 1
    assert [lvl.block_ref for lvl in groups[0].levels] == [1]


def test_nilodnode_with_no_children_dropped() -> None:
    parent = NiLODNode(
        name=_name_index(0xFFFFFFFF),
        num_children=0,
        children=[],
        num_lod_levels=0,
        lod_levels=[],
    )
    table = _table([parent])
    assert detect_lod_groups(table) == []


def test_nilodnode_falls_back_to_synthetic_name() -> None:
    child = NiTriShape(name=_name_index(0xFFFFFFFF))
    parent = NiLODNode(
        name=_name_index(0xFFFFFFFF),
        num_children=1,
        children=[1],
        num_lod_levels=1,
        lod_levels=[_lod_range(0.0, 1.0)],
    )
    table = _table([parent, child])
    groups = detect_lod_groups(table)
    assert groups[0].name == "NiLODNode_0"


# ---- detect_lod_groups: BSLODTriShape ------------------------------------


def test_bslodtrishape_three_slices() -> None:
    shape = BSLODTriShape(
        name=_name_index(0),
        lod0_size=120,
        lod1_size=60,
        lod2_size=20,
    )
    table = _table([shape], strings=["DistantTree"])
    groups = detect_lod_groups(table)
    assert len(groups) == 1
    g = groups[0]
    assert g.origin == "BSLODTriShape"
    assert g.name == "DistantTree"
    assert [lvl.triangle_slice.num_triangles for lvl in g.levels] == [120, 60, 20]
    assert all(lvl.triangle_slice.shape_ref == 0 for lvl in g.levels)


def test_bslodtrishape_zero_slice_skipped() -> None:
    shape = BSLODTriShape(
        name=_name_index(0xFFFFFFFF),
        lod0_size=100,
        lod1_size=0,
        lod2_size=10,
    )
    table = _table([shape])
    g = detect_lod_groups(table)[0]
    assert [lvl.index for lvl in g.levels] == [0, 2]


def test_bslodtrishape_all_zero_dropped() -> None:
    shape = BSLODTriShape(
        name=_name_index(0xFFFFFFFF),
        lod0_size=0,
        lod1_size=0,
        lod2_size=0,
    )
    assert detect_lod_groups(_table([shape])) == []


def test_detect_returns_nilodnode_groups_before_bslod() -> None:
    child = NiTriShape(name=_name_index(0xFFFFFFFF))
    parent = NiLODNode(
        name=_name_index(0xFFFFFFFF),
        num_children=1,
        children=[1],
        num_lod_levels=1,
        lod_levels=[_lod_range(0.0, 1.0)],
    )
    shape = BSLODTriShape(
        name=_name_index(0xFFFFFFFF),
        lod0_size=10,
        lod1_size=5,
        lod2_size=1,
    )
    table = _table([parent, child, shape])
    origins = [g.origin for g in detect_lod_groups(table)]
    assert origins == ["NiLODNode", "BSLODTriShape"]


# ---- materialise_lod_groups (with fake bpy) ------------------------------


class _FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.hide_viewport = False
        self.hide_render = False
        self._objects: list[Any] = []
        self._children: list[_FakeCollection] = []
        self.objects = SimpleNamespace(
            link=self._objects.append,
            unlink=lambda o: self._objects.remove(o) if o in self._objects else None,
        )
        self.children = _FakeChildren(self._children)
        self._properties: dict[str, Any] = {}

    def __setitem__(self, key: str, value: Any) -> None:
        self._properties[key] = value

    def __getitem__(self, key: str) -> Any:
        return self._properties[key]


class _FakeChildren:
    def __init__(self, backing: list[_FakeCollection]) -> None:
        self._backing = backing

    def link(self, c: _FakeCollection) -> None:
        self._backing.append(c)

    def __iter__(self):
        return iter(self._backing)

    def __len__(self) -> int:
        return len(self._backing)


class _FakeCollections:
    def __init__(self) -> None:
        self.created: list[_FakeCollection] = []

    def new(self, name: str) -> _FakeCollection:
        c = _FakeCollection(name)
        self.created.append(c)
        return c


def _fake_bpy() -> SimpleNamespace:
    scene_collection = _FakeCollection("Scene")
    return SimpleNamespace(
        context=SimpleNamespace(scene=SimpleNamespace(collection=scene_collection)),
        data=SimpleNamespace(collections=_FakeCollections()),
    )


def test_materialise_creates_parent_and_per_level_collections() -> None:
    obj_a = SimpleNamespace(name="ChildA")
    obj_b = SimpleNamespace(name="ChildB")
    group = LODGroup(
        name="MyLOD",
        parent_ref=0,
        origin="NiLODNode",
        levels=[
            LODLevel(index=0, near_extent=0.0, far_extent=100.0, block_ref=1),
            LODLevel(index=1, near_extent=100.0, far_extent=500.0, block_ref=2),
        ],
    )
    fake = _fake_bpy()
    out = materialise_lod_groups(
        [group], block_to_object={1: obj_a, 2: obj_b}, bpy=fake
    )
    assert len(out) == 1
    bgroup = out[0]
    assert bgroup.parent_collection.name == "LOD_MyLOD"
    assert [lvl.collection.name for lvl in bgroup.levels] == ["LOD0", "LOD1"]
    # LOD0 is visible by default; LOD1 hidden.
    assert bgroup.levels[0].collection.hide_viewport is False
    assert bgroup.levels[1].collection.hide_viewport is True
    # Each child collection received exactly its mapped object.
    assert obj_a in bgroup.levels[0].collection._objects
    assert obj_b in bgroup.levels[1].collection._objects


def test_materialise_stamps_triangle_count_for_bslod() -> None:
    obj = SimpleNamespace(name="DistantTree")
    group = LODGroup(
        name="DistantTree",
        parent_ref=0,
        origin="BSLODTriShape",
        levels=[
            LODLevel(index=0, triangle_slice=TriangleSliceLevel(shape_ref=0, num_triangles=120)),
            LODLevel(index=1, triangle_slice=TriangleSliceLevel(shape_ref=0, num_triangles=60)),
        ],
    )
    fake = _fake_bpy()
    out = materialise_lod_groups([group], block_to_object={0: obj}, bpy=fake)
    bgroup = out[0]
    assert bgroup.levels[0].collection["nifblend_lod_num_triangles"] == 120
    assert bgroup.levels[1].collection["nifblend_lod_num_triangles"] == 60
    # The same object is linked under every level (shared shape, sliced triangles).
    assert obj in bgroup.levels[0].collection._objects
    assert obj in bgroup.levels[1].collection._objects


def test_materialise_skips_unresolved_block_refs() -> None:
    group = LODGroup(
        name="Lonely",
        parent_ref=0,
        origin="NiLODNode",
        levels=[LODLevel(index=0, block_ref=99)],  # not in block_to_object
    )
    fake = _fake_bpy()
    out = materialise_lod_groups([group], block_to_object={}, bpy=fake)
    bgroup = out[0]
    # Collections still created, just no object linked.
    assert bgroup.levels[0].collection._objects == []
