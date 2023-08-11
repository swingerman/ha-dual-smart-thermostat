"""Controls Climate devices."""

from abc import ABC
import asyncio
import logging
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.const import HVACMode, ToleranceDevice

_LOGGER = logging.getLogger(__name__)


class ClimateController(ABC):
    """Generic Climate device controller."""

    _target_temp: float

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._temp_lock = asyncio.Lock()

    async def async_control_climate(self, time=None, force=False):
        """Control the climate device."""
        raise NotImplementedError

    def set_temperature(self, temperature: float):
        """Set the temperature."""
        raise NotImplementedError

    def _needs_control(self, time=None, force=False, *, dual=False, cool=False):
        """checks if the controller needs to continue"""
        raise NotImplementedError

    def _ran_long_enough(self, cooler_entity=False):
        """checks if the controller ran long enough"""
        raise NotImplementedError


class CoolerClimateController(ClimateController):
    """Climate device controller for cooling devices."""

    async def async_control_climate(self, time=None, force=False):
        async with self._temp_lock:
            _LOGGER.debug("_async_control_cooling time: %s. force: %s", time, force)

            if not self._needs_control(time, force, cool=True):
                return


class HeaterClimateController(ClimateController):
    """Climate device controller for heating devices."""


class DualClimateController(CoolerClimateController, HeaterClimateController):
    """Climate device controller for devices that can cool and heat."""

    _target_temp_low: float
    _target_temp_high: float
