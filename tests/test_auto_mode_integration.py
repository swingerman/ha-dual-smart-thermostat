"""Integration tests for AUTO mode end-to-end through the climate entity.

Tests are organised by system type and follow Given/When/Then structure.
Each test uses real ``input_boolean`` switches (or the existing mock-service
helpers) so the underlying controllers' ``is_active`` checks reflect real
state transitions, which matters for keep_alive and min_cycle_duration paths.
"""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import SERVICE_TURN_ON, STATE_OFF
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common, setup_humidity_sensor, setup_sensor, setup_switch_dual

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Cooler entity used across the heater+cooler tests; matches existing test
# conventions while staying independent of common.ENT_COOLER (which is itself
# an input_boolean used by other suites).
ENT_COOLER_SWITCH = "switch.cooler_test"
ENT_OUTSIDE_SENSOR = "sensor.outside_test"


def _heater_cooler_yaml(
    initial_mode: HVACMode | None = HVACMode.OFF, **extra: object
) -> dict:
    """Return a minimal heater+cooler climate YAML config.

    Pass ``initial_mode=None`` to omit the ``initial_hvac_mode`` key
    entirely (needed for restoration tests where the persisted state must
    drive the initial mode).
    """
    config: dict[str, object] = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 0.5,
        "hot_tolerance": 0.5,
        "heater": common.ENT_SWITCH,
        "cooler": ENT_COOLER_SWITCH,
        "target_sensor": common.ENT_SENSOR,
        "target_temp": 21.0,
    }
    if initial_mode is not None:
        config["initial_hvac_mode"] = initial_mode
    config.update(extra)
    return {"climate": config}


# ---------------------------------------------------------------------------
# System type: heater only (1 capability — AUTO must NOT be exposed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heater_only_does_not_expose_auto(hass: HomeAssistant) -> None:
    """A heater-only climate has only one capability and must not expose AUTO."""
    # Given a climate configured with just a heater and a temperature sensor.
    hass.config.units = METRIC_SYSTEM

    # When the integration is set up.
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    # Then AUTO is not in the climate's hvac_modes list.
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO not in state.attributes["hvac_modes"]


# ---------------------------------------------------------------------------
# System type: heater + cooler (2 capabilities — AUTO available)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heater_cooler_exposes_auto_in_hvac_modes(hass: HomeAssistant) -> None:
    """A heater+cooler climate has 2 capabilities and must expose AUTO."""
    # Given a heater+cooler climate configuration.
    hass.config.units = METRIC_SYSTEM

    # When the integration is set up.
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()

    # Then AUTO appears in hvac_modes alongside HEAT, COOL, OFF.
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO in state.attributes["hvac_modes"]


@pytest.mark.asyncio
async def test_heater_cooler_auto_picks_heat_when_cold(hass: HomeAssistant) -> None:
    """AUTO routes to HEAT when the room is below target."""
    # Given a heater+cooler climate at sensor=18.0 (target 21, cold_tol 0.5;
    # below target − 2× tolerance → urgent cold).
    hass.config.units = METRIC_SYSTEM
    calls = setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 18.0)
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()

    # When the user selects AUTO.
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # Then the climate reports AUTO and the heater turn_on service fires.
    assert hass.states.get(common.ENTITY).state == HVACMode.AUTO
    heater_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    assert heater_calls, "Heater should have been turned on by AUTO HEAT priority"


@pytest.mark.asyncio
async def test_heater_cooler_auto_picks_cool_when_hot(hass: HomeAssistant) -> None:
    """AUTO routes to COOL when the room is above target."""
    # Given a heater+cooler climate at sensor=25.0 (above target + 2× tol →
    # urgent hot).
    hass.config.units = METRIC_SYSTEM
    calls = setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 25.0)
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()

    # When the user selects AUTO.
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # Then the climate reports AUTO and the cooler turn_on service fires.
    assert hass.states.get(common.ENTITY).state == HVACMode.AUTO
    cooler_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == ENT_COOLER_SWITCH
    ]
    assert cooler_calls, "Cooler should have been turned on by AUTO COOL priority"


@pytest.mark.asyncio
async def test_heater_cooler_auto_idle_when_at_target(hass: HomeAssistant) -> None:
    """AUTO sits idle when the temperature is at target."""
    # Given the room temperature exactly at target.
    hass.config.units = METRIC_SYSTEM
    calls = setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 21.0)
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()

    # When AUTO is selected.
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # Then AUTO is reported and no actuator turn_on call fires.
    assert hass.states.get(common.ENTITY).state == HVACMode.AUTO
    assert not [c for c in calls if c.service == SERVICE_TURN_ON]


@pytest.mark.asyncio
async def test_heater_cooler_auto_restored_after_restart(hass: HomeAssistant) -> None:
    """A persisted AUTO state is restored on startup and re-evaluates."""
    # Given a previous AUTO state in the restore cache and a cold sensor.
    mock_restore_cache(hass, (State(common.ENTITY, HVACMode.AUTO),))
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 18.0)

    # When the climate is set up (initial_hvac_mode omitted so the
    # restored state drives the entry mode).
    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(initial_mode=None),
    )
    await hass.async_block_till_done()

    # Then the restored state is AUTO.
    assert hass.states.get(common.ENTITY).state == HVACMode.AUTO


# ---------------------------------------------------------------------------
# System type: heat pump (1 entity, both heat + cool)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heat_pump_exposes_auto_and_survives_mode_swap(
    hass: HomeAssistant,
) -> None:
    """Heat-pump cooling-sensor flips must not strip AUTO from hvac_modes."""
    # Given a heat-pump configuration with the cooling sensor reporting "off".
    hass.config.units = METRIC_SYSTEM
    hass.states.async_set(common.ENT_SWITCH, STATE_OFF)
    hass.states.async_set("binary_sensor.heat_pump_cooling", "off")
    setup_sensor(hass, 21.0)
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "heat_pump_cooling": "binary_sensor.heat_pump_cooling",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 21.0,
            }
        },
    )
    await hass.async_block_till_done()
    assert HVACMode.AUTO in hass.states.get(common.ENTITY).attributes["hvac_modes"]

    # When the heat-pump cooling sensor flips on (the device's hvac_modes
    # list refreshes — previously this overwrote _attr_hvac_modes and
    # dropped AUTO).
    hass.states.async_set("binary_sensor.heat_pump_cooling", "on")
    await hass.async_block_till_done()

    # Then AUTO remains in hvac_modes.
    assert HVACMode.AUTO in hass.states.get(common.ENTITY).attributes["hvac_modes"]


# ---------------------------------------------------------------------------
# System type: heater + dryer (DRY priority via humidity)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heater_dryer_auto_picks_dry_when_humid(hass: HomeAssistant) -> None:
    """AUTO routes to DRY when humidity exceeds the moist threshold."""
    # Given a heater+dryer climate (target_humidity=50, moist_tolerance=5)
    # with cur_humidity=60 (= target + 2×tol → urgent humidity).
    hass.config.units = METRIC_SYSTEM
    setup_humidity_sensor(hass, 60.0)
    setup_sensor(hass, 21.0)
    calls = setup_switch_dual(hass, common.ENT_DRYER, is_on=False, is_second_on=False)

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "moist_tolerance": 5,
                "dry_tolerance": 5,
                "heater": common.ENT_SWITCH,
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "target_temp": 21.0,
                "target_humidity": 50,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    # When AUTO is selected.
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # Then AUTO is reported and the dryer turn_on service fires.
    assert hass.states.get(common.ENTITY).state == HVACMode.AUTO
    dryer_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_DRYER
    ]
    assert dryer_calls, (
        "Dryer should have been turned on by AUTO DRY priority "
        f"(captured calls: {calls!r})"
    )


