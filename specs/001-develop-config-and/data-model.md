# Data Model: Config & Options Flow (dual_smart_thermostat)

## High-level entities

- `ThermostatConfigEntry`
  - `entry_id`: string (Home Assistant generated)
  - `name`: string
  - `system_type`: enum {`simple_heater`, `ac_only`, `heater_cooler`, `heat_pump`}
  - `core_settings`: dict — keys vary by `system_type` (e.g., heater_switch, cooler_switch, heat_pump_mode)
  - `features`: list of feature keys (e.g., `fan`, `humidity`, `openings`, `floor_heating`, `presets`)
  - `feature_settings`: dict mapping feature -> settings dict

## Feature settings shapes (examples)

  - `fan_entity`: optional entity_id
  - `fan_mode_support`: optional boolean

  - `sensor`: optional entity_id
  - `target`: int (0-100)
  - `min`: int
  - `max`: int
  - `dry_tolerance`: int
  - `moist_tolerance`: int

  - `openings_entities`: list of entity_id
  - `behavior`: enum {`pause_on_open`, `ignore`}

  - `floor_sensor`: optional entity_id
  - `floor_target`: number

  - `presets_list`: list of preset objects (name, target_temp, optionally opening_refs)

2) Per-feature `feature_settings` shapes

The schemas implemented in `custom_components/dual_smart_thermostat/schemas.py` are the source of truth for feature keys, defaults and validation. The config and options flows render the same selectors and therefore produce the same keys. Below are the canonical persisted shapes that correspond to those schema factories.

- fan (object)
  - `fan`: string (entity_id), optional — corresponds to `CONF_FAN` (stored as `"fan"`)
  - `fan_on_with_ac`: boolean, optional, default `true` — corresponds to `CONF_FAN_ON_WITH_AC`
  - `fan_air_outside`: boolean, optional, default `false` — corresponds to `CONF_FAN_AIR_OUTSIDE`
  - `fan_hot_tolerance_toggle`: boolean, optional, default `false` — corresponds to `CONF_FAN_HOT_TOLERANCE_TOGGLE`

- humidity (object)
  - `humidity_sensor`: string (entity_id), required when humidity feature enabled — corresponds to `CONF_HUMIDITY_SENSOR` (stored as `"humidity_sensor"`)
  - `dryer`: string (entity_id), optional — corresponds to `CONF_DRYER`
  - `target_humidity`: integer (0-100), optional, default `50` — corresponds to `CONF_TARGET_HUMIDITY`
  - `min_humidity`: integer (0-100), optional, default `30` — corresponds to `CONF_MIN_HUMIDITY`
  - `max_humidity`: integer (0-100), optional, default `99` — corresponds to `CONF_MAX_HUMIDITY`
  - `dry_tolerance`: integer (1-20), optional, default `3` — corresponds to `CONF_DRY_TOLERANCE`
  - `moist_tolerance`: integer (1-20), optional, default `3` — corresponds to `CONF_MOIST_TOLERANCE`

- openings (object)
  - Persisted key: `openings` — corresponds to `CONF_OPENINGS` and is a list of opening objects (see below). The flows briefly use a transient `selected_openings` list while building the UI but the persisted `feature_settings` should contain `openings` when configured.
  - `openings_scope`: string enum {`all`, `heat`, `cool`, `heat_cool`, `fan_only`, `dry`}, optional, default `all` — corresponds to `CONF_OPENINGS_SCOPE`

  Opening object shape (each element in the `openings` list):
  - `entity_id`: string, required — the opening entity id
  - `timeout_open`: integer (seconds), optional, default `30` — corresponds to `ATTR_OPENING_TIMEOUT`
  - `timeout_close`: integer (seconds), optional, default `30` — corresponds to `ATTR_CLOSING_TIMEOUT`

