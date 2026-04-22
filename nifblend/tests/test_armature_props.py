"""Unit tests for :mod:`nifblend.bridge.armature_props` (Phase 4 step 14)."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from nifblend.bridge.armature_props import (
    PROP_ATTR,
    apply_bind_matrix_to_props,
    read_bind_matrix_from_props,
)


def test_apply_then_read_roundtrips_full_matrix() -> None:
    bone = SimpleNamespace()
    m = np.arange(16, dtype=np.float32).reshape(4, 4)
    apply_bind_matrix_to_props(bone, m)

    props = getattr(bone, PROP_ATTR)
    assert props.has_bind_matrix is True
    assert len(props.bind_matrix) == 16

    out = read_bind_matrix_from_props(bone)
    assert out is not None
    np.testing.assert_array_equal(out, m)


def test_read_returns_none_when_unset() -> None:
    bone = SimpleNamespace(nifblend=SimpleNamespace(has_bind_matrix=False))
    assert read_bind_matrix_from_props(bone) is None


def test_read_returns_none_when_no_propertygroup() -> None:
    bone = SimpleNamespace()
    assert read_bind_matrix_from_props(bone) is None


def test_apply_accepts_flat_iterable() -> None:
    bone = SimpleNamespace()
    flat = [float(x) for x in range(16)]
    apply_bind_matrix_to_props(bone, flat)
    out = read_bind_matrix_from_props(bone)
    assert out is not None
    np.testing.assert_array_equal(out, np.array(flat, dtype=np.float32).reshape(4, 4))


def test_apply_rejects_wrong_shape() -> None:
    bone = SimpleNamespace()
    try:
        apply_bind_matrix_to_props(bone, np.zeros(9, dtype=np.float32))
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-4x4 input")
