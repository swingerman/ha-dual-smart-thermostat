"""Following a climate entity that is changed from outside (spec section 3.6).

A thermostat with climate-backed roles consumes the echoes of its own commands and
adopts what the user (a remote, a vendor app, an automation) did on the device.
The entity only routes state-change events here and supplies the narrow sink below.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from homeassistant.components.climate import ATTR_FAN_MODE, HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State

from ..climate_roles import is_climate_entity
from .entity_port import ClimateChild, is_unavailable, peek_climate_child

_LOGGER = logging.getLogger(__name__)


class FollowSink(Protocol):
    """What the follower needs from the thermostat entity."""

    hass: HomeAssistant
    entity_id: str
    features: Any  # the FeatureManager: the owner of the echoes
    hvac_modes: list
    min_temp: float
    max_temp: float

    @property
    def hvac_mode_now(self) -> HVACMode | None:
        """Provided by the thermostat."""

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Provided by the thermostat."""

    async def async_set_temperature(self, **kwargs) -> None:
        """Provided by the thermostat."""

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Provided by the thermostat."""

    async def async_adoption_run(self) -> None:
        """Provided by the thermostat."""

    async def async_assert_off(self) -> None:
        """Provided by the thermostat."""

    def async_write_ha_state(self) -> None:
        """Provided by the thermostat."""


class ClimateFollower:
    """Per thermostat: classify the events of its climate children, adopt the outside ones."""

    def __init__(self, sink: FollowSink) -> None:
        self._sink = sink
        self._lock = asyncio.Lock()
        self._changed: set[str] = set()  # what to take from the child
        self._state: State | None = None  # the newest external report
        self._seen_children: set[str] = set()  # climate children seen available
        # startup and state restore are done: changes can be adopted
        self.started = False
        self.restored = False
        self.fan_chosen = False  # the user picked a fan speed this session

    def mark_seen(self, entity_id: str) -> None:
        """Late detection has read the child (and kept a restored speed)."""
        self._seen_children.add(entity_id)

    def on_event(self, event: Event[EventStateChangedData]) -> None:
        """Consume our own echoes; adopt anything that came from outside."""
        sink = self._sink
        entity_id = event.data["entity_id"]
        if not is_climate_entity(entity_id):
            return
        old, new = event.data["old_state"], event.data["new_state"]
        self._sync_fan_display(entity_id, new)
        child = peek_climate_child(sink.hass, entity_id)
        if child is None:
            return
        if (
            old is None
            and new is not None
            and self.restored
            and sink.hvac_mode_now == HVACMode.OFF
        ):
            # First sight of a child while we are Off (restored or configured): Off
            # is asserted once here; nothing is adopted from first sight.
            sink.hass.async_create_task(self._async_assert_off())
        # Always classify (it consumes this thermostat's echoes), adopt only if following.
        report = child.external(sink.features, old, new)
        if report.fan_dropped:
            sink.hass.async_create_task(self._async_resend_fan(child))
        if (
            report.changed
            and sink.features.follow_device_changes
            and self.started
            and self.restored
        ):
            self._changed |= report.changed
            # The report that came from outside, not the child as it is by the time
            # the adoption runs (a peer may have stopped it meanwhile).
            self._state = new

            def adopt() -> None:
                if not self._lock.locked():  # the running adoption goes round again
                    sink.hass.async_create_task(self._async_adopt(child))

            # Another thermostat mid-sequence on this child: adopt when it is done.
            if not child.defer_while_sending(sink.features, adopt):
                adopt()

    def _sync_fan_display(self, entity_id: str, new_state: State | None) -> None:
        """A child seen for the first time: show its fan speed (nothing is sent).

        The display would otherwise stay at a default or a stale restore. Not
        after the user picked a speed: that selection is sent on the next turn on.
        """
        sink = self._sink
        if is_unavailable(new_state) or entity_id in self._seen_children:
            return
        self._seen_children.add(entity_id)
        speed = sink.features.fan_speed
        fan_mode = new_state.attributes.get(ATTR_FAN_MODE)
        if (
            sink.features.follow_device_changes
            and not self.fan_chosen
            and speed is not None
            and speed.entity_id == entity_id
            and fan_mode in speed.fan_modes
        ):
            speed.current_fan_mode = fan_mode
            sink.async_write_ha_state()

    async def _async_resend_fan(self, child: ClimateChild) -> None:
        """The device dropped our fan speed while powering on: send it again."""
        speed = self._sink.features.fan_speed
        if speed is not None:
            await speed.async_reapply(child.entity_id)

    async def _async_assert_off(self) -> None:
        # The task may run later than the event that scheduled it: ask again.
        if self.restored and self._sink.hvac_mode_now == HVACMode.OFF:
            await self._sink.async_assert_off()

    async def _async_adopt(self, child: ClimateChild) -> None:
        """Make the child's current settings DST's own, then carry on controlling."""
        sink = self._sink
        if self._lock.locked():
            return  # the running adoption sees the new changes and goes round again
        async with self._lock:
            while self._changed:
                changed, self._changed = self._changed, set()
                state = self._state
                if state is None or not child.available:
                    return
                _LOGGER.debug(
                    "%s adopts %s (changed: %s)", sink.entity_id, state, sorted(changed)
                )
                # our commands to it are dropped, briefly
                with child.adopting(sink.features):
                    await self._async_adopt_state(child, state, changed)
                child.clear(sink.features)
                await sink.async_adoption_run()

    async def _async_adopt_state(
        self, child: ClimateChild, state: State, changed: set[str]
    ) -> None:
        """Apply what changed on the child through DST's own setters (commands dropped).

        Only the attributes that changed are taken: the rest of the child's state is
        whatever it last held, not something the user did.
        """
        sink = self._sink
        speed = sink.features.fan_speed
        fan_mode = state.attributes.get(ATTR_FAN_MODE)
        if (
            "fan_mode" in changed
            and speed is not None
            and speed.entity_id == child.entity_id
            and fan_mode in speed.fan_modes
        ):
            await sink.async_set_fan_mode(fan_mode)

        mode = state.state
        port = child.port_for(mode)
        if "mode" in changed and (
            mode == HVACMode.OFF or port is None or mode not in sink.hvac_modes
        ):
            # off, or a mode no role owns: Off, and hands-off
            await sink.async_set_hvac_mode(HVACMode.OFF)
            return
        if "mode" in changed:
            await sink.async_set_hvac_mode(HVACMode(mode))
        target = state.attributes.get(ATTR_TEMPERATURE)
        # a target is the user's only if it changed and the role in this mode has one
        if (
            "target" in changed
            and target is not None
            and port is not None
            and port.pushes_setpoint
            and mode in sink.hvac_modes
        ):
            # like any user input: inside DST's own range
            wanted = port.device_target_to_dst(target)
            await sink.async_set_temperature(
                temperature=min(max(wanted, sink.min_temp), sink.max_temp)
            )
