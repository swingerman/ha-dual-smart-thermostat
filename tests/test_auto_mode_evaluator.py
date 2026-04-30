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
    environment.effective_temp_for_mode = lambda mode: environment.cur_temp

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


def test_outside_promotion_threshold_disabled_when_none() -> None:
    """No threshold configured → never promote, regardless of outside delta."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = None
    ev._environment.cur_temp = 18.0  # 3°C cold
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=False
        )
        is False
    )


def test_outside_promotion_skipped_when_outside_temp_none() -> None:
    """No outside reading available → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=None, outside_sensor_stalled=False
        )
        is False
    )


def test_outside_promotion_skipped_when_outside_stalled() -> None:
    """Stalled outside sensor → no promotion even when delta is huge."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=True
        )
        is False
    )


def test_outside_promotion_skipped_when_cur_temp_none() -> None:
    """Inside reading missing → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = None
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=False
        )
        is False
    )


def test_outside_promotion_heat_fires_when_delta_meets_threshold_and_outside_colder() -> (
    None
):
    """HEAT promotes when outside is colder AND |delta| ≥ threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=10.0, outside_sensor_stalled=False
        )
        is True
    )  # delta = 8.0, exactly threshold


def test_outside_promotion_heat_skipped_when_delta_below_threshold() -> None:
    """HEAT does not promote when delta is below threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=11.0, outside_sensor_stalled=False
        )
        is False
    )  # delta = 7.0


def test_outside_promotion_heat_skipped_when_outside_warmer_than_inside() -> None:
    """HEAT direction guard: outside warmer than inside → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.HEAT, outside_temp=27.0, outside_sensor_stalled=False
        )
        is False
    )  # delta = 9.0 but outside is warmer


def test_outside_promotion_cool_fires_when_outside_hotter() -> None:
    """COOL promotes when outside is hotter AND |delta| ≥ threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 24.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.COOL, outside_temp=33.0, outside_sensor_stalled=False
        )
        is True
    )


def test_outside_promotion_cool_skipped_when_outside_cooler() -> None:
    """COOL direction guard: outside cooler than inside → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 24.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.COOL, outside_temp=10.0, outside_sensor_stalled=False
        )
        is False
    )


def test_outside_promotion_skipped_for_non_temp_modes() -> None:
    """Non-temp modes (DRY, FAN_ONLY) never promote."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.DRY, outside_temp=-10.0, outside_sensor_stalled=False
        )
        is False
    )
    assert (
        ev._outside_promotes_to_urgent(
            HVACMode.FAN_ONLY, outside_temp=-10.0, outside_sensor_stalled=False
        )
        is False
    )


def test_full_scan_promotes_normal_heat_to_urgent_with_outside_bias() -> None:
    """Normal-tier HEAT becomes urgent when outside-delta crosses the threshold.

    Critically, this proves the promotion fires through evaluate() — not just
    in the helper. Inside is 1× cold tolerance below target (normal HEAT
    territory) but outside delta is large.
    """
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5  # 1× below 21.0 target
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=10.0,  # delta = 10.5 ≥ 8 threshold
        outside_sensor_stalled=False,
    )
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_normal_heat_unaffected_when_outside_delta_below_threshold() -> None:
    """Normal HEAT stays normal-tier when outside delta is small."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=15.0,  # delta = 5.5 < 8
    )
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_promotes_normal_cool_to_urgent_with_outside_bias() -> None:
    """Normal-tier COOL becomes urgent when outside-delta is large and hot."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 21.5  # 1× above 21.0 target
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=32.0,  # delta = 10.5 ≥ 8
    )
    assert decision.next_mode == HVACMode.COOL
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_outside_bias_skipped_when_below_target() -> None:
    """Bias only applies to existing normal-tier triggers — does not invent priorities."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 21.0  # AT target — neither tier fires
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=-5.0,  # huge delta but no underlying trigger
    )
    assert decision.next_mode is None  # idle


def test_free_cooling_skipped_when_no_fan_configured() -> None:
    """No fan configured → free cooling never fires."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = False
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=15.0, outside_sensor_stalled=False)
        is False
    )


