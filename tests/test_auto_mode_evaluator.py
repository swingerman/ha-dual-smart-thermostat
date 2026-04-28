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
    # cur_temp == target_temp so neither cold nor hot priorities trigger by default.
    environment.cur_temp = 21.0
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


def test_temp_urgent_cold_2x_returns_heat() -> None:
    """Priority 4: temp at 2x cold tolerance triggers HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.0  # target 21, cold_tol 0.5, 2x = 1.0 below
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_temp_urgent_hot_2x_returns_cool() -> None:
    """Priority 5: temp at 2x hot tolerance triggers COOL."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 22.0  # target 21, hot_tol 0.5, 2x = 1.0 above
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_temp_normal_cold_returns_heat() -> None:
    """Priority 7: temp at 1x cold tolerance triggers HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.5  # target 21, cold_tol 0.5, 1x below
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT


def test_temp_normal_hot_returns_cool() -> None:
    """Priority 8: temp at 1x hot tolerance triggers COOL."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 21.5  # target 21, hot_tol 0.5, 1x above
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_humidity_urgent_preempts_temp_normal() -> None:
    """Urgent humidity (priority 3) wins over normal temp (priority 7)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0  # urgent
    ev._environment.cur_temp = 20.5  # normal cold
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY


def test_temp_urgent_preempts_humidity_normal() -> None:
    """Urgent temp (priority 4) wins over normal humidity (priority 6)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # normal moist
    ev._environment.cur_temp = 20.0  # urgent cold
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT


def test_fan_band_returns_fan_only() -> None:
    """Priority 9: temp in fan band → FAN_ONLY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.FAN_ONLY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_COMFORT


def test_fan_skipped_when_no_fan_configured() -> None:
    """No fan configured → priority 9 silent."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = False
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.FAN_ONLY


def test_temp_normal_hot_preempts_fan_band() -> None:
    """Priority 8 (normal hot) beats priority 9 (fan band)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 21.5  # 1x hot tolerance
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_idle_when_all_targets_met() -> None:
    """Priority 10: nothing fires → idle-keep with TARGET_TEMP_REACHED."""
    ev = _make_evaluator()  # all defaults: nothing fires
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_idle_after_dry_uses_humidity_reached_reason() -> None:
    """Priority 10 idle after DRY → reason TARGET_HUMIDITY_REACHED."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    last = AutoDecision(
        next_mode=HVACMode.DRY, reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_HUMIDITY_REACHED


def test_range_mode_uses_target_temp_low_for_heat() -> None:
    """Range mode: HEAT priority uses target_temp_low."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.target_temp = 21.0  # ignored in range mode
    ev._environment.cur_temp = 18.4  # below low - 1x cold_tol (0.5) = below 18.5
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT


def test_range_mode_uses_target_temp_high_for_cool() -> None:
    """Range mode: COOL priority uses target_temp_high."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.target_temp = 21.0  # ignored in range mode
    ev._environment.cur_temp = 24.6  # above high + 1x hot_tol (0.5) = above 24.5
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_range_mode_idle_between_targets() -> None:
    """Range mode: temp between low and high → idle."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.cur_temp = 21.5  # comfortably between
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_flap_prevention_stays_heat_while_goal_pending() -> None:
    """In HEAT, still cold (goal pending) and no urgent → stay HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.5  # 1x below — goal still pending
    last = AutoDecision(
        next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.HEAT


def test_flap_prevention_switches_to_dry_on_urgent_humidity() -> None:
    """In HEAT, urgent humidity emerges → switch to DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_temp = 20.5  # still cold (goal pending)
    ev._environment.cur_humidity = 60.0  # urgent humidity
    last = AutoDecision(
        next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.DRY


def test_flap_prevention_normal_humidity_does_not_preempt_heat() -> None:
    """Normal-tier humidity does NOT preempt active HEAT."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_temp = 20.5  # 1x below (goal pending)
    ev._environment.cur_humidity = 55.0  # normal moist
    last = AutoDecision(
        next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.HEAT


def test_flap_prevention_rescans_when_goal_reached() -> None:
    """In HEAT, temp recovered → full top-down scan picks fresh."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 21.0  # at target — goal reached
    last = AutoDecision(
        next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode is None  # idle
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_flap_prevention_dry_stays_until_dry_goal_reached() -> None:
    """In DRY, humidity still high (goal pending) → stay DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # still 1x — goal pending
    last = AutoDecision(
        next_mode=HVACMode.DRY, reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.DRY
