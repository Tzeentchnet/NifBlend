# Starfield `.mesh` format — reference + binary layout

> **Reference-only attribution.** Format knowledge in this document was
> compiled by reading public reverse-engineering notes and the documentation
> shipped with [`SesamePaste233/StarfieldMeshConverter`](https://github.com/SesamePaste233/StarfieldMeshConverter)
> (SGB). NifBlend's Starfield code is a **clean-room Python rewrite** —
> no MIT-licensed source from SGB has been ported. The `.mesh` and `.mat`
> on-disk formats themselves are not copyrightable; the implementation
> below was authored from-scratch against this layout description.

## Asset extraction (end-user workflow)

Vanilla Starfield ships geometry inside `meshes01.ba2` / `meshes02.ba2`.
Users must extract the loose `.mesh` files with a BA2 tool (BSA Browser,
Bethesda Archive Extractor, or B.A.E.) before NifBlend can resolve them.
Materials live in `materials*.ba2` as `.mat` JSON manifests.

After extraction the layout is:

```
<assets-root>/
  meshes/<8-hex-prefix>/<8-hex-suffix>.mesh
  materials/<...>/<name>.mat
  textures/<...>/<name>.dds       # BC1 / BC3, identical to FO4/FO76
```

Configure `<assets-root>` as the `Starfield Data` root in NifBlend's
preferences. The Phase 9c [`ExternalAssetResolver`](../../bridge/external_assets.py)
walks paths under that root using the same case-insensitive +
fuzzy-fallback strategy as Phase 8i [`resolve_texture_path`](../bridge/textures.py).

## `.mesh` v1 binary layout (little-endian)

```
u32  magic        // currently observed: 1 (v1)
u32  num_indices  // total triangle indices (= num_triangles * 3)
u16  indices[num_indices]
f32  scale        // 1.0 for unscaled positions; otherwise positions are snorm i16 / 32767 * scale
u32  num_weights_per_vertex   // 0 (static) or 8 (skinned)
u32  num_positions
vec3 positions[num_positions]   // f32 triplet OR i16 snorm triplet (gated on `scale != 1.0`)
u32  num_uvs
half_vec2 uvs[num_uvs]          // 16-bit half-float per channel
u32  num_uvs2
half_vec2 uvs2[num_uvs2]
u32  num_colors
u8   colors[num_colors][4]      // RGBA
u32  num_normals
u32  packed_normals[num_normals]   // 10/10/10/2 oct-encoded
u32  num_tangents
u32  packed_tangents[num_tangents]
u32  num_weights                   // expected to equal num_positions when num_weights_per_vertex > 0
u8   bone_indices[num_weights][num_weights_per_vertex]
u16  bone_weights[num_weights][num_weights_per_vertex]   // unorm u16 / 65535
u32  num_lods
LOD  lods[num_lods]                // per-LOD index-slice triplet (start, count, distance)
u32  num_meshlets
... meshlet stream (deferred — not consumed by v1.1 import) ...
u32  num_culldata
... cull-data stream (deferred — not consumed by v1.1 import) ...
```

The `nifblend.format.starfield_mesh` decoder consumes the **headline
geometry surface** (everything up to and including the LOD slice list);
the trailing meshlet + culldata streams are recognised as optional
trailers and skipped. Round-trip parity is preserved for the geometry
surface only.

### Per-LOD slice (`LOD`)

```
u32  start_index   // offset into `indices`
u32  num_indices   // slice length, multiple of 3
f32  distance      // distance threshold (engine-side; informational)
```

## `.mat` JSON layout

Starfield materials are a small JSON manifest. Keys observed in vanilla
assets and consumed by the v1.1 [`starfield_material`](../../bridge/games/starfield_material.py)
reader:

```jsonc
{
  "Type": "Material",
  "Name": "<material name>",
  "BaseColor":   [r, g, b],            // 0..1 floats
  "EmissiveColor": [r, g, b],
  "EmissiveIntensity": <float>,
  "Roughness":   <float>,
  "Metalness":   <float>,
  "Textures": {
    "BaseColor": "textures/<...>.dds",
    "Normal":    "textures/<...>.dds",
    "Roughness": "textures/<...>.dds",
    "Metallic":  "textures/<...>.dds",
    "Emissive":  "textures/<...>.dds"
  }
}
```

Unknown keys are preserved verbatim on the `MaterialData.starfield_extras`
dict so a future export round-trip can re-emit them unchanged.

## Out-of-scope for v1.1

- **Export.** The v1.1 slice is import-only.
- **Morphs.** The `.morph` companion file is not consumed.
- **Cloth physics.** `physics_data.bin` and the SGB cloth-graph nodes are
  not consumed.
- **Havok constraints.** Static collision (`hk*` types) is not consumed.

Track these as v2 work; revisit only if modder demand surfaces after
v1.1 ships.
