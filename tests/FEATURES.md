# Feature Test Coverage Matrix


## Common Features

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| unique_id | X | X | X |
| setup defaults unknown | X | X | X |
| setup get current temp form sensor | X | X | X |
| setup default params | X | ! | X |
| restore state | X | ! | ! |
| no restore state | X | ! | ! |
| custom setup params | X | ! | ! |
| reload | X | ! | ! |

## sensors

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| sensor bad value | X | ! | ! |
| sensor unknown | X | ! | ! |
| sensor unavailable | X | ! | ! |
| floor sensor bad value | X | N/A | ! |
| floor sensor unknown | X | N/A | ! |
| floor sensor unavailable | X | N/A | ! |

## Change Settings

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| get hvac modes | X | X | X |
| set target temp | X | ! | X |
| set preset mode | X | X | X |
| - preset away | X | X | X |
| - preset home | X | X | X |
| - preset sleep | X | X | X |
| - preset eco | X | X | X |
| - preset boost | X | X | N/A |
| - preset comfort | X | X | X |
| - preset anti freeze | X | X | X |
| set preset mode restore prev temp | X | X | X |
| set preset mode 2x restore prev temp | X | X | X |
| set preset mode invalid | X | X | X |
| set preset mode set temp keeps preset mode | X | X | X |

## Hvac Operations

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| target temp switch on | X | X! | X! |
| target temp switch off | X | X! | X! |
| target temp switch on within tolerance | X | X | ! |
| target temp switch on outside tolerance | X | X | ! |
| target temp switch off within tolerance | X | X | ! |
| target temp switch off outside tolerance | X | X | ! |
| running when hvac mode off | X | X | X |
| no state change when hvac mode off | X | X | X |
| hvac mode heat | X | N/A | X |
| hvac mode cool | N/A | X | X |
| temp change heater trigger off not long enough | X | N/A | ! |
| temp change heater trigger on not long enough | X | N/A | ! |
| temp change heater trigger on long enough | X | N/A | ! |
| temp change heater trigger off long enough | X | N/A | ! |
| mode change heater trigger off not long enough | X | N/A | ! |
| mode change heater trigger on not long enough | X | N/A | ! |

| precision | X | ! | ! |
| init hvac off force switch off | X | ! | ! |
| restore will turn off | X | ! | ! |
| restore will turn off when loaded second | X | ! | ! |
| restore state uncoherence state | X | ! | ! |
| aux heater | X | N/A | N/A |
| aux heater keep primary on | X | N/A | N/A |
| aux heater today | ! | N/A | N/A |
| tolerance | X | X! | ? |
| floor temp | X | N/A | ? |
| hvac mode cycle | X | X | ? |

## Hvac Action Reason

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| hvac action reason default | X | ! | ! |
| hvac action reason service | X | ! | ! |
| floor temp Hvac Action Reason  | X | N/A | X |
| opening Hvac Action reason | X | X | ! |

## Openings

| Feature | Cool Mode | Heat Mode | Heat Cool Mode |
| --- | --- | --- | --- |
| opening | X | X | ? |