def test_free_cooling_skipped_when_outside_temp_none() -> None:
    """No outside reading → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=None, outside_sensor_stalled=False)
        is False
    )


def test_free_cooling_skipped_when_outside_stalled() -> None:
    """Stalled outside sensor → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=15.0, outside_sensor_stalled=True)
        is False
    )


def test_free_cooling_skipped_when_cur_temp_none() -> None:
    """No inside reading → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = None
    assert (
        ev._free_cooling_applies(outside_temp=15.0, outside_sensor_stalled=False)
        is False
    )


def test_free_cooling_fires_when_outside_more_than_margin_cooler() -> None:
    """Free cooling fires when outside ≤ inside − 2°C margin."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=22.0, outside_sensor_stalled=False)
        is True
    )  # exactly the 2°C margin


def test_free_cooling_skipped_when_outside_within_margin() -> None:
    """Free cooling does not fire when outside is within margin of inside."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=22.5, outside_sensor_stalled=False)
        is False
    )  # only 1.5°C cooler


def test_free_cooling_skipped_when_outside_warmer_than_inside() -> None:
    """Outside warmer than inside → free cooling never fires."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert (
        ev._free_cooling_applies(outside_temp=28.0, outside_sensor_stalled=False)
        is False
    )


def test_full_scan_picks_fan_for_free_cooling_in_normal_cool_tier() -> None:
    """Normal-tier COOL with outside cool enough → pick FAN_ONLY instead."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 21.5  # 1× above 21.0 target → normal-tier COOL
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=18.0,  # 3.5°C cooler — meets 2°C margin
        outside_sensor_stalled=False,
    )
    assert decision.next_mode == HVACMode.FAN_ONLY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_COMFORT


def test_full_scan_does_not_pick_fan_when_free_cooling_margin_not_met() -> None:
    """Normal-tier COOL with outside not cool enough → still pick COOL."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 21.5
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=20.5,  # only 1°C cooler — below 2°C margin
    )
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_skips_free_cooling_in_urgent_tier() -> None:
    """Urgent COOL stays COOL — fan would be too slow when room is hot."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 22.5  # 2× above target → urgent
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=18.0,  # cool, but irrelevant — urgent picks COOL
    )
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_skips_free_cooling_when_outside_promotes_to_urgent() -> None:
    """Outside-delta-promotion of normal COOL also suppresses free cooling.

    This proves the priority order: outside-delta promotion takes effect
    before free-cooling consideration.
    """
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._outside_delta_boost_c = 8.0
    # Normal-tier COOL (only 1× over) but outside is hot AND large delta.
    ev._environment.cur_temp = 21.5
    # outside hotter than inside by 10.5°C → promotes COOL to urgent → no fan.
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=32.0,
    )
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_picks_cool_when_apparent_above_target_even_if_raw_below() -> None:
    """When CONF_USE_APPARENT_TEMP is on, AUTO picks COOL using apparent temp.

    Setup: target=27, hot_tolerance=0.5, cur_temp=27.4 (raw → not too_hot),
    humidity=80% (apparent → ~30°C → too_hot). AUTO must pick COOL.
    """
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 27.4
    ev._environment.cur_humidity = 80.0
    ev._environment.target_temp = 27.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)

    # Stub the env's effective_temp_for_mode to return apparent only for COOL.
    def _eff(mode):
        if mode == HVACMode.COOL:
            return 30.0  # simulated apparent temp
        return 27.4

    ev._environment.effective_temp_for_mode = _eff
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_does_not_pick_cool_when_raw_below_target_and_no_apparent_substitution() -> (
    None
):
    """Without apparent substitution, AUTO does NOT pick COOL when raw < target+tol."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 27.4
    ev._environment.target_temp = 27.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
    # effective_temp_for_mode returns raw for all modes (flag off behaviour).
    ev._environment.effective_temp_for_mode = lambda mode: 27.4
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None  # idle


def test_full_scan_apparent_only_affects_cool_decisions() -> None:
    """HEAT decisions still consult cur_temp directly (regression guard)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5
    ev._environment.target_temp = 21.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
    # If something accidentally consulted effective_temp_for_mode for HEAT,
    # this stub would lie and say apparent is 22 — which would NOT trigger HEAT.
    # The test passes only if _temp_too_cold uses raw cur_temp (20.5 < 20.5).
    ev._environment.effective_temp_for_mode = lambda mode: 22.0
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT
