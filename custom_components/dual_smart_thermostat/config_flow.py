"""Config flow for Dual Smart Thermostat integration."""

from __future__ import annotations

import logging
from typing import Any, Mapping, cast

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_PRESETS,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_DUAL_STAGE,
    SYSTEM_TYPE_FLOOR_HEATING,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from .feature_steps import (
    FanSteps,
    FloorSteps,
    HumiditySteps,
    OpeningsSteps,
    PresetsSteps,
)
from .flow_utils import EntityValidator
from .schemas import (
    get_ac_only_features_schema,
    get_additional_sensors_schema,
    get_advanced_settings_schema,
    get_base_schema,
    get_dual_stage_schema,
    get_fan_schema,
    get_grouped_schema,
    get_heat_cool_mode_schema,
    get_humidity_schema,
    get_preset_selection_schema,
    get_simple_heater_features_schema,
    get_system_features_schema,
    get_system_type_schema,
)

_LOGGER = logging.getLogger(__name__)


# Schema functions have been moved to schemas.py for better organization
# They are imported above and used by the ConfigFlowHandler and OptionsFlowHandler classes


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config or options flow for Dual Smart Thermostat."""

    VERSION = 1
    CONNECTION_CLASS = "local_polling"

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self.collected_config = {}

        # Initialize feature step handlers
        self.openings_steps = OpeningsSteps()
        self.fan_steps = FanSteps()
        self.humidity_steps = HumiditySteps()
        self.presets_steps = PresetsSteps()
        self.floor_steps = FloorSteps()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - system type selection."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._async_step_system_config()

        return self.async_show_form(
            step_id="user",
            data_schema=get_system_type_schema(),
            description_placeholders={
                "simple_heater": "Basic heating only with one heater switch",
                "ac_only": "Air conditioning or cooling only",
                "heater_cooler": "Separate heater and cooler switches",
                "heat_pump": "Heat pump system with heating and cooling",
                "dual_stage": "Two-stage heating with auxiliary heater",
                "floor_heating": "Floor heating with temperature protection",
                "advanced": "Configure all options manually",
            },
        )

    async def _async_step_system_config(self) -> FlowResult:
        """Handle system-specific configuration."""
        # Determine selected system type from collected config
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        if system_type == SYSTEM_TYPE_SIMPLE_HEATER:
            return await self.async_step_basic()
        elif system_type == SYSTEM_TYPE_AC_ONLY:
            return await self.async_step_cooling_only()
        elif system_type == SYSTEM_TYPE_HEATER_COOLER:
            return await self.async_step_heater_cooler()
        elif system_type == SYSTEM_TYPE_HEAT_PUMP:
            return await self.async_step_heat_pump()
        elif system_type == SYSTEM_TYPE_DUAL_STAGE:
            return await self.async_step_dual_stage()
        elif system_type == SYSTEM_TYPE_FLOOR_HEATING:
            return await self.async_step_floor_heating()
        else:  # advanced
            return await self.async_step_basic()

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle basic configuration."""
        errors = {}

        if user_input is not None:
            if not await self._validate_basic_config(user_input):
                errors = EntityValidator.get_validation_errors(user_input)
            else:
                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use a shared core schema so config and options flows render the
        # same fields (options flow omits the name). Pass include_name=True
        # so the config flow shows the Name field.
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)
        schema = __import__(
            "custom_components.dual_smart_thermostat.schemas",
            fromlist=["get_core_schema"],
        ).get_core_schema(system_type, defaults=None, include_name=True)

        return self.async_show_form(step_id="basic", data_schema=schema, errors=errors)

    async def async_step_simple_heater_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Simple Heater system features configuration.

        Present a single combined step where the user picks which feature
        areas to configure (openings, presets, advanced). Subsequent steps
        will be shown conditionally based on these selections.
        """
        if user_input is not None:
            # If user selects advanced, show the advanced form next
            show_advanced = user_input.get("configure_advanced", False)

            if show_advanced and "advanced_shown" not in self.collected_config:
                self.collected_config.update(user_input)
                self.collected_config["advanced_shown"] = True
                return self.async_show_form(
                    step_id="simple_heater_features",
                    data_schema=get_advanced_settings_schema(),
                    description_placeholders={
                        "subtitle": "Configure advanced settings for your simple heater"
                    },
                )

            # Otherwise, store selections and proceed
            self.collected_config.update(user_input)
            # Clear toggles so they don't persist unexpectedly
            self.collected_config.pop("configure_advanced", None)
            self.collected_config.pop("advanced_shown", None)
            return await self._determine_next_step()

        # For initial display, ensure any previous simple-heater feature flags are cleared
        self.collected_config.pop("configure_advanced", None)
        self.collected_config.pop("advanced_shown", None)

        return self.async_show_form(
            step_id="simple_heater_features",
            data_schema=get_simple_heater_features_schema(),
            description_placeholders={
                "subtitle": "Choose which features to configure for your heater"
            },
        )

    async def async_step_system_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Generic features-selection step for non-AC systems.

        This step is shown after core settings and allows users to choose which
        additional features they want to configure. The available options are
        tailored by `get_system_features_schema(system_type)` in `schemas.py`.
        """
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        if user_input is not None:
            # If user asked for advanced, show advanced form first
            show_advanced = user_input.get("configure_advanced", False)

            if show_advanced and "advanced_shown" not in self.collected_config:
                self.collected_config.update(user_input)
                self.collected_config["advanced_shown"] = True
                return self.async_show_form(
                    step_id="system_features",
                    data_schema=get_advanced_settings_schema(),
                    description_placeholders={
                        "subtitle": "Configure advanced settings for your system"
                    },
                )

            # Otherwise store selections and continue
            self.collected_config.update(user_input)
            # Clear transient flags
            self.collected_config.pop("configure_advanced", None)
            self.collected_config.pop("advanced_shown", None)
            return await self._determine_next_step()

        # Initial display: clear any previous transient advanced flags
        self.collected_config.pop("configure_advanced", None)
        self.collected_config.pop("advanced_shown", None)

        return self.async_show_form(
            step_id="system_features",
            data_schema=get_system_features_schema(system_type),
            description_placeholders={
                "subtitle": "Choose which features to configure for your system"
            },
        )

    async def async_step_cooling_only(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle AC-only configuration using heater field with AC-friendly labeling.

        Uses heater field for backward compatibility but shows "Air conditioning switch" label in UI.
        """
        errors = {}

        if user_input is not None:
            if not await self._validate_basic_config(user_input):
                errors = EntityValidator.get_validation_errors(user_input)
            else:
                # Force AC mode to true for AC-only systems
                user_input[CONF_AC_MODE] = True
                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use heater field for backward compatibility but label it as "Air conditioning switch"
        grouped = get_grouped_schema(
            SYSTEM_TYPE_AC_ONLY, show_heater=True, show_cooler=False
        )
        base = get_base_schema()
        schema = vol.Schema({**base.schema, **grouped.schema})
        return self.async_show_form(
            step_id="cooling_only",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_heater_cooler(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle heater with cooler configuration."""
        errors = {}

        if user_input is not None:
            if not await self._validate_basic_config(user_input):
                heater = user_input.get(CONF_HEATER)
                sensor = user_input.get(CONF_SENSOR)
                cooler = user_input.get(CONF_COOLER)

                if heater and sensor and heater == sensor:
                    errors["base"] = "same_heater_sensor"
                elif heater and cooler and heater == cooler:
                    errors["base"] = "same_heater_cooler"
            else:
                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use grouped schema merged with base schema for better UI organization
        grouped = get_grouped_schema(
            system_type="heater_cooler",
            show_heater=True,
            show_cooler=True,
        )
        base = get_base_schema()
        schema = vol.Schema({**base.schema, **grouped.schema})

        return self.async_show_form(
            step_id="heater_cooler",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_heat_pump(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle heat pump configuration."""
        errors = {}

        if user_input is not None:
            if not await self._validate_basic_config(user_input):
                heater = user_input.get(CONF_HEATER)
                sensor = user_input.get(CONF_SENSOR)

                if heater and sensor and heater == sensor:
                    errors["base"] = "same_heater_sensor"
            else:
                # Enable heat pump cooling mode
                user_input[CONF_HEAT_PUMP_COOLING] = True
                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use grouped schema merged with base schema for better UI organization
        # For heat pump, expose the heat pump cooling toggle only for this
        # system type.
        grouped = get_grouped_schema(
            SYSTEM_TYPE_HEAT_PUMP,
            show_heater=True,
            show_heat_pump_cooling=True,
        )
        base = get_base_schema()
        schema = vol.Schema({**base.schema, **grouped.schema})

        return self.async_show_form(
            step_id="heat_pump",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_dual_stage(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle dual stage heating configuration."""
        errors = {}

        if user_input is not None:
            if not await self._validate_basic_config(user_input):
                heater = user_input.get(CONF_HEATER)
                sensor = user_input.get(CONF_SENSOR)

                if heater and sensor and heater == sensor:
                    errors["base"] = "same_heater_sensor"
            else:
                self.collected_config.update(user_input)
                return await self.async_step_dual_stage_config()

        # Use grouped schema merged with base schema for better UI organization
        grouped = get_grouped_schema(SYSTEM_TYPE_SIMPLE_HEATER, show_heater=True)
        base = get_base_schema()
        schema = vol.Schema({**base.schema, **grouped.schema})

        return self.async_show_form(
            step_id="dual_stage",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_dual_stage_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle dual stage specific configuration."""
        errors = {}

        if user_input is not None:
            # Validate that aux heater and timeout are provided for dual stage
            aux_heater = user_input.get(CONF_AUX_HEATER)
            aux_timeout = user_input.get(CONF_AUX_HEATING_TIMEOUT)

            if aux_heater and not aux_timeout:
                errors[CONF_AUX_HEATING_TIMEOUT] = "aux_heater_timeout_required"
            elif aux_timeout and not aux_heater:
                errors[CONF_AUX_HEATER] = "aux_heater_entity_required"
            else:
                self.collected_config.update(user_input)
                return await self._determine_next_step()

        return self.async_show_form(
            step_id="dual_stage_config",
            data_schema=get_dual_stage_schema(),
            errors=errors,
        )

    async def async_step_floor_heating(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle floor heating configuration."""
        # Fully delegate to the FloorSteps handler which now performs the
        # basic validation and displays the grouped form.
        return await self.floor_steps.async_step_heating(
            self, user_input, self.collected_config, self._determine_next_step
        )

    # Legacy floor_heating_toggle step removed. Floor heating is configured
    # directly via the combined features step (or system features) and then
    # `async_step_floor_config` is used for detailed floor settings.

    async def async_step_openings_toggle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle openings toggle configuration."""
        return await self.openings_steps.async_step_toggle(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_fan_toggle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle fan toggle configuration."""
        return await self.fan_steps.async_step_toggle(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_humidity_toggle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity toggle configuration."""
        return await self.humidity_steps.async_step_toggle(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_ac_only_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle AC-only system features configuration."""
        if user_input is not None:
            # Check if user wants to show advanced options
            show_advanced = user_input.get("configure_advanced", False)

            # If this is the first submission and advanced is enabled, show advanced form
            if show_advanced and "advanced_shown" not in self.collected_config:
                self.collected_config.update(user_input)
                self.collected_config["advanced_shown"] = True
                return self.async_show_form(
                    step_id="ac_only_features",
                    data_schema=get_ac_only_features_schema(),
                    description_placeholders={
                        "subtitle": "Configure AC system features and advanced settings"
                    },
                )

            # Otherwise, process the final submission and continue
            self.collected_config.update(user_input)
            # Clear the advanced toggle flags to prevent re-showing
            self.collected_config.pop("configure_advanced", None)
            self.collected_config.pop("advanced_shown", None)
            return await self._determine_next_step()

        # For initial display, always start with basic form
        # Reset any advanced state to ensure clean start
        self.collected_config.pop("configure_advanced", None)
        self.collected_config.pop("advanced_shown", None)

        return self.async_show_form(
            step_id="ac_only_features",
            data_schema=get_ac_only_features_schema(),
            description_placeholders={
                "subtitle": "Choose which features to configure for your AC system"
            },
        )

    async def async_step_floor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle floor heating specific configuration."""
        return await self.floor_steps.async_step_config(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_openings_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle openings selection configuration."""
        return await self.openings_steps.async_step_selection(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_openings_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle openings timeout configuration."""
        return await self.openings_steps.async_step_config(
            self, user_input, self.collected_config, self._determine_next_step
        )

    async def async_step_heat_cool_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle heat/cool mode configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_next_step()

        return self.async_show_form(
            step_id="heat_cool_mode",
            data_schema=get_heat_cool_mode_schema(),
        )

    async def async_step_fan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle fan configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_next_step()

        return self.async_show_form(
            step_id="fan",
            data_schema=get_fan_schema(),
        )

    async def async_step_humidity(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity control configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_next_step()

        return self.async_show_form(
            step_id="humidity",
            data_schema=get_humidity_schema(),
        )

    async def async_step_additional_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle additional sensors configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_next_step()

        return self.async_show_form(
            step_id="additional_sensors",
            data_schema=get_additional_sensors_schema(),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced settings."""
        if user_input is not None:
            self.collected_config.update(user_input)

            # Handle advanced system type selection
            advanced_system_type = user_input.get("advanced_system_type")
            if advanced_system_type == SYSTEM_TYPE_DUAL_STAGE:
                # Set system type and proceed to dual stage configuration
                self.collected_config[CONF_SYSTEM_TYPE] = SYSTEM_TYPE_DUAL_STAGE
                # Ensure dual stage configuration is shown
                return await self.async_step_dual_stage()
            elif advanced_system_type == SYSTEM_TYPE_FLOOR_HEATING:
                # Set system type and proceed to floor heating configuration
                self.collected_config[CONF_SYSTEM_TYPE] = SYSTEM_TYPE_FLOOR_HEATING
                # Ensure floor heating configuration is shown
                return await self.async_step_floor_heating()

            return await self._determine_next_step()

        return self.async_show_form(
            step_id="advanced",
            data_schema=get_advanced_settings_schema(),
        )

    async def async_step_preset_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle preset selection step."""
        if user_input is not None:
            self.collected_config.update(user_input)
            # Detect enabled presets. Support both multi-select ('presets': [...])
            # and legacy boolean per-preset keys.
            if "presets" in user_input:
                raw = user_input.get("presets") or []
                selected_presets = [
                    (
                        item["value"]
                        if isinstance(item, dict) and "value" in item
                        else item
                    )
                    for item in raw
                ]
                any_preset_enabled = bool(selected_presets)
            else:
                any_preset_enabled = any(
                    user_input.get(preset_key, False)
                    for preset_key in CONF_PRESETS.values()
                )

            if any_preset_enabled:
                # At least one preset is enabled, proceed to configuration
                return await self.async_step_presets()
            # No presets enabled, skip configuration and finish
            return self.async_create_entry(
                title=self.collected_config[CONF_NAME],
                data=self.collected_config,
            )

        return self.async_show_form(
            step_id="preset_selection",
            data_schema=get_preset_selection_schema(),
        )

    async def async_step_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle presets configuration."""
        return await self.presets_steps.async_step_config(
            self, user_input, self.collected_config
        )

    async def _validate_basic_config(self, user_input: dict[str, Any]) -> bool:
        """Validate basic configuration."""
        return EntityValidator.validate_basic_config(user_input)

    async def _determine_next_step(self) -> FlowResult:
        """Determine the next step based on configuration dependencies."""
        system_type = self.collected_config.get("system_type")
        # For non-AC systems, show a combined features-selection step first
        # (heater_cooler, heat_pump, dual_stage). This lets users pick which
        # additional features they want to configure before showing per-feature
        # toggles like floor heating.
        if (
            system_type in ["heater_cooler", "heat_pump", "dual_stage"]
            and "system_features_shown" not in self.collected_config
        ):
            self.collected_config["system_features_shown"] = True
            return await self.async_step_system_features()

        # Show floor heating toggle for systems that support floor heating
        # (all systems except ac_only and when not already configured)
        if (
            system_type not in ["ac_only"]
            and system_type
            != "floor_heating"  # floor_heating type already has floor config
        ):
            # For simple_heater, only configure floor heating if the user
            # opted into it in the earlier features-selection step. For other
            # systems that support floor heating, go straight to floor config
            # when needed.
            if system_type == "simple_heater":
                # Only go to floor config if the user opted in and floor
                # settings haven't already been provided to avoid looping
                if (
                    self.collected_config.get("configure_floor_heating")
                    and CONF_FLOOR_SENSOR not in self.collected_config
                ):
                    return await self.async_step_floor_config()
            else:
                # For other systems that support floor heating, only go to
                # floor config if the floor sensor has not already been set.
                if CONF_FLOOR_SENSOR not in self.collected_config:
                    return await self.async_step_floor_config()

        # Floor heating configuration is handled earlier where required.

        # Show openings toggle for systems that will configure openings separately.
        # AC-only and simple_heater systems use a combined 'features' step instead.
        system_type = self.collected_config.get("system_type")
        if (
            "openings_toggle_shown" not in self.collected_config
            and system_type not in ["ac_only", "simple_heater"]
        ):
            self.collected_config["openings_toggle_shown"] = True
            return await self.async_step_openings_toggle()

        # Show openings selection and config if either the legacy toggle
        # was enabled (enable_openings) or the combined features-selection
        # step requested openings configuration (configure_openings).
        if (
            self.collected_config.get("enable_openings")
            or self.collected_config.get("configure_openings")
        ) and "selected_openings" not in self.collected_config:
            return await self.async_step_openings_selection()

        # For AC-only systems, show combined features configuration
        if (
            system_type == "ac_only"
            and "ac_only_features_shown" not in self.collected_config
        ):
            self.collected_config["ac_only_features_shown"] = True
            return await self.async_step_ac_only_features()

        # For simple heater systems, show combined features configuration
        if (
            system_type == "simple_heater"
            and "simple_heater_features_shown" not in self.collected_config
        ):
            self.collected_config["simple_heater_features_shown"] = True
            return await self.async_step_simple_heater_features()

        # Show fan toggle for other systems with cooling capability (when not already configured)
        if (
            system_type in ["advanced", "heater_cooler", "heat_pump"]
            and "fan_toggle_shown" not in self.collected_config
        ):
            self.collected_config["fan_toggle_shown"] = True
            return await self.async_step_fan_toggle()

        # Show humidity toggle for other systems with cooling capability (when not already configured)
        if (
            system_type in ["advanced", "heater_cooler", "heat_pump"]
            and "humidity_toggle_shown" not in self.collected_config
        ):
            self.collected_config["humidity_toggle_shown"] = True
            return await self.async_step_humidity_toggle()

        # For AC-only systems, show fan configuration if enabled
        if (
            system_type == "ac_only"
            and self.collected_config.get("configure_fan")
            and CONF_FAN not in self.collected_config
        ):
            return await self.async_step_fan()

        # For AC-only systems, show humidity configuration if enabled
        if (
            system_type == "ac_only"
            and self.collected_config.get("configure_humidity")
            and CONF_HUMIDITY_SENSOR not in self.collected_config
        ):
            return await self.async_step_humidity()

        # For AC-only systems, show openings selection if enabled
        if (
            system_type == "ac_only"
            and self.collected_config.get("configure_openings")
            and "selected_openings" not in self.collected_config
        ):
            return await self.async_step_openings_selection()

        # Show heat/cool mode if not configured and system supports it
        # This applies to advanced, heater_cooler, and heat_pump system types
        if (
            CONF_HEAT_COOL_MODE not in self.collected_config
            and self._has_both_heating_and_cooling()
            and system_type in ["advanced", "heater_cooler", "heat_pump"]
        ):
            return await self.async_step_heat_cool_mode()

        # For advanced setup, show all options based on dependencies
        if system_type == "advanced":
            # Show fan config if not shown yet
            if self._should_show_fan_config():
                self.collected_config["fan_config_shown"] = True
                return await self.async_step_fan()

            # Show humidity config if not shown yet
            if self._should_show_humidity_config():
                self.collected_config["humidity_config_shown"] = True
                return await self.async_step_humidity()

            # Show additional sensors if not shown yet
            if self._should_show_additional_sensors():
                self.collected_config["additional_sensors_shown"] = True
                return await self.async_step_additional_sensors()

            # Show advanced config if not shown yet
            if self._should_show_advanced_config():
                self.collected_config["advanced_config_shown"] = True
                return await self.async_step_advanced()

        # For specific system types, show relevant additional configs
        if system_type == "dual_stage" and CONF_AUX_HEATER not in self.collected_config:
            return await self.async_step_dual_stage_config()

        if (
            system_type == "floor_heating"
            and CONF_FLOOR_SENSOR not in self.collected_config
        ):
            return await self.async_step_floor_config()

        # Show preset selection before presets configuration (if enabled for AC-only systems)
        system_type = self.collected_config.get("system_type")
        if system_type == "ac_only":
            # For AC-only systems, only show presets if enabled
            if self.collected_config.get("configure_presets", True):
                return await self.async_step_preset_selection()
            else:
                # Skip presets and finish configuration
                return self.async_create_entry(
                    title=self.async_config_entry_title(self.collected_config),
                    data=self.collected_config,
                )
        else:
            # For other systems, always show preset selection
            return await self.async_step_preset_selection()

    def _has_both_heating_and_cooling(self) -> bool:
        """Check if system has both heating and cooling capability."""
        has_heater = bool(self.collected_config.get(CONF_HEATER))
        has_cooler = bool(self.collected_config.get(CONF_COOLER))
        has_heat_pump = bool(self.collected_config.get(CONF_HEAT_PUMP_COOLING))
        has_ac_mode = bool(self.collected_config.get(CONF_AC_MODE))

        return has_heater and (has_cooler or has_heat_pump or has_ac_mode)

    def _should_show_fan_config(self) -> bool:
        """Check if fan configuration should be shown."""
        return (
            "fan_config_shown" not in self.collected_config
            and self.collected_config.get("system_type") == "advanced"
        )

    def _should_show_humidity_config(self) -> bool:
        """Check if humidity configuration should be shown."""
        return (
            "humidity_config_shown" not in self.collected_config
            and self.collected_config.get("system_type") == "advanced"
        )

    def _should_show_additional_sensors(self) -> bool:
        """Check if additional sensors configuration should be shown."""
        return (
            "additional_sensors_shown" not in self.collected_config
            and self.collected_config.get(CONF_SYSTEM_TYPE) == "advanced"
        )

    def _should_show_advanced_config(self) -> bool:
        """Check if advanced configuration should be shown."""
        return (
            "advanced_config_shown" not in self.collected_config
            and self.collected_config.get(CONF_SYSTEM_TYPE) == "advanced"
        )

    @callback
    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options.get(CONF_NAME, "Dual Smart Thermostat"))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        from .options_flow import OptionsFlowHandler

        return OptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        return self.async_create_entry(
            title=import_config.get(CONF_NAME, "Dual Smart Thermostat"),
            data=import_config,
        )


DualSmartThermostatConfigFlow = ConfigFlowHandler
