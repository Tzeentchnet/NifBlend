# NifBlend Phase 10 Roadmap — KF animation export (v1.1)

> Working roadmap for the **KF export** slice. Sub-stepped in the same dense format as `ROADMAP.md` Phase 9. Tick checkboxes as steps land. Record what *shipped* in [`CHANGELOG.md`](CHANGELOG.md). Once Phase 10 closes, fold this file's contents into `ROADMAP.md` and delete it.

## TL;DR

KF export is the inverse of Phase 5 KF import. Two real blockers up front:

1. **Codegen `#T#` template gap** on `Key` / `QuatKey` `.value` (currently emitted as `Any = None` — the schema's `#T#` template parameter is never resolved). Must be widened in `tools/codegen` before keyed data round-trips through [`write_nif`](../nifblend/io/block_table.py).
2. **No metadata storage** on the Blender side — sequence-level (`weight` / `frequency` / `cycle_type` / `start_time` / `stop_time` / `text_keys` / `accum_root_name`) and per-bone `ControlledBlock` metadata (`priority` / `controller_type` / `controller_id` / `interpolator_id` / `property_type`) is currently dropped on import. Need PropertyGroups on `bpy.types.Action` + `bpy.types.PoseBone` plus a back-fill pass in [`ops/import_kf.py`](../nifblend/ops/import_kf.py) so existing imported actions can re-export.

[`io/block_table.write_nif`](../nifblend/io/block_table.py) already auto-patches header bookkeeping (block-type table, type-index, sizes) and preserves cross-block u32 refs verbatim — the export writer just builds blocks in canonical order and lets the existing pipeline do the rest. KF-shaped headers + footer-roots-as-sequence-indices already round-trip at the shell level (`test_kf_io.py::test_kf_round_trip_preserves_sequence_fields`); only keyed payload + metadata round-trip is new.

Scope: **export only**. NLA blending semantics beyond first-active-strip per track, particle controllers, `NiControllerManager` synthesis, and morph controllers stay out of scope.

## Phased steps

### Phase 10 — KF animation export (v1.1)

#### 10a. Author this roadmap (`newroadmap.md`)
*Sequential, lands first as the user-requested deliverable.*

- [x] Create `docs/newroadmap.md` carrying the full Phase 10 block (10a-10g) in the dense Phase 9 format, plus this TL;DR header and a "Beyond v1.1" follow-on section.
- Pure documentation — no code touched. Sub-step boxes 10b-10g are ticked from the matching implementation steps below.

#### 10b. Codegen widening for `Key` / `QuatKey` / `KeyGroup` `#T#` template
*Sequential, blocks every keyed-data round-trip in 10e and onward. Parallel with 10c.*

- [x] Extended [`nifblend/format/base.py`](../nifblend/format/base.py) `ReadContext` with a `templates: list[str]` stack + `template` property + `push_template()` / `pop_template()`, mirroring the existing `args` stack (the `arg=` schema attribute already drove `KeyGroup` → `Key`/`QuatKey`'s `interpolation` resolution; the new stack carries the `template=` attribute downward in the same shape).
- [x] [`tools/codegen/emit.py`](../tools/codegen/emit.py): `_TEMPLATE_PRIMITIVES = {"float": …, "byte": …}` and `_TEMPLATE_COMPOUNDS = ("Vector3", "Quaternion", "Color4", "ByteColor4", "string")` drive `_emit_template_value_read` / `_emit_template_value_write` (an `if ctx.template == "float": …elif "Vector3": …else: NotImplementedError` chain) for every `f.type == "#T#"` field. Caller-side struct/block reads + writes wrap with `ctx.push_template(value)` / `pop_template()` via `_wrap_template`, with propagation (`#T#` or empty template) suppressed.
- [x] `Key.value` / `Key.forward` / `Key.backward` / `QuatKey.value` now dispatch on `ctx.template` covering `Vector3` / `Quaternion` / `float` / `byte` / `Color4` / `ByteColor4` / `string`.
- [x] Regenerated [`nifblend/format/generated/{blocks,structs}.py`](../nifblend/format/generated/). `python -m tools.codegen --check` clean. `NiTransformData` wraps `quaternion_keys` (`Quaternion`), `xyz_rotations` + `scales` (`float`), `translations` (`Vector3`); `NiTextKeyExtraData` wraps `text_keys` (`string`).
- [x] [`tools/codegen/tests/test_template_widening.py`](../tools/codegen/tests/test_template_widening.py) covers the template stack semantics + `Key`/`KeyGroup`/`QuatKey` round-trips against every supported template plus the unsupported-template `NotImplementedError` path (12 tests).
- [x] [`nifblend/tests/test_kf_io.py`](../nifblend/tests/test_kf_io.py) `test_kf_round_trip_with_real_transform_data`: `NiControllerSequence` → `ControlledBlock` → `NiTransformInterpolator` → `NiTransformData` carrying real translation `KeyGroup<Vector3>`, `QuatKey<Quaternion>` rotation list, scale `KeyGroup<float>`; round-tripped through `write_nif` → `read_nif` with every `.time` and `.value` asserted.

#### 10c. Action + pose-bone PropertyGroups for sequence + ControlledBlock metadata
*Parallel with 10b.*

- [x] New `nifblend/bridge/animation_props.py`:
  - `NifBlendActionProperties` on `bpy.types.Action`: `weight: FloatProperty`, `frequency: FloatProperty`, `start_time: FloatProperty`, `stop_time: FloatProperty`, `cycle_type: EnumProperty` (over `CycleType` enum from the codegen layer), `accum_root_name: StringProperty`, `accum_flags: IntProperty`, `phase: FloatProperty` (deprecated, stored verbatim), `play_backwards: BoolProperty`, plus a `text_keys: CollectionProperty` of `(time: FloatProperty, name: StringProperty)` for [`NiTextKeyExtraData`](../nifblend/format/generated/blocks.py).
  - `NifBlendPoseBoneProperties` on `bpy.types.PoseBone`: per-bone `priority: IntProperty` (u8), `controller_type: StringProperty`, `controller_id: StringProperty`, `interpolator_id: StringProperty`, `property_type: StringProperty` (verbatim from `ControlledBlock`).
  - Duck-typed `apply_*` / `read_*` helpers mirroring the Phase 3.13 / 4.14 / 4.17 PropertyGroup pattern (work against the real `PointerProperty` and against `SimpleNamespace` test fakes).
- [x] Wire `register()` / `unregister()` through [`nifblend/__init__.py`](../nifblend/__init__.py)'s `_CLASSES`.
- [x] Test suite `nifblend/tests/test_animation_props.py` mirroring [`test_material_props.py`](../nifblend/tests/test_material_props.py) / [`test_skin_props.py`](../nifblend/tests/test_skin_props.py): round-trip / unset-default / cleared / no-PropertyGroup short-circuit.

#### 10d. Import-side back-fill: stamp metadata onto Action + pose bones
*Depends on 10c.*

- [x] [`nifblend/bridge/animation_in.py`](../nifblend/bridge/animation_in.py): after `animation_data_to_blender` builds the Action, stamp `data.{weight,frequency,start_time,stop_time,cycle_type,accum_root_name,accum_flags,phase,play_backwards}` onto the new `NifBlendActionProperties` PointerProperty so the export side has a source.
- [x] Extend `controller_sequence_to_animation_data` to also harvest each `ControlledBlock`'s `priority` / `controller_type` / `controller_id` / `interpolator_id` / `property_type` (currently dropped) into a new `BoneTrack.metadata: BoneTrackMetadata | None` dataclass.
- [x] Stamp `BoneTrack.metadata` onto the matching pose bone's `NifBlendPoseBoneProperties` after retargeting in [`ops/import_kf.py`](../nifblend/ops/import_kf.py).
- [x] Stamp `data.text_keys` (when the `NiTextKeyExtraData` ref resolves) onto the Action's `text_keys` collection.
- [x] Test suite extends [`test_animation_in.py`](../nifblend/tests/test_animation_in.py) + [`test_import_kf_op.py`](../nifblend/tests/test_import_kf_op.py) with metadata-survival assertions.

#### 10e. Pure export bridge: Blender Action → AnimationData → block list
*Depends on 10b (keyed data) + 10d (metadata source).*

- [x] `nifblend/bridge/animation_out.py` (new), pure (no `bpy` import outside helper signatures):
  - `animation_data_from_blender(action, *, fps=DEFAULT_FPS) -> AnimationData`: walks the Action's fcurves, groups by data-path prefix (`pose.bones["X"].location` / `.rotation_quaternion` / `.rotation_euler` / `.scale`), bulk-extracts via numpy `foreach_get` on `keyframe_points` (mirror of Phase 5.19's bulk-insert path), reconstructs `BoneTrack` arrays in the same `(N, K)` shapes the decoder produced. Reads the `NifBlendActionProperties` PointerProperty for sequence metadata; falls back to action `frame_range` for `start_time` / `stop_time` when the PropertyGroup is unset (e.g., Action created from scratch in Blender).
  - `bone_track_to_ni_transform_data(track) -> NiTransformData`: one `NiTransformData` per animated bone; routes through `KeyGroup` of `Vector3` for translation, list of `QuatKey` for quaternion rotation (`rotation_type` from `track.rotation_interp`, default `LINEAR_KEY=1`), three `KeyGroup` of `float` for `XYZ_ROTATION_KEY` Euler streams (when `rotation_euler` is populated and quaternion isn't), `KeyGroup` of `float` for scale.
  - `bone_track_to_ni_transform_interpolator(track, *, data_ref) -> NiTransformInterpolator`: identity `NiQuatTransform` static-transform fallback; `data` ref points at the matching `NiTransformData` slot. When a track has zero keys on every channel, emit the bind-pose `NiQuatTransform` and `data=-1` (FO4 idle-pose pattern).
  - `bone_track_to_controlled_block(track, *, interpolator_ref, name_index, controller_type_index, controller_id_index, interpolator_id_index, property_type_index) -> ControlledBlock`: emits the SSE-shaped (v20.2.0.7) variant with direct string refs; reads metadata from the `BoneTrack.metadata` channel populated in 10d.
  - `animation_data_to_controller_sequence(anim, *, controlled_blocks, name_index, text_keys_ref=-1, manager_ref=-1, accum_root_name_index=-1) -> NiControllerSequence`: scalar metadata routed straight from `AnimationData`.
  - `build_text_key_extra_data(events, *, name_index=-1) -> NiTextKeyExtraData`: from the Action PropertyGroup's text-keys collection.
  - `assemble_kf_block_table(actions, *, version=(20, 2, 0, 7), user_version=12, bs_version=100) -> BlockTable`: orchestrator. Allocates string-table indices (one per unique string across the whole table — sequence names, accum-root names, bone names, controller-type strings), lays out blocks in canonical order (`NiTextKeyExtraData` first, then for each sequence: `NiTransformData[]` → `NiTransformInterpolator[]` → `NiControllerSequence`), sets footer roots to the sequence indices, returns a ready-for-`write_nif` `BlockTable`.
- [x] Quaternion order: NIF `(w, x, y, z)` matches Blender `rotation_quaternion` — no swizzle (mirrors Phase 5.19 decoder comment).
- [x] Non-uniform animated scale: detect-and-collapse if all three Blender scale fcurves are identical within `1e-6`; otherwise warn + take channel 0 (NIF doesn't support non-uniform animated scale on this controller path).
- [x] Test suite `nifblend/tests/test_animation_out.py` (~15 tests):
  - `animation_data_from_blender` over fake Actions (single bone all channels / quaternion-only / euler-only / scale-only / sequence-metadata round-trip from PropertyGroup).
  - Per-block builders (translation/rotation/euler/scale `KeyGroup` shapes; `rotation_type` selection; `ControlledBlock` SSE variant; metadata propagation).
  - Empty-action short-circuit.
  - **End-to-end `bpy-Action → AnimationData → block list → write_nif → read_nif → controller_sequence_to_animation_data → AnimationData` round-trip** with positions / quaternions / scales surviving within `1e-5`.

#### 10f. `NIFBLEND_OT_export_kf` operator
*Depends on 10e.*

- [ ] New `nifblend/ops/export_kf.py`: `NIFBLEND_OT_export_kf(Operator, ExportHelper)`, `bl_idname="nifblend.export_kf"`, `bl_label="Export KF"`, `filename_ext=".kf"`, `filter_glob="*.kf"`. Properties:
  - `target_armature: EnumProperty` (dynamic, all `ARMATURE` objects in scene; sentinel when empty — mirror Phase 5.21 import-side picker).
  - `actions_mode: EnumProperty` over `("ACTIVE", "ALL_FROM_ARMATURE", "SELECTED_NLA_TRACKS")`, default `"ACTIVE"`.
  - `version_preset: EnumProperty` over `("AUTO", "SKYRIM_SE", "SKYRIM_LE", "FALLOUT_4")` mapping to `(version, user_version, bs_version)` triplets — pull from `NifBlendObjectProperties.game_profile` stamp on the target armature when `AUTO`.
  - `fps: FloatProperty` (default 30.0).
- [ ] `execute`: resolve target armature → enumerate actions per `actions_mode` → for each call `animation_data_from_blender` → orchestrate through `assemble_kf_block_table` → `write_nif`. Per-action failure surfaces as `WARNING`; total failure cancels with `ERROR`.
- [ ] Wire into [`nifblend/__init__.py`](../nifblend/__init__.py)'s `_CLASSES` + `_menu_func_export` (`File → Export → KF Animation (NifBlend) (.kf)`).
- [ ] Test suite `nifblend/tests/test_export_kf_op.py` (~8 tests): target-armature picker (explicit / active fallback / non-armature reject), action enumeration modes, version-preset → header triplet mapping, `execute` happy path against in-memory fake `bpy`, **end-to-end import → edit → export → re-import** round-trip exercising the full operator pair.

#### 10g. Sidebar UI + ROADMAP / CHANGELOG entries
*Depends on 10f.*

- [ ] Sidebar: add a `KF Export` action button row under [`NIFBLEND_PT_main`](../nifblend/ui/sidebar.py) (next to the existing `Import KF` row).
- [ ] Append Phase 10 entry to [`ROADMAP.md`](ROADMAP.md) under `## Phase 10 — KF animation export (v1.1)`; CHANGELOG entries under `## [Unreleased] / ### Added` (one bullet per sub-step matching the dense Phase 9 style).
- [ ] Tick every 10b-10g checkbox in this file from the matching commits.

## Relevant files

- [`tools/codegen/parser.py`](../tools/codegen/parser.py) / [`cond_compiler.py`](../tools/codegen/cond_compiler.py) (or new `template_resolver.py`) — `#T#` resolution
- `tools/codegen/tests/` — new template-resolution tests
- [`nifblend/format/generated/blocks.py`](../nifblend/format/generated/blocks.py) + [`structs.py`](../nifblend/format/generated/structs.py) — regenerated
- `nifblend/bridge/animation_props.py` — **new**, Action + PoseBone PropertyGroups
- [`nifblend/bridge/animation_in.py`](../nifblend/bridge/animation_in.py) — extend with `BoneTrackMetadata` + metadata stamping
- `nifblend/bridge/animation_out.py` — **new**, the export bridge
- `nifblend/ops/export_kf.py` — **new**, the export operator
- [`nifblend/ops/import_kf.py`](../nifblend/ops/import_kf.py) — extend to stamp pose-bone metadata after retargeting
- [`nifblend/ui/sidebar.py`](../nifblend/ui/sidebar.py) — add `Export KF` button row
- [`nifblend/__init__.py`](../nifblend/__init__.py) — register new classes, wire `_menu_func_export`
- `nifblend/tests/test_animation_props.py` — **new**
- `nifblend/tests/test_animation_out.py` — **new**
- `nifblend/tests/test_export_kf_op.py` — **new**
- [`test_animation_in.py`](../nifblend/tests/test_animation_in.py) + [`test_import_kf_op.py`](../nifblend/tests/test_import_kf_op.py) + [`test_kf_io.py`](../nifblend/tests/test_kf_io.py) — backfill metadata + real-keyed-data round-trip tests
- [`ROADMAP.md`](ROADMAP.md) + [`CHANGELOG.md`](CHANGELOG.md) — append Phase 10 entries

## Verification

1. `python -m tools.codegen --check` clean post-regeneration (CI gate).
2. `pytest` — full suite green; expect ~50 new tests across the four new test modules + backfills.
3. `ruff check` clean across every new + modified file.
4. End-to-end **import .kf → modify Action keyframe in fake bpy → export .kf → re-import → AnimationData equality** within `1e-5` for translation / scale and `1e-4` for quaternion components.
5. Manual Blender 5.0 verification: import a vanilla Skyrim SE `.kf` against the matching skeleton, scrub the timeline, export, diff against original via NifSkope (or `read_nif` byte-faithful comparison after stripping header padding).

## Decisions

- **Cycle type / interpolation defaults** when Blender doesn't provide a source: `cycle_type=CYCLE_CLAMP`, `frequency=1.0`, `weight=1.0`, `interpolation=LINEAR_KEY`. Matches both vanilla Skyrim SE outputs and the Phase 5.21 import default expectations.
- **Quaternion order**: NIF `(w, x, y, z)` matches Blender `rotation_quaternion` — no swizzle (mirrors decoder).
- **Non-uniform animated scale**: warn + take channel 0. NIF `NiTransformData` carries one `KeyGroup` of `float` for scale; the import side already fans this to all three Blender axes. Detecting non-uniform export source + warning is the cleanest contract.
- **Static transforms**: when a `BoneTrack` has zero keys on every channel, emit a `NiTransformInterpolator` with the Blender bone's bind-pose `NiQuatTransform` and `data=-1` (no `NiTransformData`). Matches the FO4 idle-pose pattern.
- **String-table reuse**: orchestrator allocates one entry per unique string across the whole table (sequence names, accum-root names, bone names, controller-type strings) — `assemble_kf_block_table` owns this.
- **Out of scope**: NLA strip blending semantics beyond first-active-strip per track, animation events from non-`text_keys` sources, `NiPSysEmitterCtlr` / particle controllers, `NiControllerManager` synthesis (only consume the existing ref on import; export emits `manager=-1`).

## Phase ordering

10a → (10b ‖ 10c) → 10d → 10e → 10f → 10g.

10a (this file) lands first as the user-requested deliverable. 10b (codegen) and 10c (PropertyGroups) then run in parallel; everything downstream chains.

## Beyond v1.1

Natural follow-on candidates surfaced by the Phase 9/10 work, captured here so they don't get lost when this file folds back into `ROADMAP.md`:

- **Real-fixture corpus** (`pytest.mark.requires_kf_assets`, default-skipped — mirror the `requires_starfield_assets` pattern from Phase 9f). Vanilla Skyrim SE `.kf` files extracted to `nifblend/tests/data/kf/` for byte-faithful round-trip coverage.
- **KF export edge cases**: NLA strip flattening (multiple strips contributing to one bone); accum-root in-place vs root-motion handling (`accum_flags` bit semantics).
- **Starfield export (v2)** — inverse of Phase 9. `MeshData → .mesh` binary writer + `MaterialData → .mat` JSON encoder + `BSGeometry` write path.
- **FO76 external `.mesh` parser** — likely shares 80%+ with Phase 9b's Starfield decoder; opportunistic spinoff.
- **Collision (`bhk*`)** — biggest remaining modder ask. Full Havok rigid-body + shape-primitive support (`bhkCollisionObject`, `bhkRigidBody`, box/sphere/capsule/list/convex/MOPP shapes).
- **Morph / shape-key controllers** (`NiGeomMorpherController`) — Blender shape-keys ↔ morph data round-trip.
- **EGM / TRI files** (facegen) — companion morph/animation files for Bethesda character editors.

## References

- Phase 5 (KF import): [`nifblend/io/kf.py`](../nifblend/io/kf.py), [`nifblend/bridge/animation_in.py`](../nifblend/bridge/animation_in.py), [`nifblend/ops/import_kf.py`](../nifblend/ops/import_kf.py)
- Phase 9 (Starfield import) sub-step style template: see `## Phase 9 — Starfield import (v1.1)` block in [`ROADMAP.md`](ROADMAP.md)
- Schema entry points: [`NiControllerSequence`](../nifblend/format/generated/blocks.py), [`ControlledBlock`](../nifblend/format/generated/structs.py), [`NiTransformInterpolator`](../nifblend/format/generated/blocks.py), [`NiTransformData`](../nifblend/format/generated/blocks.py), [`KeyGroup`](../nifblend/format/generated/structs.py), [`Key`](../nifblend/format/generated/structs.py), [`QuatKey`](../nifblend/format/generated/structs.py), [`NiTextKeyExtraData`](../nifblend/format/generated/blocks.py)
