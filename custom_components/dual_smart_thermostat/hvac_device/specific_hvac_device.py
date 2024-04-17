from datetime import timedelta
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, HomeAssistant
from homeassistant.helpers import condition
import homeassistant.util.dt as dt_util

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.controllable_hvac_device import (
    ControlableHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    HVACDevice,
    Switchable,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class SpecificHVACDevice(HVACDevice, ControlableHVACDevice, Switchable):

    _target_temp_attr: str = "_target_temp"

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        temperatures: TemperatureManager,
        openings: OpeningManager,
    ) -> None:
        super().__init__(hass, temperatures, openings)
        self._device_type = self.__class__.__name__
        self.entity_id = entity_id
        self.min_cycle_duration = min_cycle_duration

        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
        else:
            self._hvac_mode = None

    def set_context(self, context: Context):
        self._context = context

    def get_device_ids(self) -> list[str]:
        return [self.entity_id]

    async def async_turn_on(self):
        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_OFF
        ):

            data = {ATTR_ENTITY_ID: self.entity_id}
            await self.hass.services.async_call(
                HA_DOMAIN, SERVICE_TURN_ON, data, context=self._context
            )

    async def async_turn_off(self):
        _LOGGER.info("Turning off entity %s", self.entity_id)
        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_ON
        ):

            data = {ATTR_ENTITY_ID: self.entity_id}
            await self.hass.services.async_call(
                HA_DOMAIN, SERVICE_TURN_OFF, data, context=self._context
            )

    @property
    def is_active(self) -> bool:
        """If the toggleable cooler device is currently active."""
        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_ON
        ):
            return True
        return False

    # @property
    def _ran_long_enough(self) -> bool:
        if self.is_active:
            current_state = STATE_ON
        else:
            current_state = HVACMode.OFF

        _LOGGER.debug("Checking if device ran long enough: %s", self.entity_id)
        _LOGGER.debug("current_state: %s", current_state)
        _LOGGER.debug("min_cycle_duration: %s", self.min_cycle_duration)
        _LOGGER.debug("time: %s", dt_util.utcnow())

        long_enough = condition.state(
            self.hass,
            self.entity_id,
            current_state,
            self.min_cycle_duration,
        )

        return long_enough

    def _set_self_active(self) -> None:
        """Checks if active state needs to be set true."""
        _LOGGER.debug("_active: %s", self._active)
        _LOGGER.debug("cur_temp: %s", self.temperatures.cur_temp)
        target_temp = getattr(self.temperatures, self._target_temp_attr)
        _LOGGER.debug("target_temp: %s", target_temp)

        if (
            not self._active
            and None not in (self.temperatures.cur_temp, target_temp)
            and self._hvac_mode != HVACMode.OFF
        ):
            self._active = True
            _LOGGER.debug(
                "Obtained current and target temperature. Device active. %s, %s",
                self.temperatures.cur_temp,
                target_temp,
            )

    def _needs_control(self, time=None, force=False) -> bool:
        """Checks if the controller needs to continue."""
        if not self._active or self._hvac_mode == HVACMode.OFF:
            _LOGGER.debug(
                "Not active or hvac mode is off active: %s, _hvac_mode: %s",
                self._active,
                self._hvac_mode,
            )
            return False

        if not force and time is None:
            # If the `force` argument is True, we
            # ignore `min_cycle_duration`.
            # If the `time` argument is not none, we were invoked for
            # keep-alive purposes, and `min_cycle_duration` is irrelevant.
            if self.min_cycle_duration:
                _LOGGER.debug(
                    "Checking if device ran long enough: %s", self._ran_long_enough()
                )
                return self._ran_long_enough()
        return True

    # def needs_cycle(self) -> bool:
    #     """Determines if the device needs to cycle."""
    #     return self._ran_long_enough

    async def async_control_hvac(self, time=None, force=False):
        """Controls the HVAC of the device."""

        _LOGGER.debug(
            "%s - async_control_hvac time: %s. force: %s",
            self._device_type,
            time,
            force,
        )
        self._set_self_active()

        _LOGGER.debug("_needs_control: %s", self._needs_control(time, force))
        if not self._needs_control(time, force):
            return

        any_opening_open = self.openings.any_opening_open

        _LOGGER.info(
            "%s - async_control_hvac - is device active: %s, %s,  is opening open: %s",
            self._device_type,
            self.entity_id,
            self.is_active,
            any_opening_open,
        )

        if self.is_active:
            await self._async_control_when_active(time)
        else:
            await self._async_control_when_inactive(time)

    async def _async_control_when_active(self, time=None) -> None:
        _LOGGER.debug("%s _async_control_when_active", self.__class__.__name__)
        too_cold = self.temperatures.is_too_cold(self._target_temp_attr)
        any_opening_open = self.openings.any_opening_open

        if too_cold or any_opening_open:
            _LOGGER.debug("Turning off entity %s", self.entity_id)
            await self.async_turn_off()
            if too_cold:
                self._HVACActionReason = HVACActionReason.TARGET_TEMP_REACHED
            if any_opening_open:
                self._HVACActionReason = HVACActionReason.OPENING

        elif time is not None and not any_opening_open:
            # The time argument is passed only in keep-alive case
            _LOGGER.debug(
                "Keep-alive - Turning on entity (from active) %s",
                self.entity_id,
            )
            await self.async_turn_on()
            self._HVACActionReason = HVACActionReason.TARGET_TEMP_NOT_REACHED

    async def _async_control_when_inactive(self, time=None) -> None:
        too_hot = self.temperatures.is_too_hot(self._target_temp_attr)
        any_opening_open = self.openings.any_opening_open

        if too_hot and not any_opening_open:
            _LOGGER.debug("Turning on entity (from inactive) %s", self.entity_id)
            await self.async_turn_on()
            self._HVACActionReason = HVACActionReason.TARGET_TEMP_NOT_REACHED
        elif time is not None or any_opening_open:
            # The time argument is passed only in keep-alive case
            _LOGGER.debug("Keep-alive - Turning off entity %s", self.entity_id)
            await self.async_turn_off()

            if any_opening_open:
                self._HVACActionReason = HVACActionReason.OPENING

    def on_startup(self):
        entity_state = self.hass.states.get(self.entity_id)
        if entity_state and entity_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self.hass.loop.create_task(self._async_check_device_initial_state())

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        if self._hvac_mode == HVACMode.OFF and self.is_active:
            _LOGGER.warning(
                "The climate mode is OFF, but the switch device is ON. Turning off device %s",
                self.entity_id,
            )
            await self.async_turn_off()
