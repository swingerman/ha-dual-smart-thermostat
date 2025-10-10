"""Shared utilities for config and options flows."""

from __future__ import annotations

from typing import Any

from .const import (
    ATTR_CLOSING_TIMEOUT,
    ATTR_OPENING_TIMEOUT,
    CONF_COOLER,
    CONF_HEATER,
    CONF_OPENINGS_SCOPE,
    CONF_SENSOR,
)


class EntityValidator:
    """Validator for entity configurations."""

    @staticmethod
    def validate_basic_config(user_input: dict[str, Any]) -> bool:
        """Validate basic configuration.

        Args:
            user_input: User input data

        Returns:
            True if validation passes, False otherwise
        """
        # Validate that heater and sensor are different entities
        heater = user_input.get(CONF_HEATER)
        sensor = user_input.get(CONF_SENSOR)
        if heater and sensor and heater == sensor:
            return False

        # Validate that heater and cooler are different if both specified
        cooler = user_input.get(CONF_COOLER)
        if heater and cooler and heater == cooler:
            return False

        return True

    @staticmethod
    def get_validation_errors(user_input: dict[str, Any]) -> dict[str, str]:
        """Get specific validation errors for user input.

        Args:
            user_input: User input data

        Returns:
            Dictionary of field errors
        """
        errors = {}
        heater = user_input.get(CONF_HEATER)
        sensor = user_input.get(CONF_SENSOR)
        cooler = user_input.get(CONF_COOLER)

        if heater and sensor and heater == sensor:
            errors["base"] = "same_heater_sensor"
        elif heater and cooler and heater == cooler:
            errors["base"] = "same_heater_cooler"

        return errors


class OpeningsProcessor:
    """Processor for openings configuration."""

    @staticmethod
    def process_openings_config(
        user_input: dict[str, Any], selected_entities: list[str] | None = None
    ) -> list[str | dict[str, Any]]:
        """Process openings configuration and convert to expected format.

        Args:
            user_input: User input containing timeout configurations (may be flat or section-based)
            selected_entities: List of selected opening entities

        Returns:
            List of openings in the correct format (entity_id strings or dicts with timeouts)
        """
        if selected_entities is None:
            selected_entities = user_input.get("selected_openings", [])

        openings_list = []

        for i, entity_id in enumerate(selected_entities):
            # Check for indexed field structure (opening_1_timeout_open, opening_1_timeout_close, etc.)
            opening_key = f"opening_{i + 1}_timeout_open"
            closing_key = f"opening_{i + 1}_timeout_close"

            if opening_key in user_input or closing_key in user_input:
                opening_timeout = user_input.get(opening_key, 0)
                closing_timeout = user_input.get(closing_key, 0)

                # Always create object format for consistency
                opening_obj = {"entity_id": entity_id}
                if opening_timeout:
                    opening_obj[ATTR_OPENING_TIMEOUT] = opening_timeout
                if closing_timeout:
                    opening_obj[ATTR_CLOSING_TIMEOUT] = closing_timeout
                openings_list.append(opening_obj)
                continue

            # Check for section-based structure (entity_id -> {timeout_open, timeout_close})
            if entity_id in user_input and isinstance(user_input[entity_id], dict):
                section_data = user_input[entity_id]
                opening_timeout = section_data.get("timeout_open", 0)
                closing_timeout = section_data.get("timeout_close", 0)

                # Always create object format for consistency
                opening_obj = {"entity_id": entity_id}
                if opening_timeout:
                    opening_obj[ATTR_OPENING_TIMEOUT] = opening_timeout
                if closing_timeout:
                    opening_obj[ATTR_CLOSING_TIMEOUT] = closing_timeout
                openings_list.append(opening_obj)
            else:
                # Fallback to old flat structure for backward compatibility
                opening_timeout_key = f"{entity_id}_opening_timeout"
                closing_timeout_key = f"{entity_id}_closing_timeout"
                # Also check new naming convention
                alt_opening_key = f"{entity_id}_timeout_open"
                alt_closing_key = f"{entity_id}_timeout_close"

                # Check if we have timeout settings for this entity
                has_opening_timeout = (
                    opening_timeout_key in user_input
                    and user_input[opening_timeout_key]
                ) or (alt_opening_key in user_input and user_input[alt_opening_key])
                has_closing_timeout = (
                    closing_timeout_key in user_input
                    and user_input[closing_timeout_key]
                ) or (alt_closing_key in user_input and user_input[alt_closing_key])

                # Always create object format for consistency
                opening_obj = {"entity_id": entity_id}
                if has_opening_timeout:
                    timeout_val = user_input.get(opening_timeout_key) or user_input.get(
                        alt_opening_key
                    )
                    opening_obj[ATTR_OPENING_TIMEOUT] = timeout_val
                if has_closing_timeout:
                    timeout_val = user_input.get(closing_timeout_key) or user_input.get(
                        alt_closing_key
                    )
                    opening_obj[ATTR_CLOSING_TIMEOUT] = timeout_val
                openings_list.append(opening_obj)

        return openings_list

    @staticmethod
    def extract_selected_entities_from_config(openings_config: list) -> list[str]:
        """Extract entity IDs from openings configuration.

        Args:
            openings_config: Current openings configuration

        Returns:
            List of entity IDs
        """
        selected_entities = []
        if openings_config:
            for opening in openings_config:
                if isinstance(opening, dict):
                    selected_entities.append(opening["entity_id"])
                else:
                    selected_entities.append(opening)
        return selected_entities

    @staticmethod
    def clean_openings_scope(collected_config: dict[str, Any]) -> None:
        """Clean openings scope configuration.

        Remove openings_scope if it's "all" or not set (default behavior).
        Also handles the singular "opening_scope" form field name.

        Args:
            collected_config: Configuration dictionary to modify
        """
        # Check both the constant name and the form field name
        openings_scope = collected_config.get(
            CONF_OPENINGS_SCOPE
        ) or collected_config.get("opening_scope")

        if openings_scope and openings_scope != "all" and "all" not in openings_scope:
            # Keep the scope setting only if it's not "all"
            pass
        else:
            # Remove openings_scope if it's "all" or not set (default behavior)
            # Remove both possible key names
            collected_config.pop(CONF_OPENINGS_SCOPE, None)
            collected_config.pop("opening_scope", None)


class FlowStepTracker:
    """Utility for tracking flow steps to prevent loops."""

    def __init__(self, collected_config: dict[str, Any]):
        """Initialize step tracker.

        Args:
            collected_config: Configuration dictionary to track steps in
        """
        self.collected_config = collected_config

    def is_step_shown(self, step_name: str) -> bool:
        """Check if a step has been shown.

        Args:
            step_name: Name of the step to check

        Returns:
            True if step has been shown
        """
        return f"{step_name}_shown" in self.collected_config

    def mark_step_shown(self, step_name: str) -> None:
        """Mark a step as shown.

        Args:
            step_name: Name of the step to mark as shown
        """
        self.collected_config[f"{step_name}_shown"] = True

    def should_show_step(self, step_name: str) -> bool:
        """Check if a step should be shown (not already shown).

        Args:
            step_name: Name of the step to check

        Returns:
            True if step should be shown
        """
        return not self.is_step_shown(step_name)


class LegacyCompatibility:
    """Utilities for handling legacy field compatibility."""

    @staticmethod
    def convert_legacy_cooler_to_heater(user_input: dict[str, Any]) -> None:
        """Convert legacy cooler field to heater for AC-only systems.

        Args:
            user_input: User input dictionary to modify
        """
        if CONF_COOLER in user_input and CONF_HEATER not in user_input:
            user_input[CONF_HEATER] = user_input[CONF_COOLER]


class FormHelper:
    """Helper utilities for form handling."""

    @staticmethod
    def create_step_result(
        step_id: str,
        schema,
        errors: dict[str, str] | None = None,
        description_placeholders: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a standardized form result.

        Args:
            step_id: ID of the step
            schema: Form schema
            errors: Validation errors
            description_placeholders: Placeholders for descriptions

        Returns:
            Form result dictionary
        """
        result = {
            "type": "form",
            "step_id": step_id,
            "data_schema": schema,
        }

        if errors:
            result["errors"] = errors

        if description_placeholders:
            result["description_placeholders"] = description_placeholders

        return result
