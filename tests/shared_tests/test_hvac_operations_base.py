"""Consolidated HVAC operation tests across all HVAC modes.

This module consolidates duplicate HVAC operation tests from mode-specific test files:
- test_get_hvac_modes (4 duplicates → 1 parametrized test)
- test_set_target_temp (4 duplicates → 1 parametrized test)
- test_set_target_temp_and_hvac_mode (4 duplicates → 1 parametrized test)

All tests follow the Given/When/Then pattern.
"""

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
import pytest
import voluptuous as vol

from tests import common


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_get_hvac_modes_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test that the operation list returns correct modes for heater."""
    await _test_get_hvac_modes_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_get_hvac_modes_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test that the operation list returns correct modes for cooler."""
    await _test_get_hvac_modes_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_get_hvac_modes_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test that the operation list returns correct modes for fan."""
    await _test_get_hvac_modes_impl(hass, mode_config)


async def _test_get_hvac_modes_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that the operation list returns the correct modes.

    This test consolidates 4 duplicate tests from mode-specific files.
    """
    # GIVEN - Climate entity configured with specific HVAC modes
    # (Set up by fixture)

    # WHEN - Getting the HVAC modes from the entity
    state = hass.states.get(common.ENTITY)

    # THEN - HVAC modes match the configured modes for this mode
    modes = state.attributes.get("hvac_modes")
    assert modes == mode_config["hvac_modes"]


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_set_target_temp_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test setting target temperature for heater."""
    await _test_set_target_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_set_target_temp_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test setting target temperature for cooler."""
    await _test_set_target_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_set_target_temp_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test setting target temperature for fan."""
    await _test_set_target_temp_impl(hass, mode_config)


async def _test_set_target_temp_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test the setting of the target temperature.

    This test consolidates 4 duplicate tests from mode-specific files,
    verifying that temperature can be set and retrieved correctly.
    """
    # GIVEN - Climate entity in default state
    target_temp = 30.0

    # WHEN - Setting target temperature to 30
    await common.async_set_temperature(hass, target_temp)
    await hass.async_block_till_done()

    # THEN - Temperature is updated correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp

    # WHEN - Attempting to set temperature to None (invalid)
    # THEN - Should raise validation error
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)

    # THEN - Temperature remains unchanged after invalid attempt
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat"],
)
async def test_set_target_temp_and_hvac_mode_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat,
) -> None:
    """Test setting target temperature and HVAC mode together for heater."""
    await _test_set_target_temp_and_hvac_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool"],
)
async def test_set_target_temp_and_hvac_mode_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool,
) -> None:
    """Test setting target temperature and HVAC mode together for cooler."""
    await _test_set_target_temp_and_hvac_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config"],
)
async def test_set_target_temp_and_hvac_mode_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config,
) -> None:
    """Test setting target temperature and HVAC mode together for fan."""
    await _test_set_target_temp_and_hvac_mode_impl(hass, mode_config)


async def _test_set_target_temp_and_hvac_mode_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test the setting of the target temperature and HVAC mode together.

    This test consolidates 4 duplicate tests from mode-specific files,
    verifying that temperature and mode can be set simultaneously.
    """
    # GIVEN - Climate entity in OFF mode
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.OFF

    # WHEN - Setting temperature and HVAC mode together
    target_temp = 30.0
    target_mode = mode_config["hvac_mode"]
    await common.async_set_temperature(
        hass, temperature=target_temp, hvac_mode=target_mode
    )
    await hass.async_block_till_done()

    # THEN - Both temperature and mode are updated correctly
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == target_temp
    assert state.state == target_mode
