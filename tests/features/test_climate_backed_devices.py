"""Tests for climate entities used as device roles (issue #281)."""

from datetime import timedelta
import logging

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import DOMAIN, ControlStyle
from custom_components.dual_smart_thermostat.hvac_device.entity_port import (
    ClimatePort,
    SwitchPort,
    make_port,
)
from custom_components.dual_smart_thermostat.hvac_device.generic_hvac_device import (
    GenericHVACDevice,
)
from tests import common, setup_switch


async def test_fake_child_follows_real_climate_services(hass: HomeAssistant) -> None:
    """The fake child is driven by the real climate services."""
    child = await common.add_fake_climate(hass, "climate.test_ac")

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ac", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ac").state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_fake_assumed_child_never_confirms(hass: HomeAssistant) -> None:
    """An assumed-state child records the call but its state never changes."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ir", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF
    assert hass.states.get("climate.test_ir").attributes["assumed_state"] is True
    assert child.calls


async def test_make_port_returns_switch_port_for_switch_like(
    hass: HomeAssistant,
) -> None:
    """Switch-like entities get a SwitchPort that reads on/off."""
    hass.states.async_set("switch.heater", STATE_OFF)
    port = make_port(hass, _RoleDevice("switch.heater"))
    assert isinstance(port, SwitchPort)
    assert port.is_active is False
    hass.states.async_set("switch.heater", STATE_ON)
    assert port.is_active is True


async def test_switch_port_valve_is_active_when_open(hass: HomeAssistant) -> None:
    """A valve counts as active while open."""
    hass.states.async_set("valve.loop", "open")
    port = make_port(hass, _RoleDevice("valve.loop"))
    assert port.is_active is True


async def test_switch_port_skips_command_when_unavailable(
    hass: HomeAssistant,
) -> None:
    """No service call goes to an unavailable switch."""
    calls = setup_switch(hass, True, "switch.heater")
    hass.states.async_set("switch.heater", "unavailable")
    port = make_port(hass, _RoleDevice("switch.heater"))

    await port.async_turn_off(None)

    assert calls == []


class _RoleDevice:
    """The few things a port asks its device for (see entity_port.py)."""

    def __init__(
        self,
        entity_id,
        modes=(HVACMode.HEAT,),
        *,
        target=lambda: 24.0,
        offset=0.0,
        style=ControlStyle.ON_OFF,
        hvac_mode=HVACMode.HEAT,  # the role is selected; OFF = the thermostat is Off
    ):
        self.hvac_mode = hvac_mode
        self.features = object()  # the owner: one thermostat per stub
        self.entity_id = entity_id
        self._modes = modes
        self._target = target
        self._offset = offset
        self._style = style

    def role_modes(self):
        return self._modes

    def climate_target(self):
        return self._target()

    def setpoint_offset(self):
        return self._offset

    def control_style(self):
        return self._style

    def fan_speed(self):
        return None


def _port(hass, entity_id, mode, target=lambda: 24.0, *, offset=0.0, selected=True):
    return make_port(
        hass,
        _RoleDevice(
            entity_id,
            (mode,),
            target=target,
            offset=offset,
            hvac_mode=mode if selected else HVACMode.OFF,
        ),
    )


async def test_climate_port_is_active_follows_child_mode(hass: HomeAssistant) -> None:
    """Active is derived from the child's mode, so roles exclude each other."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    assert isinstance(cool, ClimatePort)
    assert cool.is_active is True
    assert heat.is_active is False  # one mode at a time, by construction


async def test_turn_on_sets_mode_then_pushes_target(hass: HomeAssistant) -> None:
    """Turning on sets the mode first, then the target."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, target=lambda: 24.0)

    await cool.async_turn_on(None)

    assert child.calls == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}),
        ("set_temperature", {"temperature": 24.0}),
    ]
    assert cool.is_active is True


async def test_fan_role_sends_no_target(hass: HomeAssistant) -> None:
    """A role without a target only sets the mode."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    fan = _port(hass, "climate.test_ac", HVACMode.FAN_ONLY, target=lambda: None)

    await fan.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_turn_off_only_when_child_is_in_my_mode(hass: HomeAssistant) -> None:
    """An idle role cannot stop a child serving another role."""
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    await cool.async_turn_off(None)  # idle cooler must not stop the heater
    assert child.calls == []
    assert heat.is_active is True

    await heat.async_turn_off(None)
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF


async def test_stop_turns_the_child_off_in_any_mode(hass: HomeAssistant) -> None:
    """Off means off: stop ignores which role owns the current mode."""
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.FAN_ONLY)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, selected=False)

    await heat.async_turn_off(None)  # not selected, not its mode: nothing happens
    assert child.calls == []

    await heat.async_stop(None)  # Off means off
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF

    await heat.async_stop(None)  # already off: nothing more is sent
    assert child.calls == [("turn_off", {})]


async def test_stop_on_a_switch_only_acts_when_it_is_running(
    hass: HomeAssistant,
) -> None:
    """A switch's stop keeps today's behaviour: only when it is on."""
    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, _RoleDevice("switch.heater"))
    await port.async_stop(None)
    assert calls == []

    hass.states.async_set("switch.heater", STATE_ON)
    await port.async_stop(None)
    assert len(calls) == 1


async def test_unavailable_child_gets_no_commands(hass: HomeAssistant) -> None:
    """No service call goes to an unavailable child."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    hass.states.async_set("climate.test_ac", "unavailable")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert child.calls == []
    assert cool.is_active is False


async def test_unsupported_mode_is_not_sent(hass: HomeAssistant, caplog) -> None:
    """A mode the child does not list is logged once and not sent."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    child.async_write_ha_state()
    dry = _port(hass, "climate.test_ac", HVACMode.DRY)

    await dry.async_turn_on(None)
    await dry.async_turn_on(None)

    assert child.calls == []
    assert caplog.text.count("does not support") == 1  # logged once


