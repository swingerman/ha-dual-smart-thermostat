# Climate Entity Devices - Phase 2: `setpoint` Control Style and Per-Role Setpoint Offsets - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `control_style: setpoint` (the child stays engaged and regulates itself; DST mirrors target, mode, presets and openings and adds no cycling) and per-role `heater_setpoint_offset` / `cooler_setpoint_offset` (each added to that role's pushed target, clamped to the child's range; there is no thermostat-wide offset, and fan and dryer push no temperature so they have none). A heat pump uses the heater offset while heating and the cooler offset while cooling. All configurable in YAML; flows come in phase 4.

**Architecture:** Style is a property of the port, not a new device class. `ClimatePort` gains `offset` (a callable, so the heat pump can switch between its two keys) and `style`; `style == "setpoint"` makes `self_regulating` true. `GenericHVACDevice` reacts to that single flag twice: it swaps in a strategy whose goal is never reached (`HvacEnvStrategy.self_regulating`) and the port's `ran_long_enough` becomes always true. Target mirroring is one idempotent `port.async_sync()` called at the top of `async_control_hvac`, which every existing trigger already reaches. The unchanged controller then keeps the child engaged, pauses it for openings and floor limits, and restores it.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md`
**Previous phase:** `docs/superpowers/plans/2026-10-20-climate-entity-devices-phase-1-port-seam.md` (must be merged: `EntityPort`, `ClimateChild`, `ClimatePort`, the fake child in `tests/common.py`, `tests/features/test_climate_backed_devices.py`).

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

### Why a strategy swap and not a new control loop

`GenericHvacController` decides only from `strategy.hvac_goal_reached` / `hvac_goal_not_reached`, openings and (heater) floor limits. If "goal reached" is permanently false and "goal not reached" permanently true, the same controller:

- turns the child on when it is off and nothing blocks it,
- leaves it on otherwise,
- turns it off for an open opening or a hot floor and back on afterwards.

That is exactly the `setpoint` contract with zero new branching.

`HvacEnvStrategy(above, below, ...)` is built positionally as `(is_below_target, is_above_target, ...)` by devices; `hvac_goal_reached` is `above()` for `LOWER` and `below()` for `RAISE`; `hvac_goal_not_reached` is the other one. The classmethod therefore sets the first callable to `goal == RAISE` and the second to its negation.

### Pushed target

