import datetime
from datetime import timedelta
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_hvac_device import (
    MultiHvacDevice,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)

_LOGGER = logging.getLogger(__name__)


class HeaterAUXHeaterDevice(MultiHvacDevice):

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass, devices, initial_hvac_mode, environment, openings, features
        )

        self._device_type = self.__class__.__name__
        self.heater_device = devices[0]
        self.aux_heater_device = devices[1]
        self._aux_heater_timeout = self._features.aux_heater_timeout
        self._aux_heater_dual_mode = self._features.aux_heater_dual_mode

        self._aux_heater_last_run: datetime = None

    @property
    def _target_env_attr(self) -> str:
        return "_target_temp_low" if self._features.is_range_mode else "_target_temp"

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
        _LOGGER.debug("is_active: %s", self.is_active)
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
        _LOGGER.info("%s Controlling hvac while off", self.__class__.__name__)

        too_cold = self.environment.is_too_cold(self._target_env_attr)
        is_floor_hot = self.environment.is_floor_hot
        is_floor_cold = self.environment.is_floor_cold
        any_opening_open = self.openings.any_opening_open(self.hvac_mode)

        _LOGGER.debug(
            "_target_env_attr: %s, too_cold: %s, is_floor_hot: %s, is_floor_cold: %s, any_opening_open: %s, time: %s",
            self._target_env_attr,
            too_cold,
            is_floor_hot,
            is_floor_cold,
            any_opening_open,
            time,
        )

        _LOGGER.debug("is_range-Mode: %s", self._features.is_range_mode)

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

        else:
            _LOGGER.debug("No case matched when - keep device off")

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
        _LOGGER.info("%s Controlling hvac while on", self.__class__.__name__)

        too_hot = self.environment.is_too_hot(self._target_env_attr)
        is_floor_hot = self.environment.is_floor_hot
        is_floor_cold = self.environment.is_floor_cold
        any_opening_open = self.openings.any_opening_open(self.hvac_mode)
        first_stage_timed_out = self._first_stage_heating_timed_out()

        _LOGGER.debug(
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
        _LOGGER.debug("aux_heater_timeout: %s", self._aux_heater_timeout)
        _LOGGER.debug(
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
