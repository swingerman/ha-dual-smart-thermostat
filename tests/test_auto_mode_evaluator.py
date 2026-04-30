"""Tests for AutoModeEvaluator (Phase 1.2)."""

from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode
import pytest

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
    environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
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
    features.is_configured_for_heater_mode = True
    features.is_configured_for_heat_pump_mode = False
    features.is_configured_for_cooler_mode = False
    features.is_configured_for_dual_mode = False
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
    with pytest.raises(FrozenInstanceError):
        decision.next_mode = HVACMode.COOL


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
    ev._features.is_configured_for_cooler_mode = True
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
    ev._features.is_configured_for_cooler_mode = True
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
    ev._features.is_configured_for_cooler_mode = True
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
    ev._features.is_configured_for_cooler_mode = True
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


def test_flap_prevention_cool_stays_until_cool_goal_reached() -> None:
    """In COOL, still hot (goal pending) and no urgent → stay COOL."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 21.5  # 1x above — goal still pending
    last = AutoDecision(
        next_mode=HVACMode.COOL, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.COOL


def test_flap_prevention_fan_only_stays_until_fan_band_exited() -> None:
    """In FAN_ONLY, comfort band still satisfied → stay FAN_ONLY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.is_within_fan_tolerance.return_value = True
    last = AutoDecision(
        next_mode=HVACMode.FAN_ONLY, reason=HVACActionReason.AUTO_PRIORITY_COMFORT
    )
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.FAN_ONLY


def test_flap_prevention_unknown_mode_falls_through_to_full_scan() -> None:
    """A last_decision with a mode outside HEAT/COOL/DRY/FAN_ONLY → rescan."""
    ev = _make_evaluator()
    last = AutoDecision(
        next_mode=HVACMode.OFF, reason=HVACActionReason.TARGET_TEMP_REACHED
    )
    decision = ev.evaluate(last_decision=last)
    # All defaults satisfied → idle.
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_no_cooler_capability_skips_cool_priorities() -> None:
    """When can_cool is False, urgent + normal hot temp priorities don't fire."""
    ev = _make_evaluator()
    ev._features.is_configured_for_heat_pump_mode = False
    ev._features.is_configured_for_cooler_mode = False
    ev._features.is_configured_for_dual_mode = False
    ev._environment.cur_temp = (
        22.0  # 1x hot tolerance over target — would normally COOL
    )
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.COOL


def test_no_cooler_with_urgent_hot_does_not_pick_cool() -> None:
    """can_cool=False also blocks the urgent COOL priority."""
    ev = _make_evaluator()
    ev._features.is_configured_for_heat_pump_mode = False
    ev._features.is_configured_for_cooler_mode = False
    ev._features.is_configured_for_dual_mode = False
    ev._environment.cur_temp = 23.0  # 2x hot tolerance — urgent
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.COOL


def test_no_heater_capability_skips_heat_priorities() -> None:
    """When can_heat is False, HEAT priorities don't fire."""
    ev = _make_evaluator()
    ev._features.is_configured_for_heater_mode = False
    ev._features.is_configured_for_heat_pump_mode = False
    ev._environment.cur_temp = 19.0  # 2x cold — would normally HEAT
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.HEAT


def test_evaluator_accepts_outside_delta_boost_threshold() -> None:
    """Evaluator stores the outside-delta-boost threshold (in °C) at construction."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()
    ev = AutoModeEvaluator(environment, openings, features, outside_delta_boost_c=8.0)
    assert ev._outside_delta_boost_c == 8.0


def test_evaluator_default_outside_delta_boost_is_none() -> None:
    """When no threshold is provided, the evaluator stores None and disables bias."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()
    ev = AutoModeEvaluator(environment, openings, features)
    assert ev._outside_delta_boost_c is None


def test_evaluate_accepts_outside_temp_and_stall_flag() -> None:
    """evaluate() accepts outside_temp and outside_sensor_stalled kwargs without error."""
    ev = _make_evaluator()
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=5.0,
        outside_sensor_stalled=False,
    )
    # With all defaults (cur_temp == target_temp), nothing fires → idle.
    assert decision.next_mode is None


def test_evaluate_outside_temp_defaults_to_none() -> None:
    """evaluate() defaults outside_temp/outside_sensor_stalled when not supplied."""
    ev = _make_evaluator()
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
