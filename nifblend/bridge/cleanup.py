"""Phase 8c: pure helpers backing the cleanup operators.

Blender-free / unit-testable. The matching :mod:`nifblend.ops.cleanup`
module wraps each helper in a thin Operator that exposes a
``'SELECTED' | 'SCENE'`` scope toggle and other safer-than-NifCity
defaults.
"""

from __future__ import annotations

import re
from collections.abc import (
    Iterable,
    Sequence,
)

__all__ = [
    "DEFAULT_COLLISION_PATTERNS",
    "matches_collision_pattern",
    "material_base_name",
    "parse_pattern_list",
    "strip_blender_dup_suffix",
]


#: Default collision-shell name patterns matched by
#: :func:`matches_collision_pattern`. ``armature`` is intentionally NOT
#: included here -- the NifCity addon bundled it in unconditionally,
#: which silently nukes skinned imports. The matching operator exposes
#: ``also_delete_armatures`` as a separate toggle.
DEFAULT_COLLISION_PATTERNS: tuple[str, ...] = ("box", "convex", "hull")


_BLENDER_DUP_SUFFIX_RE = re.compile(r"\.\d{3,}$")


def material_base_name(name: str) -> str:
    """Strip Blender's ``.001`` / ``.045`` / ``.123`` duplicate suffix.

    Blender appends a 3+ digit numeric suffix when a name collides with
    an existing data-block of the same type. NIF round-trips frequently
    produce ``Stone`` / ``Stone.001`` / ``Stone.002`` from one source
    material; reducing them all to ``Stone`` lets
    :mod:`nifblend.ops.cleanup` group them for ``join``.
    """
    return _BLENDER_DUP_SUFFIX_RE.sub("", str(name))


# Compatibility alias: the Blender-side strip helper also matches the
# trailing ``.NNN`` suffix on any datablock name.
strip_blender_dup_suffix = material_base_name


def matches_collision_pattern(
    name: str,
    patterns: Sequence[str] = DEFAULT_COLLISION_PATTERNS,
) -> bool:
    """True when ``name`` is a collision-shell-shaped object name.

    Two match flavours:

    * **Prefix-with-numeric-suffix-or-empty-tail**: ``box``, ``box.001``,
      ``Box.45``, ``box1`` all match the ``box`` pattern. ``boxer``
      and ``boxhead`` do NOT (no boundary).
    * **Substring**: ``convex_hull``, ``my_convex_42``, ``Hull.001`` match
      the ``convex`` / ``hull`` patterns.

    Match is case-insensitive.
    """
    lowered = name.lower()
    for pat in patterns:
        p = pat.strip().lower()
        if not p:
            continue
        if lowered == p:
            return True
        # "box" + digit / "box" + ".NNN" / "box" + "_*"
        if lowered.startswith(p):
            tail = lowered[len(p):]
            if tail == "" or tail[0] in "._-" or tail[0].isdigit():
                return True
        # Substring matches for convex / hull style names.
        if p in lowered and p in ("convex", "hull"):
            return True
    return False


def parse_pattern_list(text: str) -> tuple[str, ...]:
    """Parse a comma-separated pattern list, dropping blanks and trimming whitespace.

    ``"box, convex,, hull,"`` → ``("box", "convex", "hull")``.
    ``""`` / ``None`` → ``()``.
    """
    if not text:
        return ()
    out = []
    seen: set[str] = set()
    for raw in str(text).split(","):
        s = raw.strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return tuple(out)


def group_objects_by_material_base(
    objects: Iterable,
) -> dict[str, list]:
    """Bucket mesh-shaped objects by the base name of their first material.

    ``obj`` is duck-typed: must have ``.type == 'MESH'`` (string compare),
    ``.data.materials`` (sequence-of-Material-shaped). Objects with no
    materials are skipped. Returns a ``{base_name: [objs...]}`` dict.
    """
    out: dict[str, list] = {}
    for obj in objects:
        if getattr(obj, "type", None) != "MESH":
            continue
        data = getattr(obj, "data", None)
        mats = getattr(data, "materials", None)
        if not mats:
            continue
        first = mats[0]
        if first is None:
            continue
        base = material_base_name(getattr(first, "name", ""))
        if not base:
            continue
        out.setdefault(base, []).append(obj)
    return out
