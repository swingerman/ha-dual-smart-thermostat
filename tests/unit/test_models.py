"""Tests for data models."""

import pytest

from custom_components.dual_smart_thermostat.models import (
    ACOnlyCoreSettings,
    FanFeatureSettings,
    FloorHeatingFeatureSettings,
    HeaterCoolerCoreSettings,
    HeatPumpCoreSettings,
    HumidityFeatureSettings,
    OpeningConfig,
    OpeningsFeatureSettings,
    PresetsFeatureSettings,
    SimpleHeaterCoreSettings,
    ThermostatConfig,
)


class TestCoreSettings:
    """Test core settings dataclasses."""

    def test_simple_heater_core_settings_to_dict(self):
        """Test simple_heater core settings serialization."""
        settings = SimpleHeaterCoreSettings(
            target_sensor="sensor.temp",
            heater="switch.heater",
            cold_tolerance=0.5,
            hot_tolerance=0.5,
            min_cycle_duration=600,
        )

        result = settings.to_dict()

        assert result == {
            "target_sensor": "sensor.temp",
            "heater": "switch.heater",
            "cold_tolerance": 0.5,
            "hot_tolerance": 0.5,
            "min_cycle_duration": 600,
        }

    def test_simple_heater_core_settings_from_dict(self):
        """Test simple_heater core settings deserialization."""
        data = {
            "target_sensor": "sensor.temp",
            "heater": "switch.heater",
            "cold_tolerance": 0.5,
            "hot_tolerance": 0.5,
            "min_cycle_duration": 600,
        }

        settings = SimpleHeaterCoreSettings.from_dict(data)

        assert settings.target_sensor == "sensor.temp"
        assert settings.heater == "switch.heater"
        assert settings.cold_tolerance == 0.5
        assert settings.hot_tolerance == 0.5
        assert settings.min_cycle_duration == 600

    def test_ac_only_core_settings_defaults(self):
        """Test ac_only core settings with defaults."""
        settings = ACOnlyCoreSettings(
            target_sensor="sensor.temp",
            heater="switch.ac",
        )

        assert settings.ac_mode is True
        assert settings.cold_tolerance == 0.3
        assert settings.hot_tolerance == 0.3
        assert settings.min_cycle_duration == 300

    def test_heater_cooler_core_settings_roundtrip(self):
        """Test heater_cooler core settings serialization roundtrip."""
        original = HeaterCoolerCoreSettings(
            target_sensor="sensor.temp",
            heater="switch.heater",
            cooler="switch.cooler",
            heat_cool_mode=True,
            cold_tolerance=0.2,
            hot_tolerance=0.2,
            min_cycle_duration=450,
        )

        data = original.to_dict()
        restored = HeaterCoolerCoreSettings.from_dict(data)

        assert restored.target_sensor == original.target_sensor
        assert restored.heater == original.heater
        assert restored.cooler == original.cooler
        assert restored.heat_cool_mode == original.heat_cool_mode
        assert restored.cold_tolerance == original.cold_tolerance

    def test_heat_pump_core_settings_with_entity_id(self):
        """Test heat_pump core settings with entity_id for heat_pump_cooling."""
        settings = HeatPumpCoreSettings(
            target_sensor="sensor.temp",
            heater="switch.heat_pump",
            heat_pump_cooling="binary_sensor.cooling_mode",
        )

        data = settings.to_dict()

        assert data["heat_pump_cooling"] == "binary_sensor.cooling_mode"

    def test_heat_pump_core_settings_with_boolean(self):
        """Test heat_pump core settings with boolean for heat_pump_cooling."""
        settings = HeatPumpCoreSettings(
            target_sensor="sensor.temp",
            heater="switch.heat_pump",
            heat_pump_cooling=True,
        )

        data = settings.to_dict()

        assert data["heat_pump_cooling"] is True


