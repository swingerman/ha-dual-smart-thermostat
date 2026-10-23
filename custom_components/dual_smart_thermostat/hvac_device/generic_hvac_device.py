from abc import abstractmethod
from datetime import timedelta
import logging
from typing import Callable

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant

from ..const import ControlStyle
from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_controller.generic_controller import GenericHvacController
from ..hvac_controller.hvac_controller import HvacController, HvacEnvStrategy, HvacGoal
from ..hvac_device.controllable_hvac_device import ControlableHVACDevice
from ..hvac_device.entity_port import make_port
from ..hvac_device.hvac_device import (
    HVACDevice,
    Switchable,
    TargetsEnvironmentAttribute,
)
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.hvac_power_manager import HvacPowerManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class GenericHVACDevice(
    HVACDevice, ControlableHVACDevice, Switchable, TargetsEnvironmentAttribute
):

    _target_env_attr: str = "_target_temp"
    # False for roles that tell a climate no temperature (fan, dryer).
    pushes_setpoint: bool = True
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

        self.port = make_port(hass, self)

        self.hvac_controller: HvacController = GenericHvacController(
            self.port,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

        self.strategy = (
            HvacEnvStrategy.self_regulating(
                self.hvac_goal,
                self.target_env_attr_reached_reason,
                self.target_env_attr_not_reached_reason,
            )
            if self.port.self_regulating
            else HvacEnvStrategy(
                self.is_below_target_env_attr,
                self.is_above_target_env_attr,
                self.target_env_attr_reached_reason,
                self.target_env_attr_not_reached_reason,
                self.hvac_goal,
            )
        )

        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
        else:
            self._hvac_mode = None

    def set_context(self, context: Context):
        self._context = context

    def get_device_ids(self) -> list[str]:
        return [self.entity_id]

    def ports(self) -> list:
        return [self.port]

    def set_hold_stops(self, hold: bool) -> None:
        # a heat pump keeps one controller per direction
        controllers = (
            self.hvac_controller,
            getattr(self, "heating_controller", None),
            getattr(self, "cooling_controller", None),
        )
        for controller in controllers:
            if controller is not None:
                controller.hold_stop_for_min_cycle = hold

    @abstractmethod
    def role_modes(self) -> tuple[HVACMode, ...]:
        """Climate modes that count as this role running; the first is commanded."""

    def control_style(self) -> ControlStyle:
        """Only a role that pushes a setpoint can leave the regulating to the child."""
        if self.pushes_setpoint:
            return self.features.climate_control_style
        return ControlStyle.ON_OFF

    def fan_speed(self):
        """The one fan speed target of the thermostat (chosen by the factory)."""
        return self.features.fan_speed

    def setpoint_offset(self) -> float:
        """Offset added to the temperature pushed to a climate entity."""
        return 0.0

    def climate_target(self) -> float | None:
        """The temperature a climate entity serving this role is told to hold."""
        if not self.pushes_setpoint:
            return None
        return getattr(self.environment, self.target_env_attr, None)

    @property
    def target_env_attr(self) -> str:
        return self._target_env_attr

    @property
    def is_active(self) -> bool:
        """If the toggleable hvac device is currently active."""
        return self.hvac_controller.is_active

    # override
    def reset_hvac_action_reason(self) -> None:
        """Clear the controller's copy too - it is the one control re-reads."""
        super().reset_hvac_action_reason()
        self.hvac_controller.hvac_action_reason = HVACActionReason.NONE

    @property
    def is_on(self) -> bool:
        return self.port.is_active

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

        _LOGGER.debug("Check if needs control.")
        if not self.hvac_controller.needs_control(
            self._active, self.hvac_mode, time, force
        ):
            _LOGGER.debug("Control not needed. exit.")
            return

        any_opening_open = self.openings.any_opening_open(self.hvac_mode)

        _LOGGER.debug(
            "%s - async_control_hvac - is device active: %s, %s, strategy: %s, is opening open: %s",
            self._device_type,
            self.entity_id,
            self.hvac_controller.is_active,
            self.strategy,
            any_opening_open,
        )

        # When the climate is OFF, keep-alive bypasses `needs_control` so it can
        # enforce the device staying off. We must never run goal-based logic
        # here — only turn the switch off if it ended up on externally.
        # See issue #587.
        if self._hvac_mode == HVACMode.OFF:
            await self.async_stop(keep_alive=time is not None)
            return

        # Inside the minimum cycle nothing switches; keep-alive only re-sends
        # the current state (#668).
        if not self.hvac_controller.min_cycle_elapsed(force):
            if time is not None and self.hvac_controller.is_active:
                await self.async_turn_on()
            return

        # An open opening is about to stop the device: do not push a setpoint first.
        if not any_opening_open:
            await self.port.async_sync(self._context)

        if self.hvac_controller.is_active:
            await self.hvac_controller.async_control_device_when_on(
                self.strategy,
                any_opening_open,
                time,
            )
        else:
            await self.hvac_controller.async_control_device_when_off(
                self.strategy,
                any_opening_open,
                time,
            )

        _LOGGER.debug(
            "hvac action reason after control: %s",
            self.hvac_controller.hvac_action_reason,
        )

        self._hvac_action_reason = self.hvac_controller.hvac_action_reason
        self.hvac_power.update_hvac_power(
            self.strategy, self.target_env_attr, self.hvac_action
        )

    async def async_on_startup(self, async_write_ha_state_cb: Callable = None):

        self._async_write_ha_state_cb = async_write_ha_state_cb
        entity_state = self.hass.states.get(self.entity_id)

        if entity_state and entity_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        ):
            self.hass.loop.create_task(self._async_check_device_initial_state())

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        if self._hvac_mode == HVACMode.OFF:
            await self.async_stop()

    async def async_turn_on(self):
        _LOGGER.debug(
            "%s. Turning on or opening entity %s",
            self.__class__.__name__,
            self.entity_id,
        )

        if self.entity_id is None:
            return

        await self.port.async_turn_on(self._context)

    async def async_turn_off(self):
        _LOGGER.debug(
            "%s. Turning off or closing entity %s",
            self.__class__.__name__,
            self.entity_id,
        )
        if self.entity_id is None:
            return

        await self.port.async_turn_off(self._context)

        self.hvac_power.update_hvac_power(
            self.strategy, self.target_env_attr, HVACAction.OFF
        )

    def release(self) -> None:
        """The thermostat is being removed: release the port's resources."""
        self.port.release()

    async def async_stop(self, *, keep_alive: bool = False) -> None:
        """DST is Off: the entity must end up off, whatever it was doing."""
        if self.entity_id is None:
            return

        await self.port.async_stop(self._context, keep_alive=keep_alive)

        self.hvac_power.update_hvac_power(
            self.strategy, self.target_env_attr, HVACAction.OFF
        )