async def test_assumed_child_uses_commanded_mode_not_reported_state(
    hass: HomeAssistant,
) -> None:
    """An IR child never confirms: DST's own last command is the truth."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    assert cool.is_active is False
    await cool.async_turn_on(None)

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF  # no feedback
    assert cool.is_active is True  # DST's own record

    await cool.async_turn_off(None)
    assert cool.is_active is False
    assert [c[0] for c in child.calls] == [
        "set_hvac_mode",
        "set_temperature",
        "turn_off",
    ]


async def test_ran_long_enough_uses_child_mode_age(
    hass: HomeAssistant, freezer
) -> None:
    """Min cycle is measured on the child's time in its current mode."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    assert cool.ran_long_enough(timedelta(minutes=5)) is False
    freezer.tick(timedelta(minutes=6))
    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_failed_command_rolls_back_the_assumed_record(
    hass: HomeAssistant,
) -> None:
    """A failed mode command must not leave DST believing it is on."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    async def boom(*_, **__):
        raise RuntimeError("device offline")

    child.async_set_hvac_mode = boom  # the real service now raises
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert cool.is_active is False


AC = "climate.test_ac"
SENSOR = "sensor.room_temperature"
HEATER = "switch.room_heater"


async def _setup(hass, **config):
    hass.config.units = METRIC_SYSTEM
    base = {
        "platform": DOMAIN,
        "name": "test",
        "target_sensor": SENSOR,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: {**base, **config}})
    await hass.async_block_till_done()


async def test_climate_cooler_cycles_with_switch_heater(hass: HomeAssistant) -> None:
    """Mixed setup: relay heater and climate cooler in one thermostat."""
    heater_calls = setup_switch(hass, False, HEATER)
    hass.states.async_set(SENSOR, 22.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}) in child.calls
    assert hass.states.get(AC).state == HVACMode.COOL
    assert hass.states.get("climate.test").attributes["hvac_action"] == "cooling"

    hass.states.async_set(SENSOR, 23.0)  # below target - tolerance
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert heater_calls == []  # the relay heater was never involved


async def test_climate_heater_turns_on_and_off(hass: HomeAssistant) -> None:
    """A climate heater gets mode and target, then turns off at the goal."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 22.0}) in child.calls

    hass.states.async_set(SENSOR, 23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_hvac_off_stops_the_child(hass: HomeAssistant) -> None:
    """Setting the thermostat Off turns the climate child off."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_climate_respects_min_cycle_duration(
    hass: HomeAssistant, freezer
) -> None:
    """The child's time in its mode gates turning it off."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        min_cycle_duration=timedelta(minutes=5),
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 24.0)  # goal reached, but too soon to stop
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=6))
    hass.states.async_set(SENSOR, 24.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_assumed_state_child_is_not_commanded_twice(
    hass: HomeAssistant,
) -> None:
    """IR device: state never confirms, DST must still know it is cooling."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (26.5, 27.0, 26.8):  # more sensor ticks while "on"
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("set_hvac_mode") == 1


async def test_unavailable_child_receives_no_commands(hass: HomeAssistant) -> None:
    """No calls while the child is unavailable."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC)
    hass.states.async_set(AC, "unavailable")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == []


@pytest.mark.parametrize(
    ("role", "extra", "mode"),
    [
        ("fan", {"heater": HEATER}, HVACMode.FAN_ONLY),
        (
            "dryer",
            {"heater": HEATER, "humidity_sensor": "sensor.hum", "target_humidity": 40},
            HVACMode.DRY,
        ),
    ],
)
async def test_fan_and_dryer_roles_use_their_climate_mode(
    hass: HomeAssistant, role, extra, mode
) -> None:
    """Fan and dryer roles drive the child's fan_only / dry modes."""
    hass.states.async_set(SENSOR, 26.0)
    hass.states.async_set("sensor.hum", 60.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, **extra, **{role: AC}, initial_hvac_mode=mode)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_hvac_mode(hass, mode, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": mode}) in child.calls
    assert not [c for c in child.calls if c[0] == "set_temperature"]


def test_role_mode_is_abstract() -> None:
    """A device class cannot be built without a role mode."""
    assert "role_modes" in GenericHVACDevice.__abstractmethods__


async def test_hvac_off_stops_a_child_running_a_mode_no_role_owns(
    hass: HomeAssistant,
) -> None:
    """Off means off, even for a mode set from a remote that no role owns."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)  # no fan role

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls].count("turn_off") == 1


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize("assumed", [False, True])
async def test_keep_alive_in_off_leaves_an_externally_started_climate_alone(
    hass: HomeAssistant, assumed
) -> None:
    """Off is hands-off: the AC switched on with its own remote is not turned off.

    On real hardware a 2 minute keep-alive turned the AC off 101 s after the owner
    started it from the remote. The one unscoped off is sent on the transition to
    Off; while the thermostat stays Off its ticks send nothing to a climate.
    """
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, assumed=assumed)
    child._attr_hvac_mode = HVACMode.HEAT  # started from the AC's own remote
    child.async_write_ha_state()
    await hass.async_block_till_done()

    for minutes in (2, 4, 6):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert all(c[0] != "turn_off" for c in child.calls)
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_the_transition_to_off_turns_the_climate_off_once(
    hass: HomeAssistant,
) -> None:
    """Off means off, once, on the transition (foreign modes included)."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls].count("turn_off") == 1


async def test_hvac_off_sends_nothing_to_a_switch_that_is_already_off(
    hass: HomeAssistant,
) -> None:
    """Switch behaviour is unchanged: Off only stops a running switch."""
    calls = setup_switch(hass, False, HEATER)
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    await common.add_fake_climate(hass, AC)

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert calls == []


async def test_valve_ran_long_enough_when_open(hass: HomeAssistant, freezer) -> None:
    """A valve reports open/closed, so min cycle must be measured against open."""
    hass.states.async_set("valve.loop", "open")
    port = make_port(hass, _RoleDevice("valve.loop"))
    freezer.tick(timedelta(minutes=6))

    assert port.ran_long_enough(timedelta(minutes=5)) is True


async def test_assumed_child_keep_alive_resend_does_not_reset_min_cycle(
    hass: HomeAssistant, freezer
) -> None:
    """Re-sending the mode it is already in must not restart the cycle clock."""
    await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)
    await cool.async_turn_on(None)

    freezer.tick(timedelta(minutes=3))
    await cool.async_turn_on(None)  # keep-alive resend
    freezer.tick(timedelta(minutes=3))

    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_keep_alive_stop_sends_nothing_to_a_climate(
    hass: HomeAssistant,
) -> None:
    """A tick never touches a climate, assumed or not, whatever mode it is in."""
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, selected=False)

    await heat.async_stop(None, keep_alive=True)

    assert child.calls == []


async def test_keep_alive_stop_on_a_switch_only_acts_when_it_is_running(
    hass: HomeAssistant,
) -> None:
    """A switch's state is trustworthy: keep-alive stop keeps master's rule (#587)."""
    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, _RoleDevice("switch.heater"))

    await port.async_stop(None, keep_alive=True)

    assert calls == []


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_keep_alive_in_off_sends_nothing_to_a_climate_and_once_per_tick_to_a_switch(
    hass: HomeAssistant,
) -> None:
    """Each Off keep-alive tick: master's turn_off for the switch, nothing for the AC."""
    hass.states.async_set(SENSOR, 20.0)
    heater_calls = setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert len(heater_calls) == 2
    assert [c[0] for c in child.calls].count("turn_off") == 0


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lone_assumed_climate_in_off_gets_nothing_on_a_keep_alive(
    hass: HomeAssistant,
) -> None:
    """Single-device thermostat: Off is hands-off for the IR child too."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("turn_off") == 0


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lone_switch_in_off_keep_alive_sends_nothing_when_already_off(
    hass: HomeAssistant,
) -> None:
    """Master behaviour (#587): a lone switch is only stopped if it is running."""
    hass.states.async_set(SENSOR, 20.0)
    calls = setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert calls == []


async def test_offset_is_added_to_the_pushed_target(hass: HomeAssistant) -> None:
    """The role's offset is added as-is to the pushed target."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, lambda: 24.0, offset=-2.0)

    await cool.async_turn_on(None)

    assert ("set_temperature", {"temperature": 22.0}) in child.calls


async def test_pushed_target_is_clamped_to_the_child_range(hass: HomeAssistant) -> None:
    """Target plus offset never leaves the child's min/max."""
    child = await common.add_fake_climate(hass, "climate.test_ac")  # 16..30
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 29.0, offset=5.0)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 30}) in child.calls


async def test_pushed_target_is_rounded_to_the_child_step(hass: HomeAssistant) -> None:
    """The pushed value is rounded to the child's target_temp_step."""
    child = await common.add_fake_climate(hass, "climate.test_ac")  # step 0.5
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 21.3)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 21.5}) in child.calls


async def test_target_not_resent_when_child_already_has_it(hass: HomeAssistant) -> None:
    """A value the child already reports is not pushed again."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_target_temperature = 22.0
    child.async_write_ha_state()
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 22.0)

    await heat.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_assumed_child_target_resent_only_after_a_mode_change(
    hass: HomeAssistant,
) -> None:
    """An assumed child cannot report its target: DST's last push stands in."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL, lambda: 24.0)

    await cool.async_turn_on(None)
    await cool.async_turn_on(None)  # keep-alive resend of the same mode
    assert [c[0] for c in child.calls].count("set_temperature") == 1

    await cool.async_turn_off(None)
    await cool.async_turn_on(None)  # mode changed: the device may have dropped it
    assert [c[0] for c in child.calls].count("set_temperature") == 2


async def test_target_change_while_engaged_is_mirrored(hass: HomeAssistant) -> None:
    """A new target reaches the child that is serving the role."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_temperature(hass, 23, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == [("set_temperature", {"temperature": 23.0})]


async def test_unchanged_target_is_not_resent_on_sensor_ticks(
    hass: HomeAssistant,
) -> None:
    """Sync is idempotent: sensor ticks send nothing when the target is current."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    for temp in (20.1, 20.2, 20.3):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert child.calls == []


