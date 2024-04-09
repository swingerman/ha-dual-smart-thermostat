import logging

from homeassistant.components.climate import HVACMode

from custom_components.dual_smart_thermostat.hvac_device.cooler_device import (
    CoolerDevice,
)

_LOGGER = logging.getLogger(__name__)


class FanDevice(CoolerDevice):

    hvac_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
