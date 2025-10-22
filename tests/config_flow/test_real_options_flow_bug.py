"""Test that reproduces the real options flow bug with transient flags.

This test uses real Home Assistant fixtures instead of Mocks to replicate
the runtime behavior.
"""

from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
)


@pytest.mark.asyncio
async def test_options_flow_with_real_config_entry(hass):
    """Test that options flow works correctly with real ConfigEntry and transient flags.

    This test verifies that transient flags in storage are properly filtered out
    and don't affect the options flow. The simplified options flow shows runtime
    tuning parameters in init, then proceeds through feature option steps.
    """
    # Create a config entry with transient flags (simulating contaminated storage)
    config_data = {
        CONF_NAME: "Test HC",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_FAN: "switch.fan",
        # These transient flags should NOT affect the options flow
        "features_shown": True,
        "configure_fan": True,
        "fan_options_shown": True,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="Test HC",
    )
    entry.add_to_hass(hass)

    # Open the options flow using the correct Home Assistant API
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    flow = OptionsFlowHandler(entry)
    flow.hass = hass

    # Simplified options flow shows runtime tuning parameters in init step
    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit with runtime parameter changes
    result2 = await flow.async_step_init(
        user_input={"cold_tolerance": 0.5, "hot_tolerance": 0.5},
    )

    # Since fan is configured, should proceed to fan_options step
    assert result2["type"] == "form"
    assert result2["step_id"] == "fan_options"

    # Complete fan options step
    result3 = await flow.async_step_fan_options({})

    # Should now complete since no other features are configured
    assert result3["type"] == "create_entry"

    # Verify transient flags were filtered out from final data
    final_data = result3["data"]
    print(f"DEBUG: final_data keys = {list(final_data.keys())}")
    print(f"DEBUG: has features_shown = {'features_shown' in final_data}")
    print(f"DEBUG: has configure_fan = {'configure_fan' in final_data}")
    print(f"DEBUG: has fan_options_shown = {'fan_options_shown' in final_data}")

    assert (
        "features_shown" not in final_data
    ), f"features_shown still in data! Keys: {list(final_data.keys())}"
    assert (
        "configure_fan" not in final_data
    ), f"configure_fan still in data! Keys: {list(final_data.keys())}"
    assert (
        "fan_options_shown" not in final_data
    ), f"fan_options_shown still in data! Keys: {list(final_data.keys())}"

    # Verify real config is preserved
    assert final_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert final_data[CONF_HEATER] == "switch.heater"
    assert final_data[CONF_COOLER] == "switch.cooler"
    assert final_data[CONF_FAN] == "switch.fan"


@pytest.mark.asyncio
async def test_config_flow_does_not_save_transient_flags(hass):
    """Test that ConfigFlow strips transient flags before saving."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    # Start the config flow
    result = await flow.async_step_user(
        user_input={CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    # Fill in basic config
    result = await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )

    # Skip features
    result = await flow.async_step_features({})

    # Should complete
    assert result["type"] == "create_entry"

    # Check that the saved data does NOT contain transient flags
    saved_data = result["data"]
    assert "features_shown" not in saved_data, "features_shown should not be saved!"
    assert "configure_fan" not in saved_data, "configure_fan should not be saved!"
    assert (
        "fan_options_shown" not in saved_data
    ), "fan_options_shown should not be saved!"
    assert (
        "system_type_changed" not in saved_data
    ), "system_type_changed should not be saved!"

    # But it should have the real config
    assert saved_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert saved_data[CONF_HEATER] == "switch.heater"
    assert saved_data[CONF_COOLER] == "switch.cooler"
