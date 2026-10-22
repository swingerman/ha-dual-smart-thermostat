# Climate Entity Devices - Phase 3b: Fan Speed for a Climate Child - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A climate entity filling any role (a cooler-only AC included) exposes DST's `fan_mode`, using the child's own `fan_modes` verbatim (`quiet`, `strong`, ...) and `climate.set_fan_mode`. The selected speed is re-applied after every turn on of the child, restored across restarts, and detected late if the child appears late. No new config option.

**Architecture:** Fan speed logic moves out of `FanDevice` into one small `FanSpeedControl(hass, entity_id)` (move-only, same members) that gains a climate detection source. The thermostat has exactly one fan-speed target: the factory picks it once (a fan device's control if a fan device exists, else a control over the first climate role, else none) and stores it with `features.set_fan_speed(...)`. Everything downstream (`climate.py`, `FeatureManager`, restore, redetect) talks to that one object, so there is no place that decides "whose fan speed is this". `ClimatePort.async_turn_on` asks the control to re-apply; the control acts only if it targets that same climate entity.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md` (section 3.5, D12)
**Previous phases:** 1 to 3 merged. Read `custom_components/dual_smart_thermostat/hvac_device/CLAUDE.md` first: detection is automatic and not overridable by configuration; that stays true.

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

### What moves

From `FanDevice` into `FanSpeedControl` (`hvac_device/fan_speed.py`): `_detect_fan_capabilities`, `redetect_capabilities`, `supports_fan_mode`, `fan_modes`, `uses_preset_modes`, `current_fan_mode`, `restore_fan_mode`, `async_set_fan_mode` and their state (`_supports_fan_mode`, `_fan_modes`, `_uses_preset_modes`, `_current_fan_mode`, `_pending_fan_mode`). `FanDevice` keeps the same public members as one-line delegations to `self.speed`, so `tests/test_fan_speed_control.py` and `CoolerFanDevice` / `HeaterFanDevice` keep working untouched.

### Detection sources after this phase

| Source | Modes | Service |
|---|---|---|
| `fan` + `preset_modes` | presets | `fan.set_preset_mode` |
| `fan` + `percentage` | `auto/low/medium/high` | `fan.set_percentage` |
| `switch` / other | none | n/a |
| `climate` + non-empty `fan_modes` | the list, verbatim | `climate.set_fan_mode` |

### Fake child additions (tests/common.py)

`FakeClimateChild` gets `fan_modes=["quiet", "strong", "auto"]`, a current `fan_mode`, the `FAN_MODE` supported feature, `async_set_fan_mode` (records `("set_fan_mode", {...})`), and an optional `resets_fan_on_mode_change` flag that sets the fan mode back to `"auto"` whenever `async_set_hvac_mode` runs (what many ACs do).

---

## Task 1: Extract `FanSpeedControl` (move-only) and the single target

**Files:**
- Create: `custom_components/dual_smart_thermostat/hvac_device/fan_speed.py`
- Modify: `hvac_device/fan_device.py`, `managers/feature_manager.py`, `climate.py`, `hvac_device/hvac_device_factory.py`, `tests/test_fan_speed_control.py` (3 mechanical lines)
- Test: `tests/test_fan_speed_control.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fan_speed_control.py`:

```python
from custom_components.dual_smart_thermostat.hvac_device.fan_speed import FanSpeedControl


@pytest.mark.asyncio
async def test_fan_speed_control_detects_fan_presets_without_a_device(
    hass: HomeAssistant,
):
    hass.states.async_set(
        "fan.test_fan",
        "off",
        {"preset_modes": ["auto", "low"], "preset_mode": "auto"},
    )

    speed = FanSpeedControl(hass, "fan.test_fan")

    assert speed.supports_fan_mode is True
    assert speed.fan_modes == ["auto", "low"]
    assert speed.current_fan_mode == "auto"


@pytest.mark.asyncio
async def test_fan_device_exposes_its_speed_control(hass: HomeAssistant):
    hass.states.async_set("fan.test_fan", "off", {"percentage": 0})
    fan_device = _make_fan_device(hass, "fan.test_fan")  # the helper the neighbouring tests use

    assert isinstance(fan_device.speed, FanSpeedControl)
    assert fan_device.fan_modes == fan_device.speed.fan_modes
```

(`_make_fan_device` stands for the `FanDevice(hass, ..., MagicMock(...))` construction repeated in this file; extract it into a local helper if none exists.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/test_fan_speed_control.py -k "speed_control_detects or exposes_its_speed" -v
```

Expected: FAIL, `ModuleNotFoundError: ...hvac_device.fan_speed`.

- [ ] **Step 3: Implement**

Create `hvac_device/fan_speed.py` by moving the listed members out of `FanDevice` verbatim into a class that takes `(hass, entity_id)`:

```python
"""Fan speed control for the one entity that owns the thermostat's fan_mode."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, State, callback

from ..const import FAN_MODE_TO_PERCENTAGE

_LOGGER = logging.getLogger(__name__)


class FanSpeedControl:
    """Detect, hold, restore and apply a fan speed on one entity."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self._supports_fan_mode = False
        self._fan_modes: list[str] = []
        self._uses_preset_modes = False
        self._current_fan_mode: str | None = None
        self._pending_fan_mode: str | None = None
        self._detect_fan_capabilities()

    # _detect_fan_capabilities, redetect_capabilities, restore_fan_mode,
    # async_set_fan_mode and the supports_fan_mode / fan_modes /
    # uses_preset_modes / current_fan_mode properties: moved from FanDevice
    # unchanged (replace self.hass / self.entity_id references 1:1).
```

`FanDevice`: in `__init__` replace the capability state and the `_detect_fan_capabilities()` call with `self.speed = FanSpeedControl(hass, entity_id)`, and turn the moved members into delegations:

```python
    @property
    def supports_fan_mode(self) -> bool:
        return self.speed.supports_fan_mode

    @property
    def fan_modes(self) -> list[str]:
        return self.speed.fan_modes

    @property
    def uses_preset_modes(self) -> bool:
        return self.speed.uses_preset_modes

    @property
    def current_fan_mode(self) -> str | None:
        return self.speed.current_fan_mode

    def restore_fan_mode(self, fan_mode: str) -> None:
        self.speed.restore_fan_mode(fan_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.speed.async_set_fan_mode(fan_mode)

    def redetect_capabilities(self, entity_id: str, new_state: State) -> bool:
        return self.speed.redetect_capabilities(entity_id, new_state)
```

`FanDevice.async_turn_on` keeps its current "apply the selected mode after turn on" block, reading `self.speed`.

`FeatureManager`: rename `_fan_device` / `set_fan_device` / `fan_device` to `_fan_speed` / `set_fan_speed(control: FanSpeedControl | None)` / `fan_speed`; `supports_fan_mode`, `fan_modes` and `_restore_fan_mode` read the control. `climate.py`: the three `self.features.fan_device` reads become `self.features.fan_speed` (member names on it are unchanged). `tests/test_fan_speed_control.py`: the three `features.set_fan_device(fan_device)` lines become `features.set_fan_speed(fan_device.speed)`.

Factory (`create_device`), replacing `if fan_device: self._features.set_fan_device(fan_device)`:

```python
        self._features.set_fan_speed(self._select_fan_speed(fan_device))
```

```python
    def _select_fan_speed(self, fan_device: FanDevice | None) -> FanSpeedControl | None:
        """The one entity that owns fan_mode: the fan device if there is one,
        otherwise the first climate role, otherwise nobody."""
        if fan_device is not None:
            return fan_device.speed
        source = first_climate_role(self._config)
        return FanSpeedControl(self.hass, source) if source else None
```

(`__init__` keeps `self._config = config`; import `first_climate_role`.) With no climate role this is exactly today's behaviour.

- [ ] **Step 4: Run to verify pass, then the fan tests and the whole suite**

```bash
./scripts/docker-test tests/test_fan_speed_control.py tests/test_fan_mode.py -v
./scripts/docker-test
```

Expected: PASS everywhere (move-only).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Extract FanSpeedControl; one fan-speed target per thermostat

Refs #281"
```

---

## Task 2: Climate detection source

**Files:**
- Modify: `hvac_device/fan_speed.py`, `tests/common.py`
- Test: `tests/test_fan_speed_control.py`

- [ ] **Step 1: Extend the fake child and write the failing tests**

`tests/common.py`, in `FakeClimateChild`:

```python
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_fan_modes = ["quiet", "strong", "auto"]

    def __init__(self, entity_id, mode=HVACMode.OFF, *, assumed=False, current=22.0,
                 fan_mode="auto", resets_fan_on_mode_change=False):
        ...
        self._attr_fan_mode = fan_mode
        self._resets_fan = resets_fan_on_mode_change

    async def async_set_fan_mode(self, fan_mode):
        self.calls.append(("set_fan_mode", {"fan_mode": fan_mode}))
        if not self._attr_assumed_state:
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()
```

and in `async_set_hvac_mode`, after recording the call: `if self._resets_fan: self._attr_fan_mode = "auto"` (before `_follow`, so the state write carries it; for an assumed child the reset is not visible, which is the point).

`tests/test_fan_speed_control.py`:

```python
from custom_components.dual_smart_thermostat.hvac_device.fan_speed import FanSpeedControl
from tests import common


@pytest.mark.asyncio
async def test_climate_fan_modes_are_used_verbatim(hass: HomeAssistant):
    await common.add_fake_climate(hass, "climate.test_ac", fan_mode="quiet")

    speed = FanSpeedControl(hass, "climate.test_ac")

    assert speed.supports_fan_mode is True
    assert speed.fan_modes == ["quiet", "strong", "auto"]  # no mapping to low/medium/high
    assert speed.current_fan_mode == "quiet"


@pytest.mark.asyncio
async def test_climate_without_fan_modes_has_no_speed_control(hass: HomeAssistant):
    hass.states.async_set("climate.bare", "off", {"hvac_modes": ["off", "cool"]})

    assert FanSpeedControl(hass, "climate.bare").supports_fan_mode is False


@pytest.mark.asyncio
async def test_climate_speed_is_set_with_climate_set_fan_mode(hass: HomeAssistant):
    child = await common.add_fake_climate(hass, "climate.test_ac")
    speed = FanSpeedControl(hass, "climate.test_ac")

    await speed.async_set_fan_mode("strong")

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls
    assert speed.current_fan_mode == "strong"


@pytest.mark.asyncio
async def test_climate_speed_outside_the_childs_modes_is_refused(
    hass: HomeAssistant, caplog
):
    child = await common.add_fake_climate(hass, "climate.test_ac")
    speed = FanSpeedControl(hass, "climate.test_ac")

    await speed.async_set_fan_mode("turbo")

    assert child.calls == []
    assert "Invalid fan mode" in caplog.text


@pytest.mark.asyncio
async def test_climate_speed_already_set_is_not_resent(hass: HomeAssistant):
    child = await common.add_fake_climate(hass, "climate.test_ac", fan_mode="strong")
    speed = FanSpeedControl(hass, "climate.test_ac")

    await speed.async_set_fan_mode("strong")

    assert child.calls == []  # the child already reports it
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/test_fan_speed_control.py -k "climate" -v
```

Expected: FAIL (`supports_fan_mode` is `False`: climate is not a source yet).

- [ ] **Step 3: Implement**

`FanSpeedControl._detect_fan_capabilities`, after the `fan` branch and before the final "does not support speed control" log:

```python
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
```

`async_set_fan_mode`: add the climate service branch before the existing `if self._uses_preset_modes:`:

```python
        if self._is_climate:
            state = self.hass.states.get(self.entity_id)
            # A reported-state child that already has it needs no call; an
            # assumed-state one cannot tell us, so it is always sent.
            if (
                state is not None
                and not state.attributes.get("assumed_state")
                and state.attributes.get("fan_mode") == fan_mode
            ):
                self._current_fan_mode = fan_mode
                return
            await self.hass.services.async_call(
                "climate",
                "set_fan_mode",
                {"entity_id": self.entity_id, "fan_mode": fan_mode},
                blocking=True,
            )
            self._current_fan_mode = fan_mode
            return
```

with `self._is_climate = split_entity_id(entity_id)[0] == "climate"` set in `__init__` and exposed as the read-only property `is_climate`. The validation against `self._fan_modes` that already precedes the service call covers the "invalid mode" case (it logs `Invalid fan mode ...` and returns).

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/test_fan_speed_control.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Fan speed: climate fan_modes as a detection source (verbatim)

Refs #281"
```

---

## Task 3: Any climate role gets speed control; precedence is structural

**Files:**
- Test: `tests/features/test_climate_backed_devices.py`
- Modify (only if a test fails): `hvac_device/hvac_device_factory.py` from task 1

- [ ] **Step 1: Write the tests**

```python
FAN = "fan.test_fan"


async def test_cooler_only_ac_gets_fan_speed_control(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 24.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC)
    await hass.async_block_till_done()

    state = hass.states.get("climate.test")
    assert state.attributes["fan_modes"] == ["quiet", "strong", "auto"]

    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls
    assert hass.states.get("climate.test").attributes["fan_mode"] == "strong"


async def test_separate_fan_entity_owns_fan_mode_and_the_ac_is_left_alone(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(FAN, "off", {"preset_modes": ["low", "high"], "preset_mode": "low"})
    hass.states.async_set(SENSOR, 24.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=FAN,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_modes"] == ["low", "high"]

    calls = async_mock_service(hass, "fan", "set_preset_mode")
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "high"},
        blocking=True,
    )

    assert len(calls) == 1
    assert all(c[0] != "set_fan_mode" for c in child.calls)  # the AC's speed is untouched


async def test_climate_fan_role_is_the_fan_speed_target(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 24.0)
    await _setup(
        hass, heater=HEATER, cooler=AC, fan=AC, fan_mode=True, initial_hvac_mode=HVACMode.COOL
    )
    await common.add_fake_climate(hass, AC)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_modes"] == ["quiet", "strong", "auto"]


async def test_switch_only_setup_has_no_fan_speed(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 24.0)
    await _setup(hass, heater=HEATER, initial_hvac_mode=HVACMode.HEAT)

    assert "fan_modes" not in hass.states.get("climate.test").attributes
```

(`async_mock_service` is `tests.common.async_mock_service`, already in the repo. Import it in the module.)

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "fan_speed or fan_mode_and_the_ac or fan_role_is" -v
```

Expected: PASS when tasks 1 and 2 are right. A failure here means selection is wrong; fix `_select_fan_speed` or `FeatureManager`, never add a check at the call sites.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Fan speed: any climate role gets it; separate fan entity takes precedence

Refs #281"
```

---

## Task 4: Re-apply the speed after each turn on

**Files:**
- Modify: `hvac_device/entity_port.py`, `hvac_device/fan_speed.py`, `hvac_device/generic_hvac_device.py`, `hvac_device/fan_device.py`
- Test: `tests/features/test_climate_backed_devices.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_fan_speed_is_reapplied_after_the_ac_resets_it(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, resets_fan_on_mode_change=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    child.calls.clear()

    await common.async_set_temperature(hass, 24, "climate.test")  # too hot: AC turns on
    await hass.async_block_till_done()

    order = [c[0] for c in child.calls]
    assert order.index("set_hvac_mode") < order.index("set_fan_mode")
    assert ("set_fan_mode", {"fan_mode": "quiet"}) in child.calls
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"


async def test_fan_speed_is_reapplied_on_an_assumed_state_child(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    child.calls.clear()

    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls  # no state to compare with


async def test_a_separate_fan_entity_means_no_reapply_on_the_ac(hass: HomeAssistant) -> None:
    hass.states.async_set(FAN, "off", {"preset_modes": ["low", "high"], "preset_mode": "low"})
    hass.states.async_set(SENSOR, 26.0)
    await _setup(
        hass, heater=HEATER, cooler=AC, fan=FAN, fan_mode=True, initial_hvac_mode=HVACMode.COOL
    )
    child = await common.add_fake_climate(hass, AC, resets_fan_on_mode_change=True)
    async_mock_service(hass, "fan", "set_preset_mode")

    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert all(c[0] != "set_fan_mode" for c in child.calls)


async def test_fan_role_on_the_climate_applies_the_speed_once(hass: HomeAssistant) -> None:
    hass.states.async_set(SENSOR, 26.0)
    await _setup(
        hass, heater=HEATER, cooler=AC, fan=AC, fan_mode=True, initial_hvac_mode=HVACMode.FAN_ONLY
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    child.calls.clear()

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY, "climate.test")
    await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("set_fan_mode") == 1  # port, not FanDevice too
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "reapplied or no_reapply or applies_the_speed_once" -v
```

Expected: FAIL (no `set_fan_mode` after the AC turns on).

- [ ] **Step 3: Implement**

`FanSpeedControl`:

```python
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
```

`entity_port.py`: `make_port(..., fan_speed: Callable[[], FanSpeedControl | None] = lambda: None)`; `ClimatePort.__init__` stores it and `async_turn_on` ends with:

```python
        speed = self._fan_speed()
        if speed is not None:
            await speed.async_reapply(self.entity_id)
```

(after the mode and target are set, so the speed lands last.)

`GenericHVACDevice.__init__`: pass `fan_speed=lambda: features.fan_speed` to `make_port` (lazy: the factory selects the control after the devices are built).

`FanDevice.async_turn_on`: skip the explicit "apply the selected mode" block when `self.speed.is_climate` (the port already re-applied it).

- [ ] **Step 4: Run to verify pass and the fan tests**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py tests/test_fan_speed_control.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Re-apply the selected fan speed after every climate turn on

Refs #281"
```

---

## Task 5: Restore across restarts and late discovery

**Files:**
- Test: `tests/features/test_climate_backed_devices.py`
- Modify (only if a test fails): `hvac_device/fan_speed.py`, `climate.py`

- [ ] **Step 1: Write the tests**

```python
from homeassistant.core import State

from tests.common import mock_restore_cache


async def test_fan_speed_is_restored_after_a_restart(hass: HomeAssistant) -> None:
    mock_restore_cache(
        hass,
        [State("climate.test", "cool", {"fan_mode": "strong", "temperature": 24})],
    )
    hass.states.async_set(SENSOR, 26.0)
    await common.add_fake_climate(hass, AC)  # the child is up before the thermostat
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_mode"] == "strong"


async def test_fan_speed_restore_waits_for_a_late_child(hass: HomeAssistant) -> None:
    mock_restore_cache(
        hass,
        [State("climate.test", "cool", {"fan_mode": "strong", "temperature": 24})],
    )
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    assert "fan_modes" not in hass.states.get("climate.test").attributes  # child not there yet

    child = await common.add_fake_climate(hass, AC)  # integration connects late
    await hass.async_block_till_done()

    state = hass.states.get("climate.test")
    assert state.attributes["fan_modes"] == ["quiet", "strong", "auto"]
    assert state.attributes["fan_mode"] == "strong"
    assert child is not None


async def test_late_child_without_fan_modes_never_gains_speed_control(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set(SENSOR, 26.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)

    hass.states.async_set(AC, "off", {"hvac_modes": ["off", "cool"]})
    await hass.async_block_till_done()

    assert "fan_modes" not in hass.states.get("climate.test").attributes
```

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_backed_devices.py -k "restored_after or restore_waits or never_gains" -v
```

Expected: PASS: the restore holds the value until detection succeeds and `redetect_capabilities` runs on the child's state change, both moved unchanged in task 1 (`climate.py` already sets the `FAN_MODE` feature bit when redetect returns `True`). If the late case fails, the likely cause is that `_async_switch_changed_event` reads the old `features.fan_device`; fix the read, not the test.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Fan speed: restore and late-discovery coverage for climate children

Refs #281"
```

---

## Task 6: Docs, lint, full suite

- [ ] **Step 1:** Update `custom_components/dual_smart_thermostat/hvac_device/CLAUDE.md` "Speed control": add the climate source (`fan_modes` verbatim, `climate.set_fan_mode`), the single fan-speed target chosen by the factory (fan device wins, else first climate role), the re-apply after turn on, and that detection is still automatic. Add a line to the README climate section: "A climate entity's own fan modes are available as the thermostat's fan mode, unless a separate fan entity is configured, which then owns it."
- [ ] **Step 2:** `./scripts/docker-lint --fix && ./scripts/docker-lint`
- [ ] **Step 3:** `./scripts/docker-test`
- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Docs and lint for climate fan speed

Refs #281"
```

## Acceptance (phase 3b)

1. A climate filling any role (cooler-only AC included) exposes `fan_modes` and `fan_mode`, with the child's modes verbatim and `climate.set_fan_mode`.
2. With a separate fan entity configured, `fan_mode` drives that device and the AC's fan speed is never touched.
3. Exactly one fan-speed target exists per thermostat, chosen once in the factory; no call site decides ownership.
4. The selected speed is re-applied after each turn on of the child (reported-state and assumed-state), once, not twice, when the climate is also the fan role.
5. Restore across restarts and late discovery work as they do for fans.
6. Switch-only and `fan`-entity setups behave exactly as before (the whole existing suite passes).
