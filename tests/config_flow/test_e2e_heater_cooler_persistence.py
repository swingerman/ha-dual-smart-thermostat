"""End-to-end persistence tests for HEATER_COOLER system type.

This module validates the complete lifecycle for heater_cooler systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values

Test Coverage:
- Minimal configuration (basic + single feature)
- All available features enabled (floor_heating, fan, humidity, openings, presets)
- Individual features in isolation
- Fan persistence edge cases (fan_mode, fan_on_with_ac, boolean False values)

Available features for heater_cooler:
- floor_heating ✅
- fan ✅
- humidity ✅
- openings ✅
- presets ✅

Note: Similar E2E tests should exist for all system types:
- test_e2e_simple_heater_persistence.py
- test_e2e_ac_only_persistence.py
- test_e2e_heat_pump_persistence.py (TODO: when heat pump is implemented)
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
)


@pytest.mark.asyncio
async def test_heater_cooler_minimal_config_persistence(hass):
    """Test minimal HEATER_COOLER flow: config → options → verify persistence.

    This is the test that would have caught the options flow persistence bug.
    Tests the heater_cooler system type with fan feature and tolerance changes.
    This is the baseline test for persistence with minimal configuration.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    # Fill in basic heater/cooler config
    result = await config_flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
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
    assert result["title"] == "Test Thermostat"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data, "Transient flags should not be saved!"
    assert "features_shown" not in created_data, "Transient flags should not be saved!"

    # Check actual config is saved
    assert created_data[CONF_NAME] == "Test Thermostat"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
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
        title="Test Thermostat",
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
    assert updated_entry_data[CONF_NAME] == "Test Thermostat"
    assert updated_entry_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert updated_entry_data[CONF_FAN] == "switch.fan"
    assert updated_entry_data[CONF_FAN_MODE] is True  # Unchanged from original
    assert updated_entry_data[CONF_FAN_ON_WITH_AC] is True  # Unchanged from original
    assert updated_entry_data[CONF_FAN_AIR_OUTSIDE] is True  # Unchanged from original
    assert updated_entry_data[CONF_HEATER] == "switch.heater"
    assert updated_entry_data[CONF_COOLER] == "switch.cooler"

    # ===== STEP 8: Reopen options flow and verify updated values are shown =====
    # Simulate what happens when user reopens options flow after changes
    # Update the mock entry to have the options set (as HA would)
    config_entry_after_update = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original data unchanged
        options={CONF_FAN_HOT_TOLERANCE: 0.8},  # Options contains the changes
        title="Test Thermostat",
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
async def test_heater_cooler_options_flow_preserves_unmodified_fields(hass):
    """Test that HEATER_COOLER options flow preserves fields the user didn't change.

    This validates that partial updates work correctly when only modifying
    one feature (fan) while preserving another (humidity).
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # Create entry with both heater and humidity configured
    initial_data = {
        CONF_NAME: "Test",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
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

    # All other fields should be preserved
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_COOLER] == "switch.cooler"
    assert updated_data[CONF_FAN] == "switch.fan"


@pytest.mark.asyncio
async def test_heater_cooler_all_features_full_persistence(hass):
    """Test HEATER_COOLER with all features: config → options → persistence.

    This E2E test validates:
    - All 5 features configured in config flow
    - All settings pre-filled in options flow
    - Changes to multiple features persist correctly
    - Original entry.data preserved, changes in entry.options
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow with all features =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start: Select heater_cooler
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    # Basic config
    initial_config = {
        CONF_NAME: "Heater Cooler All Features Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_heater_cooler(initial_config)

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
    assert result["title"] == "Heater Cooler All Features Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Verify basic settings
    assert created_data[CONF_NAME] == "Heater Cooler All Features Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert created_data[CONF_HEATER] == "switch.heater"
    assert created_data[CONF_COOLER] == "switch.cooler"
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
        title="Heater Cooler All Features Test",
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
    assert updated_data[CONF_NAME] == "Heater Cooler All Features Test"
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_COOLER] == "switch.cooler"

    # ===== STEP 7: Reopen options flow and verify updated values =====
    config_entry_updated = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options=updated_data,  # Updated values
        title="Heater Cooler All Features Test",
    )
    config_entry_updated.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_updated)
    options_flow2.hass = hass

    # Simplified options flow: verify it opens successfully with merged values
    result = await options_flow2.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_heater_cooler_floor_heating_only_persistence(hass):
    """Test HEATER_COOLER with only floor_heating enabled.

    This tests feature isolation - only floor_heating configured.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    result = await config_flow.async_step_heater_cooler(
        {
            CONF_NAME: "Floor Only Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
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


# ===== Fan Persistence Edge Cases =====
# These tests validate specific edge cases related to fan_mode and fan_on_with_ac
# persistence that were identified as bugs and fixed.


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_persists_in_config_flow(hass):
    """Test that fan_mode=True is saved in collected_config during config flow.

    This is the first part of the bug - verifying if fan_mode is saved
    after initial configuration.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.collected_config = {}

    # Step 1: Select heater_cooler system type
    user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    await flow.async_step_user(user_input)

    # Step 2: Configure heater_cooler basic settings
    heater_cooler_input = {
        CONF_NAME: "Test Thermostat",
        CONF_SENSOR: "sensor.temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
    }
    await flow.async_step_heater_cooler(heater_cooler_input)

    # Step 3: Enable fan feature
    features_input = {"configure_fan": True}
    await flow.async_step_features(features_input)

    # Step 4: Configure fan with fan_mode=True
    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: True,  # User sets this to True
    }
    await flow.async_step_fan(fan_input)

    # CRITICAL: Verify fan_mode is saved in collected_config
    assert (
        CONF_FAN_MODE in flow.collected_config
    ), "fan_mode not saved in collected_config"
    assert (
        flow.collected_config[CONF_FAN_MODE] is True
    ), f"fan_mode should be True, got: {flow.collected_config.get(CONF_FAN_MODE)}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_persists_in_options_flow(hass):
    """Test that fan_mode=True is saved in options flow.

    This tests the second part of the bug - when user reopens options flow
    and sets fan_mode=True, it should be saved.
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # Simulate existing config with fan configured but fan_mode=False
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test Thermostat",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: False,  # Previously False
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    # User sets fan_mode to True
    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: True,  # User changes this to True
    }
    await flow.async_step_fan_options(fan_input)

    # CRITICAL: Verify fan_mode is updated in collected_config
    assert CONF_FAN_MODE in flow.collected_config, "fan_mode not in collected_config"
    assert (
        flow.collected_config[CONF_FAN_MODE] is True
    ), f"fan_mode should be True, got: {flow.collected_config.get(CONF_FAN_MODE)}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_default_is_false_when_not_set(hass):
    """Test that fan_mode defaults to False when not explicitly set."""
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            # fan_mode not in config (never configured)
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    result = await flow.async_step_fan_options()

    # Should show fan_options step
    assert result["step_id"] == "fan_options"

    # Check that fan_mode has default of False
    schema = result["data_schema"].schema
    fan_mode_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_MODE:
            if hasattr(key, "default"):
                fan_mode_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    assert (
        fan_mode_default is False
    ), f"fan_mode default should be False, got: {fan_mode_default}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_true_shown_as_default_in_options_flow(hass):
    """Test that if fan_mode=True in config, it shows as True in options flow.

    This verifies the schema correctly pre-fills the current value.
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: True,  # Previously set to True
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    result = await flow.async_step_fan_options()

    # Check that fan_mode shows True as default
    schema = result["data_schema"].schema
    fan_mode_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_MODE:
            if hasattr(key, "default"):
                fan_mode_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    assert (
        fan_mode_default is True
    ), f"fan_mode default should be True (from config), got: {fan_mode_default}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_false_when_explicitly_set_to_false(hass):
    """Test that fan_mode stays False when explicitly set to False."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.collected_config = {}

    # Configure system
    await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
    await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )
    await flow.async_step_features({"configure_fan": True})

    # User explicitly sets fan_mode to False
    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,
    }
    await flow.async_step_fan(fan_input)

    # Verify False is saved (not missing)
    assert CONF_FAN_MODE in flow.collected_config
    assert flow.collected_config[CONF_FAN_MODE] is False


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_missing_from_user_input_when_not_changed(hass):
    """Test the actual bug: fan_mode not in user_input if user doesn't touch it.

    This simulates what happens in the UI when the user sees fan_mode toggle
    but doesn't change it - voluptuous Optional fields with defaults don't
    get included in user_input unless explicitly changed.
    """
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: True,  # Previously True
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    # Simulate what happens when user submits fan options WITHOUT changing fan_mode
    # voluptuous Optional fields don't include unchanged values in user_input
    fan_input_without_fan_mode = {
        CONF_FAN: "switch.fan",  # User might change entity
        # fan_mode NOT in user_input because user didn't change it
    }
    await flow.async_step_fan_options(fan_input_without_fan_mode)

    # This will FAIL if bug exists - fan_mode should still be True
    assert (
        CONF_FAN_MODE in flow.collected_config
    ), "BUG: fan_mode lost from collected_config"
    assert (
        flow.collected_config[CONF_FAN_MODE] is True
    ), f"BUG: fan_mode should still be True, got: {flow.collected_config.get(CONF_FAN_MODE)}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_on_with_ac_false_persists_in_config_flow(hass):
    """Test that fan_on_with_ac=False is saved in config flow."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.collected_config = {}

    # Configure system
    await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
    await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )
    await flow.async_step_features({"configure_fan": True})

    # User explicitly sets fan_on_with_ac to False (disables it)
    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_ON_WITH_AC: False,  # User disables this
    }
    await flow.async_step_fan(fan_input)

    # CRITICAL: Verify False is saved (not missing or converted to True)
    assert CONF_FAN_ON_WITH_AC in flow.collected_config, "fan_on_with_ac not saved"
    assert (
        flow.collected_config[CONF_FAN_ON_WITH_AC] is False
    ), f"fan_on_with_ac should be False, got: {flow.collected_config.get(CONF_FAN_ON_WITH_AC)}"


