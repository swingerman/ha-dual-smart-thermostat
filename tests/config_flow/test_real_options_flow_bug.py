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
    """Test that options flow shows correct fields with real ConfigEntry.

    This test replicates the bug where transient flags in storage cause
    the options flow to show the wrong system type fields.
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

    # DEBUG: Check what entry.data actually contains
    print(f"DEBUG: entry.data = {entry.data}")
    print(f"DEBUG: entry.data type = {type(entry.data)}")
    print(f"DEBUG: isinstance(entry.data, dict) = {isinstance(entry.data, dict)}")

    result = await flow.async_step_init()

    # Should show the init form (system type selection)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit the init form (keeping same system type)
    result2 = await flow.async_step_init(
        user_input={CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER},
    )

    # Should now show the basic form
    assert result2["type"] == "form"
    assert result2["step_id"] == "basic"

    # Check that the schema is for heater_cooler (not AC)
    # The heater_cooler schema should have both HEATER and COOLER fields
    schema = result2["data_schema"].schema
    field_names = [str(key) for key in schema.keys()]

    # These fields should be present in heater_cooler schema
    assert "heater" in field_names, f"heater field missing! Fields: {field_names}"
    assert "cooler" in field_names, f"cooler field missing! Fields: {field_names}"
    assert (
        "target_sensor" in field_names
    ), f"target_sensor missing! Fields: {field_names}"

    # This field should NOT be present (it's AC-only)
    # If we see AC-only fields, it means the bug is present
    # Note: Need to identify an AC-only field that's not in heater_cooler


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