- floor_heating (object)
  - `floor_sensor`: string (entity_id), optional — corresponds to `CONF_FLOOR_SENSOR`
  - `min_floor_temp`: number, optional, default `5` — corresponds to `CONF_MIN_FLOOR_TEMP`
  - `max_floor_temp`: number, optional, default `28` — corresponds to `CONF_MAX_FLOOR_TEMP`

- presets
  - The flows currently produce a flattened representation: a `presets` list (selected preset keys) plus per-preset temperature fields at the same level as other collected_config keys. This mirrors `get_preset_selection_schema()` + `get_presets_schema()` behavior in `schemas.py`.

  Persisted (flattened) presets shape produced by the flows:

  ```json
  "presets": ["home","away"],
  "home_temp": 21,
  "away_temp_low": 16,
  "away_temp_high": 24
  ```

  Rules:
  - The multi-select selector stores the selected preset keys under a `presets` list.
  - For each selected preset the dynamic schema adds either a single field `<preset>_temp` (when `heat_cool_mode` is false) or dual fields `<preset>_temp_low` and `<preset>_temp_high` (when `heat_cool_mode` is true).
  - The integration also supports older boolean-style persistence (per-preset boolean keys or the climate/platform legacy `CONF_PRESETS_OLD` keys); the schema factories contain fallbacks to parse legacy shapes.

  Validation constraints (presets):
  - `<preset>_temp`, `<preset>_temp_low`, `<preset>_temp_high`: numbers in range [5.0, 35.0]
  - When both low/high present enforce `low <= high` at runtime where applicable

  Note: The spec previously described a nested `presets.values` mapping. The current implementation stores presets in the flattened shape shown above (top-level `presets` list + per-preset fields). Future refactors may migrate to a nested mapping for clarity; any migration must be accompanied by migration code and contract tests.
## Notes
- Use schema factories in `schemas.py` to produce consistent schemas for config and options flows.

## Exact Data Models (stable, typed)

Below are precise data model shapes for each `system_type` core settings and for each feature's `feature_settings` object. These should be considered the canonical contract for persisted `ThermostatConfigEntry.data.feature_settings` mappings.

Notes:
- Use JSON-serializable primitives only (strings, numbers, booleans, lists, dicts).
- Defaults shown are applied when the user leaves optional fields blank; options flow must prefill values using the same defaults.
- Where appropriate, include validation constraints (range, allowed values).

1) Core `core_settings` per `system_type`

- simple_heater.core_settings (object)
  - `heater`: string (entity_id), required — corresponds to `CONF_HEATER` (stored as `"heater"`)
  - `target_sensor`: string (entity_id), required — corresponds to `CONF_SENSOR` (stored as `"target_sensor"`)
  - `cold_tolerance`: number (float), optional, default `DEFAULT_TOLERANCE` — corresponds to `CONF_COLD_TOLERANCE`
  - `hot_tolerance`: number (float), optional, default `DEFAULT_TOLERANCE` — corresponds to `CONF_HOT_TOLERANCE`
  - `min_cycle_duration`: integer (seconds), optional, default `300` — corresponds to `CONF_MIN_DUR`

Notes:
- The keys above use the actual persisted names from `custom_components/dual_smart_thermostat/const.py` (e.g. `"target_sensor"`, `"min_cycle_duration"`). These match the selectors and defaults defined in `schemas.py` (`get_simple_heater_schema`).
- `hvac_device_factory.py` expects `config[CONF_HEATER]` (i.e. the `"heater"` key) and reads `CONF_MIN_DUR` for `min_cycle_duration` (used as a `timedelta` in the factory). Ensure any migration/normalization converts stored `min_cycle_duration` to the expected type (seconds -> timedelta) where necessary.

Example persisted `core_settings` for `simple_heater`:

```
"core_settings": {
  "heater": "switch.living_room_heater",
  "target_sensor": "sensor.living_room_temp",
  "cold_tolerance": 0.3,
  "hot_tolerance": 0.3,
  "min_cycle_duration": 300
}
```

