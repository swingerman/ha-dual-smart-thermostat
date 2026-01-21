from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_device.cooler_device import CoolerDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.hvac_power_manager import HvacPowerManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class FanDevice(CoolerDevice):

    hvac_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
    fan_air_surce_outside = False

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
        )

        if self.features.is_fan_uses_outside_air:
            self.fan_air_surce_outside = True

        # Detect fan speed control capabilities
        self._supports_fan_mode = False
        self._fan_modes = []
        self._uses_preset_modes = False
        self._current_fan_mode = None
        self._detect_fan_capabilities()

    def _detect_fan_capabilities(self) -> None:
        """Detect if fan entity supports speed control."""
        fan_state = self.hass.states.get(self.entity_id)

        if not fan_state:
            _LOGGER.debug("Fan entity %s not found, no speed control", self.entity_id)
            return

        # Check domain - only "fan" domain supports speed control
        entity_domain = fan_state.domain
        if entity_domain == "switch":
            _LOGGER.debug("Fan entity %s is a switch, no speed control", self.entity_id)
            return

        if entity_domain == "fan":
            # Check for preset_mode support
            preset_modes = fan_state.attributes.get("preset_modes")
            if preset_modes:
                self._supports_fan_mode = True
                self._fan_modes = list(preset_modes)
                self._uses_preset_modes = True
                _LOGGER.info(
                    "Fan entity %s supports preset modes: %s",
                    self.entity_id,
                    self._fan_modes,
                )
                # Set initial mode from entity state
                current_preset = fan_state.attributes.get("preset_mode")
                if current_preset:
                    self._current_fan_mode = current_preset
                return

            # Check for percentage support
            percentage = fan_state.attributes.get("percentage")
            if percentage is not None:
                self._supports_fan_mode = True
                self._fan_modes = ["auto", "low", "medium", "high"]
                self._uses_preset_modes = False
                _LOGGER.info(
                    "Fan entity %s supports percentage-based speed control",
                    self.entity_id,
                )
                # Default to auto mode for percentage-based control
                self._current_fan_mode = "auto"
                return

        _LOGGER.debug("Fan entity %s does not support speed control", self.entity_id)

    @property
    def supports_fan_mode(self) -> bool:
        """Return if fan supports speed control."""
        return self._supports_fan_mode

    @property
    def fan_modes(self) -> list[str]:
        """Return list of available fan modes."""
        return self._fan_modes

    @property
    def uses_preset_modes(self) -> bool:
        """Return if fan uses preset modes (vs percentage)."""
        return self._uses_preset_modes

    @property
    def current_fan_mode(self) -> str | None:
        """Return current fan mode."""
        return self._current_fan_mode

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan speed mode."""
        if not self._supports_fan_mode:
            _LOGGER.warning(
                "Fan entity %s does not support speed control", self.entity_id
            )
            return

        if fan_mode not in self._fan_modes:
            _LOGGER.warning(
                "Invalid fan mode %s for entity %s. Available modes: %s",
                fan_mode,
                self.entity_id,
                self._fan_modes,
            )
            return

        _LOGGER.debug("Setting fan mode to %s for entity %s", fan_mode, self.entity_id)

        if self._uses_preset_modes:
            # Use preset_mode service
            await self.hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": self.entity_id, "preset_mode": fan_mode},
                blocking=True,
            )
        else:
            # Use percentage service
            from ..const import FAN_MODE_TO_PERCENTAGE

            percentage = FAN_MODE_TO_PERCENTAGE.get(fan_mode)
            if percentage is None:
                _LOGGER.error("No percentage mapping for fan mode %s", fan_mode)
                return

            await self.hass.services.async_call(
                "fan",
                "set_percentage",
                {"entity_id": self.entity_id, "percentage": percentage},
                blocking=True,
            )

        self._current_fan_mode = fan_mode
        _LOGGER.info("Fan mode set to %s for entity %s", fan_mode, self.entity_id)

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.FAN
        return HVACAction.IDLE
