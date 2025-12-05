"""Consolidated preset mode tests across all HVAC modes.

This module consolidates duplicate preset tests from mode-specific test files:
- test_set_preset_mode (6 duplicates × 9 presets → 1 parametrized test)
- test_set_preset_mode_and_restore_prev_temp (6 duplicates → 1 parametrized test)
- test_set_preset_modet_twice_and_restore_prev_temp (6 duplicates → 1 parametrized test)
- test_set_preset_mode_invalid (6 duplicates → 1 parametrized test)
- test_set_preset_mode_set_temp_keeps_preset_mode (6 duplicates → 1 parametrized test)
- test_set_same_preset_mode_restores_preset_temp_from_modified (6 duplicates → 1 parametrized test)

All tests follow the Given/When/Then pattern.
"""

from homeassistant.components.climate import PRESET_NONE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from tests import common


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_preset_mode_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test setting preset mode applies correct temperature for heater mode."""
    await _test_set_preset_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_preset_mode_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test setting preset mode applies correct temperature for cooler mode."""
    await _test_set_preset_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_preset_mode_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test setting preset mode applies correct temperature for fan mode."""
    await _test_set_preset_mode_impl(hass, mode_config)


async def _test_set_preset_mode_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test setting preset mode applies correct temperature across all HVAC modes.

    This test consolidates 6 duplicate tests from mode-specific files, each with
    9 preset parametrizations, for a total of 54 original test executions.
    """
    # GIVEN - Climate entity configured with presets (set up by fixture)
    initial_temp = mode_config["preset_temps"][PRESET_NONE]

    # WHEN - Setting initial temperature
    await common.async_set_temperature(hass, initial_temp)
    await hass.async_block_till_done()

    # THEN - Test each preset mode applies correct temperature
    for preset, expected_temp in mode_config["preset_temps"].items():
        # WHEN - Setting preset mode
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Temperature matches preset configuration
        state = hass.states.get(common.ENTITY)
        assert state is not None, f"Entity not found for preset {preset}"
        assert state.attributes.get("preset_mode") == preset
        assert (
            state.attributes.get("temperature") == expected_temp
        ), f"preset {preset} temp: {expected_temp} != {state.attributes.get('temperature')}"


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_preset_mode_and_restore_prev_temp_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test preset mode changes temperature and restores original for heater mode."""
    await _test_set_preset_mode_and_restore_prev_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_preset_mode_and_restore_prev_temp_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test preset mode changes temperature and restores original for cooler mode."""
    await _test_set_preset_mode_and_restore_prev_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_preset_mode_and_restore_prev_temp_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test preset mode changes temperature and restores original for fan mode."""
    await _test_set_preset_mode_and_restore_prev_temp_impl(hass, mode_config)


async def _test_set_preset_mode_and_restore_prev_temp_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test preset mode changes temperature and restores original on PRESET_NONE.

    This test consolidates 6 duplicate tests from mode-specific files, verifying
    that when a preset is set and then cleared, the original temperature is restored.
    """
    # GIVEN - Climate entity with initial temperature set
    initial_temp = mode_config["preset_temps"][PRESET_NONE]
    await common.async_set_temperature(hass, initial_temp)
    await hass.async_block_till_done()

    # Test each preset
    for preset, preset_temp in mode_config["preset_temps"].items():
        if preset == PRESET_NONE:
            continue  # Skip PRESET_NONE as it's the baseline

        # WHEN - Setting a preset mode
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Preset temperature is applied
        state = hass.states.get(common.ENTITY)
        assert state.attributes.get("temperature") == preset_temp

        # WHEN - Clearing preset mode (setting to PRESET_NONE)
        await common.async_set_preset_mode(hass, PRESET_NONE)
        await hass.async_block_till_done()

        # THEN - Original temperature is restored
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == initial_temp
        ), f"Failed to restore temp after {preset}"


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_preset_modet_twice_and_restore_prev_temp_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test setting same preset twice still allows temperature restoration for heater mode."""
    await _test_set_preset_modet_twice_and_restore_prev_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_preset_modet_twice_and_restore_prev_temp_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test setting same preset twice still allows temperature restoration for cooler mode."""
    await _test_set_preset_modet_twice_and_restore_prev_temp_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_preset_modet_twice_and_restore_prev_temp_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test setting same preset twice still allows temperature restoration for fan mode."""
    await _test_set_preset_modet_twice_and_restore_prev_temp_impl(hass, mode_config)


async def _test_set_preset_modet_twice_and_restore_prev_temp_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test setting same preset twice still allows temperature restoration.

    This test consolidates 6 duplicate tests from mode-specific files, verifying
    that calling set_preset_mode twice with the same preset doesn't break the
    ability to restore the original temperature.
    """
    # GIVEN - Climate entity with initial temperature set
    initial_temp = mode_config["preset_temps"][PRESET_NONE]
    await common.async_set_temperature(hass, initial_temp)
    await hass.async_block_till_done()

    # Test each preset
    for preset, preset_temp in mode_config["preset_temps"].items():
        if preset == PRESET_NONE:
            continue

        # WHEN - Setting preset mode twice in a row
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Preset temperature is still applied
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == preset_temp
        ), f"Temp wrong after double set of {preset}"

        # WHEN - Clearing preset mode
        await common.async_set_preset_mode(hass, PRESET_NONE)
        await hass.async_block_till_done()

        # THEN - Original temperature is still restored correctly
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == initial_temp
        ), f"Failed to restore after double {preset}"


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_preset_mode_invalid_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test invalid preset mode raises error for heater mode."""
    await _test_set_preset_mode_invalid_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_preset_mode_invalid_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test invalid preset mode raises error for cooler mode."""
    await _test_set_preset_mode_invalid_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_preset_mode_invalid_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test invalid preset mode raises error for fan mode."""
    await _test_set_preset_mode_invalid_impl(hass, mode_config)


async def _test_set_preset_mode_invalid_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test invalid preset mode raises error and case-insensitive preset names work.

    This test consolidates 6 duplicate tests from mode-specific files, verifying
    that lowercase preset names work but capitalized invalid names are rejected.
    """
    # GIVEN - Climate entity with presets configured
    await common.async_set_temperature(hass, mode_config["preset_temps"][PRESET_NONE])
    await hass.async_block_till_done()

    # WHEN - Setting preset mode with lowercase "away"
    await common.async_set_preset_mode(hass, "away")
    await hass.async_block_till_done()

    # THEN - Preset is set (lowercase is valid)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"

    # WHEN - Setting preset mode with lowercase "none"
    await common.async_set_preset_mode(hass, "none")
    await hass.async_block_till_done()

    # THEN - Preset is cleared (lowercase is valid)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"

    # WHEN - Attempting to set invalid capitalized preset "Sleep"
    # THEN - ServiceValidationError is raised
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")

    await hass.async_block_till_done()

    # THEN - Preset mode remains unchanged after error
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test changing temperature after setting preset preserves preset mode for heater mode."""
    await _test_set_preset_mode_set_temp_keeps_preset_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test changing temperature after setting preset preserves preset mode for cooler mode."""
    await _test_set_preset_mode_set_temp_keeps_preset_mode_impl(hass, mode_config)


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test changing temperature after setting preset preserves preset mode for fan mode."""
    await _test_set_preset_mode_set_temp_keeps_preset_mode_impl(hass, mode_config)


async def _test_set_preset_mode_set_temp_keeps_preset_mode_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test changing temperature after setting preset preserves preset mode.

    This test consolidates 6 duplicate tests from mode-specific files, verifying
    that when a user sets a preset and then manually adjusts temperature, the
    preset mode indicator is preserved but uses the new temperature.
    """
    # GIVEN - Climate entity with presets configured
    initial_temp = mode_config["preset_temps"][PRESET_NONE]
    target_temp = 32  # Manual override temperature

    await common.async_set_temperature(hass, initial_temp)
    await hass.async_block_till_done()

    # Test each preset
    for preset, preset_temp in mode_config["preset_temps"].items():
        # WHEN - Setting preset mode
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Preset temperature is applied
        state = hass.states.get(common.ENTITY)
        assert state.attributes.get("temperature") == preset_temp

        # WHEN - Manually setting a different temperature
        await common.async_set_temperature(hass, target_temp)
        await hass.async_block_till_done()

        # THEN - Temperature is changed but preset mode is preserved
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == target_temp
        ), f"Temp not updated for {preset}"
        assert (
            state.attributes.get("preset_mode") == preset
        ), f"Preset mode lost for {preset}"
        assert state.attributes.get("supported_features") == 401

        # WHEN - Clearing preset mode
        await common.async_set_preset_mode(hass, PRESET_NONE)
        await hass.async_block_till_done()

        # THEN - Original or manual temperature is restored based on preset type
        state = hass.states.get(common.ENTITY)
        if preset == PRESET_NONE:
            # PRESET_NONE: manual override is kept
            assert state.attributes.get("temperature") == target_temp
        else:
            # Other presets: original temperature before preset is restored
            assert state.attributes.get("temperature") == initial_temp

        # Reset temperature to initial for next iteration
        await common.async_set_temperature(hass, initial_temp)
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_presets"),
    [("heater", None)],
    indirect=["mode_config", "setup_comp_heat_presets"],
)
async def test_set_same_preset_mode_restores_preset_temp_from_modified_heater(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_presets,
) -> None:
    """Test calling same preset twice restores preset temperature for heater mode."""
    await _test_set_same_preset_mode_restores_preset_temp_from_modified_impl(
        hass, mode_config
    )


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_heat_ac_cool_presets"),
    [("cooler", None)],
    indirect=["mode_config", "setup_comp_heat_ac_cool_presets"],
)
async def test_set_same_preset_mode_restores_preset_temp_from_modified_cooler(
    hass: HomeAssistant,
    mode_config,
    setup_comp_heat_ac_cool_presets,
) -> None:
    """Test calling same preset twice restores preset temperature for cooler mode."""
    await _test_set_same_preset_mode_restores_preset_temp_from_modified_impl(
        hass, mode_config
    )