- ac_only.core_settings (object)
  - `target_sensor`: string (entity_id), required — corresponds to `CONF_SENSOR` (stored as `"target_sensor"`)
  - `heater`: string (entity_id), required — used to store the AC switch under the legacy `CONF_HEATER` key for compatibility
  - `ac_mode`: boolean, hidden and implicitly `true` for AC-only system_type — corresponds to `CONF_AC_MODE` (the config and options flows should set this to `true` and hide the selector)
  - `cold_tolerance` / `hot_tolerance` / `min_cycle_duration`: same semantics as `simple_heater` (see above), keys correspond to `CONF_COLD_TOLERANCE`, `CONF_HOT_TOLERANCE`, `CONF_MIN_DUR`

Notes:
- The AC-only implementation re-uses the `heater` key to keep backward compatibility (the code treats the heater field as the AC switch when `ac_mode` is enabled). `hvac_device_factory.py` therefore reads `config[CONF_HEATER]` for the switch even in AC-only systems.
- The `ac_mode` flag should be forced to `true` and hidden in both the config and options flow for the `ac_only` system type: use the schema factory `get_basic_ac_schema()` which omits the visible `ac_mode` selector and sets the selectors appropriately. Ensure the options flow pre-fills values and persists `ac_mode: true` for AC-only entries.

Example persisted `core_settings` for `ac_only`:

```
"core_settings": {
  "heater": "switch.living_room_ac",
  "target_sensor": "sensor.living_room_temp",
  "ac_mode": true,
  "cold_tolerance": 0.3,
  "hot_tolerance": 0.3,
  "min_cycle_duration": 300
}
```

- heater_cooler.core_settings (object)
  - `heater`: string (entity_id), required — corresponds to `CONF_HEATER`
  - `cooler`: string (entity_id), required for heater_cooler mode — corresponds to `CONF_COOLER`
  - `target_sensor`: string (entity_id), required — corresponds to `CONF_SENSOR`
  - `heat_cool_mode`: boolean, optional, default `False` — corresponds to `CONF_HEAT_COOL_MODE`
  - `cold_tolerance` / `hot_tolerance` / `min_cycle_duration`: same semantics as `simple_heater` (keys correspond to `CONF_COLD_TOLERANCE`, `CONF_HOT_TOLERANCE`, `CONF_MIN_DUR`)

Notes:
- `get_heater_cooler_schema()` in `schemas.py` defines these selectors and defaults. Persisted data should use the same keys so `hvac_device_factory.py` and other consumers can read `config[CONF_HEATER]` and `config[CONF_COOLER]` as expected.


- heater_with_cooler (alias: heater_cooler) — same shape as `heater_cooler`

- heat_pump.core_settings (object)
  - `heater`: string (entity_id), required — corresponds to `CONF_HEATER` (single switch used for heat and cool states)
  - `heat_pump_cooling`: boolean | string (entity_id), optional — corresponds to `CONF_HEAT_PUMP_COOLING`.
    - Preferred representation: an `entity_id` of a sensor/binary_sensor whose boolean state indicates whether the heat pump is currently in cooling mode (`true`) or heating mode (`false`).
    - Legacy/compact representation: a boolean may be used to force the device into a default cooling state at persist time, but this reduces dynamic behavior.
    - Recommendation: treat `heat_pump_cooling` as an entity selector in `schemas.py` (accept an entity id). The runtime device should read the entity state to determine the current operational mode and then expose the appropriate HVAC mode set.
  - `target_sensor`: string (entity_id), required — corresponds to `CONF_SENSOR`
  - `cold_tolerance` / `hot_tolerance` / `min_cycle_duration`: same semantics as `simple_heater`

Notes:
- The heat pump mode treats a single `heater` switch as a combined device; runtime logic uses `CONF_HEAT_PUMP_COOLING` to determine HVAC mode mapping. Persisted keys must match the schema factories in `schemas.py`.

