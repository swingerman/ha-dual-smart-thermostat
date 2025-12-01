"""Test reactive template behavior in Climate entity.

Tests that template-based preset temperatures automatically update when
referenced entities change state (FR-006, FR-007).
"""

from unittest.mock import AsyncMock, patch

from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.climate import DualSmartThermostatClimate
from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_PRESETS,
    CONF_SENSOR,
    PRESET_AWAY,
    PRESET_ECO,
)


class TestReactiveTemplateUpdates:
    """Test US2/US3: Templates re-evaluate when referenced entities change."""

    @pytest.mark.asyncio
    async def test_multiple_entity_changes_sequential(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test T048: Sequential entity changes trigger sequential updates.

        Tests that when multiple entities are referenced in a template,
        changes to each entity independently trigger template re-evaluation.
        """
        # Arrange: Create test entities
        hass.states.async_set(
            "input_number.base_temp", "20", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("input_number.offset", "2", {"unit_of_measurement": "°C"})
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("sensor.temp_sensor", "18", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

        # Configure thermostat with template referencing multiple entities
        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_AWAY: {
                    ATTR_TEMPERATURE: "{{ states('input_number.base_temp') | float + states('input_number.offset') | float }}"
                }
            },
        }

        # Create thermostat
        with patch(
            "custom_components.dual_smart_thermostat.climate.DualSmartThermostatClimate._async_control_climate",
            new_callable=AsyncMock,
        ) as mock_control:
            thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
            await thermostat.async_added_to_hass()
            await hass.async_block_till_done()

            # Set HVAC mode and preset
            await thermostat.async_set_hvac_mode(HVACMode.HEAT)
            await thermostat.async_set_preset_mode(PRESET_AWAY)
            await hass.async_block_till_done()

            # Assert: Initial temperature is 20 + 2 = 22
            assert thermostat.target_temperature == 22.0

            # Act: Change base_temp (entity A)
            hass.states.async_set("input_number.base_temp", "21")
            await hass.async_block_till_done()

            # Assert: Temperature updates to 21 + 2 = 23
            assert thermostat.target_temperature == 23.0
            assert mock_control.call_count >= 2  # Initial + entity A change

            # Act: Change offset (entity B)
            hass.states.async_set("input_number.offset", "3")
            await hass.async_block_till_done()

            # Assert: Temperature updates to 21 + 3 = 24
            assert thermostat.target_temperature == 24.0
            assert mock_control.call_count >= 3  # Initial + entity A + entity B

    @pytest.mark.asyncio
    async def test_conditional_template_reactive_update(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test T052: Complex conditional template responds to entity changes.

        Integration test for US3 - verifies that conditional templates
        with multiple entities trigger updates when any referenced entity changes.
        """
        # Arrange: Create test entities
        hass.states.async_set("sensor.season", "winter")
        hass.states.async_set("binary_sensor.someone_home", "on")
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("sensor.temp_sensor", "18", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

        # Configure thermostat with complex conditional template
        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_ECO: {
                    ATTR_TEMPERATURE: """
                    {{ 22 if is_state('binary_sensor.someone_home', 'on')
                       else (16 if is_state('sensor.season', 'winter') else 26) }}
                    """
                }
            },
        }

        # Create thermostat
        with patch(
            "custom_components.dual_smart_thermostat.climate.DualSmartThermostatClimate._async_control_climate",
            new_callable=AsyncMock,
        ) as mock_control:
            thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
            await thermostat.async_added_to_hass()
            await hass.async_block_till_done()

            # Set HVAC mode and preset
            await thermostat.async_set_hvac_mode(HVACMode.HEAT)
            await thermostat.async_set_preset_mode(PRESET_ECO)
            await hass.async_block_till_done()

            # Assert: Initial temperature is 22 (someone home)
            assert thermostat.target_temperature == 22.0

            # Act: Someone leaves home
            hass.states.async_set("binary_sensor.someone_home", "off")
            await hass.async_block_till_done()

            # Assert: Temperature updates to 16 (away + winter)
            assert thermostat.target_temperature == 16.0

            # Act: Season changes to summer
            hass.states.async_set("sensor.season", "summer")
            await hass.async_block_till_done()

            # Assert: Temperature updates to 26 (away + summer)
            assert thermostat.target_temperature == 26.0

            # Act: Someone comes home
            hass.states.async_set("binary_sensor.someone_home", "on")
            await hass.async_block_till_done()

            # Assert: Temperature updates to 22 (home condition takes precedence)
            assert thermostat.target_temperature == 22.0

            # Verify control cycle was triggered for each change
            assert mock_control.call_count >= 4  # Initial + 3 entity changes

    @pytest.mark.asyncio
    async def test_range_mode_reactive_update(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test T056: Range mode templates respond to entity changes.

        Tests that both target_temp_low and target_temp_high update
        reactively when referenced entities change.
        """
        # Arrange: Create test entities
        hass.states.async_set(
            "sensor.outdoor_temp", "20", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("switch.cooler", "off")
        hass.states.async_set("sensor.temp_sensor", "22", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

        # Configure thermostat with range mode templates
        config = {
            CONF_HEATER: "switch.heater",
            "cooler": "switch.cooler",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_ECO: {
                    "target_temp_low": "{{ states('sensor.outdoor_temp') | float - 2 }}",
                    "target_temp_high": "{{ states('sensor.outdoor_temp') | float + 4 }}",
                }
            },
        }

        # Create thermostat
        with patch(
            "custom_components.dual_smart_thermostat.climate.DualSmartThermostatClimate._async_control_climate",
            new_callable=AsyncMock,
        ):
            thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
            await thermostat.async_added_to_hass()
            await hass.async_block_till_done()

            # Set HVAC mode and preset
            await thermostat.async_set_hvac_mode(HVACMode.HEAT_COOL)
            await thermostat.async_set_preset_mode(PRESET_ECO)
            await hass.async_block_till_done()

            # Assert: Initial range is 18-24 (20-2, 20+4)
            assert thermostat.target_temperature_low == 18.0
            assert thermostat.target_temperature_high == 24.0

            # Act: Change outdoor temperature to 25°C
            hass.states.async_set("sensor.outdoor_temp", "25")
            await hass.async_block_till_done()

            # Assert: Range updates to 23-29 (25-2, 25+4)
            assert thermostat.target_temperature_low == 23.0
            assert thermostat.target_temperature_high == 29.0

            # Act: Change outdoor temperature to 15°C
            hass.states.async_set("sensor.outdoor_temp", "15")
            await hass.async_block_till_done()

            # Assert: Range updates to 13-19 (15-2, 15+4)
            assert thermostat.target_temperature_low == 13.0
            assert thermostat.target_temperature_high == 19.0


class TestReactiveListenerCleanup:
    """Test US6: Listener cleanup prevents memory leaks."""

    @pytest.mark.asyncio
    async def test_listener_cleanup_on_preset_change(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test T031: Listeners removed when preset changes.

        Verifies that old listeners are cleaned up when switching presets
        to prevent memory leaks.
        """
        # Arrange: Create test entities
        hass.states.async_set(
            "input_number.away_temp", "18", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set(
            "input_number.eco_temp", "20", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("sensor.temp_sensor", "19", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

        # Configure thermostat with two presets using different entities
        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_AWAY: {
                    ATTR_TEMPERATURE: "{{ states('input_number.away_temp') }}"
                },
                PRESET_ECO: {ATTR_TEMPERATURE: "{{ states('input_number.eco_temp') }}"},
            },
        }

        # Create thermostat
        thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
        await thermostat.async_added_to_hass()
        await hass.async_block_till_done()

        # Set HVAC mode and first preset (away)
        await thermostat.async_set_hvac_mode(HVACMode.HEAT)
        await thermostat.async_set_preset_mode(PRESET_AWAY)
        await hass.async_block_till_done()

        # Assert: Listening to away_temp entity
        assert "input_number.away_temp" in thermostat._active_preset_entities
        assert len(thermostat._template_listeners) > 0
        initial_listener_count = len(thermostat._template_listeners)

        # Act: Change to eco preset
        await thermostat.async_set_preset_mode(PRESET_ECO)
        await hass.async_block_till_done()

        # Assert: Now listening to eco_temp entity, not away_temp
        assert "input_number.eco_temp" in thermostat._active_preset_entities
        assert "input_number.away_temp" not in thermostat._active_preset_entities
        # Should have same number of listeners (old removed, new added)
        assert len(thermostat._template_listeners) == initial_listener_count

        # Act: Change away_temp (should NOT trigger update)
        old_target = thermostat.target_temperature
        hass.states.async_set("input_number.away_temp", "15")
        await hass.async_block_till_done()

        # Assert: Temperature unchanged (not listening to away_temp anymore)
        assert thermostat.target_temperature == old_target

        # Act: Change eco_temp (should trigger update)
        hass.states.async_set("input_number.eco_temp", "21")
        await hass.async_block_till_done()

        # Assert: Temperature updated (listening to eco_temp)
        assert thermostat.target_temperature == 21.0

    @pytest.mark.asyncio
    async def test_listener_cleanup_on_entity_removal(
        self, hass: HomeAssistant, setup_comp_1  # noqa: F811
    ):
        """Test FR-015: Listeners removed when entity removed from HA.

        Verifies proper cleanup when thermostat is removed to prevent
        memory leaks.
        """
        # Arrange: Create test entities
        hass.states.async_set(
            "input_number.away_temp", "18", {"unit_of_measurement": "°C"}
        )
        hass.states.async_set("switch.heater", "off")
        hass.states.async_set("sensor.temp_sensor", "19", {"unit_of_measurement": "°C"})
        await hass.async_block_till_done()

        # Configure thermostat
        config = {
            CONF_HEATER: "switch.heater",
            CONF_SENSOR: "sensor.temp_sensor",
            CONF_PRESETS: {
                PRESET_AWAY: {
                    ATTR_TEMPERATURE: "{{ states('input_number.away_temp') }}"
                }
            },
        }

        # Create thermostat
        thermostat = DualSmartThermostatClimate(hass, config, "test_thermostat")
        await thermostat.async_added_to_hass()
        await hass.async_block_till_done()

        # Set HVAC mode and preset
        await thermostat.async_set_hvac_mode(HVACMode.HEAT)
        await thermostat.async_set_preset_mode(PRESET_AWAY)
        await hass.async_block_till_done()

        # Assert: Listeners are active
        assert len(thermostat._template_listeners) > 0
        assert len(thermostat._active_preset_entities) > 0

        # Act: Remove thermostat from HA
        await thermostat.async_will_remove_from_hass()
        await hass.async_block_till_done()

        # Assert: All listeners cleaned up
        assert len(thermostat._template_listeners) == 0
        assert len(thermostat._active_preset_entities) == 0
