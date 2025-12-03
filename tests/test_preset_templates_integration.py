"""Integration tests for template-based preset temperatures.

Tests the complete integration of templates through the system:
- Entity state changes trigger template re-evaluation
- Multiple rapid entity changes handled correctly
- Entity unavailable/available transitions
- Non-numeric template results handled gracefully
- Seasonal scenarios with conditional templates
"""

from unittest.mock import AsyncMock, patch

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.climate import (
    DualSmartThermostat as DualSmartThermostatClimate,
)
from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_PRESETS,
    CONF_SENSOR,
    PRESET_AWAY,
    PRESET_ECO,
)


class TestSeasonalTemplateIntegration:
    """Test T088: Full seasonal template scenario."""

    @pytest.mark.asyncio
    async def test_seasonal_template_full_flow(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test complete seasonal preset scenario from config to runtime.

        Simulates a real-world scenario where preset temperature changes
        based on season sensor state.
        """
        # Arrange: Create entities
        hass.states.async_set("sensor.season", "winter")
        hass.states.async_set("sensor.temp_sensor", "15", {"unit_of_measurement": "°C"})
        hass.states.async_set("switch.heater", "off")
        await hass.async_block_till_done()

        # Configure with seasonal template
        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_ECO: {
                    ATTR_TEMPERATURE: "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"
                }
            },
        }

        with patch(
            "custom_components.dual_smart_thermostat.climate.DualSmartThermostatClimate._async_control_climate",
            new_callable=AsyncMock,
        ) as mock_control:
            # Create thermostat
            thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
            await thermostat.async_added_to_hass()
            await hass.async_block_till_done()

            # Set HVAC mode and preset
            await thermostat.async_set_hvac_mode(HVACMode.HEAT)
            await thermostat.async_set_preset_mode(PRESET_ECO)
            await hass.async_block_till_done()

            # Assert: Winter temperature (16°C)
            assert thermostat.target_temperature == 16.0

            # Act: Spring arrives - season changes
            hass.states.async_set("sensor.season", "spring")
            await hass.async_block_till_done()

            # Assert: Still using winter temp (spring not explicitly handled, uses else)
            assert thermostat.target_temperature == 26.0

            # Act: Summer arrives
            hass.states.async_set("sensor.season", "summer")
            await hass.async_block_till_done()

            # Assert: Summer temperature (26°C)
            assert thermostat.target_temperature == 26.0

            # Act: Fall arrives, then winter returns
            hass.states.async_set("sensor.season", "fall")
            await hass.async_block_till_done()
            assert thermostat.target_temperature == 26.0

            hass.states.async_set("sensor.season", "winter")
            await hass.async_block_till_done()

            # Assert: Back to winter temperature
            assert thermostat.target_temperature == 16.0

            # Verify control cycle triggered for each season change
            assert mock_control.call_count >= 5  # Initial + 4 season changes


class TestRapidEntityChanges:
    """Test T089: System stability with rapid entity changes."""

    @pytest.mark.asyncio
    async def test_rapid_entity_changes(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test system handles multiple quick entity changes correctly.

        Verifies no race conditions or errors when entity changes rapidly.
        """
        # Arrange: Create entities
        hass.states.async_set(
            "input_number.target_temp", "20", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("sensor.temp_sensor", "18", {"unit_of_measurement": "°C"})
        hass.states.async_set("switch.heater", "off")
        await hass.async_block_till_done()

        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_AWAY: {
                    ATTR_TEMPERATURE: "{{ states('input_number.target_temp') | float }}"
                }
            },
        }

        with patch(
            "custom_components.dual_smart_thermostat.climate.DualSmartThermostatClimate._async_control_climate",
            new_callable=AsyncMock,
        ):
            thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
            await thermostat.async_added_to_hass()
            await hass.async_block_till_done()

            await thermostat.async_set_hvac_mode(HVACMode.HEAT)
            await thermostat.async_set_preset_mode(PRESET_AWAY)
            await hass.async_block_till_done()

            # Assert: Initial temperature
            assert thermostat.target_temperature == 20.0

            # Act: Rapid changes (5 changes in quick succession)
            for temp in [21, 22, 21.5, 23, 22]:
                hass.states.async_set("input_number.target_temp", str(temp))
                # Don't wait - simulate rapid changes

            await hass.async_block_till_done()

            # Assert: Final temperature applied correctly
            assert thermostat.target_temperature == 22.0  # Last value

            # Assert: No errors, system stable
            # The fact that we got here without exceptions means it worked


class TestEntityAvailability:
    """Test T090: Entity unavailable/available transitions."""

    @pytest.mark.asyncio
    async def test_entity_unavailable_then_available(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test entity going unavailable then becoming available with new value.

        Verifies fallback to last good value when unavailable, then updates
        when entity becomes available again.
        """
        # Arrange: Create entities
        hass.states.async_set(
            "input_number.away_temp", "18", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("sensor.temp_sensor", "20", {"unit_of_measurement": "°C"})
        hass.states.async_set("switch.heater", "off")
        await hass.async_block_till_done()

        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_AWAY: {
                    ATTR_TEMPERATURE: "{{ states('input_number.away_temp') | float }}"
                }
            },
        }

        thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
        await thermostat.async_added_to_hass()
        await hass.async_block_till_done()

        await thermostat.async_set_hvac_mode(HVACMode.HEAT)
        await thermostat.async_set_preset_mode(PRESET_AWAY)
        await hass.async_block_till_done()

        # Assert: Initial temperature from template
        assert thermostat.target_temperature == 18.0

        # Act: Entity becomes unavailable
        hass.states.async_set("input_number.away_temp", "unavailable")
        await hass.async_block_till_done()

        # Assert: Falls back to last good value (18.0)
        assert thermostat.target_temperature == 18.0

        # Act: Entity becomes available with new value
        hass.states.async_set("input_number.away_temp", "21")
        await hass.async_block_till_done()

        # Assert: Updates to new value
        assert thermostat.target_temperature == 21.0


class TestNonNumericTemplateResults:
    """Test T091: Non-numeric template results handled gracefully."""

    @pytest.mark.asyncio
    async def test_non_numeric_template_result(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test template returns 'unknown', verifies graceful fallback.

        Simulates entity in unknown state, verifies fallback behavior.
        """
        # Arrange: Create entities - start with valid value
        hass.states.async_set(
            "sensor.external_temp", "20", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("sensor.temp_sensor", "19", {"unit_of_measurement": "°C"})
        hass.states.async_set("switch.heater", "off")
        await hass.async_block_till_done()

        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_ECO: {
                    ATTR_TEMPERATURE: "{{ states('sensor.external_temp') | float }}"
                }
            },
        }

        thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
        await thermostat.async_added_to_hass()
        await hass.async_block_till_done()

        await thermostat.async_set_hvac_mode(HVACMode.HEAT)
        await thermostat.async_set_preset_mode(PRESET_ECO)
        await hass.async_block_till_done()

        # Assert: Initial valid temperature
        assert thermostat.target_temperature == 20.0

        # Act: Entity returns non-numeric state
        hass.states.async_set("sensor.external_temp", "unknown")
        await hass.async_block_till_done()

        # Assert: Falls back to last good value (20.0)
        # System remains stable, no exceptions
        assert thermostat.target_temperature == 20.0

        # Act: Entity recovers with valid value
        hass.states.async_set("sensor.external_temp", "22")
        await hass.async_block_till_done()

        # Assert: Updates to new valid value
        assert thermostat.target_temperature == 22.0
