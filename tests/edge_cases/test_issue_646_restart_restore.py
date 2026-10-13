"""Issue #646: restart restore left no setpoint / the other mode's setpoint.

A single-setpoint mode (heat/cool) with an active range-only preset
(target_temp_low/high, no ``temperature``) must restore the preset's bound
for the restored mode, never ``temperature: null``.
"""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import CoreState, HomeAssistant, State
from homeassistant.setup import async_setup_component
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests import common


@pytest.mark.parametrize(
    ("mode", "expected"), [(HVACMode.COOL, 25.0), (HVACMode.HEAT, 18.0)]
)
async def test_restore_range_preset_in_single_mode(
    hass: HomeAssistant, mode: HVACMode, expected: float
) -> None:
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test",
                mode,
                {
                    "preset_mode": "sleep",
                    "temperature": None,
                    "target_temp_low": 18,
                    "target_temp_high": 25,
                },
            ),
        ),
    )
    hass.set_state(CoreState.starting)
    hass.states.async_set(common.ENT_SENSOR, 21)
    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
                "sleep": {"target_temp_low": 18, "target_temp_high": 25},
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test")
    assert state.state == mode
    assert state.attributes["preset_mode"] == "sleep"
    assert state.attributes["temperature"] == expected
