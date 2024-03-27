# Home Assistant Dual Smart Thermostat component

The `dual_smart_thermostat` is an enhanced version of generic thermostat implemented in Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/swingerman/ha-dual-smart-thermostat) ![Release](https://img.shields.io/github/v/release/swingerman/ha-dual-smart-thermostat?style=for-the-badge) [![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)

## Table of contents

- [Features](#features)
- [Services](#services)
- [Configuration variables](#configuration-variables)
- [Installation](#installation)

## Features

|  |  | |
| :--- | :---: | :---: |
| **Heater/Cooler Mode** | <img src="docs/images/sun-snowflake.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" style="stroke: red" />](#heatcool-mode) |
| **Heater Only Mode** | <img src="docs/images/radiator.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" />](#heater-only-mode) |
| **Two Stage (AUX) Heating Mode** | <img src="docs/images/radiator.svg" height="30" /> <img src="docs/images/plus.svg" height="30" /> <img src="docs/images/radiator.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" />](#two-stage-heating) |
| **Cooler Only mode** | <img src="docs/images/air-conditioner.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" />](#cooler-only-mode) |
| **Floor Temperature Control** | <img src="docs/images/heating-coil.svg" height="30" /> <img src="docs/images/snowflake-thermometer.svg" height="30" />  <img src="docs/images/thermometer-alert.svg" height="30" />  | [<img src="docs/images/file-document-outline.svg" height="30" />](#floor-heating-temperature-control) |
| **Window/Door sensor integration** | <img src="docs/images/window-open.svg" height="30" /> <img src="docs/images/door-open.svg" height="30" /> <img src="docs/images/chevron-right.svg" height="30" /> <img src="docs/images/timer-cog-outline.svg" height="30" /> <img src="docs/images/chevron-right.svg" height="30" /> <img src="docs/images/hvac-off.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" />](#openings) |
| **Presets** | <img src="docs/images/sleep.svg" height="30" /> <img src="docs/images/snowflake-thermometer.svg" height="30" /> <img src="docs/images/shield-lock-outline.svg" height="30" /> | [<img src="docs/images/file-document-outline.svg" height="30" />](#presets) |
| **HVAC Action Reason** | | [<img src="docs/images/file-document-outline.svg" height="30" />](#presets) |


## Heat/Cool Mode

If both [`heater`](#heater) and [`cooler`](#cooler) entities configured. The thermostat can control heaing and cooling and you sare able to set min/max low and min/max high temperatures.
In this mode you can turn the thermostat to heat only, cooler only and back to heat/cool mode.

[all features ⤴️](#features)

## Heater Only Mode

If only the [`heater`](#heater) entity is set the thermostat works only in heater mode.

[all features ⤴️](#features)

## Two Stage (AUX) Heating

Thwo stage or AUX heating can be anabled by cadding the [required configuration](#two-stage-heating-example) netities: [`secondary_heater`](#secondary_heater), [`secondary heater_timeout`](#secondar_heater_timeout). If these are set the feature will enable automatically.
Optionally you can set [`secondary heater_dual_mode`](#secondar_heater_dual_mode) to `true` to turn on the secondary heater together with the primary heater.

### How Two Stage Heating Works?

If the timeout ends and the [`heater`](#heater) was on for the whole time the thermostate switches to the [`secondary heater`](#secondary_heater). In this case the primarey heater ([`heater`](#heater)) will be turned off. This will be rmemebered for the day it turned on and in the next heating cycle the [`secondary heater`](#secondary_heater) will turn on automatically.
On the next day the primary heater will turn on again the second stage will again only turn on after a timeout.
If the third [`secondary heater_dual_mode`](#secondar_heater_dual_mode) is set to `true` the secondary heater will be turned on together with the primary heater.

### Two Stage Heating Example

```yaml
secondary_heater: switch.study_secondary_heater   # <-- required
secondar_heater_timeout: 00:00:30                 # <-- required
secondar_heater_dual_mode: true                   # <-- optional
```

## Cooler Only Mode

If only the [`cooler`](#cooler) entity is set the thermostat works only in cooling mode.

[all features ⤴️](#features)


## Openings

The `dual_smart_thermostat` can turn off heating or cooling if a window or door is opened and turn heating or cooling back on when the door or window is closed to save energy.
The `openings` configuration variable accepts a list of opening entities and opening objects.

### Opening entities and objects

An opening entity is a sensor that can be in two states: `on` or `off`. If the state is `on` the opening is considered open, if the state is `off` the opening is considered closed.
The opening object can contain a timeout property that defines the time in seconds after which the opening is considered open even if the state is still `on`. This is useful if you would want to ignor windows opened only for a short time.

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
    target_sensor: sensor.study_temperature
```
[all features ⤴️](#features)

## Floor heating temperature control

### Maximum floor temperature

The `dual_smart_thermostat` can turn off if the floor heating reaches the maximum allowed temperature you define in order to protect the floor from overheating and damage.
To enable this protection you need to set two variables:
```yaml
floor_sensor: sensor.floor_temp
max_floor_temp: 28
```

### Minimum floor temperature

The `dual_smart_thermostat` can turn on if the floor temperature reaches the minimum required temperature you define in order to protect the floor from freezing or to keep it on a comfortbale temperature.

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

Currrnetly supported presets are:

* none
* [home](#home)
* [away](#away)
* [eco](#eco)
* [sleep](#sleep)
* [comfort](#comfort)
* [anti freeze](#anti_freeze)
* [activity](#activity)
* [boost](#boost)

To set presets you need to add entries for them in the configuration file like this:

```yaml
preset_name:
  temperature: 13
  target_temp_low: 12
  target_temp_high: 14
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
| `target_temp_reached` | The target temperature has been reached |
| `misconfiguration` | The thermostat is misconfigured |
| `opening` | The thermostat is idle because an opening is open |
| `limit` | The thermostat is idle because the floor temperature is at the limit |
| `overheat` | The thermostat is idle because the floor temperature is too high |

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

  _(optional, __required for two stage heating__) (string)_ "`entity_id` for secondary heater switch, must be a toggle device.

### secondar_heater_timeout

  _(optional, __required for two stage heating__) (time, integer)_  Set a minimum amount of time that the switch specified in the *heater* option must be in its ON state before secondary heater devices needs to be turned on.

### secondar_heater_dual_mode

  _(optional, (bool)_  If set true the secondary (aux) heater will be turned on together with the primary heater.

### cooler

  _(optional) (string)_ "`entity_id` for cooler switch, must be a toggle device."

### target_sensor

  _(required) (string)_  "`entity_id` for a temperature sensor, target_sensor.state must be temperature."

### floor_sensor

  _(optional) (string)_  "`entity_id` for the floor temperature sensor, floor_sensor.state must be temperature."

### openings
  _(optional) (list)_  "list of opening `entity_id`'s and/or objects for detecting open widows or doors that will idle the thermostat until any of them are open. Note: if min_floor_temp is set and the floor temperature is below the minimum temperature, the thermostat will not idle even if any of the openings are open."

  `entity_id: <value>`The entity id of the opening bstate sensor (string)</br>

  `timeout: <value>` The time after which the opening is considered open even if the state is still `on` (timedata)</br>

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

  _(optional) (boolean)_ If variable `target_temp_low` and `target_temp_high` are not set, this parameter must be set to *true* to enable the `heat_cool` mode.

  _default: false_

### min_cycle_duration

  _(optional) (time, integer)_  Set a minimum amount of time that the switch specified in the *heater*  and/or *cooler* option must be in its current state prior to being switched either off or on.

### cold_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the *target_sensor* option and the target temperature that must change prior to being switched on. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5.

  _default: 0.3_

### hot_tolerance

  _(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the *target_sensor* option and the target temperature that must change prior to being switched off. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will stop when the sensor equals or goes above 25.5.

  _default: 0.3_

### keep_alive

  _(optional) (time, integer)_ Set a keep-alive interval. If set, the switch specified in the *heater* and/or *cooler* option will be triggered every time the interval elapses. Use with heaters and A/C units that shut off if they don't receive a signal from their remote for a while. Use also with switches that might lose state. The keep-alive call is done with the current valid climate integration state (either on or off).

### initial_hvac_mode

  _(optional) (string)_ Set the initial HVAC mode. Valid values are `off`, `heat`, `cool` or `heat_cool`. Value has to be double quoted. If this parameter is not set, it is preferable to set a *keep_alive* value. This is helpful to align any discrepancies between *dual_smart_thermostat* *heater* and *cooler* state.

  **NOTE! If this is set, the saved state will not be restored after HA retstarts.**

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
  mode will require setting `target_temp_low` higher than `target_temp_high` and vica versa.

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

## Two Stage Heateing Mode Example

For two stage heating both the `heater` and `secondary_heater` must be defined. The `secondary_heater` will be turned on only if the `heater` is on for the amount of time defined in `secondar_heater_timeout`.

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater

    secondary_heater: switch.study_secondary_heater # <-requred
    secondar_heater_timeout: 00:00:30 # <-requred

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

If the thermosat is set to heat_cool mode the tolerance will work in the same way for both the heater and the cooler.

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
    secondar_heater_timeout: 00:00:30
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

I am happy tp help the Home Assistant community but I do it in my free time at the cost of spending less time with my family. Feel free to motivate me and appreciate my sacrifice by donating:

[![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)
[![coffee](https://www.buymeacoffee.com/assets/img/custom_images/black_img.png)](https://www.buymeacoffee.com/swingerman)


### Develpoent

#### Tsting

Use pytest to run the tests:

```bash
pytest
```

__Specific test__

```bash
pytest tests/test_heater_mode.py
```

__Log Level__

```bash
pytest --log-cli-level=DEBUG
```
