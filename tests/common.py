import asyncio
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
import functools as ft
import json
import pathlib
import time
from typing import Any
from unittest.mock import patch

from homeassistant.components.climate import (
    _LOGGER,
    ATTR_AUX_HEAT,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN,
    SERVICE_SET_AUX_HEAT,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    State,
    SupportsResponse,
    callback,
)
from homeassistant.helpers import event, restore_state
from homeassistant.helpers.json import JSONEncoder
from homeassistant.loader import bind_hass
from homeassistant.util.async_ import run_callback_threadsafe
import homeassistant.util.dt as dt_util
import voluptuous as vol

ENTITY = "climate.test"
ENT_SENSOR = "sensor.test"
ENT_FLOOR_SENSOR = "input_number.floor_temp"
ENT_SWITCH = "switch.test"
ENT_HEATER = "input_boolean.test"
ENT_COOLER = "input_boolean.test_cooler"
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5
TARGET_TEMP_STEP = 0.5


async def async_set_preset_mode(hass, preset_mode, entity_id=ENTITY_MATCH_ALL) -> None:
    """Set new preset mode."""
    data = {ATTR_PRESET_MODE: preset_mode}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_SET_PRESET_MODE, data, blocking=True)


async def async_set_aux_heat(hass, aux_heat, entity_id=ENTITY_MATCH_ALL) -> None:
    """Turn all or specified climate devices auxiliary heater on."""
    data = {ATTR_AUX_HEAT: aux_heat}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_SET_AUX_HEAT, data, blocking=True)


@bind_hass
def set_aux_heat(hass, aux_heat, entity_id=ENTITY_MATCH_ALL) -> None:
    """Turn all or specified climate devices auxiliary heater on."""
    data = {ATTR_AUX_HEAT: aux_heat}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_SET_AUX_HEAT, data)


async def async_set_temperature(
    hass,
    temperature=None,
    entity_id=ENTITY_MATCH_ALL,
    target_temp_high=None,
    target_temp_low=None,
    hvac_mode=None,
) -> None:
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_TEMPERATURE, temperature),
            (ATTR_TARGET_TEMP_HIGH, target_temp_high),
            (ATTR_TARGET_TEMP_LOW, target_temp_low),
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("set_temperature start data=%s", kwargs)
    await hass.services.async_call(
        DOMAIN, SERVICE_SET_TEMPERATURE, kwargs, blocking=True
    )


@bind_hass
def set_temperature(
    hass,
    temperature=None,
    entity_id=ENTITY_MATCH_ALL,
    target_temp_high=None,
    target_temp_low=None,
    hvac_mode=None,
):
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_TEMPERATURE, temperature),
            (ATTR_TARGET_TEMP_HIGH, target_temp_high),
            (ATTR_TARGET_TEMP_LOW, target_temp_low),
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("set_temperature start data=%s", kwargs)
    hass.services.call(DOMAIN, SERVICE_SET_TEMPERATURE, kwargs)


async def async_set_hvac_mode(hass, hvac_mode, entity_id=ENTITY_MATCH_ALL) -> None:
    """Set new target operation mode."""
    data = {ATTR_HVAC_MODE: hvac_mode}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_SET_HVAC_MODE, data, blocking=True)


@bind_hass
def set_operation_mode(hass, hvac_mode, entity_id=ENTITY_MATCH_ALL) -> None:
    """Set new target operation mode."""
    data = {ATTR_HVAC_MODE: hvac_mode}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_SET_HVAC_MODE, data)


async def async_turn_on(hass, entity_id=ENTITY_MATCH_ALL) -> None:
    """Turn on device."""
    data = {}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_TURN_ON, data, blocking=True)


async def async_turn_off(hass, entity_id=ENTITY_MATCH_ALL) -> None:
    """Turn off device."""
    data = {}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_TURN_OFF, data, blocking=True)


def threadsafe_callback_factory(func):
    """Create threadsafe functions out of callbacks.

    Callback needs to have `hass` as first argument.
    """

    @ft.wraps(func)
    def threadsafe(*args, **kwargs):
        """Call func threadsafe."""
        hass = args[0]
        return run_callback_threadsafe(
            hass.loop, ft.partial(func, *args, **kwargs)
        ).result()

    return threadsafe


@callback
def async_fire_time_changed_exact(
    hass: HomeAssistant, datetime_: datetime | None = None, fire_all: bool = False
) -> None:
    """Fire a time changed event at an exact microsecond.

    Consider that it is not possible to actually achieve an exact
    microsecond in production as the event loop is not precise enough.
    If your code relies on this level of precision, consider a different
    approach, as this is only for testing.
    """
    if datetime_ is None:
        utc_datetime = datetime.now(UTC)
    else:
        utc_datetime = dt_util.as_utc(datetime_)

    _async_fire_time_changed(hass, utc_datetime, fire_all)


@callback
def async_fire_time_changed(
    hass: HomeAssistant, datetime_: datetime | None = None, fire_all: bool = False
) -> None:
    """Fire a time changed event.

    If called within the first 500  ms of a second, time will be bumped to exactly
    500 ms to match the async_track_utc_time_change event listeners and
    DataUpdateCoordinator which spreads all updates between 0.05..0.50.
    Background in PR https://github.com/home-assistant/core/pull/82233

    As asyncio is cooperative, we can't guarantee that the event loop will
    run an event at the exact time we want. If you need to fire time changed
    for an exact microsecond, use async_fire_time_changed_exact.
    """
    if datetime_ is None:
        utc_datetime = datetime.now(UTC)
    else:
        utc_datetime = dt_util.as_utc(datetime_)

    # Increase the mocked time by 0.5 s to account for up to 0.5 s delay
    # added to events scheduled by update_coordinator and async_track_time_interval
    utc_datetime += timedelta(microseconds=event.RANDOM_MICROSECOND_MAX)

    _async_fire_time_changed(hass, utc_datetime, fire_all)


_MONOTONIC_RESOLUTION = time.get_clock_info("monotonic").resolution


@callback
def _async_fire_time_changed(
    hass: HomeAssistant, utc_datetime: datetime | None, fire_all: bool
) -> None:
    timestamp = dt_util.utc_to_timestamp(utc_datetime)
    for task in list(hass.loop._scheduled):
        if not isinstance(task, asyncio.TimerHandle):
            continue
        if task.cancelled():
            continue

        mock_seconds_into_future = timestamp - time.time()
        future_seconds = task.when() - (hass.loop.time() + _MONOTONIC_RESOLUTION)

        if fire_all or mock_seconds_into_future >= future_seconds:
            with patch(
                "homeassistant.helpers.event.time_tracker_utcnow",
                return_value=utc_datetime,
            ), patch(
                "homeassistant.helpers.event.time_tracker_timestamp",
                return_value=timestamp,
            ):
                task._run()
                task.cancel()


fire_time_changed = threadsafe_callback_factory(async_fire_time_changed)


def mock_restore_cache(hass: HomeAssistant, states: Sequence[State]) -> None:
    """Mock the DATA_RESTORE_CACHE."""
    key = restore_state.DATA_RESTORE_STATE
    data = restore_state.RestoreStateData(hass)
    now = dt_util.utcnow()

    last_states = {}
    for state in states:
        restored_state = state.as_dict()
        restored_state = {
            **restored_state,
            "attributes": json.loads(
                json.dumps(restored_state["attributes"], cls=JSONEncoder)
            ),
        }
        last_states[state.entity_id] = restore_state.StoredState.from_dict(
            {"state": restored_state, "last_seen": now}
        )
    data.last_states = last_states
    _LOGGER.debug("Restore cache: %s", data.last_states)
    assert len(data.last_states) == len(states), f"Duplicate entity_id? {states}"

    hass.data[key] = data


def mock_restore_cache_with_extra_data(
    hass: HomeAssistant, states: Sequence[tuple[State, Mapping[str, Any]]]
) -> None:
    """Mock the DATA_RESTORE_CACHE."""
    key = restore_state.DATA_RESTORE_STATE
    data = restore_state.RestoreStateData(hass)
    now = dt_util.utcnow()

    last_states = {}
    for state, extra_data in states:
        restored_state = state.as_dict()
        restored_state = {
            **restored_state,
            "attributes": json.loads(
                json.dumps(restored_state["attributes"], cls=JSONEncoder)
            ),
        }
        last_states[state.entity_id] = restore_state.StoredState.from_dict(
            {"state": restored_state, "extra_data": extra_data, "last_seen": now}
        )
    data.last_states = last_states
    _LOGGER.debug("Restore cache: %s", data.last_states)
    assert len(data.last_states) == len(states), f"Duplicate entity_id? {states}"

    hass.data[key] = data


def async_mock_service(
    hass: HomeAssistant,
    domain: str,
    service: str,
    schema: vol.Schema | None = None,
    response: ServiceResponse = None,
    supports_response: SupportsResponse | None = None,
    raise_exception: Exception | None = None,
) -> list[ServiceCall]:
    """Set up a fake service & return a calls log list to this service."""
    calls = []

    @callback
    def mock_service_log(call):  # pylint: disable=unnecessary-lambda
        """Mock service call."""
        calls.append(call)
        if raise_exception is not None:
            raise raise_exception
        return response

    if supports_response is None:
        if response is not None:
            supports_response = SupportsResponse.OPTIONAL
        else:
            supports_response = SupportsResponse.NONE

    hass.services.async_register(
        domain,
        service,
        mock_service_log,
        schema=schema,
        supports_response=supports_response,
    )

    return calls


mock_service = threadsafe_callback_factory(async_mock_service)


def get_fixture_path(filename: str, integration: str | None = None) -> pathlib.Path:
    """Get path of fixture."""
    return pathlib.Path(__file__).parent.joinpath("fixtures", filename)
