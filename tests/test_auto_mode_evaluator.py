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


def test_floor_hot_returns_overheat() -> None:
    """Priority 1: floor temp at limit forces idle / OVERHEAT."""
    ev = _make_evaluator(**{"environment.is_floor_hot": True})
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.OVERHEAT


def test_opening_open_returns_opening_idle() -> None:
    """Priority 2: opening detected forces idle / OPENING."""
    ev = _make_evaluator()
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.OPENING


def test_temperature_stall_returns_temperature_stall() -> None:
    """Temperature sensor stall → idle / TEMPERATURE_SENSOR_STALLED."""
    ev = _make_evaluator()
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TEMPERATURE_SENSOR_STALLED


def test_floor_hot_preempts_opening_and_stall() -> None:
    """Safety priority 1 wins over priority 2 and over stall."""
    ev = _make_evaluator(**{"environment.is_floor_hot": True})
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.reason == HVACActionReason.OVERHEAT


def test_opening_preempts_stall() -> None:
    """Opening (safety 2) wins over a stall."""
    ev = _make_evaluator()
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.reason == HVACActionReason.OPENING


def test_humidity_urgent_2x_returns_dry() -> None:
    """Priority 3: humidity at 2x moist tolerance triggers DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0  # target 50, moist_tol 5 → 2x = 60
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_HUMIDITY


def test_humidity_normal_returns_dry() -> None:
    """Priority 6: humidity at 1x moist tolerance triggers DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # target 50, moist_tol 5 → 1x = 55
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY


def test_humidity_priority_skipped_when_no_dryer() -> None:
    """When dryer not configured, humidity priorities are silent."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = False
    ev._environment.cur_humidity = 65.0  # would otherwise be urgent
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason != HVACActionReason.AUTO_PRIORITY_HUMIDITY


def test_humidity_stall_suppresses_humidity_priorities() -> None:
    """A stalled humidity sensor → humidity priorities skipped."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0  # would be urgent
    decision = ev.evaluate(last_decision=None, humidity_sensor_stalled=True)
    assert decision.next_mode != HVACMode.DRY


def test_humidity_below_target_does_not_trigger() -> None:
    """Humidity below target does not pick DRY (Phase 1.2 doesn't humidify)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 30.0
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.DRY
