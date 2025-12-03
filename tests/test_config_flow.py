"""Test the Dual Smart Thermostat config flow."""

from unittest.mock import patch

from homeassistant.components.climate import PRESET_AWAY
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_PRESETS,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
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

        # Submit system type to move to the basic step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
        )
        assert result["type"] == "form"
        # Submit basic data (only fields accepted by basic step)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My Dual Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            },
        )
        assert result["type"] == "form"
        # The features step is unified across system types and now uses 'features'
        assert result["step_id"] == "features"

        # Submit AC-only features decision: don't configure presets -> finish
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"configure_presets": False}
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

    # Move to basic step first
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
    )

    # Test that the schema validation catches wrong domain for sensor
    # This should raise an exception because schema validation fails
    with pytest.raises(Exception) as exc_info:
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My Dual Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "switch.heater",  # Wrong domain for sensor
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
            },
        )
    # Should contain information about the schema validation error
    assert "target_sensor" in str(exc_info.value) or "expected ['sensor']" in str(
        exc_info.value
    )


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
        # Move to basic step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
        )
        # Basic config
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "My Dual Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            },
        )

        # Request presets to be configured in AC-only features
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"configure_presets": True}
        )
        assert result["step_id"] == "preset_selection"

        # Select the away preset using multi-select format
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={"presets": [PRESET_AWAY]}
        )
        assert result["step_id"] == "presets"

        # Configure the away preset temperature (preset key uses '<preset>_temp')
        # Note: TextSelector expects string values
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={f"{CONF_PRESETS[PRESET_AWAY]}_temp": "18"}
        )
        assert result["type"] == "create_entry"

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    # For config flow, selected presets are stored as a list and temps under '<preset>_temp'
    assert "presets" in config_entry.data
    assert CONF_PRESETS[PRESET_AWAY] in config_entry.data["presets"]
    # Stored as string in config
    assert config_entry.data[f"{CONF_PRESETS[PRESET_AWAY]}_temp"] == "18"


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
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from custom_components.dual_smart_thermostat.const import CONF_TARGET_TEMP

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: "Test Thermostat",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
                CONF_SENSOR: "sensor.temperature",
                CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
                CONF_TARGET_TEMP: 22.0,
            },
            options={},
            entry_id="test_id",
        )
        config_entry.add_to_hass(hass)

        # Start options flow via hass helper
        result = await hass.config_entries.options.async_init(config_entry.entry_id)
        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # In simplified options flow, init step shows runtime tuning parameters
        # Submit runtime parameters (no advanced settings since none configured)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
            },
        )

        # Flow completes directly if no features are configured
        assert result["type"] == "create_entry"
