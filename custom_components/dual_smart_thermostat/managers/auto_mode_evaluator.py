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
        """Return the next AutoDecision. Subsequent tasks fill this in."""
        # Placeholder — overridden in Task 2.
        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)
