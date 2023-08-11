# Home Assistant Dual Smart Thermostat component

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/swingerman/ha-dual-smart-thermostat) ![Release](https://img.shields.io/github/v/release/swingerman/ha-dual-smart-thermostat?style=for-the-badge) [![Donate](https://img.shields.io/badge/Donate-PayPal-yellowgreen?style=for-the-badge&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)


The `dual_smart_thermostat` is an enhanced verion of generic thermostat implemented in Home Assistant. It uses several sensors and dedicated switches connected to a heater and air conditioning under the hood. When in heater-cooler mode, if the measured temperature is cooler than the target low `target_temp_low` temperature, the heater will be turned on off when the required low temperature is reached, if the measured temperature is hotter than the target high temperature, the cooling (air conditioning) will be turned on and turned off when the required high `target_temp_high` temperature is reached. When in heater mode, if the measured temperature is cooler than the target temperature, the heater will be turned on and turned off when the required temperature is reached. When in cooling mode, if the measured temperature is hotter than the target temperature, the cooler (air conditioning) will be turned on and turned off when required high temperature is reached.

## Openings

The `dual_smart_thermostat` can turn off heating or cooling if a window or door is opened and turn heating or cooling back on when the door or window is closed to save energy.
The `openings` configuration variable accepts a list of opening entities and opening objects.

### Opening entities and objects

An opening entity is a sensor that can be in two states: `on` or `off`. If the state is `on` the opening is considered open, if the state is `off` the opening is considered closed.
The opening object can conatin a timout property that defines the time in seconds after which the opening is considered open even if the state is still `on`. This is useful if you would want to ignor windows opened only for a short time.

### Example

```yaml
openings:
  - sensor.window1
  - sensor.window2
  - entity_id: binary_sensor.window3
    timeout: 00:00:30 # cosnidered to be open if still open after 30 seconds
```

## Floor heating temperature cap

The `dual_smart_thermostat` can turn off if the floor heating reaches tha maximum allowed temperature you define in order to protect the floor from overheating and damage.
To enable this protection you need to set two variables:
```yaml
floor_sensor: sensor.floor_temp
max_floor_temp: 28
```

## Configuration

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

## Configuration variables

### name

_(required) (string)_ Name of thermostat

_default: Dual Smart_

### heater

  _(required) (string)_ "`entity_id` for heater switch, must be a toggle device. Becomes air conditioning switch when `ac_mode` is set to `true`"

### cooler

  _(optional) (string)_ "`entity_id` for cooler switch, must be a toggle device."

### target_sensor

  _(required) (string)_  "`entity_id` for a temperature sensor, target_sensor.state must be temperature."

### floor_sensor

  _(optional) (string)_  "`entity_id` for the foor temperature sensor, floor_sensor.state must be temperature."

### openings
  _(optional) (list)_  "list of opening `entity_id`'s and/or opbjects for detecting open widows or doors that will idle the termostat until any of them are open"

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

### anti_freeze

  _(optional) (list)_ Set the temperature used by `preset_mode: Anti Freeze`. If this is not specified, the preset mode feature will not be available.

  Possible values are:

  `temperature: <value>` The preset temperature to use in `heat` or `cool` mode (float)</br>
  `target_temp_low: <value>` The preset low temperature to use in `heat_cool` mode (float)</br>
  `target_temp_high: <value>` The preset high temperature to use in `heat_cool` mode (float)</br>

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

## DUAL Heat-Cool Mode Example

This mode is used whan you want (and can) control bothe the heater and the cooler. In this mode the `target_temp_low` and `target_temp_high` must be set.
In this mode you can switch between heating and cooling by setting the `hvac_mode` to `heat` or `cool` or `heat_cool`.

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Study
    heater: switch.study_heater
    cooler: switch.study_cooler
    target_sensor: sensor.study_temperature
    heat_cool_mode: true # <-important
    initial_hvac_mode: "heat_cool"
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
