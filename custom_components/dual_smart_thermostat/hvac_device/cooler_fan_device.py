from datetime import datetime, timezone
import logging
from typing import Callable, Generic

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_device.generic_hvac_device import GenericHVACDevice
from ..hvac_device.multi_hvac_device import MultiHvacDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class CoolerFanDevice(MultiHvacDevice):

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list[GenericHVACDevice],
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass, devices, initial_hvac_mode, environment, openings, features
        )

        self._device_type = self.__class__.__name__
        self._fan_on_with_cooler = self._features.is_configured_for_fan_on_with_cooler

        self.cooler_device = next(
            device for device in devices if HVACMode.COOL in device.hvac_modes
        )
        self.fan_device = next(
            device for device in devices if HVACMode.FAN_ONLY in device.hvac_modes
        )

        if self.fan_device is None or self.cooler_device is None:
            _LOGGER.error("Fan or cooler device is not found")

        self._set_fan_hot_tolerance_on_state()

    def _set_fan_hot_tolerance_on_state(self):
        if self._features.fan_hot_tolerance_on_entity is not None:
            _LOGGER.debug(
                "Setting fan_hot_tolerance_on state: %s",
                self.hass.states.get(self._features.fan_hot_tolerance_on_entity).state,
            )
            self._fan_hot_tolerance_on = (
                self.hass.states.get(self._features.fan_hot_tolerance_on_entity).state
                == STATE_ON
            )
        else:
            self._fan_hot_tolerance_on = True

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @MultiHvacDevice.hvac_mode.setter
    def hvac_mode(self, hvac_mode: HVACMode):  # noqa: F811

        _LOGGER.debug("Setter setting hvac_mode: %s", hvac_mode)
        self._hvac_mode = hvac_mode
        self.set_sub_devices_hvac_mode(hvac_mode)

    async def async_on_startup(self, async_write_ha_state_cb: Callable = None) -> None:
        await super().async_on_startup(async_write_ha_state_cb)

        if self._features.fan_hot_tolerance_on_entity is not None:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self._features.fan_hot_tolerance_on_entity],
                    self._async_fan_hot_tolerance_on_changed,
                )
            )

    async def _async_fan_hot_tolerance_on_changed(
        self, event: Event[EventStateChangedData]
    ):
        data = event.data

        new_state = data["new_state"]

        _LOGGER.info("Fan hot tolerance on changed: %s", new_state)

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._fan_hot_tolerance_on = True
            return

        self._fan_hot_tolerance_on = new_state.state == STATE_ON

        _LOGGER.debug("fan_hot_tolerance_on is %s", self._fan_hot_tolerance_on)

        await self.async_control_hvac()
        self._async_write_ha_state_cb()

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        pass

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.info({self.__class__.__name__})
        _LOGGER.debug("hvac_mode: %s", self._hvac_mode)
        self._set_fan_hot_tolerance_on_state()
        _LOGGER.debug(
            "async_control_hvac fan_hot_tolerance_on: %s", self._fan_hot_tolerance_on
        )

        match self._hvac_mode:
            case HVACMode.COOL:
                if self._fan_on_with_cooler:
                    await self._async_control_when_fan_on_with_cooler(time, force)
                else:
                    await self._async_control_cooler(time, force)

            case HVACMode.FAN_ONLY:
                if self.cooler_device.is_active:
                    await self.cooler_device.async_turn_off()
                await self.fan_device.async_control_hvac(time, force)
                self.HVACActionReason = self.fan_device.HVACActionReason
            case HVACMode.OFF:
                await self.async_turn_off_all(time=time)
                self.HVACActionReason = HVACActionReason.NONE
            case _:
                if self._hvac_mode is not None:
                    _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)

    async def _async_control_when_fan_on_with_cooler(self, time=None, force=False):
        await self.fan_device.async_control_hvac(time, force)
        await self.cooler_device.async_control_hvac(time, force)
        self.HVACActionReason = self.cooler_device.HVACActionReason

    async def _async_control_cooler(self, time=None, force=False):
        is_within_fan_tolerance = self.environment.is_within_fan_tolerance(
            self.fan_device.target_env_attr
        )
        is_warmer_outside = self.environment.is_warmer_outside
        is_fan_air_outside = self.fan_device.fan_air_surce_outside

        # If the fan_hot_tolerance is set, enforce the action for the fan or cooler device
        # to ignore cycles as we switch between the fan and cooler device
        # and we want to avoid idle time gaps between the devices
        force_override = (
            True if self.environment.fan_hot_tolerance is not None else force
        )

        has_cooler_run_long_enough = (
            self.cooler_device.hvac_controller.ran_long_enough()
        )

        if self.cooler_device.is_on and not has_cooler_run_long_enough:
            _LOGGER.debug(
                "Cooler has not run long enough at: %s",
                datetime.now(timezone.utc),
            )
            self.HVACActionReason = HVACActionReason.MIN_CYCLE_DURATION_NOT_REACHED
            return

        if (
            self._fan_hot_tolerance_on
            and is_within_fan_tolerance
            and not (is_fan_air_outside and is_warmer_outside)
        ):
            _LOGGER.debug("within fan tolerance")
            _LOGGER.debug("fan_hot_tolerance_on: %s", self._fan_hot_tolerance_on)
            _LOGGER.debug("force_override: %s", force_override)

            self.fan_device.hvac_mode = HVACMode.FAN_ONLY
            await self.fan_device.async_control_hvac(time, force_override)
            if self.cooler_device.is_active:
                await self.cooler_device.async_turn_off()
            self.HVACActionReason = HVACActionReason.TARGET_TEMP_NOT_REACHED_WITH_FAN
        else:
            _LOGGER.debug("outside fan tolerance")
            _LOGGER.debug("fan_hot_tolerance_on: %s", self._fan_hot_tolerance_on)
            await self.cooler_device.async_control_hvac(time, force_override)
            if self.fan_device.is_active:
                await self.fan_device.async_turn_off()
            self.HVACActionReason = self.cooler_device.HVACActionReason
