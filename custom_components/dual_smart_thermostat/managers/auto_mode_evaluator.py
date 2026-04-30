"""Auto Mode priority evaluator.

Pure decision class. Reads from injected EnvironmentManager / OpeningManager /
FeatureManager and returns an AutoDecision. Holds no mutable state beyond
construction-time references; the previous decision is passed in by the caller
so the evaluator itself is reentrant.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.climate import HVACMode

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from .opening_manager import OpeningHvacModeScope

_AUTO_SCOPE = OpeningHvacModeScope.ALL


@dataclass(frozen=True)
class AutoDecision:
    """Result of one priority evaluation.

    ``next_mode`` is ``None`` when the engine wants to keep the last picked
    sub-mode running (e.g., all targets met — actuators idle naturally via
    the existing bang-bang controller).
    """

    next_mode: HVACMode | None
    reason: HVACActionReason


class AutoModeEvaluator:
    """Decides which concrete sub-mode AUTO runs each tick."""

    def __init__(
        self,
        environment,
        openings,
        features,
        *,
        outside_delta_boost_c: float | None = None,
    ) -> None:
        self._environment = environment
        self._openings = openings
        self._features = features
        self._outside_delta_boost_c = outside_delta_boost_c

    @property
    def _can_heat(self) -> bool:
        feats = self._features
        return (
            feats.is_configured_for_heater_mode
            or feats.is_configured_for_heat_pump_mode
        )

    @property
    def _can_cool(self) -> bool:
        feats = self._features
        return (
            feats.is_configured_for_heat_pump_mode
            or feats.is_configured_for_cooler_mode
            or feats.is_configured_for_dual_mode
        )

    @property
    def _dryer_configured(self) -> bool:
        return self._features.is_configured_for_dryer_mode

    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
        outside_temp: float | None = None,
        outside_sensor_stalled: bool = False,
    ) -> AutoDecision:
        """Return the next AutoDecision based on the priority table."""
        env = self._environment

        # Safety preempts everything (no flap protection for safety).
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)
        if self._openings.any_opening_open(hvac_mode_scope=_AUTO_SCOPE):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = self._dryer_configured and not humidity_sensor_stalled
        # Active tolerances depend on env._hvac_mode which is mutated only
        # after evaluate() returns; safe to fetch once per call.
        cold_tolerance, hot_tolerance = env._get_active_tolerance_for_mode()

        # Flap prevention: if last_decision is set and that mode's goal is
        # still pending, only an urgent-tier priority can preempt.
        if last_decision is not None and last_decision.next_mode is not None:
            if self._goal_pending(
                last_decision.next_mode,
                humidity_available,
                cold_tolerance,
                hot_tolerance,
            ):
                urgent = self._urgent_decision(
                    humidity_available, cold_tolerance, hot_tolerance
                )
                if urgent is not None and urgent.next_mode != last_decision.next_mode:
                    return urgent
                return last_decision

        return self._full_scan(
            humidity_available, cold_tolerance, hot_tolerance, last_decision
        )

    def _goal_pending(
        self,
        mode,
        humidity_available: bool,
        cold_tolerance: float,
        hot_tolerance: float,
    ) -> bool:
        """Whether the original triggering condition for ``mode`` still holds."""
        env = self._environment
        if mode == HVACMode.HEAT:
            return self._temp_too_cold(env, cold_tolerance, multiplier=1)
        if mode == HVACMode.COOL:
            return self._temp_too_hot(env, hot_tolerance, multiplier=1)
        if mode == HVACMode.DRY:
            return humidity_available and self._humidity_at(env, multiplier=1)
        if mode == HVACMode.FAN_ONLY:
            return self._fan_band(env)
        return False

    def _urgent_decision(
        self,
        humidity_available: bool,
        cold_tolerance: float,
        hot_tolerance: float,
    ) -> AutoDecision | None:
        env = self._environment
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )
        if self._can_heat and self._temp_too_cold(env, cold_tolerance, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        return None

    def _full_scan(
        self,
        humidity_available: bool,
        cold_tolerance: float,
        hot_tolerance: float,
        last_decision: AutoDecision | None,
    ) -> AutoDecision:
        env = self._environment

        urgent = self._urgent_decision(
            humidity_available, cold_tolerance, hot_tolerance
        )
        if urgent is not None:
            return urgent

        # Priority 6 (normal humidity).
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priority 7 (normal cold).
        if self._can_heat and self._temp_too_cold(env, cold_tolerance, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 8 (normal hot).
        if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 9 (comfort fan band).
        if self._features.is_configured_for_fan_mode and self._fan_band(env):
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

    def _temp_too_cold(self, env, cold_tolerance: float, *, multiplier: int) -> bool:
        cold_target = self._cold_target(env)
        if env.cur_temp is None or cold_target is None:
            return False
        return env.cur_temp <= cold_target - multiplier * cold_tolerance

    def _temp_too_hot(self, env, hot_tolerance: float, *, multiplier: int) -> bool:
        hot_target = self._hot_target(env)
        if env.cur_temp is None or hot_target is None:
            return False
        return env.cur_temp >= hot_target + multiplier * hot_tolerance

    def _fan_band(self, env) -> bool:
        """Whether cur_temp is within the fan-tolerance comfort band."""
        target_attr = (
            "_target_temp_high"
            if (self._features.is_range_mode and env.target_temp_high is not None)
            else "_target_temp"
        )
        return env.is_within_fan_tolerance(target_attr)