class TestFeatureSettings:
    """Test feature settings dataclasses."""

    def test_fan_feature_settings_defaults(self):
        """Test fan feature settings with defaults."""
        settings = FanFeatureSettings()

        assert settings.fan is None
        assert settings.fan_on_with_ac is True
        assert settings.fan_air_outside is False
        assert settings.fan_hot_tolerance_toggle is False

    def test_fan_feature_settings_roundtrip(self):
        """Test fan feature settings serialization roundtrip."""
        original = FanFeatureSettings(
            fan="fan.living_room",
            fan_on_with_ac=False,
            fan_air_outside=True,
            fan_hot_tolerance_toggle=True,
        )

        data = original.to_dict()
        restored = FanFeatureSettings.from_dict(data)

        assert restored.fan == original.fan
        assert restored.fan_on_with_ac == original.fan_on_with_ac
        assert restored.fan_air_outside == original.fan_air_outside
        assert restored.fan_hot_tolerance_toggle == original.fan_hot_tolerance_toggle

    def test_humidity_feature_settings_defaults(self):
        """Test humidity feature settings with defaults."""
        settings = HumidityFeatureSettings()

        assert settings.humidity_sensor is None
        assert settings.dryer is None
        assert settings.target_humidity == 50
        assert settings.min_humidity == 30
        assert settings.max_humidity == 99
        assert settings.dry_tolerance == 3
        assert settings.moist_tolerance == 3

    def test_humidity_feature_settings_roundtrip(self):
        """Test humidity feature settings serialization roundtrip."""
        original = HumidityFeatureSettings(
            humidity_sensor="sensor.humidity",
            dryer="switch.dehumidifier",
            target_humidity=60,
            min_humidity=40,
            max_humidity=80,
            dry_tolerance=5,
            moist_tolerance=5,
        )

        data = original.to_dict()
        restored = HumidityFeatureSettings.from_dict(data)

        assert restored.humidity_sensor == original.humidity_sensor
        assert restored.dryer == original.dryer
        assert restored.target_humidity == original.target_humidity
        assert restored.min_humidity == original.min_humidity
        assert restored.max_humidity == original.max_humidity
        assert restored.dry_tolerance == original.dry_tolerance
        assert restored.moist_tolerance == original.moist_tolerance

    def test_opening_config_roundtrip(self):
        """Test opening config serialization roundtrip."""
        original = OpeningConfig(
            entity_id="binary_sensor.window",
            timeout_open=60,
            timeout_close=45,
        )

        data = original.to_dict()
        restored = OpeningConfig.from_dict(data)

        assert restored.entity_id == original.entity_id
        assert restored.timeout_open == original.timeout_open
        assert restored.timeout_close == original.timeout_close

    def test_openings_feature_settings_empty(self):
        """Test openings feature settings with no openings."""
        settings = OpeningsFeatureSettings()

        assert settings.openings == []
        assert settings.openings_scope == "all"

    def test_openings_feature_settings_roundtrip(self):
        """Test openings feature settings serialization roundtrip."""
        original = OpeningsFeatureSettings(
            openings=[
                OpeningConfig("binary_sensor.window_1", 30, 30),
                OpeningConfig("binary_sensor.door", 45, 60),
            ],
            openings_scope="heat",
        )

        data = original.to_dict()
        restored = OpeningsFeatureSettings.from_dict(data)

        assert len(restored.openings) == 2
        assert restored.openings[0].entity_id == "binary_sensor.window_1"
        assert restored.openings[1].entity_id == "binary_sensor.door"
        assert restored.openings[1].timeout_open == 45
        assert restored.openings_scope == "heat"

    def test_floor_heating_feature_settings_defaults(self):
        """Test floor heating feature settings with defaults."""
        settings = FloorHeatingFeatureSettings()

        assert settings.floor_sensor is None
        assert settings.min_floor_temp == 5.0
        assert settings.max_floor_temp == 28.0

    def test_floor_heating_feature_settings_roundtrip(self):
        """Test floor heating feature settings serialization roundtrip."""
        original = FloorHeatingFeatureSettings(
            floor_sensor="sensor.floor_temp",
            min_floor_temp=10.0,
            max_floor_temp=30.0,
        )

        data = original.to_dict()
        restored = FloorHeatingFeatureSettings.from_dict(data)

        assert restored.floor_sensor == original.floor_sensor
        assert restored.min_floor_temp == original.min_floor_temp
        assert restored.max_floor_temp == original.max_floor_temp

    def test_presets_feature_settings_empty(self):
        """Test presets feature settings with no presets."""
        settings = PresetsFeatureSettings()

        assert settings.presets == []

    def test_presets_feature_settings_roundtrip(self):
        """Test presets feature settings serialization roundtrip."""
        original = PresetsFeatureSettings(
            presets=["home", "away", "comfort"],
        )

        data = original.to_dict()
        restored = PresetsFeatureSettings.from_dict(data)

        assert restored.presets == ["home", "away", "comfort"]


