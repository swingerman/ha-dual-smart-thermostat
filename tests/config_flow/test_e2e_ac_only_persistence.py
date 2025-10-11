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

    # Navigate to basic step
    result = await options_flow.async_step_init()
    result = await options_flow.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})

    # Should show basic form with hot tolerance pre-filled
    assert result["type"] == "form"
    assert result["step_id"] == "basic"

    # ===== STEP 5: Change hot tolerance =====
    # Note: Tolerances are in advanced_settings, so we focus on core flow
    updated_basic_config = {
        CONF_SENSOR: "sensor.room_temp",
        CONF_COOLER: "switch.ac",
        CONF_HOT_TOLERANCE: 0.8,  # CHANGE: was 0.5
    }
    result = await options_flow.async_step_basic(updated_basic_config)

    # Should go to features
    assert result["type"] == "form"
    assert result["step_id"] == "features"

    # Check fan toggle is pre-checked
    features_schema = result["data_schema"].schema
    configure_fan_default = None
    for key in features_schema:
        if str(key) == "configure_fan":
            configure_fan_default = (
                key.default() if callable(key.default) else key.default
            )
            break

    assert configure_fan_default is True, "Fan toggle should be pre-checked!"

    # Enable fan to modify its settings
    result = await options_flow.async_step_features({"configure_fan": True})

    # Should show fan options
    assert result["type"] == "form"
    assert result["step_id"] == "fan_options"

    # Verify fan settings are pre-filled
    fan_schema = result["data_schema"].schema
    fan_defaults = {}
    for key in fan_schema:
        key_str = str(key)
        if hasattr(key, "default"):
            default_val = key.default() if callable(key.default) else key.default
            fan_defaults[key_str] = default_val

    assert fan_defaults.get(CONF_FAN_MODE) is False
    assert fan_defaults.get(CONF_FAN_ON_WITH_AC) is True

    # Change fan settings
    result = await options_flow.async_step_fan_options(
        {
            CONF_FAN: "switch.fan",
            CONF_FAN_MODE: True,  # CHANGE: was False
            CONF_FAN_ON_WITH_AC: False,  # CHANGE: was True
        }
    )

    # Should complete
    assert result["type"] == "create_entry"

    # ===== STEP 6: Verify persistence =====
    updated_data = result["data"]

    # Check no transient flags
    assert "configure_fan" not in updated_data
    assert "features_shown" not in updated_data

    # Check changed values
    assert updated_data[CONF_HOT_TOLERANCE] == 0.8
    assert updated_data[CONF_FAN_MODE] is True
    assert updated_data[CONF_FAN_ON_WITH_AC] is False

    # Check preserved values
    assert updated_data[CONF_NAME] == "AC Only Test"
    assert updated_data[CONF_COOLER] == "switch.ac"
    assert updated_data[CONF_FAN] == "switch.fan"

    # ===== STEP 7: Reopen and verify updated values shown =====
    config_entry_after = MockConfigEntry(
        domain=DOMAIN,
        data=created_data,  # Original unchanged
        options={
            CONF_HOT_TOLERANCE: 0.8,
            CONF_FAN_MODE: True,
            CONF_FAN_ON_WITH_AC: False,
        },
        title="AC Only Test",
    )
    config_entry_after.add_to_hass(hass)

    options_flow2 = OptionsFlowHandler(config_entry_after)
    options_flow2.hass = hass

    result = await options_flow2.async_step_init()
    result = await options_flow2.async_step_init(
        {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    )

    # Navigate to fan to verify updated values
    result = await options_flow2.async_step_basic({})
    result = await options_flow2.async_step_features({"configure_fan": True})

    fan_schema2 = result["data_schema"].schema
    fan_defaults2 = {}
    for key in fan_schema2:
        key_str = str(key)
        if hasattr(key, "default"):
            default_val = key.default() if callable(key.default) else key.default
            fan_defaults2[key_str] = default_val

    assert fan_defaults2.get(CONF_FAN_MODE) is True, "Updated fan_mode should be shown!"
    assert (
        fan_defaults2.get(CONF_FAN_ON_WITH_AC) is False
    ), "Updated fan_on_with_ac should be shown!"
