"""NifBlend codegen — dev-time only.

Consumes `nifblend/schema/nif.xml` (vendored snapshot of `niftools/nifxml`
under GPL-3.0) and emits typed Python classes into
`nifblend/format/generated/`. Output is committed to git so end users do not
need this toolchain.

Run:

    python -m tools.codegen --schema nifblend/schema/nif.xml \\
                            --out nifblend/format/generated/

CI uses `--check` to fail the build if committed output drifts from a fresh
generation.
"""
