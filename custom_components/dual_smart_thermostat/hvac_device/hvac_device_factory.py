from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HEAT_COOL_MODE,
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
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class HVACDeviceFactory:

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:

        self.hass = hass
        self.heater_entity_id = config[CONF_HEATER]
        if cooler_entity_id := config.get(CONF_COOLER):
            if cooler_entity_id == self.heater_entity_id:
                _LOGGER.warning(
                    "'cooler' entity cannot be equal to 'heater' entity. "
                    "'cooler' entity will be ignored"
                )
                self.cooler_entity_id = None
            else:
                self.cooler_entity_id = cooler_entity_id

        self.ac_mode = config.get(CONF_AC_MODE)
        self.fan_mode = config.get(CONF_FAN_MODE)
        self.heat_cool_mode = config.get(CONF_HEAT_COOL_MODE)

        self.fan_entity_id = config.get(CONF_FAN)
        self.fan_on_with_cooler = config.get(CONF_FAN_ON_WITH_AC)
        self.fan_tolerance = config.get(CONF_FAN_HOT_TOLERANCE)

        self.aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self.aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)
        self.aux_heater_dual_mode = config.get(CONF_AUX_HEATING_DUAL_MODE)

        self.min_cycle_duration: timedelta = config.get(CONF_MIN_DUR)

        self.initial_hvac_mode = config.get(CONF_INITIAL_HVAC_MODE)

    def create_device(
        self, temperatures: TemperatureManager, openings: OpeningManager
    ) -> ControlableHVACDevice:

        self.temperatures = temperatures

        if self._is_configured_for_fan_only_mode:
            _LOGGER.debug(
                "Creating FanDevice device, _is_configured_for_fan_only_mode: %s",
                self._is_configured_for_fan_only_mode,
            )
            return FanDevice(
                self.hass,
                self.heater_entity_id,
                self.min_cycle_duration,
                self.initial_hvac_mode,
                temperatures,
                openings,
            )

        if self._is_configured_for_cooler_mode and not self._is_configured_for_fan_mode:
            _LOGGER.debug(
                "Creating Cooler device, _is_configured_for_cooler_mode: %s, _is_configured_for_fan_mode: %s",
                True,
                False,
            )
            return CoolerDevice(
                self.hass,
                self.heater_entity_id,
                self.min_cycle_duration,
                self.initial_hvac_mode,
                temperatures,
                openings,
            )

        elif self._is_configured_for_cooler_mode and self._is_configured_for_fan_mode:
            cooler_device = CoolerDevice(
                self.hass,
                self.heater_entity_id,
                self.min_cycle_duration,
                None,
                temperatures,
                openings,
            )
            fan_device = FanDevice(
                self.hass,
                self.fan_entity_id,
                self.min_cycle_duration,
                None,
                temperatures,
                openings,
            )

            _LOGGER.debug(
                "Creating CoolerFanDevice device, _is_configured_for_cooler_mode: %s, _is_configured_for_fan_mode: %s",
                self._is_configured_for_cooler_mode,
                self._is_configured_for_fan_mode,
            )

            return CoolerFanDevice(
                self.hass,
                cooler_device,
                fan_device,
                self.initial_hvac_mode,
                temperatures,
                openings,
                fan_on_with_cooler=self.fan_on_with_cooler,
            )
        elif self._is_configured_for_heat_cool_mode:
            return self._create_heat_cool_device(temperatures, openings)
        else:
            return self._create_heater_device(temperatures, openings)

    def _create_heater_device(
        self, temperatures: TemperatureManager, openings: OpeningManager
    ) -> HeaterDevice:
        heater_device = HeaterDevice(
            self.hass,
            self.heater_entity_id,
            self.min_cycle_duration,
            self.initial_hvac_mode,
            temperatures,
            openings,
        )
        if self._is_configured_for_aux_heating_mode:
            aux_heater_device = HeaterDevice(
                self.hass,
                self.aux_heater_entity_id,
                self.min_cycle_duration,
                self.initial_hvac_mode,
                temperatures,
                openings,
            )
            return HeaterAUXHeaterDevice(
                self.hass,
                heater_device,
                aux_heater_device,
                self.aux_heater_timeout,
                self.aux_heater_dual_mode,
                self.initial_hvac_mode,
                temperatures,
                openings,
            )
        _LOGGER.debug(
            "Creating HeaterDevice device, _is_configured_for_aux_heating_mode: %s",
            self._is_configured_for_aux_heating_mode,
        )
        return heater_device

    def _create_heat_cool_device(
        self, temperatures: TemperatureManager, openings: OpeningManager
    ) -> HeaterDevice:
        heater_device = HeaterDevice(
            self.hass,
            self.heater_entity_id,
            self.min_cycle_duration,
            self.initial_hvac_mode,
            temperatures,
            openings,
            range_mode=True,
        )

        if self._is_configured_for_aux_heating_mode:
            aux_heater_device = HeaterDevice(
                self.hass,
                self.aux_heater_entity_id,
                self.min_cycle_duration,
                self.initial_hvac_mode,
                temperatures,
                openings,
                range_mode=True,
            )
            return HeaterAUXHeaterDevice(
                self.hass,
                heater_device,
                aux_heater_device,
                self.aux_heater_timeout,
                self.aux_heater_dual_mode,
                self.initial_hvac_mode,
                temperatures,
                openings,
            )

        cooler_device = CoolerDevice(
            self.hass,
            self.cooler_entity_id,
            self.min_cycle_duration,
            self.initial_hvac_mode,
            temperatures,
            openings,
            range_mode=True,
        )

        cooler_fan_device = None

        if self._is_configured_for_fan_mode:
            fan_device = FanDevice(
                self.hass,
                self.fan_entity_id,
                self.min_cycle_duration,
                self.initial_hvac_mode,
                temperatures,
                openings,
                range_mode=True,
            )
            cooler_fan_device = CoolerFanDevice(
                self.hass,
                cooler_device,
                fan_device,
                self.initial_hvac_mode,
                temperatures,
                openings,
                fan_on_with_cooler=self.fan_on_with_cooler,
            )

        _LOGGER.debug(
            "Creating HeaterCoolerDevice device, _is_configured_for_heat_cool_mode: %s, %s. %s",
            self._is_configured_for_heat_cool_mode,
            heater_device,
            cooler_fan_device if cooler_fan_device else cooler_device,
        )
        return HeaterCoolerDevice(
            self.hass,
            heater_device,
            cooler_fan_device if cooler_fan_device else cooler_device,
            self.initial_hvac_mode,
            temperatures,
            openings,
        )

    @property
    def _is_configured_for_cooler_mode(self) -> bool:
        """Determines if the cooler mode is configured."""
        return self.heater_entity_id is not None and self.ac_mode is True

    @property
    def _is_configured_for_fan_only_mode(self) -> bool:
        """Determines if the fan mode is configured."""
        return (
            self.heater_entity_id is not None
            and self.fan_mode is True
            and self.fan_entity_id is None
        )

    @property
    def _is_configured_for_fan_mode(self) -> bool:
        """Determines if the fan mode is configured."""
        return self.fan_entity_id is not None

    @property
    def _is_configured_fan_mode_tolerance(self) -> bool:
        """Determines if the fan mode is configured."""
        return self._is_configured_for_fan_mode() and self.fan_tolerance is not None

    @property
    def _is_configured_for_aux_heating_mode(self) -> bool:
        """Determines if the aux heater is configured."""
        if self.aux_heater_entity_id is None:
            return False

        if self.aux_heater_timeout is None:
            return False

        return True

    @property
    def _is_configured_for_heat_cool_mode(self) -> bool:
        """Determines if the aux heater is configured."""
        return (
            self.heat_cool_mode
            or (
                hasattr(self, "cooler_entity_id")
                and self.cooler_entity_id is not None
                and self.heater_entity_id is not None
            )
            or (
                self.temperatures.target_temp_high is not None
                and self.temperatures.target_temp_low is not None
            )
        )
