# nifgen — reference-only placeholder

## Status

**Empty by design.** NifBlend does **not** vendor a pre-built `nifgen` at runtime. After Phase 1.2 was attempted and hit the blockers documented below, the project pivoted to an in-house codegen pipeline that emits its own schema layer directly from a pinned `nif.xml`. See [`tools/codegen/`](../../tools/codegen/) and [`nifblend/format/generated/`](../../nifblend/format/generated/).

This directory is kept as an empty Python package so any historical / external references to `nifblend.vendor.nifgen.*` stay importable, and as an anchor for the notes below.

## What this means for contributors

- **Do not add a runtime dependency on a vendored nifgen here.** Schema-derived code lives under [`nifblend/format/generated/`](../../nifblend/format/generated/) and is regenerated via `python -m tools.codegen` (CI-gated by `--check`).
- **You may consult external nifgen implementations as a design reference**, in particular:
  - [`blender_niftools_addon`](https://github.com/niftools/blender_niftools_addon) bundles a working built `nifgen/` under `dependencies/` — useful for cross-checking field order, version branches, and read/write semantics for tricky niobjects.
  - [`OpenNaja/cobra-tools`](https://github.com/OpenNaja/cobra-tools) `codegen/` — useful for cross-checking how the schema cond DSL is interpreted.
- **Code may be ported from those projects under GPL-3.0** (NifBlend is GPL-3.0-or-later to match `nif.xml`'s license). Attribute the upstream file in a comment when you do, and keep ported code on the bridge / runtime side rather than re-introducing it here.

## History: why we pivoted

Phase 1.2 originally targeted vendoring a pre-built nifgen tree. The toolchain that produces it consumes:

- `nif.xml` from [niftools/nifxml](https://github.com/niftools/nifxml) — the canonical NIF schema (GPL-3.0)
- `basic.py` + `versions.py` — hand-written primitive bindings from [Candoran2/new-pyffi](https://github.com/Candoran2/new-pyffi) under `formats/nif/`
- `base/` format — primitives (Byte, Uint, …) from cobra-tools' own `source/formats/base/`

Reproduction sketch (from a cobra-tools clone) we were experimenting with:

```pwsh
# Set up source tree
$src = "source/formats/nif"
Copy-Item nifxml/nif.xml -Destination $src
Copy-Item new-pyffi/formats/nif/basic.py -Destination $src
Copy-Item new-pyffi/formats/nif/versions.py -Destination $src
# Generate into the final vendor location so import paths are baked correctly
python -m codegen -s source -g <repo>/nifblend/vendor/nifgen -f nif base
```

### Blockers encountered (April 2026)

1. **Path baking.** `codegen` writes the absolute-`os.sep`-joined output path into every generated import statement (e.g. `from C:.GitHub.NifBlend.nifblend.vendor.nifgen.formats...`). A post-pass string sweep (`replace("C:.GitHub.NifBlend.", "")`) is required.
2. **Bare `nifgen.*` imports** appear in the hand-written `new-pyffi` files (`basic.py`, `versions.py`). Same sweep must rewrite `nifgen.*` → `nifblend.vendor.nifgen.*` while avoiding double-prefixing.
3. **Generator emits invalid Python in some BS Havok niobjects.** Encountered `el (versions.is_v20_2_0_7_fo3(...)` (a truncated `elif` keyword) in `bshavok/structs/BhkNiCollisionObject.py`. Likely a templating bug in the upstream `cobra-tools` generator interacting with `nif.xml` conditional expressions.

The reference `blender_niftools_addon` ships nifgen as a separate dependency built by its own CI, sidestepping these issues by pinning a known-good build artifact.

### Why we didn't take "vendor a pre-built artifact" either

It was the lowest-friction unblock at the time and is still a valid escape hatch. We chose the in-house emitter instead because:

- The closure-walked whitelist ([`tools/codegen/whitelist.py`](../../tools/codegen/whitelist.py)) keeps the generated surface area small and reviewable (~138 types, not the full ~860).
- The full pipeline (`nif.xml` → AST → cond compiler → emit) is auditable in this repo, with a CI `--check` gate against drift.
- We avoid taking a runtime dependency on the upstream generator's bugs and release cadence.

If the in-house path ever proves untenable for a niobject family, falling back to porting the equivalent code from upstream nifgen under GPL-3.0 is explicitly allowed.

## License

`nif.xml` is **GPL-3.0**, so any code derived from it (in-house or vendored) inherits GPL-3.0. NifBlend's repo [`LICENSE`](../../LICENSE) is GPL-3.0-or-later to match.