class TestThermostatConfig:
    """Test complete thermostat configuration."""

    def test_simple_heater_config_minimal(self):
        """Test minimal simple_heater configuration."""
        config = ThermostatConfig(
            name="Living Room",
            system_type="simple_heater",
            core_settings=SimpleHeaterCoreSettings(
                target_sensor="sensor.temp",
                heater="switch.heater",
            ),
        )

        data = config.to_dict()

        assert data["name"] == "Living Room"
        assert data["system_type"] == "simple_heater"
        assert data["core_settings"]["heater"] == "switch.heater"
        assert "fan_settings" not in data

    def test_simple_heater_config_roundtrip(self):
        """Test simple_heater configuration serialization roundtrip."""
        original = ThermostatConfig(
            name="Living Room",
            system_type="simple_heater",
            core_settings=SimpleHeaterCoreSettings(
                target_sensor="sensor.temp",
                heater="switch.heater",
                cold_tolerance=0.5,
            ),
        )

        data = original.to_dict()
        restored = ThermostatConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.system_type == original.system_type
        assert isinstance(restored.core_settings, SimpleHeaterCoreSettings)
        assert restored.core_settings.heater == "switch.heater"
        assert restored.core_settings.cold_tolerance == 0.5

    def test_ac_only_config_roundtrip(self):
        """Test ac_only configuration serialization roundtrip."""
        original = ThermostatConfig(
            name="Bedroom AC",
            system_type="ac_only",
            core_settings=ACOnlyCoreSettings(
                target_sensor="sensor.bedroom_temp",
                heater="switch.ac_unit",
                ac_mode=True,
            ),
        )

        data = original.to_dict()
        restored = ThermostatConfig.from_dict(data)

        assert restored.system_type == "ac_only"
        assert isinstance(restored.core_settings, ACOnlyCoreSettings)
        assert restored.core_settings.ac_mode is True

    def test_heater_cooler_config_with_features(self):
        """Test heater_cooler configuration with features."""
        original = ThermostatConfig(
            name="Main Climate",
            system_type="heater_cooler",
            core_settings=HeaterCoolerCoreSettings(
                target_sensor="sensor.temp",
                heater="switch.heater",
                cooler="switch.cooler",
                heat_cool_mode=True,
            ),
            fan_settings=FanFeatureSettings(
                fan="fan.main",
                fan_on_with_ac=True,
            ),
            humidity_settings=HumidityFeatureSettings(
                humidity_sensor="sensor.humidity",
                target_humidity=55,
            ),
        )

        data = original.to_dict()
        restored = ThermostatConfig.from_dict(data)

        assert restored.system_type == "heater_cooler"
        assert isinstance(restored.core_settings, HeaterCoolerCoreSettings)
        assert restored.core_settings.heat_cool_mode is True
        assert restored.fan_settings is not None
        assert restored.fan_settings.fan == "fan.main"
        assert restored.humidity_settings is not None
        assert restored.humidity_settings.target_humidity == 55

    def test_heat_pump_config_with_all_features(self):
        """Test heat_pump configuration with all features."""
        original = ThermostatConfig(
            name="Complete System",
            system_type="heat_pump",
            core_settings=HeatPumpCoreSettings(
                target_sensor="sensor.temp",
                heater="switch.heat_pump",
                heat_pump_cooling="binary_sensor.cooling",
            ),
            fan_settings=FanFeatureSettings(fan="fan.system"),
            humidity_settings=HumidityFeatureSettings(
                humidity_sensor="sensor.humidity",
            ),
            openings_settings=OpeningsFeatureSettings(
                openings=[
                    OpeningConfig("binary_sensor.window", 30, 30),
                ],
                openings_scope="heat_cool",
            ),
            floor_heating_settings=FloorHeatingFeatureSettings(
                floor_sensor="sensor.floor",
                min_floor_temp=10.0,
                max_floor_temp=25.0,
            ),
            presets_settings=PresetsFeatureSettings(
                presets=["home", "away"],
            ),
        )

        data = original.to_dict()
        restored = ThermostatConfig.from_dict(data)

        assert restored.system_type == "heat_pump"
        assert restored.fan_settings is not None
        assert restored.humidity_settings is not None
        assert restored.openings_settings is not None
        assert len(restored.openings_settings.openings) == 1
        assert restored.floor_heating_settings is not None
        assert restored.floor_heating_settings.min_floor_temp == 10.0
        assert restored.presets_settings is not None
        assert restored.presets_settings.presets == ["home", "away"]

    def test_invalid_system_type_raises_error(self):
        """Test that invalid system type raises ValueError."""
        data = {
            "name": "Test",
            "system_type": "invalid_type",
            "core_settings": {
                "target_sensor": "sensor.temp",
            },
        }

        with pytest.raises(ValueError, match="Unknown system type"):
            ThermostatConfig.from_dict(data)

    def test_config_preserves_none_values(self):
        """Test that optional None values are preserved."""
        original = ThermostatConfig(
            name="Test",
            system_type="simple_heater",
            core_settings=SimpleHeaterCoreSettings(
                target_sensor="sensor.temp",
                heater=None,  # Explicitly None
            ),
            fan_settings=None,
            humidity_settings=None,
        )

        data = original.to_dict()
        restored = ThermostatConfig.from_dict(data)

        assert restored.core_settings.heater is None
        assert restored.fan_settings is None
        assert restored.humidity_settings is None
