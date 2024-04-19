import datetime
from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.controllable_hvac_device import (
    ControlableHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_device import (
    HeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    HVACDevice,
    merge_hvac_modes,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class HeaterAUXHeaterDevice(HVACDevice, ControlableHVACDevice):

    _target_temp_attr: str = "_target_temp"

    def __init__(
        self,
        hass: HomeAssistant,
        heater_device: HeaterDevice,
        aux_heter_device: HeaterDevice,
        aux_heater_timeout: timedelta,
        aux_heater_dual_mode: bool,
        initial_hvac_mode: HVACMode,
        temperatures: TemperatureManager,
        openings: OpeningManager,
        range_mode: bool = False,
    ) -> None:
        super().__init__(hass, temperatures, openings)

        self._device_type = self.__class__.__name__
        self.heater_device = heater_device
        self.aux_heater_device = aux_heter_device
        self._aux_heater_timeout = aux_heater_timeout
        self._aux_heater_dual_mode = aux_heater_dual_mode

        if range_mode:
            self._target_temp_attr = "_target_temp_low"

        self._aux_heater_last_run: datetime = None

        # _hvac_modes are the combined values of the heater_device.hvac_modes and aux_heter_device.hvac_modes without duplicates
        self.hvac_modes = merge_hvac_modes(
            heater_device.hvac_modes, aux_heter_device.hvac_modes
        )

        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
        else:
            self._hvac_mode = None

    def set_context(self, context: Context):
        self.heater_device.set_context(context)
        self.aux_heater_device.set_context(context)
        self._context = context

    def get_device_ids(self) -> list[str]:
        return [self.heater_device.entity_id, self.aux_heater_device.entity_id]

    @property
    def is_active(self) -> bool:
        return self.heater_device.is_active or self.aux_heater_device.is_active

    @property
    def hvac_action(self) -> HVACAction:
        if self.is_active:
            return HVACAction.HEATING
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    async def async_on_startup(self):

        entity_state1 = self.hass.states.get(self.heater_device.entity_id)
        entity_state2 = self.hass.states.get(self.aux_heater_device.entity_id)
        if entity_state1 and entity_state1.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self.hass.loop.create_task(self._async_check_device_initial_state())

        if entity_state2 and entity_state2.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self.hass.loop.create_task(self._async_check_device_initial_state())

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        if self._hvac_mode == HVACMode.OFF and self.is_active:
            _LOGGER.warning(
                "The climate mode is OFF, but the switch device is ON. Turning off device %s, %s",
                self.heater_device.entity_id,
                self.aux_heater_device.entity_id,
            )
            await self.async_turn_off()

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.debug({self.__class__.__name__})
        match self._hvac_mode:
            case HVACMode.HEAT:
                # await self.heater_device.async_control_hvac(time, force)
                await self.async_control_devices(time, force)
            case HVACMode.OFF:
                await self.async_turn_off()
            case _:
                _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)

    async def async_control_devices(self, time=None, force=False):
        _LOGGER.debug("async_control_devices at: %s", dt.utcnow())
        if self.is_active:
            await self._async_control_devices_when_on(time)
        else:
            await self._async_control_devices_when_off(time)

    async def async_control_devices_forced(self, time=None) -> None:
        """Control the heater and aux heater when forced."""
        _LOGGER.debug("Forced control of devices")
        await self.async_control_devices(time, force=True)

    async def _async_control_devices_when_off(self, time=None) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.debug("%s _async_control_devices_when_off", self.__class__.__name__)

        too_cold = self.temperatures.is_too_cold(self._target_temp_attr)
        is_floor_hot = self.temperatures.is_floor_hot
        is_floor_cold = self.temperatures.is_floor_cold
        any_opening_open = self.openings.any_opening_open

        if (too_cold and not any_opening_open and not is_floor_hot) or is_floor_cold:

            if self._has_aux_heating_ran_today:
                await self._async_handle_aux_heater_ran_today()
            else:
                await self._async_handle_aux_heater_havent_run_today()

            if is_floor_cold:
                self._hvac_action_reason = HVACActionReason.LIMIT
            else:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED

        elif time is not None or any_opening_open or is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning off heater %s", self.heater_device.entity_id
            )
            await self.heater_device.async_turn_off()

            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING

    async def _async_handle_aux_heater_ran_today(self) -> None:
        _LOGGER.info("Aux heater has already ran today")
        if self._aux_heater_dual_mode:
            await self.heater_device.async_turn_on()
        await self.aux_heater_device.async_turn_on()

    async def _async_handle_aux_heater_havent_run_today(self) -> None:
        if self._aux_heater_dual_mode:
            await self.heater_device.async_turn_on()
        await self.heater_device.async_turn_on()

        _LOGGER.info("Scheduling aux heater check")

        # can we move this to the climate entity?
        self.async_on_remove(
            async_call_later(
                self.hass,
                self._aux_heater_timeout,
                self.async_control_devices_forced,
            )
        )

    async def _async_control_devices_when_on(self, time=None) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.debug("%s _async_control_devices_when_on", self.__class__.__name__)

        too_hot = self.temperatures.is_too_hot(self._target_temp_attr)
        is_floor_hot = self.temperatures.is_floor_hot
        is_floor_cold = self.temperatures.is_floor_cold
        any_opening_open = self.openings.any_opening_open
        first_stage_timed_out = self._first_stage_heating_timed_out()

        _LOGGER.info(
            "too_hot: %s, is_floor_hot: %s, is_floor_cold: %s, any_opening_open: %s, time: %s",
            too_hot,
            is_floor_hot,
            is_floor_cold,
            any_opening_open,
            time,
        )

        _LOGGER.info(
            "_first_stage_heating_timed_out: %s",
            first_stage_timed_out,
        )
        _LOGGER.info("aux_heater_timeout: %s", self._aux_heater_timeout)
        _LOGGER.info(
            "aux_heater_device.is_active: %s", self.aux_heater_device.is_active
        )

        if ((too_hot or is_floor_hot) or any_opening_open) and not is_floor_cold:
            _LOGGER.info("Turning off heaters when on")

            # maybe call device -> async_control_hvac?
            await self.heater_device.async_turn_off()
            await self.aux_heater_device.async_turn_off()

            if too_hot:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_REACHED
            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING

        elif (
            self._first_stage_heating_timed_out()
            and not self.aux_heater_device.is_active
        ):
            _LOGGER.debug("Turning on aux heater %s", self.aux_heater_device.entity_id)
            if not self._aux_heater_dual_mode:
                await self.heater_device.async_turn_off()
            await self.aux_heater_device.async_turn_on()
            self._aux_heater_last_run = datetime.datetime.now()
            self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED

        else:
            await self.heater_device.async_control_hvac(time, force=False)
            self._hvac_action_reason = self.heater_device.HVACActionReason

    async def async_turn_on(self):
        """self._control_hvac will handle the logic for turning on the heater and aux heater."""
        pass

    async def async_turn_off(self):
        await self.heater_device.async_turn_off()
        await self.aux_heater_device.async_turn_off()

    def _first_stage_heating_timed_out(self, timeout=None) -> bool:
        """Determines if the heater switch has been on for the timeout period."""
        if timeout is None:
            timeout = self._aux_heater_timeout - timedelta(seconds=1)

        return condition.state(
            self.hass,
            self.heater_device.entity_id,
            STATE_ON,
            timeout,
        )

    @property
    def _has_aux_heating_ran_today(self) -> bool:
        """Determines if the aux heater has been used today."""
        if self._aux_heater_last_run is None:
            return False

        if self._aux_heater_last_run.date() == datetime.datetime.now().date():
            return True

        return False
