"""Auto Mode priority evaluator (Phase 1.2).

Pure decision class. Reads from injected EnvironmentManager / OpeningManager /
FeatureManager and returns an AutoDecision. Holds no mutable state beyond
construction-time references; the previous decision is passed in by the caller
so the evaluator itself is reentrant.

Reserved for the climate entity's AUTO mode intercept; never wired in unless
the user has selected ``HVACMode.AUTO`` and ``features.is_configured_for_auto_mode``
is True.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.climate import HVACMode

from ..hvac_action_reason.hvac_action_reason import HVACActionReason


@dataclass(frozen=True)
class AutoDecision:
    """Result of one priority evaluation.

    ``next_mode`` is ``None`` when the engine wants to keep the last picked
    sub-mode running (e.g., all targets met — actuators idle naturally via
    the existing bang-bang controller).
    """

    next_mode: HVACMode | None
    reason: HVACActionReason


def _auto_scope():
    """Return the OpeningHvacModeScope value used for AUTO opening checks."""
    from ..managers.opening_manager import OpeningHvacModeScope

    return OpeningHvacModeScope.ALL


class AutoModeEvaluator:
    """Decides which concrete sub-mode AUTO runs each tick."""

    def __init__(self, environment, openings, features) -> None:
        self._environment = environment
        self._openings = openings
        self._features = features

    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        """Return the next AutoDecision based on the priority table."""
        env = self._environment
        feats = self._features

        # Safety preempts everything (no flap protection for safety).
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)
        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = (
            feats.is_configured_for_dryer_mode and not humidity_sensor_stalled
        )
        can_heat = (
            getattr(feats, "is_configured_for_heater_mode", False)
            or feats.is_configured_for_heat_pump_mode
        )
        can_cool = (
            feats.is_configured_for_heat_pump_mode
            or feats.is_configured_for_cooler_mode
            or feats.is_configured_for_dual_mode
        )

        # Flap prevention: if last_decision is set and that mode's goal is
        # still pending, only an urgent-tier priority can preempt.
        if last_decision is not None and last_decision.next_mode is not None:
            if self._goal_pending(last_decision.next_mode, humidity_available):
                urgent = self._urgent_decision(humidity_available, can_heat, can_cool)
                if urgent is not None and urgent.next_mode != last_decision.next_mode:
                    return urgent
                return last_decision

        return self._full_scan(humidity_available, can_heat, can_cool, last_decision)

    def _goal_pending(self, mode, humidity_available: bool) -> bool:
        """Whether the original triggering condition for ``mode`` still holds."""
        env = self._environment
        if mode == HVACMode.HEAT:
            return self._temp_too_cold(env, multiplier=1)
        if mode == HVACMode.COOL:
            return self._temp_too_hot(env, multiplier=1)
        if mode == HVACMode.DRY:
            return humidity_available and self._humidity_at(env, multiplier=1)
        if mode == HVACMode.FAN_ONLY:
            return self._fan_band(env)
        return False

    def _urgent_decision(
        self,
        humidity_available: bool,
        can_heat: bool = True,
        can_cool: bool = True,
    ) -> AutoDecision | None:
        env = self._environment
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )
        if can_heat and self._temp_too_cold(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        if can_cool and self._temp_too_hot(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        return None

    def _full_scan(
        self,
        humidity_available: bool,
        can_heat: bool,
        can_cool: bool,
        last_decision: AutoDecision | None,
    ) -> AutoDecision:
        env = self._environment
        feats = self._features

        urgent = self._urgent_decision(humidity_available, can_heat, can_cool)
        if urgent is not None:
            return urgent

        # Priority 6 (normal humidity).
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priority 7 (normal cold).
        if can_heat and self._temp_too_cold(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 8 (normal hot).
        if can_cool and self._temp_too_hot(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 9 (comfort fan band).
        if feats.is_configured_for_fan_mode and self._fan_band(env):
            return AutoDecision(
                next_mode=HVACMode.FAN_ONLY,
                reason=HVACActionReason.AUTO_PRIORITY_COMFORT,
            )

        # Priority 10 (idle).
        idle_reason = HVACActionReason.TARGET_TEMP_REACHED
        if last_decision is not None and last_decision.next_mode == HVACMode.DRY:
            idle_reason = HVACActionReason.TARGET_HUMIDITY_REACHED
        return AutoDecision(next_mode=None, reason=idle_reason)

    @staticmethod
    def _humidity_at(env, *, multiplier: int) -> bool:
        """Whether cur_humidity is at or above target_humidity + multiplier×moist_tolerance."""
        if env.cur_humidity is None or env.target_humidity is None:
            return False
        threshold = env.target_humidity + multiplier * env._moist_tolerance
        return env.cur_humidity >= threshold

    def _cold_target(self, env) -> float | None:
        """Single-target mode: target_temp. Range mode: target_temp_low."""
        if self._features.is_range_mode and env.target_temp_low is not None:
            return env.target_temp_low
        return env.target_temp

    def _hot_target(self, env) -> float | None:
        """Single-target mode: target_temp. Range mode: target_temp_high."""
        if self._features.is_range_mode and env.target_temp_high is not None:
            return env.target_temp_high
        return env.target_temp

    def _temp_too_cold(self, env, *, multiplier: int) -> bool:
        cold_target = self._cold_target(env)
        if env.cur_temp is None or cold_target is None:
            return False
        cold_tolerance, _ = env._get_active_tolerance_for_mode()
        return env.cur_temp <= cold_target - multiplier * cold_tolerance

    def _temp_too_hot(self, env, *, multiplier: int) -> bool:
        hot_target = self._hot_target(env)
        if env.cur_temp is None or hot_target is None:
            return False
        _, hot_tolerance = env._get_active_tolerance_for_mode()
        return env.cur_temp >= hot_target + multiplier * hot_tolerance

    def _fan_band(self, env) -> bool:
        """Whether cur_temp is within the fan-tolerance comfort band."""
        target_attr = (
            "_target_temp_high"
            if (self._features.is_range_mode and env.target_temp_high is not None)
            else "_target_temp"
        )
        return env.is_within_fan_tolerance(target_attr)
