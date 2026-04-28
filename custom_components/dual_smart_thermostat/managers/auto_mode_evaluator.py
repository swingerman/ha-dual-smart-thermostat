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

        # Priority 1: floor overheat — preempts everything.
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)

        # Priority 2: opening — preempts everything except floor overheat.
        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)

        # Temperature sensor stall pauses everything below safety.
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = (
            feats.is_configured_for_dryer_mode and not humidity_sensor_stalled
        )

        # Priority 3 (urgent): humidity at 2x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priorities 4-5 fill in next task (urgent temp).

        # Priority 6 (normal): humidity at 1x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priorities 7-10 fill in next tasks.

        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)

    @staticmethod
    def _humidity_at(env, *, multiplier: int) -> bool:
        """Whether cur_humidity is at or above target_humidity + multiplier×moist_tolerance."""
        if env.cur_humidity is None or env.target_humidity is None:
            return False
        threshold = env.target_humidity + multiplier * env._moist_tolerance
        return env.cur_humidity >= threshold