async def test_preset_target_is_mirrored(hass: HomeAssistant) -> None:
    """Switching preset changes the target, which is mirrored."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        away={"temperature": 17},
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_preset_mode(hass, "away", "climate.test")
    await hass.async_block_till_done()

    assert ("set_temperature", {"temperature": 17.0}) in child.calls


async def test_target_is_never_pushed_before_the_role_owns_the_mode(
    hass: HomeAssistant,
) -> None:
    """Child is in a mode this role does not own: mode first, then target."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)  # not our mode

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_setpoint_style_never_turns_the_child_off_at_target(
    hass: HomeAssistant,
) -> None:
    """The child regulates itself: DST does not stop it when the goal is met."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass, heater=AC, initial_hvac_mode=HVACMode.HEAT, control_style="setpoint"
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 25.0)  # far above target: on_off would stop here
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert "turn_off" not in [c[0] for c in child.calls]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_setpoint_style_ignores_min_cycle_duration(hass: HomeAssistant) -> None:
    """DST adds no cycle limit on a self-regulating child."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        min_cycle_duration=timedelta(minutes=30),
        openings=["binary_sensor.window"],
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    # An opening must pause the child at once, not after the 30 minute "cycle".
    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(SENSOR, 20.1)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_setpoint_style_opening_pauses_and_restores_the_child(
    hass: HomeAssistant,
) -> None:
    """Openings and restore go through the unchanged controller."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        openings=["binary_sensor.window"],
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(SENSOR, 20.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child.calls.clear()
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(SENSOR, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    # the child kept its 22 degree setpoint, so only the mode is restored
    assert child.calls == [("set_hvac_mode", {"hvac_mode": HVACMode.HEAT})]


async def test_setpoint_style_each_role_uses_its_own_offset(
    hass: HomeAssistant,
) -> None:
    """Heater and cooler children get their own role's offset only."""
    heater_ac = "climate.test_heater_ac"
    hass.states.async_set(SENSOR, 18.0)
    await _setup(
        hass,
        heater=heater_ac,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        heater_setpoint_offset=3,
        cooler_setpoint_offset=-5,
    )
    heater_child = await common.add_fake_climate(hass, heater_ac)
    cooler_child = await common.add_fake_climate(hass, AC)

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 25.0}) in heater_child.calls  # 22 + 3

    hass.states.async_set(SENSOR, 28.0)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 19.0}) in cooler_child.calls  # 24 - 5
    assert all(c[1].get("temperature") != 19.0 for c in heater_child.calls)


async def test_on_off_style_is_unchanged_by_the_new_code(hass: HomeAssistant) -> None:
    """Default style still stops the child at the goal."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)  # default style
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_setpoint_style_cooler_stays_engaged_below_target(
    hass: HomeAssistant,
) -> None:
    """The cooler goal is never reached either (LOWER direction)."""
    hass.states.async_set(SENSOR, 28.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.COOL,
        control_style="setpoint",
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.COOL

    hass.states.async_set(SENSOR, 20.0)  # far below target: on_off would stop here
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.COOL
    assert "turn_off" not in [c[0] for c in child.calls]


async def test_same_climate_as_heater_and_cooler_is_accepted(
    hass: HomeAssistant, caplog
) -> None:
    """One climate may fill both roles: the cooler is not dropped."""
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    assert "cannot be equal" not in caplog.text


async def test_shared_climate_is_listened_to_once(hass: HomeAssistant) -> None:
    """A shared entity registers one state listener, not one per role."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    thermostat = hass.data["climate"].get_entity("climate.test")

    assert thermostat.hvac_device.get_device_ids() == [AC]


async def test_switch_entity_in_two_roles_is_still_ignored(
    hass: HomeAssistant, caplog
) -> None:
    """Existing behaviour is kept for switches."""
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(
            hass, heater=HEATER, cooler=HEATER, initial_hvac_mode=HVACMode.HEAT
        )

    assert "cannot be equal" in caplog.text


async def test_single_ac_walks_through_every_mode_one_at_a_time(
    hass: HomeAssistant,
) -> None:
    """Four roles on one climate never fight: one command per transition."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("sensor.hum", 60.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        fan=AC,
        dryer=AC,
        humidity_sensor="sensor.hum",
        target_humidity=40,
        fan_mode=True,
        initial_hvac_mode=HVACMode.HEAT,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    expected = {
        HVACMode.HEAT: HVACMode.HEAT,
        HVACMode.COOL: HVACMode.OFF,  # 20 degrees: nothing to cool
        HVACMode.FAN_ONLY: HVACMode.FAN_ONLY,
        HVACMode.DRY: HVACMode.DRY,
        HVACMode.OFF: HVACMode.OFF,
    }
    for dst_mode, child_mode in expected.items():
        await common.async_set_hvac_mode(hass, dst_mode, "climate.test")
        if dst_mode == HVACMode.FAN_ONLY:
            hass.states.async_set(SENSOR, 26.0)  # the fan only runs when it is hot
        await hass.async_block_till_done()
        assert hass.states.get(AC).state == child_mode, dst_mode

    # One command per transition: no role ever re-commanded another's mode.
    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.DRY]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_idle_role_keep_alive_does_not_stop_the_active_role(
    hass: HomeAssistant,
) -> None:
    """The idle cooler's keep-alive must not switch off the heating child."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.HEAT,
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_ran_long_enough_without_a_min_cycle_is_always_true(
    hass: HomeAssistant,
) -> None:
    """Callers may ask with no min_cycle_duration configured (it is None)."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    assert cool.ran_long_enough(None) is True


async def test_setpoint_style_does_not_apply_to_a_climate_fan(
    hass: HomeAssistant,
) -> None:
    """Only roles that push a setpoint can be self-regulating: a fan still stops."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        fan=AC,
        initial_hvac_mode=HVACMode.FAN_ONLY,
        control_style="setpoint",
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.FAN_ONLY

    hass.states.async_set(SENSOR, 20.0)  # fan goal reached
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_child_without_a_step_gets_whole_degrees_and_one_push(
    hass: HomeAssistant,
) -> None:
    """The pushed value is one the child can hold, so it is never re-pushed."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_target_temperature_step = None  # reports no step
    child.async_write_ha_state()
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 22.3)

    for _ in range(3):
        await heat.async_sync(None)  # inactive: nothing
        await heat.async_turn_on(None)

    assert [c for c in child.calls if c[0] == "set_temperature"] == [
        ("set_temperature", {"temperature": 22.0})
    ]


async def test_target_change_during_an_opening_is_not_pushed(
    hass: HomeAssistant,
) -> None:
    """No push-then-off: while an opening is open the setpoint is left alone."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        openings=["binary_sensor.window"],
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    async def ignore_off():  # the device is slow: still engaged when control runs
        child.calls.append(("turn_off", {}))

    child.async_turn_off = ignore_off
    child.calls.clear()

    hass.states.async_set("binary_sensor.window", "on")
    await common.async_set_temperature(hass, 23, "climate.test")
    await hass.async_block_till_done()

    assert ("set_temperature", {"temperature": 23.0}) not in child.calls
    assert ("turn_off", {}) in child.calls


