"""Tests for feature settings persistence in options flow.

This tests the defect where feature settings (fan, humidity, etc.) are not
pre-filled when reopening the options flow after initial configuration.

Bug: When configuring fan settings in config flow, then opening options flow,
     the fan settings are not pre-filled with existing values.
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    CONF_TARGET_HUMIDITY,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestFanSettingsPersistence:
    """Test fan settings persistence in options flow."""

    async def test_heater_cooler_fan_settings_prefilled_in_options_flow(
        self, mock_hass
    ):
        """Test that fan settings are pre-filled when reopening options flow.

        Scenario:
        1. User configures heater_cooler with fan feature enabled
        2. User saves configuration
        3. User opens options flow
        4. Fan settings should be pre-filled with previous values

        Acceptance: Fan configuration step shows existing values as defaults
        """
        # Simulate existing config entry with fan configured
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test Thermostat",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            # Fan feature previously configured
            CONF_FAN: "switch.fan",
            CONF_FAN_HOT_TOLERANCE: 0.7,
            CONF_FAN_HOT_TOLERANCE_TOGGLE: "switch.fan_toggle",
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Initialize options flow
        result = await flow.async_step_init()
        assert result["type"] == FlowResultType.FORM

        # Proceed through basic step
        result = await flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )

        # Submit basic configuration (will proceed to features automatically)
        result = await flow.async_step_basic({})

        # Should show features step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

        # Enable fan to get to fan configuration
        result = await flow.async_step_features({"configure_fan": True})

        # Should show fan_options configuration step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "fan_options"

        # Verify defaults are pre-filled from existing config
        schema = result["data_schema"].schema

        fan_field_default = None
        fan_hot_tolerance_default = None
        fan_hot_tolerance_toggle_default = None

        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if field_name == CONF_FAN and hasattr(key, "default"):
                    fan_field_default = (
                        key.default() if callable(key.default) else key.default
                    )
                elif field_name == CONF_FAN_HOT_TOLERANCE and hasattr(key, "default"):
                    fan_hot_tolerance_default = (
                        key.default() if callable(key.default) else key.default
                    )
                elif field_name == CONF_FAN_HOT_TOLERANCE_TOGGLE and hasattr(
                    key, "default"
                ):
                    fan_hot_tolerance_toggle_default = (
                        key.default() if callable(key.default) else key.default
                    )

        # Assert that existing values are used as defaults
        assert (
            fan_field_default == "switch.fan"
        ), f"Fan field not pre-filled, got: {fan_field_default}"
        assert (
            fan_hot_tolerance_default == 0.7
        ), f"Fan hot tolerance not pre-filled, got: {fan_hot_tolerance_default}"
        assert (
            fan_hot_tolerance_toggle_default == "switch.fan_toggle"
        ), f"Fan toggle not pre-filled, got: {fan_hot_tolerance_toggle_default}"

    async def test_simple_heater_fan_settings_prefilled_in_options_flow(
        self, mock_hass
    ):
        """Test fan settings persistence for simple_heater system type."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Simple Heater",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_FAN: "switch.fan",
            CONF_FAN_HOT_TOLERANCE: 0.5,
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Navigate to fan configuration
        await flow.async_step_init()
        result = await flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        result = await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_fan": True})

        assert result["step_id"] == "fan_options"

        # Check defaults
        schema = result["data_schema"].schema
        fan_hot_tolerance_default = None

        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
                if hasattr(key, "default"):
                    fan_hot_tolerance_default = (
                        key.default() if callable(key.default) else key.default
                    )
                    break

        assert (
            fan_hot_tolerance_default == 0.5
        ), "Fan hot tolerance not pre-filled for simple_heater"

    async def test_ac_only_fan_settings_prefilled_in_options_flow(self, mock_hass):
        """Test fan settings persistence for ac_only system type."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "AC Only",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.ac",
            CONF_FAN: "switch.fan",
            CONF_FAN_HOT_TOLERANCE: 0.3,
            CONF_FAN_HOT_TOLERANCE_TOGGLE: "switch.ac_fan_toggle",
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        result = await flow.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        result = await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_fan": True})

        assert result["step_id"] == "fan_options"

        schema = result["data_schema"].schema
        defaults = {}

        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if hasattr(key, "default"):
                    defaults[field_name] = (
                        key.default() if callable(key.default) else key.default
                    )

        assert defaults.get(CONF_FAN) == "switch.fan"
        assert defaults.get(CONF_FAN_HOT_TOLERANCE) == 0.3
        assert defaults.get(CONF_FAN_HOT_TOLERANCE_TOGGLE) == "switch.ac_fan_toggle"


class TestHumiditySettingsPersistence:
    """Test humidity settings persistence in options flow."""

    async def test_heater_cooler_humidity_settings_prefilled_in_options_flow(
        self, mock_hass
    ):
        """Test that humidity settings are pre-filled when reopening options flow."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test Thermostat",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            # Humidity feature previously configured
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_TARGET_HUMIDITY: 55.0,
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        result = await flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        result = await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_humidity": True})

        assert result["step_id"] == "humidity_options"

        schema = result["data_schema"].schema
        defaults = {}

        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if hasattr(key, "default"):
                    defaults[field_name] = (
                        key.default() if callable(key.default) else key.default
                    )

        assert defaults.get(CONF_HUMIDITY_SENSOR) == "sensor.humidity"
        assert defaults.get(CONF_TARGET_HUMIDITY) == 55.0

    async def test_simple_heater_humidity_settings_prefilled_in_options_flow(
        self, mock_hass
    ):
        """Test humidity settings persistence for simple_heater system type."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Simple Heater",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_TARGET_HUMIDITY: 45.0,
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        result = await flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        result = await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_humidity": True})

        assert result["step_id"] == "humidity_options"

        schema = result["data_schema"].schema
        target_humidity_default = None

        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_TARGET_HUMIDITY:
                if hasattr(key, "default"):
                    target_humidity_default = (
                        key.default() if callable(key.default) else key.default
                    )
                    break

        assert (
            target_humidity_default == 45.0
        ), "Target humidity not pre-filled for simple_heater"


class TestFeaturePersistenceEdgeCases:
    """Test edge cases for feature persistence."""

    async def test_fan_settings_not_configured_uses_defaults(self, mock_hass):
        """Test that when fan was never configured, schema uses normal defaults."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            # No fan configuration
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        result = await flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        result = await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_fan": True})

        assert result["step_id"] == "fan_options"

        # Should use default value (0.5) not existing config
        schema = result["data_schema"].schema
        fan_hot_tolerance_default = None

        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_HOT_TOLERANCE:
                if hasattr(key, "default"):
                    fan_hot_tolerance_default = (
                        key.default() if callable(key.default) else key.default
                    )
                    break

        # Should be default 0.5, not None or some other value
        assert (
            fan_hot_tolerance_default == 0.5
        ), "Should use default when not previously configured"
