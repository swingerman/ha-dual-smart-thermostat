"""Tests for the climate role helpers."""

from custom_components.dual_smart_thermostat.climate_roles import (
    applicable_offset_keys,
    climate_control_keys,
    drop_inapplicable,
    is_climate_entity,
    sensor_required,
    unsupported_climate_roles,
)


def test_is_climate_entity_by_domain() -> None:
    """Climate-ness is decided by entity domain alone."""
    assert is_climate_entity("climate.living_room_ac")
    assert not is_climate_entity("switch.living_room_ac")
    assert not is_climate_entity("input_boolean.heater")
    assert not is_climate_entity("not_an_entity_id")
    assert not is_climate_entity(None)


def test_unsupported_climate_roles() -> None:
    """Only the aux heater cannot be climate-backed."""
    assert (
        unsupported_climate_roles(
            {"heater": "climate.hp", "heat_pump_cooling": "binary_sensor.c"}
        )
        == []
    )
    assert unsupported_climate_roles(
        {"heater": "switch.h", "secondary_heater": "climate.aux"}
    ) == ["secondary_heater"]
    assert unsupported_climate_roles({"heater": "climate.h"}) == []
    assert unsupported_climate_roles({"cooler": "climate.ac"}) == []


def test_heat_pump_heater_keeps_its_offset_even_with_ac_mode():
    """The heat pump clause decides, not ac_mode (a heat pump heats and cools)."""
    assert applicable_offset_keys(
        {
            "heater": "climate.hp",
            "ac_mode": True,
            "heat_pump_cooling": "binary_sensor.c",
        }
    ) == ["heater_setpoint_offset", "cooler_setpoint_offset"]
    assert applicable_offset_keys({"heater": "climate.hp", "ac_mode": True}) == [
        "cooler_setpoint_offset"
    ]


def test_control_style_only_matters_for_heater_or_cooler():
    """Fan and dryer are always on_off: no style to choose for them."""
    assert climate_control_keys({"heater": "switch.h", "fan": "climate.f"}) == []
    assert climate_control_keys({"dryer": "climate.d"}) == []
    assert climate_control_keys({"heater": "switch.h", "cooler": "climate.ac"}) == [
        "control_style",
        "cooler_setpoint_offset",
    ]


def test_drop_inapplicable_removes_stale_climate_keys():
    """Keys whose role stopped being a climate entity are removed, others kept."""
    config = {
        "heater": "switch.h",
        "cooler": "climate.ac",
        "control_style": "setpoint",
        "heater_setpoint_offset": 1.0,
        "cooler_setpoint_offset": 2.0,
        "name": "T",
    }
    assert drop_inapplicable(config) == {
        "heater": "switch.h",
        "cooler": "climate.ac",
        "control_style": "setpoint",
        "cooler_setpoint_offset": 2.0,
        "name": "T",
    }
    assert "heater_setpoint_offset" in config  # the input is not mutated
    assert drop_inapplicable({"heater": "switch.h", "control_style": "on_off"}) == {
        "heater": "switch.h"
    }


def test_sensor_required_unless_a_climate_role_supplies_it():
    """The one rule behind YAML validation and the flows."""
    assert sensor_required({"heater": "switch.h"}) is True
    assert sensor_required({"heater": "switch.h", "target_sensor": "sensor.t"}) is False
    assert sensor_required({"heater": "switch.h", "cooler": "climate.ac"}) is False
