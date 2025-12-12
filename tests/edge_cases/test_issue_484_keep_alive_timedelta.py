"""Test for issue #484 - keep_alive stored as float instead of timedelta.

Issue: When keep_alive is configured via config flow, it's stored as a numeric
value (seconds) but climate.py expects a timedelta object. This causes:
AttributeError: 'float' object has no attribute 'total_seconds'

Root cause: Config flow stores time values as int/float (seconds) from NumberSelector,
but async_track_time_interval() expects timedelta objects.

Fix: _normalize_config_numeric_values() converts time-based config values
(keep_alive, min_cycle_duration, stale_duration) from seconds to timedelta.
"""

from datetime import timedelta

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_KEEP_ALIVE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_STALE_DURATION,
    DOMAIN,
)
from tests import common, setup_sensor, setup_switch


@pytest.mark.asyncio
async def test_keep_alive_float_converted_to_timedelta(hass: HomeAssistant):
    """Test that keep_alive stored as float is converted to timedelta during setup.

    This reproduces issue #484 where keep_alive from config flow is stored as
    float (300.0) but code expects timedelta(seconds=300).

    Without the fix, this test would fail with:
    AttributeError: 'float' object has no attribute 'total_seconds'
    """
    # Create necessary test entities
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config from config flow with keep_alive as float (seconds)
    # This mimics what the config flow UI stores
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_KEEP_ALIVE: 300.0,  # Float from config flow, not timedelta!
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    # This should NOT raise AttributeError
    # The fix in _normalize_config_numeric_values() converts float to timedelta
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"  # Initial state


@pytest.mark.asyncio
async def test_min_cycle_duration_int_converted_to_timedelta(hass: HomeAssistant):
    """Test that min_cycle_duration stored as int is converted to timedelta during setup.

    min_cycle_duration from config flow is stored as int (seconds) but code may
    expect timedelta in some places.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config from config flow with min_cycle_duration as int
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_MIN_DUR: 180,  # Int from config flow
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_stale_duration_float_converted_to_timedelta(hass: HomeAssistant):
    """Test that stale_duration stored as float is converted to timedelta during setup.

    stale_duration from config flow is stored as float (seconds) but code expects
    timedelta for sensor staleness detection.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config from config flow with stale_duration as float
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_STALE_DURATION: 600.0,  # Float from config flow
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_timedelta_values_preserved(hass: HomeAssistant):
    """Test that timedelta values are preserved when already in correct format.

    When config comes from YAML (not config flow), values may already be
    timedelta objects. These should be preserved as-is.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config from YAML with timedelta objects
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_KEEP_ALIVE: timedelta(seconds=300),  # Already timedelta
        CONF_STALE_DURATION: timedelta(seconds=600),  # Already timedelta
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_mixed_numeric_and_time_normalization(hass: HomeAssistant):
    """Test that both numeric (precision/temp_step) and time values are normalized.

    Issue #468 required precision/temp_step string-to-float conversion.
    Issue #484 requires keep_alive float-to-timedelta conversion.
    Both should work together.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config with both string numeric and float time values
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        "precision": "0.5",  # String from SelectSelector (issue #468)
        "target_temp_step": "0.5",  # String from SelectSelector (issue #468)
        CONF_KEEP_ALIVE: 300.0,  # Float from NumberSelector (issue #484)
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully with both normalizations applied
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"
    # Precision should be 0.5 (from string conversion)
    assert state.attributes["target_temp_step"] == 0.5


@pytest.mark.asyncio
async def test_keep_alive_dict_deserialized_to_timedelta(hass: HomeAssistant):
    """Test that keep_alive stored as dict (after HA serialization) converts to timedelta.

    After the initial fix in beta10, users reported the issue persisted with a different error:
    AttributeError: 'dict' object has no attribute 'total_seconds'

    This happens because:
    1. Config flow stores keep_alive as float (300.0)
    2. Our fix converts it to timedelta(seconds=300)
    3. Home Assistant serializes timedelta to storage as dict: {'days': 0, 'seconds': 300, 'microseconds': 0}
    4. On reload, it's deserialized as dict, not timedelta
    5. Our normalization must handle this dict format

    Without this fix, beta10 would fail with dict AttributeError after HA restart.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config after Home Assistant storage deserialization
    # When timedelta is saved and reloaded, HA deserializes it as a dict
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        # This is how HA storage represents timedelta(seconds=300)
        CONF_KEEP_ALIVE: {"days": 0, "seconds": 300, "microseconds": 0},
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    # This should NOT raise AttributeError: 'dict' object has no attribute 'total_seconds'
    # The fix converts dict back to timedelta
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity was created successfully
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_min_cycle_duration_dict_to_timedelta(hass: HomeAssistant):
    """Test that min_cycle_duration as dict converts to timedelta correctly."""
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        # Dict representation from HA storage
        CONF_MIN_DUR: {"days": 0, "seconds": 180, "microseconds": 0},
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_stale_duration_dict_to_timedelta(hass: HomeAssistant):
    """Test that stale_duration as dict converts to timedelta correctly."""
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        # Dict representation from HA storage
        CONF_STALE_DURATION: {"days": 0, "seconds": 600, "microseconds": 0},
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"


@pytest.mark.asyncio
async def test_options_flow_with_dict_keep_alive(hass: HomeAssistant):
    """Test that options flow handles dict-serialized keep_alive correctly.

    This reproduces the user-reported scenario in issue #484 where:
    1. Initial config works fine with keep_alive as float
    2. HA converts timedelta to dict in storage after initial setup
    3. User opens options flow to modify settings (e.g., target temp)
    4. Options flow loads config and encounters dict-serialized keep_alive
    5. Without fix, options flow would fail with AttributeError when trying to display keep_alive

    The fix ensures options flow calls _normalize_config_from_storage()
    to convert dict back to timedelta before building the form.
    """
    setup_sensor(hass, 22.0)
    setup_switch(hass, False, common.ENT_HEATER)

    # Simulate config stored by HA with dict-serialized timedelta
    # This is what the config looks like after HA restart - keep_alive is a dict
    config_data = {
        "name": "test",
        CONF_HEATER: common.ENT_HEATER,
        CONF_SENSOR: common.ENT_SENSOR,
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        # This is how HA storage represents timedelta after serialization
        CONF_KEEP_ALIVE: {"days": 0, "seconds": 300, "microseconds": 0},
    }

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="test",
    )
    config_entry.add_to_hass(hass)

    # Initial setup should work (climate.py normalizes dict to timedelta)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == "off"

    # Now simulate options flow
    # This is where the bug occurred - options flow loads dict from storage
    # Without the fix, this would fail with AttributeError when building form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Options flow should successfully load and normalize the dict keep_alive
    # and display the initial form
    assert result["type"] == "form"
    assert result["step_id"] == "init"