`pushed = round_to_step(clamp(target + role_offset, child.min_temp, child.max_temp), child.target_temperature_step)`. A push is skipped when the child already reports that value (`attributes["temperature"]`; for an assumed child, DST's last pushed value).

---

## Task 1: Config keys and YAML validation

**Files:**
- Modify: `const.py`, `climate_roles.py`, `climate.py` (`PLATFORM_SCHEMA`)
- Test: `tests/unit/test_config_validation_integration.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_config_validation_integration.py`:

```python
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.climate import PLATFORM_SCHEMA
from custom_components.dual_smart_thermostat.const import DOMAIN


def _yaml(**extra):
    return {
        "platform": DOMAIN,
        "name": "t",
        "target_sensor": "sensor.t",
        "heater": "switch.h",
        **extra,
    }


def test_control_style_and_cooler_offset_accepted_with_climate_cooler() -> None:
    cfg = PLATFORM_SCHEMA(
        _yaml(cooler="climate.ac", control_style="setpoint", cooler_setpoint_offset=-3)
    )
    assert cfg["control_style"] == "setpoint"
    assert cfg["cooler_setpoint_offset"] == -3.0


def test_each_offset_needs_its_own_climate_role() -> None:
    # heater is a switch: its offset has nothing to apply to
    with pytest.raises(vol.Invalid, match="heater_setpoint_offset"):
        PLATFORM_SCHEMA(_yaml(cooler="climate.ac", heater_setpoint_offset=2))
    # cooler is a switch: same for the cooler offset
    with pytest.raises(vol.Invalid, match="cooler_setpoint_offset"):
        PLATFORM_SCHEMA(_yaml(heater="climate.ac", cooler="switch.c", cooler_setpoint_offset=2))


def test_ac_mode_climate_heater_serves_as_the_cooler() -> None:
    cfg = PLATFORM_SCHEMA(_yaml(heater="climate.ac", ac_mode=True, cooler_setpoint_offset=-2))
    assert cfg["cooler_setpoint_offset"] == -2.0
    with pytest.raises(vol.Invalid, match="heater_setpoint_offset"):
        PLATFORM_SCHEMA(_yaml(heater="climate.ac", ac_mode=True, heater_setpoint_offset=2))


def test_climate_heat_pump_accepts_both_offsets() -> None:
    cfg = PLATFORM_SCHEMA(
        _yaml(
            heater="climate.hp",
            heat_pump_cooling="binary_sensor.cooling",
            heater_setpoint_offset=3,
            cooler_setpoint_offset=-5,
        )
    )
    assert (cfg["heater_setpoint_offset"], cfg["cooler_setpoint_offset"]) == (3.0, -5.0)


def test_applicable_offset_keys_follow_the_roles() -> None:
    from custom_components.dual_smart_thermostat.climate_roles import applicable_offset_keys

    assert applicable_offset_keys({"heater": "switch.h", "cooler": "climate.ac"}) == [
        "cooler_setpoint_offset"
    ]
    assert applicable_offset_keys({"heater": "climate.h", "cooler": "climate.c"}) == [
        "heater_setpoint_offset",
        "cooler_setpoint_offset",
    ]
    assert applicable_offset_keys({"heater": "climate.h", "fan": "climate.h"}) == [
        "heater_setpoint_offset"
    ]
    assert applicable_offset_keys({"heater": "switch.h"}) == []


@pytest.mark.parametrize(
    "key,value",
    [("control_style", "on_off"), ("heater_setpoint_offset", 1), ("cooler_setpoint_offset", 1)],
)
def test_climate_only_options_rejected_without_a_climate_role(key, value) -> None:
    with pytest.raises(vol.Invalid, match="climate"):
        PLATFORM_SCHEMA(_yaml(**{key: value}))


def test_unknown_control_style_rejected() -> None:
    with pytest.raises(vol.Invalid):
        PLATFORM_SCHEMA(_yaml(cooler="climate.ac", control_style="auto"))


def test_setpoint_with_climate_heat_pump_rejected() -> None:
    with pytest.raises(vol.Invalid, match="heat pump"):
        PLATFORM_SCHEMA(
            _yaml(
                heater="climate.hp",
                heat_pump_cooling="binary_sensor.cooling",
                control_style="setpoint",
            )
        )


def test_climate_aux_heater_rejected() -> None:
    with pytest.raises(vol.Invalid, match="secondary_heater"):
        PLATFORM_SCHEMA(_yaml(secondary_heater="climate.ac"))
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -k "control_style or climate_only or heat_pump or aux_heater_rejected or offset or ac_mode" -v
```

Expected: FAIL (`extra keys not allowed` / no error raised).

- [ ] **Step 3: Implement**

`const.py`:

```python
CONF_CONTROL_STYLE = "control_style"
CONF_HEATER_SETPOINT_OFFSET = "heater_setpoint_offset"
CONF_COOLER_SETPOINT_OFFSET = "cooler_setpoint_offset"


class ControlStyle(enum.StrEnum):
    """How a climate-backed device is controlled."""

    ON_OFF = "on_off"
    SETPOINT = "setpoint"


DEFAULT_CONTROL_STYLE = ControlStyle.ON_OFF
DEFAULT_SETPOINT_OFFSET = 0.0  # per role: heater_/cooler_setpoint_offset
```

`climate_roles.py` (add):

```python
import voluptuous as vol

from .const import (
    CONF_AUX_HEATER,
    CONF_AC_MODE,
    CONF_CONTROL_STYLE,
    CONF_COOLER,
    CONF_HEAT_PUMP_COOLING,
    CONF_COOLER_SETPOINT_OFFSET,
    CONF_HEATER_SETPOINT_OFFSET,
    ControlStyle,
)


def applicable_offset_keys(config: Mapping[str, Any]) -> list[str]:
    """Which per-role offsets mean something for these roles.

    Only roles that push a temperature have one. A climate `heater` that only
    serves as the cooler (`ac_mode`, no `cooler`) uses the cooler offset; a heat
    pump uses the heater offset while heating and the cooler offset while cooling.
    """
    heater_is_climate = is_climate_entity(config.get(CONF_HEATER))
    ac_only = bool(config.get(CONF_AC_MODE)) and not config.get(CONF_COOLER)
    heat_pump = bool(config.get(CONF_HEAT_PUMP_COOLING))

    keys = []
    if heater_is_climate and (not ac_only or heat_pump):
        keys.append(CONF_HEATER_SETPOINT_OFFSET)
    if is_climate_entity(config.get(CONF_COOLER)) or (
        heater_is_climate and (ac_only or heat_pump)
    ):
        keys.append(CONF_COOLER_SETPOINT_OFFSET)
    return keys


def setpoint_unsupported(config: Mapping[str, Any]) -> bool:
    """control_style: setpoint cannot drive a climate heat pump (spec OQ2)."""
    return bool(
        config.get(CONF_CONTROL_STYLE) == ControlStyle.SETPOINT
        and config.get(CONF_HEAT_PUMP_COOLING)
        and is_climate_entity(config.get(CONF_HEATER))
    )


def validate_climate_options(config: dict[str, Any]) -> dict[str, Any]:
    """Cross-field rules for climate-backed roles (shared by YAML and the flows)."""
    has_role = has_climate_role(config)
    if CONF_CONTROL_STYLE in config and not has_role:
        raise vol.Invalid(
            "control_style needs heater, cooler, fan or dryer to be a climate entity"
        )
    applicable = applicable_offset_keys(config)
    for key in (CONF_HEATER_SETPOINT_OFFSET, CONF_COOLER_SETPOINT_OFFSET):
        if key in config and key not in applicable:
            raise vol.Invalid(
                f"{key} needs the matching role to be a climate entity (climate)"
            )
    if setpoint_unsupported(config):
        raise vol.Invalid(
            "control_style: setpoint is not supported for a climate heat pump"
        )
    if is_climate_entity(config.get(CONF_AUX_HEATER)):
        raise vol.Invalid("secondary_heater cannot be a climate entity")
    return config
```

`climate.py`: add to the `PLATFORM_SCHEMA.extend({...})` dict

```python
        vol.Optional(CONF_CONTROL_STYLE): vol.Coerce(ControlStyle),
        vol.Optional(CONF_HEATER_SETPOINT_OFFSET): vol.Coerce(float),
        vol.Optional(CONF_COOLER_SETPOINT_OFFSET): vol.Coerce(float),
```

and wrap the result: `PLATFORM_SCHEMA = vol.All(PLATFORM_SCHEMA.extend({...}), validate_climate_options)`. First `grep -n "PLATFORM_SCHEMA" custom_components` to confirm nothing later calls `.extend` on it (HA itself calls it as a plain validator).

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/unit/test_config_validation_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add control_style and per-role setpoint offset keys with climate role validation

Refs #281"
```

---

## Task 2: Offset, clamp and step in the pushed target

**Files:**
- Modify: `hvac_device/entity_port.py`, `managers/feature_manager.py`, `hvac_device/generic_hvac_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

Append:

```python
from custom_components.dual_smart_thermostat.const import ControlStyle


def _port2(hass, entity_id, mode, target, *, offset=0.0, style=ControlStyle.ON_OFF):
    # offset is read lazily through a callable (a heat pump switches between two keys)
    return make_port(
        hass,
        entity_id,
        role_mode=lambda: mode,
        target=lambda: target,
        style=style,
        offset=lambda: offset,
    )


async def test_offset_is_added_to_the_pushed_target(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port2(hass, "climate.test_ac", HVACMode.COOL, 24.0, offset=-3.0)

    await cool.async_turn_on(None)

    assert ("set_temperature", {"temperature": 21.0}) in child.calls


async def test_pushed_target_is_clamped_to_the_child_range(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")  # 16..30
    heat = _port2(hass, "climate.test_ac", HVACMode.HEAT, 29.0, offset=5.0)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 30}) in child.calls


async def test_pushed_target_is_rounded_to_the_child_step(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")  # step 0.5
    heat = _port2(hass, "climate.test_ac", HVACMode.HEAT, 21.3)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 21.5}) in child.calls


async def test_target_not_resent_when_child_already_has_it(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_target_temperature = 22.0
    child.async_write_ha_state()
    heat = _port2(hass, "climate.test_ac", HVACMode.HEAT, 22.0)

    await heat.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "offset or clamped or rounded or not_resent" -v
```

Expected: FAIL (`make_port() got an unexpected keyword argument 'style'`).

- [ ] **Step 3: Implement**

`entity_port.py`:

```python
class ClimateChild:
    ...
    async def async_push_target(self, value: float, context: Context | None) -> None:
        async with self._lock:
            if not self.available:
                return
            attrs = self.state.attributes
            features = attrs.get("supported_features")
            if features is not None and not features & ClimateEntityFeature.TARGET_TEMPERATURE:
                return
            value = self._fit(value, attrs)
            current = self._last_pushed if self.assumed else attrs.get("temperature")
            if current == value:
                return
            ... # existing set_temperature call, then self._last_pushed = value

    @staticmethod
    def _fit(value: float, attrs) -> float:
        """Round to the child's step, then clamp to its range."""
        step = attrs.get("target_temp_step")  # ATTR_TARGET_TEMP_STEP
        if step:
            value = round(round(value / step) * step, 4)
        low, high = attrs.get("min_temp"), attrs.get("max_temp")
        if low is not None:
            value = max(value, low)
        if high is not None:
            value = min(value, high)
        return value
```

(The state attribute is `target_temp_step`; the fake child's `_attr_target_temperature_step` surfaces under that name.)

`ClimatePort`:

```python
    def __init__(self, child, role_mode, target, offset: Callable[[], float], style: ControlStyle):
        ...
        self._offset = offset
        self.self_regulating = style == ControlStyle.SETPOINT

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        if self.self_regulating:  # the child cycles itself; DST adds no cycle limit
            return True
        ...

    async def _push(self, context) -> None:
        target = self._target()
        if target is not None:
            await self._child.async_push_target(target + self._offset(), context)

    async def async_turn_on(self, context):
        if await self._child.async_set_mode(self._role_mode(), context):
            await self._push(context)
```

`make_port(hass, entity_id, *, role_mode, target, style=ControlStyle.ON_OFF, offset=lambda: 0.0)` forwards both to `ClimatePort`.

`FeatureManager`: read-only properties over the config, mirroring existing ones such as `heat_pump_cooling_entity_id`:

```python
    @property
    def climate_control_style(self) -> ControlStyle:
        return ControlStyle(self._config.get(CONF_CONTROL_STYLE, DEFAULT_CONTROL_STYLE))

    @property
    def heater_setpoint_offset(self) -> float:
        return float(self._config.get(CONF_HEATER_SETPOINT_OFFSET, DEFAULT_SETPOINT_OFFSET))

    @property
    def cooler_setpoint_offset(self) -> float:
        return float(self._config.get(CONF_COOLER_SETPOINT_OFFSET, DEFAULT_SETPOINT_OFFSET))
```

Each device class says which offset its role uses (fan and dryer push no temperature, so the default is `0.0`):

```python
# GenericHVACDevice
    def setpoint_offset(self) -> float:
        return 0.0

# HeaterDevice
    def setpoint_offset(self) -> float:
        return self.features.heater_setpoint_offset

# CoolerDevice  (also the ac_mode cooler on the heater entity)
    def setpoint_offset(self) -> float:
        return self.features.cooler_setpoint_offset

# HeatPumpDevice
    def setpoint_offset(self) -> float:
        return (
            self.features.cooler_setpoint_offset
            if self._heat_pump_is_cooling
            else self.features.heater_setpoint_offset
        )
```

(`FanDevice` extends `CoolerDevice`: override it back to `0.0`; `DryerDevice` inherits the default.)

`GenericHVACDevice.__init__`: pass `style=features.climate_control_style, offset=self.setpoint_offset` (the bound method, read lazily) to `make_port`.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Climate roles: per-role setpoint offsets, clamp and step on the pushed target

Refs #281"
```

---

## Task 3: Mirror target changes (`async_sync`)

**Files:**
- Modify: `hvac_device/entity_port.py`, `hvac_device/generic_hvac_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_target_change_while_engaged_is_mirrored(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_temperature(hass, 23, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == [("set_temperature", {"temperature": 23.0})]


async def test_unchanged_target_is_not_resent_on_sensor_ticks(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    for temp in (20.1, 20.2, 20.3):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert child.calls == []


async def test_preset_target_is_mirrored(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        away={"temperature": 17},
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_preset_mode(hass, "away", "climate.test")
    await hass.async_block_till_done()

    assert ("set_temperature", {"temperature": 17.0}) in child.calls


async def test_setpoint_is_never_pushed_before_the_role_owns_the_mode(
    hass: HomeAssistant,
) -> None:
    """Child is in a mode this role does not own: mode first, then target."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)  # not our mode

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "mirrored or not_resent or idle_role" -v
```

Expected: FAIL (`test_target_change_while_engaged_is_mirrored`: `calls == []`).

- [ ] **Step 3: Implement**

`ClimatePort`:

```python
    async def async_sync(self, context: Context | None) -> None:
        # Only the role the child is serving may touch its setpoint.
        if self.is_active:
            await self._push(context)
```

`GenericHVACDevice.async_control_hvac`, directly after the `if self._hvac_mode == HVACMode.OFF:` block returns and before `if self.hvac_controller.is_active:`:

```python
        await self.port.async_sync(self._context)
```

The `needs_control` gate above it is unchanged; target changes already call control with `force=True`, sensor ticks pass it once the device is active.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Mirror target changes onto an engaged climate role (async_sync)

Refs #281"
```

---

## Task 4: `setpoint` style (self-regulating strategy)

**Files:**
- Modify: `hvac_controller/hvac_controller.py`, `hvac_device/generic_hvac_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_setpoint_style_never_turns_the_child_off_at_target(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass, heater=AC, initial_hvac_mode=HVACMode.HEAT, control_style="setpoint"
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 25.0)  # far above target: on_off would stop here
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert "turn_off" not in [c[0] for c in child.calls]


async def test_setpoint_style_ignores_min_cycle_duration(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        min_cycle_duration=timedelta(minutes=30),
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    # Mode change must not wait 30 minutes for the "cycle" to be old enough.
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_setpoint_style_opening_pauses_and_restores_the_child(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        openings=["binary_sensor.window"],
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(SENSOR, 20.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child.calls.clear()
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(SENSOR, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 22.0}) in child.calls


async def test_setpoint_style_each_role_uses_its_own_offset(hass: HomeAssistant) -> None:
    heater_ac = "climate.test_heater_ac"
    hass.states.async_set(SENSOR, 18.0)
    await _setup(
        hass,
        heater=heater_ac,
        cooler=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        heater_setpoint_offset=3,
        cooler_setpoint_offset=-5,
    )
    heater_child = await common.add_fake_climate(hass, heater_ac)
    cooler_child = await common.add_fake_climate(hass, AC)

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 25.0}) in heater_child.calls  # 22 + 3

    hass.states.async_set(SENSOR, 28.0)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 19.0}) in cooler_child.calls  # 24 - 5
    assert all(c[1].get("temperature") != 19.0 for c in heater_child.calls)


async def test_on_off_style_is_unchanged_by_the_new_code(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)  # default style
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "setpoint_style or on_off_style" -v
```

Expected: FAIL (`...never_turns_the_child_off_at_target`: child ends `off`).

- [ ] **Step 3: Implement**

`hvac_controller/hvac_controller.py`, in `HvacEnvStrategy`:

```python
    @classmethod
    def self_regulating(cls, goal, goal_reached_reason, goal_not_reached_reason):
        """Strategy for a device that regulates itself: goal never reached.

        The controller then keeps the device engaged and only lets openings and
        floor limits pause it. `above`/`below` are positional the way devices
        build them: RAISE reads `below()` for reached and `above()` for
        not-reached, LOWER the other way round.
        """
        raise_goal = goal == HvacGoal.RAISE
        return cls(
            lambda: raise_goal,
            lambda: not raise_goal,
            goal_reached_reason,
            goal_not_reached_reason,
            goal,
        )
```

`GenericHVACDevice.__init__`, right after `self.strategy = HvacEnvStrategy(...)`:

```python
        if self.port.self_regulating:
            self.strategy = HvacEnvStrategy.self_regulating(
                self.hvac_goal,
                self.target_env_attr_reached_reason,
                self.target_env_attr_not_reached_reason,
            )
```

Nothing else: min-cycle bypass is already in `ClimatePort.ran_long_enough` (task 2); OFF mode, openings and floor limits go through the unchanged controller.

- [ ] **Step 4: Run to verify pass and the whole suite**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add control_style: setpoint (self-regulating climate child)

Refs #281"
```

---

## Task 5: Lint and wrap-up

- [ ] **Step 1:** `./scripts/docker-lint --fix && ./scripts/docker-lint`
- [ ] **Step 2:** `./scripts/docker-test`
- [ ] **Step 3: Commit** lint fixes: `git add -A && git commit -m "Lint fixes for setpoint style

Refs #281"`

## Acceptance (phase 2)

1. `control_style: setpoint` keeps the child engaged beyond the target; no DST-initiated turn-off at target; no min-cycle wait.
2. Target, preset and mode changes reach the child; unchanged values are not resent.
3. An opening pauses and restores a setpoint child; floor limits still apply to a climate heater.
4. `heater_setpoint_offset` / `cooler_setpoint_offset` apply to their own role's pushes only (heat pump: by direction) and are clamped and stepped to the child's range; there is no thermostat-wide offset.
5. `on_off` default behaviour unchanged.
6. `control_style` without a climate role, an offset key whose role is not a climate entity, a climate heat pump with `setpoint`, and a climate `secondary_heater` are rejected at YAML validation.
