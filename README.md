# Home Assistant Dual Smart Thermostat component

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)

The `dual_smart_thermostat` is an enhanced verion of generic thermostat implemented in Home Assistant. It uses several sensors and dedicated switches connected to a heater and air conditioning under the hood. When in heater-cooler mode, if the measured temperature is cooler than the target low `target_temp_low` temperature, the heater will be turned on off when the required low temperature is reached, if the measured temperature is hotter than the target high temperature, the cooling (air conditioning) will be turned on and turned off when the required high `target_temp_high` temperature is reached. When in heater mode, if the measured temperature is cooler than the target temperature, the heater will be turned on and turned off when the required temperature is reached. When in cooling mode, if the measured temperature is hotter than the target temperature, the cooler (air conditioning) will be turned on and turned off when required high temperature is reached.

## Openings

The `dual_smart_thermostat` can turn off heating or cooling if a window or door is opened and turn heating or cooling back on when the door or window is closed to save energy.
The `openings` configuration variable accepts a list of openings.

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
      - sensor.window1
      - sensor.window2
    target_sensor: sensor.study_temperature
```

## Configuration variables

### name

&nbsp;&nbsp;&nbsp;&nbsp;_(required) (string)_ Name of thermostat

&nbsp;&nbsp;&nbsp;&nbsp;_default: Dual Smart_

### heater

  &nbsp;&nbsp;&nbsp;&nbsp;_(required) (string)_ "`entity_id` for heater switch, must be a toggle device. Becomes air conditioning switch when `ac_mode` is set to `true`"

### cooler

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (string)_ "`entity_id` for cooler switch, must be a toggle device."

### target_sensor

  &nbsp;&nbsp;&nbsp;&nbsp;_(required) (string)_  "`entity_id` for a temperature sensor, target_sensor.state must be temperature."

### floor_sensor

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (string)_  "`entity_id` for the foor temperature sensor, floor_sensor.state must be temperature."

### openings
  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (list)_  "list of opening `entity_id`'s for detecting open widows or doors that will idle the termostat until any of them are open"

### min_temp

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_

  &nbsp;&nbsp;&nbsp;&nbsp;_default: 7_

### max_temp

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_

  &nbsp;&nbsp;&nbsp;&nbsp;_default: 35_

### max_floor_temp

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_

  &nbsp;&nbsp;&nbsp;&nbsp;_default: 28_

### target_temp

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ Set initial target temperature. Failure to set this variable will result in target temperature being set to null on startup.

### target_temp_low

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ Set initial target low temperature. Failure to set this variable will result in target temperature being set to null on startup.

### target_temp_high

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ Set initial target high temperature. Failure to set this variable will result in target temperature being set to null on startup.

### ac_mode

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (boolean)_ Set the switch specified in the *heater* option to be treated as a cooling device instead of a heating device.

  &nbsp;&nbsp;&nbsp;&nbsp;_default: false_

### min_cycle_duration

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (time, integer)_  Set a minimum amount of time that the switch specified in the *heater*  and/or *cooler* option must be in its current state prior to being switched either off or on.

### cold_tolerance

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the *target_sensor* option and the target temperature that must change prior to being switched on. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will start when the sensor equals or goes below 24.5.

  &nbsp;&nbsp;&nbsp;&nbsp;_default: 0.3_

### hot_tolerance

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ Set a minimum amount of difference between the temperature read by the sensor specified in the *target_sensor* option and the target temperature that must change prior to being switched off. For example, if the target temperature is 25 and the tolerance is 0.5 the heater will stop when the sensor equals or goes above 25.5.

  &nbsp;&nbsp;&nbsp;&nbsp;_default: 0.3_

### keep_alive

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (time, integer)_ Set a keep-alive interval. If set, the switch specified in the *heater* and/or *cooler* option will be triggered every time the interval elapses. Use with heaters and A/C units that shut off if they don't receive a signal from their remote for a while. Use also with switches that might lose state. The keep-alive call is done with the current valid climate integration state (either on or off).

### initial_hvac_mode

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (string)_ Set the initial HVAC mode. Valid values are `off`, `heat`, `cool` or `heat_cool`. Value has to be double quoted. If this parameter is not set, it is preferable to set a *keep_alive* value. This is helpful to align any discrepancies between *dual_smart_thermostat* *heater* and *cooler* state.

### away_temp

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ "Set the temperature used by `preset_mode: away`. If this is not specified, the preset mode feature will not be available."

### precision

  &nbsp;&nbsp;&nbsp;&nbsp;_(optional) (float)_ "The desired precision for this device. Can be used to match your actual thermostat's precision. Supported values are `0.1`, `0.5` and `1.0`."

  &nbsp;&nbsp;&nbsp;&nbsp;_default: "`0.5` for Celsius and `1.0` for Fahrenheit."_

## Installation

Installation is via the [Home Assistant Community Store (HACS)](https://hacs.xyz/), which is the best place to get third-party integrations for Home Assistant. Once you have HACS set up, simply [search the `Integrations` section](https://hacs.xyz/docs/basic/getting_started) for Dual Smart Thermostat.

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
      - sensor.window1
      - sensor.window2
    min_temp: 15
    max_temp: 21
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
    initial_hvac_mode: "off"
    away_temp: 16
    precision: 0.1
```

### Donate

I am happy tp help the Home Assistant community but I do it in my free time at the cost of spending less time with my family. Feel free to motivate me and appreciate my sacrifice by donating:

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)