async def test_setpoint_port_keeps_the_users_min_cycle(hass: HomeAssistant) -> None:
    """Style does not change min cycle: openings force past it, nothing else does."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    port = make_port(
        hass,
        _RoleDevice(
            "climate.test_ac",
            (HVACMode.HEAT,),
            target=lambda: 22.0,
            style=ControlStyle.SETPOINT,
        ),
    )

    assert port.ran_long_enough(timedelta(minutes=5)) is False


async def test_standalone_ac_uses_its_own_temperature(hass: HomeAssistant) -> None:
    """No target_sensor: the AC's current_temperature drives everything."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "cooler": AC,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=22.0)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get("climate.test").attributes["current_temperature"] == 22.0

    child.set_current_temperature(26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 26.0
    assert hass.states.get(AC).state == HVACMode.COOL

    child.set_current_temperature(23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_child_temperature_read_at_startup(hass: HomeAssistant) -> None:
    """The first reading comes from the child before any change event."""
    # Only the state matters at startup; the real entity comes later (adding it
    # would set the climate component up without the platform config).
    hass.states.async_set(AC, "off", {"current_temperature": 21.5})
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {CLIMATE: {"platform": DOMAIN, "name": "test", "heater": AC}},
    )
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 21.5


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_stale_child_temperature_triggers_the_emergency_stop(
    hass: HomeAssistant, freezer
) -> None:
    """A child that stops reporting is treated like a stale sensor."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "sensor_stale_duration": timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=18.0)
    await common.async_set_temperature(hass, 22, "climate.test")
    child.set_current_temperature(18.5)  # a real reading arms the watchdog
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


COOLING_FLAG = "binary_sensor.hp_cooling"


@pytest.mark.parametrize(
    ("cooling", "dst_mode", "room", "expected"),
    [
        ("off", HVACMode.HEAT, 18.0, HVACMode.HEAT),
        ("on", HVACMode.COOL, 27.0, HVACMode.COOL),
    ],
)
async def test_climate_heat_pump_follows_the_cooling_flag(
    hass: HomeAssistant, cooling, dst_mode, room, expected
) -> None:
    """The child's mode is heat or cool, following heat_pump_cooling."""
    hass.states.async_set(COOLING_FLAG, cooling)
    hass.states.async_set(SENSOR, room)
    await _setup(
        hass, heater=AC, heat_pump_cooling=COOLING_FLAG, initial_hvac_mode=dst_mode
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == expected


async def test_shared_fan_with_ac_flag_does_not_flap(hass: HomeAssistant) -> None:
    """fan_on_with_ac cannot stack two modes on one climate: it is forced off."""
    hass.states.async_set(SENSOR, 27.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=AC,
        fan_on_with_ac=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (27.1, 27.2, 27.3, 27.4):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.COOL]  # never fan_only, never repeated
    assert hass.states.get(AC).state == HVACMode.COOL


async def test_entity_cannot_be_its_own_device(hass: HomeAssistant, caplog) -> None:
    """A role pointing at the thermostat itself would loop: it is refused."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater="climate.test")

    assert hass.states.get("climate.test") is None
    assert "itself" in caplog.text


CHILDREN_KEY = "dual_smart_thermostat_climate_children"


async def test_child_is_shared_until_the_last_port_releases_it(
    hass: HomeAssistant,
) -> None:
    """One thermostat going away must not pull the child from under another."""
    await common.add_fake_climate(hass, "climate.test_ac")
    first = _port(hass, "climate.test_ac", HVACMode.HEAT)
    second = _port(hass, "climate.test_ac", HVACMode.COOL)
    assert first._child is second._child

    first.release()
    first.release()  # idempotent: a double release cannot steal the other's reference
    assert "climate.test_ac" in hass.data[CHILDREN_KEY]

    second.release()
    assert "climate.test_ac" not in hass.data[CHILDREN_KEY]


async def test_reload_starts_from_a_fresh_child_record(hass: HomeAssistant) -> None:
    """A stale DST record of an IR child cannot survive its thermostat."""
    await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    old = _port(hass, "climate.test_ir", HVACMode.COOL)
    await old.async_turn_on(None)
    assert old.is_active is True
    old.release()

    new = _port(hass, "climate.test_ir", HVACMode.COOL)

    assert new.is_active is False  # adopted from the reported state (off), not stale


async def test_removing_a_thermostat_releases_its_children(
    hass: HomeAssistant,
) -> None:
    """Entity removal drops the thermostat's references."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC)
    await common.add_fake_climate(hass, AC)
    assert AC in hass.data[CHILDREN_KEY]

    await hass.data["climate"].get_entity("climate.test").async_remove()

    assert AC not in hass.data[CHILDREN_KEY]


async def _stale_heating_child(hass: HomeAssistant, freezer):
    """A heating AC whose only temperature source is itself, watchdog armed."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "sensor_stale_duration": timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=18.0)
    await common.async_set_temperature(hass, 22, "climate.test")
    child.set_current_temperature(18.5)  # a real reading arms the watchdog
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT
    return child


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_empty_readings_do_not_feed_the_stale_watchdog(
    hass: HomeAssistant, freezer
) -> None:
    """A child reporting no temperature is silent: the emergency stop still fires."""
    child = await _stale_heating_child(hass, freezer)

    for _ in range(3):
        freezer.tick(timedelta(minutes=1))
        child.set_current_temperature(None)
        common.async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_our_own_echo_does_not_recover_a_stalled_child(
    hass: HomeAssistant, freezer
) -> None:
    """After the emergency stop only a new reading restarts control."""
    child = await _stale_heating_child(hass, freezer)
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child._attr_target_temperature = 23.0  # any event, same temperature
    child.async_write_ha_state()
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_new_reading_recovers_a_stalled_child(
    hass: HomeAssistant, freezer
) -> None:
    """A changed temperature is a real reading: control resumes."""
    child = await _stale_heating_child(hass, freezer)
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child.set_current_temperature(19.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_climate_heat_pump_is_stopped_when_the_flag_flips_while_heating(
    hass: HomeAssistant,
) -> None:
    """A switch heat pump is turned off on a flip; a climate must not keep heating."""
    hass.states.async_set(COOLING_FLAG, "off")
    hass.states.async_set(SENSOR, 18.0)
    await _setup(
        hass,
        heater=AC,
        heat_pump_cooling=COOLING_FLAG,
        initial_hvac_mode=HVACMode.HEAT,
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(COOLING_FLAG, "on")
    hass.states.async_set(SENSOR, 18.1)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state != HVACMode.HEAT


FAN = "fan.test_fan"


async def test_cooler_only_ac_gets_fan_speed_control(hass: HomeAssistant) -> None:
    """Any climate role exposes the child's fan modes, set via climate.set_fan_mode."""
    hass.states.async_set(SENSOR, 27.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    state = hass.states.get("climate.test")
    assert state.attributes["fan_modes"] == ["quiet", "strong", "auto"]

    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls
    assert hass.states.get("climate.test").attributes["fan_mode"] == "strong"


async def test_separate_fan_entity_owns_fan_mode_and_the_ac_is_left_alone(
    hass: HomeAssistant,
) -> None:
    """Precedence is structural: a configured fan entity wins."""
    hass.states.async_set(
        FAN, "off", {"preset_modes": ["low", "high"], "preset_mode": "low"}
    )
    hass.states.async_set(SENSOR, 24.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=FAN,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_modes"] == ["low", "high"]

    calls = common.async_mock_service(hass, "fan", "set_preset_mode")
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "high"},
        blocking=True,
    )

    assert len(calls) == 1
    assert all(c[0] != "set_fan_mode" for c in child.calls)  # AC speed untouched


async def test_climate_fan_role_is_the_fan_speed_target(hass: HomeAssistant) -> None:
    """A climate as the fan role provides the speed control."""
    hass.states.async_set(SENSOR, 24.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=AC,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    await common.add_fake_climate(hass, AC)
    await hass.async_block_till_done()

    state = hass.states.get("climate.test")
    assert state.attributes["fan_modes"] == ["quiet", "strong", "auto"]


async def test_switch_only_setup_has_no_fan_speed(hass: HomeAssistant) -> None:
    """Nothing changes without a climate role or fan entity."""
    hass.states.async_set(SENSOR, 24.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, initial_hvac_mode=HVACMode.HEAT)

    assert "fan_modes" not in hass.states.get("climate.test").attributes


async def test_fan_speed_is_reapplied_after_the_ac_resets_it(
    hass: HomeAssistant,
) -> None:
    """Many ACs drop the fan speed on a mode change: it is sent again after."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, resets_fan_on_mode_change=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    child.calls.clear()

    await common.async_set_temperature(hass, 24, "climate.test")  # too hot: AC on
    await hass.async_block_till_done()

    order = [c[0] for c in child.calls]
    assert order.index("set_hvac_mode") < order.index("set_fan_mode")
    assert ("set_fan_mode", {"fan_mode": "quiet"}) in child.calls
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"


async def test_fan_speed_is_reapplied_on_an_assumed_state_child(
    hass: HomeAssistant,
) -> None:
    """No state to compare with: an assumed child is always sent the speed."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    child.calls.clear()

    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls


async def test_a_separate_fan_entity_means_no_reapply_on_the_ac(
    hass: HomeAssistant,
) -> None:
    """The AC's own fan speed is never touched when a fan entity owns fan_mode."""
    hass.states.async_set(
        FAN, "off", {"preset_modes": ["low", "high"], "preset_mode": "low"}
    )
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=FAN,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC, resets_fan_on_mode_change=True)
    common.async_mock_service(hass, "fan", "set_preset_mode")

    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert all(c[0] != "set_fan_mode" for c in child.calls)


async def test_fan_role_on_the_climate_applies_the_speed_once(
    hass: HomeAssistant,
) -> None:
    """The port re-applies; FanDevice must not send it a second time."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=AC,
        fan_mode=True,
        initial_hvac_mode=HVACMode.FAN_ONLY,
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    await common.async_set_temperature(hass, 24, "climate.test")
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY, "climate.test")
    await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("set_hvac_mode") == 1
    assert [c[0] for c in child.calls].count("set_fan_mode") == 1


async def test_fan_speed_is_restored_after_a_restart(hass: HomeAssistant) -> None:
    """The last selected speed comes back from the restored state."""
    common.mock_restore_cache(
        hass,
        [State("climate.test", "cool", {"fan_mode": "strong", "temperature": 24})],
    )
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    hass.states.async_set(
        AC,
        "off",
        {"fan_modes": ["quiet", "strong", "auto"], "fan_mode": "auto"},
    )  # the child is up before the thermostat
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_mode"] == "strong"


async def test_fan_speed_restore_waits_for_a_late_child(hass: HomeAssistant) -> None:
    """A child that connects late is detected on its first state."""
    common.mock_restore_cache(
        hass,
        [State("climate.test", "cool", {"fan_mode": "strong", "temperature": 24})],
    )
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    assert "fan_modes" not in hass.states.get("climate.test").attributes

    await common.add_fake_climate(hass, AC)  # integration connects late
    await hass.async_block_till_done()

    state = hass.states.get("climate.test")
    assert state.attributes["fan_modes"] == ["quiet", "strong", "auto"]
    assert state.attributes["fan_mode"] == "strong"


async def test_late_child_without_fan_modes_never_gains_speed_control(
    hass: HomeAssistant,
) -> None:
    """No fan_modes, no speed control, however late it shows up."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)

    hass.states.async_set(AC, "off", {"hvac_modes": ["off", "cool"]})
    await hass.async_block_till_done()

    assert "fan_modes" not in hass.states.get("climate.test").attributes


async def test_failed_fan_speed_reapply_does_not_abort_the_control_cycle(
    hass: HomeAssistant, caplog
) -> None:
    """A child that rejects set_fan_mode still gets its mode and target."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    async def reject(fan_mode):
        raise RuntimeError("device rejected the fan mode")

    child.async_set_fan_mode = reject
    child.calls.clear()

    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}) in child.calls
    assert ("set_temperature", {"temperature": 24.0}) in child.calls
    assert hass.states.get(AC).state == HVACMode.COOL
    # handled where it happens (logged), not left to abort the control cycle
    assert any(
        r.name.endswith("entity_port") and "Failed to apply fan mode" in r.getMessage()
        for r in caplog.records
    )


async def test_fan_speed_chosen_while_the_ac_is_off_is_applied_on_turn_on(
    hass: HomeAssistant,
) -> None:
    """Nothing is sent to an off child; the selection waits for the next turn on."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, resets_fan_on_mode_change=True)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF  # nothing to cool at 20

    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    assert all(c[0] != "set_fan_mode" for c in child.calls)

    hass.states.async_set(SENSOR, 27.0)  # too hot: the AC turns on
    await hass.async_block_till_done()

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls
    assert hass.states.get(AC).attributes["fan_mode"] == "strong"


def _leaf_devices(device):
    """Every sub-device that owns a port, however deeply wrapped."""
    sub = getattr(device, "hvac_devices", None)
    if sub is None:
        return [device]
    return [leaf for d in sub for leaf in _leaf_devices(d)]


@pytest.mark.parametrize(
    ("transitions"),
    [
        [
            (HVACMode.HEAT, 18.0, HVACMode.HEAT),
            (HVACMode.COOL, 27.0, HVACMode.COOL),
            (HVACMode.FAN_ONLY, 27.0, HVACMode.FAN_ONLY),
            (HVACMode.HEAT, 18.0, HVACMode.HEAT),
            (HVACMode.COOL, 27.0, HVACMode.COOL),
            (HVACMode.HEAT, 18.0, HVACMode.HEAT),
            (HVACMode.FAN_ONLY, 27.0, HVACMode.FAN_ONLY),
            (HVACMode.COOL, 27.0, HVACMode.COOL),
        ]
    ],
)
async def test_a_late_stop_from_a_deactivated_role_never_kills_the_active_mode(
    hass: HomeAssistant, transitions
) -> None:
    """On real hardware the old role's stop can land after the new role's set_mode.

    Off means off is only for a thermostat that is Off: a role being switched out
    must only stop the child if the child is still in its own mode.
    """
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        fan=AC,
        fan_mode=True,
        initial_hvac_mode=HVACMode.OFF,
    )
    await common.add_fake_climate(hass, AC)
    thermostat = hass.data["climate"].get_entity("climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for dst_mode, room, child_mode in transitions:
        hass.states.async_set(SENSOR, room)
        await common.async_set_hvac_mode(hass, dst_mode, "climate.test")
        await hass.async_block_till_done()
        assert hass.states.get(AC).state == child_mode, dst_mode

        # the late stops of every role that is not the active one
        for leaf in _leaf_devices(thermostat.hvac_device):
            if leaf.role_modes()[0] != child_mode:
                await leaf.async_stop()
        await hass.async_block_till_done()
        assert hass.states.get(AC).state == child_mode, f"killed after {dst_mode}"

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_climate_child_logs_every_command_at_debug(
    hass: HomeAssistant, caplog
) -> None:
    """Hardware evidence: every command the child sends is visible in the log."""
    import logging

    await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, lambda: 24.0)

    with caplog.at_level(logging.DEBUG):
        await cool.async_turn_on(None)
        await cool.async_turn_off(None)

    text = caplog.text
    assert "set_hvac_mode" in text and "climate.test_ac" in text and "cool" in text
    assert "set_temperature" in text
    assert "turn_off" in text


async def test_switching_cool_to_fan_only_sends_no_stop_before_the_new_mode(
    hass: HomeAssistant,
) -> None:
    """The new mode replaces the old one: a stop in between can land after it.

    On real hardware cool -> fan_only left the AC off: the extra turn_off arrived
    after set_hvac_mode(fan_only). The deactivated role is stopped after the new
    role has run, and only if the child is still in its mode.
    """
    hass.states.async_set(SENSOR, 27.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        fan=AC,
        fan_mode=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.COOL
    child.calls.clear()

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == [("set_hvac_mode", {"hvac_mode": HVACMode.FAN_ONLY})]
    assert hass.states.get(AC).state == HVACMode.FAN_ONLY


async def test_a_switched_out_role_is_stopped_when_the_new_role_stays_idle(
    hass: HomeAssistant,
) -> None:
    """Nothing to cool: the child leaves the old mode with exactly one stop."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC, fan=AC, fan_mode=True)
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls] == ["turn_off"]


async def test_shared_ac_walk_ends_in_each_mode_with_no_trailing_off(
    hass: HomeAssistant,
) -> None:
    """The P5 mode walk on one AC as heater, cooler and fan (on_off), through the
    real paths: mode changes, set_temperature with hvac_mode in one call (HA sets
    the mode first with the old target), and the fan-speed set_fan_mode flow that
    the logbook pointed at. After every step the AC is in exactly the expected
    mode and the last thing sent to it is not an off."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "cooler": AC,
                "fan": AC,
                "fan_mode": True,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=27.0)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    async def mode(hvac_mode):
        child.calls.clear()
        await common.async_set_hvac_mode(hass, hvac_mode, "climate.test")
        await hass.async_block_till_done()

    async def temperature_with_mode(hvac_mode, temperature):
        child.calls.clear()
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": "climate.test",
                "hvac_mode": hvac_mode,
                "temperature": temperature,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

    async def fan_speed(speed):
        child.calls.clear()
        await hass.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": "climate.test", "fan_mode": speed},
            blocking=True,
        )
        await hass.async_block_till_done()

    def settled(expected):
        assert hass.states.get(AC).state == expected
        assert not child.calls or child.calls[-1][0] != "turn_off", child.calls

    await mode(HVACMode.FAN_ONLY)  # hot room: the fan runs
    settled(HVACMode.FAN_ONLY)

    await fan_speed("strong")
    settled(HVACMode.FAN_ONLY)
    assert child.calls == [("set_fan_mode", {"fan_mode": "strong"})]

    await temperature_with_mode(HVACMode.HEAT, 30)  # fan_only -> heat, new target
    settled(HVACMode.HEAT)
    assert child.calls[0][0] != "turn_off"  # the mode replaces fan_only

    await fan_speed("quiet")
    settled(HVACMode.HEAT)
    assert child.calls == [("set_fan_mode", {"fan_mode": "quiet"})]

    await temperature_with_mode(HVACMode.COOL, 24)  # heat -> cool
    settled(HVACMode.COOL)
    assert child.calls[0][0] != "turn_off"  # no stop between the two steps
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"  # speed kept

    await mode(HVACMode.FAN_ONLY)  # cool -> fan_only
    settled(HVACMode.FAN_ONLY)
    assert child.calls == [("set_hvac_mode", {"hvac_mode": HVACMode.FAN_ONLY})] or (
        ("set_hvac_mode", {"hvac_mode": HVACMode.FAN_ONLY}) in child.calls
        and "turn_off" not in [c[0] for c in child.calls]
    )

    await mode(HVACMode.OFF)  # fan_only -> off
    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls] == ["turn_off"]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_manual_target_change_bypasses_min_cycle_like_master(
    hass: HomeAssistant,
) -> None:
    """Intentional (force=True, as on master): a user's target change acts at once.

    Only automatic ticks wait for min_cycle_duration; lowering the target below
    the room temperature stops the running AC without waiting for it.
    """
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        min_cycle_duration=timedelta(minutes=30),
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 23.0)  # goal reached, but min cycle not over
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT  # the tick waits

    await common.async_set_temperature(hass, 21, "climate.test")  # the user acts
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF  # at once


