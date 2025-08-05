#!/usr/bin/env python3
"""
Focused Configuration Parameter Dependencies for Dual Smart Thermostat

This script identifies and documents only the critical conditional dependencies
where configuration parameters only make sense when other parameters are set.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Dict, List, Optional


class DependencyType(Enum):
    """Focused dependency types for configuration parameters."""

    REQUIRES = "requires"  # A requires B to function
    ENABLES = "enables"  # A enables B functionality
    CONDITIONAL = "conditional"  # A is only used if B is set
    MUTUAL_EXCLUSIVE = "mutual_exclusive"  # Only one of A or B can be used


@dataclass
class ConfigParameter:
    """Configuration parameter with focused metadata."""

    name: str
    description: str
    condition: Optional[str] = None  # When this parameter is relevant
    enabled_by: Optional[str] = None  # What parameter enables this
    requires: List[str] = field(default_factory=list)  # Required parameters
    conflicts_with: List[str] = field(default_factory=list)  # Conflicting parameters


@dataclass
class ConfigDependency:
    """Represents a configuration dependency relationship."""

    source: str
    target: str
    type: DependencyType
    description: str
    example: Optional[str] = None


class FocusedConfigDependencies:
    """Critical configuration parameter dependencies only."""

    def __init__(self):
        self.parameters: Dict[str, ConfigParameter] = {}
        self.dependencies: List[ConfigDependency] = []
        self._initialize_critical_dependencies()

    def _initialize_critical_dependencies(self):
        """Initialize only the critical conditional dependencies."""

        # === SECONDARY HEATING DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="secondary_heater",
                    target="secondary_heater_timeout",
                    type=DependencyType.ENABLES,
                    description="Secondary heater timeout only works when secondary heater is defined",
                    example="secondary_heater: switch.aux_heater → secondary_heater_timeout: '00:05:00'",
                ),
                ConfigDependency(
                    source="secondary_heater",
                    target="secondary_heater_dual_mode",
                    type=DependencyType.ENABLES,
                    description="Dual mode operation only works when secondary heater is defined",
                    example="secondary_heater: switch.aux_heater → secondary_heater_dual_mode: true",
                ),
            ]
        )

        # === FLOOR HEATING DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="floor_sensor",
                    target="max_floor_temp",
                    type=DependencyType.ENABLES,
                    description="Floor temperature limits only work when floor sensor is defined",
                    example="floor_sensor: sensor.floor_temp → max_floor_temp: 28",
                ),
                ConfigDependency(
                    source="floor_sensor",
                    target="min_floor_temp",
                    type=DependencyType.ENABLES,
                    description="Minimum floor temperature only works when floor sensor is defined",
                    example="floor_sensor: sensor.floor_temp → min_floor_temp: 5",
                ),
            ]
        )

        # === COOLING MODE DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="cooler",
                    target="ac_mode",
                    type=DependencyType.MUTUAL_EXCLUSIVE,
                    description="AC mode is ignored when separate cooler entity is defined",
                    example="If cooler: switch.ac_unit is set, ac_mode setting is ignored",
                ),
                ConfigDependency(
                    source="heat_cool_mode",
                    target="target_temp_low",
                    type=DependencyType.ENABLES,
                    description="Low temperature setting only works in heat/cool mode",
                    example="heat_cool_mode: true → target_temp_low: 18",
                ),
                ConfigDependency(
                    source="heat_cool_mode",
                    target="target_temp_high",
                    type=DependencyType.ENABLES,
                    description="High temperature setting only works in heat/cool mode",
                    example="heat_cool_mode: true → target_temp_high: 24",
                ),
            ]
        )

        # === FAN CONTROL DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="fan",
                    target="fan_mode",
                    type=DependencyType.ENABLES,
                    description="Fan mode only works when fan entity is defined",
                    example="fan: switch.ceiling_fan → fan_mode: true",
                ),
                ConfigDependency(
                    source="fan",
                    target="fan_on_with_ac",
                    type=DependencyType.ENABLES,
                    description="Fan with AC only works when fan entity is defined",
                    example="fan: switch.ceiling_fan → fan_on_with_ac: true",
                ),
                ConfigDependency(
                    source="fan",
                    target="fan_hot_tolerance",
                    type=DependencyType.ENABLES,
                    description="Fan temperature tolerance only works when fan entity is defined",
                    example="fan: switch.ceiling_fan → fan_hot_tolerance: 1.0",
                ),
                ConfigDependency(
                    source="fan",
                    target="fan_hot_tolerance_toggle",
                    type=DependencyType.ENABLES,
                    description="Fan tolerance toggle only works when fan entity is defined",
                    example="fan: switch.ceiling_fan → fan_hot_tolerance_toggle: input_boolean.fan_auto",
                ),
                ConfigDependency(
                    source="outside_sensor",
                    target="fan_air_outside",
                    type=DependencyType.ENABLES,
                    description="Fan air outside control only works when outside sensor is defined",
                    example="outside_sensor: sensor.outdoor_temp → fan_air_outside: true",
                ),
            ]
        )

        # === HUMIDITY CONTROL DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="humidity_sensor",
                    target="target_humidity",
                    type=DependencyType.ENABLES,
                    description="Target humidity only works when humidity sensor is defined",
                    example="humidity_sensor: sensor.room_humidity → target_humidity: 50",
                ),
                ConfigDependency(
                    source="humidity_sensor",
                    target="min_humidity",
                    type=DependencyType.ENABLES,
                    description="Minimum humidity only works when humidity sensor is defined",
                    example="humidity_sensor: sensor.room_humidity → min_humidity: 30",
                ),
                ConfigDependency(
                    source="humidity_sensor",
                    target="max_humidity",
                    type=DependencyType.ENABLES,
                    description="Maximum humidity only works when humidity sensor is defined",
                    example="humidity_sensor: sensor.room_humidity → max_humidity: 70",
                ),
                ConfigDependency(
                    source="dryer",
                    target="dry_tolerance",
                    type=DependencyType.ENABLES,
                    description="Dry tolerance only works when dryer entity is defined",
                    example="dryer: switch.dehumidifier → dry_tolerance: 5",
                ),
                ConfigDependency(
                    source="dryer",
                    target="moist_tolerance",
                    type=DependencyType.ENABLES,
                    description="Moist tolerance only works when dryer entity is defined",
                    example="dryer: switch.dehumidifier → moist_tolerance: 5",
                ),
            ]
        )

        # === POWER MANAGEMENT DEPENDENCIES ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="hvac_power_levels",
                    target="hvac_power_min",
                    type=DependencyType.ENABLES,
                    description="Minimum power level only works when power levels are defined",
                    example="hvac_power_levels: 5 → hvac_power_min: 1",
                ),
                ConfigDependency(
                    source="hvac_power_levels",
                    target="hvac_power_max",
                    type=DependencyType.ENABLES,
                    description="Maximum power level only works when power levels are defined",
                    example="hvac_power_levels: 5 → hvac_power_max: 100",
                ),
                ConfigDependency(
                    source="hvac_power_levels",
                    target="hvac_power_tolerance",
                    type=DependencyType.ENABLES,
                    description="Power tolerance only works when power levels are defined",
                    example="hvac_power_levels: 5 → hvac_power_tolerance: 0.5",
                ),
            ]
        )

        # === ENTITY CONFLICTS ===
        self.dependencies.extend(
            [
                ConfigDependency(
                    source="heater",
                    target="target_sensor",
                    type=DependencyType.MUTUAL_EXCLUSIVE,
                    description="Heater and temperature sensor must be different entities",
                    example="heater: switch.heater ≠ target_sensor: sensor.temp (must be different)",
                ),
                ConfigDependency(
                    source="heater",
                    target="cooler",
                    type=DependencyType.MUTUAL_EXCLUSIVE,
                    description="Heater and cooler must be different entities when both are defined",
                    example="heater: switch.heater ≠ cooler: switch.ac (must be different)",
                ),
            ]
        )

    def get_conditional_parameters(self) -> Dict[str, List[str]]:
        """Get parameters that are conditional on others."""
        conditional_map = {}

        for dep in self.dependencies:
            if dep.type in [DependencyType.ENABLES, DependencyType.CONDITIONAL]:
                if dep.source not in conditional_map:
                    conditional_map[dep.source] = []
                conditional_map[dep.source].append(dep.target)

        return conditional_map

    def get_parameter_condition(self, param_name: str) -> Optional[str]:
        """Get the condition under which a parameter is relevant."""
        for dep in self.dependencies:
            if dep.target == param_name and dep.type in [
                DependencyType.ENABLES,
                DependencyType.CONDITIONAL,
            ]:
                return f"Only relevant when '{dep.source}' is configured"
        return None

    def generate_conditional_guide(self) -> Dict:
        """Generate a guide for conditional parameters."""
        guide = {
            "conditional_parameters": {},
            "dependency_groups": {},
            "configuration_examples": {},
        }

        # Group by dependency type
        for dep in self.dependencies:
            if dep.type.value not in guide["dependency_groups"]:
                guide["dependency_groups"][dep.type.value] = []

            guide["dependency_groups"][dep.type.value].append(
                {
                    "source": dep.source,
                    "target": dep.target,
                    "description": dep.description,
                    "example": dep.example,
                }
            )

        # Create conditional parameters map
        for dep in self.dependencies:
            if dep.type in [DependencyType.ENABLES, DependencyType.CONDITIONAL]:
                guide["conditional_parameters"][dep.target] = {
                    "required_parameter": dep.source,
                    "description": dep.description,
                    "example": dep.example,
                }

        # Configuration examples
        guide["configuration_examples"] = {
            "floor_heating": {
                "description": "Floor heating with temperature protection",
                "required": ["floor_sensor"],
                "optional": ["max_floor_temp", "min_floor_temp"],
                "example": {
                    "floor_sensor": "sensor.floor_temperature",
                    "max_floor_temp": 28,
                    "min_floor_temp": 5,
                },
            },
            "two_stage_heating": {
                "description": "Two-stage heating with auxiliary heater",
                "required": ["secondary_heater"],
                "optional": ["secondary_heater_timeout", "secondary_heater_dual_mode"],
                "example": {
                    "secondary_heater": "switch.aux_heater",
                    "secondary_heater_timeout": "00:05:00",
                    "secondary_heater_dual_mode": True,
                },
            },
            "fan_control": {
                "description": "Fan control with advanced features",
                "required": ["fan"],
                "optional": [
                    "fan_mode",
                    "fan_on_with_ac",
                    "fan_hot_tolerance",
                    "fan_hot_tolerance_toggle",
                ],
                "example": {
                    "fan": "switch.ceiling_fan",
                    "fan_mode": True,
                    "fan_on_with_ac": True,
                    "fan_hot_tolerance": 1.0,
                },
            },
            "humidity_control": {
                "description": "Humidity control with dry mode",
                "required": ["humidity_sensor", "dryer"],
                "optional": [
                    "target_humidity",
                    "min_humidity",
                    "max_humidity",
                    "dry_tolerance",
                    "moist_tolerance",
                ],
                "example": {
                    "humidity_sensor": "sensor.room_humidity",
                    "dryer": "switch.dehumidifier",
                    "target_humidity": 50,
                    "dry_tolerance": 5,
                    "moist_tolerance": 3,
                },
            },
            "heat_cool_mode": {
                "description": "Heat/Cool mode with temperature ranges",
                "required": ["heat_cool_mode"],
                "optional": ["target_temp_low", "target_temp_high"],
                "example": {
                    "heat_cool_mode": True,
                    "target_temp_low": 18,
                    "target_temp_high": 24,
                },
            },
            "power_management": {
                "description": "HVAC power level management",
                "required": ["hvac_power_levels"],
                "optional": [
                    "hvac_power_min",
                    "hvac_power_max",
                    "hvac_power_tolerance",
                ],
                "example": {
                    "hvac_power_levels": 5,
                    "hvac_power_min": 20,
                    "hvac_power_max": 100,
                    "hvac_power_tolerance": 0.5,
                },
            },
        }

        return guide


def main():
    """Generate focused configuration dependency analysis."""
    config_deps = FocusedConfigDependencies()

    # Generate the focused guide
    guide = config_deps.generate_conditional_guide()

    # Save to JSON
    with open(
        "/workspaces/dual_smart_thermostat/focused_config_dependencies.json", "w"
    ) as f:
        json.dump(guide, f, indent=2)

    # Print analysis
    print("🎯 Focused Configuration Parameter Dependencies")
    print("=" * 55)
    print(f"Total conditional dependencies: {len(config_deps.dependencies)}")
    print()

    print("📋 Dependency Types:")
    dep_types = {}
    for dep in config_deps.dependencies:
        dep_types[dep.type.value] = dep_types.get(dep.type.value, 0) + 1

    for dep_type, count in sorted(dep_types.items()):
        print(f"  {dep_type}: {count} dependencies")
    print()

    print("🔗 Key Conditional Relationships:")
    print()

    # Group by enabling parameter
    enabling_params = {}
    for dep in config_deps.dependencies:
        if dep.type == DependencyType.ENABLES:
            if dep.source not in enabling_params:
                enabling_params[dep.source] = []
            enabling_params[dep.source].append(dep.target)

    for source, targets in enabling_params.items():
        print(f"  📌 {source}")
        for target in targets:
            print(f"     └─ enables → {target}")
        print()

    print("⚠️  Critical Conflicts:")
    for dep in config_deps.dependencies:
        if dep.type == DependencyType.MUTUAL_EXCLUSIVE:
            print(f"  ❌ {dep.source} ↔ {dep.target}: {dep.description}")
    print()

    print("📝 Configuration Examples Generated:")
    for example_name in guide["configuration_examples"]:
        example = guide["configuration_examples"][example_name]
        print(f"  • {example_name}: {example['description']}")
    print()

    print("Files generated:")
    print(
        "  📄 focused_config_dependencies.json - Conditional dependencies and examples"
    )


if __name__ == "__main__":
    main()
