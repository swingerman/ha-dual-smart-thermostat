from datetime import timedelta
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_controller.generic_controller import (
    GenericHvacController,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacController,
    HvacEnvStrategy,
    HvacGoal,
)
from custom_components.dual_smart_thermostat.hvac_device.controllable_hvac_device import (
    ControlableHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    HVACDevice,
    Switchable,
    TargetsEnvironmentAttribute,
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


class GenericHVACDevice(
    HVACDevice, ControlableHVACDevice, Switchable, TargetsEnvironmentAttribute
):

    _target_env_attr: str = "_target_temp"
    hvac_controller: HvacController
    strategy: HvacEnvStrategy

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
        hvac_goal: HvacGoal,
    ) -> None:
        super().__init__(hass, environment, openings)
        self._device_type = self.__class__.__name__

        # the hvac goal controls the hvac strategy
        # it will decide to raise or lower the temperature, humidity or othet target attribute
        self.hvac_goal = hvac_goal

        self.features = features
        self.hvac_power = hvac_power
        self.entity_id = entity_id
        self.min_cycle_duration = min_cycle_duration

        self.hvac_controller: HvacController = GenericHvacController(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

        self.strategy = HvacEnvStrategy(
            self.is_below_target_env_attr,
            self.is_above_target_env_attr,
            self.target_env_attr_reached_reason,
            self.target_env_attr_not_reached_reason,
            self.hvac_goal,
        )

        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
        else:
            self._hvac_mode = None

    def set_context(self, context: Context):
        self._context = context

    def get_device_ids(self) -> list[str]:
        return [self.entity_id]

    @property
    def _entity_state(self) -> str:
        return self.hass.states.get(self.entity_id)

    @property
    def _is_valve(self) -> bool:
        domain = self._entity_state.domain if self._entity_state else None
        return domain == VALVE_DOMAIN

    @property
    def _entity_features(self) -> int:
        return (
            self.hass.states.get(self.entity_id).attributes.get("supported_features")
            if self._entity_state
            else 0
        )

    @property
    def _supports_open_valve(self) -> bool:
        _LOGGER.debug("entity_features: %s", self._entity_features)
        return self._is_valve and self._entity_features & ValveEntityFeature.OPEN

    @property
    def _supports_close_valve(self) -> bool:
        return self._is_valve and self._entity_features & ValveEntityFeature.CLOSE

    @property
    def target_env_attr(self) -> str:
        return self._target_env_attr

    @property
    def is_active(self) -> bool:
        """If the toggleable hvac device is currently active."""
        return self.hvac_controller.is_active

    def is_below_target_env_attr(self) -> bool:
        """is too cold?"""
        return self.environment.is_too_cold(self.target_env_attr)

    def is_above_target_env_attr(self) -> bool:
        """is too hot?"""
        return self.environment.is_too_hot(self.target_env_attr)

    def target_env_attr_reached_reason(self) -> HVACActionReason:
        return HVACActionReason.TARGET_TEMP_REACHED

    def target_env_attr_not_reached_reason(self) -> HVACActionReason:
        return HVACActionReason.TARGET_TEMP_NOT_REACHED

    def _set_self_active(self) -> None:
        """Checks if active state needs to be set true."""

        target_temp = getattr(self.environment, self.target_env_attr)

        _LOGGER.debug("_active: %s", self._active)
        _LOGGER.debug("cur_temp: %s", self.environment.cur_temp)
        _LOGGER.debug("target_env_attr: %s", self.target_env_attr)
        _LOGGER.debug("hvac_mode: %s", self.hvac_mode)
        _LOGGER.debug("target_temp: %s", target_temp)

        if (
            not self._active
            and None not in (self.environment.cur_temp, target_temp)
            and self._hvac_mode != HVACMode.OFF
        ):
            self._active = True
            _LOGGER.debug(
                "Obtained current and target temperature. Device active. %s, %s",
                self.environment.cur_temp,
                target_temp,
            )

    async def async_control_hvac(self, time=None, force=False):
        """Controls the HVAC of the device."""

        _LOGGER.debug(
            "%s - async_control_hvac time: %s. force: %s",
            self._device_type,
            time,
            force,
        )

        self._set_self_active()

        _LOGGER.debug(
            "needs_control: %s",
            self.hvac_controller.needs_control(
                self._active, self.hvac_mode, time, force
            ),
        )

        if not self.hvac_controller.needs_control(
            self._active, self.hvac_mode, time, force
        ):
            return

        any_opeing_open = self.openings.any_opening_open(self.hvac_mode)

        _LOGGER.debug(
            "%s - async_control_hvac - is device active: %s, %s, strategy: %s, is opening open: %s",
            self._device_type,
            self.entity_id,
            self.hvac_controller.is_active,
            self.strategy,
            any_opeing_open,
        )

        if self.hvac_controller.is_active:
            await self.hvac_controller.async_control_device_when_on(
                self.strategy,
                any_opeing_open,
                time,
            )
        else:
            await self.hvac_controller.async_control_device_when_off(
                self.strategy,
                any_opeing_open,
                time,
            )

        self._hvac_action_reason = self.hvac_controller.hvac_action_reason
        self.hvac_power.update_hvac_power(self.strategy, self.target_env_attr)

    async def async_on_startup(self):
        entity_state = self.hass.states.get(self.entity_id)
        if entity_state and entity_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self.hass.loop.create_task(self._async_check_device_initial_state())

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        if self._hvac_mode == HVACMode.OFF and self.hvac_controller.is_active:
            _LOGGER.warning(
                "The climate mode is OFF, but the switch device is ON. Turning off device %s",
                self.entity_id,
            )
            await self.async_turn_off()

    async def async_turn_on(self):
        _LOGGER.info(
            "%s. Turning on or opening entity %s",
            self.__class__.__name__,
            self.entity_id,
        )

        if self.entity_id is None:
            return

        if self._supports_open_valve:
            await self._async_open_valve_entity()
        else:
            await self._async_turn_on_entity()

    async def async_turn_off(self):
        _LOGGER.info(
            "%s. Turning off or closing entity %s",
            self.__class__.__name__,
            self.entity_id,
        )
        if self.entity_id is None:
            return

        if self._supports_close_valve:
            await self._async_close_valve_entity()
        else:
            await self._async_turn_off_entity()

    async def _async_turn_on_entity(self) -> None:
        """Turn on the entity."""
        _LOGGER.info(
            "%s. Turning on entity %s", self.__class__.__name__, self.entity_id
        )

        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_OFF
        ):
            await self.hass.services.async_call(
                HA_DOMAIN,
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self.entity_id},
                context=self._context,
            )

    async def _async_turn_off_entity(self) -> None:
        """Turn off the entity."""
        _LOGGER.info(
            "%s. Turning off entity %s", self.__class__.__name__, self.entity_id
        )

        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_ON
        ):
            await self.hass.services.async_call(
                HA_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self.entity_id},
                context=self._context,
            )

    async def _async_open_valve_entity(self) -> None:
        """Open the entity."""
        _LOGGER.info("%s. Opening entity %s", self.__class__.__name__, self.entity_id)

        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_CLOSED
        ):
            await self.hass.services.async_call(
                HA_DOMAIN,
                SERVICE_OPEN_VALVE,
                {ATTR_ENTITY_ID: self.entity_id},
                context=self._context,
            )

    async def _async_close_valve_entity(self) -> None:
        """Close the entity."""
        _LOGGER.info("%s. Closing entity %s", self.__class__.__name__, self.entity_id)

        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, STATE_OPEN
        ):
            await self.hass.services.async_call(
                HA_DOMAIN,
                SERVICE_CLOSE_VALVE,
                {ATTR_ENTITY_ID: self.entity_id},
                context=self._context,
            )
