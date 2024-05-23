from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.specific_hvac_device import (
    SpecificHVACDevice,
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


class HeaterDevice(SpecificHVACDevice):

    hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
        )

    @property
    def target_env_attr(self) -> str:
        return (
            "_target_temp_low" if self.features.is_range_mode else self._target_env_attr
        )

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.debug({self.__class__.__name__})
        _LOGGER.debug("async_control_hvac")
        _LOGGER.debug(
            "sensor safety timed out: %s", self.environment.is_sensor_safety_timed_out
        )
        self._set_self_active()

        if not self._needs_control(time, force):
            _LOGGER.debug("No need for control")
            return

        _LOGGER.debug("Needs control")

        if self.is_active:
            await self._async_control_device_when_on(time)
        else:
            await self._async_control_device_when_off(time)

    async def _async_control_device_when_on(self, time=None) -> None:
        """Check if we need to turn heating on or off when theheater is on."""
        too_hot = self.environment.is_too_hot(self.target_env_attr)
        is_floor_hot = self.environment.is_floor_hot
        is_floor_cold = self.environment.is_floor_cold
        is_sensor_safety_timed_out = self.environment.is_sensor_safety_timed_out
        any_opening_open = self.openings.any_opening_open(self.hvac_mode)

        _LOGGER.debug("_async_control_device_when_on, floor cold: %s", is_floor_cold)
        _LOGGER.debug("_async_control_device_when_on, too_hot: %s", too_hot)
        _LOGGER.debug(
            "is sensor safety timed out: %s",
            self.environment.is_sensor_safety_timed_out,
        )

        if (
            (too_hot or is_floor_hot) or any_opening_open or is_sensor_safety_timed_out
        ) and not is_floor_cold:
            _LOGGER.debug("Turning off heater %s", self.entity_id)

            await self.async_turn_off()

            if too_hot:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_REACHED
            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING
            if is_sensor_safety_timed_out:
                self._hvac_action_reason = HVACActionReason.TEMPERATURE_SENSOR_TIMED_OUT

        elif (
            time is not None
            and not any_opening_open
            and not is_floor_hot
            and not is_sensor_safety_timed_out
        ):
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning on heater (from active) %s",
                self.entity_id,
            )
            self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED
            await self.async_turn_on()

    async def _async_control_device_when_off(self, time=None) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.debug("%s _async_control_device_when_off", self.__class__.__name__)

        too_cold = self.environment.is_too_cold(self.target_env_attr)
        is_floor_hot = self.environment.is_floor_hot
        is_floor_cold = self.environment.is_floor_cold
        any_opening_open = self.openings.any_opening_open(self.hvac_mode)

        if (too_cold and not any_opening_open and not is_floor_hot) or is_floor_cold:
            _LOGGER.debug("Turning on heater (from inactive) %s", self.entity_id)

            await self.async_turn_on()

            if is_floor_cold:
                self._hvac_action_reason = HVACActionReason.LIMIT
            else:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED

        elif time is not None or any_opening_open or is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.debug("Keep-alive - Turning off heater %s", self.entity_id)
            await self.async_turn_off()

            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING
