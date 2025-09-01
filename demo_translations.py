#!/usr/bin/env python3
"""Demo script to verify translation functionality for openings scope options."""

import json
import os


def load_translations(lang="en"):
    """Load translations for a specific language."""
    translations_dir = "custom_components/dual_smart_thermostat/translations"
    translation_file = os.path.join(translations_dir, f"{lang}.json")

    if os.path.exists(translation_file):
        with open(translation_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def demo_scope_translations():
    """Demonstrate the translated scope options."""
    print("=== Openings Scope Options Translation Demo ===\n")

    # Load English translations
    en_translations = load_translations("en")
    sk_translations = load_translations("sk")

    # Extract scope options
    en_scope_options = (
        en_translations.get("selector", {}).get("openings_scope", {}).get("options", {})
    )
    sk_scope_options = (
        sk_translations.get("selector", {}).get("openings_scope", {}).get("options", {})
    )

    print("English translations:")
    for key, value in en_scope_options.items():
        print(f"  {key}: {value}")

    print("\nSlovak translations:")
    for key, value in sk_scope_options.items():
        print(f"  {key}: {value}")

    # Simulate scope generation for different system types
    print("\n=== System Type Examples ===\n")

    system_scenarios = [
        ("AC-only system", ["all", "cool", "fan_only", "dry"]),
        ("Simple heater", ["all", "heat"]),
        ("Heat pump with heat/cool mode", ["all", "heat", "cool", "heat_cool"]),
        (
            "Dual system with all features",
            ["all", "heat", "cool", "heat_cool", "fan_only", "dry"],
        ),
    ]

    for system_name, available_scopes in system_scenarios:
        print(f"{system_name}:")
        print("  English options:")
        for scope in available_scopes:
            translation = en_scope_options.get(scope, scope)
            print(f"    - {scope}: {translation}")

        print("  Slovak options:")
        for scope in available_scopes:
            translation = sk_scope_options.get(scope, scope)
            print(f"    - {scope}: {translation}")
        print()


if __name__ == "__main__":
    demo_scope_translations()
