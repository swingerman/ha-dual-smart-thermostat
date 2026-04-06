"""Tests for HVACDeviceFactory warning and validation logic."""

import logging

from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN


class TestFanHotToleranceWithoutCooler:
    """Test that fan_hot_tolerance without a cooler path logs a warning.

    When fan_hot_tolerance is configured but no cooler entity or ac_mode
    exists, the fan tolerance feature has no effect because it only operates
    within the CoolerFanDevice. Users should be warned about this (#425).
    """

    @pytest.mark.asyncio
    async def test_fan_hot_tolerance_without_cooler_logs_warning(
        self, hass: HomeAssistant, caplog
    ):
        """Test warning logged when fan_hot_tolerance set without cooler.

        Config has heater + fan + fan_hot_tolerance but no cooler/ac_mode.
        The fan_hot_tolerance feature only works with a cooler device, so
        this configuration is ineffective and should warn the user.
        """
        hass.config.units = METRIC_SYSTEM

        heater_entity = "input_boolean.heater"
        fan_entity = "switch.fan"
        sensor_entity = "sensor.temp"

        hass.states.async_set(heater_entity, STATE_OFF)
        hass.states.async_set(fan_entity, STATE_OFF)
        hass.states.async_set(sensor_entity, 20.0)

        yaml_config = {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_entity,
                "fan": fan_entity,
                "target_sensor": sensor_entity,
                "fan_hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        }

        with caplog.at_level(logging.WARNING):
            assert await async_setup_component(hass, CLIMATE, yaml_config)
            await hass.async_block_till_done()

        fan_tol_warnings = [
            r
            for r in caplog.records
            if "fan_hot_tolerance" in r.message and "no cooler device" in r.message
        ]
        assert len(fan_tol_warnings) == 1, (
            "Should warn that fan_hot_tolerance has no effect without a cooler. "
            f"Log messages: {[r.message for r in caplog.records]}"
        )

    @pytest.mark.asyncio
    async def test_fan_hot_tolerance_with_cooler_no_warning(
        self, hass: HomeAssistant, caplog
    ):
        """Test NO warning logged when fan_hot_tolerance is set WITH a cooler.

        Config has heater + cooler + fan + fan_hot_tolerance — this is valid.
        """
        hass.config.units = METRIC_SYSTEM

        heater_entity = "input_boolean.heater"
        cooler_entity = "input_boolean.cooler"
        fan_entity = "switch.fan"
        sensor_entity = "sensor.temp"

        hass.states.async_set(heater_entity, STATE_OFF)
        hass.states.async_set(cooler_entity, STATE_OFF)
        hass.states.async_set(fan_entity, STATE_OFF)
        hass.states.async_set(sensor_entity, 20.0)

        yaml_config = {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_entity,
                "cooler": cooler_entity,
                "fan": fan_entity,
                "target_sensor": sensor_entity,
                "fan_hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.COOL,
            }
        }

        with caplog.at_level(logging.WARNING):
            assert await async_setup_component(hass, CLIMATE, yaml_config)
            await hass.async_block_till_done()

        fan_tol_warnings = [
            r
            for r in caplog.records
            if "fan_hot_tolerance" in r.message and "no cooler device" in r.message
        ]
        assert len(fan_tol_warnings) == 0, (
            "Should NOT warn about fan_hot_tolerance when cooler is configured. "
            f"Warning messages: {[r.message for r in fan_tol_warnings]}"
        )

    @pytest.mark.asyncio
    async def test_fan_hot_tolerance_with_ac_mode_no_warning(
        self, hass: HomeAssistant, caplog
    ):
        """Test NO warning logged when fan_hot_tolerance is set with ac_mode.

        Config has heater + ac_mode + fan + fan_hot_tolerance — this is valid
        because ac_mode makes the heater entity act as a cooler too.
        """
        hass.config.units = METRIC_SYSTEM

        heater_entity = "input_boolean.heater"
        fan_entity = "switch.fan"
        sensor_entity = "sensor.temp"

        hass.states.async_set(heater_entity, STATE_OFF)
        hass.states.async_set(fan_entity, STATE_OFF)
        hass.states.async_set(sensor_entity, 20.0)

        yaml_config = {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_entity,
                "ac_mode": True,
                "fan": fan_entity,
                "target_sensor": sensor_entity,
                "fan_hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.COOL,
            }
        }

        with caplog.at_level(logging.WARNING):
            assert await async_setup_component(hass, CLIMATE, yaml_config)
            await hass.async_block_till_done()

        fan_tol_warnings = [
            r
            for r in caplog.records
            if "fan_hot_tolerance" in r.message and "no cooler device" in r.message
        ]
        assert len(fan_tol_warnings) == 0, (
            "Should NOT warn about fan_hot_tolerance when ac_mode is set. "
            f"Warning messages: {[r.message for r in fan_tol_warnings]}"
        )
