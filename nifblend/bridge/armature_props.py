"""Phase 4 step 14: typed ``PropertyGroup`` on ``bpy.types.Bone``.

Stores the full 4x4 NIF bind matrix verbatim so a NifBlend armature can
round-trip through *import → edit → export* without being clipped to
Blender's (head, tail, roll) representation. Bone roll alone is lossy
because it discards the off-axis rotation introduced by per-node scale,
non-uniform parent transforms, and any NIF rotation that doesn't align
the bone's local Y with the parent → child vector.

The local matrix is the bone's transform *relative to its parent*
(translation + Matrix33 x scale, lifted to homogeneous 4x4) — exactly
the data carried on the source ``NiNode``. World-space matrices are
re-derivable from a tree walk and therefore not stored here.

The module exposes two layers, mirroring
:mod:`nifblend.bridge.material_props`:

* :class:`NifBlendBoneProperties` — the registered ``PropertyGroup``.
* :func:`apply_bind_matrix_to_props` /
  :func:`read_bind_matrix_from_props` — duck-typed helpers used by
  :mod:`nifblend.bridge.armature_in` (and, later, ``armature_out``).
  They work against either a real ``PointerProperty``-backed
  PropertyGroup or any attribute-bearing fake (the test suite uses
  ``SimpleNamespace``).
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from typing import Any

import bpy
import numpy as np
import numpy.typing as npt

__all__ = [
    "PROP_ATTR",
    "NifBlendBoneProperties",
    "apply_bind_matrix_to_props",
    "read_bind_matrix_from_props",
    "register",
    "unregister",
]


#: Attribute name on ``bpy.types.Bone`` that carries the PropertyGroup.
PROP_ATTR = "nifblend"


class NifBlendBoneProperties(bpy.types.PropertyGroup):
    """NIF-only bone state attached to ``bpy.types.Bone.nifblend``.

    ``bind_matrix`` is the 4x4 local bind transform from the source
    ``NiNode``, flattened in row-major order so it survives Blender's
    ``FloatVectorProperty`` storage. ``has_bind_matrix`` distinguishes
    "never imported" (default identity) from "imported as identity".
    """

    has_bind_matrix: bpy.props.BoolProperty(  # type: ignore[valid-type]
        name="Has Bind Matrix",
        description="True when bind_matrix was populated from a NIF import",
        default=False,
    )
    bind_matrix: bpy.props.FloatVectorProperty(  # type: ignore[valid-type]
        name="Bind Matrix",
        description=(
            "Full 4x4 local bind transform from the source NiNode "
            "(row-major). Preserves rotation+scale beyond Blender's "
            "(head, tail, roll) representation."
        ),
        size=16,
        default=(
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            0.0, 0.0, 0.0, 1.0,
        ),
    )


_REGISTERED_CLASSES: tuple[type, ...] = (NifBlendBoneProperties,)


# ---- duck-typed helpers --------------------------------------------------


def apply_bind_matrix_to_props(bone: Any, matrix: npt.ArrayLike) -> None:
    """Stamp ``matrix`` onto ``bone.nifblend.bind_matrix`` (row-major flat).

    No-op when neither the real PropertyGroup nor a writable fallback
    attribute is reachable on ``bone``.
    """
    props = _get_or_create_props(bone)
    if props is None:
        return
    flat = tuple(float(x) for x in np.asarray(matrix, dtype=np.float32).reshape(-1))
    if len(flat) != 16:
        raise ValueError(f"bind matrix must be 4x4 (got {len(flat)} floats)")
    _set_attr(props, "bind_matrix", flat)
    _set_attr(props, "has_bind_matrix", True)


def read_bind_matrix_from_props(bone: Any) -> npt.NDArray[np.float32] | None:
    """Return the stored bind matrix as a (4, 4) array, or ``None``."""
    props = getattr(bone, PROP_ATTR, None)
    if props is None:
        return None
    if not getattr(props, "has_bind_matrix", False):
        return None
    flat = getattr(props, "bind_matrix", None)
    if flat is None:
        return None
    arr = np.asarray(list(flat), dtype=np.float32)
    if arr.size != 16:
        return None
    return arr.reshape(4, 4)


# ---- registration --------------------------------------------------------


def register() -> None:
    """Register the PropertyGroup and attach the PointerProperty."""
    for cls in _REGISTERED_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Bone.nifblend = bpy.props.PointerProperty(
        type=NifBlendBoneProperties,
        name="NifBlend",
        description="NIF-only bone state preserved across import/export",
    )


def unregister() -> None:
    """Inverse of :func:`register`. Tolerant of partial registration."""
    if hasattr(bpy.types.Bone, "nifblend"):
        with contextlib.suppress(AttributeError, TypeError):
            del bpy.types.Bone.nifblend
    for cls in reversed(_REGISTERED_CLASSES):
        with contextlib.suppress(RuntimeError, ValueError):
            bpy.utils.unregister_class(cls)


# ---- private -------------------------------------------------------------


def _get_or_create_props(bone: Any) -> Any:
    props = getattr(bone, PROP_ATTR, None)
    if props is not None:
        return props
    try:
        ns = SimpleNamespace()
        setattr(bone, PROP_ATTR, ns)
    except (AttributeError, TypeError):
        return None
    return ns


def _set_attr(props: Any, name: str, value: Any) -> None:
    with contextlib.suppress(AttributeError, TypeError):
        setattr(props, name, value)
