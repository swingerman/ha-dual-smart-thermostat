"""Test the Dual Smart Thermostat config flow."""

from unittest.mock import patch

from homeassistant.components.climate import PRESET_AWAY
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.const import (
    CONF_AC_MODE,
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_PRESETS,
    CONF_SENSOR,
    DOMAIN,
)


async def test_config_flow_basic(hass: HomeAssistant) -> None:
    """Test the basic config flow."""
    with patch(
        "custom_components.dual_smart_thermostat.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        # Test the first step with basic config
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My Dual Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_AC_MODE: False,
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
            },
        )
        assert result["type"] == "form"
        assert result["step_id"] == "additional"

        # Skip additional step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "advanced"

        # Skip advanced step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "presets"

        # Skip presets step and create entry
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["type"] == "create_entry"
        assert result["title"] == "My Dual Thermostat"

        await hass.async_block_till_done()

    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.title == "My Dual Thermostat"


async def test_config_flow_validation_errors(hass: HomeAssistant) -> None:
    """Test that validation errors are handled properly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # Test same heater and sensor
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Dual Thermostat",
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "switch.heater",  # Same as heater
            CONF_AC_MODE: False,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        },
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"]["base"] == "same_heater_sensor"


async def test_config_flow_with_presets(hass: HomeAssistant) -> None:
    """Test the config flow with presets."""
    with patch(
        "custom_components.dual_smart_thermostat.async_setup_entry",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        # Basic config
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My Dual Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_AC_MODE: False,
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
            },
        )

        # Skip additional step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["step_id"] == "advanced"

        # Skip advanced step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )
        assert result["step_id"] == "presets"

        # Add presets
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_PRESETS[PRESET_AWAY]: 18.0,
            },
        )
        assert result["type"] == "create_entry"

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert CONF_PRESETS[PRESET_AWAY] in config_entry.options
    assert config_entry.options[CONF_PRESETS[PRESET_AWAY]] == 18.0


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow."""
    # Create a config entry
    config_entry = (
        hass.config_entries.async_entries(DOMAIN)[0]
        if hass.config_entries.async_entries(DOMAIN)
        else None
    )

    if not config_entry:
        # Create a mock config entry for the test
        from homeassistant.config_entries import ConfigEntry

        config_entry = ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="Test Thermostat",
            data={},
            options={
                CONF_NAME: "Test Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            },
            entry_id="test_id",
            source=SOURCE_USER,
        )
        config_entry.add_to_hass(hass)

    # Test options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Test configuring options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_AC_MODE: True,
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
        },
    )
    assert result["type"] == "form"
    assert result["step_id"] == "additional"