Heat pump semantics and HVAC modes

- When `heat_pump_cooling` resolves to `true` (sensor state or persisted boolean), the thermostat's available HVAC modes should be restricted to the cooling set (e.g., `heat_cool`, `cool`, `off`) depending on `heat_cool_mode` configuration.
- When `heat_pump_cooling` resolves to `false`, the thermostat should expose the heating set (e.g., `heat_cool`, `heat`, `off`) accordingly.
- If the integration supports a dynamic sensor (`entity_id`) for `heat_pump_cooling`, the thermostat should listen to state changes and update available modes in real-time.

Example (entity-based):

```
"core_settings": {
  "heater": "switch.heat_pump_main",
  "target_sensor": "sensor.living_room_temp",
  "heat_pump_cooling": "binary_sensor.heat_pump_mode",  # entity whose state 'on' means cooling
  "cold_tolerance": 0.3,
  "hot_tolerance": 0.3
}
```

Implementation guidance:
- Update `schemas.py` to accept an entity selector for `CONF_HEAT_PUMP_COOLING` when building the heat pump schema (use `get_entity_selector(SENSOR_DOMAIN)` or `BINARY_SENSOR_DOMAIN` as appropriate).
- Update `config_flow.py` / `options_flow.py` to present an entity selector for `heat_pump_cooling` when `system_type == heat_pump` and to persist the entity id (or boolean) unchanged.
- In the HVAC device implementation, normalize `heat_pump_cooling` to a callable that returns current boolean state (reading the entity state when an entity id is provided, or returning the persisted boolean if provided).

2) Per-feature `feature_settings` shapes

- fan (object)
  - fan_entity: string (entity_id), optional
  - fan_mode_support: boolean, optional, default False
  - fan_on_with_ac: boolean, optional, default True
  - fan_air_outside: boolean, optional, default False

- humidity (object)
  - humidity_sensor: string (entity_id), optional
  - dryer_entity: string (entity_id), optional
  - target: integer (0-100), optional, default 50
  - min: integer (0-100), optional, default 30
  - max: integer (0-100), optional, default 99
  - dry_tolerance: integer (1-20), optional, default 3
  - moist_tolerance: integer (1-20), optional, default 3

- openings (object)
  - openings: list of opening objects (see below), optional
  - openings_scope: string enum {"all","heat","cool","heat_cool","fan_only","dry"}, optional, default "all"

  Opening object shape (each element in `openings` list):
  - entity_id: string, required
  - timeout_open: integer (seconds), optional, default 30
  - timeout_close: integer (seconds), optional, default 30

- floor_heating (object)
  - floor_sensor: string (entity_id), optional
  - floor_target: number (temperature), optional
  - min_floor_temp: number, optional, default 5
  - max_floor_temp: number, optional, default 28

- presets (object)
  - presets: list of preset keys (strings) present in selection order, optional
  - For each preset key present, the object includes either:
    - `{preset}_temp`: number (5-35) — when heat_cool_mode is False
    - `{preset}_temp_low` and `{preset}_temp_high`: numbers when heat_cool_mode is True

Detailed presets model (canonical mapping)

The presets feature is stored as a mapping where each preset key maps to an object that can contain any combination of the following six options. This supports the README's 6 options so presets are expressive and can be partially specified.

Presets persisted shape (object)

```
"presets": {
  "presets_order": ["home","away","eco"],         # optional list defining ordering / presence
  "values": {
    "home": {
      "temperature": 21,            # number, optional (applies when heat_cool_mode==False or as fallback)
      "target_temp_low": 20,        # number, optional (heat in heat_cool_mode)
      "target_temp_high": 23,       # number, optional (cool in heat_cool_mode)
      "humidity": 45,               # integer 0-100, optional (only valid if humidity feature enabled)
      "min_floor_temp": 7,          # number, optional
      "max_floor_temp": 26          # number, optional
    },
    "away": { ... }
  }
}
```

Rules and semantics:
- `presets_order` (optional): list of preset keys (strings). If present it defines which presets are active and their presentation order. If absent, `values` keys define available presets and order is unspecified.
- `values`: mapping from preset key -> preset object. Each preset object may include any subset of the six supported options.
- Temperature selection at runtime follows these rules:
  - If `heat_cool_mode` is True and both `target_temp_low` and `target_temp_high` are present for the active preset, use them depending on current hvac mode (heat => `target_temp_low`, cool/fan_only => `target_temp_high`).
  - Otherwise if `temperature` is present, it is used for single-mode operations (heat, cool, fan_only) or as a fallback.
- `humidity` is only meaningful when the `humidity` feature is enabled; otherwise it is ignored on load/validation.
- Floor temperature bounds (`min_floor_temp`, `max_floor_temp`) must follow `min <= max` when both present.

Validation constraints (presets):
- `temperature`, `target_temp_low`, `target_temp_high`: numbers in range [5.0, 35.0]
- `humidity`: integer in [0, 100]
- `min_floor_temp`, `max_floor_temp`: numbers, recommended defaults 5 and 28; when both present enforce `min_floor_temp <= max_floor_temp`.

Examples

Minimal example using `presets_order` and values:

```
"presets": {
  "presets_order": ["home","away"],
  "values": {
    "home": {"temperature": 21, "humidity": 45},
    "away": {"target_temp_low": 16, "target_temp_high": 24}
  }
}
```

Full example (embedded in the full persisted entry):

```
{
  "entry_id": "<ha-generated>",
  "name": "Living Room Thermostat",
  "system_type": "heater_cooler",
  "core_settings": { ... },
  "features": ["openings","presets","fan"],
  "feature_settings": {
    "presets": {
      "presets_order": ["home","away"],
      "values": {
        "home": {"temperature": 21, "humidity": 45, "max_floor_temp": 26},
        "away": {"target_temp_low": 16, "target_temp_high": 24}
      }
    }
  }
}
```

3) Canonical persisted entry shape (ThermostatConfigEntry.data)

Example full config entry data (JSON):

{
  "entry_id": "<ha-generated>",
  "name": "Living Room Thermostat",
  "system_type": "heater_cooler",
  "core_settings": {
    "heater_entity": "switch.living_room_heater",
    "cooler_entity": "switch.living_room_ac",
    "sensor_entity": "sensor.living_room_temp",
    "heat_cool_mode": true,
    "cold_tolerance": 0.3
  },
  "features": ["openings","presets","fan"],
  "feature_settings": {
    "fan": {"fan_entity": "switch.living_room_fan", "fan_on_with_ac": true},
    "openings": {
      "openings": [
        {"entity_id": "binary_sensor.front_door", "timeout_open": 30, "timeout_close": 30}
      ],
      "openings_scope": "all"
    },
    "presets": {
      "presets": ["home","away"],
      "home_temp": 21,
      "away_temp": 16
    }
  }
}

4) Validation rules (summary)
- entity_id strings must match HA `domain.entity_id` pattern (e.g., `sensor.xxx`, `switch.xxx`)
- numeric ranges:
  - humidity targets: 0 <= value <= 100
  - tolerances: 1 <= value <= 20 (where applicable)
  - timeouts: 0 <= seconds <= 3600
  - temperatures: 5 <= temp <= 35 (unless explicitly allowed otherwise)
- presets referencing openings: presets that include `opening_refs` must refer to `entity_id` values present in `openings` when saved; if absent, validation error at final submission.

5) Next steps (implementation)
- Add Python typed dicts or dataclasses under `custom_components/dual_smart_thermostat/models.py` to reflect these shapes (follow-up task).
- Add contract tests that import these model types and `schemas.py` to ensure schema factories match the persisted shapes.
