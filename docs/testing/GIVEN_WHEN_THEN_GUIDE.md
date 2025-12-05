# Given/When/Then Test Pattern Guide

**Purpose:** Ensure all tests follow a consistent, readable structure that clearly communicates test intent and logic flow.

---

## Pattern Overview

The Given/When/Then pattern structures tests into three distinct sections:

```python
async def test_example(hass):
    """Test that [specific behavior happens]."""

    # GIVEN - Setup initial state and prerequisites
    # [Setup code here]

    # WHEN - Perform the action being tested
    # [Action code here]

    # THEN - Verify the expected outcome
    # [Assertion code here]
```

---

## Section Breakdown

### GIVEN - Setup Initial State
**Purpose:** Establish the starting conditions for the test

**Guidelines:**
- Set up entities, sensors, and configuration
- Initialize state values
- Configure test fixtures
- Create test data
- Should be idempotent and isolated

**Example:**
```python
# GIVEN - Thermostat configured in heat mode at 20°C
setup_sensor(hass, 20)
heater_switch = "input_boolean.heater"
assert await async_setup_component(
    hass, input_boolean.DOMAIN, {"input_boolean": {"heater": None}}
)
await async_setup_climate(hass, {
    "heater": heater_switch,
    "target_sensor": common.ENT_SENSOR,
    "initial_hvac_mode": HVACMode.HEAT,
})
await hass.async_block_till_done()
```

---

### WHEN - Perform Action
**Purpose:** Execute the specific action or behavior being tested

**Guidelines:**
- Single, focused action (or sequence of related actions)
- Clear and explicit (no hidden side effects)
- Should be the only thing that changes between GIVEN and THEN
- Can have multiple WHEN sections for complex scenarios

**Example:**
```python
# WHEN - Temperature rises above target + tolerance
setup_sensor(hass, 25)
await hass.async_block_till_done()
```

**Complex Example:**
```python
# WHEN - User sets preset mode
await common.async_set_preset_mode(hass, PRESET_AWAY)
await hass.async_block_till_done()

# WHEN - Temperature changes during preset
setup_sensor(hass, 18)
await hass.async_block_till_done()
```

---

### THEN - Verify Outcome
**Purpose:** Assert that the expected behavior occurred

**Guidelines:**
- Clear, specific assertions
- Test one logical outcome (can have multiple related assertions)
- Use descriptive assertion messages when helpful
- Verify both direct effects and side effects
- Can have multiple THEN sections matching multiple WHENs

**Example:**
```python
# THEN - Heater turns off
state = hass.states.get(common.ENTITY)
assert state.attributes.get("temperature") == 25
assert state.state == HVACMode.HEAT
heater_state = hass.states.get(heater_switch)
assert heater_state.state == STATE_OFF
```

---

## Pattern Variations

### Simple Test (Single Action)
```python
async def test_set_target_temperature(hass, setup_comp_heat):
    """Test that setting target temperature updates the thermostat state."""

    # GIVEN - Thermostat in heat mode with initial temp
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23

    # WHEN - User sets new target temperature
    await common.async_set_temperature(hass, 25)
    await hass.async_block_till_done()

    # THEN - Target temperature is updated
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 25
```

### Complex Test (Multiple Actions)
```python
async def test_preset_mode_temperature_restoration(hass, setup_comp_heat_presets):
    """Test that exiting preset mode restores previous temperature."""

    # GIVEN - Thermostat at 23°C with no preset
    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23

    # WHEN - User activates AWAY preset
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    await hass.async_block_till_done()

    # THEN - Temperature changes to preset value (16°C)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 16
    assert state.attributes.get("preset_mode") == PRESET_AWAY

    # WHEN - User deactivates preset
    await common.async_set_preset_mode(hass, PRESET_NONE)
    await hass.async_block_till_done()

    # THEN - Original temperature is restored
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23
    assert state.attributes.get("preset_mode") == PRESET_NONE
```

