"""End-to-end tests for SIMPLE_HEATER system type: config flow → options flow persistence.

This test validates the complete lifecycle for simple_heater systems:
1. User completes config flow with initial settings
2. User opens options flow and sees the correct values pre-filled
3. User changes some settings in options flow
4. Changes persist correctly (in entry.options)
5. Original values are preserved (in entry.data)
6. Reopening options flow shows the updated values
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_FAN,
    CONF_FAN_MODE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.mark.asyncio
async def test_simple_heater_full_config_then_options_flow_persistence(hass):
    """Test complete SIMPLE_HEATER flow: config → options → verify persistence.

    Tests the simple_heater system type with fan feature and tolerance changes.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow - user selects simple heater
    result = await config_flow.async_step_user(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    # Fill in basic simple heater config
    initial_config = {
        CONF_NAME: "Simple Heater Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.3,
    }
    result = await config_flow.async_step_basic(initial_config)

    # Enable fan feature
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )

    # Configure fan
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,  # Simple heater with fan mode off
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "Simple Heater Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data
    assert "features_shown" not in created_data

    # Check actual config is saved
    assert created_data[CONF_NAME] == "Simple Heater Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
    assert created_data[CONF_HEATER] == "switch.heater"
    assert created_data[CONF_COLD_TOLERANCE] == 0.5
    assert created_data[CONF_HOT_TOLERANCE] == 0.3
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data[CONF_FAN_MODE] is False

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="Simple Heater Test",
    )
    config_entry.add_to_hass(hass)

    # ===== STEP 4: Open options flow and verify pre-filled values =====
    options_flow = OptionsFlowHandler(config_entry)
    options_flow.hass = hass

    # Simplified options flow shows runtime tuning directly in init
    result = await options_flow.async_step_init()

    # Should show init form with runtime tuning parameters
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Verify tolerances are pre-filled
    init_schema = result["data_schema"].schema
    cold_tolerance_default = None
    hot_tolerance_default = None
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
            if hasattr(key, "default"):
                cold_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )

    assert cold_tolerance_default == 0.5, "Cold tolerance should be pre-filled!"
    assert hot_tolerance_default == 0.3, "Hot tolerance should be pre-filled!"

    # ===== STEP 5: Change tolerance settings =====
    # Simplified options flow: only runtime tuning parameters
    updated_config = {
        CONF_COLD_TOLERANCE: 0.8,  # CHANGE: was 0.5
        CONF_HOT_TOLERANCE: 0.6,  # CHANGE: was 0.3
    }
    result = await options_flow.async_step_init(updated_config)

    # Since CONF_FAN is configured, proceeds to fan_options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Complete fan options with existing values
    result = await options_flow.async_step_fan_options({})

    # Now should complete
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Check no transient flags
    assert "configure_fan" not in updated_data
    assert "features_shown" not in updated_data

    # Check changed runtime tuning values
    assert updated_data[CONF_COLD_TOLERANCE] == 0.8
    assert updated_data[CONF_HOT_TOLERANCE] == 0.6

    # Check preserved values (feature config unchanged, only runtime tuning)
    assert updated_data[CONF_NAME] == "Simple Heater Test"
    assert updated_data[CONF_HEATER] == "switch.heater"
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_FAN_MODE] is False  # Unchanged from original

    # ===== STEP 7: Reopen and verify updated values shown =====
    config_entry_after = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options={
            CONF_COLD_TOLERANCE: 0.8,
            CONF_HOT_TOLERANCE: 0.6,
        },
        title="Simple Heater Test",
    )
    config_entry_after.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after)
    options_flow2.hass = hass

    result = await options_flow2.async_step_init()

    # Verify updated tolerances are shown in init step
    init_schema2 = result["data_schema"].schema
    cold_tolerance_default2 = None
    hot_tolerance_default2 = None
    for key in init_schema2:
        if hasattr(key, "schema") and key.schema == CONF_COLD_TOLERANCE:
            if hasattr(key, "default"):
                cold_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )

    assert (
        cold_tolerance_default2 == 0.8
    ), "Updated cold_tolerance should be shown in reopened flow!"
    assert (
        hot_tolerance_default2 == 0.6
    ), "Updated hot_tolerance should be shown in reopened flow!"
