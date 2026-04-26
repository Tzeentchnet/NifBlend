# NifBlend

Fast NIF/KF import/export for Bethesda game modding, as a Blender 5.0+ extension.

> **Status:** pre-alpha. Phases 0–9 of the [`roadmap`](docs/ROADMAP.md) are complete, with Phase 10 KF export work in progress (~678 passing tests). See [`CHANGELOG.md`](docs/CHANGELOG.md) for full per-phase detail.

## Supported games

Morrowind, Oblivion, Fallout 3 / NV, Skyrim LE, Skyrim SE, Fallout 4, Fallout 76, and Starfield. Starfield support is import-only for now: external `.mesh` geometry, skin influences, LOD slices, and `.mat` JSON materials are decoded from loose files under a configured Starfield `Data` root.

## Why another NIF addon?

- **Speed** — numpy-vectorized binary I/O, batched `foreach_set` mesh writes, vectorised keyframe insertion via `keyframe_points.add(n)` + `foreach_set("co", flat)`, and parallel batch parse / write through a thread pool (the `BlockTable` walk and bulk-array reads release the GIL).
- **Modern packaging** — Blender 5.0+ extension format with declared wheel deps; no manual install dance.
- **First-class BSTriShape** — preserved on round-trip, no silent conversion to NiTriShape.
- **In-house schema codegen** — [`tools/codegen/`](tools/codegen/) emits [`nifblend/format/generated/`](nifblend/format/generated/) directly from a pinned [`nif.xml`](nifblend/schema/nif.xml). CI gates drift via `python -m tools.codegen --check`.
- **Lossless round-trip** — typed `PropertyGroup`s on `Mesh` / `Material` / `Bone` / `VertexGroup` / `Object` preserve every NIF flag, shader bit, dismember partition, and 4×4 bind matrix Blender's native data model can't represent.

## Features

### File formats

- **NIF read/write** for all v0.3 → v20.2 BSVersion families through a single buffered, version-aware [`BlockTable`](nifblend/io/block_table.py) pipeline. Header magic, string table, block-type table, footer roots, and raw u32 cross-references all round-trip byte-faithfully.
- **KF read** with vectorised keyframe decode through [`bridge/animation_in.py`](nifblend/bridge/animation_in.py); detection + iteration helpers in [`io/kf.py`](nifblend/io/kf.py). KF *export* is out of scope for v1.0.

### Meshes

- **BSTriShape** (Skyrim SE) — full `BSVertexDesc`-driven packed-vertex import/export with half-float positions/UVs and byte-encoded normals/tangents/colors.
- **NiTriShape / NiTriStrips** (Morrowind, Oblivion, FO3-NV) — strip→triangle decode and on-data vertex/normal/UV/colour streams.
- **BSSubIndexTriShape** (Fallout 4) — geometry decode plus a `MeshSegments` sidecar (segments, sub-segments, SSF path, per-segment user indices).
- **BSGeometry** (Fallout 76 / Starfield) — Fallout 76 LOD slot mesh-refs are preserved; Starfield populated LOD slots resolve external `.mesh` files through the configured asset resolver and materialise one Blender mesh per LOD.
- **Starfield `.mesh`** — clean-room v1 decoder/encoder for external geometry, including positions, indices, normals, tangents, UVs, vertex colours, per-vertex skin weights, and LOD slices. Meshlet / cull-data trailers are recognised as out of scope for the current import slice.

### Materials

- **BSLightingShaderProperty** + **BSEffectShaderProperty** (Skyrim SE / FO4) — Principled BSDF graph with diffuse / normal / glow texture nodes, plus a sibling `BSShaderTextureSet` and `NiAlphaProperty` (`BLEND` / `CLIP` mapped to Blender `blend_method`).
- **BSShaderPPLightingProperty** (FO3 / NV) — six-slot texture set, refraction + parallax scalars, `Color4`-alpha-as-emissive-multiplier handling.
- **NiMaterialProperty + NiTexturingProperty + NiSourceTexture** (Morrowind, Oblivion) — twelve-slot classic texturing (diffuse / dark / detail / gloss / glow / bump / normal / height / decal0..3) with inline `FilePath` round-trip.
- **Starfield `.mat` JSON** — material manifests attached to `BSGeometry` resolve through the same external-asset pipeline, decode into the existing `MaterialData` model, and build a Principled BSDF graph with Starfield texture-channel labels mapped onto NifBlend's texture slots. Imported materials remember their source `.mat` path for in-place reloads.
- All shader flags, glossiness, specular state, and per-game-only fields are preserved verbatim through [`NifBlendMaterialProperties`](nifblend/bridge/material_props.py) for lossless export even when Blender's BSDF can't represent the field natively.

### Armatures, skin, animation

- **Armature import** with full 4×4 bind matrices stamped on each `Bone.nifblend.bind_matrix` PropertyGroup so the `(head, tail, roll)` reduction Blender forces is recoverable on export.
- **Skin import** — vectorised numpy decode for both classic (`NiSkinInstance` + `NiSkinData`) and per-vertex (`BSVertexDataSSE.bone_indices` / `bone_weights`) layouts; bucket-batched vertex-group writes (one Blender API call per influence-class).
- **Skin export** — `NiSkinPartition` rebuilder with greedy first-fit triangle packing under per-game limits (Morrowind 4/4, Oblivion+FO3-NV 18/4, Skyrim LE+SE 80/4, FO4 80/8, FO76 100/8).
- **BSDismemberSkinInstance** — partition flags + body-part IDs round-tripped via a `VertexGroup.nifblend` PropertyGroup.
- **KF animation import** — `NiTransformInterpolator` → fcurves (translation / rotation / scale) with bulk `keyframe_points.add(n)` + `foreach_set("co", flat)` for 10–100× speedup over per-frame `keyframe_insert`. Quaternion (lossless) or Euler (intrinsic XYZ) rotation mode toggle. Retargeting onto a chosen scene armature with a missing-bone warning report.

### Operators

- **File → Import** — NIF, KF Animation, NIF Folder (batch), NIF Cell (CSV layout).
- **File → Export** — NIF, NIF Folder (batch), xEdit Cell Script (`.pas`).
- **Batch import/export** — split into a parallel parse phase (thread-pooled, GIL-releasing) and a serialised Blender-data materialisation phase. Configurable worker count via add-on prefs.
- **xEdit cell workflow** — bundled [`scripts/blender_export.pas`](nifblend/scripts/blender_export.pas) generates a `# model,x,y,z,rx,ry,rz,scale` CSV from any cell; the cell importer parses it, deduplicates mesh paths (one parse per `.nif` even if the cell references it 50 times), and instances or copies the data per row.
- **LOD preview** — sidebar panel auto-detects `NiLODNode` and `BSLODTriShape` groups, materialises one collection per LOD level, and exposes per-level visibility toggles + a "show only this level" radio.

### Sidebar UI (`NifBlend` N-panel tab)

- **Main** — detected `GameProfile` + manual override + source-file readout + quick-action grid for every importer/exporter.
- **Utilities** — generic post-import cleanup (delete empties, delete collision shells, combine by material, clear extra materials, recenter to origin, apply Bethesda scale, fix viewport clip) and mesh hygiene (merge doubles with UV/normal-seam guards, recalc normals outside, split by material slot, weld UV seams). Every cleanup op offers `'SELECTED' | 'SCENE'` scope (defaults to `SELECTED` to avoid the NifCity scene-wide footgun).
- **Game-specific** — sub-panels gated on the active object's stamped `GameProfile`:
  - **Skyrim LE ↔ SE** shader-flag conversion (re-stamps `bs_version` 83 ↔ 100).
  - **Oblivion stripify** — greedy adjacency walk; strip arrays cached on `mesh["nifblend_strips"]`.
  - **Fallout 4** — `BSSubIndexTriShape` segment list editor (promote / add / remove) with read-only UIList over the imported sidecar.
  - **Fallout 76** — `BSGeometry` per-slot external-mesh-ref editor (LOD0–LOD3 paths).
  - **Starfield** — external `.mesh` reload for stamped LOD slots, plus `.mat` material reload for stamped material slots after a Data-root change or manifest edit.
  - **Fallout 3 / NV** — `BSShaderPPLightingProperty` field editor (PP flags, env-map scale, clamp mode, refraction + parallax scalars).
  - **Morrowind** — classic-prop split preview + ambient/diffuse/specular/glossiness/texturing-flag editor.
- **Texture utilities** — relink `bpy.data.images` against per-game `Data/` roots (`STRICT` / `CASE_INSENSITIVE` / `FUZZY_LOOSEN_ROOT` modes); misses surfaced via UIList. Bake operator (DIFFUSE / EMIT / NORMAL / ROUGHNESS) with auto-inserted `TEX_IMAGE` node.
- **Cell workflow** — xEdit script export + cell CSV import + recenter + clip-fit.

### Add-on preferences

Per-game `Data/` roots (including Starfield loose-file assets), default `GameProfile`, texture resolution mode, batch worker count, default KF rotation mode, auto-stamp toggle, and four cell-import defaults (mesh root, normalize-location, instance-duplicates, exclude-prefixes).

### Performance harness

[`nifblend/bench.py`](nifblend/bench.py) + [`scripts/bench.py`](scripts/bench.py) time `parse_and_decode_many` against `blender_niftools_addon`'s `NifFormat.Data().read` and emit a Markdown comparison table (gracefully no-ops when the reference addon isn't installed). The ≥3× speedup target gates Phase 7.

## Building

```pwsh
pip install -e ".[dev]"
pytest -c tests/pytest.ini
```

Regenerate the schema layer after touching [`nifblend/schema/nif.xml`](nifblend/schema/nif.xml):

```pwsh
python -m tools.codegen           # write
python -m tools.codegen --check   # CI drift gate
```

## License

GPL-3.0-or-later. The codegen-emitted [`nifblend/format/generated/`](nifblend/format/generated/) layer derives from [`nif.xml`](https://github.com/niftools/nifxml), which is GPL-3.0. See [`LICENSE`](LICENSE) and [`docs/schema/UPSTREAM.md`](docs/schema/UPSTREAM.md).

## References

- [`niftools/nifxml`](https://github.com/niftools/nifxml) — canonical NIF schema
- [`blender_niftools_addon`](https://github.com/niftools/blender_niftools_addon) — reference addon
- [`OpenNaja/cobra-tools`](https://github.com/OpenNaja/cobra-tools) — reference codegen for the `nifxml` cond DSL
- [pyffi NIF format](https://www.niftools.org/pyffi/pyffi/formats/nif.html)
- [pyffi KFM format](https://www.niftools.org/pyffi/pyffi/formats/kfm.html)
