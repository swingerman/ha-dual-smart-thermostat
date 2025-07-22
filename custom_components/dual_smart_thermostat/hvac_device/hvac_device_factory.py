from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import (
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_ON_WITH_AC,
    CONF_HEAT_PUMP_COOLING,
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
from custom_components.dual_smart_thermostat.hvac_device.dryer_device import DryerDevice
from custom_components.dual_smart_thermostat.hvac_device.fan_device import FanDevice
from custom_components.dual_smart_thermostat.hvac_device.heat_pump_device import (
    HeatPumpDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_aux_heater_device import (
    HeaterAUXHeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_cooler_device import (
    HeaterCoolerDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_device import (
    HeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_cooler_device import (
    MultiCoolerDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_heater_device import (
    MultiHeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_hvac_device import (
    MultiHvacDevice,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.hvac_power_manager import (
    HvacPowerManager,
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

        self._heater_entity_ids = config[CONF_HEATER]
        # Ensure heater_entity_ids is always a list for consistent handling
        if isinstance(self._heater_entity_ids, str):
            self._heater_entity_ids = [self._heater_entity_ids]

        self._cooler_entity_ids = None
        if cooler_entity_ids := config.get(CONF_COOLER):
            # Ensure cooler_entity_ids is always a list for consistent handling
            if isinstance(cooler_entity_ids, str):
                cooler_entity_ids = [cooler_entity_ids]
            
            # Check for conflicts with heater entities
            heater_set = set(self._heater_entity_ids)
            cooler_set = set(cooler_entity_ids)
            if heater_set & cooler_set:
                _LOGGER.warning(
                    "'cooler' entities cannot overlap with 'heater' entities. "
                    "Overlapping entities will be ignored: %s",
                    heater_set & cooler_set,
                )
                # Remove overlapping entities from cooler list
                self._cooler_entity_ids = [
                    entity_id for entity_id in cooler_entity_ids 
                    if entity_id not in heater_set
                ]
                if not self._cooler_entity_ids:
                    self._cooler_entity_ids = None
            else:
                self._cooler_entity_ids = cooler_entity_ids

        self._fan_entity_id = config.get(CONF_FAN)
        self._fan_on_with_cooler = config.get(CONF_FAN_ON_WITH_AC)

        self._dryer_entity_id = config.get(CONF_DRYER)
        self._heat_pump_cooling_entity_id = config.get(CONF_HEAT_PUMP_COOLING)

        self._aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self._aux_heater_dual_mode = config.get(CONF_AUX_HEATING_DUAL_MODE)
        self._aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)

        self._min_cycle_duration: timedelta = config.get(CONF_MIN_DUR)

        self._initial_hvac_mode = config.get(CONF_INITIAL_HVAC_MODE)

    def create_device(
        self,
        environment: EnvironmentManager,
        openings: OpeningManager,
        hvac_power: HvacPowerManager,
    ) -> ControlableHVACDevice:

        dryer_device = None
        fan_device = None
        cooler_device = None
        heater_device = None
        aux_heater_device = None

        if self._features.is_configured_for_dryer_mode:
            dryer_device = DryerDevice(
                self.hass,
                self._dryer_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
            )

        if self._features.is_configured_for_fan_only_mode:
            fan_device = FanDevice(
                self.hass,
                self._heater_entity_ids[0],  # Fan only mode uses single entity
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
            )

        if self._features.is_configured_for_fan_mode:
            fan_device = FanDevice(
                self.hass,
                self._fan_entity_id,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
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
                hvac_power,
            )

        if self._features.is_configured_for_dual_mode:
            cooler_entity_ids = self._cooler_entity_ids
        else:
            cooler_entity_ids = self._heater_entity_ids

        if (
            self._features.is_configured_for_cooler_mode
            or self._cooler_entity_ids is not None
        ):
            cooler_device = self._create_cooler_device(
                environment, openings, hvac_power, cooler_entity_ids, fan_device
            )

        if self._features.is_configured_for_heat_pump_mode:
            heater_device = HeatPumpDevice(
                self.hass,
                self._heater_entity_ids[0],  # Heat pump uses single entity
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
            )

        if (
            self._heater_entity_ids
            and not self._features.is_configured_for_cooler_mode
            and not self._features.is_configured_for_fan_only_mode
            and not self._features.is_configured_for_heat_pump_mode
        ):
            """Create a heater device if no other specific device is configured"""
            if len(self._heater_entity_ids) == 1:
                # Single heater entity - use original HeaterDevice
                heater_device = HeaterDevice(
                    self.hass,
                    self._heater_entity_ids[0],
                    self._min_cycle_duration,
                    self._initial_hvac_mode,
                    environment,
                    openings,
                    self._features,
                    hvac_power,
                )
            else:
                # Multiple heater entities - use MultiHeaterDevice
                heater_device = MultiHeaterDevice(
                    self.hass,
                    self._heater_entity_ids,
                    self._min_cycle_duration,
                    self._initial_hvac_mode,
                    environment,
                    openings,
                    self._features,
                    hvac_power,
                )

        if aux_heater_device and heater_device:
            _LOGGER.info("Creating heater aux heater device")
            heater_device = HeaterAUXHeaterDevice(
                self.hass,
                [heater_device, aux_heater_device],
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        _LOGGER.debug(
            "heater_device: %s, cooler_device: %s", heater_device, cooler_device
        )

        if heater_device is not None and cooler_device is not None:
            _LOGGER.info("Creating heater cooler device")
            heater_cooler_device = HeaterCoolerDevice(
                self.hass,
                [heater_device, cooler_device],
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

            if dryer_device:
                return MultiHvacDevice(
                    self.hass,
                    [heater_cooler_device, dryer_device],
                    self._initial_hvac_mode,
                    environment,
                    openings,
                    self._features,
                )
            else:
                return heater_cooler_device

        if heater_device:
            if dryer_device:
                return MultiHvacDevice(
                    self.hass,
                    [heater_device, dryer_device],
                    self._initial_hvac_mode,
                    environment,
                    openings,
                    self._features,
                )
            else:
                return heater_device

        if cooler_device:
            if dryer_device:
                return MultiHvacDevice(
                    self.hass,
                    [cooler_device, dryer_device],
                    self._initial_hvac_mode,
                    environment,
                    openings,
                    self._features,
                )
            else:
                return cooler_device

        if fan_device:
            return fan_device

    def _create_cooler_device(
        self,
        environment: EnvironmentManager,
        openings: OpeningManager,
        hvac_power: HvacPowerManager,
        cooler_entity_ids: list[str] | None,
        fan_device: FanDevice | None,
    ) -> CoolerDevice:

        if not cooler_entity_ids:
            return None

        if len(cooler_entity_ids) == 1:
            # Single cooler entity - use original CoolerDevice
            cooler_device = CoolerDevice(
                self.hass,
                cooler_entity_ids[0],
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
            )
        else:
            # Multiple cooler entities - use MultiCoolerDevice
            cooler_device = MultiCoolerDevice(
                self.hass,
                cooler_entity_ids,
                self._min_cycle_duration,
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
                hvac_power,
            )

        if fan_device:
            cooler_device = CoolerFanDevice(
                self.hass,
                [cooler_device, fan_device],
                self._initial_hvac_mode,
                environment,
                openings,
                self._features,
            )

        return cooler_device
