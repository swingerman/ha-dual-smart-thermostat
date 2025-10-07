"""End-to-end tests for HEATER_COOLER system type: config flow → options flow persistence.

This test validates the complete lifecycle for heater_cooler systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values

Note: Similar E2E tests should exist for all system types:
- test_e2e_simple_heater_persistence.py
- test_e2e_ac_only_persistence.py
- test_e2e_heat_pump_persistence.py (TODO: when heat pump is implemented)
- test_e2e_dual_stage_persistence.py (TODO: if needed)
- test_e2e_floor_heating_persistence.py (TODO: if needed)
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
)


@pytest.mark.asyncio
async def test_heater_cooler_full_config_then_options_flow_persistence(hass):
    """Test complete HEATER_COOLER flow: config → options → verify persistence.

    This is the test that would have caught the options flow persistence bug.
    Tests the heater_cooler system type with fan feature.
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

    # Step through options flow to get to fan configuration
    result = await options_flow.async_step_init()
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await options_flow.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "basic"

    result = await options_flow.async_step_basic({})
    assert result["type"] == "form"
    assert result["step_id"] == "features"

    # Check that fan toggle is pre-checked (because fan is configured)
    features_schema = result["data_schema"].schema
    configure_fan_field = None
    for key in features_schema:
        if str(key) == "configure_fan":
            configure_fan_field = key
            break

    assert configure_fan_field is not None, "configure_fan field should exist"
    configure_fan_default = (
        configure_fan_field.default()
        if callable(configure_fan_field.default)
        else configure_fan_field.default
    )
    assert configure_fan_default is True, "Fan toggle should be pre-checked!"

    # Continue to fan options
    result = await options_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Verify fan options are pre-filled with original values
    fan_schema = result["data_schema"].schema
    fan_defaults = {}
    for key in fan_schema:
        key_str = str(key)
        if hasattr(key, "default"):
            default_val = key.default() if callable(key.default) else key.default
            fan_defaults[key_str] = default_val

    # These should match the initial config
    assert fan_defaults.get(CONF_FAN) == "switch.fan"
    assert fan_defaults.get(CONF_FAN_MODE) is True
    assert fan_defaults.get(CONF_FAN_ON_WITH_AC) is True
    assert fan_defaults.get(CONF_FAN_AIR_OUTSIDE) is True
    assert fan_defaults.get(CONF_FAN_HOT_TOLERANCE) == 0.5

    # ===== STEP 5: Make changes to fan settings =====
    updated_fan_config = {
        CONF_FAN: "switch.fan",  # Keep same
        CONF_FAN_MODE: False,  # CHANGE: was True
        CONF_FAN_ON_WITH_AC: False,  # CHANGE: was True
        CONF_FAN_AIR_OUTSIDE: False,  # CHANGE: was True
        CONF_FAN_HOT_TOLERANCE: 0.8,  # CHANGE: was 0.5
    }
    result = await options_flow.async_step_fan_options(updated_fan_config)

    # Should complete the options flow
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence in entry =====
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

    # Check changed values are in the result
    assert updated_entry_data[CONF_FAN_MODE] is False, "Changed value should persist"
    assert (
        updated_entry_data[CONF_FAN_ON_WITH_AC] is False
    ), "Changed value should persist"
    assert (
        updated_entry_data[CONF_FAN_AIR_OUTSIDE] is False
    ), "Changed value should persist"
    assert (
        updated_entry_data[CONF_FAN_HOT_TOLERANCE] == 0.8
    ), "Changed value should persist"

    # Check unchanged values are preserved
    assert updated_entry_data[CONF_NAME] == "Test Thermostat"
    assert updated_entry_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert updated_entry_data[CONF_FAN] == "switch.fan"
    assert updated_entry_data[CONF_HEATER] == "switch.heater"
    assert updated_entry_data[CONF_COOLER] == "switch.cooler"

    # ===== STEP 7: Reopen options flow and verify updated values are shown =====
    # Simulate what happens when user reopens options flow after changes
    # Update the mock entry to have the options set (as HA would)
    config_entry_after_update = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original data unchanged
        options=updated_fan_config,  # Options contains the changes
        title="Test Thermostat",
    )
    config_entry_after_update.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after_update)
    options_flow2.hass = hass

    # Navigate to fan options again
    result = await options_flow2.async_step_init()
    result = await options_flow2.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )
    result = await options_flow2.async_step_basic({})
    result = await options_flow2.async_step_features({"configure_fan": True})

    # Verify the UPDATED values are now shown as defaults
    fan_schema2 = result["data_schema"].schema
    fan_defaults2 = {}
    for key in fan_schema2:
        key_str = str(key)
        if hasattr(key, "default"):
            default_val = key.default() if callable(key.default) else key.default
            fan_defaults2[key_str] = default_val

    # These should match the UPDATED config from options flow
    assert fan_defaults2.get(CONF_FAN_MODE) is False, "Updated value should be shown!"
    assert (
        fan_defaults2.get(CONF_FAN_ON_WITH_AC) is False
    ), "Updated value should be shown!"
    assert (
        fan_defaults2.get(CONF_FAN_AIR_OUTSIDE) is False
    ), "Updated value should be shown!"
    assert (
        fan_defaults2.get(CONF_FAN_HOT_TOLERANCE) == 0.8
    ), "Updated value should be shown!"


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

    # Navigate through options flow and only modify fan, not humidity
    result = await options_flow.async_step_init()
    result = await options_flow.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )
    result = await options_flow.async_step_basic({})
    result = await options_flow.async_step_features(
        {
            "configure_fan": True,  # Only configure fan, not humidity
        }
    )

    # Change fan mode
    result = await options_flow.async_step_fan_options(
        {
            CONF_FAN: "switch.fan",
            CONF_FAN_MODE: False,  # Changed from True
        }
    )

    # Since humidity is configured, it will show humidity options
    # Skip through it without changes
    if result["type"] == "form" and result["step_id"] == "humidity_options":
        result = await options_flow.async_step_humidity_options({})

    # Now should complete
    assert result["type"] == "create_entry"

    updated_data = result["data"]

    # Fan mode should be changed
    assert updated_data[CONF_FAN_MODE] is False

    # Humidity sensor should be PRESERVED even though we didn't configure it
    assert (
        updated_data.get(CONF_HUMIDITY_SENSOR) == "sensor.humidity"
    ), "Unmodified humidity sensor should be preserved!"

    # All other fields should be preserved
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_COOLER] == "switch.cooler"
