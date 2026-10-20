# Climate Entity Devices - Phase 4: Config, Reconfigure and Options Flows - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Everything phases 1 to 3 made possible in YAML becomes reachable from the UI: climate entities selectable for heater/cooler/fan/dryer, `target_sensor` optional when a climate role exists, a `climate_control` step (`control_style`, `setpoint_offset`) in the config, reconfigure and options flows, dependency tracking, translations, README and an example.

**Architecture:** Follows `.claude/skills/config-flow-integration`. One shared step handler `feature_steps/climate_control.py` (same shape as `FanSteps`) used by both flows. The step is part of "basic entity configuration", so `_determine_next_step()` / `_determine_options_next_step()` route to it right after the entity step and before `features`; openings and presets stay the last two steps (`docs/config_flow/step_ordering.md`). "Has a climate role" is answered by `climate_roles.has_climate_role` (phase 1), the same function YAML validation and runtime use, so flow and runtime cannot disagree.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, voluptuous selectors, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md`
**Previous phases:** 1 to 3 merged (`climate_roles.py`, `ControlStyle`, `CONF_CONTROL_STYLE`, `CONF_SETPOINT_OFFSET`, `normalize_climate_roles`).

---

## Testing Environment

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
python tools/config_validator.py        # dependency validator, task 7 (runs locally, no HA needed)
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly.

---

## Shared Context

### Flow wiring points (verified in the code)

| Concern | Location |
|---|---|
| Entity steps (`basic`, `basic_ac_only`, `heater_cooler`, `heat_pump`, `dual_stage`, `floor_heating`) | all end in `await self._determine_next_step()` |
| Config-flow routing and the first stop `features_shown` | `config_flow.py` `_determine_next_step` |
| Reconfigure | `async_step_reconfigure` seeds `collected_config` from the entry, clears the `*_shown` flags, then reuses the same entity steps |
| Options routing | `options_flow.py` `_determine_options_next_step`; step flags cleared in `async_step_init` (`step_flags`) and excluded from saved data by `_get_excluded_flags` |
| Shared step handlers | `feature_steps/fan.py` (`FanSteps`), `floor.py`, `humidity.py`, `openings.py`, `presets.py` |
| Role selectors | `schemas.py`: every `get_entity_selector([SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN])` on `CONF_HEATER` / `CONF_COOLER` / `CONF_DRYER`; `FAN_ENTITY_DOMAINS` for `CONF_FAN`. `CONF_AUX_HEATER` selectors stay as they are (no climate). |
| Duplicate entity checks | `flow_utils.EntityValidator` and an inline copy inside `config_flow.async_step_heater_cooler` |

### Decisions

- The sensor selector becomes optional in every schema; the rule "sensor or a climate role" is enforced by `EntityValidator` with error key `sensor_required`.
- `same_heater_cooler` / `same_heater_sensor` apply only to non-climate entities (a climate entity is legitimately the heater, the cooler, and the temperature source).
- The inline duplicate error logic in `async_step_heater_cooler` is replaced by `EntityValidator.get_validation_errors`, so the rule lives in one place.
- Stale climate keys are dropped when no climate role remains (reconfigure from climate to switches).

---

## Task 1: Climate domain in the role selectors

**Files:**
- Modify: `schemas.py`
- Test: `tests/unit/test_heater_cooler_schema.py`, `tests/unit/test_heat_pump_schema.py`, `tests/unit/test_schema_utils.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_heater_cooler_schema.py` (reuse the module's existing schema construction):

```python
from custom_components.dual_smart_thermostat.schemas import (
    get_fan_schema,
    get_heater_cooler_schema,
)


def test_heater_and_cooler_accept_climate_entities() -> None:
    schema = get_heater_cooler_schema(hass=None, defaults={}, include_name=True)
    validated = schema(
        {
            "name": "T",
            "target_sensor": "sensor.t",
            "heater": "climate.ac",
            "cooler": "climate.ac",
        }
    )
    assert validated["heater"] == "climate.ac"
    assert validated["cooler"] == "climate.ac"


def test_fan_accepts_climate_entity() -> None:
    assert get_fan_schema(hass=None)({"fan": "climate.ac"})["fan"] == "climate.ac"


def test_aux_heater_still_rejects_climate_entity() -> None:
    from custom_components.dual_smart_thermostat.schemas import get_dual_stage_schema
    import pytest
    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        get_dual_stage_schema()({"heater": "switch.h", "secondary_heater": "climate.ac"})
