# Climate Entity Devices - Phase 1: Port Seam and Climate on_off Role - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `heater`, `cooler`, `fan` or `dryer` be a `climate.*` entity in YAML with `control_style: on_off` behaviour (DST's loop decides; on = set the child's hvac mode and push the target, off = `climate.turn_off`). Mixed setups (climate cooler + switch heater) work. Introduce the `EntityPort` seam by moving the existing switch/valve logic behind it first, with no behaviour change.

**Architecture:** One new module `hvac_device/entity_port.py`: `EntityPort` (4 calls), `SwitchPort` (today's code, moved), `ClimateChild` (one per real climate entity, owns its single mode record), `ClimatePort` (per-role view over the child, `is_active` derived from `child.mode`). `GenericHVACDevice` builds its port with `make_port` from the entity domain and hands it to `GenericHvacController`. Nothing above them (managers, `climate.py`, `MultiHvacDevice`) changes.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, `homeassistant.helpers.entity_platform` (test fake child), pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md`

---

## Testing Environment

This repo runs tests and lint only inside Docker:

```bash
./scripts/docker-test <pytest-args>      # e.g. ./scripts/docker-test tests/foo.py::test_bar
./scripts/docker-lint                    # full lint check
./scripts/docker-lint --fix              # auto-fix lint issues
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly.

Test code below follows the HA test plugin idioms used elsewhere in this repo. Where an import or fixture name differs from reality, fix it in the red step; the structure and assertions are what matter.

---

## Shared Context

### How the stack touches an entity today (the seam)

| Where | What |
|---|---|
| `GenericHvacController.is_active` | `hass.states.is_state(entity_id, "on")` (`"open"` for valves) |
| `GenericHvacController.ran_long_enough` | `condition.state(hass, entity_id, "on"/"off", min_cycle_duration)` |
| `GenericHVACDevice._async_turn_on_entity` / `_async_turn_off_entity` | skip when unavailable, else `homeassistant.turn_on/off` |
| `GenericHVACDevice._async_open_valve_entity` / `_async_close_valve_entity` | valve services |
| `GenericHVACDevice.is_on`, `_entity_state`, `_is_valve`, `_entity_features`, `_supports_*_valve` | helpers for the above |

Everything else calls `device.async_turn_on()` / `async_turn_off()` / `is_active`. Those stay.

### Role to child mode

| Device class | `role_mode()` | Pushes target |
|---|---|---|
| `HeaterDevice` | `HVACMode.HEAT` | yes |
| `CoolerDevice` | `HVACMode.COOL` | yes |
| `FanDevice` | `HVACMode.FAN_ONLY` | no |
| `DryerDevice` | `HVACMode.DRY` | no |

(`HeatPumpDevice` arrives in phase 3. Until then a climate entity as heat pump `heater` with `heat_pump_cooling` raises at setup via the "no role mode" guard, see task 5.)

### Fake child for tests

A real `ClimateEntity` subclass registered through `MockEntityPlatform`, so the real `climate.*` services run against it (registering a mock `climate.set_hvac_mode` service would hijack DST's own entity services). It records calls, and in `assumed` mode records them but never changes its reported state (worst case: no state feedback).

---

## Task 1: `climate_roles.py` - one definition of "is this role a climate entity"

**Files:**
- Create: `custom_components/dual_smart_thermostat/climate_roles.py`
- Test: `tests/unit/test_config_validation_integration.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_config_validation_integration.py`:

```python
from custom_components.dual_smart_thermostat.climate_roles import (
    climate_role_ids,
    first_climate_role,
    has_climate_role,
    is_climate_entity,
)


def test_is_climate_entity_by_domain() -> None:
    assert is_climate_entity("climate.living_room_ac")
    assert not is_climate_entity("switch.living_room_ac")
    assert not is_climate_entity("input_boolean.heater")
    assert not is_climate_entity(None)


def test_climate_role_ids_only_considers_device_roles() -> None:
    config = {
        "heater": "switch.heater",
        "cooler": "climate.ac",
        "fan": "climate.ac",
        "target_sensor": "climate.not_a_role",
        "secondary_heater": "climate.not_a_role_either",
    }
    assert climate_role_ids(config) == {"cooler": "climate.ac", "fan": "climate.ac"}
    assert has_climate_role(config)
    assert first_climate_role(config) == "climate.ac"


def test_no_climate_role() -> None:
    config = {"heater": "switch.heater", "target_sensor": "sensor.t"}
    assert climate_role_ids(config) == {}
    assert not has_climate_role(config)
    assert first_climate_role(config) is None


def test_first_climate_role_follows_role_priority() -> None:
    config = {"dryer": "climate.b", "cooler": "climate.a"}
    assert first_climate_role(config) == "climate.a"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -k "climate_role or is_climate_entity" -v
```

Expected: FAIL, `ModuleNotFoundError: ...climate_roles`.

- [ ] **Step 3: Implement**

Create `custom_components/dual_smart_thermostat/climate_roles.py`:

```python
"""Which device roles are backed by a climate entity.

The one definition shared by YAML validation, the config flows and runtime, so
they cannot disagree about it. Aux (secondary) heater is deliberately absent:
it stays switch-like.
"""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.core import split_entity_id

from .const import CONF_COOLER, CONF_DRYER, CONF_FAN, CONF_HEATER

CLIMATE_DOMAIN = "climate"

# Priority order, also the order the temperature fallback picks a source in.
CLIMATE_ROLE_KEYS = (CONF_HEATER, CONF_COOLER, CONF_FAN, CONF_DRYER)


def is_climate_entity(entity_id: Any) -> bool:
    """True when the id belongs to the climate domain."""
    return isinstance(entity_id, str) and split_entity_id(entity_id)[0] == CLIMATE_DOMAIN


def climate_role_ids(config: Mapping[str, Any]) -> dict[str, str]:
    """Role key -> entity id for every role that is a climate entity."""
    return {
        key: config[key]
        for key in CLIMATE_ROLE_KEYS
        if is_climate_entity(config.get(key))
    }


def has_climate_role(config: Mapping[str, Any]) -> bool:
    return bool(climate_role_ids(config))


def first_climate_role(config: Mapping[str, Any]) -> str | None:
    roles = climate_role_ids(config)
    return next(iter(roles.values()), None)
```

`split_entity_id` raises on ids without a dot; guard by catching `ValueError` and returning `False` (add `try/except ValueError` around it if the test for malformed ids is added).

- [ ] **Step 4: Run test to verify it passes**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -k "climate_role or is_climate_entity" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate_roles.py tests/unit/test_config_validation_integration.py
git commit -m "Add climate_roles helper: single definition of climate-backed roles

Refs #281"
```

---

## Task 2: Fake climate child for tests

**Files:**
- Modify: `tests/common.py`
- Test: `tests/features/test_climate_backed_devices.py` (new, the feature's single home)

- [ ] **Step 1: Write the failing test**

Create `tests/features/test_climate_backed_devices.py`:

```python
"""Tests for climate entities used as device roles (issue #281)."""

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from .. import common


async def test_fake_child_follows_real_climate_services(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ac", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ac").state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_fake_assumed_child_never_confirms(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ir", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF
    assert hass.states.get("climate.test_ir").attributes["assumed_state"] is True
    assert child.calls
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: FAIL, `AttributeError: module 'tests.common' has no attribute 'add_fake_climate'`.

- [ ] **Step 3: Implement the fake**

Add to `tests/common.py`:

```python
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockEntityPlatform


class FakeClimateChild(ClimateEntity):
    """A real climate entity standing in for a physical AC / radiator valve."""

    _attr_temperature_unit = "°C"
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
        HVACMode.DRY,
    ]
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 0.5
    _attr_should_poll = False

    def __init__(self, entity_id, mode=HVACMode.OFF, *, assumed=False, current=22.0):
        self.entity_id = entity_id
        self._attr_hvac_mode = mode
        self._attr_assumed_state = assumed
        self._attr_target_temperature = 21.0
        self._attr_current_temperature = current
        self.calls: list[tuple[str, dict]] = []

    def _follow(self, mode):
        # An assumed-state device never reports back: the state stays put.
        if not self._attr_assumed_state:
            self._attr_hvac_mode = mode
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        self.calls.append(("set_hvac_mode", {"hvac_mode": hvac_mode}))
        self._follow(hvac_mode)

    async def async_turn_off(self):
        self.calls.append(("turn_off", {}))
        self._follow(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        self.calls.append(("set_temperature", dict(kwargs)))
        if "temperature" in kwargs and not self._attr_assumed_state:
            self._attr_target_temperature = kwargs["temperature"]
            self.async_write_ha_state()

    def set_current_temperature(self, value):
        self._attr_current_temperature = value
        self.async_write_ha_state()


async def add_fake_climate(hass, entity_id, mode=HVACMode.OFF, **kwargs):
    """Register a FakeClimateChild; the real climate services act on it."""
    assert await async_setup_component(hass, "climate", {})
    child = FakeClimateChild(entity_id, mode, **kwargs)
    platform = MockEntityPlatform(hass, domain="climate", platform_name="fake")
    await platform.async_add_entities([child])
    await hass.async_block_till_done()
    return child
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/common.py tests/features/test_climate_backed_devices.py
git commit -m "Test helper: fake climate child backed by the real climate services

Refs #281"
```

---

## Task 3: Extract `EntityPort` / `SwitchPort` (move-only, no behaviour change)

**Files:**
- Create: `custom_components/dual_smart_thermostat/hvac_device/entity_port.py`
- Modify: `hvac_device/generic_hvac_device.py`, `hvac_controller/hvac_controller.py`, `hvac_controller/generic_controller.py`, `hvac_controller/heater_controller.py`, `hvac_controller/cooler_controller.py`, `hvac_device/heater_device.py`, `hvac_device/cooler_device.py`, `hvac_device/heat_pump_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Find every user of the helpers being moved**

```bash
grep -rn "_is_valve\|\._entity_state\|\.is_on\b\|_entity_features\|_supports_open_valve\|_supports_close_valve\|_async_turn_on_entity\|_async_turn_off_entity\|_async_open_valve_entity\|_async_close_valve_entity\|ran_long_enough" custom_components tests
```

Expected: hits in `generic_hvac_device.py`, `generic_controller.py`, `cooler_fan_device.py` (reads `cooler_device.is_on` and `cooler_device.hvac_controller.ran_long_enough()`, both of which keep working through the delegations below) and, if any, tests. Every hit in a test is updated to go through `device.port` in step 4; any other production hit must be rewritten the same way.

- [ ] **Step 2: Write the failing test (port contract on a switch)**

Append to `tests/features/test_climate_backed_devices.py`:

```python
from datetime import timedelta

from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.dual_smart_thermostat.hvac_device.entity_port import (
    SwitchPort,
    make_port,
)


async def test_make_port_returns_switch_port_for_switch_like(hass: HomeAssistant) -> None:
    hass.states.async_set("switch.heater", STATE_OFF)
    port = make_port(
        hass, "switch.heater", role_mode=lambda: None, target=lambda: None
    )
    assert isinstance(port, SwitchPort)
    assert port.is_active is False
    hass.states.async_set("switch.heater", STATE_ON)
    assert port.is_active is True
    assert port.self_regulating is False


async def test_switch_port_valve_is_active_when_open(hass: HomeAssistant) -> None:
    hass.states.async_set("valve.loop", "open")
    port = make_port(hass, "valve.loop", role_mode=lambda: None, target=lambda: None)
    assert port.is_active is True


async def test_switch_port_skips_command_when_unavailable(hass: HomeAssistant) -> None:
    from tests import setup_switch  # registers homeassistant.turn_on/off recorders

    calls = setup_switch(hass, True, "switch.heater")
    hass.states.async_set("switch.heater", "unavailable")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)

    await port.async_turn_off(None)

    assert calls == []
```

- [ ] **Step 3: Run test to verify it fails**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "port" -v
```

Expected: FAIL, `ModuleNotFoundError: ...hvac_device.entity_port`.

- [ ] **Step 4: Implement the port module (switch half) and rewire**

Create `custom_components/dual_smart_thermostat/hvac_device/entity_port.py`:

```python
"""How a device role talks to its entity.

The one place that knows what "on" means for an entity and how to command it.
Controllers and devices call these four methods; they never read the entity's
state or call its services themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
import logging
from typing import Callable

from homeassistant.components.climate import HVACMode
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, HomeAssistant
from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition

_LOGGER = logging.getLogger(__name__)


class EntityPort(ABC):
    """What a device role needs from its entity."""

    entity_id: str
    # True when the entity regulates itself and DST must not cycle it.
    self_regulating: bool = False

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Whether the role is currently engaged."""

    @abstractmethod
    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        """Whether the current on/off state has lasted at least min_cycle."""

    @abstractmethod
    async def async_turn_on(self, context: Context | None) -> None:
        """Engage the role."""

    @abstractmethod
    async def async_turn_off(self, context: Context | None) -> None:
        """Disengage the role."""

    async def async_sync(self, context: Context | None) -> None:
        """Mirror DST state onto the entity. Nothing to mirror by default."""
        return

    @abstractmethod
    async def async_stop(self, context: Context | None) -> None:
        """DST is Off: make sure the entity is off. Off means off."""


class SwitchPort(EntityPort):
    """switch / input_boolean / valve style entities (the original behaviour)."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id

    @property
    def _state(self):
        return self.hass.states.get(self.entity_id)

    @property
    def _is_valve(self) -> bool:
        state = self._state
        return state is not None and state.domain == VALVE_DOMAIN

    @property
    def _features(self) -> int:
        state = self._state
        return state.attributes.get("supported_features") if state else 0

    @property
    def _supports_open_valve(self) -> bool:
        return self._is_valve and self._features & ValveEntityFeature.OPEN

    @property
    def _supports_close_valve(self) -> bool:
        return self._is_valve and self._features & ValveEntityFeature.CLOSE

    @property
    def is_active(self) -> bool:
        on_state = STATE_OPEN if self._is_valve else STATE_ON
        return self.hass.states.is_state(self.entity_id, on_state)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        current_state = STATE_ON if self.is_active else HVACMode.OFF
        try:
            return condition.state(self.hass, self.entity_id, current_state, min_cycle)
        except ConditionError:
            return False

    async def async_turn_on(self, context: Context | None) -> None:
        if self._supports_open_valve:
            await self._call(SERVICE_OPEN_VALVE, context)
            return
        if self._unavailable():
            _LOGGER.debug("Skipping turn_on for unavailable entity %s", self.entity_id)
            return
        # Sent even when already on: keep-alive relies on it.
        await self._call(SERVICE_TURN_ON, context)

    async def async_turn_off(self, context: Context | None) -> None:
        if self._supports_close_valve:
            await self._call(SERVICE_CLOSE_VALVE, context)
            return
        if self._unavailable():
            _LOGGER.debug("Skipping turn_off for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_OFF, context)

    async def async_stop(self, context: Context | None) -> None:
        # Today's Off behaviour for switches: stop it if it is running.
        if self.is_active:
            await self.async_turn_off(context)

    def _unavailable(self) -> bool:
        state = self._state
        return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    async def _call(self, service: str, context: Context | None) -> None:
        try:
            await self.hass.services.async_call(
                HA_DOMAIN,
                service,
                {ATTR_ENTITY_ID: self.entity_id},
                context=context,
                blocking=True,
            )
        except Exception as e:  # noqa: BLE001 - same policy as before: log, never raise
            _LOGGER.error("Error calling %s on %s. Error: %s", service, self.entity_id, e)


def make_port(
    hass: HomeAssistant,
    entity_id: str,
    *,
    role_mode: Callable[[], HVACMode | None],
    target: Callable[[], float | None],
) -> EntityPort:
    """Build the port for a role from the entity domain. Climate arrives in task 4."""
    return SwitchPort(hass, entity_id)
```

`SwitchPort._call` copies the original exactly: every command (`turn_on`, `turn_off`, `open_valve`, `close_valve`) went through `HA_DOMAIN` (`homeassistant.<service>`). Move-only means copying the call, not improving it.

Then rewire (each edit is a deletion plus a delegation):

1. `GenericHVACDevice.__init__`: first line after `super().__init__`: 

```python
        self.port = make_port(
            hass,
            entity_id,
            role_mode=self.role_mode,
            target=lambda: getattr(self.environment, self.target_env_attr, None),
        )
```

   Pass it on: `GenericHvacController(self.port, min_cycle_duration, environment, openings, self.async_turn_on, self.async_turn_off)`.
2. Keep `GenericHVACDevice.is_on` (read by `CoolerFanDevice`) as a one-line delegation: `return self.port.is_active`. Delete from `GenericHVACDevice`: `_entity_state`, `_is_valve`, `_entity_features`, `_supports_open_valve`, `_supports_close_valve`, `_async_turn_on_entity`, `_async_turn_off_entity`, `_async_open_valve_entity`, `_async_close_valve_entity`, and the unused imports. Add `def role_mode(self) -> HVACMode | None: return None`.
3. `GenericHVACDevice.async_turn_on` becomes: log; `if self.entity_id is None: return`; `await self.port.async_turn_on(self._context)`. `async_turn_off` likewise, keeping the `hvac_power.update_hvac_power(...)` line after it.
4. `HvacController.__init__` and `GenericHvacController.__init__`: take `port: EntityPort` instead of `hass, entity_id`; set `self.port = port`, `self.hass = ...` is no longer needed. Add `entity_id` property returning `self.port.entity_id`. Replace the `is_active` body with `return self.port.is_active`, `ran_long_enough` with `return self.port.ran_long_enough(self.min_cycle_duration)`, delete `_is_valve`.
5. `HeaterHvacConroller`, `CoolerHvacController`: signature `(port, min_cycle_duration, environment, openings, turn_on_callback, turn_off_callback)` and forward.
6. `HeaterDevice`, `CoolerDevice`, `HeatPumpDevice` (two controllers): construct their controllers with `self.port` instead of `hass, entity_id`.
7. Tests found in step 1 that touched removed helpers use `device.port` instead.

- [ ] **Step 5: Run the port tests and the whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "port" -v
./scripts/docker-test
```

Expected: port tests PASS; **the full suite passes with no other change**. If anything else fails the move was not behaviour-preserving; fix before continuing.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Move entity IO behind EntityPort/SwitchPort (no behaviour change)

Refs #281"
```

---

## Task 4: `ClimateChild` and `ClimatePort` (on_off)

**Files:**
- Modify: `custom_components/dual_smart_thermostat/hvac_device/entity_port.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
import pytest

from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimatePort


def _port(hass, entity_id, mode, target=lambda: 24.0):
    return make_port(hass, entity_id, role_mode=lambda: mode, target=target)


async def test_climate_port_is_active_follows_child_mode(hass: HomeAssistant) -> None:
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    assert isinstance(cool, ClimatePort)
    assert cool.is_active is True
    assert heat.is_active is False  # one mode at a time, by construction


async def test_turn_on_sets_mode_then_pushes_target(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, target=lambda: 24.0)

    await cool.async_turn_on(None)

    assert child.calls == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}),
        ("set_temperature", {"temperature": 24.0}),
    ]
    assert cool.is_active is True


async def test_fan_role_sends_no_target(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    fan = _port(hass, "climate.test_ac", HVACMode.FAN_ONLY, target=lambda: None)

    await fan.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_turn_off_only_when_child_is_in_my_mode(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    await cool.async_turn_off(None)  # idle cooler must not stop the heater
    assert child.calls == []
    assert heat.is_active is True

    await heat.async_turn_off(None)
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF


async def test_stop_turns_the_child_off_in_any_mode(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.FAN_ONLY)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)  # no role owns fan_only here

    await heat.async_turn_off(None)  # role stop: not its mode, nothing happens
    assert child.calls == []

    await heat.async_stop(None)  # Off means off
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF

    await heat.async_stop(None)  # already off: nothing more is sent
    assert child.calls == [("turn_off", {})]


async def test_stop_on_a_switch_only_acts_when_it_is_running(hass: HomeAssistant) -> None:
    from tests import setup_switch

    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)
    await port.async_stop(None)
    assert calls == []

    hass.states.async_set("switch.heater", STATE_ON)
    await port.async_stop(None)
    assert len(calls) == 1


async def test_unavailable_child_gets_no_commands(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    hass.states.async_set("climate.test_ac", "unavailable")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert child.calls == []
    assert cool.is_active is False


async def test_unsupported_mode_is_not_sent(hass: HomeAssistant, caplog) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    child.async_write_ha_state()
    dry = _port(hass, "climate.test_ac", HVACMode.DRY)

    await dry.async_turn_on(None)
    await dry.async_turn_on(None)

    assert child.calls == []
    assert caplog.text.count("does not support") == 1  # logged once


async def test_assumed_child_uses_commanded_mode_not_reported_state(
    hass: HomeAssistant,
) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    assert cool.is_active is False
    await cool.async_turn_on(None)

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF  # no feedback
    assert cool.is_active is True  # DST's own record

    await cool.async_turn_off(None)
    assert cool.is_active is False
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature", "turn_off"]


async def test_ran_long_enough_uses_child_mode_age(hass: HomeAssistant, freezer) -> None:
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    assert cool.ran_long_enough(timedelta(minutes=5)) is False
    freezer.tick(timedelta(minutes=6))
    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_failed_command_rolls_back_the_assumed_record(
    hass: HomeAssistant,
) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    async def boom(**_):
        raise RuntimeError("device offline")

    child.async_set_hvac_mode = boom  # the real service now raises
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert cool.is_active is False
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: FAIL, `ImportError: cannot import name 'ClimatePort'`.

- [ ] **Step 3: Implement**

Add to `entity_port.py`:

```python
import asyncio
from datetime import datetime

from homeassistant.components.climate import ClimateEntityFeature
from homeassistant.core import State
from homeassistant.util import dt as dt_util

from ..climate_roles import is_climate_entity

CLIMATE = "climate"
_CHILDREN_KEY = "dual_smart_thermostat_climate_children"


class ClimateChild:
    """One real climate entity. The only record of its mode, shared by every role.

    Roles never store "am I on": they ask the child, so two roles on the same
    climate cannot both be active. A non-assumed child's reported state is the
    truth. An assumed_state child (IR) never confirms anything, so there DST's
    own last command is the truth.
    """

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self._lock = asyncio.Lock()
        self._commanded: str | None = None
        self._commanded_at: datetime | None = None
        self._last_pushed: float | None = None
        self._warned: set[str] = set()

    @property
    def state(self) -> State | None:
        return self.hass.states.get(self.entity_id)

    @property
    def available(self) -> bool:
        state = self.state
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    @property
    def assumed(self) -> bool:
        state = self.state
        return bool(state and state.attributes.get("assumed_state"))

    def _adopt_reported(self) -> None:
        """First sight of an assumed child: start from what HA restored."""
        if self._commanded is None and self.available:
            self._commanded = self.state.state
            self._commanded_at = self.state.last_changed

    @property
    def mode(self) -> str | None:
        if not self.available:
            return None
        if self.assumed:
            self._adopt_reported()
            return self._commanded
        return self.state.state

    @property
    def since(self) -> datetime | None:
        if not self.available:
            return None
        if self.assumed:
            self._adopt_reported()
            return self._commanded_at
        return self.state.last_changed

    async def async_set_mode(self, mode: str, context: Context | None) -> bool:
        """Command a mode. False when nothing was sent or the call failed."""
        async with self._lock:
            if not self.available:
                _LOGGER.debug("Skipping set_hvac_mode for unavailable %s", self.entity_id)
                return False
            supported = self.state.attributes.get("hvac_modes")
            if supported is not None and mode not in supported:
                if mode not in self._warned:
                    self._warned.add(mode)
                    _LOGGER.warning(
                        "%s does not support hvac mode %s, not sending it",
                        self.entity_id,
                        mode,
                    )
                return False
            # A reported state already in this mode makes a resend pointless; an
            # assumed device cannot report, so keep-alive resends are the point.
            if not self.assumed and self.state.state == mode:
                return True
            before = (self._commanded, self._commanded_at, self._last_pushed)
            self._commanded, self._commanded_at, self._last_pushed = (
                mode,
                dt_util.utcnow(),
                None,  # a mode change may reset the device's setpoint
            )
            try:
                await self.hass.services.async_call(
                    CLIMATE,
                    "set_hvac_mode",
                    {ATTR_ENTITY_ID: self.entity_id, "hvac_mode": mode},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Error setting %s on %s. Error: %s", mode, self.entity_id, e)
                self._commanded, self._commanded_at, self._last_pushed = before
                return False
            return True

    async def async_turn_off(self, context: Context | None) -> None:
        async with self._lock:
            if not self.available:
                return
            before = (self._commanded, self._commanded_at)
            self._commanded, self._commanded_at = HVACMode.OFF, dt_util.utcnow()
            try:
                await self.hass.services.async_call(
                    CLIMATE,
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self.entity_id},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Error turning off %s. Error: %s", self.entity_id, e)
                self._commanded, self._commanded_at = before

    async def async_push_target(self, value: float, context: Context | None) -> None:
        async with self._lock:
            if not self.available:
                return
            features = self.state.attributes.get("supported_features")
            if features is not None and not features & ClimateEntityFeature.TARGET_TEMPERATURE:
                return
            try:
                await self.hass.services.async_call(
                    CLIMATE,
                    "set_temperature",
                    {ATTR_ENTITY_ID: self.entity_id, "temperature": value},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Error setting target on %s. Error: %s", self.entity_id, e)
                return
            self._last_pushed = value


def climate_child(hass: HomeAssistant, entity_id: str) -> ClimateChild:
    """Get or create the single ClimateChild for a real climate entity."""
    children = hass.data.setdefault(_CHILDREN_KEY, {})
    if entity_id not in children:
        children[entity_id] = ClimateChild(hass, entity_id)
    return children[entity_id]


class ClimatePort(EntityPort):
    """One role's view of a (possibly shared) climate entity."""

    def __init__(
        self,
        child: ClimateChild,
        role_mode: Callable[[], HVACMode | None],
        target: Callable[[], float | None],
    ) -> None:
        self._child = child
        self._role_mode = role_mode
        self._target = target
        self.entity_id = child.entity_id

    @property
    def is_active(self) -> bool:
        mode = self._role_mode()
        return mode is not None and self._child.mode == mode

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        since = self._child.since
        return since is not None and dt_util.utcnow() - since >= min_cycle

    async def async_turn_on(self, context: Context | None) -> None:
        if not await self._child.async_set_mode(self._role_mode(), context):
            return
        target = self._target()
        if target is not None:
            await self._child.async_push_target(target, context)

    async def async_turn_off(self, context: Context | None) -> None:
        # Only the role the child is currently serving may stop it, so an idle
        # cooler's keep-alive can never switch off the heater on the same device.
        if self.is_active:
            await self._child.async_turn_off(context)

    async def async_stop(self, context: Context | None) -> None:
        # Off means off: whatever mode the child is in, even one no role owns.
        if self._child.mode not in (None, HVACMode.OFF):
            await self._child.async_turn_off(context)
```

Replace the body of `make_port`:

```python
    if is_climate_entity(entity_id):
        mode = role_mode()
        if mode is None:
            raise ValueError(
                f"{entity_id}: this device role cannot be backed by a climate entity"
            )
        return ClimatePort(climate_child(hass, entity_id), role_mode, target)
    return SwitchPort(hass, entity_id)
```

Note: `role_mode()` is evaluated once here only to refuse roles without a mapping (D2); it is evaluated lazily afterwards. In the tests above `role_mode` lambdas return a mode, and the switch tests pass `lambda: None`, which is fine because switches skip the check.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: PASS. (If `test_failed_command_rolls_back_the_assumed_record` cannot raise through the real service, replace the monkeypatch with `hass.services.async_register` of an erroring `climate.set_hvac_mode` handler and note it in the commit.)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add ClimateChild/ClimatePort: climate-backed role, on_off behaviour

Refs #281"
```

---

## Task 5: Wire roles to modes and run climate roles end to end from YAML

**Files:**
- Modify: `hvac_device/heater_device.py`, `cooler_device.py`, `fan_device.py`, `dryer_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.dual_smart_thermostat.const import DOMAIN

AC = "climate.test_ac"
SENSOR = "sensor.room_temperature"
HEATER = "switch.room_heater"


async def _setup(hass, **config):
    hass.config.units = METRIC_SYSTEM
    base = {
        "platform": DOMAIN,
        "name": "test",
        "target_sensor": SENSOR,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: {**base, **config}})
    await hass.async_block_till_done()


async def test_climate_cooler_cycles_with_switch_heater(hass: HomeAssistant) -> None:
    """Mixed setup: relay heater and climate cooler in one thermostat."""
    from tests import setup_switch

    heater_calls = setup_switch(hass, False, HEATER)
    hass.states.async_set(SENSOR, 22.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}) in child.calls
    assert hass.states.get(AC).state == HVACMode.COOL
    assert hass.states.get("climate.test").attributes["hvac_action"] == "cooling"

    hass.states.async_set(SENSOR, 23.0)  # below target - tolerance
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert heater_calls == []  # the relay heater was never involved


async def test_climate_heater_turns_on_and_off(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 22.0}) in child.calls

    hass.states.async_set(SENSOR, 23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_hvac_off_stops_the_child(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_climate_respects_min_cycle_duration(
    hass: HomeAssistant, freezer
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        min_cycle_duration=timedelta(minutes=5),
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 24.0)  # goal reached, but too soon to stop
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=6))
    hass.states.async_set(SENSOR, 24.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_assumed_state_child_is_not_commanded_twice(hass: HomeAssistant) -> None:
    """IR device: state never confirms, DST must still know it is cooling."""
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (26.5, 27.0, 26.8):  # more sensor ticks while "on"
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("set_hvac_mode") == 1


async def test_unavailable_child_receives_no_commands(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC)
    hass.states.async_set(AC, "unavailable")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == []


@pytest.mark.parametrize(
    ("role", "extra", "mode"),
    [
        ("fan", {"heater": HEATER, "fan_mode": True}, HVACMode.FAN_ONLY),
        (
            "dryer",
            {"heater": HEATER, "humidity_sensor": "sensor.hum", "target_humidity": 40},
            HVACMode.DRY,
        ),
    ],
)
async def test_fan_and_dryer_roles_use_their_climate_mode(
    hass: HomeAssistant, role, extra, mode
) -> None:
    hass.states.async_set(SENSOR, 26.0)
    hass.states.async_set("sensor.hum", 60.0)
    await _setup(hass, **extra, **{role: AC}, initial_hvac_mode=mode)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_hvac_mode(hass, mode, "climate.test")
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": mode}) in child.calls
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "climate_cooler or climate_heater or hvac_off or min_cycle or assumed_state_child or unavailable_child or fan_and_dryer" -v
```

Expected: FAIL: device classes return `role_mode() is None`, so setup raises `ValueError: ... cannot be backed by a climate entity`.

- [ ] **Step 3: Implement**

Add to each device class:

```python
# heater_device.py
    def role_mode(self) -> HVACMode | None:
        return HVACMode.HEAT

# cooler_device.py
    def role_mode(self) -> HVACMode | None:
        return HVACMode.COOL

# fan_device.py  (FanDevice extends CoolerDevice, so it must override)
    def role_mode(self) -> HVACMode | None:
        return HVACMode.FAN_ONLY

# dryer_device.py
    def role_mode(self) -> HVACMode | None:
        return HVACMode.DRY
```

The fan and dryer devices have no temperature target to push. Give them a target provider that returns `None`: in `GenericHVACDevice.__init__` the lambda is `getattr(self.environment, self.target_env_attr, None)`; for the dryer `target_env_attr` is `_target_humidity` which is a humidity, not a setpoint. Guard it on the class: add `pushes_temperature_target: bool = True` on `GenericHVACDevice`, set `False` on `FanDevice` and `DryerDevice`, and build the lambda as `(lambda: ... ) if self.pushes_temperature_target else (lambda: None)`.

`HeatPumpDevice` does not override `role_mode`, so a climate heat pump raises at setup until phase 3; the error message is the user-visible behaviour in the meantime.

- [ ] **Step 4: Run to verify pass, then the whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS everywhere.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Wire heater/cooler/fan/dryer roles to climate modes; mixed setups work

Refs #281"
```

---

## Task 6: Off means off (every Off path calls `async_stop`)

**Files:**
- Modify: `hvac_device/controllable_hvac_device.py`, `hvac_device/generic_hvac_device.py`, `hvac_device/multi_hvac_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_hvac_off_stops_a_child_running_a_mode_no_role_owns(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)  # no fan role

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls].count("turn_off") == 1


async def test_keep_alive_in_off_stops_a_child_set_to_a_foreign_mode(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)

    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert ("turn_off", {}) in child.calls
```

Add a switch regression next to them: with a switch-only heater already off, Off sends no extra service call.

(Imports: `timedelta` and `dt_util` as in the other tests of the file.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "foreign_mode or no_role_owns" -v
```

Expected: FAIL (the child stays `fan_only`: every Off path still asks `is_active` first).

- [ ] **Step 3: Implement**

`GenericHVACDevice`:

```python
    async def async_stop(self) -> None:
        """DST is Off: the entity must end up off, whatever it was doing."""
        if self.entity_id is None:
            return
        await self.port.async_stop(self._context)
        self.hvac_power.update_hvac_power(
            self.strategy, self.target_env_attr, HVACAction.OFF
        )
```

Use it in `GenericHVACDevice.async_control_hvac` (OFF branch: replace `if self.hvac_controller.is_active: ... await self.async_turn_off()` with `await self.async_stop()`) and `_async_check_device_initial_state` (when the mode is OFF).

`ControlableHVACDevice`: declare `async_stop` (abstract) and in `async_set_hvac_mode` replace `if self.is_active: await self.async_turn_off()` in the OFF branch with `await self.async_stop()`.

`MultiHvacDevice`:

```python
    async def async_stop(self) -> None:
        for device in self.hvac_devices:
            await device.async_stop()
```

`async_turn_off_all(time)`: keep the existing keep-alive branch (`time is not None` unconditional `async_turn_off`) and use `async_stop()` otherwise:

```python
        for device in self.hvac_devices:
            if time is not None:
                await device.async_turn_off()
            else:
                await device.async_stop()
```

Wrapper devices that subclass `MultiHvacDevice` inherit it. Switch behaviour is unchanged: `SwitchPort.async_stop` only acts when the switch is active, exactly the old `if is_active` guard.

- [ ] **Step 4: Run to verify pass and the whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Off means off: every Off path stops climate children in any mode

Refs #281"
```

---

## Task 7: Lint and phase wrap-up

- [ ] **Step 1: Lint**

```bash
./scripts/docker-lint --fix
./scripts/docker-lint
```

Expected: clean. Fix anything flagged (the `# noqa: BLE001` comments exist because the codebase's policy for service failures is log-and-continue).

- [ ] **Step 2: Full suite**

```bash
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "Lint fixes for climate port seam

Refs #281"
```

## Acceptance (phase 1)

1. Existing suite passes unchanged apart from tests that referenced removed device helpers (now via `device.port`).
2. YAML `cooler: climate.x` / `heater: climate.x` / `fan:` / `dryer:` set the child's hvac mode, push the target, and turn it off with `climate.turn_off`.
3. Mixed climate cooler + switch heater cycles independently.
4. Unavailable child: no calls. `assumed_state` child: control works from DST's own record, one `set_hvac_mode` per engagement.
5. `min_cycle_duration` respected on climate roles.
6. A device class with no role mode cannot be built on a climate entity (clear setup error).
7. DST Off turns every climate child off whatever mode it is in; a role's own stop stays scoped to its mode; switch behaviour is unchanged.
