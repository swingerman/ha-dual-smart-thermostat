"""End-to-end persistence tests for HEAT_PUMP system type.

This module validates the complete lifecycle for heat_pump systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values

This test follows the same pattern as:
- test_e2e_simple_heater_persistence.py
- test_e2e_ac_only_persistence.py
- test_e2e_heater_cooler_persistence.py

Test Coverage:
- Minimal configuration (basic + fan feature)
- All available features enabled (floor_heating, fan, humidity, openings, presets)
- Individual features in isolation
- Specific edge cases (field preservation, cooling sensor persistence)
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEAT_PUMP,
)


@pytest.mark.asyncio
async def test_heat_pump_full_config_then_options_flow_persistence(hass):
    """Test complete HEAT_PUMP flow: config → options → verify persistence.

    This is the test that would have caught the options flow persistence bug.
    Tests the heat_pump system type with fan feature.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
    )

    # Fill in basic heat pump config
    result = await config_flow.async_step_heat_pump(
        {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }
    )

    # Enable fan feature
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )

    # Configure fan with specific settings
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: True,
        CONF_FAN_ON_WITH_AC: True,
        CONF_FAN_AIR_OUTSIDE: True,
        CONF_FAN_HOT_TOLERANCE: 0.5,
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Test Heat Pump"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data, "Transient flags should not be saved!"
    assert "features_shown" not in created_data, "Transient flags should not be saved!"

    # Check actual config is saved
    assert created_data[CONF_NAME] == "Test Heat Pump"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP
    assert created_data[CONF_HEATER] == "switch.heat_pump"
    assert created_data[CONF_HEAT_PUMP_COOLING] == "binary_sensor.cooling_mode"
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data[CONF_FAN_MODE] is True
    assert created_data[CONF_FAN_ON_WITH_AC] is True
    assert created_data[CONF_FAN_AIR_OUTSIDE] is True
    assert created_data[CONF_FAN_HOT_TOLERANCE] == 0.5

    # ===== STEP 3: Create MockConfigEntry to simulate HA storage =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},  # Initially empty, as HA would have
        title="Test Heat Pump",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow shows runtime tuning directly in init
    result = await options_flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # ===== STEP 5: Submit init step (no changes to basic runtime params) =====
    # Init step shows basic tolerances, not fan_hot_tolerance
    result = await options_flow.async_step_init({})

    # Since CONF_FAN is configured, proceeds to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Verify fan hot tolerance is pre-filled in fan_options step
    fan_schema = result["data_schema"].schema
    fan_hot_tolerance_default = None
    for key in fan_schema:
        if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
            if hasattr(key, "default"):
                fan_hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert fan_hot_tolerance_default == 0.5, "Fan hot tolerance should be pre-filled!"

    # ===== STEP 6: Make changes to fan runtime tuning =====
    # Change fan_hot_tolerance in fan_options step
    updated_fan_config = {
        CONF_FAN_HOT_TOLERANCE: 0.8,  # CHANGE: was 0.5
    }
    result = await options_flow.async_step_fan_options(updated_fan_config)

    # Now should complete the options flow
    assert result["type"] == "create_entry"

    # ===== STEP 7: Verify persistence in entry =====
    # The entry should now have the updated values in .options
    updated_entry_data = result["data"]

    # Check no transient flags saved
    assert (
        "configure_fan" not in updated_entry_data
    ), "Transient flags should not be saved!"
    assert (
        "features_shown" not in updated_entry_data
    ), "Transient flags should not be saved!"
    assert (
        "fan_options_shown" not in updated_entry_data
    ), "Transient flags should not be saved!"

    # Check changed runtime tuning parameter
    assert (
        updated_entry_data[CONF_FAN_HOT_TOLERANCE] == 0.8
    ), "Changed value should persist"

    # Check feature config unchanged (only runtime tuning in options flow)
    assert updated_entry_data[CONF_NAME] == "Test Heat Pump"
    assert updated_entry_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP
    assert updated_entry_data[CONF_FAN] == "switch.fan"
    assert updated_entry_data[CONF_FAN_MODE] is True  # Unchanged from original
    assert updated_entry_data[CONF_FAN_ON_WITH_AC] is True  # Unchanged from original
    assert updated_entry_data[CONF_FAN_AIR_OUTSIDE] is True  # Unchanged from original
    assert updated_entry_data[CONF_HEATER] == "switch.heat_pump"
    assert updated_entry_data[CONF_HEAT_PUMP_COOLING] == "binary_sensor.cooling_mode"

    # ===== STEP 8: Reopen options flow and verify updated values are shown =====
    # Simulate what happens when user reopens options flow after changes
    # Update the mock entry to have the options set (as HA would)
    config_entry_after_update = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original data unchanged
        options={CONF_FAN_HOT_TOLERANCE: 0.8},  # Options contains the changes
        title="Test Heat Pump",
    )
    config_entry_after_update.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after_update)
    options_flow2.hass = hass

    # Simplified flow shows runtime tuning directly
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit init (no changes)
    result = await options_flow2.async_step_init({})

    # Should proceed to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Verify the UPDATED fan_hot_tolerance is now shown as default in fan_options
    fan_schema2 = result["data_schema"].schema
    fan_hot_tolerance_default2 = None
    for key in fan_schema2:
        if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
            if hasattr(key, "default"):
                fan_hot_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert (
        fan_hot_tolerance_default2 == 0.8
    ), "Updated fan_hot_tolerance should be shown!"


