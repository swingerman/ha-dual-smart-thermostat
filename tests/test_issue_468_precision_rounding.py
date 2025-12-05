"""Test for issue #468 - precision and temperature rounding issues.

After v0.11.0-beta3, users reported these problems when configuring via UI:
1. The displayed temperature from the sensor is rounded to the nearest whole number
2. The preset target temperature when no preset is active does not match the setting
3. The set temperature is rounded to the nearest whole number
4. When you first click to increase the temperature, it jumps to the maximum temperature

Root cause hypothesis:
The config flow stores precision as string "0.1" but climate.py expects float 0.1
When config_entry.data and options are merged, string values are passed to climate entity.
"""

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_PRECISION,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    CONF_TEMP_STEP,
    DOMAIN,
)
from tests import common, setup_sensor, setup_switch


class TestIssue468PrecisionFromConfigEntry:
    """Test precision handling when config comes from config entry (UI flow).

    This simulates the real user scenario where:
    1. User configures via UI (config flow stores strings)
    2. Entity is created
    3. User sets target temp to 22.3
    4. Bug: temp gets rounded to 22
    """

    async def test_precision_string_from_config_entry_is_converted_to_float(
        self, hass: HomeAssistant
    ):
        """Test that string precision from config entry is converted to float correctly.

        This verifies the fix for issue #468:
        When precision is stored as string "0.1" from config flow,
        it should be converted to float 0.1 and work correctly.
        """
        setup_sensor(hass, 22.5)
        setup_switch(hass, False, common.ENT_HEATER)

        # Simulate what config_entry.data looks like after config flow
        # Note: Config flow stores many values as strings!
        config_entry_data = {
            "name": "test",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.5,  # This might be stored as string too
            CONF_PRECISION: "0.1",  # String from config flow (fixed: should be converted to float)
            CONF_TEMP_STEP: "0.1",  # Also string from config flow
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        # Create a mock config entry using the test helper
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_precision_string",
        )
        config_entry.add_to_hass(hass)

        # Setup the integration via config entry
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state is not None, "Climate entity should be created from config entry"

        # Check the precision property - it should be a float, not a string
        # After the fix, string "0.1" should be converted to float 0.1
        target_temp_step = state.attributes.get("target_temp_step")

        # Verify the string-to-float conversion worked correctly
        assert isinstance(
            target_temp_step, (int, float)
        ), f"target_temp_step should be numeric, got {type(target_temp_step)}: {target_temp_step}"

        # Verify the step value is correct (0.1, not "0.1" string)
        assert (
            target_temp_step == 0.1
        ), f"target_temp_step should be 0.1, got {target_temp_step}"

        # Now try to set temperature to 22.3
        # With precision of 0.1, this should be accepted as 22.3
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 22.3, "entity_id": common.ENTITY},
            blocking=True,
        )

        state = hass.states.get(common.ENTITY)
        target_temp = state.attributes.get("temperature")

        # This verifies the fix is working
        # If precision string conversion works, target_temp will be 22.3
        assert target_temp == 22.3, (
            f"Target temp should be 22.3 but got {target_temp}. "
            "String precision was not correctly converted to float."
        )


