import logging

from homeassistant.components.climate import HVACAction, HVACMode

from custom_components.dual_smart_thermostat.hvac_device.specific_hvac_device import (
    SpecificHVACDevice,
)

_LOGGER = logging.getLogger(__name__)


class DryerDevice(SpecificHVACDevice):

    _target_env_attr: str = "_target_humidity"

    hvac_modes = [HVACMode.DRY, HVACMode.OFF]

    def __init__(
        self,
        hass,
        entity_id,
        min_cycle_duration,
        initial_hvac_mode,
        environment,
        openings,
        features,
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
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.DRYING
        return HVACAction.IDLE

    def _set_self_active(self) -> None:
        """Checks if active state needs to be set true."""
        _LOGGER.debug("_active: %s", self._active)
        _LOGGER.debug("cur_humidity: %s", self.environment.cur_humidity)
        _LOGGER.debug("target_env_attr: %s", self.target_env_attr)
        target_humidity = getattr(self.environment, self.target_env_attr)
        _LOGGER.debug("target_humidity: %s", target_humidity)

        if (
            not self._active
            and None not in (self.environment.cur_humidity, target_humidity)
            and self._hvac_mode != HVACMode.OFF
        ):
            self._active = True
            _LOGGER.debug(
                "Obtained current and target temperature. Device active. %s, %s",
                self.environment.cur_humidity,
                target_humidity,
            )

    def is_below_target_env_attr(self) -> bool:
        """is too dry?"""
        return self.environment.is_too_dry

    def is_above_target_env_attr(self) -> bool:
        """is too moist?"""
        return self.environment.is_too_moist
