"""Consolidated tolerance tests across all HVAC modes.

This module consolidates duplicate tolerance tests from mode-specific test files:
- test_temp_change_*_on_within_tolerance (3 duplicates → 1 parametrized test)
- test_temp_change_*_on_outside_tolerance (3 duplicates → 1 parametrized test)
- test_temp_change_*_off_within_tolerance (3 duplicates → 1 parametrized test)
- test_temp_change_*_off_outside_tolerance (3 duplicates → 1 parametrized test)

All tests follow the Given/When/Then pattern.
"""

from homeassistant.components.homeassistant import (
    DOMAIN as HASS_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant
import pytest

from tests import common, setup_sensor, setup_switch


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_temp_change_device_on_within_tolerance_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test that temperature change doesn't turn device off when within hot tolerance for heater."""
    await _test_temp_change_device_on_within_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_temp_change_device_on_within_tolerance_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test that temperature change doesn't turn device off when within cold tolerance for cooler."""
    await _test_temp_change_device_on_within_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_temp_change_device_on_within_tolerance_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test that temperature change doesn't turn device off when within cold tolerance for fan."""
    await _test_temp_change_device_on_within_tolerance_impl(hass, mode_config)


async def _test_temp_change_device_on_within_tolerance_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that temperature change doesn't trigger device off when within tolerance.

    This test consolidates 3 duplicate tests from mode-specific files:
    - test_temp_change_heater_off_within_tolerance
    - test_temp_change_ac_off_within_tolerance
    - test_temp_change_fan_off_within_tolerance

    Uses fixed temperature values to match original test behavior.
    """
    # GIVEN - Device is ON and target temperature is set to 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    await hass.async_block_till_done()

    # WHEN - Temperature changes but stays within tolerance
    # Heater: 33 degrees (within hot tolerance, should not turn off)
    # Cooler/Fan: 29.8 degrees (within cold tolerance, should not turn off)
    if mode_config["name"] == "heater":
        within_tolerance_temp = 33
    else:
        within_tolerance_temp = 29.8

    setup_sensor(hass, within_tolerance_temp)
    await hass.async_block_till_done()

    # THEN - Device remains ON (no service calls)
    assert len(calls) == 0


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_temp_change_device_on_outside_tolerance_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test that temperature change turns device off when outside hot tolerance for heater."""
    await _test_temp_change_device_on_outside_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_temp_change_device_on_outside_tolerance_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test that temperature change turns device off when outside cold tolerance for cooler."""
    await _test_temp_change_device_on_outside_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_temp_change_device_on_outside_tolerance_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test that temperature change turns device off when outside cold tolerance for fan."""
    await _test_temp_change_device_on_outside_tolerance_impl(hass, mode_config)


async def _test_temp_change_device_on_outside_tolerance_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that temperature change triggers device off when outside tolerance.

    This test consolidates 3 duplicate tests from mode-specific files:
    - test_temp_change_heater_off_outside_tolerance
    - test_set_temp_change_ac_off_outside_tolerance
    - test_set_temp_change_fan_off_outside_tolerance

    Uses fixed temperature values to match original test behavior.
    """
    # GIVEN - Device is ON and target temperature is set to 30
    calls = setup_switch(hass, True)
    await common.async_set_temperature(hass, 30)
    await hass.async_block_till_done()

    # WHEN - Temperature changes outside tolerance
    # Heater: 35 degrees (outside hot tolerance, should turn off)
    # Cooler/Fan: 27 degrees (outside cold tolerance, should turn off)
    if mode_config["name"] == "heater":
        outside_tolerance_temp = 35
    else:
        outside_tolerance_temp = 27

    setup_sensor(hass, outside_tolerance_temp)
    await hass.async_block_till_done()

    # THEN - Device turns OFF
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == mode_config["device_entity"]


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_temp_change_device_off_within_tolerance_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test that temperature change doesn't turn device on when within cold tolerance for heater."""
    await _test_temp_change_device_off_within_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_temp_change_device_off_within_tolerance_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test that temperature change doesn't turn device on when within hot tolerance for cooler."""
    await _test_temp_change_device_off_within_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_temp_change_device_off_within_tolerance_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test that temperature change doesn't turn device on when within hot tolerance for fan."""
    await _test_temp_change_device_off_within_tolerance_impl(hass, mode_config)


async def _test_temp_change_device_off_within_tolerance_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that temperature change doesn't trigger device on when within tolerance.

    This test consolidates 3 duplicate tests from mode-specific files:
    - test_temp_change_heater_on_within_tolerance
    - test_temp_change_ac_on_within_tolerance
    - test_temp_change_fan_off_within_tolerance

    Uses fixed temperature values to match original test behavior.
    """
    # GIVEN - Device is OFF and target temperature is set
    calls = setup_switch(hass, False)
    if mode_config["name"] == "heater":
        # Heater uses target 30
        await common.async_set_temperature(hass, 30)
        await hass.async_block_till_done()
        # Temperature: 29 (within cold tolerance of 30)
        within_tolerance_temp = 29
    else:
        # Cooler/Fan uses target 25
        await common.async_set_temperature(hass, 25)
        await hass.async_block_till_done()
        # Temperature: 25.2 (within hot tolerance of 25)
        within_tolerance_temp = 25.2

    # WHEN - Temperature changes but stays within tolerance
    setup_sensor(hass, within_tolerance_temp)
    await hass.async_block_till_done()

    # THEN - Device remains OFF (no service calls)
    assert len(calls) == 0


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_temp_change_device_off_outside_tolerance_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test that temperature change turns device on when outside cold tolerance for heater."""
    await _test_temp_change_device_off_outside_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_temp_change_device_off_outside_tolerance_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test that temperature change turns device on when outside hot tolerance for cooler."""
    await _test_temp_change_device_off_outside_tolerance_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_temp_change_device_off_outside_tolerance_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test that temperature change turns device on when outside hot tolerance for fan."""
    await _test_temp_change_device_off_outside_tolerance_impl(hass, mode_config)


async def _test_temp_change_device_off_outside_tolerance_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that temperature change triggers device on when outside tolerance.

    This test consolidates 3 duplicate tests from mode-specific files:
    - test_temp_change_heater_on_outside_tolerance
    - test_temp_change_ac_on_outside_tolerance
    - test_set_temp_change_fan_off_outside_tolerance

    Uses fixed temperature values to match original test behavior.
    """
    # GIVEN - Device is OFF and target temperature is set
    calls = setup_switch(hass, False)
    if mode_config["name"] == "heater":
        # Heater uses target 30, temp 27 (outside cold tolerance)
        await common.async_set_temperature(hass, 30)
        await hass.async_block_till_done()
        outside_tolerance_temp = 27
    else:
        # Cooler/Fan both use target 25, temp 30 (outside hot tolerance)
        await common.async_set_temperature(hass, 25)
        await hass.async_block_till_done()
        outside_tolerance_temp = 30

    # WHEN - Temperature changes outside tolerance
    setup_sensor(hass, outside_tolerance_temp)
    await hass.async_block_till_done()

    # THEN - Device turns ON
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == mode_config["device_entity"]
