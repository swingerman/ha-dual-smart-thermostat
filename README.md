# Home Assistant Dual Smart Thermostat component


The `dual_smart_thermostat` is an enhanced version of generic thermostat implemented in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/swingerman/ha-dual-smart-thermostat) ![Release](https://img.shields.io/github/v/release/swingerman/ha-dual-smart-thermostat?style=for-the-badge) [![Python tests](https://img.shields.io/github/actions/workflow/status/swingerman/ha-dual-smart-thermostat/tests.yaml?style=for-the-badge&label=tests)](https://github.com/swingerman/ha-dual-smart-thermostat/actions/workflows/tests.yaml) [![Coverage](https://img.shields.io/sonar/coverage/swingerman_ha-dual-smart-thermostat?server=https%3A%2F%2Fsonarcloud.io&style=for-the-badge)](https://sonarcloud.io/dashboard?id=swingerman_ha-dual-smart-thermostat) [![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)


[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=swingerman&repository=ha-dual-smart-thermostat&category=Integration)


## Table of contents

- [Features](#features)
- [Examples](#examples)
- [Services](#services)
- [Configuration variables](#configuration-variables)
- [Troubleshooting](#troubleshooting)
- [Installation](#installation)

## Features

| Feature | Icon | Documentation |
| :--- | :---: | :---: |
| **Heater/Cooler Mode (Heat-Cool)** | ![cooler](docs/images/sun-snowflake-custom.png) | [docs](#heatcool-mode) |
| **Heater Only Mode** | ![heating](/docs/images/fire-custom.png) | [docs](#heater-only-mode) |
| **Cooler Only Mode** | ![cool](/docs/images/snowflake-custom.png) | [docs](#cooler-only-mode) |
| **Two Stage (AUX) Heating Mode** | ![heating](/docs/images/fire-custom.png) ![heating](/docs/images/radiator-custom.png) | [docs](#two-stage-heating) |
| **Fan Only Mode** | ![fan](/docs/images/fan-custom.png) | [docs](#fan-only-mode) |
| **Fan With Cooler Mode** | ![fan](/docs/images/fan-custom.png)  ![cool](/docs/images/snowflake-custom.png) | [docs](#fan-with-cooler-mode) |
| **Fan Speed Control** | ![fan](/docs/images/fan-custom.png) | [docs](#fan-speed-control) |
| **Dry Mode (Humidity Control)** | ![humidity](docs/images/water-percent-custom.png) | [docs](#dry-mode) |
| **Heat Pump Mode** | ![heat/cool](docs/images/sun-snowflake-custom.png) | [docs](#heat-pump-one-switch-heatcool-mode) |
| **Floor Temperature Control** | ![heating-coil](docs/images/heating-coil-custom.png) ![snowflake-thermometer](docs/images/snowflake-thermometer-custom.png)  ![thermometer-alert](docs/images/thermometer-alert-custom.png) | [docs](#floor-heating-temperature-control) |
| **Window/Door Sensor Integration (Openings)** | ![window-open](docs/images/window-open-custom.png)  ![window-open](docs/images/door-open-custom.png) ![chevron-right](docs/images/chevron-right-custom.png) ![timer-cog](docs/images/timer-cog-outline-custom.png)  ![chevron-right](docs/images/chevron-right-custom.png) ![hvac-off](docs/images/hvac-off-custom.png)| [docs](#openings) |
| **Preset Modes Support** |  | [docs](#presets) |
| **HVAC Action Reason Tracking** | | [docs](#hvac-action-reason) |

## Examples

Looking for ready-to-use configurations? Check out our **[examples directory](examples/)** with:

- **[Basic Configurations](examples/basic_configurations/)** - Simple setups for heater-only, cooler-only, heat pumps, and dual-mode systems
- **[Advanced Features](examples/advanced_features/)** - Floor heating limits, two-stage heating, opening detection, and presets
- **[Integration Patterns](examples/integrations/)** - Smart scheduling and automation examples
- **[Single-Mode Thermostat Wrapper](examples/single_mode_wrapper/)** - Create Nest-like "Keep Between" functionality on single-mode thermostats

Each example includes complete YAML configurations with detailed explanations, troubleshooting tips, and best practices.

## Heat/Cool Mode

If both [`heater`](#heater) and [`cooler`](#cooler) entities configured. The thermostat can control heating and cooling and you are able to set min/max low and min/max high temperatures.
In this mode you can turn the thermostat to heat only, cooler only and back to heat/cool mode.

## Heat/Cool With Fan Mode

If the [`fan`](#fan) entity is set the thermostat can control the fan mode of the AC. The fan will turn on when the temperature is above the target temperature and the fan_hot_tolerance is not reached. If the temperature is above the target temperature and the fan_hot_tolerance is reached the AC will turn on.

[all features ⤴️](#features)

## Heater Only Mode

If only the [`heater`](#heater) entity is set the thermostat works only in heater mode.

[all features ⤴️](#features)

## Two Stage (AUX) Heating

Two stage or AUX heating can be enabled by adding the [required configuration](#two-stage-heating-example) entities: [`secondary_heater`](#secondary_heater), [`secondary heater_timeout`](#secondary_heater_timeout). If these are set the feature will enable automatically.
Optionally you can set [`secondary heater_dual_mode`](#secondar_heater_dual_mode) to `true` to turn on the secondary heater together with the primary heater.

### How Two Stage Heating Works?

If the timeout ends and the [`heater`](#heater) was on for the whole time, the thermostat switches to the [`secondary heater`](#secondary_heater). In this case, the primary heater ([`heater`](#heater)) will be turned off. This will be remembered for the day it turned on, and in the next heating cycle, the [`secondary heater`](#secondary_heater) will turn on automatically.
On the following day the primary heater will turn on again, and the second stage will again only turn on after a timeout.
If the third [`secondary heater_dual_mode`](#secondar_heater_dual_mode) is set to `true`, the secondary heater will be turned on together with the primary heater.

### Two Stage Heating Example

```yaml
secondary_heater: switch.study_secondary_heater   # <-- required
secondary_heater_timeout: 00:00:30                 # <-- required
secondary_heater_timeout: true                   # <-- optional
```

## Fan Only Mode

If the [`fan_mode`](#fan_mode) entity is set to true the thermostat works only in fan mode. The heater entity will be treated as a fan only device.

### Fan Only Mode Example

```yaml
heater: switch.study_heater
fan_mode: true
```

## Fan With Cooler Mode

If the [`ac_mode`](#ac_mode) is set to true and the [`fan`](#fan) entity is also set, the heater entity will be treated as a cooler (AC) device with an additional fan device. This will allow not only the use of a separate physical fan device but also turning on the fan mode of an AC using advanced switches.
With this setup, you can use your AC's fan mode more easily.

### Fan With Cooler Mode Example

```yaml
heater: switch.study_heater
ac_mode: true
fan: switch.study_fan
```
#### Fan Hot Tolerance

If you also set the [`fan_hot_tolerance`](#fan_hot_tolerance) the fan will turn on when the temperature is above the target temperature and the fan_hot_tolerance is not reached. If the temperature is above the target temperature and the fan_hot_tolerance is reached the AC will turn on.

##### Cooler With Auto Fan Mode Example

```yaml
heater: switch.study_heater
ac_mode: true
fan: switch.study_fan
fan_hot_tolerance: 0.5
```

#### Outside Temperature And Fan Hot Tolerance

If you set the [`fan_hot_tolerance`](#fan_hot_tolerance), [`outside_sensor`](#outside_sensor)  and the [`fan_air_outside`](#fan_air_outside) the fan will turn on only if the outside temperature is colder than the inside temperature and the fan_hot_tolerance is not reached. If the outside temperature is colder than the inside temperature and the fan_hot_tolerance is reached the AC will turn on.

## Fan Speed Control

The `dual_smart_thermostat` automatically detects and enables fan speed control when you configure a `fan` entity that supports speed capabilities. This allows you to control your HVAC fan speeds (low, medium, high, auto) directly from the thermostat interface, just like built-in thermostats.

### Automatic Detection

The thermostat automatically detects whether your fan entity supports speed control based on its capabilities:

- **Native fan entities** (`fan` domain) with `preset_mode` or `percentage` attributes → Fan speed control enabled automatically
- **Switch entities** (`switch` domain) → Traditional on/off control (backward compatible)

**No configuration changes required** - the thermostat detects capabilities at runtime.

### Fan Speed Control Example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.study_heater
    fan: fan.hvac_fan  # Native fan entity - speeds automatically detected
    target_sensor: sensor.study_temperature
```

With this configuration, you'll see fan speed controls in the thermostat UI allowing you to select speeds like "auto", "low", "medium", "high" depending on what your fan entity supports.

### Backward Compatibility

Existing configurations using switch entities continue working unchanged:

```yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.study_heater
    fan: switch.fan_relay  # Switch entity - on/off only (no speed control)
    target_sensor: sensor.study_temperature
```

### Integration with Existing Features

Fan speed control works seamlessly with all existing fan-related features:

- **FAN_ONLY Mode**: Fan runs at selected speed in fan-only mode
- **Fan with AC** (`fan_on_with_ac`): Fan runs at selected speed when AC is active
- **Fan Hot Tolerance**: Fan activates at selected speed when temperature tolerance is exceeded
- **Heat Pump Mode**: Fan speed applies to both heating and cooling operations

Your fan speed selection persists across heating/cooling cycles and restarts.

### Upgrading Switch-Based Fans

If you currently use a `switch` entity for your fan but want speed control, you can create a template fan entity that wraps your switch. Here are several examples:

#### Template Fan with Input Select (Preset Modes)

This example uses an input_select helper to provide speed presets:

```yaml
# Helper for fan speed selection
input_select:
  hvac_fan_speed:
    name: HVAC Fan Speed
    options:
      - "auto"
      - "low"
      - "medium"
      - "high"
    initial: "auto"

# Template fan wrapping switch + speed control
fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('switch.fan_relay', 'on') }}"
        preset_mode_template: "{{ states('input_select.hvac_fan_speed') }}"
        preset_modes:
          - "auto"
          - "low"
          - "medium"
          - "high"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.fan_relay
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.fan_relay
        set_preset_mode:
          service: input_select.select_option
          target:
            entity_id: input_select.hvac_fan_speed
          data:
            option: "{{ preset_mode }}"

# Use in thermostat
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.study_heater
    fan: fan.hvac_fan  # Uses template fan with speed control
    target_sensor: sensor.study_temperature
```

#### Template Fan with Percentage Control

This example uses an input_number helper for percentage-based speed control:

```yaml
# Helper for fan percentage
input_number:
  hvac_fan_speed:
    name: HVAC Fan Speed
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"

# Template fan with percentage support
fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('switch.fan_relay', 'on') }}"
        percentage_template: "{{ states('input_number.hvac_fan_speed') | int }}"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.fan_relay
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.fan_relay
        set_percentage:
          - service: input_number.set_value
            target:
              entity_id: input_number.hvac_fan_speed
            data:
              value: "{{ percentage }}"

# Use in thermostat
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.study_heater
    fan: fan.hvac_fan  # Percentage-based speed control
    target_sensor: sensor.study_temperature
```

#### Template Fan for IR/RF Controlled Fans

For fans controlled via Broadlink, IR blaster, or RF remote:

```yaml
# Helpers to track state
input_boolean:
  fan_state:
    name: Fan State

input_select:
  hvac_fan_speed:
    name: HVAC Fan Speed
    options:
      - "low"
      - "medium"
      - "high"
    initial: "low"

# Template fan for IR/RF control
fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('input_boolean.fan_state', 'on') }}"
        preset_mode_template: "{{ states('input_select.hvac_fan_speed') }}"
        preset_modes:
          - "low"
          - "medium"
          - "high"
        turn_on:
          - service: input_boolean.turn_on
            target:
              entity_id: input_boolean.fan_state
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_on"
        turn_off:
          - service: input_boolean.turn_off
            target:
              entity_id: input_boolean.fan_state
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_off"
        set_preset_mode:
          - service: input_select.select_option
            target:
              entity_id: input_select.hvac_fan_speed
            data:
              option: "{{ preset_mode }}"
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_{{ preset_mode }}"

# Use in thermostat
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.study_heater
    fan: fan.hvac_fan  # IR/RF controlled with speed support
    target_sensor: sensor.study_temperature
```

**Benefits of Template Fans:**
- Use existing switch hardware without buying new devices
- Add speed control functionality to any fan
- Automatic detection by the thermostat
- Full UI integration with speed controls
- Works with IR/RF remotes, relays, or any controllable device

**Reference:** [Home Assistant Template Fan Documentation](https://www.home-assistant.io/integrations/fan.template/)

[all features ⤴️](#features)

## AC With Fan Switch Support

Some AC systems have independent fan controls to cycle the house air for filtering or humidity control, without using the heating or cooling elements. Central AC systems require the thermostat to turn on both the AC wire ("Y" wire) and the air-handler/fan wire ("G" wire) to activate the AC

This feature lets you do just that.

To use this feature, you need to set the [`heater`](#heater) entity, the [`ac_mode`](#ac_mode), and the [`fan)`](#fan) entity and the [`fan_on_with_ac`](#fan_on_with_ac) to `true`.


### example
```yaml
heater: switch.study_heater
ac_mode: true
fan: switch.study_fan
fan_on_with_ac: true
```

## Cooler Only Mode

If only the [`cooler`](#cooler) entity is set, the thermostat works only in cooling mode.

[all features ⤴️](#features)

## Dry mode

If the [`dryer`](#dryer) entity is set, the thermostat can switch to dry mode. The dryer will turn on when the humidity is above the target humidity and the [`moist_tolerance`](#moist_tolerance) is not reached. If the humidity is above the target humidity and the [`moist_tolerance`](#moist_tolerance) is reached, the dryer will stop.


### Dry Mode Example with cooler

```yaml
heater: switch.study_heater
target_sensor: sensor.study_temperature
ac_mode: true
dryer: switch.study_dryer
humidity_sensor: sensor.study_humidity
moist_tolerance: 5
dry_tolerance: 5
```

### Dryer example in dual mode

```yaml
heater: switch.study_heater
cooler: switch.study_cooler
target_sensor: sensor.study_temperature
dryer: switch.study_dryer
humidity_sensor: sensor.study_humidity
moist_tolerance: 5
dry_tolerance: 5
```

### Heat Pump (one switch heat/cool) mode

This setup allows you to use a single switch for both heating and cooling. To enable this mode, you define only a single switch for the heater and set your heat pump's current state (heating or cooling) as for the [`heat_pump_cooling`](#heat_pump_cooling) attribute. This must be an entity ID of a sensor with a state of `on` or `off`.

The entity can be a Boolean input for manual control or an entity provided by the heat pump.

```yaml
heater: switch.study_heat_pump
target_sensor: sensor.study_temperature
heat_pump_cooling: sensor.study_heat_pump_state
```

#### Heat Pump HVAC Modes

##### Heat-Cool Mode

```yaml
heater: switch.study_heat_pump
target_sensor: sensor.study_temperature
heat_pump_cooling: sensor.study_heat_pump_state
heat_cool_mode: true
```

**heating** _(heat_pump_cooling: false)_:
- heat/cool
- heat
- off

**cooling** _(heat_pump_cooling: true)_:
- heat/cool
- cool
- off

##### Single mode

```yaml
heater: switch.study_heat_pump
target_sensor: sensor.study_temperature
heat_pump_cooling: sensor.study_heat_pump_state
heat_cool_mode: false # <-- or not set
```

**heating** _(heat_pump_cooling: false)_:
- heat
- off

**cooling** _(heat_pump_cooling: true)_:
- cool
- off


## Openings

The `dual_smart_thermostat` can turn off heating or cooling when a window or door is opened and turn it back on when the door or window is closed, saving energy.
The `openings` configuration variable accepts a list of opening entities and opening objects.

### Opening entities and objects

An opening entity is a sensor that can be in two states: `on` or `off`. If the state is `on`, the opening is considered open; if the state is `off`, the opening is considered closed.
The opening object can contain a `timeout` and a `closing_timeout` property that defines the time for which the opening is still considered closed or open, even if the state is `on` or `off`. This is useful if you want to ignore windows that are only open or closed for a short time.

### Openings Scope

The `openings_scope` configuration variable defines the scope of the openings. If set to `all` or not defined, any open openings will turn off the current HVAC device, and it will be in the idle state. If set, only devices that are operating in the defined HVAC modes will be turned off. For example, if set to `heat`, only the heater will be turned off if any of the openings are open.

### Openings Scope Configuration

```yaml
openings_scope: [heat, cool, heat_cool, fan_only, dry]
```

```yaml
openings_scope:
  - heat
  - cool
```

## Openings Configuration

```yaml
# Example configuration.yaml entry
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    cooler: switch.study_cooler
    openings:
      - binary_sensor.window1
      - entity_id: binary_sensor.window2
        timeout: 00:00:30
      - entity_id: binary_sensor.window3
        timeout: 00:00:30
        closing_timeout: 00:00:15
    openings_scope: [heat, cool]
    target_sensor: sensor.study_temperature
```

[all features ⤴️](#features)

## Floor heating temperature control

The `dual_smart_thermostat` can control the floor heating temperature. The thermostat can turn off if the floor heating reaches the maximum allowed temperature you define in order to protect the floor from overheating and damage.
These limits also can be set in presets.

### Maximum floor temperature

The `dual_smart_thermostat` can turn off if the floor heating reaches the maximum allowed temperature you define in order to protect the floor from overheating and damage.
There is a default value of 28 degrees Celsius as per inustry recommendations.
To enable this protection you need to set two variables:

```yaml
floor_sensor: sensor.floor_temp
max_floor_temp: 28
```

#### Set in presets

You can also set the `max_floor_temp` in the presets configuration. This will allow you to set different maximum floor temperatures for different presets.

```yaml
floor_sensor: sensor.floor_temp
max_floor_temp: 28
preset_name:
  max_floor_temp: 25
```

### Minimum floor temperature

The `dual_smart_thermostat` can turn on if the floor temperature reaches the minimum required temperature you define in order to protect the floor from freezing or to keep it on a comfortable temperature.

```yaml
floor_sensor: sensor.floor_temp
min_floor_temp: 5
```

#### Set in presets

You can also set the `min_floor_temp` in the presets configuration. This will allow you to set different minimum floor temperatures for different presets.

```yaml
floor_sensor: sensor.floor_temp
min_floor_temp: 5
preset_name:
  min_floor_temp: 8
```

### Floor Temperature Control Configuration

```yaml
# Example configuration.yaml entry
climate:
  - platform: dual_smart_thermostat
    name: Study
    unique_id: study
    heater: switch.study_heater
    cooler: switch.study_cooler
    target_sensor: sensor.study_temperature
    floor_sensor: sensor.floor_temp
    max_floor_temp: 28
    min_floor_temp: 5
```

[all features ⤴️](#features)

## Presets

Currently supported presets are:

- none
- [home](#home)
- [away](#away)
- [eco](#eco)
- [sleep](#sleep)
- [comfort](#comfort)
- [anti freeze](#anti_freeze)
- [activity](#activity)
- [boost](#boost)

To set presets you need to add entries for them in the configuration file like this:

You have 6 options here:

1. Set the `temperature` for heat, cool or fan-only mode
2. Set the `target_temp_low` and `target_temp_high` for heat_cool mode. If `temperature` is not set but `target_temp_low` and `target_temp_high` are set, the `temperature` will be picked based on hvac mode. For heat mode it will be `target_temp_low` and for cool, fan_only mode it will be `target_temp_high`
3. Set the `humidity` for dry mode
4. Set `min_floor_temp` for floor heating temperature control
5. Set `max_floor_temp` for floor heating temperature control
6. Set all above

### Presets Configuration

```yaml
preset_name:
  temperature: 13
  humidity: 50 # <-- only if dry mode configured
  target_temp_low: 12
  target_temp_high: 14
  min_floor_temp: 5
  max_floor_temp: 28
```

## HVAC Action Reason

State attribute: `hvac_action_reason`

The `dual_smart_thermostat` will set the `hvac_action` attribute to `heating`, `cooling`, `idle` or `off` based on the current state of the thermostat. The `hvac_action` attribute is used to indicate the current action of the thermostat. The `dual_smart_thermostat` will also set the `hvac_action_reason` attribute based on the current state of the thermostat. The `hvac_action_reason` attribute is used to indicate the reason for the current action of the thermostat.

### HVAC Action Reason values

The `hvac_action_reason` attribute is grouped by [internal](#hvac-action-reason-internal-values) and [external](#hvac-action-reason-external-values) values.
The internal values can be set by the component only and the external values can be set by the user or automations.

#### HVAC Action Reason Internal values

| Value | Description |
|-------|-------------|
| `none` | No action reason |
| `target_temp_not_reached` | The target temperature has not been reached |
| `target_temp_not_reached_with_fan` | The target temperature has not been reached trying it with a fan |
| `target_temp_reached` | The target temperature has been reached |
| `target_humidity_reached` | The target humidity has been reached |
| `target_humidity_not_reached` | The target humidity has not been reached |
| `misconfiguration` | The thermostat is misconfigured |
| `opening` | The thermostat is idle because an opening is open |
| `limit` | The thermostat is idle because the floor temperature is at the limit |
| `overheat` | The thermostat is idle because the floor temperature is too high |
| `temperature_sensor_stalled` | The thermostat is idle because the temperature sensor is not provided data for the defined time that could indicate a malfunctioning sensor |
| `humidity_sensor_sstalled` | The thermostat is idle because the temperature sensor is not provided data for the defined time that could indicate a malfunctioning sensor |

#### HVAC Action Reason External values

| Value | Description |
|-------|-------------|
| `none` | No action reason |
| `presence`| the last HVAc action was triggered by presence |
| `schedule` | the last HVAc action was triggered by schedule |
| `emergency` | the last HVAc action was triggered by emergency |
| `malfunction` | the last HVAc action was triggered by malfunction |

[all features ⤴️](#features)

## Services

### Set HVAC Action Reason

`dial_smart_thermostat.set_hvac_action_reason` is exposed for automations to set the `hvac_action_reason` attribute. The service accepts the following parameters:

| Parameter | Description | Type | Required |
|-----------|-------------|------|----------|
| entity_id | The entity id of the thermostat | string | yes |
| hvac_action_reason | The reason for the current action of the thermostat | [HVACActionReasonExternal](#hvac-action-reason-external-values) | yes |

## Configuration variables

### name

  _(required) (string)_ Name of thermostat

  _default: Dual Smart_

### unique_id

  _(optional) (string)_ the unique id for the thermostat. It allows you to customize it in the UI and to assign the component to an area.

  _default: none

### heater

  _(required) (string)_ "`entity_id` for heater switch, must be a toggle device. Becomes air conditioning switch when `ac_mode` is set to `true`"

### secondary_heater

  _(optional, **required for two stage heating**) (string)_ "`entity_id` for secondary heater switch, must be a toggle device.

### secondary_heater_timeout

  _(optional, **required for two stage heating**) (time, integer)_  Set a minimum amount of time that the switch specified in the _heater_ option must be in its ON state before secondary heater devices needs to be turned on.

### secondary_heater_dual_mode

  _(optional, (bool)_  If set true the secondary (aux) heater will be turned on together with the primary heater.

### cooler

  _(optional) (string)_ "`entity_id` for cooler switch, must be a toggle device."

### fan_mode

  _(optional) (bool)_ If set to `true` the heater entity will be treated as a fan only device.

### fan

  _(optional) (string)_ "`entity_id` for fan switch, must be a toggle device."

### fan_hot_tolerance

  _(optional) (float)_ Temperature range above `hot_tolerance` where the fan is used instead of the AC. This creates an intermediate zone where the fan attempts to cool before engaging the AC.

  **Example:** With target temperature 25°C, `hot_tolerance` 1°C, and `fan_hot_tolerance` 0.5°C:
  - At 26°C (target + hot_tolerance): Fan turns on
  - At 26.5°C (target + hot_tolerance + fan_hot_tolerance): AC turns on (fan turns off)

  This feature helps save energy by using the fan for minor temperature increases before engaging the more power-intensive AC.

  _default: 0.5_

  _requires: `fan`_

### fan_hot_tolerance_toggle

  _(optional) (string)_ `entity_id` for an `input_boolean` or `binary_sensor` that dynamically enables/disables the `fan_hot_tolerance` feature.

  - When the toggle entity is `on` (or not configured): The fan_hot_tolerance feature is active
  - When the toggle entity is `off`: The AC is used immediately when `hot_tolerance` is exceeded (bypasses fan zone)

  Useful for automations that disable fan-first behavior during extreme heat, high humidity, or other conditions where immediate AC is preferred.

  _default: Feature enabled (behaves as if toggle is `on`)_

  _requires: `fan`_

### fan_on_with_ac

  _(optional) (boolean)_ If set to `true` the fan will be turned on together with the AC. This is useful for central AC systems that require the fan to be turned on together with the AC.

  _requires: `fan`_

### fan_air_outside

  _(optional) (boolean)_ "If set to `true` the fan will be turned on only if the outside temperature is colder than the inside temperature and the `fan_hot_tolerance` is not reached. If the outside temperature is colder than the inside temperature and the `fan_hot_tolerance` is reached the AC will turn on."

  _requires: `fan` , `sensor_outside`_


### dryer

  _(optional) (string)_ "`entity_id` for dryer switch, must be a toggle device."

### moist_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the humidity read by the sensor specified in the _humidity_sensor_ option and the target humidity that must change prior to being switched on. For example, if the target humidity is 50 and the tolerance is 5 the dryer will start when the sensor equals or goes below 45.

  _requires: `dryer`, `humidity_sensor`_

### dry_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the humidity read by the sensor specified in the _humidity_sensor_ option and the target humidity that must change prior to being switched off. For example, if the target humidity is 50 and the tolerance is 5 the dryer will stop when the sensor equals or goes above 55.

  _requires: `dryer`, `humidity_sensor`_

### humidity_sensor

  _(optional) (string)_ "`entity_id` for a humidity sensor, humidity_sensor.state must be humidity."

### target_sensor

  _(required) (string)_  "`entity_id` for a temperature sensor, target_sensor.state must be temperature."

### sensor_stale_duration

  _(optional) (timedelta)_  Set a delay for the target sensor to be considered not stalled. If the sensor is not available for the specified time or doesn't get updated the thermostat will be turned off.

  _requires: `target_sensor` and/or `huidity_sensor`_

### floor_sensor

  _(optional) (string)_  "`entity_id` for the floor temperature sensor, floor_sensor.state must be temperature."

### outside_sensor

  _(optional) (string)_  "`entity_id` for the outside temperature sensor, oustide_sensor.state must be temperature."

### openings

  _(optional) (list)_  "list of opening `entity_id`'s and/or objects for detecting open windows or doors that will idle the thermostat until any of them are open. Note: if min_floor_temp is set and the floor temperature is below the minimum temperature, the thermostat will not idle even if any of the openings are open."

  `entity_id: <value>` The entity id of the opening bstate sensor (string)</br>

  `timeout: <value>` The time for which the opening is still considered closed even if the state of the sensor is `on` (timedelta)</br>

  `closing_timeout: <value>` The time for which the opening is still considered open even if the state of the sensor is `off` (timedelta)</br>

### openings_scope

  _(optional) (array[string])_  "The scope of the openings. If set to [`all`] or not defined, any open openings will turn off the current hvac device and it will be in the idle state. If set, only devices that operating in the defined HVAC modes will be turned off. For example, if set to `heat` only the heater will be turned off if any of the openings are open."

  _default: `all`_

  options:
    - `all`
    - `heat`
    - `cool`
    - `heat_cool`
    - `fan_only`

### heat_pump_cooling

  _(optional) (string)_  "`entity_id` for the heat pump cooling state sensor, heat_pump_cooling.state must be `on` or `off`."
  enables [heat pump mode](#heat-pump-one-switch-heatcool-mode)

### min_temp

  _(optional) (float)_

  _default: 7_

### max_temp

  _(optional) (float)_

  _default: 35_

### max_floor_temp

  _(optional) (float)_

  _default: 28_

### min_floor_temp

  _(optional) (float)_

### target_temp

  _(optional) (float)_ Set initial target temperature. If this variable is not set, it will retain the target temperature set before restart if available.

### target_temp_low

  _(optional) (float)_ Set initial target low temperature. If this variable is not set, it will retain the target low temperature set before restart if available.

### target_temp_high

  _(optional) (float)_ Set initial target high temperature. If this variable is not set, it will retain the target high temperature set before restart if available.

### ac_mode

  _(optional) (boolean)_ Set the switch specified in the `heater` option to be treated as a cooling device instead of a heating device. This parameter will be ignored if `cooler` entity is defined.

  _default: false_

### heat_cool_mode

  _(optional) (boolean)_ If variable `target_temp_low` and `target_temp_high` are not set, this parameter must be set to _true_ to enable the `heat_cool` mode.

  _default: false_

### min_cycle_duration

  _(optional) (time, integer)_  Set a minimum amount of time that the switch specified in the _heater_  and/or _cooler_ option must be in its current state prior to being switched either off or on. This option will be ignored if the `keep_alive` option is set.

### cold_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the _target_sensor_ option and the target temperature that must change prior to being switched on. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5.

  _default: 0.3_

### hot_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the _target_sensor_ option and the target temperature that must change prior to being switched off. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will stop when the sensor equals or goes above 25.5.

  _default: 0.3_

### heat_tolerance

  _(optional) (float)_ **[Dual-mode systems only]** Set a mode-specific tolerance for heating operations. Only available for systems that support both heating and cooling (`heater_cooler` or `heat_pump` system types).

  When configured, this tolerance is used instead of `cold_tolerance` when the system is actively heating. This allows you to have different tolerance values for heating vs cooling operations.

  **Example use case:** Tight temperature control during heating (±0.3°C) while allowing looser control during cooling (±2.0°C) for energy savings.

  **Priority:** If set, `heat_tolerance` takes priority over `cold_tolerance` for heating operations.

  **Availability:**
  - ✅ Available: `heater_cooler`, `heat_pump` (dual-mode systems)
  - ❌ Not available: `simple_heater`, `ac_only` (single-mode systems use legacy tolerances)

  _default: Uses `cold_tolerance` if not set_

### cool_tolerance

  _(optional) (float)_ **[Dual-mode systems only]** Set a mode-specific tolerance for cooling operations. Only available for systems that support both heating and cooling (`heater_cooler` or `heat_pump` system types).

  When configured, this tolerance is used instead of `hot_tolerance` when the system is actively cooling. This allows you to have different tolerance values for heating vs cooling operations.

  **Example use case:** Allow wider temperature swings during cooling to reduce energy consumption while maintaining comfort.

  **Priority:** If set, `cool_tolerance` takes priority over `hot_tolerance` for cooling operations.

  **Availability:**
  - ✅ Available: `heater_cooler`, `heat_pump` (dual-mode systems)
  - ❌ Not available: `simple_heater`, `ac_only` (single-mode systems use legacy tolerances)

  _default: Uses `hot_tolerance` if not set_

### keep_alive

  _(optional) (time, integer)_ Set a keep-alive interval. If set, the switch specified in the _heater_ and/or _cooler_ option will be triggered every time the interval elapses. Use with heaters and A/C units that shut off if they don't receive a signal from their remote for a while. Use also with switches that might lose state. The keep-alive call is done with the current valid climate integration state (either on or off). When `keep_alive` is set the `min_cycle_duration` option will be ignored.

  _default: 300 seconds (5 minutes)_

  **Note:** Some AC units (like certain Hitachi models) beep with each command they receive. If your AC beeps excessively every few minutes, the keep-alive feature may be sending redundant commands. You can disable keep-alive by setting it to `0`:

  ```yaml
  keep_alive: 0  # Disables keep-alive to prevent beeping
  ```

### initial_hvac_mode

  _(optional) (string)_ Set the initial HVAC mode. Valid values are `off`, `heat`, `cool` or `heat_cool`. Value has to be double quoted. If this parameter is not set, it is preferable to set a _keep_alive_ value. This is helpful to align any discrepancies between _dual_smart_thermostat_ _heater_ and _cooler_ state.

  **NOTE! If this is set, the saved state will not be restored after HA restarts.**

### away

  _(optional) (list)_ Set the temperatures used by `preset_mode: away`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### eco

  _(optional) (list)_ Set the temperature used by `preset_mode: eco`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### home

  _(optional) (list)_ Set the temperature used by `preset_mode: home`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### comfort

  _(optional) (list)_ Set the temperature used by `preset_mode: comfort`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### sleep

  _(optional) (list)_ Set the temperature used by `preset_mode: sleep`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### anti_freeze

  _(optional) (list)_ Set the temperature used by `preset_mode: Anti Freeze`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### activity

  _(optional) (list)_ Set the temperature used by `preset_mode: Activity`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

### boost

  _(optional) (list)_ Set the temperature used by `preset_mode: Boost`. If this is not specified, the preset mode feature will not be available.
  This preset mode only works in `heat` or `cool` mode because boosting temperatures on heat_cools
  mode will require setting `target_temp_low` higher than `target_temp_high` and vice versa.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>

### precision

  _(optional) (float)_ The desired precision for this device. Can be used to match your actual thermostat's precision. Supported values are `0.1`, `0.5` and `1.0`.

  _default: `0.5` for Celsius and `1.0` for Fahrenheit._

### target_temp_step

  _(optional) (float)_ The desired step size for setting the target temperature. Supported values are `0.1`, `0.5` and `1.0`.

  _default: Value used for `precision`_

## Troubleshooting

### AC/Heater beeping excessively

**Problem:** Your air conditioner or heater beeps every few minutes (typically every 5 minutes) even when no temperature changes occur.

**Root Cause:** The `keep_alive` feature defaults to 300 seconds (5 minutes) and sends periodic commands to keep devices synchronized. Some HVAC units (like certain Hitachi AC models) beep audibly with each command they receive, including these keep-alive commands.

**Solution:** Disable the keep-alive feature by setting it to `0` in your configuration:

```yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.my_heater
    target_sensor: sensor.my_temperature
    keep_alive: 0  # Disables keep-alive to prevent beeping
```

**When to use keep_alive:** The keep-alive feature is useful for:
- HVAC units that turn off automatically if they don't receive commands regularly
- Switches that might lose state over time
- Maintaining synchronization between the thermostat and physical device

If your HVAC device doesn't have these issues, you can safely disable keep-alive.

**Related:** [GitHub Issue #461](https://github.com/swingerman/ha-dual-smart-thermostat/issues/461)

## Installation

Installation is via the [Home Assistant Community Store (HACS)](https://hacs.xyz/), which is the best place to get third-party integrations for Home Assistant. Once you have HACS set up, simply [search the `Integrations` section](https://hacs.xyz/docs/basic/getting_started) for Dual Smart Thermostat.

## Heater Mode Example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    target_sensor: sensor.study_temperature
    initial_hvac_mode: "heat"
```

## Two Stage Heating Mode Example

For two stage heating both the `heater` and `secondary_heater` must be defined. The `secondary_heater` will be turned on only if the `heater` is on for the amount of time defined in `secondary_heater_timeout`.

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater

    secondary_heater: switch.study_secondary_heater # <-requred
    secondary_heater_timeout: 00:00:30 # <-requred

    target_sensor: sensor.study_temperature
    initial_hvac_mode: "heat"
```

## Cooler Mode Example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_cooler
    ac_mode: true # <-important
    target_sensor: sensor.study_temperature
    initial_hvac_mode: "cool"
```

## Floor Temperature Caps Example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    target_sensor: sensor.study_temperature
    initial_hvac_mode: "heat"
    floor_sensor: sensor.floor_temp # <-required
    max_floor_temp: 28 # <-required
    min_floor_temp: 20 # <-required
```

## DUAL Heat-Cool Mode Example

This mode is used when you want (and can) control both the heater and the cooler. In this mode the `target_temp_low` and `target_temp_high` must be set.
In this mode you can switch between heating and cooling by setting the `hvac_mode` to `heat` or `cool` or `heat_cool`.

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater # <-required
    cooler: switch.study_cooler # <-required
    target_sensor: sensor.study_temperature
    heat_cool_mode: true # <-required
    initial_hvac_mode: "heat_cool"
```

## OPENINGS Example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    cooler: switch.study_cooler
    target_sensor: sensor.study_temperature
    openings: # <-required
      - binary_sensor.window1
      - binary_sensor.window2
      - entity_id: binary_sensor.window3
        timeout: 00:00:30 # <-optional
```

## Tolerances

The `dual_smart_thermostat` supports multiple tolerance configurations to prevent the heater or cooler from switching on and off too frequently.

### Legacy Tolerances (All System Types)

The basic tolerance variables `cold_tolerance` and `hot_tolerance` work for all system types. These variables are used to prevent the heater or cooler from switching on and off too frequently. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5. The heater will stop when the sensor equals or goes above 25.5. This prevents the heater from switching on and off too frequently when the temperature is close to the target temperature.

If the thermostat is set to heat_cool mode the tolerance will work in the same way for both the heater and the cooler.

### Mode-Specific Tolerances (Dual-Mode Systems Only)

For systems that support both heating and cooling (`heater_cooler` or `heat_pump` system types), you can optionally configure separate tolerances for heating vs cooling operations using `heat_tolerance` and `cool_tolerance`.

**Tolerance Selection Priority:**
1. **Mode-specific tolerance** (if configured): `heat_tolerance` for heating, `cool_tolerance` for cooling
2. **Legacy tolerance**: `cold_tolerance` / `hot_tolerance`
3. **Default**: 0.3°C/°F

**Example:** Tight heating control with loose cooling for energy savings:

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Living Room
    heater: switch.heater
    cooler: switch.ac_unit
    target_sensor: sensor.temperature
    heat_tolerance: 0.3   # Tight control during heating (±0.3°C)
    cool_tolerance: 2.0   # Loose control during cooling (±2.0°C) - saves energy
```

**System Type Availability:**
- ✅ `heater_cooler` - Full support for heat_tolerance and cool_tolerance
- ✅ `heat_pump` - Full support for heat_tolerance and cool_tolerance
- ❌ `simple_heater` - Use cold_tolerance only (heating-only system)
- ❌ `ac_only` - Use hot_tolerance only (cooling-only system)

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    cooler: switch.study_cooler
    target_sensor: sensor.study_temperature
    cold_tolerance: 0.3
    hot_tolerance: 0
```

## Full configuration example

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    cooler: switch.study_cooler
    secondary_heater: switch.study_secondary_heater
    secondary_heater_timeout: 00:00:30
    target_sensor: sensor.study_temperature
    floor_sensor: sensor.floor_temp
    max_floor_temp: 28
    openings:
      - binary_sensor.window1
      - binary_sensor.window2
      - entity_id: binary_sensor.window3
        timeout: 00:00:30
    min_temp: 10
    max_temp: 28
    ac_mode: false
    target_temp: 17
    target_temp_high: 26
    target_temp_low: 23
    cold_tolerance: 0.3
    hot_tolerance: 0
    min_cycle_duration:
      minutes: 5
    keep_alive:
      minutes: 3
    initial_hvac_mode: "off" # hvac mode will reset to this value after restart
    away: # this preset will be available for all hvac modes
      temperature: 13
      target_temp_low: 12
      target_temp_high: 14
    home: # this preset will be available only for heat or cool hvac mode
      temperature: 21
    precision: 0.1
    target_temp_step: 0.5
```

### Donate

I am happy to help the Home Assistant community but I do it in my free time at the cost of spending less time with my family. Feel free to motivate me and appreciate my sacrifice by donating:

[![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)
[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/swingerman)

### Development

The Dual Smart Thermostat supports two development workflows: **Docker-based** and **VS Code DevContainer**. Both approaches provide consistent, isolated development environments with Home Assistant 2025.1.0+.

📚 **[Comprehensive Docker Development Guide](README-DOCKER.md)** - Complete documentation for Docker-based development, testing with multiple HA versions, and CI/CD integration.

📋 **[Development Guidelines](CLAUDE.md)** - Detailed coding standards, architecture overview, and contribution requirements.

#### Quick Start

**Option 1: Docker Workflow (Recommended for CI/CD and version testing)**

```bash
# Build development environment with HA 2025.1.0
docker-compose build dev

# Run all tests
./scripts/docker-test

# Run linting checks
./scripts/docker-lint

# Open interactive shell
./scripts/docker-shell

# Test with different HA version
HA_VERSION=2025.2.0 docker-compose build dev
```

**Option 2: VS Code DevContainer (Recommended for interactive development)**

Open the project in VS Code and select "Reopen in Container" when prompted. The DevContainer will automatically set up the development environment.

#### Testing

**Run all tests:**
```bash
pytest
# or with Docker:
./scripts/docker-test
```

**Run specific test file:**
```bash
pytest tests/test_heater_mode.py
# or with Docker:
./scripts/docker-test tests/test_heater_mode.py
```

**Run specific test function:**
```bash
pytest tests/test_heater_mode.py::test_heater_mode_on
```

**Run tests with pattern matching:**
```bash
pytest -k "heater"
```

**Run with verbose output and debug logging:**
```bash
pytest -v --log-cli-level=DEBUG
```

**Run with coverage report:**
```bash
pytest --cov --cov-report=html
```

**Run config flow tests only:**
```bash
pytest tests/config_flow/
```

#### Code Quality & Linting

**All code must pass linting checks before committing.** The following tools are required:

```bash
# Check all linting rules
isort . --check-only --diff    # Import sorting
black --check .                 # Code formatting
flake8 .                        # Style/linting
codespell                       # Spell checking
ruff check .                    # Modern Python linter

# Auto-fix issues
isort .                         # Fix imports
black .                         # Fix formatting
ruff check . --fix              # Fix ruff issues

# Or use Docker to run all checks
./scripts/docker-lint           # Check all
./scripts/docker-lint --fix     # Auto-fix
```

**Pre-commit hooks** (automatically runs linting on commit):
```bash
pre-commit install              # Install hooks
pre-commit run --all-files      # Run manually
```

#### Testing with Different Home Assistant Versions

The Docker workflow makes it easy to test with different HA versions:

```bash
# Test with HA 2025.1.0 (default)
docker-compose build dev
./scripts/docker-test

# Test with HA 2025.2.0
HA_VERSION=2025.2.0 docker-compose build dev
./scripts/docker-test

# Test with latest HA
HA_VERSION=latest docker-compose build dev
./scripts/docker-test
```

#### Development Resources

- **[README-DOCKER.md](README-DOCKER.md)** - Docker workflow, troubleshooting, and advanced usage
- **[CLAUDE.md](CLAUDE.md)** - Architecture, development rules, and testing strategy
- **[Examples Directory](examples/)** - Ready-to-use configuration examples
- **[GitHub Issues](https://github.com/swingerman/ha-dual-smart-thermostat/issues)** - Bug reports and feature requests
- **[Home Assistant Developer Docs](https://developers.home-assistant.io/)** - Official HA development documentation

#### Contributing

Before submitting a pull request:

1. ✅ All tests pass: `pytest` or `./scripts/docker-test`
2. ✅ All linting passes: `./scripts/docker-lint` or run linters individually
3. ✅ Add tests for new features
4. ✅ Update documentation if needed
5. ✅ Follow the patterns in [CLAUDE.md](CLAUDE.md)

**Configuration Flow Changes:** If you add or modify configuration options, you **must** integrate them into the appropriate configuration flows (config, reconfigure, or options). See [CLAUDE.md Configuration Flow Integration](CLAUDE.md#configuration-flow-integration) for detailed requirements.
