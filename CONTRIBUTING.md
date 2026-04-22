# Contributing to NifBlend

Thanks for helping! Two lightweight rules keep the project honest:

1. **Update [`CHANGELOG.md`](CHANGELOG.md) on every PR.** Add a bullet under `[Unreleased]` in the appropriate subsection (`Added` / `Changed` / `Fixed` / `Deprecated` / `Removed` / `Security`). One line, user-visible language. Releases promote `[Unreleased]` to a versioned heading.
2. **Tick boxes in [`ROADMAP.md`](ROADMAP.md) as steps land.** Find the step you completed under its phase and change `- [ ]` to `- [x]`. If a step's scope changes mid-flight, edit the step text in the same PR — the roadmap is the living plan, not a frozen spec.

## Quick orientation

- **What** we're building, **why**, and **in what order**: see [`ROADMAP.md`](ROADMAP.md).
- **What has shipped** in each release: see [`CHANGELOG.md`](CHANGELOG.md).
- **Architecture**: clean-room Blender bridge on top of a vendored `nifgen` schema layer. Don't modify `nifblend/vendor/nifgen/` in feature PRs — upstream syncs are separate commits.

## Code style

- `ruff` for lint + format
- Tests via `pytest`; Blender-integration tests run headless via `blender --background -P scripts/run_tests.py`