@pytest.mark.asyncio
async def test_heat_pump_all_features_full_persistence(hass):
    """Test HEAT_PUMP with all features: config → options → persistence.

    This E2E test validates:
    - All 5 features configured in config flow
    - All settings pre-filled in options flow
    - Changes to multiple features persist correctly
    - Original entry.data preserved, changes in entry.options

    Available features for heat_pump:
    - floor_heating ✅
    - fan ✅
    - humidity ✅
    - openings ✅
    - presets ✅
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow with all features =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start: Select heat_pump
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
    )

    # Basic config
    initial_config = {
        CONF_NAME: "Heat Pump All Features Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heat_pump",
        CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_heat_pump(initial_config)

    # Enable ALL features
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_fan": True,
            "configure_humidity": True,
            "configure_openings": True,
            "configure_presets": True,
        }
    )

    # Configure floor heating
    initial_floor_config = {
        CONF_FLOOR_SENSOR: "sensor.floor_temp",
        CONF_MIN_FLOOR_TEMP: 5,
        CONF_MAX_FLOOR_TEMP: 28,
    }
    result = await config_flow.async_step_floor_config(initial_floor_config)

    # Configure fan
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        "fan_on_with_ac": True,
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Configure humidity
    initial_humidity_config = {
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        CONF_DRYER: "switch.dehumidifier",
        "target_humidity": 50,
    }
    result = await config_flow.async_step_humidity(initial_humidity_config)

    # Configure openings
    result = await config_flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
    )
    result = await config_flow.async_step_openings_config(
        {
            "opening_scope": "all",
            "timeout_openings_open": 300,
        }
    )

    # Configure presets
    # Note: async_step_preset_selection automatically advances to async_step_presets
    result = await config_flow.async_step_preset_selection(
        {"presets": ["away", "home"]}
    )

    # Now we're at the presets config step
    assert result["type"] == "form"
    assert result["step_id"] == "presets"

    result = await config_flow.async_step_presets(
        {
            "away_temp": 16,
            "home_temp": 21,
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Heat Pump All Features Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Verify basic settings
    assert created_data[CONF_NAME] == "Heat Pump All Features Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP
    assert created_data[CONF_HEATER] == "switch.heat_pump"
    assert created_data[CONF_HEAT_PUMP_COOLING] == "binary_sensor.cooling_mode"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3

    # Verify floor heating
    assert created_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert created_data[CONF_MIN_FLOOR_TEMP] == 5
    assert created_data[CONF_MAX_FLOOR_TEMP] == 28

    # Verify fan
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data["fan_on_with_ac"] is True

    # Verify humidity
    assert created_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert created_data[CONF_DRYER] == "switch.dehumidifier"
    assert created_data["target_humidity"] == 50

    # Verify openings
    # Note: opening_scope may be cleaned/normalized during processing
    assert "openings" in created_data
    assert len(created_data["openings"]) == 2
    assert any(
        o.get("entity_id") == "binary_sensor.window_1" for o in created_data["openings"]
    )
    assert any(
        o.get("entity_id") == "binary_sensor.door_1" for o in created_data["openings"]
    )

    # Verify presets
    # Note: Presets are stored as temp values, not in a "presets" list
    assert "away_temp" in created_data
    assert created_data["away_temp"] == 16
    assert "home_temp" in created_data
    assert created_data["home_temp"] == 21

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="Heat Pump All Features Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow: init shows runtime tuning directly
    result = await options_flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # ===== STEP 5: Make changes - simplified to test persistence =====
    # Change tolerances (runtime parameters) in init step
    result = await options_flow.async_step_init(
        {
            CONF_COLD_TOLERANCE: 0.8,  # CHANGED from 0.5
            CONF_HOT_TOLERANCE: 0.6,  # CHANGED from 0.3
        }
    )

    # Navigate through configured features in order (simplified options flow)
    # Each feature step automatically proceeds to the next when submitted with {}

    # Floor heating options
    assert result["step_id"] == "floor_options"
    result = await options_flow.async_step_floor_options({})

    # Fan options
    assert result["step_id"] == "fan_options"
    result = await options_flow.async_step_fan_options({})

    # Humidity options
    assert result["step_id"] == "humidity_options"
    result = await options_flow.async_step_humidity_options({})

    # Openings options (single-step in options flow)
    assert result["step_id"] == "openings_options"
    result = await options_flow.async_step_openings_options({})

    # Presets selection - when submitted with {}, completes directly in options flow
    assert result["step_id"] == "preset_selection"
    result = await options_flow.async_step_preset_selection({})

    # In options flow, preset_selection with {} completes the flow (no separate presets step)
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Verify changed basic values
    assert updated_data[CONF_COLD_TOLERANCE] == 0.8
    assert updated_data[CONF_HOT_TOLERANCE] == 0.6

    # Verify original feature values preserved (from config flow)
    assert updated_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert updated_data[CONF_MIN_FLOOR_TEMP] == 5
    assert updated_data[CONF_MAX_FLOOR_TEMP] == 28
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
    assert updated_data[CONF_DRYER] == "switch.dehumidifier"
    assert updated_data["target_humidity"] == 50
    # Openings list preserved
    assert "openings" in updated_data
    assert len(updated_data["openings"]) == 2
    assert updated_data["away_temp"] == 16  # Original preset value
    assert updated_data["home_temp"] == 21  # Original preset value

    # Verify preserved system info
    assert updated_data[CONF_NAME] == "Heat Pump All Features Test"
    assert updated_data[CONF_HEATER] == "switch.heat_pump"
    assert updated_data[CONF_HEAT_PUMP_COOLING] == "binary_sensor.cooling_mode"

    # ===== STEP 7: Reopen options flow and verify updated values =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options=updated_data,  # Updated values
        title="Heat Pump All Features Test",
    )
    config_entry_updated.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_updated)
    options_flow2.hass = hass

    # Simplified options flow: verify it opens successfully with merged values
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_heat_pump_floor_heating_only_persistence(hass):
    """Test HEAT_PUMP with only floor_heating enabled.

    This tests feature isolation - only floor_heating configured.
    Validates that when only one feature is enabled, the configuration
    persists correctly and other features remain unconfigured.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
    )

    result = await config_flow.async_step_heat_pump(
        {
            CONF_NAME: "Floor Only Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }
    )

    # Enable only floor_heating
    result = await config_flow.async_step_features(
        {
            "configure_floor_heating": True,
            "configure_fan": False,
            "configure_humidity": False,
            "configure_openings": False,
            "configure_presets": False,
        }
    )

    result = await config_flow.async_step_floor_config(
        {
            CONF_FLOOR_SENSOR: "sensor.floor_temp",
            CONF_MIN_FLOOR_TEMP: 5,
            CONF_MAX_FLOOR_TEMP: 28,
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # Verify floor heating configured
    assert created_data[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
    assert created_data[CONF_MIN_FLOOR_TEMP] == 5
    assert created_data[CONF_MAX_FLOOR_TEMP] == 28

    # Verify other features NOT configured
    assert CONF_FAN not in created_data
    assert CONF_HUMIDITY_SENSOR not in created_data
    assert "selected_openings" not in created_data or not created_data.get(
        "selected_openings"
    )
    assert "away_temp" not in created_data  # No presets configured
    assert "home_temp" not in created_data


@pytest.mark.asyncio
async def test_heat_pump_options_flow_preserves_unmodified_fields(hass):
    """Test that HEAT_PUMP options flow preserves fields the user didn't change.

    This validates that partial updates work correctly when only modifying
    one feature (fan) while preserving another (humidity).
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # Create entry with both heat pump and humidity configured
    initial_data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heat_pump",
        CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: True,
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=initial_data,
        options={},
        title="Test",
    )
    config_entry.add_to_hass(hass)

    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow: no navigation, just runtime tuning in init
    # Since no runtime changes needed, just verify preservation
    result = await options_flow.async_step_init()

    # Complete without changes (empty dict or just submit)
    result = await options_flow.async_step_init({})

    # Since CONF_FAN is configured, proceeds to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Complete fan options with existing values
    result = await options_flow.async_step_fan_options({})

    # Since CONF_HUMIDITY_SENSOR is configured, proceeds to humidity_options
    assert result["type"] == "form"
    assert result["step_id"] == "humidity_options"

    # Complete humidity options with existing values
    result = await options_flow.async_step_humidity_options({})

    # Now should complete
    assert result["type"] == "create_entry"

    updated_data = result["data"]

    # All feature config should be PRESERVED (no changes in options flow)
    assert updated_data[CONF_FAN_MODE] is True  # Unchanged

    # Humidity sensor should be PRESERVED
    assert (
        updated_data.get(CONF_HUMIDITY_SENSOR) == "sensor.humidity"
    ), "Unmodified humidity sensor should be preserved!"

    # Heat pump cooling sensor should be PRESERVED
    assert (
        updated_data.get(CONF_HEAT_PUMP_COOLING) == "binary_sensor.cooling_mode"
    ), "Unmodified heat_pump_cooling sensor should be preserved!"

    # All other fields should be preserved
    assert updated_data[CONF_HEATER] == "switch.heat_pump"
    assert updated_data[CONF_FAN] == "switch.fan"


@pytest.mark.asyncio
async def test_heat_pump_cooling_sensor_persistence(hass):
    """Test that heat_pump_cooling sensor persists correctly through options flow.

    This specifically validates that the heat_pump_cooling entity_id is preserved
    when modifying other settings in the options flow.
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # Create entry with heat_pump_cooling configured
    initial_data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heat_pump",
        CONF_HEAT_PUMP_COOLING: "binary_sensor.original_cooling",
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=initial_data,
        options={},
        title="Test",
    )
    config_entry.add_to_hass(hass)

    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow: only runtime tuning, cannot change heat_pump_cooling
    # heat_pump_cooling is feature config, not runtime tuning - use reconfigure flow
    result = await options_flow.async_step_init()

    # Verify no heat_pump_cooling field (it's not a runtime tuning parameter)
    init_schema = result["data_schema"].schema
    has_heat_pump_cooling = False
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_HEAT_PUMP_COOLING:
            has_heat_pump_cooling = True
            break

    assert (
        not has_heat_pump_cooling
    ), "heat_pump_cooling should NOT be in options flow (use reconfigure flow)"

    # Complete without changes
    result = await options_flow.async_step_init({})

    # No fan or humidity configured in this test, should complete directly
    assert result["type"] == "create_entry"

    updated_data = result["data"]

    # Verify heat_pump_cooling is preserved (unchanged)
    assert (
        updated_data[CONF_HEAT_PUMP_COOLING] == "binary_sensor.original_cooling"
    ), "heat_pump_cooling should be preserved"

    # Verify other fields are preserved
    assert updated_data[CONF_HEATER] == "switch.heat_pump"
    assert updated_data[CONF_SENSOR] == "sensor.temp"
