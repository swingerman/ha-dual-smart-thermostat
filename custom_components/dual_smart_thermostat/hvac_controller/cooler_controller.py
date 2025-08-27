from datetime import timedelta
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

from ..hvac_controller.generic_controller import GenericHvacController
from ..managers.environment_manager import EnvironmentManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class CoolerHvacController(GenericHvacController):

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id,
        min_cycle_duration: timedelta,
        environment: EnvironmentManager,
        openings: OpeningManager,
        turn_on_callback: Callable,
        turn_off_callback: Callable,
    ) -> None:
        self._controller_type = self.__class__.__name__

        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            turn_on_callback,
            turn_off_callback,
        )
