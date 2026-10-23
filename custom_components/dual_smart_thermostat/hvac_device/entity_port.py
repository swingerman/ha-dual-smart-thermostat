"""How a device role talks to its entity.

The one place that knows what "on" means for an entity and how to command it.
Controllers and devices call these methods; they never read the entity's state
or call its services themselves.

A port keeps a reference to its device and asks it lazily for what it needs
(`entity_id`, `role_modes()`, `climate_target()`, `setpoint_offset()`,
`control_style()`, `fan_speed()`), so nothing is copied at construction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
import logging
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, HomeAssistant, State

from ..climate_roles import is_climate_entity

_LOGGER = logging.getLogger(__name__)


def is_unavailable(state: State | None) -> bool:
    """True when an entity has no usable state."""
    return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)


async def _call_service(
    hass: HomeAssistant,
    domain: str,
    service: str,
    data: dict[str, Any],
    context: Context | None,
    error: str,
    *args: Any,
) -> bool:
    """Blocking service call; a failure is logged (`error` + the exception), not raised."""
    try:
        await hass.services.async_call(
            domain, service, data, context=context, blocking=True
        )
    except Exception as e:  # noqa: BLE001
        _LOGGER.error(error + ". Error: %s", *args, e)
        return False
    return True


class EntityPort(ABC):
    """What a device role needs from its entity."""

    entity_id: str
    # True when the entity regulates itself and DST must not cycle it.
    self_regulating: bool = False

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        self.hass = hass
        self._device = device
        self.entity_id = device.entity_id

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Whether the role is currently engaged."""

    @abstractmethod
    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        """Whether the current on/off state has lasted at least min_cycle."""

    # A stop is scoped to the role's own mode on a device shared by several roles
    # (a climate); begin_pass/end_pass bracket a control run on such a device.
    role_scoped = False

    def begin_pass(self) -> None:
        return

    async def end_pass(self) -> None:
        return

    def holds_stop(self, min_cycle: timedelta) -> bool:
        """A goal-reached stop must wait for the minimum cycle, even in a forced run.

        Only a climate holds it (its compressor); a switch lets a forced run skip
        the minimum cycle.
        """
        return False

    def holds_start(self, min_cycle: timedelta) -> bool:
        """A start must wait for the minimum cycle, even in a forced run."""
        return False

    @abstractmethod
    async def async_turn_on(self, context: Context | None) -> None:
        """Engage the role."""

    @abstractmethod
    async def async_turn_off(self, context: Context | None) -> None:
        """Disengage the role."""

    async def async_sync(self, context: Context | None) -> None:
        """Mirror DST state onto the entity. Nothing to mirror by default."""
        return

    def release(self) -> None:
        """The thermostat is going away: let go of shared resources."""
        return

    @abstractmethod
    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
        """DST is Off: make sure the entity is off. Off means off.

        `keep_alive` marks a periodic tick while Off: a switch is stopped if it is
        running (it reports reliably); a climate is left alone.
        """

    async def _reapply_fan_speed(self) -> None:
        """After a turn on, send the selected fan speed again.

        Many ACs (infrared ones especially) reset it on a mode change. A failure
        is logged here and never aborts the control cycle.
        """
        speed = self._device.fan_speed()
        if speed is None:
            return
        try:
            await speed.async_reapply(self.entity_id)
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply fan mode %s after turning on %s: %s",
                speed.current_fan_mode,
                self.entity_id,
                e,
            )


def make_port(hass: HomeAssistant, device: Any) -> EntityPort:
    """Build the port for a device's role from its entity domain."""
    # Local imports: the port modules import EntityPort from here.
    from .climate_port import ClimatePort
    from .switch_port import SwitchPort

    if is_climate_entity(device.entity_id):
        return ClimatePort(hass, device)
    return SwitchPort(hass, device)
