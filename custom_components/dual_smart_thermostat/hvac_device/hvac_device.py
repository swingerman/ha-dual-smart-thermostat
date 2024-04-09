from abc import ABC, abstractmethod
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import Context, HomeAssistant

from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


def merge_hvac_modes(first: list[HVACMode], second: list[HVACMode]):
    return list(set(first + second))


class Switchable(ABC):
    @abstractmethod
    async def async_turn_on(self):
        pass

    @abstractmethod
    async def async_turn_off(self):
        pass


class HVACDevice:

    _active: bool

    hvac_modes: list[HVACMode]

    def __init__(
        self,
        hass: HomeAssistant,
        temperatures: TemperatureManager,
        openings: OpeningManager,
    ) -> None:
        self.hass = hass
        self.temperatures = temperatures
        self.openings = openings

        self._HVACActionReason = None
        self._active = False
        self._hvac_modes = []

    def set_context(self, context: Context):
        self._context = context
