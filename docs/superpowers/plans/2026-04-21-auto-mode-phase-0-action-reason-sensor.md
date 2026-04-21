# Auto Mode — Phase 0: `hvac_action_reason` Sensor Entity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose each climate entity's `hvac_action_reason` as a diagnostic enum sensor entity (dual-exposed with the existing deprecated state attribute), and declare three new `HVACActionReasonAuto` enum values reserved for Phase 1.

**Architecture:** Add a new `sensor` platform that registers one `HvacActionReasonSensor` per climate instance. The climate entity fan-outs every assignment to `self._hvac_action_reason` onto a new dispatcher signal keyed by the climate's `unique_id`; the sensor subscribes to that signal and mirrors the value as its enum `native_value`. Both config-entry and legacy YAML setup paths are supported.

**Tech Stack:** Python 3.13, Home Assistant 2025.1.0+, `homeassistant.components.sensor.SensorEntity` + `RestoreEntity`, `homeassistant.helpers.dispatcher`, `homeassistant.helpers.discovery` (for YAML path).

**Spec:** `docs/superpowers/specs/2026-04-21-auto-mode-phase-0-action-reason-sensor-design.md`

---

## Testing Environment

This repo runs tests and lint only inside Docker. Use **these two commands** everywhere in this plan:

```bash
./scripts/docker-test <pytest-args>      # e.g. ./scripts/docker-test tests/foo.py::test_bar
./scripts/docker-lint                    # full lint check
./scripts/docker-lint --fix              # auto-fix lint issues
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly — those will not use the pinned HA version.

---

## Shared Key Concept: `sensor_key`

Every climate has a stable identifier we can use for dispatcher signals, available at setup time:

- **Config-entry path:** `config_entry.entry_id` (a UUID-like string).
- **YAML path:** `config.get(CONF_UNIQUE_ID)` if set, else the climate `name` (from `config[CONF_NAME]`).

This derived value is called the **`sensor_key`** throughout this plan. It's what the dispatcher signal is formatted with and what the sensor uses as its `unique_id` base. Both climate and sensor compute it identically.

---

## Task 1: Create `HVACActionReasonAuto` enum + merge into aggregate

**Files:**
- Create: `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason_auto.py`
- Modify: `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason.py`
- Test: `tests/test_hvac_action_reason_sensor.py` (new file; will be expanded in later tasks)

- [ ] **Step 1: Write the failing test**

Create `tests/test_hvac_action_reason_sensor.py`:

```python
"""Tests for the hvac_action_reason sensor entity (Phase 0)."""

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_auto import (
    HVACActionReasonAuto,
)


def test_hvac_action_reason_auto_values_exist() -> None:
    """Auto-mode enum declares the three Phase 1 reserved values."""
    assert HVACActionReasonAuto.AUTO_PRIORITY_HUMIDITY == "auto_priority_humidity"
    assert HVACActionReasonAuto.AUTO_PRIORITY_TEMPERATURE == "auto_priority_temperature"
    assert HVACActionReasonAuto.AUTO_PRIORITY_COMFORT == "auto_priority_comfort"


def test_hvac_action_reason_aggregate_includes_auto_values() -> None:
    """The top-level HVACActionReason aggregates Auto values alongside Internal/External."""
    assert HVACActionReason.AUTO_PRIORITY_HUMIDITY == "auto_priority_humidity"
    assert HVACActionReason.AUTO_PRIORITY_TEMPERATURE == "auto_priority_temperature"
    assert HVACActionReason.AUTO_PRIORITY_COMFORT == "auto_priority_comfort"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_auto'`.

- [ ] **Step 3: Create the new enum module**

Create `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason_auto.py`:

```python
import enum


class HVACActionReasonAuto(enum.StrEnum):
    """Auto-mode-selected HVAC Action Reason.

    Values declared in Phase 0 and reserved for Auto Mode (Phase 1). They
    appear in the sensor's ``options`` list but are not emitted by any
    controller until Phase 1 wires the priority evaluation engine.
    """

    AUTO_PRIORITY_HUMIDITY = "auto_priority_humidity"

    AUTO_PRIORITY_TEMPERATURE = "auto_priority_temperature"

    AUTO_PRIORITY_COMFORT = "auto_priority_comfort"
```

- [ ] **Step 4: Merge Auto values into aggregate `HVACActionReason`**

Replace the full contents of `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason.py` with:

```python
import enum
from itertools import chain

from ..hvac_action_reason.hvac_action_reason_auto import HVACActionReasonAuto
from ..hvac_action_reason.hvac_action_reason_external import HVACActionReasonExternal
from ..hvac_action_reason.hvac_action_reason_internal import HVACActionReasonInternal

SET_HVAC_ACTION_REASON_SIGNAL = "set_hvac_action_reason_signal_{}"
SERVICE_SET_HVAC_ACTION_REASON = "set_hvac_action_reason"


class HVACActionReason(enum.StrEnum):
    """HVAC Action Reason for climate devices."""

    _ignore_ = "member cls"
    cls = vars()
    for member in chain(
        list(HVACActionReasonInternal),
        list(HVACActionReasonExternal),
        list(HVACActionReasonAuto),
    ):
        cls[member.name] = member.value

    NONE = ""
```

