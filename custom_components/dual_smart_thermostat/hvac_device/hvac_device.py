from abc import ABC, abstractmethod
import logging
from typing import Self

from homeassistant.components.climate import HVACMode
from homeassistant.core import Context, HomeAssistant

from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacGoal,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
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


class TargetsEnvironmentAttribute(ABC):

    _target_env_attr: str = "_target_temp"

    @property
    @abstractmethod
    def target_env_attr(self) -> str:
        pass


class HVACDevice:

    _active: bool

    hvac_modes: list[HVACMode]
    hvac_goal: HvacGoal

    def __init__(
        self,
        hass: HomeAssistant,
        environment: EnvironmentManager,
        openings: OpeningManager,
    ) -> None:
        self.hass = hass
        self.environment = environment
        self.openings = openings

        self._hvac_action_reason = None
        self._active = False
        self._hvac_modes = []

    def set_context(self, context: Context):
        self._context = context

    # _hvac_modes are the combined values of the device.hvac_modes without duplicates
    def init_hvac_modes(
        self, hvac_devices: list[Self]
    ):  # list[ControlledHVACDevice] not typed because circular dependency error
        device_hvac_modes = []
        for device in hvac_devices:
            device_hvac_modes = merge_hvac_modes(device.hvac_modes, device_hvac_modes)
        self.hvac_modes = device_hvac_modes
