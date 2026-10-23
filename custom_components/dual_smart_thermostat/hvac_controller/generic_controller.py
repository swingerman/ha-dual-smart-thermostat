from datetime import timedelta
import logging
from typing import Callable

from homeassistant.components.climate import HVACMode
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.const import STATE_CLOSED, STATE_OFF, STATE_ON, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition
import homeassistant.util.dt as dt_util

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_controller.hvac_controller import HvacController, HvacEnvStrategy
from ..managers.environment_manager import EnvironmentManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class GenericHvacController(HvacController):

    entity_id: str
    min_cycle_duration: timedelta
    _hvac_action_reason: HVACActionReason

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

        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            turn_on_callback,
            turn_off_callback,
        )

        self._hvac_action_reason = HVACActionReason.NONE

    @property
    def _is_valve(self) -> bool:
        state = self.hass.states.get(self.entity_id)
        domain = state.domain if state else None
        return domain == VALVE_DOMAIN

    @property
    def _on_off_states(self) -> tuple[str, str]:
        """(on, off) entity states for this device's domain."""
        if self._is_valve:
            return STATE_OPEN, STATE_CLOSED
        return STATE_ON, STATE_OFF

    @property
    def hvac_action_reason(self) -> HVACActionReason:
        return self._hvac_action_reason

    @hvac_action_reason.setter
    def hvac_action_reason(self, hvac_action_reason: HVACActionReason) -> None:
        self._hvac_action_reason = hvac_action_reason

    @property
    def is_active(self) -> bool:
        """If the toggleable hvac device is currently active."""
        on_state = self._on_off_states[0]

        _LOGGER.debug(
            "Checking if device is active: %s, on_state: %s",
            self.entity_id,
            on_state,
        )
        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, on_state
        ):
            return True
        return False

    def ran_long_enough(self) -> bool:
        on_state, off_state = self._on_off_states
        current_state = on_state if self.is_active else off_state

        _LOGGER.debug("Checking if device ran long enough: %s", self.entity_id)
        _LOGGER.debug("current_state: %s", current_state)
        _LOGGER.debug("min_cycle_duration: %s", self.min_cycle_duration)
        _LOGGER.debug("time: %s", dt_util.utcnow())

        try:
            long_enough = condition.state(
                self.hass,
                self.entity_id,
                current_state,
                self.min_cycle_duration,
            )
        except ConditionError:
            long_enough = False

        return long_enough

    def needs_control(
        self, active: bool, hvac_mode: HVACMode, time=None, force=False
    ) -> bool:
        """Checks if the controller needs to continue."""
        # CRITICAL: Never control when HVAC mode is OFF, EXCEPT for keep-alive
        # This prevents devices from turning on when thermostat is in OFF state,
        # but allows keep-alive to enforce OFF state (turn devices off periodically)
        if hvac_mode == HVACMode.OFF and time is None:
            _LOGGER.debug(
                "HVAC mode is OFF and not keep-alive, skipping control (force=%s)",
                force,
            )
            return False

        if not active and time is None:
            _LOGGER.debug(
                "Device not active and time is None, skipping control",
            )
            return False

        return True

    def min_cycle_elapsed(self, force=False) -> bool:
        """True if the device may change its on/off state now."""
        if force or not self.min_cycle_duration:
            return True
        long_enough = self.ran_long_enough()
        _LOGGER.debug("Checking if device ran long enough: %s", long_enough)
        return long_enough

    async def async_control_device_when_on(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when theheater is on."""
        _LOGGER.debug(
            "%s Controlling hvac entity %s while on",
            self.__class__.__name__,
            self.entity_id,
        )
        _LOGGER.debug("below_env_attr: %s", strategy.hvac_goal_reached)
        _LOGGER.debug("any_opening_open: %s", any_opening_open)
        _LOGGER.debug("hvac_goal_reached: %s", strategy.hvac_goal_reached)

        if strategy.hvac_goal_reached or any_opening_open:
            _LOGGER.info(
                "Turning off entity due to hvac goal reached or opening is open %s",
                self.entity_id,
            )

            await self.async_turn_off_callback()

            if strategy.hvac_goal_reached:
                _LOGGER.debug("setting hvac_action_reason goal reached")
                self._hvac_action_reason = strategy.goal_reached_reason()
            if any_opening_open:
                _LOGGER.debug("setting hvac_action_reason opening")
                self._hvac_action_reason = HVACActionReason.OPENING

        elif time is not None and not any_opening_open:
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning on entity (from active) %s",
                self.entity_id,
            )
            await self.async_turn_on_callback()
            self._hvac_action_reason = strategy.goal_not_reached_reason()
        else:
            _LOGGER.debug("No case matched when - keep device on")

    async def async_control_device_when_off(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.debug(
            "%s Controlling hvac entity %s while off",
            self.__class__.__name__,
            self.entity_id,
        )
        _LOGGER.debug("above_env_attr: %s", strategy.hvac_goal_reached)
        _LOGGER.debug("below_env_attr: %s", strategy.hvac_goal_not_reached)
        _LOGGER.debug("any_opening_open: %s", any_opening_open)
        _LOGGER.debug("is_active: %s", True)
        _LOGGER.debug("time: %s", time)

        if strategy.hvac_goal_not_reached and not any_opening_open:
            _LOGGER.info(
                "Turning on entity (from inactive) due to hvac goal is not reached %s",
                self.entity_id,
            )

            await self.async_turn_on_callback()
            self._hvac_action_reason = strategy.goal_not_reached_reason()

        elif time is not None:
            # The time argument is passed only in keep-alive case
            # Keep-alive should only send turn_off if device is unexpectedly ON
            if self.is_active:
                _LOGGER.info("Keep-alive - Turning off entity %s", self.entity_id)
                await self.async_turn_off_callback()
            else:
                _LOGGER.debug("Keep-alive - Entity already off %s", self.entity_id)

            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING
        else:
            _LOGGER.debug("No case matched when - keeping device off")
            if strategy.hvac_goal_reached:
                self._hvac_action_reason = strategy.goal_reached_reason()
            else:
                self._hvac_action_reason = strategy.goal_not_reached_reason()