- [ ] **Step 5: Run test to verify it passes**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason_auto.py \
        custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason.py \
        tests/test_hvac_action_reason_sensor.py
git commit -m "feat(auto-mode): declare HVACActionReasonAuto enum values

Phase 0 (#563): reserve AUTO_PRIORITY_HUMIDITY, AUTO_PRIORITY_TEMPERATURE,
AUTO_PRIORITY_COMFORT. Not emitted until Phase 1."
```

---

## Task 2: Add the sensor dispatcher signal constant

**Files:**
- Modify: `custom_components/dual_smart_thermostat/const.py`
- Test: `tests/test_hvac_action_reason_sensor.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hvac_action_reason_sensor.py`:

```python
from custom_components.dual_smart_thermostat.const import (
    SET_HVAC_ACTION_REASON_SENSOR_SIGNAL,
)


def test_sensor_signal_constant_has_placeholder() -> None:
    """Signal template has one {} placeholder for the sensor_key."""
    assert "{}" in SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
    # Sanity — format with a sample key must produce a distinct, stable string.
    formatted = SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123")
    assert formatted.endswith("abc123")
    assert formatted != SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py::test_sensor_signal_constant_has_placeholder -v
```

Expected: FAIL — `ImportError: cannot import name 'SET_HVAC_ACTION_REASON_SENSOR_SIGNAL'`.

- [ ] **Step 3: Add the constant**

Add near the existing `ATTR_HVAC_ACTION_REASON = "hvac_action_reason"` line (around line 136) in `custom_components/dual_smart_thermostat/const.py`:

```python
# Dispatcher signal used to mirror the climate entity's _hvac_action_reason value
# onto its companion HvacActionReasonSensor entity. Formatted with the
# climate's sensor_key (config_entry.entry_id or CONF_UNIQUE_ID or CONF_NAME).
SET_HVAC_ACTION_REASON_SENSOR_SIGNAL = "set_hvac_action_reason_sensor_signal_{}"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py::test_sensor_signal_constant_has_placeholder -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/const.py tests/test_hvac_action_reason_sensor.py
git commit -m "feat(auto-mode): add sensor-mirror dispatcher signal constant

Phase 0 (#563): SET_HVAC_ACTION_REASON_SENSOR_SIGNAL is formatted with the
climate's sensor_key and broadcasts every hvac_action_reason change to the
companion sensor entity."
```

---

## Task 3: Create the `HvacActionReasonSensor` entity class

**Files:**
- Create: `custom_components/dual_smart_thermostat/sensor.py` (initial class only — platform wiring added in later tasks)
- Test: `tests/test_hvac_action_reason_sensor.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hvac_action_reason_sensor.py`:

```python
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_external import (
    HVACActionReasonExternal,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
)
from custom_components.dual_smart_thermostat.sensor import HvacActionReasonSensor


def test_sensor_entity_defaults() -> None:
    """The sensor entity exposes the correct ENUM contract and defaults."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")

    assert sensor.device_class == SensorDeviceClass.ENUM
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.unique_id == "abc123_hvac_action_reason"
    assert sensor.translation_key == "hvac_action_reason"
    # Default native_value is the "none" string (empty enum value).
    assert sensor.native_value == HVACActionReason.NONE


def test_sensor_options_contains_all_reason_values() -> None:
    """options contains every Internal + External + Auto reason plus 'none'."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")

    options = set(sensor.options or [])
    # Every enum value from each sub-category must be present.
    for value in HVACActionReasonInternal:
        assert value.value in options, f"missing internal: {value.value}"
    for value in HVACActionReasonExternal:
        assert value.value in options, f"missing external: {value.value}"
    for value in HVACActionReasonAuto:
        assert value.value in options, f"missing auto: {value.value}"
    # NONE is the empty string — it must also be an allowed option.
    assert HVACActionReason.NONE in options
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.dual_smart_thermostat.sensor'`.

- [ ] **Step 3: Create `sensor.py` with the entity class**

Create `custom_components/dual_smart_thermostat/sensor.py`:

```python
"""Sensor platform for dual_smart_thermostat.

Phase 0 of the Auto Mode roadmap (#563): exposes each climate entity's
``hvac_action_reason`` value as a diagnostic enum sensor entity. The sensor
is dual-exposed alongside the existing (deprecated) climate state attribute.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
from .hvac_action_reason.hvac_action_reason import HVACActionReason
from .hvac_action_reason.hvac_action_reason_auto import HVACActionReasonAuto
from .hvac_action_reason.hvac_action_reason_external import HVACActionReasonExternal
from .hvac_action_reason.hvac_action_reason_internal import HVACActionReasonInternal

_LOGGER = logging.getLogger(__name__)


def _build_options() -> list[str]:
    """Return every valid sensor state value (sorted for stability)."""
    values: set[str] = {HVACActionReason.NONE}
    for enum_cls in (
        HVACActionReasonInternal,
        HVACActionReasonExternal,
        HVACActionReasonAuto,
    ):
        for member in enum_cls:
            values.add(member.value)
    return sorted(values)


_OPTIONS = _build_options()


class HvacActionReasonSensor(SensorEntity, RestoreEntity):
    """Diagnostic enum sensor that mirrors a climate's hvac_action_reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_translation_key = "hvac_action_reason"

    def __init__(self, sensor_key: str, name: str) -> None:
        """Initialise the sensor.

        Args:
            sensor_key: The climate's stable identifier (config entry id,
                unique_id, or name). Used to build unique_id and subscribe
                to the mirror signal.
            name: Human-readable base name, usually the climate's name.
        """
        self._sensor_key = sensor_key
        self._attr_name = f"{name} HVAC Action Reason"
        self._attr_unique_id = f"{sensor_key}_hvac_action_reason"
        self._attr_options = list(_OPTIONS)
        self._attr_native_value = HVACActionReason.NONE
        self._remove_signal: callable | None = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: PASS for Task 3 tests. (Earlier tests continue to pass.)

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/sensor.py tests/test_hvac_action_reason_sensor.py
git commit -m "feat(auto-mode): add HvacActionReasonSensor entity class

Phase 0 (#563): diagnostic enum sensor that mirrors each climate entity's
hvac_action_reason value. Platform wiring in follow-up commits."
```

---

## Task 4: Signal handling + invalid-value guard

**Files:**
- Modify: `custom_components/dual_smart_thermostat/sensor.py`
- Test: `tests/test_hvac_action_reason_sensor.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hvac_action_reason_sensor.py`:

```python
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.dual_smart_thermostat.const import (
    SET_HVAC_ACTION_REASON_SENSOR_SIGNAL,
)


async def test_sensor_updates_state_on_valid_signal(hass: HomeAssistant) -> None:
    """A valid reason dispatched on the signal updates native_value."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")
    sensor.hass = hass
    # Simulate entity being added to hass (subscribes to the signal).
    await sensor.async_added_to_hass()

    async_dispatcher_send(
        hass,
        SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
        HVACActionReasonInternal.TARGET_TEMP_REACHED,
    )
    await hass.async_block_till_done()

    assert sensor.native_value == HVACActionReasonInternal.TARGET_TEMP_REACHED


async def test_sensor_ignores_invalid_signal_value(
    hass: HomeAssistant, caplog
) -> None:
    """An invalid reason is logged as a warning and state is preserved."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")
    sensor.hass = hass
    await sensor.async_added_to_hass()

    # Prime the sensor with a known valid value.
    async_dispatcher_send(
        hass,
        SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
        HVACActionReasonInternal.TARGET_TEMP_REACHED,
    )
    await hass.async_block_till_done()

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        async_dispatcher_send(
            hass,
            SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
            "this_is_not_a_real_reason",
        )
        await hass.async_block_till_done()

    # State preserved.
    assert sensor.native_value == HVACActionReasonInternal.TARGET_TEMP_REACHED
    # A warning was logged.
    assert any(
        "Invalid hvac_action_reason" in rec.message for rec in caplog.records
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: the two new tests FAIL (signal handler not yet connected; sensor state unchanged).

- [ ] **Step 3: Implement `async_added_to_hass`, signal handler, and unload**

Replace the `HvacActionReasonSensor` class in `custom_components/dual_smart_thermostat/sensor.py` with the following version (adds lifecycle + signal handler — earlier attribute declarations preserved):

```python
class HvacActionReasonSensor(SensorEntity, RestoreEntity):
    """Diagnostic enum sensor that mirrors a climate's hvac_action_reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_translation_key = "hvac_action_reason"

    def __init__(self, sensor_key: str, name: str) -> None:
        """Initialise the sensor."""
        self._sensor_key = sensor_key
        self._attr_name = f"{name} HVAC Action Reason"
        self._attr_unique_id = f"{sensor_key}_hvac_action_reason"
        self._attr_options = list(_OPTIONS)
        self._attr_native_value = HVACActionReason.NONE
        self._remove_signal: callable | None = None

    async def async_added_to_hass(self) -> None:
        """Restore previous state (if any) and subscribe to the mirror signal."""
        await super().async_added_to_hass()

        # Restore last persisted state.
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self._attr_options:
            self._attr_native_value = last_state.state
        else:
            if last_state is not None:
                _LOGGER.debug(
                    "Ignoring unknown restored state %s for %s; defaulting to none",
                    last_state.state,
                    self.entity_id,
                )
            self._attr_native_value = HVACActionReason.NONE

        # Local import avoids circular imports at module load time.
        from homeassistant.helpers.dispatcher import async_dispatcher_connect

        self._remove_signal = async_dispatcher_connect(
            self.hass,
            SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format(self._sensor_key),
            self._handle_reason_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the mirror signal."""
        if self._remove_signal is not None:
            self._remove_signal()
            self._remove_signal = None
        await super().async_will_remove_from_hass()

    def _handle_reason_update(self, reason) -> None:
        """Update native_value from a dispatched reason; ignore invalid values."""
        # Normalise None to NONE (empty enum value).
        if reason is None:
            reason = HVACActionReason.NONE

        # Coerce StrEnum members to their underlying string for comparison.
        value = reason.value if hasattr(reason, "value") else str(reason)

        if value not in self._attr_options:
            _LOGGER.warning(
                "Invalid hvac_action_reason %s for %s; ignoring",
                value,
                self.entity_id,
            )
            return

        self._attr_native_value = value
        if self.hass is not None:
            self.async_write_ha_state()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: all tests in this file PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/sensor.py tests/test_hvac_action_reason_sensor.py
git commit -m "feat(auto-mode): wire sensor signal handler + invalid-value guard

Phase 0 (#563): sensor subscribes to SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
on add, validates incoming values against its options list, and logs a
warning while preserving state on invalid values."
```

---

## Task 5: Wire up sensor platform (config entry + YAML paths)

**Files:**
- Modify: `custom_components/dual_smart_thermostat/__init__.py`
- Modify: `custom_components/dual_smart_thermostat/sensor.py`
- Modify: `custom_components/dual_smart_thermostat/climate.py`
- Test: `tests/test_hvac_action_reason_sensor.py` (extend — integration via YAML fixture)

This task adds both setup paths so existing YAML tests can be extended with parallel sensor assertions in Task 7.

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_hvac_action_reason_sensor.py`:

```python
import pytest

from tests import setup_comp_heat  # noqa: F401
from tests import common


@pytest.mark.asyncio
async def test_sensor_created_alongside_climate_yaml(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """YAML setup_comp_heat creates a companion sensor and initialises to 'none'."""
    sensor_entity_id = "sensor.test_hvac_action_reason"
    state = hass.states.get(sensor_entity_id)
    assert state is not None, f"{sensor_entity_id} was not created"
    assert state.state == HVACActionReason.NONE


@pytest.mark.asyncio
async def test_sensor_mirrors_external_service_call(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Calling set_hvac_action_reason updates the sensor entity state."""
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.PRESENCE
    )
    await hass.async_block_till_done()

    sensor_state = hass.states.get("sensor.test_hvac_action_reason")
    assert sensor_state is not None
    assert sensor_state.state == HVACActionReasonExternal.PRESENCE
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: the two new tests FAIL — sensor entity is not registered yet.

- [ ] **Step 3: Register `Platform.SENSOR` in `__init__.py`**

Replace `custom_components/dual_smart_thermostat/__init__.py` with:

```python
"""The dual_smart_thermostat component."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

DOMAIN = "dual_smart_thermostat"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- [ ] **Step 4: Implement `async_setup_entry` + `async_setup_platform` in `sensor.py`**

Append to `custom_components/dual_smart_thermostat/sensor.py` (below the `HvacActionReasonSensor` class):

```python
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


def _derive_sensor_key(config: dict[str, Any], fallback_name: str) -> str:
    """Return the stable key used by both climate and sensor for signalling.

    Preference order: config_entry.entry_id > CONF_UNIQUE_ID > CONF_NAME.
    The caller supplies ``fallback_name`` as the last-resort value.
    """
    return config.get(CONF_UNIQUE_ID) or fallback_name


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the companion action-reason sensor for a config entry."""
    config = {**config_entry.data, **config_entry.options}
    name = config.get(CONF_NAME, "dual_smart_thermostat")
    sensor_key = config_entry.entry_id

    async_add_entities([HvacActionReasonSensor(sensor_key=sensor_key, name=name)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create the companion action-reason sensor for a YAML-discovered climate."""
    if discovery_info is None:
        # This platform is only instantiated via discovery from climate.py.
        return

    name = discovery_info["name"]
    sensor_key = discovery_info["sensor_key"]

    async_add_entities([HvacActionReasonSensor(sensor_key=sensor_key, name=name)])
```

- [ ] **Step 5: Trigger sensor platform from YAML climate setup**

In `custom_components/dual_smart_thermostat/climate.py`:

(a) At the top of the file, add imports (next to the other `homeassistant.helpers` imports):

```python
from homeassistant.helpers import discovery
```

(b) In `_async_setup_config` (around line 445, right **after** the `async_add_entities([...DualSmartThermostat(...)...])` call and **before** the `# Service to set HVACActionReason.` block), add:

```python
    # Load the companion sensor platform via discovery. For YAML setups we
    # don't have a config entry id, so we derive a stable sensor_key from
    # CONF_UNIQUE_ID (if set) or the climate name.
    sensor_key = unique_id or name
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            "sensor",
            DOMAIN,
            {"name": name, "sensor_key": sensor_key},
            config,
        )
    )
```

(c) Also stash the `sensor_key` on the created `DualSmartThermostat` so it knows where to dispatch later (Task 6). Modify the `async_add_entities([...])` call in `_async_setup_config` to set the attribute immediately after creation:

```python
    thermostat = DualSmartThermostat(
        name,
        sensor_entity_id,
        sensor_floor_entity_id,
        sensor_outside_entity_id,
        sensor_humidity_entity_id,
        sensor_stale_duration,
        sensor_heat_pump_cooling_entity_id,
        keep_alive,
        has_min_cycle,
        precision,
        unit,
        unique_id,
        hvac_device,
        preset_manager,
        environment_manager,
        opening_manager,
        feature_manager,
        hvac_power_manager,
    )
    thermostat._action_reason_sensor_key = sensor_key
    async_add_entities([thermostat])
```

(Replace the existing `async_add_entities([DualSmartThermostat(...)])` block with the above.)

- [ ] **Step 6: Run tests to verify they pass**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: `test_sensor_created_alongside_climate_yaml` PASSES. `test_sensor_mirrors_external_service_call` still FAILS — dispatch wiring is Task 6.

- [ ] **Step 7: Commit**

```bash
git add custom_components/dual_smart_thermostat/__init__.py \
        custom_components/dual_smart_thermostat/sensor.py \
        custom_components/dual_smart_thermostat/climate.py \
        tests/test_hvac_action_reason_sensor.py
git commit -m "feat(auto-mode): register sensor platform for both setup paths

Phase 0 (#563): add Platform.SENSOR to PLATFORMS for config-entry setups,
and load via discovery.async_load_platform from the YAML climate path.
Sensor key uses config_entry.entry_id (config entry) or unique_id/name
(YAML)."
```

---

## Task 6: Dispatch sensor signal from climate on every `_hvac_action_reason` change

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py`
- Test: `tests/test_hvac_action_reason_sensor.py` (the `test_sensor_mirrors_external_service_call` from Task 5 should pass after this)

- [ ] **Step 1: Confirm the target test is currently failing**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py::test_sensor_mirrors_external_service_call -v
```

Expected: FAIL (sensor still reports "none").

- [ ] **Step 2: Add a central dispatch helper on the climate entity**

In `custom_components/dual_smart_thermostat/climate.py`:

(a) Add the new signal import alongside the existing `SET_HVAC_ACTION_REASON_SIGNAL` import (around line 128):

```python
from .const import (
    ...  # existing imports kept
    SET_HVAC_ACTION_REASON_SENSOR_SIGNAL,
)
```

(The `const.py` module already defines it from Task 2; just add it to whichever existing `from .const import (...)` block is nearest. If there is no block for `const.py` at that spot, adapt to the existing import pattern in `climate.py`.)

(b) Add imports for `async_dispatcher_send` if not already present in the file. Search for `dispatcher_send` — if only the non-async variant is imported, add:

```python
from homeassistant.helpers.dispatcher import async_dispatcher_send
```

(c) Inside the `DualSmartThermostat` class, add a helper method (place it near `_set_hvac_action_reason` around line 1675):

```python
    def _publish_hvac_action_reason(self, reason) -> None:
        """Mirror the current hvac_action_reason onto the companion sensor.

        Invoked after every assignment to ``self._hvac_action_reason`` so the
        ``HvacActionReasonSensor`` entity stays in sync. Silently no-ops if
        the sensor key was never assigned (defensive; should not happen in
        normal setup).
        """
        sensor_key = getattr(self, "_action_reason_sensor_key", None)
        if sensor_key is None:
            return
        async_dispatcher_send(
            self.hass,
            SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format(sensor_key),
            reason,
        )
```

(d) Call `self._publish_hvac_action_reason(...)` after every assignment to `self._hvac_action_reason`. From the earlier grep, the assignments are at lines **590, 906, 1195, 1334, 1364, 1385, 1459, 1563, 1685**. For each of those lines, add the dispatch call on the next line. Example for line 1685 inside `_set_hvac_action_reason`:

```python
        self._hvac_action_reason = reason
        self._publish_hvac_action_reason(reason)

        self.schedule_update_ha_state(True)
```

Apply the same pattern to all nine assignments. The __init__ assignment at line 590 does **not** need dispatch (hass isn't attached yet) — skip that one.

**Final list of assignments to wrap with a publish call (8 total):**

- line 906 — restore path (`self._hvac_action_reason = old_state.attributes.get(ATTR_HVAC_ACTION_REASON)`)
- line 1195
- line 1334
- line 1364 (sensor stalled)
- line 1385 (humidity sensor stalled)
- line 1459
- line 1563
- line 1685 (external service signal handler)

Each becomes:

```python
self._hvac_action_reason = <expression>
self._publish_hvac_action_reason(self._hvac_action_reason)
```

For the restore path (906), dispatch the value *after* restoration so the sensor converges once it is added. The sensor may be added before or after the climate — the restore handler in the sensor (Task 4) handles the pre-add case from its own last_state.

- [ ] **Step 3: Run the failing test to verify it now passes**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: all tests in this file PASS.

- [ ] **Step 4: Run the broader test suite for regressions**

```bash
./scripts/docker-test tests/test_hvac_action_reason_service.py -v
./scripts/docker-test tests/test_heater_mode.py -v
```

Expected: both files PASS (no behavioural regression from the added dispatch calls).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py
git commit -m "feat(auto-mode): mirror hvac_action_reason onto sensor

Phase 0 (#563): every assignment to self._hvac_action_reason now fans out
on SET_HVAC_ACTION_REASON_SENSOR_SIGNAL so the companion sensor stays in
sync. Legacy state attribute is still populated unchanged."
```

---

## Task 7: Add sensor restoration test + extend legacy service tests in parallel

**Files:**
- Modify: `tests/test_hvac_action_reason_sensor.py` (restore test)
- Modify: `tests/test_hvac_action_reason_service.py` (parallel sensor assertions)
- Modify: `tests/common.py` (sensor helpers)

- [ ] **Step 1: Add sensor helpers to `tests/common.py`**

Add near the end of `tests/common.py` (before the `threadsafe_callback_factory` helper at line 250):

```python
def get_action_reason_sensor_entity_id(climate_entity_id: str) -> str:
    """Return the expected hvac_action_reason sensor entity id for a climate.

    The sensor's object id mirrors the climate's object id plus the
    '_hvac_action_reason' suffix.
    """
    _, object_id = climate_entity_id.split(".", 1)
    return f"sensor.{object_id}_hvac_action_reason"


def get_action_reason_sensor_state(hass, climate_entity_id: str):
    """Return the current state string of the companion action-reason sensor."""
    sensor_state = hass.states.get(
        get_action_reason_sensor_entity_id(climate_entity_id)
    )
    return sensor_state.state if sensor_state is not None else None
```

- [ ] **Step 2: Write the failing restore test**

Append to `tests/test_hvac_action_reason_sensor.py`:

```python
from pytest_homeassistant_custom_component.common import mock_restore_cache
from homeassistant.core import State


@pytest.mark.asyncio
async def test_sensor_restores_last_state(hass: HomeAssistant) -> None:
    """The sensor restores its previous enum value across restarts."""
    sensor_entity_id = "sensor.test_hvac_action_reason"
    mock_restore_cache(
        hass,
        (State(sensor_entity_id, HVACActionReasonInternal.TARGET_TEMP_REACHED),),
    )

    hass.config.units = hass.config.units  # keep metric (set by fixture normally)
    from homeassistant.components.climate import DOMAIN as CLIMATE
    from homeassistant.setup import async_setup_component
    from custom_components.dual_smart_thermostat.const import DOMAIN

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "heat",
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(sensor_entity_id)
    assert state is not None
    assert state.state == HVACActionReasonInternal.TARGET_TEMP_REACHED
```

- [ ] **Step 3: Run the restore test to verify it fails**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py::test_sensor_restores_last_state -v
```

Expected: PASS if everything is wired correctly. If it FAILS (e.g. restore cache not being consulted), investigate `async_added_to_hass` implementation from Task 4 — it should already read `async_get_last_state()`.

If it passes immediately: good, the implementation is complete. If not, the fix is to ensure the sensor's `async_added_to_hass` (already written in Task 4) is being invoked. Verify by adding a breakpoint or log line.

- [ ] **Step 4: Extend the legacy service tests with parallel sensor assertions**

In `tests/test_hvac_action_reason_service.py`, add the import at the top:

```python
from . import common  # already imported; ensure get_action_reason_sensor_state is available
```

Then, for each of the four existing tests (`test_service_set_hvac_action_reason_presence`, `_schedule`, `_emergency`, `_malfunction`), add a parallel sensor assertion immediately **after** the existing attribute assertion. Example for PRESENCE:

```python
async def test_service_set_hvac_action_reason_presence(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test setting HVAC action reason to PRESENCE."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE
    # Sensor mirrors the attribute.
    assert (
        common.get_action_reason_sensor_state(hass, common.ENTITY)
        == HVACActionReason.NONE
    )

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.PRESENCE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.PRESENCE
    )
    # Sensor mirrors the attribute.
    assert (
        common.get_action_reason_sensor_state(hass, common.ENTITY)
        == HVACActionReasonExternal.PRESENCE
    )
```

Apply the same parallel assertion pattern to the other three tests (SCHEDULE, EMERGENCY, MALFUNCTION). Keep every existing attribute assertion in place.

- [ ] **Step 5: Run all affected tests**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py tests/test_hvac_action_reason_service.py -v
```

Expected: all tests PASS (both legacy attribute + new sensor surfaces verified in the same scenarios).

- [ ] **Step 6: Commit**

```bash
git add tests/common.py \
        tests/test_hvac_action_reason_sensor.py \
        tests/test_hvac_action_reason_service.py
git commit -m "test(auto-mode): add sensor restore + parallel legacy assertions

Phase 0 (#563): verifies the new sensor surface is kept in sync with the
deprecated attribute surface in every existing external-service scenario,
and that restore across restarts works."
```

---

## Task 8: Sensor state translations (en + sk)

**Files:**
- Modify: `custom_components/dual_smart_thermostat/translations/en.json`
- Modify: `custom_components/dual_smart_thermostat/translations/sk.json`

- [ ] **Step 1: Update `translations/en.json`**

Insert an `"entity"` block at the **top level** of the JSON (sibling of `"title"`, `"config"`, `"services"`). Place it immediately after the `"title"` line:

```json
    "entity": {
        "sensor": {
            "hvac_action_reason": {
                "state": {
                    "": "None",
                    "min_cycle_duration_not_reached": "Min cycle duration not reached",
                    "target_temp_not_reached": "Target temperature not reached",
                    "target_temp_reached": "Target temperature reached",
                    "target_temp_not_reached_with_fan": "Target temperature not reached (fan assist)",
                    "target_humidity_not_reached": "Target humidity not reached",
                    "target_humidity_reached": "Target humidity reached",
                    "misconfiguration": "Misconfiguration",
                    "opening": "Opening detected",
                    "limit": "Limit reached",
                    "overheat": "Overheat protection",
                    "temperature_sensor_stalled": "Temperature sensor stalled",
                    "humidity_sensor_stalled": "Humidity sensor stalled",
                    "presence": "Presence",
                    "schedule": "Schedule",
                    "emergency": "Emergency",
                    "malfunction": "Malfunction",
                    "auto_priority_humidity": "Auto: humidity priority",
                    "auto_priority_temperature": "Auto: temperature priority",
                    "auto_priority_comfort": "Auto: comfort priority"
                }
            }
        }
    },
```

(Mind the trailing comma — `"title"` must also end with a comma now.)

- [ ] **Step 2: Mirror the block in `translations/sk.json`**

Open `custom_components/dual_smart_thermostat/translations/sk.json` and add the identical `"entity"` block (English fallback values are acceptable for Phase 0 — full Slovak translations are left to translators).

- [ ] **Step 3: Validate the JSON files parse**

```bash
./scripts/docker-test tests/test_hvac_action_reason_sensor.py -v
```

Expected: PASS (any JSON parse error at HA load would surface as a setup failure).

- [ ] **Step 4: Commit**

```bash
git add custom_components/dual_smart_thermostat/translations/en.json \
        custom_components/dual_smart_thermostat/translations/sk.json
git commit -m "feat(auto-mode): add sensor state translations (en, sk)

Phase 0 (#563): user-facing labels for every hvac_action_reason enum
value. Slovak mirrors English as a placeholder until translated."
```

---

## Task 9: Update README — exposure, reserved Auto values, service

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace the `## HVAC Action Reason` section (starting at line 613)**

In `README.md`, locate the line `## HVAC Action Reason` (around line 613). Replace the section through the end of `#### HVAC Action Reason External values` with:

```markdown
## HVAC Action Reason

The `dual_smart_thermostat` tracks **why** the current HVAC action is happening and exposes it in two places:

- **Sensor entity (preferred):** `sensor.<climate_name>_hvac_action_reason` — a diagnostic enum sensor created automatically alongside each climate entity. Use this for automations, templates, and dashboards going forward.
- **State attribute (deprecated):** `hvac_action_reason` on the climate entity. Still populated for backward compatibility; slated for removal in a future major release. Please migrate templates and automations to the sensor entity above.

Both surfaces carry the same raw enum value at all times.

### HVAC Action Reason values

The reason is grouped into three categories:

- [Internal values](#hvac-action-reason-internal-values) — set by the component itself.
- [External values](#hvac-action-reason-external-values) — set by automations or scripts via the `set_hvac_action_reason` service.
- [Auto values](#hvac-action-reason-auto-values) — reserved for Auto Mode (Phase 1 of the Auto Mode roadmap, issue #563). Declared in the sensor's options list but not yet emitted by any controller.

#### HVAC Action Reason Internal values

| Value | Description |
|-------|-------------|
| `none` | No action reason |
| `target_temp_not_reached` | The target temperature has not been reached |
| `target_temp_not_reached_with_fan` | The target temperature has not been reached trying it with a fan |
| `target_temp_reached` | The target temperature has been reached |
| `target_humidity_not_reached` | The target humidity has not been reached |
| `target_humidity_reached` | The target humidity has been reached |
| `misconfiguration` | The thermostat is misconfigured |
| `opening` | An opening (window/door) was detected as open |
| `limit` | A configured limit (floor temp, etc.) was hit |
| `overheat` | Overheat protection engaged |
| `min_cycle_duration_not_reached` | Minimum cycle duration not reached yet |
| `temperature_sensor_stalled` | Temperature sensor has not reported data within the stale window |
| `humidity_sensor_stalled` | Humidity sensor has not reported data within the stale window |

#### HVAC Action Reason External values

| Value | Description |
|-------|-------------|
| `none` | No action reason |
| `presence`| The last HVAC action was triggered by presence |
| `schedule` | The last HVAC action was triggered by schedule |
| `emergency` | The last HVAC action was triggered by emergency |
| `malfunction` | The last HVAC action was triggered by a malfunction |

#### HVAC Action Reason Auto values

> **Reserved.** These values are declared so the sensor's `options` list is stable across Auto Mode development phases. They are **not yet emitted** by any controller. Phase 1 (see issue #563) will wire the priority engine to emit them.

| Value | Description |
|-------|-------------|
| `auto_priority_humidity` | Auto Mode prioritised humidity control (→ DRY) |
| `auto_priority_temperature` | Auto Mode prioritised temperature control (→ HEAT / COOL) |
| `auto_priority_comfort` | Auto Mode chose fan for comfort (→ FAN_ONLY) |
```

(Keep the existing heavy-detail row text from the current README for the internal table — in particular the specific phrasing of each description. The block above preserves them. Cross-check after editing.)

- [ ] **Step 2: Update the `### Set HVAC Action Reason` service section (around line 655)**

Append a note at the end of the service section explaining dual exposure. Find the service section and add at its end, after the parameters table:

```markdown
> The service updates both the deprecated `hvac_action_reason` state attribute and the new `sensor.<climate_name>_hvac_action_reason` entity. Automations reading either surface continue to work.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document hvac_action_reason sensor + reserved Auto values

Phase 0 (#563): README now describes the new diagnostic sensor (preferred
surface), deprecates the state attribute, lists the three reserved Auto
Mode values, and notes the service updates both surfaces."
```

---

## Task 10: Full lint + full test run

**Files:**
- (none — verification only)

- [ ] **Step 1: Run the lint suite**

```bash
./scripts/docker-lint
```

Expected: all linters PASS. If any fail:

```bash
./scripts/docker-lint --fix
```

Then re-run `./scripts/docker-lint` until clean. If `--fix` does not clear the remaining issues, inspect the failing file(s) and fix manually.

- [ ] **Step 2: Run the full test suite**

```bash
./scripts/docker-test
```

Expected: all tests PASS. If any fail, diagnose and fix before proceeding; do not mark this task complete with failing tests.

- [ ] **Step 3: Commit any lint fixes**

If `docker-lint --fix` modified files:

```bash
git add -u
git commit -m "chore: apply linter auto-fixes"
```

If no changes, skip this step.

---

## Self-Review Coverage Check

Below each spec section, the task(s) that implement it:

- Spec §1 Goal & Scope → all tasks.
- Spec §2 Decisions Q1 (deprecated attribute) → Task 6 preserves all existing attribute assignments.
- Spec §2 Decisions Q2 (auto-created sensor, DIAGNOSTIC) → Tasks 3, 5.
- Spec §2 Decisions Q3 (raw enum state, no extra attrs) → Task 3.
- Spec §2 Decisions Q4 (ENUM device class, static options) → Task 3 (`_build_options`).
- Spec §2 Decisions Q5 (`HVACActionReasonAuto`) → Task 1.
- Spec §3.1 new sensor platform → Tasks 3, 5.
- Spec §3.2 entity class (device_class, category, options, unique_id, translation_key) → Tasks 3, 4.
- Spec §3.3 signals → Tasks 2 (constant), 6 (dispatch).
- Spec §4 data flow → Tasks 4, 6.
- Spec §5 auto enum module → Task 1.
- Spec §6 persistence & restore → Task 4 (sensor restore), Task 7 (test).
- Spec §7 error handling (invalid value, unload) → Task 4.
- Spec §8 translations → Task 8.
- Spec §9 testing (new sensor test file, extensions, common helpers) → Tasks 1–7.
- Spec §10 README → Task 9.
- Spec §11 files touched → confirmed above.
- Spec §12 risks — mitigations are baked into the task structure (single dispatch site, all paths covered, tests prove sync).
- Spec §13 acceptance criteria → Task 10 verifies (1–7).

No gaps identified.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-21-auto-mode-phase-0-action-reason-sensor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
