"""End-to-end tests for AC_ONLY system type: config flow → options flow persistence.

This test validates the complete lifecycle for ac_only systems:
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
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HOT_TOLERANCE,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
)


@pytest.mark.asyncio
async def test_ac_only_full_config_then_options_flow_persistence(hass):
    """Test complete AC_ONLY flow: config → options → verify persistence.

    Tests the ac_only system type with fan feature and tolerance changes.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    # ===== STEP 1: Complete config flow =====
    config_flow = ConfigFlowHandler()
    config_flow.hass = hass

    # Start config flow - user selects AC only
    result = await config_flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    # Fill in basic AC config
    initial_config = {
        CONF_NAME: "AC Only Test",
        CONF_SENSOR: "sensor.room_temp",
        CONF_COOLER: "switch.ac",
        CONF_HOT_TOLERANCE: 0.5,
    }
    result = await config_flow.async_step_basic_ac_only(initial_config)

    # Enable fan feature
    result = await config_flow.async_step_features(
        {
            "configure_fan": True,
        }
    )

    # Configure fan for AC
    initial_fan_config = {
        CONF_FAN: "switch.fan",
        CONF_FAN_MODE: False,
        CONF_FAN_ON_WITH_AC: True,  # Fan runs with AC
    }
    result = await config_flow.async_step_fan(initial_fan_config)

    # Flow should complete
    assert result["type"] == "create_entry"
    assert result["title"] == "AC Only Test"

    # ===== STEP 2: Verify initial config entry =====
    created_data = result["data"]

    # Check no transient flags saved
    assert "configure_fan" not in created_data
    assert "features_shown" not in created_data

    # Check actual config is saved
    assert created_data[CONF_NAME] == "AC Only Test"
    assert created_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_AC_ONLY
    assert created_data[CONF_COOLER] == "switch.ac"
    assert created_data[CONF_HOT_TOLERANCE] == 0.5
    assert created_data[CONF_FAN] == "switch.fan"
    assert created_data[CONF_FAN_MODE] is False
    assert created_data[CONF_FAN_ON_WITH_AC] is True

    # ===== STEP 3: Create MockConfigEntry =====
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,
        options={},
        title="AC Only Test",
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

    # Verify hot tolerance is pre-filled
    init_schema = result["data_schema"].schema
    hot_tolerance_default = None
    for key in init_schema:
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert hot_tolerance_default == 0.5, "Hot tolerance should be pre-filled!"

    # ===== STEP 5: Change hot tolerance =====
    # Simplified options flow: only runtime tuning parameters
    updated_config = {
        CONF_HOT_TOLERANCE: 0.8,  # CHANGE: was 0.5
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

    # Check changed value
    assert updated_data[CONF_HOT_TOLERANCE] == 0.8

    # Check preserved values (feature config unchanged, only runtime tuning)
    assert updated_data[CONF_NAME] == "AC Only Test"
    assert updated_data[CONF_COOLER] == "switch.ac"
    assert updated_data[CONF_FAN] == "switch.fan"
    assert updated_data[CONF_FAN_MODE] is False  # Unchanged from original
    assert updated_data[CONF_FAN_ON_WITH_AC] is True  # Unchanged from original

    # ===== STEP 7: Reopen and verify updated values shown =====
    config_entry_after = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options={
            CONF_HOT_TOLERANCE: 0.8,
        },
        title="AC Only Test",
    )
    config_entry_after.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after)
    options_flow2.hass = hass

    result = await options_flow2.async_step_init()

    # Verify updated hot tolerance is shown in init step
    init_schema2 = result["data_schema"].schema
    hot_tolerance_default2 = None
    for key in init_schema2:
        if hasattr(key, "schema") and key.schema == CONF_HOT_TOLERANCE:
            if hasattr(key, "default"):
                hot_tolerance_default2 = (
                    key.default() if callable(key.default) else key.default
                )
            break

    assert (
        hot_tolerance_default2 == 0.8
    ), "Updated hot_tolerance should be shown in reopened flow!"