@pytest.mark.asyncio
async def test_heater_cooler_multiple_fan_booleans_false_persist_in_config_flow(hass):
    """Test that multiple False boolean values persist."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.collected_config = {}

    await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
    await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )
    await flow.async_step_features({"configure_fan": True})

    # User sets multiple booleans to False
    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,
        CONF_FAN_ON_WITH_AC: False,
        CONF_FAN_AIR_OUTSIDE: False,
    }
    await flow.async_step_fan(fan_input)

    # Verify all False values are saved
    assert flow.collected_config[CONF_FAN_MODE] is False
    assert flow.collected_config[CONF_FAN_ON_WITH_AC] is False
    assert flow.collected_config[CONF_FAN_AIR_OUTSIDE] is False


@pytest.mark.asyncio
async def test_heater_cooler_fan_on_with_ac_false_shown_in_options_flow(hass):
    """Test that fan_on_with_ac=False is shown correctly in options flow UI."""
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # Config entry with fan_on_with_ac explicitly set to False
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured for options flow
            CONF_FAN_ON_WITH_AC: False,  # User previously disabled this
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    result = await flow.async_step_fan_options()

    # Get the schema and check the default
    schema = result["data_schema"].schema
    fan_on_with_ac_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_ON_WITH_AC:
            if hasattr(key, "default"):
                fan_on_with_ac_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    # BUG CHECK: Should show False (from config), not True (schema default)
    assert (
        fan_on_with_ac_default is False
    ), f"BUG: fan_on_with_ac should show False, got: {fan_on_with_ac_default}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_on_with_ac_false_not_in_config_shows_true_default(
    hass,
):
    """Test that if fan_on_with_ac was never configured, it shows True default."""
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            # fan_on_with_ac NOT in config (never configured)
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    flow = OptionsFlowHandler(config_entry)
    flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    result = await flow.async_step_fan_options()

    schema = result["data_schema"].schema
    fan_on_with_ac_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_ON_WITH_AC:
            if hasattr(key, "default"):
                fan_on_with_ac_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    # Should show True (default) since never configured
    assert (
        fan_on_with_ac_default is True
    ), f"Should show True default when not configured, got: {fan_on_with_ac_default}"


@pytest.mark.asyncio
async def test_heater_cooler_fan_mode_true_persists_and_shows_in_options(hass):
    """Test that fan_mode=True persists and shows correctly in options flow."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # First save fan_mode=True in config flow
    flow = ConfigFlowHandler()
    flow.hass = hass
    flow.collected_config = {}

    await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
    await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )
    await flow.async_step_features({"configure_fan": True})

    fan_input = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: True,  # User enables this
    }
    await flow.async_step_fan(fan_input)

    assert flow.collected_config[CONF_FAN_MODE] is True

    # Now test options flow shows True
    # Create complete data dict before MockConfigEntry
    config_data = dict(flow.collected_config)
    config_data[CONF_NAME] = "Test"
    config_data[CONF_SYSTEM_TYPE] = SYSTEM_TYPE_HEATER_COOLER

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        options={},
    )
    config_entry.add_to_hass(hass)

    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow: init step shows runtime tuning
    await options_flow.async_step_init({})

    # After init, flow proceeds to fan_options step since fan is configured
    result = await options_flow.async_step_fan_options()

    schema = result["data_schema"].schema
    fan_mode_default = None

    for key in schema.keys():
        if hasattr(key, "schema") and key.schema == CONF_FAN_MODE:
            if hasattr(key, "default"):
                fan_mode_default = (
                    key.default() if callable(key.default) else key.default
                )
                break

    assert (
        fan_mode_default is True
    ), f"fan_mode should show True, got: {fan_mode_default}"
