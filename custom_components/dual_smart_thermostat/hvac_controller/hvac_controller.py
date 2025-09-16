from abc import ABC, abstractmethod
from datetime import timedelta
import enum
import logging
from typing import Callable

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..managers.environment_manager import EnvironmentManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class HvacGoal(enum.StrEnum):
    """The environment goal of the HVAC."""

    LOWER = "lower"
    RAISE = "raise"


class HvacEnvStrategy:
    """Strategy for controlling the HVAC based on the environment."""

    def __init__(
        self,
        above: Callable[[], bool],
        below: Callable[[], bool],
        goal_reached_reason: Callable[[], HVACActionReason],
        goal_not_reached_reason: Callable[[], HVACActionReason],
        goal: HvacGoal,
    ):
        self.above = above
        self.below = below
        self.goal_reached_reason = goal_reached_reason
        self.goal_not_reached_reason = goal_not_reached_reason
        self.goal = goal

    @property
    def hvac_goal_reached(self) -> bool:
        _LOGGER.debug(
            "Checking if goal reached. Goal: %s, Above: %s, Below: %s",
            self.goal,
            self.above(),
            self.below(),
        )
        if self.goal == HvacGoal.LOWER:
            return self.above()
        return self.below()

    @property
    def hvac_goal_not_reached(self) -> bool:
        if self.goal == HvacGoal.LOWER:
            return self.below()
        return self.above()


class HvacController(ABC):
    """Abstract class for controlling an HVAC device."""

    hass: HomeAssistant
    entity_id: str
    min_cycle_duration: timedelta
    _hvac_action_reason: HVACActionReason
    _environment: EnvironmentManager
    _openings: OpeningManager
    async_turn_on_callback: Callable
    async_turn_off_callback: Callable

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id,
        min_cycle_duration: timedelta,
        environment: EnvironmentManager,
        openings: OpeningManager,
        turn_on_callback: Callable,
        turn_off_callback: Callable,
    ) -> None:
        self._controller_type = self.__class__.__name__

        self.hass = hass
        self.entity_id = entity_id
        self.min_cycle_duration = min_cycle_duration
        self._environment = environment
        self._openings = openings
        self.async_turn_on_callback = turn_on_callback
        self.async_turn_off_callback = turn_off_callback

        self._hvac_action_reason = HVACActionReason.NONE

    @property
    def hvac_action_reason(self) -> HVACActionReason:
        return self._hvac_action_reason

    @abstractmethod
    def async_control_device_when_on(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        pass

    @abstractmethod
    def async_control_device_when_off(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        pass

    @abstractmethod
    def needs_control(self, active: bool, hvac_mode: HVACMode, time=None) -> bool:
        pass
