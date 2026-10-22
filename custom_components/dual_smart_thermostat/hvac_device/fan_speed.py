"""Fan speed control for the one entity that owns the thermostat's fan_mode."""

from __future__ import annotations

import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State, callback

from ..climate_roles import is_climate_entity
from ..const import FAN_MODE_TO_PERCENTAGE
from .entity_port import peek_climate_child

_LOGGER = logging.getLogger(__name__)


class FanSpeedControl:
    """Detect, hold, restore and apply a fan speed on one entity."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self._is_climate = is_climate_entity(entity_id)
        self._supports_fan_mode = False
        self._fan_modes: list[str] = []
        self._uses_preset_modes = False
        self._current_fan_mode: str | None = None
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

        if entity_domain == "climate":
            fan_modes = fan_state.attributes.get("fan_modes")
            if fan_modes:
                self._supports_fan_mode = True
                self._fan_modes = list(fan_modes)  # verbatim: quiet / strong survive
                self._uses_preset_modes = True
                self._current_fan_mode = fan_state.attributes.get("fan_mode")
                _LOGGER.info(
                    "Climate entity %s supports fan modes: %s",
                    self.entity_id,
                    self._fan_modes,
                )
                return

        _LOGGER.debug("Fan entity %s does not support speed control", self.entity_id)

    @callback
    def redetect_capabilities(self, entity_id: str, new_state: State) -> bool:
        """Retry detection once our entity shows up, True if it gained speed control."""
        if entity_id != self.entity_id or self._supports_fan_mode:
            return False

        self._detect_fan_capabilities(new_state)

        if not self._supports_fan_mode:
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
            not self._is_climate
            or entity_id != self.entity_id
            or not self._supports_fan_mode
            or self._current_fan_mode is None
        ):
            return
        await self.async_set_fan_mode(self._current_fan_mode)

    @property
    def is_climate(self) -> bool:
        """Return if the speed is set on a climate entity."""
        return self._is_climate

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

    def restore_fan_mode(self, fan_mode: str) -> None:
        """Restore fan mode from persisted state.

        Args:
            fan_mode: The fan mode to restore

        This method validates that the fan mode is valid for the current
        fan device before restoring it. Invalid modes are logged and ignored.
        """
        if not self._supports_fan_mode:
            # Entity isn't up yet; hold it for redetect_capabilities (issue #636).
            self._pending_fan_mode = fan_mode
            return

        if fan_mode in self._fan_modes:
            self._current_fan_mode = fan_mode
            _LOGGER.info("Restored fan mode %s for entity %s", fan_mode, self.entity_id)
        else:
            _LOGGER.warning(
                "Cannot restore invalid fan mode %s for entity %s. Available modes: %s",
                fan_mode,
                self.entity_id,
                self._fan_modes,
            )

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

        if self._is_climate:
            state = self.hass.states.get(self.entity_id)
            assumed = bool(state and state.attributes.get("assumed_state"))
            # Is the child running? An assumed-state (IR) child never reports it,
            # so its mode is DST's own record (the shared ClimateChild), if any.
            child = peek_climate_child(self.hass, self.entity_id)
            mode = child.mode if child is not None else state and state.state
            # An off or unavailable child gets nothing now: the selection is only
            # recorded and async_reapply sends it on the next turn on. An IR frame
            # could otherwise power the AC on while the thermostat is Off.
            if mode in (None, False, HVACMode.OFF, STATE_UNAVAILABLE, STATE_UNKNOWN):
                self._current_fan_mode = fan_mode
                return
            # A reported-state child that already has it needs no call; an
            # assumed-state one cannot tell us, so it is always sent.
            if not assumed and state.attributes.get("fan_mode") == fan_mode:
                self._current_fan_mode = fan_mode
                return
            await self.hass.services.async_call(
                "climate",
                "set_fan_mode",
                {"entity_id": self.entity_id, "fan_mode": fan_mode},
                blocking=True,
            )
        elif self._uses_preset_modes:
            # Use preset_mode service
            await self.hass.services.async_call(
                "fan",
                "set_preset_mode",
                {"entity_id": self.entity_id, "preset_mode": fan_mode},
                blocking=True,
            )
        else:
            # Use percentage service
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
