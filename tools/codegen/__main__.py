"""Codegen CLI entry point.

Usage:

    python -m tools.codegen --schema nifblend/schema/nif.xml \\
                            --out nifblend/format/generated/

    python -m tools.codegen --check
        # Compare a fresh generation against the committed output and exit
        # non-zero on any difference. Used by CI.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from .emit import emit_all
from .parser import parse_schema
from .whitelist import SEED_TYPES

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SCHEMA = _REPO_ROOT / "nifblend" / "schema" / "nif.xml"
_DEFAULT_OUT = _REPO_ROOT / "nifblend" / "format" / "generated"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m tools.codegen",
        description="Generate NifBlend's typed NIF schema layer from nif.xml.",
    )
    p.add_argument("--schema", type=Path, default=_DEFAULT_SCHEMA)
    p.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    p.add_argument(
        "--check",
        action="store_true",
        help="Diff a fresh generation against committed output; exit non-zero on drift.",
    )
    return p


def _format_diff(a: str, b: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile=f"committed/{name}",
            tofile=f"regenerated/{name}",
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    schema = parse_schema(args.schema)
    result = emit_all(schema, SEED_TYPES)

    if args.check:
        any_drift = False
        for name, src in result.files.items():
            committed_path = args.out / name
            committed = committed_path.read_text(encoding="utf-8") if committed_path.exists() else ""
            if committed != src:
                any_drift = True
                sys.stderr.write(f"DRIFT: {committed_path}\n")
                sys.stderr.write(_format_diff(committed, src, name))
        # Detect orphan files in --out that codegen would not produce.
        if args.out.exists():
            for child in args.out.iterdir():
                if child.is_file() and child.name not in result.files:
                    any_drift = True
                    sys.stderr.write(f"ORPHAN: {child}\n")
        return 1 if any_drift else 0

    args.out.mkdir(parents=True, exist_ok=True)
    for name, src in result.files.items():
        (args.out / name).write_text(src, encoding="utf-8", newline="\n")
    print(f"Wrote {len(result.files)} files to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