```

`tests/unit/test_heat_pump_schema.py`:

```python
def test_heat_pump_heater_accepts_climate_entity() -> None:
    schema = get_heat_pump_schema(hass=None, defaults={}, include_name=True)  # use the helper this file already imports
    assert schema(
        {
            "name": "T",
            "target_sensor": "sensor.t",
            "heater": "climate.hp",
            "heat_pump_cooling": "binary_sensor.cooling",
        }
    )["heater"] == "climate.hp"
```

(Match the exact factory/argument names the neighbouring tests in each file use; the assertions are what matter.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/unit/test_heater_cooler_schema.py tests/unit/test_heat_pump_schema.py -k "climate" -v
```

Expected: FAIL (`value must be one of ... for dictionary value @ data['heater']`, or entity domain rejected).

- [ ] **Step 3: Implement**

In `schemas.py` near `FAN_ENTITY_DOMAINS`:

```python
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN

# What a heater, cooler or dryer role may be backed by.
DEVICE_ENTITY_DOMAINS = [SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN, CLIMATE_DOMAIN]
FAN_ENTITY_DOMAINS = [SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN, FAN_DOMAIN, CLIMATE_DOMAIN]
```

Then:

```bash
grep -n "\[SWITCH_DOMAIN, INPUT_BOOLEAN_DOMAIN\]" custom_components/dual_smart_thermostat/schemas.py
```

Replace the literal with `DEVICE_ENTITY_DOMAINS` on every hit whose field is `CONF_HEATER`, `CONF_COOLER` or `CONF_DRYER` (including the `ac_only` core schema that stores the AC under `CONF_HEATER`). Leave every `CONF_AUX_HEATER` hit untouched.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/unit -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Flows: accept climate entities for heater, cooler, fan, dryer

