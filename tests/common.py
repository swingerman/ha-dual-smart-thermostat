import asyncio
from asyncio import TimerHandle
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
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TOGGLE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.humidifier import ATTR_HUMIDITY
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    UnitOfTemperature,
)
from homeassistant.core import (
    Context,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    State,
    SupportsResponse,
    callback,
    split_entity_id,
)
from homeassistant.helpers import event, restore_state
from homeassistant.helpers.dispatcher import SignalType, async_dispatcher_connect
from homeassistant.helpers.json import JSONEncoder
from homeassistant.loader import bind_hass
from homeassistant.setup import async_setup_component
from homeassistant.util.async_ import run_callback_threadsafe
import homeassistant.util.dt as dt_util
from pytest_homeassistant_custom_component.common import MockEntityPlatform
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    ATTR_HVAC_ACTION_REASON,
    DOMAIN as DUAL_DOMAIN,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    SERVICE_SET_HVAC_ACTION_REASON,
    HVACActionReason,
)

ENTITY = "climate.test"
ENT_SENSOR = "sensor.test"
ENT_FLOOR_SENSOR = "input_number.floor_temp"
ENT_OUTSIDE_SENSOR = "input_number.outside_temp"
ENT_OPENING_SENSOR = "input_number.opneing1"
ENT_HUMIDITY_SENSOR = "input_number.humidity"
ENT_SWITCH = "switch.test"
ENT_VALVE = "valve.test"
ENT_HEATER = "input_boolean.test"
ENT_COOLER = "input_boolean.test_cooler"
ENT_FAN = "switch.test_fan"
ENT_FAN_HOT_TOLERNACE_TOGGLE = "input_boolean.test_fan_hot_tolerance_toggle"
ENT_DRYER = "switch.test_dryer"
ENT_HEAT_PUMP_COOLING = "switch.test_heat_pump_cooling"
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


async def async_set_temperature_range(
    hass,
    entity_id=ENTITY_MATCH_ALL,
    target_temp_high=None,
    target_temp_low=None,
    hvac_mode=None,
) -> None:
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
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


async def async_set_humidity(
    hass,
    humidity=None,
    entity_id=ENTITY_MATCH_ALL,
) -> None:
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HUMIDITY, humidity),
        ]
        if value is not None
    }
    _LOGGER.debug("set_humidity start data=%s", kwargs)
    await hass.services.async_call(DOMAIN, SERVICE_SET_HUMIDITY, kwargs, blocking=True)


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


async def async_toggle(hass, entity_id=ENTITY_MATCH_ALL) -> None:
    """Set new target operation mode."""
    data = {}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id

    await hass.services.async_call(DOMAIN, SERVICE_TOGGLE, data, blocking=True)


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


async def async_set_hvac_action_reason(
    hass, entity_id, reason: HVACActionReason
) -> None:
    """Turn off device."""
    data = {}

    if entity_id is not None:
        data[ATTR_ENTITY_ID] = entity_id
    if reason is not None:
        data[ATTR_HVAC_ACTION_REASON] = reason

    await hass.services.async_call(
        DUAL_DOMAIN, SERVICE_SET_HVAC_ACTION_REASON, data, blocking=True
    )


def get_action_reason_sensor_entity_id(climate_entity_id: str) -> str:
    """Return the expected hvac_action_reason sensor entity id for a climate.

    The sensor's object id mirrors the climate's object id plus the
    '_hvac_action_reason' suffix.
    """
    _, object_id = split_entity_id(climate_entity_id)
    return f"sensor.{object_id}_hvac_action_reason"


def get_action_reason_sensor_state(hass, climate_entity_id: str):
    """Return the current state string of the companion action-reason sensor."""
    sensor_state = hass.states.get(
        get_action_reason_sensor_entity_id(climate_entity_id)
    )
    return sensor_state.state if sensor_state is not None else None


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
    timestamp = utc_datetime.timestamp()
    for task in list(get_scheduled_timer_handles(hass.loop)):
        if not isinstance(task, asyncio.TimerHandle):
            continue
        if task.cancelled():
            continue

        mock_seconds_into_future = timestamp - time.time()
        future_seconds = task.when() - (hass.loop.time() + _MONOTONIC_RESOLUTION)

        if fire_all or mock_seconds_into_future >= future_seconds:
            with (
                patch(
                    "homeassistant.helpers.event.time_tracker_utcnow",
                    return_value=utc_datetime,
                ),
                patch(
                    "homeassistant.helpers.event.time_tracker_timestamp",
                    return_value=timestamp,
                ),
            ):
                task._run()
                task.cancel()


fire_time_changed = threadsafe_callback_factory(async_fire_time_changed)


def get_scheduled_timer_handles(loop: asyncio.AbstractEventLoop) -> list[TimerHandle]:
    """Return a list of scheduled TimerHandles."""
    handles: list[TimerHandle] = loop._scheduled  # type: ignore[attr-defined] # noqa: SLF001
    return handles


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

    restore_state.async_get.cache_clear()
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


@callback
def async_mock_signal(
    hass: HomeAssistant, signal: SignalType[Any] | str
) -> list[tuple[Any]]:
    """Catch all dispatches to a signal."""
    calls = []

    @callback
    def mock_signal_handler(*args: Any) -> None:
        """Mock service call."""
        calls.append(args)

    async_dispatcher_connect(hass, signal, mock_signal_handler)

    return calls


class FakeClimateChild(ClimateEntity):
    """A real climate entity standing in for a physical AC / radiator valve."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 0.5
    _attr_should_poll = False

    def __init__(
        self,
        entity_id,
        mode=HVACMode.OFF,
        *,
        assumed=False,
        current=22.0,
        fan_mode="auto",
        resets_fan_on_mode_change=False,
    ):
        """Create the child; `assumed` never reports its state back."""
        self.entity_id = entity_id
        self._attr_hvac_mode = mode
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
            HVACMode.DRY,
            HVACMode.AUTO,
        ]
        self._attr_assumed_state = assumed
        self._attr_target_temperature = 21.0
        self._attr_current_temperature = current
        self._attr_fan_modes = ["quiet", "strong", "auto"]
        self._attr_fan_mode = fan_mode
        self._resets_fan = resets_fan_on_mode_change
        self.calls: list[tuple[str, dict]] = []
        self.contexts: list[tuple[str, Context | None]] = []
        self._echo_queue = None

    def _apply(self, **attrs):
        """A command takes effect now, or is parked when echoes are held.

        An assumed-state device never reports back: the state stays put.
        """
        if self._attr_assumed_state:
            return
        if self._echo_queue is not None:
            self._echo_queue.append((attrs, self._context))
            return
        self._write(attrs, self._context)

    def _write(self, attrs, context):
        for key, value in attrs.items():
            setattr(self, f"_attr_{key}", value)
        if context is not None:
            self.async_set_context(context)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Record the call; follow it unless assumed."""
        self.calls.append(("set_hvac_mode", {"hvac_mode": hvac_mode}))
        self.contexts.append(("set_hvac_mode", self._context))
        attrs = {"hvac_mode": hvac_mode}
        if self._resets_fan:  # what many ACs do on a mode change
            attrs["fan_mode"] = "auto"
        self._apply(**attrs)

    async def async_set_fan_mode(self, fan_mode):
        """Record the call; follow it unless assumed."""
        self.calls.append(("set_fan_mode", {"fan_mode": fan_mode}))
        self.contexts.append(("set_fan_mode", self._context))
        self._apply(fan_mode=fan_mode)

    async def async_turn_off(self):
        """Record the call; follow it unless assumed."""
        self.calls.append(("turn_off", {}))
        self.contexts.append(("turn_off", self._context))
        self._apply(hvac_mode=HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        """Record the call; follow it unless assumed."""
        kwargs.pop("entity_id", None)  # the service layer adds it
        self.calls.append(("set_temperature", dict(kwargs)))
        self.contexts.append(("set_temperature", self._context))
        if "temperature" in kwargs:
            self._apply(target_temperature=kwargs["temperature"])

    def remote(
        self,
        *,
        mode=None,
        temperature=None,
        fan_mode=None,
        reuse_context=False,
        **extra,
    ):
        """The user acts on the device: a state change from outside DST.

        reuse_context=True keeps the entity's current context, like HA does for
        any write within 5 s of a service call (a remote press then carries the
        context of DST's last command).
        """
        attrs = {
            key: value
            for key, value in {
                "hvac_mode": mode,
                "target_temperature": temperature,
                "fan_mode": fan_mode,
            }.items()
            if value is not None
        }
        self._write(attrs | extra, None if reuse_context else Context())

    def power_on_default(self, fan="auto"):
        """The device reports its power-on default fan under the context of the
        last command it was sent (HA stamps a recent write with it)."""
        self._write({"fan_mode": fan}, self._context)

    def hold_echoes(self):
        """Park command effects until flush_echoes (a slow or polled device)."""
        self._echo_queue = []

    def flush_echoes(self, order=None, *, context="own"):
        """Deliver parked effects, optionally reordered; "foreign" strips DST's context."""
        queue, self._echo_queue = self._echo_queue, None
        for index in order if order is not None else range(len(queue)):
            attrs, ctx = queue[index]
            self._write(attrs, Context() if context == "foreign" else ctx)

    def set_current_temperature(self, value):
        """Report a new measured temperature."""
        self._attr_current_temperature = value
        self.async_write_ha_state()


async def add_fake_climate(hass, entity_id, mode=HVACMode.OFF, **kwargs):
    """Register a FakeClimateChild; the real climate services act on it."""
    assert await async_setup_component(hass, DOMAIN, {})
    child = FakeClimateChild(entity_id, mode, **kwargs)
    platform = MockEntityPlatform(hass, domain=DOMAIN, platform_name="fake")
    await platform.async_add_entities([child])
    await hass.async_block_till_done()
    return child


def validate_form_input(result, user_input):
    """Validate user_input through the form's real data_schema, as HA does.

    Flow tests call step methods directly, which skips schema validation; use this
    on the form a step returned before submitting to the next call.
    """
    return result["data_schema"](user_input)
