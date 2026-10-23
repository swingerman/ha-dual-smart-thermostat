"""Port for climate entities: one role's view of a (possibly shared) child."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util

from ..const import ControlStyle
from .climate_child import _CHILDREN_KEY, acquire_climate_child
from .entity_port import EntityPort


class ClimatePort(EntityPort):
    """One role's view of a (possibly shared) climate entity."""

    @property
    def owner(self) -> Any:
        """The thermostat this role belongs to (its FeatureManager)."""
        return self._device.features

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        super().__init__(hass, device)
        self._child = acquire_climate_child(hass, device.entity_id)
        self._child.ports.add(self)
        self.self_regulating = device.control_style() == ControlStyle.SETPOINT

    def role_modes(self) -> list:
        """The child modes this role runs in (the first is the one commanded)."""
        return self._device.role_modes()

    @property
    def selected(self) -> bool:
        """Whether the thermostat's mode selects this role (it is not Off)."""
        return self._device.hvac_mode not in (None, HVACMode.OFF)

    @property
    def pushes_setpoint(self) -> bool:
        return self._device.pushes_setpoint

    def release(self) -> None:
        child = self._child
        if self not in child.ports:
            return  # idempotent
        child.ports.discard(self)
        if not any(p.owner is self.owner for p in child.ports):
            child.echo.forget(self.owner)
        if not child.ports:
            child.hass.data.get(_CHILDREN_KEY, {}).pop(child.entity_id, None)

    @property
    def is_active(self) -> bool:
        # The first role mode is the one commanded; any of them counts as running
        # (a heat pump in either mode, so a flip of its flag still stops it).
        return self._child.mode in self.role_modes()

    role_scoped = True

    def begin_pass(self) -> None:
        self._child.begin_pass()

    async def end_pass(self) -> None:
        await self._child.end_pass()

    def holds_stop(self, min_cycle: timedelta) -> bool:
        return not self.ran_long_enough(min_cycle)

    def holds_start(self, min_cycle: timedelta) -> bool:
        # Switching a running child from one role's mode to another's is not a start.
        return self._child.mode == HVACMode.OFF and not self.ran_long_enough(min_cycle)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        if not min_cycle:  # none configured: nothing to wait for
            return True
        child = self._child
        if child.mode == HVACMode.OFF:
            # Only an off DST itself commanded counts: an off nobody saw running (a
            # restart, a new entity) says nothing about the compressor.
            since = child.commanded_at if child.commanded == HVACMode.OFF else None
            return since is None or dt_util.utcnow() - since >= min_cycle
        since = child.since
        return since is not None and dt_util.utcnow() - since >= min_cycle

    async def _push(self, context: Context | None) -> None:
        target = self._device.climate_target()
        if target is not None:
            await self._child.async_push_target(
                self.dst_target_to_device(target), context, self.owner
            )

    def dst_target_to_device(self, target: float) -> float:
        """DST's target as this role pushes it (plus the role's setpoint offset)."""
        return target + self._device.setpoint_offset()

    def device_target_to_dst(self, value: float) -> float:
        """The inverse: a target reported by the device, in DST's own terms."""
        return round(value - self._device.setpoint_offset(), 4)

    async def async_turn_on(self, context: Context | None) -> None:
        # One sequence: what the device reports meanwhile (a reset fan, a changed
        # setpoint) is its own side effect, not the user's.
        with self._child.echo.sending(self.owner):
            if not await self._child.async_set_mode(
                self.role_modes()[0], context, self.owner
            ):
                return
            if self._child.in_pass:
                self._child.defer_tail(self, context, turn_on=True)
                return
            await self.async_finish_turn_on(context, turn_on=True)

    async def async_finish_turn_on(
        self, context: Context | None, *, turn_on: bool
    ) -> None:
        await self._push(context)
        if turn_on:
            # Last, so the speed lands after the mode change that may have reset it.
            await self._reapply_fan_speed()

    async def async_sync(self, context: Context | None) -> None:
        # Only the role the child is serving may touch its setpoint.
        if self.is_active:
            if self._child.in_pass:
                self._child.defer_tail(self, context, turn_on=False)
            else:
                await self._push(context)

    async def async_turn_off(self, context: Context | None) -> None:
        # Only the role the child is currently serving may stop it, so an idle
        # cooler's stop can never switch off the heater on the same device. And only
        # while a role is selected: when the thermostat is Off it leaves the device
        # alone (a stop of the Off transition goes through async_stop).
        if self.is_active and self._child.wanted_on:
            if self._child.in_pass:
                self._child.defer_stop(self, context)
            else:
                await self._child.async_turn_off(context, self.owner)

    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
        # Off means off, once, on the transition to Off: whatever mode the child is
        # in, even one no role owns, but only while no role on the child is selected
        # (otherwise this role is just being switched out). A keep-alive tick while
        # Off leaves a climate alone, so the AC's own remote keeps working.
        child = self._child
        if keep_alive:
            return
        if not child.wanted_on and child.mode not in (None, HVACMode.OFF):
            await child.async_stop_unscoped(context, self.owner)
        else:
            await self.async_turn_off(context)
