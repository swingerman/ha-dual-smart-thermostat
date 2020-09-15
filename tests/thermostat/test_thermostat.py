from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_PRESET_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_UNAVAILABLE

from custom_components.dual_smart_thermostat.climate import DualSmartThermostat
from ..helpers import assert_device_properties_set


class TestDualSmartThermostat(IsolatedAsyncioTestCase):
    def setUp(self):
        self.subject = DualSmartThermostat()

    def test_supported_features(self):
        self.assertEqual(
            self.subject.supported_features,
            SUPPORT_TARGET_TEMPERATURE
            | SUPPORT_PRESET_MODE
            | SUPPORT_TARGET_TEMPERATURE_RANGE,
        )
