"""Tests for the climate role helpers."""

from custom_components.dual_smart_thermostat.climate_roles import (
    is_climate_entity,
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
    """Heat pump and aux heater cannot be climate-backed yet."""
    assert unsupported_climate_roles(
        {"heater": "climate.hp", "heat_pump_cooling": "binary_sensor.c"}
    ) == ["heater"]
    assert unsupported_climate_roles(
        {"heater": "switch.h", "secondary_heater": "climate.aux"}
    ) == ["secondary_heater"]
    assert unsupported_climate_roles({"heater": "climate.h"}) == []
    assert unsupported_climate_roles({"cooler": "climate.ac"}) == []