### Parametrized Test
```python
@pytest.mark.parametrize(
    ("preset", "expected_temp"),
    [
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
    ],
)
async def test_preset_mode_sets_temperature(
    hass, setup_comp_heat_presets, preset, expected_temp
):
    """Test that preset modes set correct temperatures."""

    # GIVEN - Thermostat in heat mode with default temp
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_NONE

    # WHEN - User activates preset mode
    await common.async_set_preset_mode(hass, preset)
    await hass.async_block_till_done()

    # THEN - Temperature matches preset configuration
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == expected_temp
    assert state.attributes.get("preset_mode") == preset
```

---

## Common Patterns

### Testing State Transitions
```python
async def test_hvac_mode_transition(hass, setup_comp):
    """Test HVAC mode transitions from OFF to HEAT."""

    # GIVEN - Thermostat is OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    # WHEN - User switches to HEAT mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # THEN - Mode changes to HEAT
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.HEAT
```

### Testing Tolerance Logic
```python
async def test_temperature_within_tolerance(hass, setup_comp_heat):
    """Test that heater stays on when temperature within tolerance."""

    # GIVEN - Heater running with target 23°C, current 22°C
    await common.async_set_temperature(hass, 23)
    setup_sensor(hass, 22)
    await hass.async_block_till_done()
    heater_state = hass.states.get("input_boolean.heater")
    assert heater_state.state == STATE_ON

    # WHEN - Temperature rises slightly (within cold tolerance)
    setup_sensor(hass, 22.3)
    await hass.async_block_till_done()

    # THEN - Heater remains on (within 0.5°C tolerance)
    heater_state = hass.states.get("input_boolean.heater")
    assert heater_state.state == STATE_ON
```

### Testing Error Conditions
```python
async def test_invalid_preset_mode(hass, setup_comp_heat_presets):
    """Test that setting invalid preset mode raises ValueError."""

    # GIVEN - Thermostat configured with standard presets
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_NONE

    # WHEN - User attempts invalid preset
    # THEN - ValueError is raised
    with pytest.raises(ValueError):
        await common.async_set_preset_mode(hass, "invalid_preset")
```

### Testing Sensor Behavior
```python
async def test_sensor_unavailable_handling(hass, setup_comp_heat):
    """Test that unavailable sensor prevents heater operation."""

    # GIVEN - Heater operating normally at 20°C
    setup_sensor(hass, 20)
    await hass.async_block_till_done()
    heater_state = hass.states.get("input_boolean.heater")
    assert heater_state.state == STATE_ON

    # WHEN - Temperature sensor becomes unavailable
    hass.states.async_set(common.ENT_SENSOR, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    # THEN - Heater turns off for safety
    heater_state = hass.states.get("input_boolean.heater")
    assert heater_state.state == STATE_OFF
```

---

## Best Practices

### DO ✅

1. **Use clear section comments**
   ```python
   # GIVEN - Heater in auto mode with 20°C target
   # WHEN - Temperature drops below threshold
   # THEN - Heater activates
   ```

2. **Keep sections focused**
   - GIVEN should only set up state
   - WHEN should only perform actions
   - THEN should only verify outcomes

3. **Use descriptive test names**
   ```python
   # Good
   async def test_heater_activates_when_temperature_below_target_minus_tolerance()

   # Bad
   async def test_heater()
   ```

4. **Include docstrings**
   ```python
   async def test_example(hass):
       """Test that heater activates when temperature drops below target.

       This verifies the cold tolerance logic works correctly.
       """
   ```

5. **Group related assertions**
   ```python
   # THEN - Heater activates and HVAC action updates
   heater_state = hass.states.get("input_boolean.heater")
   assert heater_state.state == STATE_ON

   state = hass.states.get(common.ENTITY)
   assert state.attributes.get("hvac_action") == HVACAction.HEATING
   ```

---

### DON'T ❌

1. **Mix sections**
   ```python
   # Bad - mixing setup and action
   setup_sensor(hass, 20)
   await common.async_set_temperature(hass, 25)
   state = hass.states.get(common.ENTITY)
   ```

2. **Skip section comments**
   ```python
   # Bad - unclear where sections begin/end
   setup_sensor(hass, 20)
   await hass.async_block_till_done()
   await common.async_set_temperature(hass, 25)
   state = hass.states.get(common.ENTITY)
   assert state.attributes.get("temperature") == 25
   ```