async def test_fan_speed_reapply_follows_an_external_fan_change(
    hass: HomeAssistant,
) -> None:
    """Phase 6 (was "overrides today"): a fan speed changed on the AC's own remote
    is adopted as the new selection, so the next turn on re-applies that one."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    await hass.async_block_till_done()

    child._attr_fan_mode = "quiet"  # changed on the AC's own remote
    child.async_write_ha_state()
    await hass.async_block_till_done()
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"

    hass.states.async_set(SENSOR, 27.0)  # hot: the AC (re)starts
    await hass.async_block_till_done()
    hass.states.async_set(SENSOR, 20.0)
    await hass.async_block_till_done()
    hass.states.async_set(SENSOR, 27.0)
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["fan_mode"] == "quiet"
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"


async def test_fan_step_defaults_shared_climate_fan_flags_off_in_the_flow(
    mock_hass_flow,
) -> None:
    """The config flow fan step offers fan_on_with_ac/heater off for a shared climate."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = mock_hass_flow
    flow.collected_config = {
        "system_type": "heater_cooler",
        "heater": "climate.ac",
        "cooler": "climate.ac",
        "fan": "climate.ac",
    }

    form = await flow.async_step_fan()

    defaults = {
        str(k): k.default()
        for k in form["data_schema"].schema
        if getattr(k, "default", vol.UNDEFINED) is not vol.UNDEFINED
    }
    assert defaults["fan_on_with_ac"] is False
    assert defaults["fan_on_with_heater"] is False


@pytest.fixture
def mock_hass_flow():
    """A minimal hass for driving a config flow step directly."""
    from unittest.mock import Mock

    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass
