"""Test for boolean False value persistence in fan settings.

Bug hypothesis: When user sets fan_on_with_ac=False or fan_mode=False,
the value might not be saved to the config entry, causing it to revert
to the default (True for fan_on_with_ac, False for fan_mode) when
reopening the options flow.
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
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


class TestFanBooleanFalsePersistence:
    """Test that boolean False values are persisted correctly."""

    async def test_fan_on_with_ac_false_persists_in_config_flow(self, mock_hass):
        """Test that fan_on_with_ac=False is saved in config flow."""
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

        # User explicitly sets fan_on_with_ac to False (disables it)
        fan_input = {
            CONF_FAN: "switch.fan",
            CONF_FAN_ON_WITH_AC: False,  # User disables this
        }
        await flow.async_step_fan(fan_input)

        # CRITICAL: Verify False is saved (not missing or converted to True)
        print(
            f"fan_on_with_ac in collected_config: {CONF_FAN_ON_WITH_AC in flow.collected_config}"
        )
        print(f"fan_on_with_ac value: {flow.collected_config.get(CONF_FAN_ON_WITH_AC)}")
        print(
            f"All fan-related keys: {[k for k in flow.collected_config.keys() if 'fan' in k]}"
        )

        assert CONF_FAN_ON_WITH_AC in flow.collected_config, "fan_on_with_ac not saved"
        assert (
            flow.collected_config[CONF_FAN_ON_WITH_AC] is False
        ), f"fan_on_with_ac should be False, got: {flow.collected_config.get(CONF_FAN_ON_WITH_AC)}"

    async def test_multiple_fan_booleans_false_persist_in_config_flow(self, mock_hass):
        """Test that multiple False boolean values persist."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

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

        # User sets multiple booleans to False
        fan_input = {
            CONF_FAN: "switch.fan",
            CONF_FAN_MODE: False,
            CONF_FAN_ON_WITH_AC: False,
            CONF_FAN_AIR_OUTSIDE: False,
        }
        await flow.async_step_fan(fan_input)

        # Verify all False values are saved
        assert flow.collected_config[CONF_FAN_MODE] is False
        assert flow.collected_config[CONF_FAN_ON_WITH_AC] is False
        assert flow.collected_config[CONF_FAN_AIR_OUTSIDE] is False

    async def test_fan_on_with_ac_false_shown_in_options_flow(self, mock_hass):
        """Test that fan_on_with_ac=False is shown correctly in options flow UI."""
        # Config entry with fan_on_with_ac explicitly set to False
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",
            CONF_FAN_ON_WITH_AC: False,  # User previously disabled this
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        await flow.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_fan": True})

        # Get the schema and check the default
        schema = result["data_schema"].schema
        fan_on_with_ac_default = None

        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_ON_WITH_AC:
                if hasattr(key, "default"):
                    fan_on_with_ac_default = (
                        key.default() if callable(key.default) else key.default
                    )
                    break

        print(f"fan_on_with_ac default in options schema: {fan_on_with_ac_default}")

        # BUG CHECK: Should show False (from config), not True (schema default)
        assert (
            fan_on_with_ac_default is False
        ), f"BUG: fan_on_with_ac should show False, got: {fan_on_with_ac_default}"

    async def test_fan_on_with_ac_false_not_in_config_shows_true_default(
        self, mock_hass
    ):
        """Test that if fan_on_with_ac was never configured, it shows True default."""
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_FAN: "switch.fan",
            # fan_on_with_ac NOT in config (never configured)
        }

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        await flow.async_step_init()
        await flow.async_step_init({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_basic({})
        result = await flow.async_step_features({"configure_fan": True})

        schema = result["data_schema"].schema
        fan_on_with_ac_default = None

        for key in schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_FAN_ON_WITH_AC:
                if hasattr(key, "default"):
                    fan_on_with_ac_default = (
                        key.default() if callable(key.default) else key.default
                    )
                    break

        # Should show True (default) since never configured
        assert (
            fan_on_with_ac_default is True
        ), f"Should show True default when not configured, got: {fan_on_with_ac_default}"

    async def test_fan_mode_true_persists_and_shows_in_options(self, mock_hass):
        """Test that fan_mode=True persists and shows correctly."""
        # First save fan_mode=True in config flow
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

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

        fan_input = {
            CONF_FAN: "switch.fan",
            CONF_FAN_MODE: True,  # User enables this
        }
        await flow.async_step_fan(fan_input)

        assert flow.collected_config[CONF_FAN_MODE] is True

        # Now test options flow shows True
        config_entry = Mock()
        config_entry.data = dict(flow.collected_config)
        config_entry.data[CONF_NAME] = "Test"

        options_flow = OptionsFlowHandler(config_entry)
        options_flow.hass = mock_hass

        await options_flow.async_step_init()
        await options_flow.async_step_init(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        await options_flow.async_step_basic({})
        result = await options_flow.async_step_features({"configure_fan": True})

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
        ), f"fan_mode should show True, got: {fan_mode_default}"