Refs #281"
```

---

## Task 2: Optional sensor and entity validation

**Files:**
- Modify: `schemas.py`, `flow_utils.py`, `config_flow.py`
- Test: `tests/config_flow/test_heater_cooler_flow.py`, `tests/config_flow/test_config_flow_validation.py`

- [ ] **Step 1: Write the failing tests**

`tests/config_flow/test_heater_cooler_flow.py` (existing `mock_hass` fixture and imports; add `CONF_CONTROL_STYLE`, `CONF_SETPOINT_OFFSET` to the import list):

```python
class TestClimateRolesInHeaterCoolerFlow:
    """Climate entities as device roles (issue #281)."""

    async def test_same_climate_entity_as_heater_and_cooler_is_allowed(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "AC",
                CONF_SENSOR: "sensor.t",
                CONF_HEATER: "climate.ac",
                CONF_COOLER: "climate.ac",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] != "heater_cooler"  # moved on, no error

    async def test_same_switch_as_heater_and_cooler_is_still_rejected(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "AC",
                CONF_SENSOR: "sensor.t",
                CONF_HEATER: "switch.x",
                CONF_COOLER: "switch.x",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert result["step_id"] == "heater_cooler"
        assert result["errors"] == {"base": "same_heater_cooler"}

    async def test_sensor_is_required_without_a_climate_role(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "T",
                CONF_HEATER: "switch.h",
                CONF_COOLER: "switch.c",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert result["step_id"] == "heater_cooler"
        assert result["errors"] == {"base": "sensor_required"}

    async def test_sensor_is_optional_with_a_climate_role(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "T",
                CONF_HEATER: "switch.h",
                CONF_COOLER: "climate.ac",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert result["step_id"] != "heater_cooler"
        assert CONF_SENSOR not in flow.collected_config
```

`tests/config_flow/test_config_flow_validation.py`:

```python
from custom_components.dual_smart_thermostat.flow_utils import EntityValidator


def test_climate_entity_may_be_heater_and_temperature_source() -> None:
    cfg = {"heater": "climate.ac", "target_sensor": "climate.ac"}
    assert EntityValidator.validate_basic_config(cfg) is True
    assert EntityValidator.get_validation_errors(cfg) == {}


def test_missing_sensor_without_climate_role_is_an_error() -> None:
    errors = EntityValidator.get_validation_errors({"heater": "switch.h"})
    assert errors == {"base": "sensor_required"}
    assert EntityValidator.validate_basic_config({"heater": "switch.h"}) is False
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/config_flow/test_heater_cooler_flow.py tests/config_flow/test_config_flow_validation.py -k "climate or sensor_is or missing_sensor" -v
```

Expected: FAIL (`same_heater_cooler` for the climate pair; schema requires the sensor).

- [ ] **Step 3: Implement**

`flow_utils.py`:

```python
from .climate_roles import has_climate_role, is_climate_entity

    @staticmethod
    def get_validation_errors(user_input: dict[str, Any]) -> dict[str, str]:
        errors = {}
        heater = user_input.get(CONF_HEATER)
        sensor = user_input.get(CONF_SENSOR)
        cooler = user_input.get(CONF_COOLER)

        # A climate entity is legitimately several roles and its own temperature source.
        if heater and sensor and heater == sensor and not is_climate_entity(heater):
            errors["base"] = "same_heater_sensor"
        elif heater and cooler and heater == cooler and not is_climate_entity(heater):
            errors["base"] = "same_heater_cooler"
        elif not sensor and not has_climate_role(user_input):
            errors["base"] = "sensor_required"

        return errors

    @staticmethod
    def validate_basic_config(user_input: dict[str, Any]) -> bool:
        return not EntityValidator.get_validation_errors(user_input)
```

(`validate_basic_config` was a second copy of the same two rules; it now derives from the one function so they cannot drift.)

`config_flow.async_step_heater_cooler`: replace the inline block

```python
            if not await self._validate_basic_config(user_input):
                heater = ...
                ...
```

with

```python
            if not await self._validate_basic_config(user_input):
                errors = EntityValidator.get_validation_errors(user_input)
```

(the shape the `basic` step already uses). Check the other entity steps (`heat_pump`, `dual_stage`, `floor_heating`, `basic_ac_only`) for the same pattern and apply it where an inline copy exists.

`schemas.py`: every `vol.Required(CONF_SENSOR, ...)` becomes `vol.Optional(CONF_SENSOR, ...)`:

```bash
grep -n "vol.Required(\s*CONF_SENSOR\|vol.Required(CONF_SENSOR" custom_components/dual_smart_thermostat/schemas.py
```

(note the `default=defaults.get(CONF_SENSOR) if defaults else vol.UNDEFINED` forms; keep their defaults).

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/config_flow tests/unit -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Flows: optional temperature sensor with a climate role; single entity validator

Refs #281"
```

---

## Task 3: `climate_control` step in the config and reconfigure flows

**Files:**
- Create: `feature_steps/climate_control.py`
- Modify: `feature_steps/__init__.py`, `schemas.py`, `config_flow.py`
- Test: `tests/config_flow/test_heater_cooler_flow.py`, `tests/config_flow/test_step_ordering.py`, `tests/config_flow/test_reconfigure_flow.py`

- [ ] **Step 1: Write the failing tests**

`tests/config_flow/test_heater_cooler_flow.py`, in `TestClimateRolesInHeaterCoolerFlow`:

```python
    async def test_climate_role_routes_through_climate_control_step(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "T",
                CONF_SENSOR: "sensor.t",
                CONF_HEATER: "switch.h",
                CONF_COOLER: "climate.ac",
                CONF_HEAT_COOL_MODE: False,
            }
        )
        assert result["step_id"] == "climate_control"

        result = await flow.async_step_climate_control(
            {CONF_CONTROL_STYLE: "setpoint", CONF_SETPOINT_OFFSET: -2.0}
        )
        assert result["step_id"] == "features"
        assert flow.collected_config[CONF_CONTROL_STYLE] == "setpoint"
        assert flow.collected_config[CONF_SETPOINT_OFFSET] == -2.0

    async def test_switch_only_setup_skips_climate_control(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "T",
                CONF_SENSOR: "sensor.t",
                CONF_HEATER: "switch.h",
                CONF_COOLER: "switch.c",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert result["step_id"] == "features"

    async def test_stale_climate_keys_are_dropped_when_no_climate_role_remains(
        self, mock_hass
    ):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_CONTROL_STYLE: "setpoint",
            CONF_SETPOINT_OFFSET: 3.0,
        }

        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "T",
                CONF_SENSOR: "sensor.t",
                CONF_HEATER: "switch.h",
                CONF_COOLER: "switch.c",
                CONF_HEAT_COOL_MODE: False,
            }
        )

        assert CONF_CONTROL_STYLE not in flow.collected_config
        assert CONF_SETPOINT_OFFSET not in flow.collected_config

    async def test_setpoint_with_climate_heat_pump_is_rejected_in_the_step(
        self, mock_hass
    ):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {
            CONF_SYSTEM_TYPE: "heat_pump",
            CONF_HEATER: "climate.hp",
            "heat_pump_cooling": "binary_sensor.cooling",
        }

        result = await flow.async_step_climate_control(
            {CONF_CONTROL_STYLE: "setpoint", CONF_SETPOINT_OFFSET: 0.0}
        )

        assert result["step_id"] == "climate_control"
        assert result["errors"] == {"base": "setpoint_heat_pump_unsupported"}
```

`tests/config_flow/test_step_ordering.py` (reuse the file's existing flow-driving helper):

```python
async def test_climate_control_comes_before_features_and_openings_presets_stay_last(
    mock_hass,
) -> None:
    flow = ConfigFlowHandler()
    flow.hass = mock_hass
    flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}

    visited = []
    result = await flow.async_step_heater_cooler(
        {
            CONF_NAME: "T",
            CONF_HEATER: "climate.ac",
            CONF_COOLER: "climate.ac",
            CONF_HEAT_COOL_MODE: False,
        }
    )
    visited.append(result["step_id"])
    result = await flow.async_step_climate_control(
        {CONF_CONTROL_STYLE: "on_off", CONF_SETPOINT_OFFSET: 0.0}
    )
    visited.append(result["step_id"])

    assert visited == ["climate_control", "features"]
```

`tests/config_flow/test_reconfigure_flow.py`:

```python
async def test_reconfigure_revisits_climate_control(mock_hass, heater_cooler_climate_entry) -> None:
    """The shown-flag is cleared, so reconfigure passes through the step again."""
    flow = ConfigFlowHandler()
    flow.hass = mock_hass
    flow.collected_config = {"climate_control_shown": True}
    # drive async_step_reconfigure exactly as the neighbouring tests do, then:
    assert "climate_control_shown" not in flow.collected_config
```

(Add the fixture `heater_cooler_climate_entry` next to the module's other config-entry fixtures: a `MockConfigEntry` whose data has `heater: switch.h`, `cooler: climate.ac`, `target_sensor: sensor.t`, `system_type: heater_cooler`. Drive `async_step_reconfigure` the way `test_reconfigure_flow_e2e_heater_cooler.py` does and assert the flow reaches `climate_control` after the entity step.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/config_flow -k "climate_control or climate_role or stale_climate or setpoint_with_climate" -v
```

Expected: FAIL (`AttributeError: ... async_step_climate_control`).

- [ ] **Step 3: Implement**

`climate_roles.setpoint_unsupported` already exists (phase 2); the step below reuses it so the flow and YAML validation share one rule.

`schemas.py`:

```python
from homeassistant.helpers import selector

def get_climate_control_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """control_style and setpoint_offset for climate-backed roles."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_CONTROL_STYLE,
                default=defaults.get(CONF_CONTROL_STYLE, DEFAULT_CONTROL_STYLE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[style.value for style in ControlStyle],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="control_style",
                )
            ),
            vol.Optional(
                CONF_SETPOINT_OFFSET,
                default=defaults.get(CONF_SETPOINT_OFFSET, DEFAULT_SETPOINT_OFFSET),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-20, max=20, step=0.5, mode=selector.NumberSelectorMode.BOX
                )
            ),
        }
    )
```

`feature_steps/climate_control.py` (same shape as `FanSteps`):

```python
"""Climate-backed device control steps."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult

from ..climate_roles import setpoint_unsupported
from ..schemas import get_climate_control_schema


class ClimateControlSteps:
    """control_style / setpoint_offset, shared by the config and options flows."""

    async def _async_step(
        self,
        step_id: str,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        defaults: dict,
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            candidate = {**collected_config, **user_input}
            if setpoint_unsupported(candidate):
                errors["base"] = "setpoint_heat_pump_unsupported"
            else:
                collected_config.update(user_input)
                return await next_step_handler()
        return flow_instance.async_show_form(
            step_id=step_id,
            data_schema=get_climate_control_schema({**defaults, **(user_input or {})}),
            errors=errors,
        )

    async def async_step_config(
        self, flow_instance, user_input, collected_config, next_step_handler
    ) -> FlowResult:
        return await self._async_step(
            "climate_control",
            flow_instance,
            user_input,
            collected_config,
            next_step_handler,
            collected_config,
        )

    async def async_step_options(
        self, flow_instance, user_input, collected_config, next_step_handler, current_config
    ) -> FlowResult:
        return await self._async_step(
            "climate_control_options",
            flow_instance,
            user_input,
            collected_config,
            next_step_handler,
            current_config,
        )
```

Export it in `feature_steps/__init__.py` next to `FanSteps`.

`config_flow.py`:

```python
        self.climate_control_steps = ClimateControlSteps()   # in __init__, beside fan_steps

    async def async_step_climate_control(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose how climate-backed devices are controlled."""
        return await self.climate_control_steps.async_step_config(
            self, user_input, self.collected_config, self._determine_next_step
        )
```

In `_determine_next_step`, as the first block, before the `features_shown` check:

```python
        # Climate-backed devices: part of basic entity configuration, so it
        # comes before features, openings and presets (step_ordering.md).
        if has_climate_role(self.collected_config):
            if "climate_control_shown" not in self.collected_config:
                self.collected_config["climate_control_shown"] = True
                return await self.async_step_climate_control()
        else:
            self.collected_config.pop(CONF_CONTROL_STYLE, None)
            self.collected_config.pop(CONF_SETPOINT_OFFSET, None)
```

Add `"climate_control_shown"` to `flow_control_flags` in `async_step_reconfigure`. Check where the config entry is created (the `async_create_entry` path / `_clean...`) for any list of transient flags that must also include `"climate_control_shown"` (`grep -n "features_shown" custom_components`); add it everywhere `features_shown` is stripped.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/config_flow -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Config and reconfigure flows: climate_control step

Refs #281"
```

---

## Task 4: `climate_control_options` step in the options flow

**Files:**
- Modify: `options_flow.py`
- Test: `tests/config_flow/test_options_flow.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.fixture
def climate_cooler_config_entry():
    """Heater cooler entry whose cooler is a climate entity."""
    entry = Mock()
    entry.data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "climate.ac",
        CONF_SENSOR: "sensor.t",
        CONF_CONTROL_STYLE: "on_off",
        CONF_SETPOINT_OFFSET: 0.0,
    }
    entry.options = {}
    entry.entry_id = "climate-entry"
    return entry


async def test_options_flow_offers_climate_control_for_climate_roles(
    mock_hass, climate_cooler_config_entry
):
    flow = OptionsFlowHandler(climate_cooler_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_init({})

    assert result["step_id"] == "climate_control_options"
    schema_keys = {str(k) for k in result["data_schema"].schema}
    assert {CONF_CONTROL_STYLE, CONF_SETPOINT_OFFSET} <= schema_keys


async def test_options_flow_saves_climate_control_values(
    mock_hass, climate_cooler_config_entry
):
    flow = OptionsFlowHandler(climate_cooler_config_entry)
    flow.hass = mock_hass
    await flow.async_step_init({})

    await flow.async_step_climate_control_options(
        {CONF_CONTROL_STYLE: "setpoint", CONF_SETPOINT_OFFSET: -3.0}
    )

    assert flow.collected_config[CONF_CONTROL_STYLE] == "setpoint"
    assert flow.collected_config[CONF_SETPOINT_OFFSET] == -3.0


async def test_options_flow_prefills_current_climate_control_values(
    mock_hass, climate_cooler_config_entry
):
    climate_cooler_config_entry.data = {
        **climate_cooler_config_entry.data,
        CONF_CONTROL_STYLE: "setpoint",
        CONF_SETPOINT_OFFSET: 2.5,
    }
    flow = OptionsFlowHandler(climate_cooler_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_init({})

    defaults = {str(k): k.default() for k in result["data_schema"].schema}
    assert defaults[CONF_CONTROL_STYLE] == "setpoint"
    assert defaults[CONF_SETPOINT_OFFSET] == 2.5


async def test_options_flow_skips_climate_control_for_switch_only_entries(
    mock_hass, dual_system_config_entry
):
    flow = OptionsFlowHandler(dual_system_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_init({})

    assert result["step_id"] != "climate_control_options"


async def test_climate_flag_is_not_saved_into_the_entry(
    mock_hass, climate_cooler_config_entry
):
    flow = OptionsFlowHandler(climate_cooler_config_entry)
    flow.hass = mock_hass
    await flow.async_step_init({})

    assert "climate_control_options_shown" in flow._get_excluded_flags()
```

(Add the new imports to the module's import block. `_get_excluded_flags` is a method on the handler as used in `async_step_init`.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/config_flow/test_options_flow.py -k "climate" -v
```

Expected: FAIL (no `climate_control_options` step).

- [ ] **Step 3: Implement**

`options_flow.py`:

```python
        self.climate_control_steps = ClimateControlSteps()   # beside fan_steps

    async def async_step_climate_control_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle control style and setpoint offset for climate-backed devices."""
        current_config = {**self._get_current_config(), **self.collected_config}
        return await self.climate_control_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            current_config,
        )
```

In `_determine_options_next_step`, first block (before dual stage):

```python
        # Climate-backed devices come first: they are basic entity configuration.
        if (
            has_climate_role(current_config)
            and "climate_control_options_shown" not in self.collected_config
        ):
            self.collected_config["climate_control_options_shown"] = True
            return await self.async_step_climate_control_options()
```

Add `"climate_control_options_shown"` to the `step_flags` list in `async_step_init` and to whatever `_get_excluded_flags` returns.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/config_flow -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Options flow: climate_control_options step

Refs #281"
```

---

## Task 5: Persistence end to end

**Files:**
- Test: `tests/config_flow/test_e2e_heater_cooler_persistence.py`, `tests/config_flow/test_reconfigure_flow_e2e_heater_cooler.py`
- Modify (only if a test fails): code from tasks 3 and 4

- [ ] **Step 1: Write the tests**

`tests/config_flow/test_e2e_heater_cooler_persistence.py` (follow the file's own helper for driving config flow then options flow on a real `MockConfigEntry`):

```python
async def test_heater_cooler_climate_control_persists_from_config_to_options(hass):
    """control_style / setpoint_offset survive config -> options and prefill."""
    entry = await _run_config_flow(  # the module's existing helper
        hass,
        heater="switch.heater",
        cooler="climate.ac",
        sensor=None,  # optional with a climate role
        extra_steps={"climate_control": {"control_style": "setpoint", "setpoint_offset": -2.0}},
    )

    assert entry.data["control_style"] == "setpoint"
    assert entry.data["setpoint_offset"] == -2.0
    assert "target_sensor" not in entry.data or not entry.data["target_sensor"]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    # init form, then submit it and land on the climate step with current values
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "climate_control_options"
    defaults = {str(k): k.default() for k in result["data_schema"].schema}
    assert defaults["control_style"] == "setpoint"
    assert defaults["setpoint_offset"] == -2.0


async def test_climate_control_values_that_are_falsy_are_kept(hass):
    """setpoint_offset 0.0 and on_off must persist, not be dropped as 'empty'."""
    entry = await _run_config_flow(
        hass,
        heater="climate.ac",
        cooler="climate.ac",
        sensor=None,
        extra_steps={"climate_control": {"control_style": "on_off", "setpoint_offset": 0.0}},
    )

    assert entry.data["setpoint_offset"] == 0.0
    assert entry.data["control_style"] == "on_off"
```

`tests/config_flow/test_reconfigure_flow_e2e_heater_cooler.py`:

```python
async def test_reconfigure_from_climate_to_switches_drops_climate_keys(hass):
    entry = _mock_entry(  # module's existing entry builder
        {
            "system_type": "heater_cooler",
            "name": "T",
            "heater": "switch.h",
            "cooler": "climate.ac",
            "control_style": "setpoint",
            "setpoint_offset": 2.0,
        }
    )
    # drive reconfigure: change cooler to a switch and submit sensor
    updated = await _run_reconfigure(  # module's existing helper
        hass, entry, heater="switch.h", cooler="switch.c", sensor="sensor.t"
    )

    assert "control_style" not in updated.data
    assert "setpoint_offset" not in updated.data
```

(Use the helper names that actually exist in each file; if there is no shared helper, inline the flow calls the way the neighbouring tests do.)

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/config_flow/test_e2e_heater_cooler_persistence.py tests/config_flow/test_reconfigure_flow_e2e_heater_cooler.py -k "climate" -v
```

Expected: PASS if tasks 3 and 4 are right. A FAIL here is a real persistence bug (for example a falsy-value filter in the entry-creation path dropping `0.0`): fix it in the flow code, not the test.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Flows: persistence and reconfigure tests for climate-backed devices

Refs #281"
```

---

## Task 6: Translations

**Files:**
- Modify: `translations/en.json` (+ other locales per what `test_translations.py` demands)
- Test: `tests/config_flow/test_translations.py`

- [ ] **Step 1: Run the existing translation test to see what parity it enforces**

```bash
./scripts/docker-test tests/config_flow/test_translations.py -v
```

Note which locales and keys it checks.

- [ ] **Step 2: Write the failing test**

Add to `tests/config_flow/test_translations.py` (use the module's loader helper for `en.json`):

```python
def test_climate_control_strings_exist_in_english() -> None:
    en = _load("en")
    config = en["config"]
    assert {"control_style", "setpoint_offset"} <= set(config["step"]["climate_control"]["data"])
    assert {"control_style", "setpoint_offset"} <= set(
        config["step"]["climate_control"]["data_description"]
    )
    options = en["options"]["step"]["climate_control_options"]
    assert {"control_style", "setpoint_offset"} <= set(options["data"])
    assert {"sensor_required", "setpoint_heat_pump_unsupported"} <= set(config["error"])
    assert {"on_off", "setpoint"} <= set(en["selector"]["control_style"]["options"])
```

Run it; expected FAIL (`KeyError: 'climate_control'`).

- [ ] **Step 3: Implement**

`translations/en.json`:

```json
"config": {
  "error": {
    "sensor_required": "Choose a temperature sensor, or use a climate entity as a device (its own temperature is then used)",
    "setpoint_heat_pump_unsupported": "Setpoint control is not supported for a climate heat pump"
  },
  "step": {
    "climate_control": {
      "title": "Climate Entity Control",
      "description": "One or more devices are climate entities. Choose how the thermostat controls them.",
      "data": {
        "control_style": "Control style",
        "setpoint_offset": "Setpoint offset"
      },
      "data_description": {
        "control_style": "On/off: this thermostat decides when to run the device and switches it on and off. Setpoint: the device stays on and regulates itself; this thermostat mirrors target, mode, presets and openings to it.",
        "setpoint_offset": "Added to the target temperature sent to the device. Use it when the device's own sensor reads differently from your room sensor. Default 0."
      }
    }
  }
},
"options": {
  "step": {
    "climate_control_options": {
      "title": "Climate Entity Control",
      "description": "Modify how climate entity devices are controlled.",
      "data": {
        "control_style": "Control style",
        "setpoint_offset": "Setpoint offset"
      },
      "data_description": {
        "control_style": "On/off: this thermostat switches the device on and off. Setpoint: the device regulates itself and mirrors this thermostat's target.",
        "setpoint_offset": "Added to the target temperature sent to the device. Default 0."
      }
    }
  }
},
"selector": {
  "control_style": {
    "options": {
      "on_off": "On/off (this thermostat decides)",
      "setpoint": "Setpoint (the device regulates itself)"
    }
  }
}
```

(Merge into the existing `config.error`, `config.step`, `options.step` and `selector` objects; do not replace them. The temperature sensor field labels that say it is required, if any, become "optional with a climate device".) Add the same keys with the English text to the other locale files in the same way the repo already does for untranslated strings (for example `sk.json` fallbacks) only if `test_translations.py` enforces parity.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/config_flow/test_translations.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Translations for the climate_control steps

Refs #281"
```

---

## Task 7: Dependency tracking

**Files:**
- Modify: `tools/config_validator.py`, `tools/focused_config_dependencies.py`, `tools/focused_config_dependencies.json`, `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`, `tools/README.md`, `docs/config_flow/step_ordering.md`

(`tools/` has no unit tests; verification is running the validator against positive and negative configs, per the skill.)

- [ ] **Step 1: Write the failing verification**

Save as a scratch file outside the repo, for example `/tmp/climate_roles_bad.yaml`, and a good one:

```yaml
# /tmp/climate_roles_bad.yaml
climate:
  - platform: dual_smart_thermostat
    name: Bad
    heater: switch.heater
    target_sensor: sensor.t
    control_style: setpoint
    setpoint_offset: 2
```

```yaml
# /tmp/climate_roles_good.yaml
climate:
  - platform: dual_smart_thermostat
    name: Good
    heater: climate.ac
    cooler: climate.ac
    control_style: setpoint
    setpoint_offset: 2
```

Run:

```bash
python tools/config_validator.py /tmp/climate_roles_bad.yaml
python tools/config_validator.py /tmp/climate_roles_good.yaml
```

(Check the script's `main` for the exact invocation; the bad file must report errors and the good one must be valid.) Expected now: bad file passes silently and good file fails the "heater and cooler must be different entities" conflict, which is the failing state.

- [ ] **Step 2: Implement**

`tools/config_validator.py`:

```python
        # Climate-backed device options need a climate role.
        self.climate_role_parameters = ["control_style", "setpoint_offset"]
        self.climate_role_keys = ["heater", "cooler", "fan", "dryer"]
```

In `validate_config`, before checking conflicts:

```python
        has_climate_role = any(
            str(config.get(key) or "").startswith("climate.")
            for key in self.climate_role_keys
        )
        for param in self.climate_role_parameters:
            if param in config and config[param] is not None and not has_climate_role:
                errors.append(
                    f"Parameter '{param}' requires heater, cooler, fan or dryer to be a climate entity"
                )
        if not config.get("target_sensor") and not has_climate_role:
            errors.append(
                "Parameter 'target_sensor' is required unless heater, cooler, fan or dryer is a climate entity"
            )
```

and in the conflict loop skip pairs whose shared value starts with `climate.`:

```python
                if config[param1] == config[param2] and not str(config[param1]).startswith("climate."):
```

Add the same suggestion text in `suggest_fixes`, and a `climate_devices` group in `get_feature_groups` (`enabled`: has climate role; parameters `control_style`, `setpoint_offset`).

`tools/focused_config_dependencies.py`: add `control_style` and `setpoint_offset` as `ConfigParameter(... requires=["climate_role"])` entries and matching `ConfigDependency` objects (follow the neighbouring `fan_mode` entries), then update `tools/focused_config_dependencies.json` accordingly (the generator writes to a hard-coded `/workspaces/...` path, so edit the JSON by hand to match the generator output: a `conditional_parameters` entry per key with `required_parameter: "heater|cooler|fan|dryer as a climate.* entity"`, `description`, `example`, and a `dependency_groups` entry).

`docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`: a new "Climate Entity Devices" section in the same shape as the floor section (enabling parameter: any of `heater`/`cooler`/`fan`/`dryer` being a `climate.*` entity; table of `control_style`, `setpoint_offset`; configuration example; note that `target_sensor` is then optional). Update the totals in the heading and `tools/README.md` (22 to 24 conditional dependencies).

`docs/config_flow/step_ordering.md`: under "Features Configuration Logical Ordering", item 1, append "(including the `climate_control` step when a device is a climate entity)".

- [ ] **Step 3: Run to verify pass**

```bash
python tools/config_validator.py /tmp/climate_roles_bad.yaml
python tools/config_validator.py /tmp/climate_roles_good.yaml
python tools/config_validator.py
```

Expected: bad file reports the two climate-role errors; good file is valid; the built-in self-check still passes.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "Dependency tracking for control_style, setpoint_offset and optional target_sensor

Refs #281"
```

---

## Task 8: README and example

**Files:**
- Modify: `README.md`
- Create: `examples/basic_configurations/climate_entity_roles.yaml`

- [ ] **Step 1: Write the docs**

`README.md`: a section "Climate entities as devices" (place it next to the section that documents `heater`/`cooler`), content:

- Any of `heater`, `cooler`, `fan`, `dryer` (and the heat pump `heater`) may be a `climate.*` entity; detected from the domain, mixed with switches freely.
- `control_style` table: `on_off` (default) and `setpoint`, with one sentence each on who decides.
- `setpoint_offset` and the typical reason for it (device sensor reads differently from the room sensor).
- `target_sensor` optional when a climate device exists, using the device's own temperature.
- One climate in several roles: only one mode at a time, so `fan_on_with_ac` / `fan_on_with_heater` are ignored for a fan on the same climate.
- Behaviour notes: respects `min_cycle_duration` (on_off), skips an unavailable device, infrared devices that report an assumed state are controlled from what the thermostat last sent.
- Limits: no fan speed or humidity from the climate entity; `setpoint` not supported for a climate heat pump; `secondary_heater` stays switch-only.
- Config flow: the "Climate Entity Control" step appears when a device is a climate entity.

`examples/basic_configurations/climate_entity_roles.yaml`: three short examples, using only generic ids.

```yaml
# Mixed room: climate cooler, smart-plug heater.
climate:
  - platform: dual_smart_thermostat
    name: Bedroom
    heater: switch.bedroom_heater_plug
    cooler: climate.bedroom_ac
    target_sensor: sensor.bedroom_temperature
    min_cycle_duration:
      minutes: 5

# Standalone AC in every role, using its own temperature (no target_sensor).
  - platform: dual_smart_thermostat
    name: Office
    heater: climate.office_ac
    cooler: climate.office_ac
    fan: climate.office_ac
    dryer: climate.office_ac
    humidity_sensor: sensor.office_humidity

# AC regulates itself; the thermostat mirrors target, presets and windows.
  - platform: dual_smart_thermostat
    name: Living room
    cooler: climate.living_room_ac
    heater: switch.living_room_radiator
    target_sensor: sensor.living_room_temperature
    control_style: setpoint
    setpoint_offset: -2
    openings:
      - binary_sensor.living_room_window
```

- [ ] **Step 2: Lint (codespell, markdown)**

```bash
./scripts/docker-lint
```

Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "Docs: climate entities as devices (README and example)

Refs #281"
```

---

## Task 9: Full verification

- [ ] **Step 1:** `./scripts/docker-lint --fix && ./scripts/docker-lint`
- [ ] **Step 2:** `./scripts/docker-test`
- [ ] **Step 3: Commit** any fixes: `git add -A && git commit -m "Lint and test fixes for climate entity flows

Refs #281"`

## Acceptance (phase 4)

1. Heater, cooler, fan and dryer selectors in config, reconfigure and options flows accept `climate` entities; `secondary_heater` does not.
2. The temperature sensor may be omitted exactly when a role is a climate entity; otherwise `sensor_required`.
3. A climate entity may be heater, cooler and temperature source at once; two identical switches are still rejected.
4. The `climate_control` step appears right after the entity step (config, reconfigure) and as the first options step, only when a climate role exists; openings and presets remain the last two steps.
5. `control_style` / `setpoint_offset` persist from config to options (including falsy values) and are dropped when no climate role remains.
6. A climate heat pump with `setpoint` is rejected in the step.
7. Dependency tools, docs, translations, README and the example are updated; `python tools/config_validator.py` accepts the good configuration and rejects the bad one.
