# nif.xml — vendored schema snapshot

## Source

- Repository: [niftools/nifxml](https://github.com/niftools/nifxml)
- Branch: `develop`
- Commit: `292bb9403cbf4052c58d66e80906b6bde1700779`
- Commit date: 2024-09-15
- Retrieved: 2026-04-19
- Source URL: https://raw.githubusercontent.com/niftools/nifxml/292bb9403cbf4052c58d66e80906b6bde1700779/nif.xml
- File size: 570454 bytes
- SHA-256: `752C79786CEB217641FD7E94BE4033898C97E9AA38025BF05F2CBEE9CFFBBF0D`

## Why vendored

NifBlend is standalone — we do not depend on any niftools or cobra-tools toolchain at
build or runtime. `nif.xml` is the canonical NIF binary-format schema and is treated
here as a frozen GPL-3.0 data snapshot. Our own codegen
(`tools/codegen/`, dev-time only) consumes this file to emit the typed Python classes
under `nifblend/format/generated/`.

## License

`nif.xml` is GPL-3.0. Generated code derived from it inherits GPL-3.0, which matches
the repository's `LICENSE`.

## Updating

1. Pick a new upstream commit, fetch the raw XML, replace this file.
2. Update the SHA, date, and SHA-256 above.
3. Re-run `python -m tools.codegen --schema nifblend/schema/nif.xml --out nifblend/format/generated/`.
4. Review the diff in `nifblend/format/generated/`, run `pytest`, commit.
