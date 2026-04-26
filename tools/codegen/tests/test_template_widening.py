"""Phase 10b — codegen `#T#` template widening.

These tests exercise the emitter's template-stack handling: the resolved
type for `#T#`-typed fields (`Key.value`, `Key.forward`, `Key.backward`,
`QuatKey.value`) is dispatched on `ctx.template`, and concrete `template=`
attributes on caller fields push/pop the stack. Without this, every
keyed-animation read/write on `KeyGroup` / `Key` / `QuatKey` would fall
through to a `# CODEGEN-TODO` marker (the pre-Phase 10b state).
"""

from __future__ import annotations

import io

import pytest

from nifblend.format.base import ReadContext
from nifblend.format.generated.structs import (
    Key,
    KeyGroup,
    Quaternion,
    QuatKey,
    Vector3,
)
from nifblend.format.versions import pack_version


def _ctx() -> ReadContext:
    """ReadContext for SSE (20.2.0.7, user 12, bs 100)."""
    return ReadContext(version=pack_version(20, 2, 0, 7), user_version=12, bs_version=100)


# ---- template stack ------------------------------------------------------


def test_read_context_template_stack_empty_default() -> None:
    ctx = _ctx()
    assert ctx.template == ""


def test_read_context_template_stack_push_pop() -> None:
    ctx = _ctx()
    ctx.push_template("Vector3")
    assert ctx.template == "Vector3"
    ctx.push_template("float")
    assert ctx.template == "float"
    ctx.pop_template()
    assert ctx.template == "Vector3"
    ctx.pop_template()
    assert ctx.template == ""


# ---- Key value dispatch (per-template round-trip) ------------------------


def test_key_value_round_trip_float_template() -> None:
    """Key.value with template='float' reads/writes a single f32."""
    ctx = _ctx()
    ctx.push_template("float")
    src = Key(time=0.5, value=3.25)
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = Key.read(sink, ctx)
    assert rt.time == pytest.approx(0.5)
    assert rt.value == pytest.approx(3.25)


def test_key_value_round_trip_byte_template() -> None:
    ctx = _ctx()
    ctx.push_template("byte")
    src = Key(time=1.0, value=200)
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = Key.read(sink, ctx)
    assert rt.value == 200


def test_key_value_round_trip_vector3_template() -> None:
    ctx = _ctx()
    ctx.push_template("Vector3")
    src = Key(time=2.0, value=Vector3(x=1.0, y=2.0, z=3.0))
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = Key.read(sink, ctx)
    assert rt.time == pytest.approx(2.0)
    assert rt.value.x == pytest.approx(1.0)
    assert rt.value.y == pytest.approx(2.0)
    assert rt.value.z == pytest.approx(3.0)


def test_key_value_unsupported_template_raises() -> None:
    ctx = _ctx()
    ctx.push_template("Frobnicator")
    src = Key(time=0.0, value=0.0)
    with pytest.raises(NotImplementedError, match="Frobnicator"):
        src.write(io.BytesIO(), ctx)


# ---- KeyGroup propagates template to inner Keys --------------------------


def test_keygroup_translation_round_trip() -> None:
    """A KeyGroup of Vector3 (translation channel)."""
    ctx = _ctx()
    ctx.push_template("Vector3")
    keys = [
        Key(time=0.0, value=Vector3(x=0.0, y=0.0, z=0.0)),
        Key(time=1.0, value=Vector3(x=1.0, y=2.0, z=3.0)),
        Key(time=2.0, value=Vector3(x=4.0, y=5.0, z=6.0)),
    ]
    src = KeyGroup(num_keys=3, interpolation=1, keys=keys)
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = KeyGroup.read(sink, ctx)
    assert rt.num_keys == 3
    assert rt.interpolation == 1
    assert len(rt.keys) == 3
    for orig, decoded in zip(keys, rt.keys, strict=True):
        assert decoded.time == pytest.approx(orig.time)
        assert decoded.value.x == pytest.approx(orig.value.x)
        assert decoded.value.y == pytest.approx(orig.value.y)
        assert decoded.value.z == pytest.approx(orig.value.z)


def test_keygroup_scale_round_trip_float_template() -> None:
    ctx = _ctx()
    ctx.push_template("float")
    keys = [Key(time=t, value=v) for t, v in [(0.0, 1.0), (1.5, 0.5), (2.0, 1.5)]]
    src = KeyGroup(num_keys=3, interpolation=1, keys=keys)
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = KeyGroup.read(sink, ctx)
    assert [k.time for k in rt.keys] == pytest.approx([0.0, 1.5, 2.0])
    assert [k.value for k in rt.keys] == pytest.approx([1.0, 0.5, 1.5])


# ---- QuatKey ------------------------------------------------------------


def test_quatkey_quaternion_round_trip() -> None:
    """QuatKey with template='Quaternion' reads/writes time + w/x/y/z."""
    ctx = _ctx()
    ctx.push_template("Quaternion")
    ctx.push_arg(1)  # LINEAR_KEY interpolation (no tangents, no TBC)
    src = QuatKey(time=0.5, value=Quaternion(w=1.0, x=0.0, y=0.0, z=0.0))
    sink = io.BytesIO()
    src.write(sink, ctx)
    sink.seek(0)
    rt = QuatKey.read(sink, ctx)
    assert rt.time == pytest.approx(0.5)
    assert rt.value.w == pytest.approx(1.0)
    assert rt.value.x == pytest.approx(0.0)
    assert rt.value.y == pytest.approx(0.0)
    assert rt.value.z == pytest.approx(0.0)


def test_quatkey_arg_4_skips_value_and_time() -> None:
    """KeyType=4 (XYZ_ROTATION_KEY) on QuatKey: schema gates value/time
    on `arg != 4`. Verify the read/write skips the value field entirely.
    """
    ctx = _ctx()
    ctx.push_template("Quaternion")
    ctx.push_arg(4)
    src = QuatKey()  # all defaults
    sink = io.BytesIO()
    src.write(sink, ctx)
    # arg=4 means: time skipped (since>=10.1.0.106 gate is `arg != 4`),
    # and value skipped. Only the legacy `time` (until 10.1.0.0) gate
    # would fire on older versions; SSE skips that too.
    assert sink.getvalue() == b""
