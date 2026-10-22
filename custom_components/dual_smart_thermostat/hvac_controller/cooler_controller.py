from datetime import timedelta
import logging
from typing import Callable

from ..hvac_controller.generic_controller import GenericHvacController
from ..hvac_device.entity_port import EntityPort
from ..managers.environment_manager import EnvironmentManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class CoolerHvacController(GenericHvacController):

    def __init__(
        self,
        port: EntityPort,
        min_cycle_duration: timedelta,
        environment: EnvironmentManager,
        openings: OpeningManager,
        turn_on_callback: Callable,
        turn_off_callback: Callable,
    ) -> None:
        self._controller_type = self.__class__.__name__

        super().__init__(
            port,
            min_cycle_duration,
            environment,
            openings,
            turn_on_callback,
            turn_off_callback,
        )
