#!/usr/bin/env python3
"""
Configuration Dependency Validator for Dual Smart Thermostat

This script validates configurations against critical parameter dependencies,
focusing only on parameters that require other parameters to function.
"""

from typing import Any, Dict, List, Tuple

import yaml


class ConfigValidator:
    """Validates configuration against critical dependencies.

    Note: This validator checks parameter-level dependencies (e.g., max_floor_temp
    requires floor_sensor). It does NOT validate preset temperature VALUES, including
    templates. Template validation is handled by the config flow validator
    (schemas.py:validate_template_or_number). Preset parameters (away_temp, eco_temp,
    etc.) can contain static numeric values or template strings, and this validator
    correctly treats them as values rather than dependencies.
    """

    def __init__(self):
        self.conditional_dependencies = {
            # Secondary heating dependencies
            "secondary_heater_timeout": "secondary_heater",
            "secondary_heater_dual_mode": "secondary_heater",
            # Floor heating dependencies
            "max_floor_temp": "floor_sensor",
            "min_floor_temp": "floor_sensor",
            # Heat/cool mode dependencies
            "target_temp_low": "heat_cool_mode",
            "target_temp_high": "heat_cool_mode",
            # Fan control dependencies
            "fan_mode": "fan",
            "fan_on_with_ac": "fan",
            "fan_hot_tolerance": "fan",
            "fan_hot_tolerance_toggle": "fan",
            "fan_air_outside": "outside_sensor",
            # Humidity control dependencies
            "target_humidity": "humidity_sensor",
            "min_humidity": "humidity_sensor",
            "max_humidity": "humidity_sensor",
            "dry_tolerance": "dryer",
            "moist_tolerance": "dryer",
            # Power management dependencies
            "hvac_power_min": "hvac_power_levels",
            "hvac_power_max": "hvac_power_levels",
            "hvac_power_tolerance": "hvac_power_levels",
        }

        self.conflicts = [
            (
                "heater",
                "target_sensor",
                "Heater and temperature sensor must be different entities",
            ),
            ("heater", "cooler", "Heater and cooler must be different entities"),
        ]

        # Climate-backed devices: options that need a climate role, and the roles
        # whose entity may be a climate (mirrors climate_roles.py: CLIMATE_ROLE_KEYS
        # and CLIMATE_OPTION_KEYS; the offsets have their own role, see below).
        self.climate_role_keys = ["heater", "cooler", "fan", "dryer"]
        self.climate_role_parameters = ["control_style", "follow_device_changes"]
        self.climate_offset_parameters = [
            "heater_setpoint_offset",
            "cooler_setpoint_offset",
        ]

        self.overrides = [
            ("cooler", "ac_mode", "AC mode is ignored when cooler is defined"),
        ]

    def validate_config(
        self, config: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration against dependencies.

        Returns:
            (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Check conditional dependencies
        for param, required_param in self.conditional_dependencies.items():
            if param in config and config[param] is not None:
                if required_param not in config or config[required_param] is None:
                    errors.append(
                        f"Parameter '{param}' requires '{required_param}' to be configured"
                    )

        # Climate-backed device options need a climate role
        errors.extend(self._climate_errors(config))

        # Check conflicts
        for param1, param2, message in self.conflicts:
            if (
                param1 in config
                and param2 in config
                and config[param1] is not None
                and config[param2] is not None
            ):
                # A climate entity may legitimately fill several roles
                if config[param1] == config[param2] and not self._is_climate(
                    config[param1]
                ):
                    errors.append(
                        f"Conflict: {message} (both set to '{config[param1]}')"
                    )

        # Check overrides
        for primary, secondary, message in self.overrides:
            if (
                primary in config
                and secondary in config
                and config[primary] is not None
                and config[secondary] is not None
            ):
                warnings.append(f"Warning: {message}")

        return len(errors) == 0, errors, warnings

    @staticmethod
    def _is_climate(value: Any) -> bool:
        return str(value or "").startswith("climate.")

    def _climate_errors(self, config: dict[str, Any]) -> list[str]:
        """Rules for climate-backed devices (the same ones climate_roles.py applies)."""
        errors = []

        def is_climate(key: str) -> bool:
            return self._is_climate(config.get(key))

        has_climate_role = any(is_climate(key) for key in self.climate_role_keys)

        for param in self.climate_role_parameters:
            if config.get(param) is not None and not has_climate_role:
                errors.append(
                    f"Parameter '{param}' requires heater, cooler, fan or dryer "
                    "to be a climate entity"
                )

        ac_only = bool(config.get("ac_mode")) and not config.get("cooler")
        heat_pump = bool(config.get("heat_pump_cooling"))
        offset_ok = {
            "heater_setpoint_offset": is_climate("heater")
            and (not ac_only or heat_pump),
            "cooler_setpoint_offset": is_climate("cooler")
            or (is_climate("heater") and (ac_only or heat_pump)),
        }
        for param, ok in offset_ok.items():
            if config.get(param) is not None and not ok:
                errors.append(
                    f"Parameter '{param}' requires its own role to be a climate entity"
                )

        if (
            config.get("control_style") == "setpoint"
            and has_climate_role
            and not (is_climate("heater") or is_climate("cooler"))
        ):
            errors.append(
                "Parameter 'control_style: setpoint' needs heater or cooler to be a "
                "climate entity"
            )
        if (
            config.get("control_style") == "setpoint"
            and heat_pump
            and is_climate("heater")
        ):
            errors.append(
                "Parameter 'control_style: setpoint' is not supported for a climate "
                "heat pump"
            )
        if (
            config.get("control_style") == "setpoint"
            and is_climate("heater")
            and config.get("heater") == config.get("cooler")
            and (
                config.get("heat_cool_mode")
                or (
                    config.get("target_temp_low") is not None
                    and config.get("target_temp_high") is not None
                )
            )
        ):
            errors.append(
                "Parameter 'control_style: setpoint' cannot do heat_cool with one "
                "climate as both heater and cooler"
            )
        if self._is_climate(config.get("secondary_heater")):
            errors.append("Parameter 'secondary_heater' cannot be a climate entity")
        if not config.get("target_sensor") and not has_climate_role:
            errors.append(
                "Parameter 'target_sensor' is required unless heater, cooler, fan or "
                "dryer is a climate entity"
            )
        return errors

    def suggest_fixes(self, config: Dict[str, Any]) -> List[str]:
        """Suggest fixes for configuration issues."""
        suggestions = []

        # Find orphaned conditional parameters
        for param, required_param in self.conditional_dependencies.items():
            if param in config and config[param] is not None:
                if required_param not in config or config[required_param] is None:
                    suggestions.append(
                        f"Add '{required_param}' to enable '{param}' functionality"
                    )

        for error in self._climate_errors(config):
            suggestions.append(f"Fix: {error}")

        return suggestions

    def get_feature_groups(self, config: Dict[str, Any]) -> Dict[str, Dict]:
        """Analyze configuration by feature groups."""
        features = {
            "secondary_heating": {
                "enabled": config.get("secondary_heater") is not None,
                "parameters": [
                    "secondary_heater",
                    "secondary_heater_timeout",
                    "secondary_heater_dual_mode",
                ],
                "configured": [],
            },
            "floor_protection": {
                "enabled": config.get("floor_sensor") is not None,
                "parameters": ["floor_sensor", "max_floor_temp", "min_floor_temp"],
                "configured": [],
            },
            "heat_cool_mode": {
                "enabled": config.get("heat_cool_mode", False),
                "parameters": ["heat_cool_mode", "target_temp_low", "target_temp_high"],
                "configured": [],
            },
            "fan_control": {
                "enabled": config.get("fan") is not None,
                "parameters": [
                    "fan",
                    "fan_mode",
                    "fan_on_with_ac",
                    "fan_hot_tolerance",
                    "fan_hot_tolerance_toggle",
                ],
                "configured": [],
            },
            "humidity_control": {
                "enabled": config.get("humidity_sensor") is not None
                or config.get("dryer") is not None,
                "parameters": [
                    "humidity_sensor",
                    "dryer",
                    "target_humidity",
                    "min_humidity",
                    "max_humidity",
                    "dry_tolerance",
                    "moist_tolerance",
                ],
                "configured": [],
            },
            "climate_devices": {
                "enabled": any(
                    self._is_climate(config.get(key)) for key in self.climate_role_keys
                ),
                "parameters": [
                    *self.climate_role_parameters,
                    *self.climate_offset_parameters,
                ],
                "configured": [],
            },
            "power_management": {
                "enabled": config.get("hvac_power_levels") is not None,
                "parameters": [
                    "hvac_power_levels",
                    "hvac_power_min",
                    "hvac_power_max",
                    "hvac_power_tolerance",
                ],
                "configured": [],
            },
        }

        # Find configured parameters for each feature
        for feature_name, feature_info in features.items():
            for param in feature_info["parameters"]:
                if param in config and config[param] is not None:
                    feature_info["configured"].append(param)

        return features


def validate_yaml_config(yaml_content: str) -> None:
    """Validate a YAML configuration string."""
    try:
        config = yaml.safe_load(yaml_content)

        # Extract climate configuration if it's a full HA config
        if "climate" in config:
            if isinstance(config["climate"], list):
                config = config["climate"][0]  # Take first climate config
            else:
                config = config["climate"]

        validator = ConfigValidator()
        is_valid, errors, warnings = validator.validate_config(config)

        print("🔍 Configuration Validation Results")
        print("=" * 40)
        print(f"Configuration: {'✅ Valid' if is_valid else '❌ Invalid'}")
        print()

        if errors:
            print("❌ Errors:")
            for error in errors:
                print(f"  • {error}")
            print()

        if warnings:
            print("⚠️  Warnings:")
            for warning in warnings:
                print(f"  • {warning}")
            print()

        # Feature analysis
        features = validator.get_feature_groups(config)
        print("📊 Feature Analysis:")
        for feature_name, feature_info in features.items():
            status = "✅ Enabled" if feature_info["enabled"] else "⭕ Disabled"
            configured_count = len(feature_info["configured"])
            total_count = len(feature_info["parameters"])

            print(
                f"  {feature_name}: {status} ({configured_count}/{total_count} parameters)"
            )
            if feature_info["configured"]:
                print(f"    Configured: {', '.join(feature_info['configured'])}")
        print()

        # Suggestions
        if not is_valid:
            suggestions = validator.suggest_fixes(config)
            if suggestions:
                print("💡 Suggestions:")
                for suggestion in suggestions:
                    print(f"  • {suggestion}")

    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
    except Exception as e:
        print(f"❌ Validation error: {e}")


def main():
    """Main function with example configurations."""
    print("🎯 Dual Smart Thermostat Configuration Dependency Validator")
    print()

    # Test configurations
    test_configs = {
        "❌ Invalid - Missing Dependencies": """
name: "Test Thermostat"
heater: switch.heater
target_sensor: sensor.temperature
max_floor_temp: 28  # Missing floor_sensor
fan_mode: true      # Missing fan
        """,
        "❌ Invalid - Entity Conflicts": """
name: "Test Thermostat"
heater: switch.main_device
target_sensor: switch.main_device  # Same as heater!
cooler: switch.main_device          # Same as heater!
        """,
        "✅ Valid - Basic Configuration": """
name: "Basic Thermostat"
heater: switch.heater
target_sensor: sensor.temperature
        """,
        "✅ Valid - Full Featured": """
name: "Advanced Thermostat"
heater: switch.heater
cooler: switch.ac_unit
target_sensor: sensor.temperature
secondary_heater: switch.aux_heater
secondary_heater_timeout: "00:05:00"
floor_sensor: sensor.floor_temp
max_floor_temp: 28
heat_cool_mode: true
target_temp_low: 18
target_temp_high: 24
fan: switch.ceiling_fan
fan_mode: true
humidity_sensor: sensor.humidity
target_humidity: 50
        """,
        "✅ Valid - Template-Based Presets": """
name: "Template Thermostat"
heater: switch.heater
cooler: switch.ac_unit
target_sensor: sensor.temperature
heat_cool_mode: true
# Preset temperatures can use static values or templates
away_temp: "{{ states('input_number.away_heat') | float }}"
away_temp_high: "{{ states('input_number.away_cool') | float }}"
eco_temp: "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"
eco_temp_high: 28
home_temp: "{{ states('sensor.outdoor_temp') | float + 5 }}"
home_temp_high: "{{ states('sensor.outdoor_temp') | float + 10 }}"
comfort_temp: 21
comfort_temp_high: 24
        """,
    }

    for config_name, config_yaml in test_configs.items():
        print(f"Testing: {config_name}")
        print("-" * 50)
        validate_yaml_config(config_yaml)
        print()


if __name__ == "__main__":
    main()
