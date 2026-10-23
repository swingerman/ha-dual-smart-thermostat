"""Fan speed control for the one entity that owns the thermostat's fan_mode."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State, callback

from ..climate_roles import is_climate_entity
from ..const import FAN_MODE_TO_PERCENTAGE
from .entity_port import peek_climate_child

_LOGGER = logging.getLogger(__name__)


class FanSpeedControl:
    """Detect, hold, restore and apply a fan speed on one entity."""

    def __init__(self, hass: HomeAssistant, entity_id: str, owner: Any = None) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self.owner = owner  # the thermostat whose fan speed this is
        self._is_climate = is_climate_entity(entity_id)
        self.fan_modes: list[str] = []
        self.uses_preset_modes = False
        self.current_fan_mode: str | None = None
        self._pending_fan_mode: str | None = None
        self._detect_fan_capabilities()

    def _detect_fan_capabilities(self, fan_state: State | None = None) -> None:
        """Detect if fan entity supports speed control."""
        fan_state = fan_state or self.hass.states.get(self.entity_id)

        if not fan_state:
            _LOGGER.debug("Fan entity %s not found, no speed control", self.entity_id)
            return

        # Check domain - only "fan" domain supports speed control
        entity_domain = fan_state.domain
        if entity_domain == SWITCH_DOMAIN:
            _LOGGER.debug("Fan entity %s is a switch, no speed control", self.entity_id)
            return

        if entity_domain == FAN_DOMAIN:
            # Check for preset_mode support
            preset_modes = fan_state.attributes.get(ATTR_PRESET_MODES)
            if preset_modes:
                self.fan_modes = list(preset_modes)
                self.uses_preset_modes = True
                _LOGGER.info(
                    "Fan entity %s supports preset modes: %s",
                    self.entity_id,
                    self.fan_modes,
                )
                # Set initial mode from entity state
                current_preset = fan_state.attributes.get(ATTR_PRESET_MODE)
                if current_preset:
                    self.current_fan_mode = current_preset
                return

            # Check for percentage support
            percentage = fan_state.attributes.get(ATTR_PERCENTAGE)
            if percentage is not None:
                self.fan_modes = ["auto", "low", "medium", "high"]
                self.uses_preset_modes = False
                _LOGGER.info(
                    "Fan entity %s supports percentage-based speed control",
                    self.entity_id,
                )
                # Default to auto mode for percentage-based control
                self.current_fan_mode = "auto"
                return

        if entity_domain == CLIMATE_DOMAIN:
            fan_modes = fan_state.attributes.get(ATTR_FAN_MODES)
            if fan_modes:
                self.fan_modes = list(fan_modes)  # verbatim: quiet / strong survive
                self.uses_preset_modes = True
                self.current_fan_mode = fan_state.attributes.get(ATTR_FAN_MODE)
                _LOGGER.info(
                    "Climate entity %s supports fan modes: %s",
                    self.entity_id,
                    self.fan_modes,
                )
                return

        _LOGGER.debug("Fan entity %s does not support speed control", self.entity_id)

    @callback
    def redetect_capabilities(self, entity_id: str, new_state: State) -> bool:
        """Retry detection once our entity shows up, True if it gained speed control."""
        if entity_id != self.entity_id or self.supports_fan_mode:
            return False

        self._detect_fan_capabilities(new_state)

        if not self.supports_fan_mode:
            return False

        if self._pending_fan_mode is not None:
            self.restore_fan_mode(self._pending_fan_mode)
            self._pending_fan_mode = None

        return True

    async def async_reapply(self, entity_id: str) -> None:
        """Re-send the selected speed after the climate child was turned on.

        Many ACs (infrared ones especially) reset their fan speed on a mode
        change. Acts only when this control targets that very climate entity,
        so a separate fan entity, or another climate, is never touched.
        """
        if (
            entity_id != self.entity_id
            or not self.supports_fan_mode
            or self.current_fan_mode is None
        ):
            return
        await self.async_set_fan_mode(self.current_fan_mode)

    @property
    def supports_fan_mode(self) -> bool:
        """Return if fan supports speed control."""
        return bool(self.fan_modes)

    def restore_fan_mode(self, fan_mode: str) -> None:
        """Restore fan mode from persisted state.

        Args:
            fan_mode: The fan mode to restore

        This method validates that the fan mode is valid for the current
        fan device before restoring it. Invalid modes are logged and ignored.
        """
        if not self.supports_fan_mode:
            # Entity isn't up yet; hold it for redetect_capabilities (issue #636).
            self._pending_fan_mode = fan_mode
            return

        if fan_mode in self.fan_modes:
            self.current_fan_mode = fan_mode
            _LOGGER.info("Restored fan mode %s for entity %s", fan_mode, self.entity_id)
        else:
            _LOGGER.warning(
                "Cannot restore invalid fan mode %s for entity %s. Available modes: %s",
                fan_mode,
                self.entity_id,
                self.fan_modes,
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan speed mode."""
        if not self.supports_fan_mode:
            _LOGGER.warning(
                "Fan entity %s does not support speed control", self.entity_id
            )
            return

        if fan_mode not in self.fan_modes:
            _LOGGER.warning(
                "Invalid fan mode %s for entity %s. Available modes: %s",
                fan_mode,
                self.entity_id,
                self.fan_modes,
            )
            return

        _LOGGER.debug("Setting fan mode to %s for entity %s", fan_mode, self.entity_id)

        if self._is_climate:
            # The shared child decides whether the AC is running (and sends it);
            # otherwise the selection is only recorded below for the next turn on.
            if child := peek_climate_child(self.hass, self.entity_id):
                await child.async_set_fan_mode(fan_mode, None, self.owner)
        elif self.uses_preset_modes:
            # Use preset_mode service
            await self.hass.services.async_call(
                FAN_DOMAIN,
                SERVICE_SET_PRESET_MODE,
                {ATTR_ENTITY_ID: self.entity_id, ATTR_PRESET_MODE: fan_mode},
                blocking=True,
            )
        else:
            # Use percentage service
            percentage = FAN_MODE_TO_PERCENTAGE.get(fan_mode)
            if percentage is None:
                _LOGGER.error("No percentage mapping for fan mode %s", fan_mode)
                return

            await self.hass.services.async_call(
                FAN_DOMAIN,
                SERVICE_SET_PERCENTAGE,
                {ATTR_ENTITY_ID: self.entity_id, ATTR_PERCENTAGE: percentage},
                blocking=True,
            )

        self.current_fan_mode = fan_mode
        _LOGGER.info("Fan mode set to %s for entity %s", fan_mode, self.entity_id)