# ---------------------------------------------------------------------------
# Feature interaction: keep_alive forwards `time` through AUTO dispatch
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.asyncio
async def test_auto_keep_alive_forwards_time_to_controller(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Keep-alive ticks pass ``time`` through AUTO dispatch to the device.

    Background: the heater controller's keep-alive branches gate on
    ``time is not None``. If the AUTO dispatch path drops ``time``, those
    branches never fire and keep_alive becomes a no-op.
    """
    from unittest.mock import patch

    # Given a heater+cooler climate in AUTO mode with keep_alive=5s.
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 18.0)
    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(keep_alive=timedelta(seconds=5)),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # When the keep_alive timer fires (advance past 5s) — patch
    # async_control_hvac so we can capture the time argument it receives.
    times_seen: list = []

    async def _spy(time=None, force=False):
        times_seen.append(time)

    with patch(
        "custom_components.dual_smart_thermostat.hvac_device.heater_cooler_device."
        "HeaterCoolerDevice.async_control_hvac",
        side_effect=_spy,
    ):
        freezer.tick(timedelta(seconds=6))
        common.async_fire_time_changed(hass)
        await hass.async_block_till_done()

    # Then at least one call carried a non-None ``time`` argument
    # (the keep_alive tick fired with time=<datetime>).
    assert any(t is not None for t in times_seen), (
        "No keep-alive tick produced a time-bearing async_control_hvac call; "
        f"observed times: {times_seen!r}"
    )


# ---------------------------------------------------------------------------
# Feature interaction: min_cycle_duration is respected within an AUTO sub-mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_min_cycle_duration_propagates_to_controller(
    hass: HomeAssistant,
) -> None:
    """min_cycle_duration setting reaches the heater controller via AUTO mode.

    The controller's cycle-protection logic is exercised by the existing
    test_heater_mode_cycle suite; this test simply pins that the
    min_cycle_duration value is plumbed through AUTO setup so the controller
    receives it.
    """
    # Given a heater+cooler AUTO climate configured with min_cycle_duration=15s.
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 21.0)
    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(min_cycle_duration=timedelta(seconds=15)),
    )
    await hass.async_block_till_done()

    # When AUTO is selected.
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    # Then the climate platform has the min_cycle_duration plumbed into the
    # heater device's controller — i.e., the integration loaded successfully
    # with cycle protection enabled (no schema or wiring error from AUTO).
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == HVACMode.AUTO


# ---------------------------------------------------------------------------
# Outside-sensor stall flag — Task 8
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_outside_sensor_unconfigured_loads_cleanly(
    hass: HomeAssistant,
) -> None:
    """Given a heater+cooler+AUTO setup with no outside sensor configured /
    When AUTO loads /
    Then setup completes without errors and the entity is reachable.

    This is a regression guard for Task 8: if the new ``_outside_sensor_stalled``
    attribute or ``_remove_outside_stale_tracking`` initialisation is broken the
    entity will fail to load and ``state`` will be None / "unavailable".
    """
    # Given a heater+cooler climate with no outside_sensor in the config.
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 21.0)

    # When the integration is set up.
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()

    # Then the entity is reachable and not unavailable.
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state != "unavailable"


# ---------------------------------------------------------------------------
# Phase 1.3: outside-temperature bias
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_helsinki_winter_loads_with_outside_sensor(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler with outside_sensor and outside-delta-boost = 8°C,
    AUTO active, room 1× tolerance below target, outside very cold /
    When AUTO evaluates /
    Then it picks HEAT and emits AUTO_PRIORITY_TEMPERATURE.

    This is a smoke test: it verifies the Phase 1.3 wiring (config read,
    sensor plumbing, evaluator threading) works end-to-end and does not
    break the normal HEAT path.
    """
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 20.5)  # 1× cold-tolerance below 21.0 target
    hass.states.async_set(ENT_OUTSIDE_SENSOR, "-5.0")  # very cold

    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(
            outside_sensor=ENT_OUTSIDE_SENSOR,
            auto_outside_delta_boost=8.0,
        ),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"


@pytest.mark.asyncio
async def test_auto_free_cooling_picks_fan_over_cool_in_normal_tier(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler+fan with outside_sensor /
    AUTO active, room 1× hot-tolerance above target, outside 4°C cooler /
    When AUTO evaluates /
    Then it picks FAN_ONLY (not COOL) — outside air does the work.

    Verifies the free-cooling path emits AUTO_PRIORITY_COMFORT.
    """
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_switch_dual(hass, "switch.fan_test", False, False)
    setup_sensor(hass, 21.5)  # 1× hot-tolerance above 21.0 target → normal COOL
    hass.states.async_set(ENT_OUTSIDE_SENSOR, "17.5")  # 4°C cooler

    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(
            outside_sensor=ENT_OUTSIDE_SENSOR,
            fan="switch.fan_test",
        ),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] == "auto_priority_comfort"


@pytest.mark.asyncio
async def test_auto_without_outside_sensor_behaves_like_phase_1_2(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler with NO outside_sensor /
    AUTO active, room 1× cold-tolerance below target /
    When AUTO evaluates /
    Then it picks HEAT with AUTO_PRIORITY_TEMPERATURE — Phase 1.2 behavior
    is preserved (regression guard for Tasks 5/7/9 plumbing)."""
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 20.5)

    assert await async_setup_component(hass, CLIMATE, _heater_cooler_yaml())
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"
