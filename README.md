# NifBlend

Fast NIF/KF import/export for Bethesda game modding, as a Blender 5.0+ extension.

> **Status:** pre-alpha. See [`ROADMAP.md`](ROADMAP.md) for the plan and [`CHANGELOG.md`](CHANGELOG.md) for what's shipped.

## Supported games (target for v1.0)

Morrowind, Oblivion, Fallout 3 / NV, Skyrim LE, Skyrim SE, Fallout 4 / 76. Starfield is targeted for v1.1.

## Why another NIF addon?

- **Speed** — numpy-vectorized I/O and batched Blender data writes; target ≥3× faster than the reference addon for typical Skyrim SE armor.
- **Modern packaging** — Blender 5.0+ extension format with declared wheel deps; no manual install dance.
- **First-class BSTriShape** — preserved on round-trip, no silent conversion to NiTriShape.
- **Batch operations** — import/export entire folders, with viewport LOD preview.

## Building

```pwsh
pip install -e ".[dev]"
pytest
```

## License

GPL-3.0-or-later. The vendored `nifblend/vendor/nifgen/` (when populated) derives from [`nif.xml`](https://github.com/niftools/nifxml) which is GPL-3.0. See [`LICENSE`](LICENSE) and [`nifblend/vendor/nifgen/UPSTREAM.md`](nifblend/vendor/nifgen/UPSTREAM.md).

## References

- [`blender_niftools_addon`](https://github.com/niftools/blender_niftools_addon)
- [pyffi NIF format](https://www.niftools.org/pyffi/pyffi/formats/nif.html)
- [pyffi KFM format](https://www.niftools.org/pyffi/pyffi/formats/kfm.html)
