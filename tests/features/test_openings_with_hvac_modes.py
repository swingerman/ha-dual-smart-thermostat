"""Interaction tests for openings feature with different HVAC modes.

Task: T007A - Phase 3: Interaction Tests
Issue: #440

These tests validate that openings (window/door sensors) can be configured
successfully through the config flow for all system types.

KNOWN BUG: openings_scope and timeout values from user_input are not currently
being saved to collected_config in async_step_config. The config step processes
the openings list but doesn't copy the scope/timeout fields to collected_config.
See: feature_steps/openings.py line 111-142

Test Coverage:
1. Openings configuration flow completes for all system types
2. Selected openings are saved in processed format
3. Multiple opening sensors supported
4. Single opening sensor supported
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestOpeningsHeaterCooler:
    """Test openings configuration with heater_cooler system."""

    async def test_openings_single_sensor(self, mock_hass):
        """Test openings with single sensor on heater_cooler system.

        Acceptance Criteria:
        - Flow completes successfully
        - Single opening saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )

        assert result["step_id"] == "openings_config"

        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True
        assert "binary_sensor.window_1" in flow.collected_config["selected_openings"]

    async def test_openings_multiple_sensors(self, mock_hass):
        """Test openings with multiple sensors on heater_cooler system.

        Acceptance Criteria:
        - Flow completes successfully
        - All selected openings saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        result = await flow.async_step_openings_selection(
            {
                "selected_openings": [
                    "binary_sensor.window_1",
                    "binary_sensor.window_2",
                    "binary_sensor.door_1",
                ]
            }
        )

        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True
        assert len(flow.collected_config["selected_openings"]) == 3
        assert "binary_sensor.window_1" in flow.collected_config["selected_openings"]
        assert "binary_sensor.door_1" in flow.collected_config["selected_openings"]


class TestOpeningsSimpleHeater:
    """Test openings configuration with simple_heater system."""

    async def test_openings_simple_heater(self, mock_hass):
        """Test openings on heating-only system.

        Acceptance Criteria:
        - Flow completes successfully
        - Openings saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})
        await flow.async_step_basic(
            {
                CONF_NAME: "Test Heater",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )

        result = await flow.async_step_openings_config(
            {
                "opening_scope": "heat",
                "timeout_openings_open": 300,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True


class TestOpeningsAcOnly:
    """Test openings configuration with ac_only system."""

    async def test_openings_ac_only(self, mock_hass):
        """Test openings on cooling-only system.

        Acceptance Criteria:
        - Flow completes successfully
        - Openings saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1", "binary_sensor.door_1"]}
        )

        result = await flow.async_step_openings_config(
            {
                "opening_scope": "cool",
                "timeout_openings_open": 240,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True
        assert len(flow.collected_config["selected_openings"]) == 2


class TestOpeningsHeatPump:
    """Test openings configuration with heat_pump system."""

    async def test_openings_heat_pump(self, mock_hass):
        """Test openings on heat pump system.

        Heat pump uses single switch for both heating and cooling.

        Acceptance Criteria:
        - Flow completes successfully
        - Openings saved to config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP})
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Test Heat Pump",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            }
        )

        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )

        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_openings"] is True


class TestOpeningsWithOtherFeatures:
    """Test openings combined with other features."""

    async def test_openings_with_fan_and_humidity(self, mock_hass):
        """Test openings alongside fan and humidity features.

        Acceptance Criteria:
        - Flow completes with multiple features
        - All features configured correctly
        - Step ordering correct (openings before presets)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Enable fan, humidity, and openings
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Should go to fan first
        assert result["step_id"] == "fan"
        result = await flow.async_step_fan(
            {
                "fan": "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Then humidity
        assert result["step_id"] == "humidity"
        result = await flow.async_step_humidity(
            {
                "humidity_sensor": "sensor.humidity",
                "dryer": "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        # Then openings selection
        assert result["step_id"] == "openings_selection"
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window_1"]}
        )

        # Then openings config
        assert result["step_id"] == "openings_config"
        result = await flow.async_step_openings_config(
            {
                "opening_scope": "all",
                "timeout_openings_open": 300,
            }
        )

        # Flow should complete
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify all features configured
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config["configure_humidity"] is True
        assert flow.collected_config["configure_openings"] is True
