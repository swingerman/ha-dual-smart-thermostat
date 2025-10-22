"""Test for fan_mode persistence bug.

Bug Report: When user sets fan_mode to True in config/options flow,
the value is not persisted in collected_config or final config entry.

Steps to reproduce:
1. Complete config flow for heater_cooler with fan enabled
2. Set fan_mode to True
3. Complete the flow
4. Open options flow
5. Navigate to fan settings
6. Observe: fan_mode shows as False (should be True)
7. Set fan_mode to True again
8. Complete options flow
9. Open options flow again
10. Navigate to fan settings
11. Observe: fan_mode shows as False again (DEFECT)
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_MODE,
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
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


class TestFanModePersistenceBug:
    """Test fan_mode persistence through config and options flows."""

    async def test_fan_mode_persists_in_config_flow(self, mock_hass):
        """Test that fan_mode=True is saved in collected_config during config flow.

        This is the first part of the bug - verifying if fan_mode is saved
        after initial configuration.
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
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

    async def test_fan_mode_persists_in_options_flow(self, mock_hass):
        """Test that fan_mode=True is saved in options flow.

        This tests the second part of the bug - when user reopens options flow
        and sets fan_mode=True, it should be saved.
        """
        # Simulate existing config with fan configured but fan_mode=False
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test Thermostat",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: False,  # Previously False
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

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
        assert (
            CONF_FAN_MODE in flow.collected_config
        ), "fan_mode not in collected_config"
        assert (
            flow.collected_config[CONF_FAN_MODE] is True
        ), f"fan_mode should be True, got: {flow.collected_config.get(CONF_FAN_MODE)}"

    async def test_fan_mode_default_is_false_when_not_set(self, mock_hass):
        """Test that fan_mode defaults to False when not explicitly set."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            # fan_mode not in config (never configured)
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

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

    async def test_fan_mode_true_shown_as_default_in_options_flow(self, mock_hass):
        """Test that if fan_mode=True in config, it shows as True in options flow.

        This verifies the schema correctly pre-fills the current value.
        """
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: True,  # Previously set to True
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

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

    async def test_fan_mode_false_when_explicitly_set_to_false(self, mock_hass):
        """Test that fan_mode stays False when explicitly set to False."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
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

    async def test_fan_mode_missing_from_user_input_when_not_changed(self, mock_hass):
        """Test the actual bug: fan_mode not in user_input if user doesn't touch it.

        This simulates what happens in the UI when the user sees fan_mode toggle
        but doesn't change it - voluptuous Optional fields with defaults don't
        get included in user_input unless explicitly changed.
        """
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",  # Fan must be pre-configured
            CONF_FAN_MODE: True,  # Previously True
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

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

        # BUG: fan_mode gets lost because it's not in user_input
        # and collected_config.update() doesn't preserve it
        print(f"collected_config keys: {flow.collected_config.keys()}")
        print(
            f"CONF_FAN_MODE in collected_config: {CONF_FAN_MODE in flow.collected_config}"
        )
        if CONF_FAN_MODE in flow.collected_config:
            print(f"fan_mode value: {flow.collected_config[CONF_FAN_MODE]}")

        # This will FAIL if bug exists - fan_mode should still be True
        assert (
            CONF_FAN_MODE in flow.collected_config
        ), "BUG: fan_mode lost from collected_config"
        assert (
            flow.collected_config[CONF_FAN_MODE] is True
        ), f"BUG: fan_mode should still be True, got: {flow.collected_config.get(CONF_FAN_MODE)}"