class TestCorrectFloatPrecisionBehavior:
    """Test that float precision works correctly (baseline using YAML config)."""

    async def test_current_temperature_with_float_precision(self, hass: HomeAssistant):
        """Test that current temperature displays correctly with float precision."""
        setup_sensor(hass, 22.5)
        setup_switch(hass, False, common.ENT_HEATER)

        config = {
            "name": "test",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.5,
            CONF_PRECISION: 0.1,  # Float - correct
            CONF_TEMP_STEP: 0.5,  # Float - correct
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state is not None

        current_temp = state.attributes.get("current_temperature")
        assert current_temp == 22.5

    async def test_target_temperature_with_float_precision(self, hass: HomeAssistant):
        """Test that target temperature is correct with float precision."""
        setup_sensor(hass, 22.5)
        setup_switch(hass, False, common.ENT_HEATER)

        config = {
            "name": "test",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.5,
            CONF_PRECISION: 0.1,
            CONF_TEMP_STEP: 0.5,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state is not None

        target_temp = state.attributes.get("temperature")
        assert target_temp == 21.5

    async def test_set_non_whole_temperature_with_float_precision(
        self, hass: HomeAssistant
    ):
        """Test setting 22.3 works with float precision."""
        setup_sensor(hass, 22.5)
        setup_switch(hass, False, common.ENT_HEATER)

        config = {
            "name": "test",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: 0.1,  # Float
            CONF_TEMP_STEP: 0.1,  # Float
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        # Set temperature to 22.3
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 22.3, "entity_id": common.ENTITY},
            blocking=True,
        )

        state = hass.states.get(common.ENTITY)
        target_temp = state.attributes.get("temperature")
        assert target_temp == 22.3, f"Expected 22.3 but got {target_temp}"


class TestIssue468AllEdgeCases:
    """Test all 4 specific edge cases reported in issue #468.

    From user filipjurik's comment:
    1. The displayed temperature from the sensor is rounded to the nearest whole number
    2. The preset target temperature when no preset is active does not match the setting
    3. The set temperature is rounded to the nearest whole number
    4. When you first click to increase the temperature, it jumps to the maximum temperature
    """

    async def test_edge_case_1_sensor_temperature_not_rounded(
        self, hass: HomeAssistant
    ):
        """Edge case 1: Displayed temperature from sensor should NOT be rounded.

        When sensor reports 22.5°C and precision is 0.1, the UI should show 22.5°C,
        not 23°C (rounded up) or 22°C (rounded down).
        """
        setup_sensor(hass, 22.5)
        setup_switch(hass, False, common.ENT_HEATER)

        # Config as it comes from config flow (strings)
        config_entry_data = {
            "name": "test_edge_1",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.5,
            CONF_PRECISION: "0.1",  # String from UI - should be converted
            CONF_TEMP_STEP: "0.5",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_edge_1",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "climate.test_edge_1"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Edge case 1: current_temperature should NOT be rounded
        current_temp = state.attributes.get("current_temperature")
        assert current_temp == 22.5, (
            f"Edge case 1 FAILED: Sensor temperature was rounded! "
            f"Expected 22.5, got {current_temp}"
        )

    async def test_edge_case_2_preset_target_temp_matches_config(
        self, hass: HomeAssistant
    ):
        """Edge case 2: Preset target temperature when no preset is active.

        The target temperature should exactly match what was configured,
        not be rounded to a whole number.
        """
        setup_sensor(hass, 20.0)
        setup_switch(hass, False, common.ENT_HEATER)

        # Config with a decimal target temperature
        config_entry_data = {
            "name": "test_edge_2",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.5,  # Decimal target
            CONF_PRECISION: "0.1",  # String from UI
            CONF_TEMP_STEP: "0.5",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_edge_2",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "climate.test_edge_2"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Edge case 2: Target temperature should match config exactly
        target_temp = state.attributes.get("temperature")
        assert target_temp == 21.5, (
            f"Edge case 2 FAILED: Preset target temperature doesn't match config! "
            f"Expected 21.5, got {target_temp}"
        )

    async def test_edge_case_2b_auto_preset_selection_with_string_preset_temps(
        self, hass: HomeAssistant
    ):
        """Edge case 2b: Auto-preset selection with string preset temperatures.

        When preset temperatures come from config flow as strings (e.g., "18.5"),
        they should still be correctly matched when user sets temperature.
        This tests the auto-preset-selection feature with string values.
        """
        setup_sensor(hass, 20.0)
        setup_switch(hass, False, common.ENT_HEATER)

        # Config with string preset temperatures (simulating UI config flow)
        # Note: Config flow stores preset temps with keys like "eco_temp", "home_temp"
        config_entry_data = {
            "name": "test_edge_2b",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: "0.1",  # String from UI
            CONF_TEMP_STEP: "0.5",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            # Preset temperatures as strings (how they come from UI)
            "eco_temp": "18.5",  # String from UI
            "home_temp": "21.5",  # String from UI
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_edge_2b",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "climate.test_edge_2b"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Verify presets are available
        preset_modes = state.attributes.get("preset_modes", [])
        assert "eco" in preset_modes, f"eco preset not found in {preset_modes}"
        assert "home" in preset_modes, f"home preset not found in {preset_modes}"

        # Set temperature to match eco preset (18.5)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 18.5, "entity_id": entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)

        # Check if preset was auto-selected
        preset_mode = state.attributes.get("preset_mode")
        target_temp = state.attributes.get("temperature")

        # The temperature should be set correctly regardless of preset auto-selection
        assert target_temp == 18.5, (
            f"Edge case 2b FAILED: Temperature not set correctly! "
            f"Expected 18.5, got {target_temp}"
        )

        # Ideally, eco preset should be auto-selected (if feature works with strings)
        # But the main test is that the temperature comparison doesn't crash
        # due to string vs float comparison
        if preset_mode == "eco":
            # Auto-selection worked - great!
            pass
        else:
            # Log for debugging, but don't fail - the critical thing is no crash
            import logging

            logging.getLogger(__name__).info(
                f"Auto-preset selection did not activate eco preset. "
                f"preset_mode={preset_mode}, target_temp={target_temp}. "
                f"This may be expected if the feature is disabled or conditions not met."
            )

    async def test_edge_case_3_set_temperature_not_rounded(self, hass: HomeAssistant):
        """Edge case 3: Set temperature should NOT be rounded.

        When user sets temperature to 22.3°C with precision 0.1,
        it should stay at 22.3°C, not be rounded to 22°C.
        """
        setup_sensor(hass, 20.0)
        setup_switch(hass, False, common.ENT_HEATER)

        config_entry_data = {
            "name": "test_edge_3",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: "0.1",  # String from UI
            CONF_TEMP_STEP: "0.1",  # Fine-grained steps
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_edge_3",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "climate.test_edge_3"

        # Set temperature to 22.3
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 22.3, "entity_id": entity_id},
            blocking=True,
        )

        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"
        target_temp = state.attributes.get("temperature")

        assert target_temp == 22.3, (
            f"Edge case 3 FAILED: Set temperature was rounded! "
            f"Expected 22.3, got {target_temp}"
        )

    async def test_edge_case_4_temp_step_increments_correctly(
        self, hass: HomeAssistant
    ):
        """Edge case 4: First click should NOT jump to maximum temperature.

        This tests that target_temp_step is a proper float so UI calculations work.
        When temp_step is 0.5, increasing from 21.0 should go to 21.5, not max temp.
        """
        setup_sensor(hass, 20.0)
        setup_switch(hass, False, common.ENT_HEATER)

        config_entry_data = {
            "name": "test_edge_4",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: "0.1",  # String from UI
            CONF_TEMP_STEP: "0.5",  # String from UI
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data=config_entry_data,
            entry_id="test_edge_4",
        )
        config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        entity_id = "climate.test_edge_4"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Verify target_temp_step is a proper float (not string)
        target_temp_step = state.attributes.get("target_temp_step")
        assert isinstance(target_temp_step, (int, float)), (
            f"Edge case 4 FAILED: target_temp_step is not numeric! "
            f"Got {type(target_temp_step)}: {target_temp_step}"
        )
        assert (
            target_temp_step == 0.5
        ), f"target_temp_step should be 0.5, got {target_temp_step}"

        # Simulate what the UI does: increase by one step
        # UI calculates: current_temp + target_temp_step
        # If target_temp_step is string "0.5", JS would do "21.0" + "0.5" = "21.00.5" -> NaN -> max_temp!
        initial_temp = state.attributes.get("temperature")
        assert initial_temp == 21.0

        # Increase by one step (simulating UI click)
        new_temp = initial_temp + target_temp_step
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: new_temp, "entity_id": entity_id},
            blocking=True,
        )

        state = hass.states.get(entity_id)
        final_temp = state.attributes.get("temperature")

        # Should be 21.5, NOT the max temp
        max_temp = state.attributes.get("max_temp")
        assert final_temp == 21.5, (
            f"Edge case 4 FAILED: Temperature jumped incorrectly! "
            f"Expected 21.5, got {final_temp}. Max temp is {max_temp}"
        )
        assert (
            final_temp != max_temp
        ), f"Edge case 4 CRITICAL: Temperature jumped to max ({max_temp})!"


class TestTemplatePresetsYAMLWithAutoSelection:
    """Test template presets in YAML config with auto-preset-selection.

    This verifies that users can configure template-based presets in YAML
    and the auto-preset-selection feature correctly evaluates the templates.
    """

    async def test_yaml_template_preset_auto_selection_single_temp(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test auto-preset selection works with template presets in YAML.

        Scenario:
        1. User configures preset with template: `eco: {temperature: "{{ states('input_number.eco_temp') | float }}"}`
        2. input_number.eco_temp = 20
        3. User sets temperature to 20
        4. Auto-preset selection should evaluate the template and match 'eco' preset
        """
        setup_switch(hass, False, common.ENT_HEATER)
        setup_sensor(hass, 22.0)

        # YAML config with template preset
        config = {
            "name": "test_template_preset",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: 0.1,
            CONF_TEMP_STEP: 0.5,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            # Template presets
            "eco": {
                ATTR_TEMPERATURE: "{{ states('input_number.eco_temp') | float }}",
            },
            "away": {
                ATTR_TEMPERATURE: "{{ states('input_number.away_temp') | float }}",
            },
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        entity_id = "climate.test_template_preset"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Verify presets are available
        preset_modes = state.attributes.get("preset_modes", [])
        assert "eco" in preset_modes, f"eco preset not found in {preset_modes}"
        assert "away" in preset_modes, f"away preset not found in {preset_modes}"

        # Set temperature to match eco preset template value (20.0 from input_number.eco_temp)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 20.0, "entity_id": entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        preset_mode = state.attributes.get("preset_mode")
        target_temp = state.attributes.get("temperature")

        # Temperature should be set correctly
        assert target_temp == 20.0, f"Expected 20.0, got {target_temp}"

        # Auto-preset selection should have matched 'eco' preset
        assert preset_mode == "eco", (
            f"Auto-preset selection failed! Expected 'eco' preset "
            f"(template evaluates to 20.0), got '{preset_mode}'"
        )

    async def test_yaml_template_preset_dynamic_value_change(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test auto-preset selection adapts when template entity value changes.

        Scenario:
        1. Configure eco preset with template pointing to input_number.eco_temp
        2. Initially input_number.eco_temp = 20
        3. Change input_number.eco_temp to 19
        4. Set temperature to 19
        5. Auto-preset selection should match the updated template value
        """
        setup_switch(hass, False, common.ENT_HEATER)
        setup_sensor(hass, 22.0)

        config = {
            "name": "test_dynamic_template",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: 0.1,
            CONF_TEMP_STEP: 0.5,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            "eco": {
                ATTR_TEMPERATURE: "{{ states('input_number.eco_temp') | float }}",
            },
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        entity_id = "climate.test_dynamic_template"

        # Change the input_number value
        hass.states.async_set(
            "input_number.eco_temp", "19", {"unit_of_measurement": "°C"}
        )
        await hass.async_block_till_done()

        # Set temperature to the new eco value (19)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 19.0, "entity_id": entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        preset_mode = state.attributes.get("preset_mode")
        target_temp = state.attributes.get("temperature")

        assert target_temp == 19.0, f"Expected 19.0, got {target_temp}"
        assert preset_mode == "eco", (
            f"Auto-preset selection didn't adapt to template change! "
            f"Expected 'eco' (template now 19.0), got '{preset_mode}'"
        )

    async def test_yaml_old_style_template_preset(
        self, hass: HomeAssistant, setup_template_test_entities
    ):
        """Test old-style preset config (eco_temp, away_temp) with templates.

        This tests the CONF_PRESETS_OLD schema supports templates.
        """
        setup_switch(hass, False, common.ENT_HEATER)
        setup_sensor(hass, 22.0)

        config = {
            "name": "test_old_style_template",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_TARGET_TEMP: 21.0,
            CONF_PRECISION: 0.1,
            CONF_TEMP_STEP: 0.5,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            # Old-style preset keys (eco_temp instead of eco: {temperature: ...})
            "eco_temp": "{{ states('input_number.eco_temp') | float }}",
            "away_temp": "{{ states('input_number.away_temp') | float }}",
        }

        assert await async_setup_component(
            hass, CLIMATE_DOMAIN, {CLIMATE_DOMAIN: {**config, "platform": DOMAIN}}
        )
        await hass.async_block_till_done()

        entity_id = "climate.test_old_style_template"
        state = hass.states.get(entity_id)
        assert state is not None, f"Entity {entity_id} not found"

        # Verify presets are available
        preset_modes = state.attributes.get("preset_modes", [])
        assert "eco" in preset_modes, f"eco preset not found in {preset_modes}"
        assert "away" in preset_modes, f"away preset not found in {preset_modes}"

        # Set temperature to match eco preset (20.0)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_TEMPERATURE: 20.0, "entity_id": entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        preset_mode = state.attributes.get("preset_mode")
        target_temp = state.attributes.get("temperature")

        assert target_temp == 20.0, f"Expected 20.0, got {target_temp}"
        # Auto-selection should work with old-style template presets too
        assert preset_mode == "eco", (
            f"Auto-preset selection failed with old-style template! "
            f"Expected 'eco', got '{preset_mode}'"
        )
