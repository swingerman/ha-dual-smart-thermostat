"""Unit tests for FloorTempLimitEnv via TempEnv / PresetEnv floor limits."""

import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
)
from custom_components.dual_smart_thermostat.preset_env.preset_env import (
    PresetEnv,
)


def test_zero_values_are_kept():
    env = PresetEnv(**{CONF_MIN_FLOOR_TEMP: 0, CONF_MAX_FLOOR_TEMP: 0})
    assert env.min_floor_temp == 0
    assert env.max_floor_temp == 0


def test_unset_values_are_none():
    env = PresetEnv()
    assert env.min_floor_temp is None
    assert env.max_floor_temp is None


@pytest.mark.parametrize(
    "kwargs",
    [{CONF_MIN_FLOOR_TEMP: 0}, {CONF_MAX_FLOOR_TEMP: 0}],
)
def test_preset_env_zero_counts_as_floor_limit(kwargs):
    assert PresetEnv(**kwargs).has_floor_temp_limits() is True


def test_preset_env_without_limits():
    assert PresetEnv().has_floor_temp_limits() is False
