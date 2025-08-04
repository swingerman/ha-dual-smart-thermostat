# Feature Test Coverage Matrix

This matrix tracks test coverage across different HVAC modes supported by the dual smart thermostat.

**Legend:**
- `X` = Test exists and passes
- `!` = Test exists but needs attention/updating  
- `?` = Test status unknown or missing
- `N/A` = Not applicable for this mode

## Common Features

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| unique_id | X | X | X | X | X | X |
| setup defaults unknown | X | X | X | X | X | X |
| setup get current temp from sensor | X | X | X | X | X | X |
| setup default params | X | X | ! | X | X | X |
| restore state | X | X | ! | ! | X | X |
| no restore state | X | X | ! | ! | X | X |
| custom setup params | X | X | ! | ! | X | X |
| reload | X | X | ! | ! | X | X |

## Sensors

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| sensor bad value | X | X | ! | ! | X | X |
| sensor unknown | X | X | ! | ! | X | X |
| sensor unavailable | X | X | ! | ! | X | X |
| floor sensor bad value | X | X | N/A | ! | N/A | ? |
| floor sensor unknown | X | X | N/A | ! | N/A | ? |
| floor sensor unavailable | X | X | N/A | ! | N/A | ? |
| humidity sensor (dry mode) | N/A | N/A | N/A | N/A | X | N/A |

## Change Settings

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| get hvac modes | X | X | X | X | X | X |
| get hvac modes fan configured | N/A | N/A | X | X | N/A | X |
| set target temp | X | X | ! | X | N/A | X |
| set target humidity | N/A | N/A | N/A | N/A | X | N/A |
| set preset mode | X | X | X | X | X | X |
| - preset away | X | X | X | X | X | X |
| - preset home | X | X | X | X | X | X |
| - preset sleep | X | X | X | X | X | X |
| - preset eco | X | X | X | X | X | X |
| - preset boost | X | X | X | N/A | X | X |
| - preset comfort | X | X | X | X | X | X |
| - preset anti freeze | X | X | X | X | X | X |
| set preset mode restore prev temp | X | X | X | X | X | X |
| set preset mode 2x restore prev temp | X | X | X | X | X | X |
| set preset mode invalid | X | X | X | X | X | X |
| set preset mode set temp keeps preset mode | X | X | X | X | X | X |

## HVAC Operations

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| target temp switch on | X | X | X! | X! | N/A | X |
| target temp switch off | X | X | X! | X! | N/A | X |
| target humidity switch on | N/A | N/A | N/A | N/A | X | N/A |
| target humidity switch off | N/A | N/A | N/A | N/A | X | N/A |
| target temp switch on within tolerance | X | X | X | ! | N/A | X |
| target temp switch on outside tolerance | X | X | X | ! | N/A | X |
| target temp switch off within tolerance | X | X | X | ! | N/A | X |
| target temp switch off outside tolerance | X | X | X | ! | N/A | X |
| running when hvac mode off | X | X | X | X | X | X |
| no state change when hvac mode off | X | X | X | X | X | X |
| hvac mode heat | N/A | X | N/A | X | N/A | X |
| hvac mode cool | X | N/A | X | X | N/A | X |
| hvac mode fan only | X | N/A | N/A | N/A | N/A | N/A |
| hvac mode dry | N/A | N/A | N/A | N/A | X | N/A |
| temp change heater trigger off not long enough | N/A | X | N/A | ! | N/A | X |
| temp change heater trigger on not long enough | N/A | X | N/A | ! | N/A | X |
| temp change heater trigger on long enough | N/A | X | N/A | ! | N/A | X |
| temp change heater trigger off long enough | N/A | X | N/A | ! | N/A | X |
| mode change heater trigger off not long enough | N/A | X | N/A | ! | N/A | X |
| mode change heater trigger on not long enough | N/A | X | N/A | ! | N/A | X |
| precision | X | ! | ! | ! | X | X |
| init hvac off force switch off | X | X | ! | ! | X | X |
| restore will turn off | X | X | ! | ! | X | X |
| restore will turn off when loaded second | X | X | ! | ! | X | X |
| restore state uncoherence state | X | X | ! | ! | X | X |
| aux heater | N/A | X | N/A | N/A | N/A | N/A |
| aux heater keep primary on | N/A | X | N/A | N/A | N/A | N/A |
| aux heater today | N/A | ! | N/A | N/A | N/A | N/A |
| tolerance | X | X | X! | ? | X | X |
| floor temp | X | X | N/A | ? | N/A | ? |
| hvac mode cycle | X | X | X | ? | X | X |
| fan mode hvac fan only mode | X | N/A | ! | ! | N/A | N/A |
| fan mode hvac fan only mode on | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan on within tolerance | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan on outside tolerance | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan off within tolerance | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan off outside tolerance | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan on with cooler | X | N/A | ! | ! | N/A | N/A |
| fan mode turn fan off with cooler | X | N/A | ! | ! | N/A | N/A |

## HVAC Action Reason

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| hvac action reason default | X | X | ! | ! | X | X |
| hvac action reason service | X | X | ! | ! | X | X |
| floor temp hvac action reason | X | X | N/A | X | N/A | ? |
| opening hvac action reason | X | X | X | ! | X | X |

## Openings (Window/Door Sensors)

| Feature | Fan Mode | Cool Mode | Heat Mode | Heat Cool Mode | Dry Mode | Heat Pump Mode |
| --- | --- | --- | --- | --- | --- | --- |
| opening detection | X | X | X | ! | X | X |
| opening fan mode | X | N/A | ! | ! | N/A | N/A |
| opening timeout | X | X | X | ! | X | X |
| opening scope configuration | X | X | X | ! | X | X |

## Missing Test Coverage Areas

These features exist in the codebase but may need additional test coverage:

| Feature | Status | Notes |
| --- | --- | --- |
| HVAC Power Levels | ? | New feature, needs test coverage |
| Heat Pump Mode switching | ! | Partial coverage, needs more comprehensive tests |
| Two-stage heating in heat-cool mode | ! | Needs testing |
| Fan air outside temperature logic | ! | Complex feature needs more tests |
| Sensor stale detection | ! | Error handling needs testing |
| Multiple device combinations | ! | Multi-device scenarios need testing |

## Test File Summary

- `test_heater_mode.py`: 66 tests - Comprehensive heater-only testing
- `test_cooler_mode.py`: 50 tests - Comprehensive cooler-only testing  
- `test_fan_mode.py`: 112 tests - Most comprehensive, covers fan-only and fan+cooler modes
- `test_dual_mode.py`: 69 tests - Heat+cool dual mode testing
- `test_dry_mode.py`: 44 tests - Humidity control testing
- `test_heat_pump_mode.py`: 19 tests - Basic heat pump testing, needs expansion
- `test_init.py`: 0 tests - Module initialization testing
