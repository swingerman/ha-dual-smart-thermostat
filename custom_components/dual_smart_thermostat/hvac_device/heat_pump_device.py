from datetime import timedelta
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State, callback

from custom_components.dual_smart_thermostat.hvac_controller.cooler_controller import (
    CoolerHvacController,
)
from custom_components.dual_smart_thermostat.hvac_controller.heater_controller import (
    HeaterHvacConroller,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacEnvStrategy,
    HvacGoal,
)
from custom_components.dual_smart_thermostat.hvac_device.generic_hvac_device import (
    GenericHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    merge_hvac_modes,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
    TargetTemperatures,
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


class HeatPumpDevice(GenericHVACDevice):

    hvac_modes = [HVACMode.OFF]

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
        hvac_power: HvacPowerManager,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
            hvac_power,
            hvac_goal=HvacGoal.RAISE,  # will not take effect as we will define new controllers
        )

        _LOGGER.debug("HeatPumpDevice.__init__")

        self.heating_strategy = HvacEnvStrategy(
            self.is_below_target_env_attr,
            self.is_above_target_env_attr,
            self.target_env_attr_reached_reason,
            self.target_env_attr_not_reached_reason,
            HvacGoal.RAISE,
        )

        self.cooling_strategy = HvacEnvStrategy(
            self.is_below_target_env_attr,
            self.is_above_target_env_attr,
            self.target_env_attr_reached_reason,
            self.target_env_attr_not_reached_reason,
            HvacGoal.LOWER,
        )

        self.heating_controller = HeaterHvacConroller(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

        self.cooling_controller = CoolerHvacController(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

        # HEAT or COOL mode availabiiity is determined by the current state of the
        # het pumps current mode provided by the CONF_HEAT_PUMP_COOLING inputs' state
        # If the heat pump is currently in cooling mode, then the device will support
        # COOL mode, and vice versa for HEAT mode

        self._apply_heat_pump_cooling_state()

        if features.is_configured_for_heat_cool_mode:
            self.hvac_modes = merge_hvac_modes(self.hvac_modes, [HVACMode.HEAT_COOL])

    @property
    def target_env_attr(self) -> str:

        if self.features.is_range_mode:
            if self._heat_pump_is_cooling:
                return "_target_temp_high"
            else:
                return "_target_temp_low"
        else:
            return self._target_env_attr

    @callback
    def on_entity_state_changed(self, entity_id: str, new_state: State) -> None:
        """Hndles state change of the heat pump cooling entity. In order to determine
        if the heat pump is currently in cooling mode."""

        super().on_entity_state_change(entity_id, new_state)

        if (
            self.features.heat_pump_cooling_entity_id is None
            or entity_id != self.features.heat_pump_cooling_entity_id
        ):
            return

        _LOGGER.info("Handling heat_pump_cooling_entity_id state change")

        self._apply_heat_pump_cooling_state(new_state)

    def _apply_heat_pump_cooling_state(self, state: State = None) -> None:
        """Applies the state of the heat pump cooling entity to the device."""
        _LOGGER.debug("Applying heat pump cooling state, state: %s", state)
        entity_id = self.features.heat_pump_cooling_entity_id
        entity_state = state or self.hass.states.get(entity_id)

        _LOGGER.debug(
            "Heat pump cooling entity state: %s, %s",
            entity_id,
            entity_state,
        )

        if entity_state and entity_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):

            self._heat_pump_is_cooling = entity_state.state == STATE_ON
        else:
            _LOGGER.warning(
                "Heat pump cooling entity state is unknown or unavailable: %s",
                entity_state,
            )
            self._heat_pump_is_cooling = False

        _LOGGER.debug("Heat pump is cooling applied: %s", self._heat_pump_is_cooling)

        self._change_hvac_strategy(self._heat_pump_is_cooling)
        self._change_hvac_modes(self._heat_pump_is_cooling)
        self._change_hvac_mode(self._heat_pump_is_cooling)

    def _change_hvac_strategy(self, heat_pump_is_cooling: bool) -> None:
        """Changes the HVAC strategy based on the heat pump's current mode."""

        if heat_pump_is_cooling:
            self.strategy = self.cooling_strategy
            self.hvac_controller = self.cooling_controller

        else:
            self.strategy = self.heating_strategy
            self.hvac_controller = self.heating_controller

    def _change_hvac_modes(self, heat_pump_is_cooling: bool) -> None:
        """Changes the HVAC modes based on the heat pump's current mode."""
        hvac_mode_set = set(self.hvac_modes)
        if heat_pump_is_cooling:
            _LOGGER.debug(
                "Heat pump is cooling, discarding HEAT mode and adding COOL mode"
            )
            hvac_mode_set.discard(HVACMode.HEAT)
            hvac_mode_set.add(HVACMode.COOL)
            self.hvac_modes = list(hvac_mode_set)

        else:
            _LOGGER.debug(
                "Heat pump is heating, discarding COOL mode and adding HEAT mode"
            )
            hvac_mode_set.discard(HVACMode.COOL)
            hvac_mode_set.add(HVACMode.HEAT)
            self.hvac_modes = list(hvac_mode_set)

    def _change_hvac_mode(self, heat_pump_is_cooling: bool) -> None:
        """Changes the HVAC mode based on the heat pump's current mode."""
        _LOGGER.debug(
            "Changing hvac mode based on heat pump mode, heat_pump_is_cooling: %s, hvac_mode: %s, hvac_modes: %s",
            heat_pump_is_cooling,
            self.hvac_mode,
            self.hvac_modes,
        )
        if (
            self.hvac_mode is not None
            and self.hvac_mode is not HVACMode.OFF
            and self.hvac_mode not in self.hvac_modes
        ):
            if heat_pump_is_cooling:
                self.hvac_mode = HVACMode.COOL
            else:
                self.hvac_mode = HVACMode.HEAT
        _LOGGER.debug("Changed hvac mode based on heat pump mode: %s", self.hvac_mode)

    # override
    def on_target_temperature_change(self, temperatures: TargetTemperatures) -> None:
        super().on_target_temperature_change(temperatures)

        # handle if het_pump is configured and we are in heat_cool mode
        # and the range is set to the value that doesn't make sens for the current
        # heat pump mode.
        if not self.features.is_range_mode:
            return

        current_temp = self.environment.cur_temp
        if current_temp is None:
            _LOGGER.warning("Current temperature is None")
            return

        if self._heat_pump_is_cooling:
            if temperatures.temp_low > current_temp:
                _LOGGER.warning(
                    "Heat pump is in cooling mode, setting the lower target temperature makes no effect until the het pump switches to heating mode"
                )
        else:
            _LOGGER.warning(
                "temp_high: %s, current_temp: %s", temperatures.temp_high, current_temp
            )
            if temperatures.temp_high < current_temp:
                _LOGGER.warning(
                    "Heat pump is in heating mode, setting the higher target temperature makes no effect until the het pump switches to cooling mode"
                )
