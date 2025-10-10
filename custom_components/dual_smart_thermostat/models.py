"""Data models for Dual Smart Thermostat configuration.

This module provides type-safe dataclasses representing the canonical data model
for each system type and feature configuration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# System type constants
SYSTEM_TYPE_SIMPLE_HEATER = "simple_heater"
SYSTEM_TYPE_AC_ONLY = "ac_only"
SYSTEM_TYPE_HEATER_COOLER = "heater_cooler"
SYSTEM_TYPE_HEAT_PUMP = "heat_pump"


@dataclass
class CoreSettingsBase:
    """Base core settings shared by all system types."""

    target_sensor: str
    cold_tolerance: float = 0.3
    hot_tolerance: float = 0.3
    min_cycle_duration: int = 300  # seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CoreSettingsBase:
        """Create instance from dictionary."""
        # Collect all annotations from the class hierarchy
        all_annotations = {}
        for klass in reversed(cls.__mro__):
            if hasattr(klass, "__annotations__"):
                all_annotations.update(klass.__annotations__)
        return cls(**{k: v for k, v in data.items() if k in all_annotations})


@dataclass
class SimpleHeaterCoreSettings(CoreSettingsBase):
    """Core settings for simple_heater system type."""

    heater: str | None = None


@dataclass
class ACOnlyCoreSettings(CoreSettingsBase):
    """Core settings for ac_only system type."""

    heater: str | None = None  # Reuses heater field for AC switch
    ac_mode: bool = True


@dataclass
class HeaterCoolerCoreSettings(CoreSettingsBase):
    """Core settings for heater_cooler system type."""

    heater: str | None = None
    cooler: str | None = None
    heat_cool_mode: bool = False


@dataclass
class HeatPumpCoreSettings(CoreSettingsBase):
    """Core settings for heat_pump system type."""

    heater: str | None = None
    heat_pump_cooling: str | bool | None = None  # entity_id or boolean


@dataclass
class FanFeatureSettings:
    """Fan feature settings."""

    fan: str | None = None  # fan entity_id
    fan_on_with_ac: bool = True
    fan_air_outside: bool = False
    fan_hot_tolerance_toggle: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FanFeatureSettings:
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class HumidityFeatureSettings:
    """Humidity feature settings."""

    humidity_sensor: str | None = None
    dryer: str | None = None
    target_humidity: int = 50
    min_humidity: int = 30
    max_humidity: int = 99
    dry_tolerance: int = 3
    moist_tolerance: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HumidityFeatureSettings:
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class OpeningConfig:
    """Configuration for a single opening (window/door sensor)."""

    entity_id: str
    timeout_open: int = 30  # seconds
    timeout_close: int = 30  # seconds

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpeningConfig:
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class OpeningsFeatureSettings:
    """Openings feature settings."""

    openings: list[OpeningConfig] = field(default_factory=list)
    openings_scope: str = "all"  # all, heat, cool, heat_cool, fan_only, dry

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "openings": [opening.to_dict() for opening in self.openings],
            "openings_scope": self.openings_scope,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OpeningsFeatureSettings:
        """Create instance from dictionary."""
        openings_data = data.get("openings", [])
        openings = [OpeningConfig.from_dict(o) for o in openings_data]
        return cls(
            openings=openings,
            openings_scope=data.get("openings_scope", "all"),
        )


@dataclass
class FloorHeatingFeatureSettings:
    """Floor heating feature settings."""

    floor_sensor: str | None = None
    min_floor_temp: float = 5.0
    max_floor_temp: float = 28.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FloorHeatingFeatureSettings:
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class PresetConfig:
    """Configuration for a single preset."""

    name: str
    temperature: float | None = None  # For single temp mode
    temperature_low: float | None = None  # For heat_cool mode
    temperature_high: float | None = None  # For heat_cool mode

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetConfig:
        """Create instance from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class PresetsFeatureSettings:
    """Presets feature settings."""

    presets: list[str] = field(default_factory=list)  # List of preset keys

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"presets": self.presets}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PresetsFeatureSettings:
        """Create instance from dictionary."""
        return cls(presets=data.get("presets", []))


@dataclass
class ThermostatConfig:
    """Complete thermostat configuration."""

    name: str
    system_type: str
    core_settings: (
        SimpleHeaterCoreSettings
        | ACOnlyCoreSettings
        | HeaterCoolerCoreSettings
        | HeatPumpCoreSettings
    )
    fan_settings: FanFeatureSettings | None = None
    humidity_settings: HumidityFeatureSettings | None = None
    openings_settings: OpeningsFeatureSettings | None = None
    floor_heating_settings: FloorHeatingFeatureSettings | None = None
    presets_settings: PresetsFeatureSettings | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "system_type": self.system_type,
            "core_settings": self.core_settings.to_dict(),
        }

        if self.fan_settings:
            result["fan_settings"] = self.fan_settings.to_dict()
        if self.humidity_settings:
            result["humidity_settings"] = self.humidity_settings.to_dict()
        if self.openings_settings:
            result["openings_settings"] = self.openings_settings.to_dict()
        if self.floor_heating_settings:
            result["floor_heating_settings"] = self.floor_heating_settings.to_dict()
        if self.presets_settings:
            result["presets_settings"] = self.presets_settings.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThermostatConfig:
        """Create instance from dictionary."""
        system_type = data["system_type"]

        # Create appropriate core settings based on system type
        core_data = data["core_settings"]
        if system_type == SYSTEM_TYPE_SIMPLE_HEATER:
            core_settings = SimpleHeaterCoreSettings.from_dict(core_data)
        elif system_type == SYSTEM_TYPE_AC_ONLY:
            core_settings = ACOnlyCoreSettings.from_dict(core_data)
        elif system_type == SYSTEM_TYPE_HEATER_COOLER:
            core_settings = HeaterCoolerCoreSettings.from_dict(core_data)
        elif system_type == SYSTEM_TYPE_HEAT_PUMP:
            core_settings = HeatPumpCoreSettings.from_dict(core_data)
        else:
            raise ValueError(f"Unknown system type: {system_type}")

        # Parse optional feature settings
        fan_settings = None
        if "fan_settings" in data:
            fan_settings = FanFeatureSettings.from_dict(data["fan_settings"])

        humidity_settings = None
        if "humidity_settings" in data:
            humidity_settings = HumidityFeatureSettings.from_dict(
                data["humidity_settings"]
            )

        openings_settings = None
        if "openings_settings" in data:
            openings_settings = OpeningsFeatureSettings.from_dict(
                data["openings_settings"]
            )

        floor_heating_settings = None
        if "floor_heating_settings" in data:
            floor_heating_settings = FloorHeatingFeatureSettings.from_dict(
                data["floor_heating_settings"]
            )

        presets_settings = None
        if "presets_settings" in data:
            presets_settings = PresetsFeatureSettings.from_dict(
                data["presets_settings"]
            )

        return cls(
            name=data["name"],
            system_type=system_type,
            core_settings=core_settings,
            fan_settings=fan_settings,
            humidity_settings=humidity_settings,
            openings_settings=openings_settings,
            floor_heating_settings=floor_heating_settings,
            presets_settings=presets_settings,
        )
