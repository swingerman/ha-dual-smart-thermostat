from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import (
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_ON_WITH_AC,
    CONF_HEATER,
    CONF_INITIAL_HVAC_MODE,
    CONF_MIN_DUR,
)
from custom_components.dual_smart_thermostat.hvac_device.controllable_hvac_device import (
    ControlableHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.cooler_device import (
    CoolerDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.cooler_fan_device import (
    CoolerFanDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.fan_device import FanDevice
from custom_components.dual_smart_thermostat.hvac_device.heater_aux_heater_device import (
    HeaterAUXHeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_cooler_device import (
    HeaterCoolerDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_device import (
    HeaterDevice,
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


class HVACDeviceFactory:

    def __init__(
        self, hass: HomeAssistant, config: ConfigType, features: FeatureManager
    ) -> None:

        self.hass = hass
        self._features = features

        self._heater_entity_id = config[CONF_HEATER]
        if cooler_entity_id := config.get(CONF_COOLER):
            if cooler_entity_id == self._heater_entity_id:
                _LOGGER.warning(
                    "'cooler' entity cannot be equal to 'heater' entity. "
                    "'cooler' entity will be ignored"
                )
                self._cooler_entity_id = None
            else:
                self._cooler_entity_id = cooler_entity_id

        self._fan_entity_id = config.get(CONF_FAN)
        self._fan_on_with_cooler = config.get(CONF_FAN_ON_WITH_AC)

        self._aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self._aux_heater_dual_mode = config.get(CONF_AUX_HEATING_DUAL_MODE)
        self._aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)

        self._min_cycle_duration: timedelta = config.get(CONF_MIN_DUR)

        self._initial_hvac_mode = config.get(CONF_INITIAL_HVAC_MODE)

    def create_device(
        self, environment: EnvironmentManager, openings: OpeningManager
    ) -> ControlableHVACDevice:

        self.environment = environment

        if self._features.is_configured_for_fan_only_mode:
            _LOGGER.info(
                "Creating FanDevice device, _is_configured_for_fan_only_mode: %s",
                self._features.is_configured_for_fan_only_mode,
            )
            return FanDevice(
                self.hass,
                self._heater_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        if (
            self._features.is_configured_for_cooler_mode
            and not self._features.is_configured_for_fan_mode
        ):
            _LOGGER.info(
                "Creating Cooler device, _is_configured_for_cooler_mode: %s, _is_configured_for_fan_mode: %s",
                True,
                False,
            )
            return CoolerDevice(
                self.hass,
                self._heater_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        elif (
            self._features.is_configured_for_cooler_mode
            and self._features.is_configured_for_fan_mode
        ):
            cooler_device = CoolerDevice(
                self.hass,
                self._heater_entity_id,
                self._min_cycle_duration,
                None,
                environment,
                openings,
                self._features,
            )
            fan_device = FanDevice(
                self.hass,
                self._fan_entity_id,
                self._min_cycle_duration,
                None,
                environment,
                openings,
                self._features,
            )

            _LOGGER.info(
                "Creating CoolerFanDevice device, _is_configured_for_cooler_mode: %s, _is_configured_for_fan_mode: %s",
                self._features.is_configured_for_cooler_mode,
                self._features.is_configured_for_fan_mode,
            )

            return CoolerFanDevice(
                self.hass,
                cooler_device,
                fan_device,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        elif self._features.is_configured_for_dual_mode:
            return self._create_heat_cool_device(environment, openings)
        else:
            return self._create_heater_device(environment, openings)

    def _create_heater_device(
        self, environment: EnvironmentManager, openings: OpeningManager
    ) -> HeaterDevice:
        heater_device = HeaterDevice(
            self.hass,
            self._heater_entity_id,
            self._min_cycle_duration,
            self._initial_hvac_mode,
            environment,
            openings,
            self._features,
        )
        if self._features.is_configured_for_aux_heating_mode:
            aux_heater_device = HeaterDevice(
                self.hass,
                self._aux_heater_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )
            return HeaterAUXHeaterDevice(
                self.hass,
                heater_device,
                aux_heater_device,
                self._aux_heater_timeout,
                self._aux_heater_dual_mode,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )
        _LOGGER.info(
            "Creating HeaterDevice device, _is_configured_for_aux_heating_mode: %s",
            self._features.is_configured_for_aux_heating_mode,
        )
        return heater_device

    def _create_heat_cool_device(
        self, environment: EnvironmentManager, openings: OpeningManager
    ) -> HeaterDevice:
        heater_device = HeaterDevice(
            self.hass,
            self._heater_entity_id,
            self._min_cycle_duration,
            self._initial_hvac_mode,
            environment,
            openings,
            self._features,
        )

        if self._features.is_configured_for_aux_heating_mode:
            aux_heater_device = HeaterDevice(
                self.hass,
                self._aux_heater_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )
            return HeaterAUXHeaterDevice(
                self.hass,
                heater_device,
                aux_heater_device,
                self._aux_heater_timeout,
                self._aux_heater_dual_mode,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        cooler_device = CoolerDevice(
            self.hass,
            self._cooler_entity_id,
            self._min_cycle_duration,
            self._initial_hvac_mode,
            environment,
            openings,
            self._features,
        )

        cooler_fan_device = None

        if self._features.is_configured_for_fan_mode:
            fan_device = FanDevice(
                self.hass,
                self._fan_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )
            cooler_fan_device = CoolerFanDevice(
                self.hass,
                cooler_device,
                fan_device,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        _LOGGER.info(
            "Creating HeaterCoolerDevice device, _is_configured_for_heat_cool_mode: %s, %s. %s",
            self._features.is_configured_for_heat_cool_mode,
            heater_device,
            cooler_fan_device if cooler_fan_device else cooler_device,
        )
        return HeaterCoolerDevice(
            self.hass,
            heater_device,
            cooler_fan_device if cooler_fan_device else cooler_device,
            self._initial_hvac_mode,
            self._features.is_configured_for_heat_cool_mode,
            environment,
            openings,
        )
