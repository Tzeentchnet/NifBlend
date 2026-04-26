"""Unit tests for :mod:`nifblend.bridge.animation_props` (Phase 10 step 10c)."""

from __future__ import annotations

from types import SimpleNamespace

from nifblend.bridge.animation_props import (
    CYCLE_TYPE_ITEMS,
    PROP_ATTR,
    apply_controlled_block_to_pose_bone,
    apply_sequence_metadata_to_action,
    apply_text_keys_to_action,
    clear_controlled_block_on_pose_bone,
    clear_sequence_metadata_on_action,
    read_controlled_block_from_pose_bone,
    read_sequence_metadata_from_action,
    read_text_keys_from_action,
)
from nifblend.format.generated.enums import CycleType

# ---- enum items ----------------------------------------------------------


def test_cycle_type_items_cover_every_enum_member() -> None:
    by_name = {label: int(key) for key, label, _desc in CYCLE_TYPE_ITEMS}
    assert by_name == {m.name: int(m) for m in CycleType}


# ---- sequence metadata ---------------------------------------------------


def test_apply_then_read_round_trips_sequence_metadata() -> None:
    action = SimpleNamespace(name="walk")
    apply_sequence_metadata_to_action(
        action,
        weight=0.75,
        frequency=2.0,
        start_time=0.5,
        stop_time=4.5,
        cycle_type=int(CycleType.CYCLE_LOOP),
        accum_root_name="NPC Root [Root]",
        accum_flags=0xDEADBEEF,
        phase=0.125,
        play_backwards=True,
    )

    read = read_sequence_metadata_from_action(action)
    assert read == {
        "weight": 0.75,
        "frequency": 2.0,
        "start_time": 0.5,
        "stop_time": 4.5,
        "cycle_type": int(CycleType.CYCLE_LOOP),
        "accum_root_name": "NPC Root [Root]",
        "accum_flags": 0xDEADBEEF,
        "phase": 0.125,
        "play_backwards": True,
    }


def test_apply_uses_phase_10_defaults() -> None:
    action = SimpleNamespace(name="idle")
    apply_sequence_metadata_to_action(action)
    read = read_sequence_metadata_from_action(action)
    assert read is not None
    assert read["weight"] == 1.0
    assert read["frequency"] == 1.0
    assert read["cycle_type"] == int(CycleType.CYCLE_CLAMP)
    assert read["accum_root_name"] == ""
    assert read["accum_flags"] == 0
    assert read["play_backwards"] is False


def test_read_returns_none_when_no_propertygroup() -> None:
    assert read_sequence_metadata_from_action(SimpleNamespace(name="x")) is None


def test_clear_resets_sequence_metadata_to_defaults() -> None:
    action = SimpleNamespace(name="x")
    apply_sequence_metadata_to_action(
        action,
        weight=0.1,
        accum_root_name="root",
        play_backwards=True,
    )
    apply_text_keys_to_action(action, [(0.0, "start"), (1.0, "end")])

    clear_sequence_metadata_on_action(action)

    read = read_sequence_metadata_from_action(action)
    assert read is not None
    assert read["weight"] == 1.0
    assert read["accum_root_name"] == ""
    assert read["play_backwards"] is False
    assert read_text_keys_from_action(action) == []


def test_apply_clamps_accum_flags_to_u32() -> None:
    action = SimpleNamespace(name="x")
    apply_sequence_metadata_to_action(action, accum_flags=0x1_0000_0042)
    read = read_sequence_metadata_from_action(action)
    assert read is not None
    assert read["accum_flags"] == 0x42


def test_apply_preserves_unknown_cycle_type() -> None:
    action = SimpleNamespace(name="x")
    # Future / modder cycle types must survive verbatim rather than
    # being clamped to a known enum value.
    apply_sequence_metadata_to_action(action, cycle_type=99)
    read = read_sequence_metadata_from_action(action)
    assert read is not None
    assert read["cycle_type"] == 99


# ---- text keys -----------------------------------------------------------


def test_apply_then_read_round_trips_text_keys() -> None:
    action = SimpleNamespace(name="walk")
    keys = [(0.0, "start"), (0.4, "footLeft"), (0.8, "end")]
    apply_text_keys_to_action(action, keys)
    assert read_text_keys_from_action(action) == keys


def test_apply_text_keys_replaces_existing() -> None:
    action = SimpleNamespace(name="walk")
    apply_text_keys_to_action(action, [(0.0, "a"), (1.0, "b")])
    apply_text_keys_to_action(action, [(0.5, "c")])
    assert read_text_keys_from_action(action) == [(0.5, "c")]


def test_read_text_keys_returns_empty_when_no_propertygroup() -> None:
    assert read_text_keys_from_action(SimpleNamespace(name="x")) == []


# ---- pose bone / ControlledBlock ----------------------------------------


def test_apply_then_read_round_trips_controlled_block() -> None:
    pb = SimpleNamespace(name="Bip01 Spine")
    apply_controlled_block_to_pose_bone(
        pb,
        priority=42,
        controller_type="NiTransformController",
        controller_id="ctl",
        interpolator_id="interp",
        property_type="prop",
    )

    read = read_controlled_block_from_pose_bone(pb)
    assert read == {
        "priority": 42,
        "controller_type": "NiTransformController",
        "controller_id": "ctl",
        "interpolator_id": "interp",
        "property_type": "prop",
    }


def test_apply_clamps_priority_to_u8() -> None:
    pb = SimpleNamespace(name="x")
    apply_controlled_block_to_pose_bone(pb, priority=0x1_FF)
    read = read_controlled_block_from_pose_bone(pb)
    assert read is not None
    assert read["priority"] == 0xFF


def test_read_pose_bone_returns_none_when_no_propertygroup() -> None:
    assert read_controlled_block_from_pose_bone(SimpleNamespace(name="x")) is None


def test_clear_resets_pose_bone_metadata() -> None:
    pb = SimpleNamespace(name="x")
    apply_controlled_block_to_pose_bone(
        pb,
        priority=10,
        controller_type="t",
        controller_id="c",
        interpolator_id="i",
        property_type="p",
    )
    clear_controlled_block_on_pose_bone(pb)
    read = read_controlled_block_from_pose_bone(pb)
    assert read == {
        "priority": 0,
        "controller_type": "",
        "controller_id": "",
        "interpolator_id": "",
        "property_type": "",
    }


def test_apply_pose_bone_no_writable_attrs_short_circuits() -> None:
    """Helper must no-op against an object that refuses attribute writes."""

    class _Frozen:
        __slots__ = ()

    pb = _Frozen()
    apply_controlled_block_to_pose_bone(pb, priority=1, controller_type="t")
    # Nothing got attached, but the call did not raise.
    assert getattr(pb, PROP_ATTR, None) is None
    assert read_controlled_block_from_pose_bone(pb) is None


def test_apply_action_no_writable_attrs_short_circuits() -> None:
    class _Frozen:
        __slots__ = ()

    action = _Frozen()
    apply_sequence_metadata_to_action(action, weight=2.0)
    apply_text_keys_to_action(action, [(0.0, "start")])
    assert getattr(action, PROP_ATTR, None) is None
    assert read_sequence_metadata_from_action(action) is None
    assert read_text_keys_from_action(action) == []
