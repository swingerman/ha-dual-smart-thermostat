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
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_PRESETS,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_DUAL_STAGE,
    SYSTEM_TYPE_FLOOR_HEATING,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_SIMPLE_HEATER,
    SystemType,
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
    get_additional_sensors_schema,
    get_base_schema,
    get_basic_ac_schema,
    get_dual_stage_schema,
    get_fan_schema,
    get_features_schema,
    get_grouped_schema,
    get_heat_cool_mode_schema,
    get_heater_cooler_schema,
    get_humidity_schema,
    get_preset_selection_schema,
    get_simple_heater_schema,
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
            },
        )

    async def _async_step_system_config(self) -> FlowResult:
        """Handle system-specific configuration."""
        # Determine selected system type from collected config
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        if system_type == SystemType.SIMPLE_HEATER:
            return await self.async_step_basic()
        elif system_type == SystemType.AC_ONLY:
            return await self.async_step_basic_ac_only()
        elif system_type == SystemType.HEATER_COOLER:
            return await self.async_step_heater_cooler()
        elif system_type == SystemType.HEAT_PUMP:
            return await self.async_step_heat_pump()
        elif system_type == SystemType.DUAL_STAGE:
            return await self.async_step_dual_stage()
        elif system_type == SystemType.FLOOR_HEATING:
            return await self.async_step_floor_heating()
        else:  # advanced
            return await self.async_step_basic()

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle basic configuration."""
        errors = {}
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        if user_input is not None:
            # Extract advanced settings from section and flatten to top level
            if "advanced_settings" in user_input:
                advanced_settings = user_input.pop("advanced_settings")
                if advanced_settings:
                    user_input.update(advanced_settings)

            if not await self._validate_basic_config(user_input):
                errors = EntityValidator.get_validation_errors(user_input)
            else:
                # For AC-only systems, force AC mode to true
                if system_type == SystemType.AC_ONLY:
                    user_input[CONF_AC_MODE] = True

                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use a shared core schema so config and options flows render the
        # same fields (options flow omits the name). Pass include_name=True
        # so the config flow shows the Name field.

        # Use system-specific schemas with advanced settings
        if system_type == SystemType.SIMPLE_HEATER:
            schema = get_simple_heater_schema(defaults=None, include_name=True)
        else:
            schema = __import__(
                "custom_components.dual_smart_thermostat.schemas",
                fromlist=["get_core_schema"],
            ).get_core_schema(system_type, defaults=None, include_name=True)

        return self.async_show_form(step_id="basic", data_schema=schema, errors=errors)

    async def async_step_basic_ac_only(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle basic AC-only configuration with dedicated translations."""
        errors = {}

        if user_input is not None:
            # Extract advanced settings from section and flatten to top level
            if "advanced_settings" in user_input:
                advanced_settings = user_input.pop("advanced_settings")
                if advanced_settings:
                    user_input.update(advanced_settings)

            if not await self._validate_basic_config(user_input):
                errors = EntityValidator.get_validation_errors(user_input)
            else:
                user_input[CONF_AC_MODE] = True

                self.collected_config.update(user_input)
                return await self._determine_next_step()

        # Use AC-only specific schema with dedicated translations
        schema = get_basic_ac_schema(defaults=None, include_name=True)

        return self.async_show_form(
            step_id="basic_ac_only", data_schema=schema, errors=errors
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle unified features configuration for all system types.

        Present a single combined step where the user picks which feature
        areas to configure. The available features are automatically determined
        based on the system type. Subsequent steps will be shown conditionally
        based on these selections.
        """
        system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        if user_input is not None:
            # Store selections and proceed
            self.collected_config.update(user_input)
            # Clear toggles so they don't persist unexpectedly
            self.collected_config.pop("configure_advanced", None)
            self.collected_config.pop("advanced_shown", None)
            return await self._determine_next_step()

        # For initial display, ensure any previous feature flags are cleared
        self.collected_config.pop("configure_advanced", None)
        self.collected_config.pop("advanced_shown", None)

        return self.async_show_form(
            step_id="features",
            data_schema=get_features_schema(system_type),
            description_placeholders={
                "subtitle": "Choose which features to configure for your system"
            },
        )

    async def async_step_heater_cooler(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle heater with cooler configuration."""
        errors = {}

        if user_input is not None:
            # Extract advanced settings from section and flatten to top level
            if "advanced_settings" in user_input:
                advanced_settings = user_input.pop("advanced_settings")
                if advanced_settings:
                    user_input.update(advanced_settings)

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

        # Use dedicated heater+cooler schema with advanced settings in collapsible section
        schema = get_heater_cooler_schema()

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
        """Determine the next step based on configuration dependencies.

        CRITICAL: Configuration step ordering rules (see .copilot-instructions.md):
        1. Openings steps must be among the last configuration steps (depend on system config)
        2. Presets steps must be the absolute final steps (depend on all other settings)
        3. Feature configuration must be ordered based on dependencies
        """
        system_type = self.collected_config.get("system_type")
        # Show features configuration for all systems (when not already shown)
        if "features_shown" not in self.collected_config:
            self.collected_config["features_shown"] = True
            return await self.async_step_features()

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
            if system_type == SystemType.SIMPLE_HEATER:
                # Only go to floor config if the user opted in and floor
                # settings haven't already been provided to avoid looping
                if (
                    self.collected_config.get("configure_floor_heating")
                    and CONF_FLOOR_SENSOR not in self.collected_config
                ):
                    return await self.async_step_floor_config()
            else:
                # For other systems that support floor heating, only go to
                # floor config if the user opted in during features selection
                if (
                    self.collected_config.get("configure_floor_heating")
                    and CONF_FLOOR_SENSOR not in self.collected_config
                ):
                    return await self.async_step_floor_config()

        # Floor heating configuration is handled earlier where required.

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

        # For heater_cooler and heat_pump systems, show fan configuration if enabled
        if (
            system_type in ["heater_cooler", "heat_pump"]
            and self.collected_config.get("configure_fan")
            and CONF_FAN not in self.collected_config
        ):
            return await self.async_step_fan()

        # For heater_cooler and heat_pump systems, show humidity configuration if enabled
        if (
            system_type in ["heater_cooler", "heat_pump"]
            and self.collected_config.get("configure_humidity")
            and CONF_HUMIDITY_SENSOR not in self.collected_config
        ):
            return await self.async_step_humidity()

        # For specific system types, show relevant additional configs
        if (
            system_type == SystemType.DUAL_STAGE
            and CONF_AUX_HEATER not in self.collected_config
        ):
            return await self.async_step_dual_stage_config()

        # CRITICAL: Show openings configuration AFTER all feature configuration is complete
        # This ensures openings scope generation has access to all configured features

        # Show openings selection and config if the features-selection
        # step requested openings configuration (configure_openings).
        if (
            self.collected_config.get("configure_openings")
            and "selected_openings" not in self.collected_config
        ):
            return await self.async_step_openings_selection()

        if (
            system_type == "floor_heating"
            and CONF_FLOOR_SENSOR not in self.collected_config
        ):
            return await self.async_step_floor_config()

        # Show preset selection only if user explicitly enabled presets in features step
        if self.collected_config.get("configure_presets", False):
            return await self.async_step_preset_selection()
        else:
            # Skip presets and finish configuration
            return self.async_create_entry(
                title=self.async_config_entry_title(self.collected_config),
                data=self.collected_config,
            )

    def _has_both_heating_and_cooling(self) -> bool:
        """Check if system has both heating and cooling capability."""
        has_heater = bool(self.collected_config.get(CONF_HEATER))
        has_cooler = bool(self.collected_config.get(CONF_COOLER))
        has_heat_pump = bool(self.collected_config.get(CONF_HEAT_PUMP_COOLING))
        has_ac_mode = bool(self.collected_config.get(CONF_AC_MODE))

        return has_heater and (has_cooler or has_heat_pump or has_ac_mode)


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
