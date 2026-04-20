# NifBlend Roadmap

> Contributor-facing source of truth for what NifBlend is building, in what order, and how we'll know it works. Tick checkboxes as steps land. Record what *shipped* in [`CHANGELOG.md`](CHANGELOG.md).

## TL;DR

NifBlend is a greenfield Blender 5.0+ extension for importing/exporting Bethesda NIF and KF files (Morrowind → Fallout 76; Starfield deferred to v1.1). Architecture: an **in-house generated schema layer** (`nifblend/format/generated/`, emitted from a pinned snapshot of `niftools/nifxml`, GPL-3.0) plus a **clean-room, numpy-vectorized Blender bridge** for speed and clarity. Ships in slices: Skyrim SE static mesh first, then materials, armature/skin, KF, then per-game expansion.

## Architecture overview

```
nifblend/
├── manifest/blender_manifest.toml   # Blender 5.x extension manifest (numpy wheel dep)
├── __init__.py                      # registration, operators, menu wiring
├── schema/nif.xml                   # pinned snapshot of niftools/nifxml (GPL-3.0); single source of truth
├── format/                          # game-specific dispatch + generated schema layer
│   ├── base.py / primitives.py / versions.py   # hand-written runtime substrate
│   └── generated/                   # blocks.py, structs.py, enums.py, bitfields.py — emitted by tools/codegen
├── vendor/nifgen/                   # reference-only: empty; `blender_niftools_addon`'s nifgen may be consulted for design parity
├── io/                              # buffered + numpy-vectorized binary I/O
│   ├── reader.py / writer.py
│   ├── header.py
│   └── block_table.py
├── format/                          # (continued) game-specific dispatch
│   ├── versions.py                  # GameProfile enum from (version, user, bs_version)
│   ├── bstrishape.py
│   ├── bsgeometry.py
│   └── starfield_mesh.py            # v1.1 — reserved
├── bridge/                          # Blender ↔ NIF translation (clean-room)
│   ├── mesh_in.py / mesh_out.py
│   ├── material_in.py / material_out.py
│   ├── armature_in.py / armature_out.py
│   └── animation_in.py
├── ops/                             # Blender operators
│   ├── import_nif.py / export_nif.py
│   ├── import_kf.py
│   ├── import_batch.py / export_batch.py
│   └── preview_lod.py
├── preferences.py                   # Data-folder roots per game, defaults
└── tests/                           # pytest suite + per-game golden NIFs

tools/codegen/                       # in-house schema → Python emitter
├── parser.py                        # nif.xml → AST
├── cond_compiler.py                 # schema DSL → Python expressions
├── whitelist.py                     # seed types; closure walked automatically
├── emit.py                          # writes blocks/structs/enums/bitfields
└── __main__.py                      # `python -m tools.codegen [--check]`
```

## Phased steps

### Phase 0 — Roadmap & changelog scaffolding
*Sequential, blocks all later phases.*

- [x] 0a. Create `ROADMAP.md` at repo root mirroring the plan
- [x] 0b. Create `CHANGELOG.md` (Keep a Changelog 1.1.0 + SemVer)
- [x] 0c. Add `CONTRIBUTING.md` snippet: update CHANGELOG every PR, tick ROADMAP boxes as phases land
- [x] 0d. Render per-phase Steps as GitHub task-list checkboxes

### Phase 1 — Project skeleton & schema vendoring
*All steps sequential.*

- [x] 1. Init repo: `pyproject.toml` (hatchling), `blender_manifest.toml` (Blender 5.0+, schema_version 1.0.0), `.editorconfig`, `ruff.toml`, `pytest.ini`, GPL-3.0-or-later `LICENSE`
- [x] 2. **Pivoted away from vendoring.** Instead of bundling a pre-built `nifgen` from `blender_niftools_addon` / `cobra-tools` (blocked on path-baking, bare-import rewrites, and generator bugs in BS-Havok niobjects — see [`nifblend/vendor/nifgen/UPSTREAM.md`](nifblend/vendor/nifgen/UPSTREAM.md)), NifBlend now emits its own schema layer in [`tools/codegen/`](tools/codegen/) directly from a pinned `nif.xml`. The reference `vendor/nifgen/` directory remains as an empty placeholder; `blender_niftools_addon`'s built nifgen and cobra-tools' generator may still be consulted as design references (and code may be ported under GPL-3.0), but are not a runtime dependency.
  - [x] 2a. Pin `niftools/nifxml` snapshot at [`nifblend/schema/nif.xml`](nifblend/schema/nif.xml); document update procedure in [`nifblend/schema/UPSTREAM.md`](nifblend/schema/UPSTREAM.md).
  - [x] 2b. Build `tools/codegen/` (parser → cond_compiler → emit) producing `nifblend/format/generated/{blocks,structs,enums,bitfields}.py` with structural read/write methods on every type.
  - [x] 2c. Hand-written runtime substrate in [`nifblend/format/base.py`](nifblend/format/base.py), [`primitives.py`](nifblend/format/primitives.py), [`versions.py`](nifblend/format/versions.py) (ReadContext, scalar + numpy bulk-array primitives, version packing).
  - [x] 2d. Whitelist + closure walker in [`tools/codegen/whitelist.py`](tools/codegen/whitelist.py); ~60 seed types expand to ~138 emitted (72 blocks, 66 structs, 40 enums, 7 bitfields). BSTriShape is in the closure with full read/write.
  - [x] 2e. CI gate: `python -m tools.codegen --check` enforces no drift between committed generated files and a fresh emit.
  - [ ] 2f. Pragmatic gaps to revisit when needed by Phase 2+ bridge work: `Ref`/`Ptr` read as raw u32 (resolution lives in bridge); `string` read as u32 index (header string-table lookup lives in bridge); template parameters are descriptive only; a small number of fields with unresolved types are emitted with `# CODEGEN-TODO` markers and skipped. Track real failures via Phase 2 round-trip tests rather than speculative widening.
- [x] 3. Wire Blender extension entry point (`__init__.py`) with no-op operator + File→Import/Export menu items; verify install → uninstall round-trip in Blender 5.0
- [x] 4. CI scaffolding: GitHub Actions running `ruff`, `mypy --strict` on `bridge/`+`io/`, headless Blender pytest job

### Phase 2 — MVP: Skyrim SE static mesh (BSTriShape) round-trip
*Delivers a usable v0.1. Per-block read/write is already codegen'd; this phase adds file-level orchestration + Blender bridge.*

- [x] 5. `io/reader.py` + `io/writer.py`: buffered file readers/writers wrapping the scalar/bulk primitives in [`nifblend/format/primitives.py`](nifblend/format/primitives.py); add any missing array readers (vec3, half-float vec2, packed BSVertexData) discovered while wiring BSTriShape
- [ ] 6. `io/header.py` + `io/block_table.py`: parse the NIF header (version/user/bs_version, block-type table, block sizes, string table, group sizes), drive a per-block read loop using the generated `Block.read(stream, ctx)` classmethods, expose a flat `BlockTable` with raw u32 refs preserved; inverse for write
- [ ] 7. `format/versions.py` (extend): add `GameProfile` enum with detection from `(version, user_version, bs_version)`; cover Skyrim LE/SE first
- [ ] 8. `bridge/mesh_in.py`: BSTriShape → `bpy.data.meshes.new` via `foreach_set` for positions/normals/UVs/colors/tangents. Resolves block refs and string-table indices into Blender semantics. **First-class BSTriShape** — preserved on round-trip, no NiTriShape conversion
- [ ] 9. `bridge/mesh_out.py`: inverse — `foreach_get`, build BSVertexData with appropriate flags, repack indices, allocate block-table slots and string-table entries
- [ ] 10. Wire [`ops/import_nif.py`](nifblend/ops/import_nif.py) + [`ops/export_nif.py`](nifblend/ops/export_nif.py) (currently stubs) to the bridge, then add round-trip tests: import → export → re-import; assert vertex/index/UV equality within float epsilon for ≥3 sample SSE meshes. Use failures here to drive any whitelist/codegen widening (step 2f) rather than speculating up front.

### Phase 3 — Materials
*Depends on Phase 2.*

- [ ] 11. `bridge/material_in.py`: BSLightingShaderProperty + BSEffectShaderProperty → Principled BSDF group with diffuse/normal/specular/glow texture nodes; resolve texture paths against pref-configured Data roots (case-insensitive on Windows)
- [ ] 12. `bridge/material_out.py`: inverse, reading from "NifBlend Material" node group output to preserve shader flags
- [ ] 13. Material flag preservation via typed `PropertyGroup` registered on `Material` (round-trip even when Blender can't represent the flag)

### Phase 4 — Armature & skinning
*Depends on Phase 2; parallel with Phase 3.*

- [ ] 14. `bridge/armature_in.py`: NiNode tree → Armature; preserve full 4×4 bind matrix on each bone via typed `PropertyGroup` (bone roll alone is lossy)
- [ ] 15. NiSkinInstance / NiSkinPartition / BSSkin::Instance → vertex groups, vectorized via numpy (no per-vertex Python loop)
- [ ] 16. `bridge/armature_out.py`: rebuild skin partitions, optimize splits per game limits (SLE/SSE 80 bones/partition, FO4 different)
- [ ] 17. BSDismemberSkinInstance partition support: store partition ID per vertex group via typed `PropertyGroup`

### Phase 5 — KF animation import
*Depends on Phase 4.*

- [ ] 18. KF file = standalone NIF with NiControllerSequence root; reuse Phase 1–2 reader
- [ ] 19. `bridge/animation_in.py`: NiControllerSequence → Action; for each NiTransformInterpolator → fcurves. **Vectorized keyframe insertion** — pre-allocate `keyframe_points.add(n)` then `foreach_set("co", flat)` (10–100× faster than per-frame `keyframe_insert`)
- [ ] 20. Quaternion → Euler / native quaternion rotation mode toggle in import operator
- [ ] 21. `ops/import_kf.py` operator + retargeting onto a selected armature

### Phase 6 — Per-game expansion
*Steps within phase parallel after stub adapter exists.*

- [ ] 22. Oblivion (NIF 20.0.0.5, NiTriStrips path) — strips→triangles conversion in `mesh_in`, no BSTriShape
- [ ] 23. Fallout 3 / NV (20.2.0.7 user 11/34) — BSShaderPPLightingProperty material path
- [ ] 24. Fallout 4 / 76 — BSGeometry / BSSubIndexTriShape (FO4 user 130+)
- [ ] 25. Morrowind (4.0.0.2) — older NiTriShape, NiTexturingProperty, no shader properties
- [ ] 26. ~~Starfield~~ **deferred to v1.1**. Reserve `GameProfile.STARFIELD` enum value and ensure mesh/material/animation bridge interfaces accept an `external_assets` hook so adding `format/starfield_mesh.py` later is additive

### Phase 7 — Modder differentiators
*Parallel after Phase 2.*

- [ ] 27. Batch import/export operators: `ops/import_batch.py` walks a folder, parallelizes parsing in a thread pool (I/O bound), serializes Blender data creation on the main thread
- [ ] 28. LOD preview: detect LOD0/1/2 sibling shapes (BSLODTriShape, NiLODNode), import each into its own collection, viewport toggle panel
- [ ] 29. Performance benchmark harness vs `blender_niftools_addon`; target ≥3× faster import for typical SSE armor

## Relevant files (to be created)

- `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- `blender_manifest.toml` — Blender 5.0+ extension manifest, declare numpy wheel dep
- `pyproject.toml` — dev/test deps (`pytest`, `ruff`, `mypy`, `numpy`, `fake-bpy-module-latest`)
- `nifblend/__init__.py` — `register()` / `unregister()`, operator class registration
- `nifblend/schema/nif.xml` + `tools/codegen/` — pinned schema + emitter (GPL-3.0); regenerate via `python -m tools.codegen`, gated in CI by `--check`
- `nifblend/format/generated/{blocks,structs,enums,bitfields}.py` — emitted schema layer (do not hand-edit)
- `nifblend/format/{base,primitives,versions}.py` — hand-written runtime substrate the generated code depends on
- `nifblend/vendor/nifgen/` — empty; reference-only placeholder (see [`UPSTREAM.md`](nifblend/vendor/nifgen/UPSTREAM.md))
- `nifblend/io/{reader,writer,header,block_table}.py` — numpy-vectorized binary I/O
- `nifblend/format/versions.py` — `GameProfile` enum + dispatch (extend in Phase 2)
- `nifblend/bridge/{mesh,material,armature,animation}_{in,out}.py` — clean-room Blender bridge
- `nifblend/ops/*.py` — operators
- `nifblend/preferences.py` — addon prefs
- `nifblend/tests/data/` — small per-game golden NIFs

## Verification

1. **Install round-trip** (manual): in fresh Blender 5.0, install `.zip` extension, verify operators appear, uninstall cleanly
2. **Headless test job**: `blender --background -P scripts/run_tests.py` runs pytest inside Blender's Python; CI gate
3. **Per-phase round-trip tests**: semantic equality (vertex set ≈, triangle set ≈, UV ≈, bone bind matrices ≈ within `1e-5`); byte-equivalence is unrealistic
4. **Game-load test (manual, per game)**: load exported NIF in NifSkope (visual diff vs original) and in-game where possible
5. **Performance benchmark**: `scripts/bench.py` times import of `tests/data/perf/*.nif` and compares vs reference addon (≥3× target gates Phase 7)
6. **Schema regression**: keep upstream `nifgen` tests passing as-is

## Decisions

- **Parser strategy**: in-house codegen from a pinned `nif.xml` snapshot ([`tools/codegen/`](tools/codegen/) → [`nifblend/format/generated/`](nifblend/format/generated/)) plus a **clean-room** numpy-vectorized Blender bridge. Vendoring `nifgen` from `blender_niftools_addon` / cobra-tools was attempted and abandoned (see [`nifblend/vendor/nifgen/UPSTREAM.md`](nifblend/vendor/nifgen/UPSTREAM.md)); their codebase remains a useful design reference and may be ported under GPL-3.0, but is not a runtime dependency. License remains GPL-3.0 because the schema itself is GPL-3.0.
- **Blender target**: 5.0+ only. New extension/wheel system; numpy as wheel dep declared in manifest.
- **Game scope sequencing**: Skyrim SE first (largest modding community + BSTriShape is the tricky case), then SLE, then expand outward. Morrowind last in v1.0.
- **BSTriShape is first-class**: no silent conversion to NiTriShape — preserved through round-trip.
- **License**: **GPL-3.0-or-later** to match `nif.xml` lineage (the canonical NIF schema is GPL-3.0; any code derived from it inherits the license).

### Resolved planning decisions

1. **Starfield**: deferred to v1.1. Every abstraction (GameProfile dispatch, mesh adapters, external-asset hooks) designed with Starfield in mind so adding `format/starfield_mesh.py` later is additive, not a rewrite.
2. **NIF flag storage**: typed `PropertyGroup` registered on Mesh/Material/Bone (schema-validated round-trip). Not raw ID-property dicts.
3. **Schema layer**: in-house codegen from a pinned `nif.xml` snapshot, not a vendored prebuilt nifgen. Keeps the toolchain auditable, lets us emit only the closure of types we actually need, and avoids the path-baking / generator-bug issues hit when trying to vendor cobra-tools output. Revisit if upstream `nifgen` ever stabilizes as a clean PyPI dep.

### Out of scope for v1.0

Collision (`bhk*`), Havok constraints, BSDismember editing UI, morph/shape-key controllers (`NiGeomMorpherController`), KF *export*, EGM/TRI files, Starfield. Deferred to v1.1+ / v2.

## References

- [`niftools/nifxml`](https://github.com/niftools/nifxml) — canonical NIF schema (GPL-3.0); pinned snapshot at [`nifblend/schema/nif.xml`](nifblend/schema/nif.xml)
- [`blender_niftools_addon`](https://github.com/niftools/blender_niftools_addon) — reference Blender addon; its bundled `nifgen/` is a useful design reference for read/write semantics and game-version branching, but **not** a runtime dependency for NifBlend
- [`OpenNaja/cobra-tools`](https://github.com/OpenNaja/cobra-tools) — `codegen/` generator that produces upstream `nifgen` from `nif.xml`; reference for cond DSL / version-guard idioms
- [pyffi NIF format docs](https://www.niftools.org/pyffi/pyffi/formats/nif.html#module-pyffi.formats.nif)
- [pyffi KFM format docs](https://www.niftools.org/pyffi/pyffi/formats/kfm.html#module-pyffi.formats.kfm)
