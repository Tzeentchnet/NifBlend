#!/usr/bin/env python3
"""Build the NifBlend Blender extension zip into ``dist/``.

Blender's ``extension build`` CLI requires ``blender_manifest.toml`` to sit
directly alongside ``__init__.py`` in the directory it builds from. In this
repo the manifest lives at the repo root while the installable package lives
in ``nifblend/``, so this script stages a temporary directory containing the
package contents (minus its own ``tests/``) plus ``LICENSE``, ``README.md``,
and ``blender_manifest.toml`` before invoking Blender's official builder.

Usage:
    python scripts/build_extension.py [--blender PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "nifblend"
MANIFEST_PATH = REPO_ROOT / "blender_manifest.toml"
ROOT_FILES = ("LICENSE", "README.md")


def _find_blender() -> str:
    """Locate a Blender executable, preferring the newest installed version."""
    found = shutil.which("blender")
    if found:
        return found
    candidates = sorted(
        Path("C:/Program Files/Blender Foundation").glob("Blender */blender.exe"),
        reverse=True,
    )
    if candidates:
        return str(candidates[0])
    raise SystemExit(
        "Could not locate a blender executable on PATH or in "
        "'C:/Program Files/Blender Foundation'. Pass --blender <path> explicitly."
    )


def _stage(staging_dir: Path) -> None:
    shutil.copytree(
        PACKAGE_DIR,
        staging_dir,
        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
    )
    for name in ROOT_FILES:
        shutil.copy2(REPO_ROOT / name, staging_dir / name)
    shutil.copy2(MANIFEST_PATH, staging_dir / MANIFEST_PATH.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", default=None, help="Path to the blender executable")
    parser.add_argument(
        "--output",
        default=None,
        help="Output zip filepath (default: dist/<id>-<version>-blender.zip)",
    )
    args = parser.parse_args()

    manifest = tomllib.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ext_id = manifest["id"]
    version = manifest["version"]

    blender = args.blender or _find_blender()
    dist_dir = REPO_ROOT / "dist"
    dist_dir.mkdir(exist_ok=True)
    output = Path(args.output) if args.output else dist_dir / f"{ext_id}-{version}-blender.zip"

    with tempfile.TemporaryDirectory(prefix="nifblend_build_") as tmp:
        staging_dir = Path(tmp) / ext_id
        _stage(staging_dir)
        cmd = [
            blender,
            "--command",
            "extension",
            "build",
            "--source-dir",
            str(staging_dir),
            "--output-filepath",
            str(output),
            "--verbose",
        ]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            return result.returncode

    print(f"Built {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