@pytest.mark.parametrize(
    ("mode_config", "setup_comp_fan_only_config_presets"),
    [("fan", None)],
    indirect=["mode_config", "setup_comp_fan_only_config_presets"],
)
async def test_set_same_preset_mode_restores_preset_temp_from_modified_fan(
    hass: HomeAssistant,
    mode_config,
    setup_comp_fan_only_config_presets,
) -> None:
    """Test calling same preset twice restores preset temperature for fan mode."""
    await _test_set_same_preset_mode_restores_preset_temp_from_modified_impl(
        hass, mode_config
    )


async def _test_set_same_preset_mode_restores_preset_temp_from_modified_impl(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test calling same preset twice restores preset temperature after manual change.

    This test consolidates 6 duplicate tests from mode-specific files, verifying
    that when a user modifies temperature while in a preset, calling the same
    preset again restores the original preset temperature.
    """
    # GIVEN - Climate entity with presets configured
    initial_temp = mode_config["preset_temps"][PRESET_NONE]
    target_temp = 32  # Manual override temperature

    await common.async_set_temperature(hass, initial_temp)
    await hass.async_block_till_done()

    # Test each preset (skip PRESET_NONE as it doesn't have restore behavior)
    for preset, preset_temp in mode_config["preset_temps"].items():
        if preset == PRESET_NONE:
            continue

        # WHEN - Setting preset mode
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Preset temperature is applied
        state = hass.states.get(common.ENTITY)
        assert state.attributes.get("temperature") == preset_temp

        # WHEN - Manually modifying temperature while in preset
        await common.async_set_temperature(hass, target_temp)
        await hass.async_block_till_done()

        state = hass.states.get(common.ENTITY)
        assert state.attributes.get("temperature") == target_temp
        assert state.attributes.get("preset_mode") == preset

        # WHEN - Calling the same preset mode again
        await common.async_set_preset_mode(hass, preset)
        await hass.async_block_till_done()

        # THEN - Original preset temperature is restored (not the manual override)
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == preset_temp
        ), f"Preset temp not restored for {preset}"

        # WHEN - Clearing preset mode
        await common.async_set_preset_mode(hass, PRESET_NONE)
        await hass.async_block_till_done()

        # THEN - Original temperature (before any preset) is restored
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get("temperature") == initial_temp
        ), f"Initial temp not restored after {preset}"
