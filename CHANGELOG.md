2# Changelog

All notable changes to NifBlend are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project roadmap and changelog scaffolding (Phase 0): `ROADMAP.md`, `CHANGELOG.md`, `CONTRIBUTING.md`.
- Project skeleton (Phase 1.1): `pyproject.toml`, `blender_manifest.toml`, `ruff.toml`, `mypy.ini`, `pytest.ini`, `.editorconfig`, `.gitignore`, `LICENSE` (GPL-3.0-or-later), `README.md`.
- Blender extension entry point with stub Import/Export NIF operators wired into File menu (Phase 1.3).
- CI workflow running `ruff` lint + format check, `mypy --strict` on `bridge/io/format`, and pytest smoke suite (Phase 1.4).
- Headless test bootstrap: repo-root `conftest.py` stubs `bpy`/`bpy_extras` so unit tests run without Blender; `scripts/run_tests.py` runs the same suite inside Blender for integration tests.
- `nifblend/vendor/nifgen/UPSTREAM.md` documenting the vendoring plan, toolchain, blockers encountered, and recommended next attempt for Phase 1.2.
- Smoke test `nifblend/tests/test_generated_imports.py` verifying the generated schema layer imports cleanly, every whitelisted seed type lands in the closure, and `python -m tools.codegen --check` reports no drift.
- **Phase 2.5 — buffered I/O substrate**: `nifblend/io/reader.py` (`NifReader`, `open_nif`) and `nifblend/io/writer.py` (`NifWriter`, `open_nif_writer`) wrap stdlib buffered streams with the minimal `IO[bytes]` surface the generated `Block.read`/`write` methods consume, plus NIF-specific helpers (`peek`, `expect`, `skip`, `at_eof`, `remaining`, `reserve_u32`, `patch_u32`).
- **Phase 2.5 — primitives widening**: added `read_array_u8`/`i16`/`f16` (+ writers), packed compound array helpers (`read_half_vec2_array`, `read_half_vec3_array`, `read_byte_vec3_array`, `read_byte_color4_array`, `read_triangle_array`), and a vectorised `read_packed_vertex_data` / `write_packed_vertex_data` fast path keyed on `vertex_dtype_for_desc(desc)` for BSTriShape's `BSVertexData` payloads. The packed dtype matches the generated per-record reader byte-for-byte (covered by a cross-check test).
- Test suites `nifblend/tests/test_primitives.py` (29 tests) and `nifblend/tests/test_io.py` (13 tests) covering scalars, bulk arrays, packed compounds, BSVertexData layouts, and reader/writer + path/stream/bytes construction modes.

### Changed

- **Phase 1.2 pivot**: dropped the plan to vendor a pre-built `nifgen` from `blender_niftools_addon` / cobra-tools and replaced it with an in-house codegen pipeline (`tools/codegen/` → `nifblend/format/generated/`) that emits its schema layer directly from the pinned [`nifblend/schema/nif.xml`](nifblend/schema/nif.xml). [`nifblend/vendor/nifgen/`](nifblend/vendor/nifgen/) is now an empty reference-only placeholder; upstream nifgen implementations may be consulted (and code ported under GPL-3.0) but are not a runtime dependency. Roadmap Phase 1.2 (steps 2, 2a–2f) and the architecture diagram, decisions, references, and Phase 2 step list updated accordingly. [`nifblend/vendor/nifgen/UPSTREAM.md`](nifblend/vendor/nifgen/UPSTREAM.md) rewritten to reflect the pivot and preserve the original blocker notes as history.
- License switched from BSD-3-Clause to **GPL-3.0-or-later**. Required because the `nifgen` schema layer (Phase 1.2) is derived from `niftools/nifxml`'s `nif.xml`, which is GPL-3.0; any project bundling code generated from it must be GPL-compatible. `LICENSE` contains the canonical GPL-3.0 text.
- ROADMAP TL;DR, architecture diagram, decisions, and references sections updated to reflect GPL-3.0 + GPL-derived `nifgen` (post-license-switch consistency pass).
- Phase 1.2 step expanded with a sub-step (2a) describing the concrete resume path: extract `nifgen/` from a `blender_niftools_addon` release zip, rewrite `from generated.` import prefixes to `nifblend.vendor.nifgen.`, smoke-test the import.

### Deprecated

### Removed

### Fixed

- Codegen `cond_compiler` now accepts numeric literals with a leading `+` and signed-exponent floats (e.g. `+3.402823466e+38`, `-1.0E-7`) — the operand regex was previously `-?` only, so positive-signed exponent constants raised `ValueError: unexpected operand`.
- Codegen `_class_name` collapses C++-style `::` scope separators (`BSSkin::Instance` → `BSSkinInstance`) so Bethesda namespaced niobjects emit valid Python class names.
- `pytest.ini`'s `testpaths` now also includes `tools/codegen/tests` so the cond-compiler suite runs under the default `pytest` invocation (was previously only collected when explicitly pointed at).

### Security
