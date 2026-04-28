"""Tests for AutoModeEvaluator (Phase 1.2)."""

from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.managers.auto_mode_evaluator import (
    AutoDecision,
    AutoModeEvaluator,
)


def _make_evaluator(**overrides) -> AutoModeEvaluator:
    """Build an evaluator with stub managers; overrides set attribute values on stubs."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()

    # Sensible defaults — every test overrides what it cares about.
    environment.cur_temp = 20.0
    environment.cur_humidity = 50.0
    environment.cur_floor_temp = None
    environment.target_temp = 21.0
    environment.target_temp_low = None
    environment.target_temp_high = None
    environment.target_humidity = 50.0
    environment._cold_tolerance = 0.5
    environment._hot_tolerance = 0.5
    environment._moist_tolerance = 5.0
    environment._dry_tolerance = 5.0
    environment._fan_hot_tolerance = 0.0
    environment.is_floor_hot = False
    environment.is_too_cold.return_value = False
    environment.is_too_hot.return_value = False
    environment.is_too_moist = False
    environment.is_within_fan_tolerance.return_value = False

    openings.any_opening_open.return_value = False

    features.is_configured_for_dryer_mode = False
    features.is_configured_for_fan_mode = False
    features.is_range_mode = False

    for key, value in overrides.items():
        if "." in key:
            obj_name, attr = key.split(".", 1)
            setattr(locals()[obj_name], attr, value)
        else:
            raise AssertionError(f"Override key must be 'object.attr', got {key!r}")

    return AutoModeEvaluator(environment, openings, features)


def test_evaluator_constructs_with_managers() -> None:
    """AutoModeEvaluator is importable and constructible."""
    ev = _make_evaluator()
    assert ev is not None


def test_auto_decision_is_frozen_dataclass() -> None:
    """AutoDecision exposes next_mode and reason and is hashable/frozen."""
    decision = AutoDecision(
        next_mode=HVACMode.HEAT, reason=HVACActionReason.TARGET_TEMP_NOT_REACHED
    )
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.TARGET_TEMP_NOT_REACHED
    # frozen → cannot reassign
    try:
        decision.next_mode = HVACMode.COOL
    except Exception as exc:  # FrozenInstanceError
        assert "frozen" in str(exc).lower() or "cannot" in str(exc).lower()
    else:
        raise AssertionError("AutoDecision should be frozen")