3. **Test multiple unrelated things**
   ```python
   # Bad - testing multiple behaviors in one test
   async def test_everything(hass):
       # Tests preset mode, tolerance, opening detection, etc.
   ```

4. **Use vague assertions**
   ```python
   # Bad
   assert state is not None

   # Good
   assert state.attributes.get("temperature") == 25
   ```

---

## Converting Existing Tests

### Before (No Pattern)
```python
async def test_temp_change_heater_on_within_tolerance(hass, setup_comp_heat):
    """Test if temperature change doesn't turn off the heater."""
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    setup_sensor(hass, 23.3)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
```

### After (With Pattern)
```python
async def test_temp_change_heater_on_within_tolerance(hass, setup_comp_heat):
    """Test that heater remains on when temperature change is within tolerance."""

    # GIVEN - Heater running with target 25°C, current 23°C
    await common.async_set_temperature(hass, 25)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    heater_state = hass.states.get(heater_switch)
    assert heater_state.state == STATE_ON

    # WHEN - Temperature rises slightly within cold tolerance
    setup_sensor(hass, 23.3)
    await hass.async_block_till_done()

    # THEN - Heater remains on (within 0.5°C tolerance)
    heater_state = hass.states.get(heater_switch)
    assert heater_state.state == STATE_ON
```

**Improvements:**
1. Clear section separation
2. Explicit state verification in GIVEN
3. Descriptive comments explaining the logic
4. Verification that initial state is correct before testing transition

---

## Parametrized Test Pattern

```python
@pytest.mark.parametrize(
    "mode_type,expected_modes",
    [
        ("heater", [HVACMode.HEAT, HVACMode.OFF]),
        ("cooler", [HVACMode.COOL, HVACMode.OFF]),
        ("heat_pump", [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]),
    ],
)
async def test_get_hvac_modes(hass, mode_type, expected_modes):
    """Test that HVAC modes are correctly reported for each system type."""

    # GIVEN - System configured with specific mode type
    await setup_mode_config(hass, mode_type)
    await hass.async_block_till_done()

    # WHEN - Retrieving available HVAC modes
    state = hass.states.get(common.ENTITY)
    actual_modes = state.attributes.get("hvac_modes")

    # THEN - Modes match system type configuration
    assert actual_modes == expected_modes
```

---

## Shared Test Template

Use this template when creating new shared parametrized tests:

```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.keys(), indirect=True)
async def test_feature_name(hass, mode_config):
    """Test that [specific behavior] works across all HVAC modes.

    This test verifies [detailed description of what's being tested].
    Mode-specific configurations are applied via mode_config fixture.
    """
    # GIVEN - [Setup description]
    # Extract mode-specific config
    device_entity = mode_config["device_entity"]
    hvac_mode = mode_config["hvac_mode"]
    target_temp = mode_config["target_temp"]

    # Setup component with mode config
    await setup_component_with_mode(hass, mode_config)
    await hass.async_block_till_done()

    # WHEN - [Action description]
    await common.async_set_temperature(hass, target_temp)
    await hass.async_block_till_done()

    # THEN - [Expected outcome description]
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.state == hvac_mode
```

---

## Review Checklist

Before committing tests, verify:

- [ ] Each test has clear GIVEN/WHEN/THEN sections with comments
- [ ] Test name describes what is being tested
- [ ] Docstring explains the test purpose
- [ ] GIVEN section sets up all prerequisites
- [ ] WHEN section performs focused action(s)
- [ ] THEN section verifies expected outcomes
- [ ] No mixing of setup, action, and assertion logic
- [ ] Assertions are specific and descriptive
- [ ] Test is focused on one logical behavior
- [ ] Parametrized tests use indirect fixtures appropriately

---

## Examples Repository

See these files for examples:
- `tests/shared_tests/test_setup_base.py` - Setup test examples
- `tests/shared_tests/test_preset_base.py` - Preset test examples
- `tests/test_heater_mode.py` - Mode-specific test examples

---

**Last Updated:** 2025-12-04
**Related:** TEST_CONSOLIDATION_PLAN.md
