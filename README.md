# Home Assistant Dual Smart Thermostat component

The `dual_smart_thermostat` is an enhanced version of generic thermostat implemented in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/swingerman/ha-dual-smart-thermostat) ![Release](https://img.shields.io/github/v/release/swingerman/ha-dual-smart-thermostat?style=for-the-badge) [![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=swingerman&repository=ha-dual-smart-thermostat&category=Integration)


## Table of contents

- [Features](#features)
- [Services](#services)
- [Configuration variables](#configuration-variables)
- [Installation](#installation)

## Features

|  |  | |
| :--- | :---: | :---: |
| **Heater/Cooler Mode** | ![cooler](docs/images/sun-snowflake-custom.png) | [docs](#heatcool-mode) |
| **Heater Only Mode** | ![heating](/docs/images/fire-custom.png) | [docs](#heater-only-mode) |
| **Two Stage (AUX) Heating Mode** | ![heating](/docs/images/fire-custom.png) ![heating](/docs/images/radiator-custom.png) | [docs](#two-stage-heating) |
| **Fan Only mode** | ![fan](/docs/images/fan-custom.png) | [docs](#fan-only-mode) |
| **Fan With Cooler mode** | ![fan](/docs/images/fan-custom.png)  ![cool](/docs/images/snowflake-custom.png) | [docs](#fan-with-cooler-mode) |
| **Cooler Only mode** | ![cool](/docs/images/snowflake-custom.png) | [docs](#cooler-only-mode) |
| **Dry mode** | ![humidity](docs/images/water-percent-custom.png) | [docs](#dry-mode) |
| **Heat Pump mode** | ![haet/cool](docs/images/sun-snowflake-custom.png) | [docs](#heat-pump-one-switch-heatcool-mode) |
| **Floor Temperature Control** | ![heating-coil](docs/images/heating-coil-custom.png) ![snowflake-thermometer](docs/images/snowflake-thermometer-custom.png)  ![thermometer-alert](docs/images/thermometer-alert-custom.png) | [docs](#floor-heating-temperature-control) |
| **Window/Door sensor integration** | ![window-open](docs/images/window-open-custom.png)  ![window-open](docs/images/door-open-custom.png) ![chevron-right](docs/images/chevron-right-custom.png) ![timer-cog](docs/images/timer-cog-outline-custom.png)  ![chevron-right](docs/images/chevron-right-custom.png) ![hvac-off](docs/images/hvac-off-custom.png)| [docs](#openings) |
| **Presets** |  | [docs](#presets) |
| **HVAC Action Reason** | | [docs](#hvac-action-reason) |

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
The opening object can contain a timeout property that defines the time in seconds after which the opening is considered open, even if the state is still `on`. This is useful if you want to ignore windows that are only open for a short time.

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
      - binary_sensor.window2
      - entity_id: binary_sensor.window3
        timeout: 00:00:30
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

  _(optional) (float)_ Set a maximum amount of difference between the temperature read by the sensor specified in the _target_sensor_ option and the target temperature and the _hot_tolerance_ that considered to be ok for the fan to be turned on. For example, if the target temperature is 25 and the hot_tolerance is 1 and the fan_hot_tolerance is 0.5 the fan will start when the sensor equals or goes above 25 but not above 25.5. In that case the AC will turn on.

  _requires: `fan`_

### fan_hot_tolerance_toggle

  _(optional) (string)_ `entity_id` for a switch that will toggle the `fan_hot_tolerance` feature on and off.
  This is enabled by default.

  _default: True_

  _requires: `fan` , `fan_hot_tolerance`_

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

  _(optional) (list)_  "list of opening `entity_id`'s and/or objects for detecting open widows or doors that will idle the thermostat until any of them are open. Note: if min_floor_temp is set and the floor temperature is below the minimum temperature, the thermostat will not idle even if any of the openings are open."

  `entity_id: <value>`The entity id of the opening bstate sensor (string)</br>

  `timeout: <value>` The time after which the opening is considered open even if the state is still `on` (timedata)</br>

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

  _(optional) (time, integer)_  Set a minimum amount of time that the switch specified in the _heater_  and/or _cooler_ option must be in its current state prior to being switched either off or on.

### cold_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the _target_sensor_ option and the target temperature that must change prior to being switched on. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5.

  _default: 0.3_

### hot_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the _target_sensor_ option and the target temperature that must change prior to being switched off. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will stop when the sensor equals or goes above 25.5.

  _default: 0.3_

### keep_alive

  _(optional) (time, integer)_ Set a keep-alive interval. If set, the switch specified in the _heater_ and/or _cooler_ option will be triggered every time the interval elapses. Use with heaters and A/C units that shut off if they don't receive a signal from their remote for a while. Use also with switches that might lose state. The keep-alive call is done with the current valid climate integration state (either on or off).

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

The `dual_smart_thermostat` has two tolerance variables: `cold_tolerance` and `hot_tolerance`. These variables are used to prevent the heater or cooler from switching on and off too frequently. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5. The heater will stop when the sensor equals or goes above 25.5. This prevents the heater from switching on and off too frequently when the temperature is close to the target temperature.

If the thermostat is set to heat_cool mode the tolerance will work in the same way for both the heater and the cooler.

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
      seconds: 5
      seconds: 5
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

#### Testing

Use pytest to run the tests:

```bash
pytest
```

**Specific test**

```bash
pytest tests/test_heater_mode.py
```

**Log Level**

```bash
pytest --log-cli-level=DEBUG
```
