import logging

from homeassistant.components.climate import HVACMode

from custom_components.dual_smart_thermostat.hvac_device.cooler_device import (
    CoolerDevice,
)

_LOGGER = logging.getLogger(__name__)


class FanDevice(CoolerDevice):

    hvac_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
    fan_air_surce_outside = False

    def __init__(
        self,
        hass,
        entity_id,
        min_cycle_duration,
        initial_hvac_mode,
        temperatures,
        openings,
        features,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            temperatures,
            openings,
            features,
        )

        if self.features.is_fan_uses_outside_air:
            self.fan_air_surce_outside = True
