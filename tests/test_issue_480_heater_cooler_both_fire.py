"""Tests for issue #480 - heater and cooler fired both at the same time.

https://github.com/swingerman/ha-dual-smart-thermostat/issues/480

When in heat_cool mode, both heater and cooler switches are being turned on
simultaneously when the climate entity is turned on.
"""

import datetime
import logging

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE,
    HVACMode,
)
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
import homeassistant.core as ha
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM, US_CUSTOMARY_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common
from .common import mock_restore_cache

_LOGGER = logging.getLogger(__name__)


def setup_sensor(hass: HomeAssistant, temp: float) -> None:
    """Set up the test sensor."""
    hass.states.async_set(common.ENT_SENSOR, temp)


def setup_switch_dual_heater_cooler(
    hass: HomeAssistant,
    heater_entity: str,
    cooler_entity: str,
    heater_on: bool = False,
    cooler_on: bool = False,
) -> list:
    """Set up the test switches for heater and cooler."""
    hass.states.async_set(heater_entity, STATE_ON if heater_on else STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_ON if cooler_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


@pytest.fixture
async def setup_comp_issue_480_config1(hass: HomeAssistant) -> None:
    """Initialize components based on user ovimano's config from issue #480.

    Config:
    - heater and cooler separate switches
    - heat_cool_mode: true
    - initial_hvac_mode: heat_cool
    - cold_tolerance: 0.5
    - hot_tolerance: -0.5 (NEGATIVE - unusual!)
    - target_temp_low: 23
    - target_temp_high: 25
    - min_cycle_duration: 60 seconds
    """
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_temp": 16,
                "max_temp": 30,
                "target_temp_high": 25,
                "target_temp_low": 23,
                "cold_tolerance": 0.5,
                "hot_tolerance": -0.5,
                "min_cycle_duration": datetime.timedelta(seconds=60),
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "precision": 0.1,
                "target_temp_step": 0.5,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_issue_480_config2(hass: HomeAssistant) -> None:
    """Initialize components based on user hrv231's config from issue #480.

    Config:
    - heater and cooler separate switches
    - heat_cool_mode: true
    - initial_hvac_mode: off (then set to heat_cool)
    - cold_tolerance: 0.5
    - hot_tolerance: 0.5
    - target_temp_low: 70.2
    - target_temp_high: 74.2
    - Uses Fahrenheit
    """
    hass.config.units = US_CUSTOMARY_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_temp": 45,
                "max_temp": 85,
                "target_temp_high": 74.2,
                "target_temp_low": 70.2,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.OFF,
                "precision": 1.0,
                "target_temp_step": 1.0,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()


class TestIssue480HeaterCoolerBothFire:
    """Tests for issue #480 - both heater and cooler firing simultaneously."""

    @pytest.mark.asyncio
    async def test_initial_heat_cool_mode_with_temp_sensor_available(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test initialization with heat_cool mode when sensor already has temp.

        This is the exact scenario from issue #480 - the thermostat starts
        with initial_hvac_mode: heat_cool and both devices fire.
        """
        hass.config.units = METRIC_SYSTEM

        # Set up sensor BEFORE creating climate - this is key!
        # The user's sensor already has temperature data
        setup_sensor(hass, 24)  # Within target_temp_low=23 and target_temp_high=25
        await hass.async_block_till_done()

        # Set up switch BEFORE creating climate to capture all calls
        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Now create the climate with initial_hvac_mode: heat_cool
        assert await async_setup_component(
            hass,
            CLIMATE,
            {
                "climate": {
                    "platform": DOMAIN,
                    "name": "test",
                    "heater": common.ENT_HEATER,
                    "cooler": common.ENT_COOLER,
                    "target_sensor": common.ENT_SENSOR,
                    "min_temp": 16,
                    "max_temp": 30,
                    "target_temp_high": 25,
                    "target_temp_low": 23,
                    "cold_tolerance": 0.5,
                    "hot_tolerance": 0.5,
                    "initial_hvac_mode": HVACMode.HEAT_COOL,
                    "heat_cool_mode": True,
                }
            },
        )
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls during initialization: %s", calls)
        _LOGGER.debug("Turn on calls: %s", turn_on_calls)

        # THE BUG: Both heater and cooler are being turned on during initialization
        # Expected: neither should be on when temp is within range
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on during init when temp is within range. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 0, (
            f"Cooler should NOT be turned on during init when temp is within range. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expected_lingering_timers", [True])
    async def test_heat_cool_mode_temp_within_range_neither_fires(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config1,  # noqa: F811
    ) -> None:
        """Test that when temperature is within range, neither heater nor cooler fires.

        With target_temp_low=23, target_temp_high=25, and current temp=24,
        we are within the comfort zone. Neither device should turn on.
        """
        # Temperature within range
        setup_sensor(hass, 24)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Simulate setting hvac mode to heat_cool
        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        # Neither heater nor cooler should be turned on
        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls: %s", calls)
        _LOGGER.debug("Turn on calls: %s", turn_on_calls)

        # THE BUG: Both heater and cooler are being turned on
        # Expected: neither should be on when temp is within range
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on when temp is within range. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 0, (
            f"Cooler should NOT be turned on when temp is within range. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expected_lingering_timers", [True])
    async def test_heat_cool_mode_temp_too_cold_only_heater_fires(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config1,  # noqa: F811
    ) -> None:
        """Test that when temperature is too cold, only heater fires.

        With target_temp_low=23, cold_tolerance=0.5, and current temp=22,
        we are below target_temp_low - cold_tolerance (22.5).
        Only heater should turn on.
        """
        # Temperature below target_temp_low - cold_tolerance (23 - 0.5 = 22.5)
        setup_sensor(hass, 22)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls: %s", calls)

        # Heater should be on, cooler should NOT
        assert len(heater_on_calls) == 1, (
            f"Heater should be turned on when temp is too cold. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 0, (
            f"Cooler should NOT be turned on when temp is too cold. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expected_lingering_timers", [True])
    async def test_heat_cool_mode_temp_too_hot_only_cooler_fires(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config1,  # noqa: F811
    ) -> None:
        """Test that when temperature is too hot, only cooler fires.

        With target_temp_high=25, hot_tolerance=-0.5 (negative!), and current temp=26,
        we are above target_temp_high + hot_tolerance (25 + (-0.5) = 24.5).
        Only cooler should turn on.
        """
        # Temperature above target_temp_high + hot_tolerance (25 + (-0.5) = 24.5)
        setup_sensor(hass, 26)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls: %s", calls)

        # Cooler should be on, heater should NOT
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on when temp is too hot. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 1, (
            f"Cooler should be turned on when temp is too hot. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    async def test_switch_from_off_to_heat_cool_temp_in_range(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config2,  # noqa: F811
    ) -> None:
        """Test switching from OFF to HEAT_COOL when temp is in range.

        This reproduces user hrv231's scenario where they switch from
        OFF to HEAT_COOL mode. With current temp within range, neither
        heater nor cooler should fire.

        target_temp_low=70.2, target_temp_high=74.2, current=72
        """
        # Temperature within range
        setup_sensor(hass, 72)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Initially OFF
        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.OFF

        # Switch to HEAT_COOL
        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls: %s", calls)

        # THE BUG: Both heater and cooler are being turned on
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on when temp is within range. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 0, (
            f"Cooler should NOT be turned on when temp is within range. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    async def test_switch_from_off_to_heat_cool_temp_too_cold(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config2,  # noqa: F811
    ) -> None:
        """Test switching from OFF to HEAT_COOL when temp is too cold.

        target_temp_low=70.2, cold_tolerance=0.5, current=69
        Expected: only heater turns on
        """
        # Temperature below target_temp_low - cold_tolerance
        setup_sensor(hass, 69)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Switch to HEAT_COOL
        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        assert len(heater_on_calls) == 1, "Heater should be turned on when too cold"
        assert len(cooler_on_calls) == 0, "Cooler should NOT be turned on when too cold"

    @pytest.mark.asyncio
    async def test_switch_from_off_to_heat_cool_temp_too_hot(
        self,
        hass: HomeAssistant,
        setup_comp_issue_480_config2,  # noqa: F811
    ) -> None:
        """Test switching from OFF to HEAT_COOL when temp is too hot.

        target_temp_high=74.2, hot_tolerance=0.5, current=76
        Expected: only cooler turns on
        """
        # Temperature above target_temp_high + hot_tolerance
        setup_sensor(hass, 76)
        await hass.async_block_till_done()

        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Switch to HEAT_COOL
        await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
        await hass.async_block_till_done()

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        assert len(heater_on_calls) == 0, "Heater should NOT be turned on when too hot"
        assert len(cooler_on_calls) == 1, "Cooler should be turned on when too hot"

    @pytest.mark.asyncio
    async def test_restored_state_heat_cool_mode(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test state restoration with heat_cool mode.

        This tests what happens when HA restarts and restores state from
        a previous session where heat_cool mode was active.
        """
        hass.config.units = METRIC_SYSTEM

        # Mock restore cache with previous heat_cool state
        mock_restore_cache(
            hass,
            (
                State(
                    common.ENTITY,
                    HVACMode.HEAT_COOL,
                    {
                        ATTR_HVAC_MODE: HVACMode.HEAT_COOL,
                        ATTR_TARGET_TEMP_LOW: 23,
                        ATTR_TARGET_TEMP_HIGH: 25,
                    },
                ),
            ),
        )

        # Set up sensor with temp in range
        setup_sensor(hass, 24)
        await hass.async_block_till_done()

        # Set up switches before climate to capture all calls
        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Create climate WITHOUT initial_hvac_mode (so it restores from state)
        assert await async_setup_component(
            hass,
            CLIMATE,
            {
                "climate": {
                    "platform": DOMAIN,
                    "name": "test",
                    "heater": common.ENT_HEATER,
                    "cooler": common.ENT_COOLER,
                    "target_sensor": common.ENT_SENSOR,
                    "min_temp": 16,
                    "max_temp": 30,
                    "cold_tolerance": 0.5,
                    "hot_tolerance": 0.5,
                    "heat_cool_mode": True,
                }
            },
        )
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        _LOGGER.debug("State after restore: %s", state.state)
        assert state.state == HVACMode.HEAT_COOL

        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls after restore: %s", calls)

        # Neither should turn on when temp is in range
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on during restore when temp is in range. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 0, (
            f"Cooler should NOT be turned on during restore when temp is in range. "
            f"Calls: {cooler_on_calls}"
        )

    @pytest.mark.asyncio
    async def test_heat_cool_mode_prevents_duplicate_toggle_calls(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that async_heater_cooler_toggle is not called multiple times.

        This verifies the fix for the bug where async_heater_cooler_toggle was
        called twice (once in normal flow, once in keep-alive), causing both
        devices to potentially fire.

        The fix removed the duplicate keep-alive call - now the method is only
        called once regardless of keep-alive triggering.
        """
        hass.config.units = METRIC_SYSTEM

        # Set up sensor with temp too hot (needs cooling)
        setup_sensor(hass, 26)  # Above target_temp_high=25
        await hass.async_block_till_done()

        # Set up switches
        calls = setup_switch_dual_heater_cooler(
            hass, common.ENT_HEATER, common.ENT_COOLER, False, False
        )

        # Create climate entity in heat_cool mode
        assert await async_setup_component(
            hass,
            CLIMATE,
            {
                "climate": {
                    "platform": DOMAIN,
                    "name": "test",
                    "heater": common.ENT_HEATER,
                    "cooler": common.ENT_COOLER,
                    "target_sensor": common.ENT_SENSOR,
                    "min_temp": 16,
                    "max_temp": 30,
                    "target_temp_high": 25,
                    "target_temp_low": 23,
                    "cold_tolerance": 0.5,
                    "hot_tolerance": 0.5,
                    "initial_hvac_mode": HVACMode.HEAT_COOL,
                    "heat_cool_mode": True,
                }
            },
        )
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.state == HVACMode.HEAT_COOL

        # Check initial setup - cooler should have turned on (temp too hot)
        turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
        heater_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_HEATER
        ]
        cooler_on_calls = [
            c for c in turn_on_calls if c.data["entity_id"] == common.ENT_COOLER
        ]

        _LOGGER.debug("All calls: %s", calls)
        _LOGGER.debug("Turn on calls: %s", turn_on_calls)

        # With the fix, async_heater_cooler_toggle is only called once
        # Expected: only cooler should be on (temp too hot)
        assert len(heater_on_calls) == 0, (
            f"Heater should NOT be turned on when temp is too hot. "
            f"Calls: {heater_on_calls}"
        )
        assert len(cooler_on_calls) == 1, (
            f"Cooler should be turned on exactly once when temp is too hot. "
            f"Calls: {cooler_on_calls}"
        )
