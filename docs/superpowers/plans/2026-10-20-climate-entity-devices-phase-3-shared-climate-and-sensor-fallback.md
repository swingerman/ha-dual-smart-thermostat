# Climate Entity Devices - Phase 3: One Climate in Several Roles, Heat Pump Role, `target_sensor` Fallback - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `climate.*` entity can fill heater, cooler, fan and dryer (and a heat pump) of the same thermostat without the roles fighting. `target_sensor` becomes optional when a climate role exists and falls back to the child's `current_temperature`. A role pointing at the thermostat's own entity is refused.

**Architecture:** Conflict-freedom is already structural from phase 1 (one `ClimateChild` per entity, role "active" derived from the child's single mode). This phase removes the three places that still assume distinct entities per role: the factory's "cooler equals heater" guard, the duplicated state listener from `get_device_ids`, and the concurrent fan-with-cooler/heater cooperation (which needs two modes at once and cannot exist on one device). The sensor fallback is one config normalisation plus a domain-aware temperature reader; listeners, stale detection and startup keep using `sensor_entity_id` unchanged.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md`
**Previous phases:** phase 1 (`...-phase-1-port-seam.md`) and phase 2 (`...-phase-2-setpoint-style.md`) merged.

---

## Testing Environment

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly.

---

## Shared Context

### Why fan-with-cooler cannot run on one climate

`CoolerFanDevice` with `fan_on_with_ac` runs the fan device and then the cooler device in the same tick. On a shared climate that is two commands for one mode slot: the cooler ends in `cool`, the fan then sees itself inactive and sets `fan_only`, and the loop flaps every tick. The AC's own `cool` mode already runs its fan, so the cooperation has no meaning on one entity. The decision is made once, in config normalisation: when the fan resolves to the same climate as the cooler (or heater), `fan_on_with_ac` / `fan_on_with_heater` are forced off with an info log. The sequential behaviour (`fan_hot_tolerance`: fan alone when slightly warm, cooler beyond) keeps working, because it alternates modes instead of stacking them.

### Where config normalisation runs

`climate.py` computes `sensor_entity_id = config[CONF_SENSOR]` near the top of the setup function. A new `normalize_climate_roles(config)` call goes immediately before that line (after `_normalize_config_numeric_values`), so every consumer (`EnvironmentManager`, `config_validation` models, `FeatureManager`, the entity) sees the normalised config.

---

## Task 1: Allow the same climate in several roles

**Files:**
- Modify: `hvac_device/hvac_device_factory.py`, `hvac_device/multi_hvac_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import timedelta
import logging

from homeassistant.util import dt as dt_util


async def test_same_climate_as_heater_and_cooler_is_accepted(
    hass: HomeAssistant, caplog
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    assert "cannot be equal" not in caplog.text


async def test_shared_climate_is_listened_to_once(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    thermostat = hass.data["climate"].get_entity("climate.test")

    assert thermostat.hvac_device.get_device_ids() == [AC]


async def test_switch_entity_in_two_roles_is_still_ignored(
    hass: HomeAssistant, caplog
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(hass, heater=HEATER, cooler=HEATER, initial_hvac_mode=HVACMode.HEAT)

    assert "cannot be equal" in caplog.text  # existing behaviour kept for switches


async def test_single_ac_walks_through_every_mode_one_at_a_time(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("sensor.hum", 60.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        fan=AC,
        dryer=AC,
        humidity_sensor="sensor.hum",
        target_humidity=40,
        fan_mode=True,
        initial_hvac_mode=HVACMode.HEAT,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    expected = {
        HVACMode.HEAT: HVACMode.HEAT,
        HVACMode.COOL: HVACMode.OFF,  # 20 degrees: nothing to cool
        HVACMode.FAN_ONLY: HVACMode.FAN_ONLY,
        HVACMode.DRY: HVACMode.DRY,
        HVACMode.OFF: HVACMode.OFF,
    }
    for dst_mode, child_mode in expected.items():
        await common.async_set_hvac_mode(hass, dst_mode, "climate.test")
        await hass.async_block_till_done()
        assert hass.states.get(AC).state == child_mode, dst_mode

    # One command per transition: no role ever re-commanded another's mode.
    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.DRY]


async def test_idle_role_keep_alive_does_not_stop_the_active_role(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.HEAT,
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "same_climate or listened_to_once or switch_entity_in_two or single_ac or keep_alive" -v
```

Expected: FAIL (`cannot be equal` logged for the climate; the cooler is dropped; `get_device_ids()` has duplicates).

- [ ] **Step 3: Implement**

`hvac_device_factory.py`, in `__init__`:

```python
from ..climate_roles import is_climate_entity
...
            if cooler_entity_id == self._heater_entity_id and not is_climate_entity(
                cooler_entity_id
            ):
                _LOGGER.warning(...)   # unchanged text and branch
```

(Only the condition changes. A climate entity in two roles takes the `else` branch and is kept.)

`multi_hvac_device.py`:

```python
    def get_device_ids(self) -> list[str]:
        device_ids = []
        for device in self.hvac_devices:
            device_ids += device.get_device_ids()

        # One entity can back several roles; listen to it once.
        return list(dict.fromkeys(device_ids))
```

- [ ] **Step 4: Run to verify pass, then whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Allow one climate entity in several roles; dedupe state listeners

Refs #281"
```

---

## Task 2: Config normalisation (sensor fallback and shared-fan flags)

**Files:**
- Modify: `climate_roles.py`, `climate.py`
- Test: `tests/unit/test_config_validation_integration.py`

- [ ] **Step 1: Write the failing tests**

```python
from custom_components.dual_smart_thermostat.climate_roles import normalize_climate_roles


def test_missing_target_sensor_falls_back_to_first_climate_role() -> None:
    cfg = normalize_climate_roles({"heater": "switch.h", "cooler": "climate.ac"})
    assert cfg["target_sensor"] == "climate.ac"


def test_explicit_target_sensor_is_kept() -> None:
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "target_sensor": "sensor.room"}
    )
    assert cfg["target_sensor"] == "sensor.room"


def test_normalisation_does_not_mutate_the_input() -> None:
    original = {"cooler": "climate.ac"}
    normalize_climate_roles(original)
    assert "target_sensor" not in original


def test_fan_sharing_a_climate_with_the_cooler_cannot_run_alongside_it() -> None:
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "fan": "climate.ac", "fan_on_with_ac": True}
    )
    assert cfg["fan_on_with_ac"] is False


def test_fan_sharing_a_climate_with_the_heater_cannot_run_alongside_it() -> None:
    cfg = normalize_climate_roles(
        {"heater": "climate.ac", "fan": "climate.ac", "fan_on_with_heater": True}
    )
    assert cfg["fan_on_with_heater"] is False


def test_separate_fan_keeps_its_flags() -> None:
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "fan": "switch.fan", "fan_on_with_ac": True}
    )
    assert cfg["fan_on_with_ac"] is True


def test_ac_mode_heater_is_the_cooler_for_fan_sharing() -> None:
    cfg = normalize_climate_roles(
        {"heater": "climate.ac", "ac_mode": True, "fan": "climate.ac", "fan_on_with_ac": True}
    )
    assert cfg["fan_on_with_ac"] is False


def test_target_sensor_required_without_climate_role() -> None:
    with pytest.raises(vol.Invalid, match="target_sensor"):
        PLATFORM_SCHEMA({"platform": DOMAIN, "name": "t", "heater": "switch.h"})


def test_target_sensor_optional_with_climate_role() -> None:
    cfg = PLATFORM_SCHEMA({"platform": DOMAIN, "name": "t", "heater": "climate.ac"})
    assert "target_sensor" not in cfg  # normalised at setup, not at validation
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -k "falls_back or explicit_target or mutate or fan_sharing or separate_fan or ac_mode_heater or target_sensor_" -v
```

Expected: FAIL (`ImportError: cannot import name 'normalize_climate_roles'`).

- [ ] **Step 3: Implement**

`climate_roles.py`:

```python
from .const import CONF_AC_MODE, CONF_FAN_ON_WITH_AC, CONF_FAN_ON_WITH_HEATER, CONF_SENSOR


def normalize_climate_roles(config: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve what climate roles imply, once, before anything reads the config.

    - No target_sensor: the first climate role is the temperature source.
    - A fan on the same climate as the cooler or heater cannot run alongside it
      (one entity holds one mode), so the concurrent options are forced off.
    """
    config = dict(config)

    if not config.get(CONF_SENSOR):
        source = first_climate_role(config)
        if source:
            config[CONF_SENSOR] = source

    fan = config.get(CONF_FAN)
    if is_climate_entity(fan):
        heater = config.get(CONF_HEATER)
        cooler = config.get(CONF_COOLER) or (heater if config.get(CONF_AC_MODE) else None)
        if fan == cooler and config.get(CONF_FAN_ON_WITH_AC):
            config[CONF_FAN_ON_WITH_AC] = False
        if fan == heater and config.get(CONF_FAN_ON_WITH_HEATER):
            config[CONF_FAN_ON_WITH_HEATER] = False

    return config
```

and in `validate_climate_options` (phase 2) add, before `return config`:

```python
    if not config.get(CONF_SENSOR) and not has_role:
        raise vol.Invalid(
            "target_sensor is required unless heater, cooler, fan or dryer is a climate entity"
        )
```

`climate.py`: `PLATFORM_SCHEMA`: change `vol.Required(CONF_SENSOR)` to `vol.Optional(CONF_SENSOR)`. In the setup function, just before `sensor_entity_id = config[CONF_SENSOR]`:

```python
    config = normalize_climate_roles(config)
```

Info-log in the normaliser is not needed; log in `climate.py` when the fallback or a forced-off flag actually changed something (compare before/after keys) so users can see why.

Before editing, `grep -rn "required key" tests` to find any existing test that asserts the old "target_sensor is required" error text; none expected, update if any.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Normalise climate roles: optional target_sensor, shared-fan flags

Refs #281"
```

---

## Task 3: Temperature from the child's `current_temperature`

**Files:**
- Modify: `managers/environment_manager.py`
- Test: `tests/features/test_climate_backed_devices.py`, `tests/test_environment_manager.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_environment_manager.py` (existing file, add near the other `update_temp_from_state` tests; reuse its manager fixture):

```python
from homeassistant.core import State


def test_update_temp_from_climate_state_reads_current_temperature(environment_manager) -> None:
    environment_manager.update_temp_from_state(
        State("climate.ac", "cool", {"current_temperature": 23.5})
    )
    assert environment_manager.cur_temp == 23.5


def test_update_temp_from_climate_without_reading_keeps_previous(environment_manager) -> None:
    environment_manager.update_temp_from_state(
        State("climate.ac", "cool", {"current_temperature": 23.5})
    )
    environment_manager.update_temp_from_state(
        State("climate.ac", "cool", {"current_temperature": None})
    )
    assert environment_manager.cur_temp == 23.5


def test_update_temp_from_sensor_state_unchanged(environment_manager) -> None:
    environment_manager.update_temp_from_state(State("sensor.room", "21.0"))
    assert environment_manager.cur_temp == 21.0
```

(If the file has no `environment_manager` fixture, construct `EnvironmentManager(hass, config)` the way its existing tests do.)

`tests/features/test_climate_backed_devices.py`:

```python
async def test_standalone_ac_uses_its_own_temperature(hass: HomeAssistant) -> None:
    """No target_sensor: the AC's current_temperature drives everything."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "cooler": AC,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=22.0)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get("climate.test").attributes["current_temperature"] == 22.0

    child.set_current_temperature(26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 26.0
    assert hass.states.get(AC).state == HVACMode.COOL

    child.set_current_temperature(23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_child_temperature_read_at_startup(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, AC, current=21.5)
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {CLIMATE: {"platform": DOMAIN, "name": "test", "heater": AC}},
    )
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 21.5


async def test_stale_child_temperature_triggers_the_emergency_stop(
    hass: HomeAssistant, freezer
) -> None:
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "sensor_stale_duration": timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await common.add_fake_climate(hass, AC, current=18.0)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/test_environment_manager.py tests/features/test_climate_backed_devices.py -k "climate_state or climate_without or standalone or startup or stale_child" -v
```

Expected: FAIL (`ValueError ... could not convert string to float: 'cool'` logged, `cur_temp` stays `None`).

- [ ] **Step 3: Implement**

`environment_manager.py`:

```python
    @callback
    def update_temp_from_state(self, state: State) -> None:
        """Update thermostat with latest state from sensor (or climate entity)."""
        raw = (
            state.attributes.get("current_temperature")
            if state.domain == "climate"
            else state.state
        )
        if raw is None:  # a climate that has no reading yet
            return
        try:
            cur_temp = float(raw)
            if not math.isfinite(cur_temp):
                raise ValueError(f"Sensor has illegal state {raw}")
            self._cur_temp = cur_temp
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)
```

Before editing, `grep -n "sensor_entity_id\|states.get(self.sensor" climate.py` and read each hit: every direct read of the sensor state that parses `.state` as a number must go through `update_temp_from_state` (initial-state, startup and sensor-changed paths already do). Anything else is changed to call it.

Stale detection compares `state.last_updated`; a climate's `last_updated` moves on every attribute change, which is the right "it reported something" signal.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/test_environment_manager.py tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Use a climate entity's current_temperature as the temperature source

Refs #281"
```

---

## Task 4: Heat pump role on a climate entity

**Files:**
- Modify: `hvac_device/heat_pump_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
COOLING_FLAG = "binary_sensor.hp_cooling"


@pytest.mark.parametrize(
    ("cooling", "dst_mode", "room", "expected"),
    [
        ("off", HVACMode.HEAT, 18.0, HVACMode.HEAT),
        ("on", HVACMode.COOL, 27.0, HVACMode.COOL),
    ],
)
async def test_climate_heat_pump_follows_the_cooling_flag(
    hass: HomeAssistant, cooling, dst_mode, room, expected
) -> None:
    hass.states.async_set(COOLING_FLAG, cooling)
    hass.states.async_set(SENSOR, room)
    await _setup(
        hass, heater=AC, heat_pump_cooling=COOLING_FLAG, initial_hvac_mode=dst_mode
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == expected
```

(`control_style: setpoint` with a climate heat pump is rejected at validation; that test lives in phase 2 task 1.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "heat_pump" -v
```

Expected: FAIL: `ValueError: climate.test_ac: this device role cannot be backed by a climate entity` (no role mode on `HeatPumpDevice`).

- [ ] **Step 3: Implement**

`heat_pump_device.py`:

```python
class HeatPumpDevice(GenericHVACDevice):

    hvac_modes = [HVACMode.OFF]
    # Read by the port before _apply_heat_pump_cooling_state() has run.
    _heat_pump_is_cooling = False

    def role_mode(self) -> HVACMode | None:
        return HVACMode.COOL if self._heat_pump_is_cooling else HVACMode.HEAT
```

Both heating and cooling controllers already share `self.port` (phase 1), so `is_active` and the commanded mode follow the flag lazily.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test tests/test_heat_pump_mode.py tests/test_heat_pump_mode_behavioral.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Climate heat pump role: child mode follows heat_pump_cooling

Refs #281"
```

---

## Task 5: Shared fan does not flap; self-reference refused

**Files:**
- Modify: `climate.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_shared_fan_with_ac_flag_does_not_flap(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 27.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=AC,
        fan_on_with_ac=True,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (27.1, 27.2, 27.3, 27.4):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.COOL]  # never fan_only, never repeated
    assert hass.states.get(AC).state == HVACMode.COOL


async def test_entity_cannot_be_its_own_device(hass: HomeAssistant, caplog) -> None:
    hass.states.async_set(SENSOR, 20.0)
    hass.config.units = METRIC_SYSTEM
    await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",  # becomes climate.test
                "target_sensor": SENSOR,
                "heater": "climate.test",
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get("climate.test") is None
    assert "itself" in caplog.text
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "shared_fan or its_own_device" -v
```

Expected: `shared_fan` passes only if task 2 landed (it should); `its_own_device` FAILS (entity is created and recurses through its own services).

- [ ] **Step 3: Implement**

`climate.py`, at the top of `DualSmartThermostat.async_added_to_hass` (before listeners are registered):

```python
        if self.entity_id in self.hvac_device.get_device_ids():
            msg = f"{self.entity_id} is configured as one of its own devices"
            _LOGGER.error(msg + " ('itself'); refusing to add it")
            raise HomeAssistantError(msg)
```

Use the exact wording that makes the test's `"itself"` substring appear in the log (`"... one of its own devices ... itself"` as above, or reword both). `HomeAssistantError` is already imported in the module, otherwise import from `homeassistant.exceptions`.

- [ ] **Step 4: Run to verify pass and whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Refuse a thermostat configured as its own device; shared-fan regression

Refs #281"
```

---

## Task 6: Lint and wrap-up

- [ ] **Step 1:** `./scripts/docker-lint --fix && ./scripts/docker-lint`
- [ ] **Step 2:** `./scripts/docker-test`
- [ ] **Step 3: Commit** lint fixes: `git add -A && git commit -m "Lint fixes for shared climate roles

Refs #281"`

## Acceptance (phase 3)

1. `heater`, `cooler`, `fan` and `dryer` on the same climate: the child steps through one mode at a time; exactly one `set_hvac_mode` per transition; an idle role's keep-alive never stops the active one.
2. `fan_on_with_ac` / `fan_on_with_heater` on a shared climate are forced off (no flapping); `fan_hot_tolerance` sequencing still works.
3. Duplicate state listeners for a shared entity are gone.
4. Omitting `target_sensor` with a climate role uses the child's `current_temperature` for control, startup, and stale detection; without a climate role it is still required.
5. A climate heat pump follows `heat_pump_cooling` (child `heat` or `cool`); `setpoint` with it is rejected (phase 2 validation).
6. A thermostat that names itself as a device is refused with a clear error.
7. Switch-only configurations behave exactly as before (the whole existing suite passes).
