"""Options flow for Dual Smart Thermostat."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import DEGREE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (  # CONF_MIN_DUR and CONF_SENSOR are not used in this module; removed to satisfy linter
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_INITIAL_HVAC_MODE,
    CONF_KEEP_ALIVE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_PRECISION,
    CONF_SYSTEM_TYPE,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    CONF_TEMP_STEP,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_DUAL_STAGE,
    SYSTEM_TYPE_FLOOR_HEATING,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
    SYSTEM_TYPES,
)
from .feature_steps import (
    FanSteps,
    FloorSteps,
    HumiditySteps,
    OpeningsSteps,
    PresetsSteps,
)
from .schemas import (
    get_basic_ac_schema,
    get_core_schema,
    get_fan_toggle_schema,
    get_features_schema,
    get_heat_cool_mode_schema,
    get_heat_pump_schema,
    get_heater_cooler_schema,
    get_humidity_toggle_schema,
    get_simple_heater_schema,
)

_LOGGER = logging.getLogger(__name__)


class OptionsFlowHandler(OptionsFlow):
    """Handle options flow for Dual Smart Thermostat."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow.

        We avoid assigning ``self.config_entry`` here to prevent Home Assistant
        runtime deprecation warnings. The platform will set ``config_entry``
        on this object when running inside Home Assistant. For tests and any
        early access during construction we keep a private reference.
        """
        # Keep the initially passed entry privately for tests/early access.
        self._init_config_entry = config_entry
        self.collected_config = {}

        # Initialize feature step handlers
        self.openings_steps = OpeningsSteps()
        self.fan_steps = FanSteps()
        self.humidity_steps = HumiditySteps()
        self.presets_steps = PresetsSteps()
        self.floor_steps = FloorSteps()

    @staticmethod
    def _get_excluded_flags() -> set[str]:
        """Get set of transient flags that should not be persisted.

        These flags control flow navigation and should be excluded when
        copying config between sessions.
        """
        return {
            "dual_stage_options_shown",
            "floor_options_shown",
            "features_shown",
            "fan_options_shown",
            "humidity_options_shown",
            "openings_options_shown",
            "presets_shown",
            "configure_openings",
            "configure_presets",
            "configure_fan",
            "configure_humidity",
            "configure_floor_heating",
            "system_type_changed",
        }

    def _get_current_config(self) -> dict[str, Any]:
        """Get current configuration merging data and options.

        Home Assistant OptionsFlow saves to entry.options, not entry.data.
        This method merges both, with options taking precedence.
        """
        entry = self._get_entry()
        # entry.options might be empty dict or not exist (in tests)
        options = getattr(entry, "options", {}) or {}
        # entry.data is a mappingproxy in real HA, dict or Mock in tests
        # Convert to dict for merging - check if it's dict-like first
        try:
            data = dict(entry.data) if entry.data else {}
        except (TypeError, AttributeError):
            data = entry.data if isinstance(entry.data, dict) else {}
        try:
            options = dict(options) if options else {}
        except (TypeError, AttributeError):
            options = options if isinstance(options, dict) else {}
        return {**data, **options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First options step: allow changing (or keeping) the system type."""
        current_config = self._get_current_config()

        _LOGGER.debug(
            "Options flow INIT - Config entry data at start: fan=%s, fan_mode=%s, fan_on_with_ac=%s",
            current_config.get("fan"),
            current_config.get("fan_mode"),
            current_config.get("fan_on_with_ac"),
        )

        current_system_type = current_config.get(
            CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER
        )

        if user_input is not None:
            # If user changed system type, store override in collected_config
            selected_type = user_input.get(CONF_SYSTEM_TYPE, current_system_type)

            # Copy current_config but exclude transient flow state flags
            # These flags control flow navigation and should not be persisted
            excluded_flags = self._get_excluded_flags()
            self.collected_config = {
                k: v for k, v in current_config.items() if k not in excluded_flags
            }

            if selected_type != current_system_type:
                self.collected_config[CONF_SYSTEM_TYPE] = selected_type
                self.collected_config["system_type_changed"] = True
            else:
                self.collected_config["system_type_changed"] = False

            # Clear step flags to allow users to see all steps again in options flow
            step_flags = [
                "dual_stage_options_shown",
                "floor_options_shown",
                "features_shown",  # The unified features step flag
                "fan_options_shown",
                "humidity_options_shown",
                "openings_options_shown",
                "presets_shown",
            ]
            # Also clear any transient "configure_*" toggles that may have been
            # saved in the entry data from a previous run. These should not be
            # treated as persistent configuration and can cause the options
            # flow to jump directly to a feature's detailed options.
            transient_config_flags = [
                "configure_openings",
                "configure_presets",
                "configure_fan",
                "configure_humidity",
                "configure_floor_heating",
            ]
            step_flags.extend(transient_config_flags)
            for flag in step_flags:
                self.collected_config.pop(flag, None)

            # Proceed to basic reconfiguration step
            return await self.async_step_basic()

        # Reuse existing system type schema but default to current system type
        # Provide description so user understands they can leave unchanged
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SYSTEM_TYPE,
                    default=current_system_type,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v} for k, v in SYSTEM_TYPES.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="init",
            description_placeholders={"current": current_system_type},
            data_schema=schema,
        )

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Basic system entities & tolerances reconfiguration."""
        if user_input is not None:
            # Extract advanced settings from section and flatten to top level
            if "advanced_settings" in user_input:
                advanced_settings = user_input.pop("advanced_settings")
                if advanced_settings:
                    user_input.update(advanced_settings)

            # Preserve unmodified fields: merge current config into collected_config first
            # This ensures fields not in user_input are preserved
            current_config = self._get_current_config()
            # Define flags that should NOT be copied from current_config
            # These are transient state flags that control flow navigation
            excluded_flags = self._get_excluded_flags()
            # Only add fields from current_config that aren't already in collected_config
            # and aren't excluded flags
            for key, value in current_config.items():
                if key not in self.collected_config and key not in excluded_flags:
                    self.collected_config[key] = value

            # Merge edits with any previously stored overrides
            effective_system_type = self.collected_config.get(
                CONF_SYSTEM_TYPE,
                current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
            )
            if effective_system_type == SYSTEM_TYPE_AC_ONLY:
                # Enforce AC mode True and discard cooler/heat pump cooling in AC-only
                user_input[CONF_AC_MODE] = True
                user_input.pop(CONF_COOLER, None)
                user_input.pop(CONF_HEAT_PUMP_COOLING, None)
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_current_config()
        # If system type was changed in first step use override for defaults logic if needed later
        effective_system_type = self.collected_config.get(
            CONF_SYSTEM_TYPE,
            current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
        )

        _LOGGER.debug(
            "Options flow BASIC - collected_config system_type=%s, current_config system_type=%s, effective=%s",
            self.collected_config.get(CONF_SYSTEM_TYPE),
            current_config.get(CONF_SYSTEM_TYPE),
            effective_system_type,
        )
        _LOGGER.debug(
            "Options flow BASIC - collected_config keys: %s",
            list(self.collected_config.keys()),
        )

        # Build a shared basic schema used by both config and options flows.
        # Provide current_config as defaults and omit the name field in options flow.

        # For simple heater systems, use the dedicated schema with advanced settings
        if effective_system_type == SYSTEM_TYPE_SIMPLE_HEATER:
            schema = get_simple_heater_schema(
                defaults=current_config, include_name=False
            )
        elif effective_system_type == SYSTEM_TYPE_AC_ONLY:
            # For AC-only systems, use the dedicated schema with advanced settings in collapsible section
            schema = get_basic_ac_schema(defaults=current_config, include_name=False)
        elif effective_system_type == SYSTEM_TYPE_HEATER_COOLER:
            # For heater+cooler systems, use the dedicated schema with advanced settings in collapsible section
            schema = get_heater_cooler_schema(
                defaults=current_config, include_name=False
            )
        elif effective_system_type == SYSTEM_TYPE_HEAT_PUMP:
            # For heat pump systems, use the dedicated schema with advanced settings in collapsible section
            schema = get_heat_pump_schema(defaults=current_config, include_name=False)
        else:
            schema = get_core_schema(
                effective_system_type, defaults=current_config, include_name=False
            )

        return self.async_show_form(
            step_id="basic",
            data_schema=schema,
        )

    async def _determine_options_next_step(self) -> FlowResult:
        """Determine next step for options flow.

        CRITICAL: Configuration step ordering rules (see .copilot-instructions.md):
        1. Openings steps must be among the last configuration steps (depend on system config)
        2. Presets steps must be the absolute final steps (depend on all other settings)
        3. Feature configuration must be ordered based on dependencies
        """
        current_config = self._get_current_config()
        # If user changed system type earlier, use override; else original persisted
        original_system_type = self.collected_config.get(
            CONF_SYSTEM_TYPE,
            current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
        )

        # (heat/cool mode routing moved below to mirror config_flow ordering)

        # Show dual stage options only for dual_stage system type

        if (
            original_system_type == SYSTEM_TYPE_DUAL_STAGE
        ) and "dual_stage_options_shown" not in self.collected_config:
            self.collected_config["dual_stage_options_shown"] = True
            return await self.async_step_dual_stage_options()

        # Show floor heating options only for floor_heating systems
        if (
            original_system_type == SYSTEM_TYPE_FLOOR_HEATING
            and "floor_options_shown" not in self.collected_config
        ):
            self.collected_config["floor_options_shown"] = True
            return await self.async_step_floor_options()

        # If user selected floor heating in a features step (e.g. simple heater),
        # go straight to the floor options instead of showing an extra toggle.
        if (
            self.collected_config.get("configure_floor_heating")
            and "floor_options_shown" not in self.collected_config
        ):
            self.collected_config["floor_options_shown"] = True
            return await self.async_step_floor_options()

        # Show unified features configuration for all systems
        if "features_shown" not in self.collected_config:
            self.collected_config["features_shown"] = True
            return await self.async_step_features()

        # Show fan options if fan toggle was enabled or if fan is already configured
        if (
            self.collected_config.get("configure_fan") or current_config.get(CONF_FAN)
        ) and "fan_options_shown" not in self.collected_config:
            self.collected_config["fan_options_shown"] = True
            return await self.async_step_fan_options()

        # Show humidity options if humidity toggle was enabled or if humidity sensor is already configured
        if (
            self.collected_config.get("configure_humidity")
            or current_config.get(CONF_HUMIDITY_SENSOR)
        ) and "humidity_options_shown" not in self.collected_config:
            self.collected_config["humidity_options_shown"] = True
            return await self.async_step_humidity_options()

        # CRITICAL: Show openings options AFTER all feature configuration is complete
        # This ensures openings scope generation has access to all configured features

        # Show openings options only if user selected configure_openings in features step
        # This is now consistent across all system types
        should_show_openings = self.collected_config.get("configure_openings", False)

        if (
            should_show_openings
            and "openings_options_shown" not in self.collected_config
        ):
            self.collected_config["openings_options_shown"] = True
            return await self.async_step_openings_options()

        # Show preset configuration only if user selected configure_presets in features step
        # This is now consistent across all system types
        should_show_presets = self.collected_config.get("configure_presets", False)

        if should_show_presets and "presets_shown" not in self.collected_config:
            self.collected_config["presets_shown"] = True
            return await self.async_step_preset_selection()

        # Final step - update the config entry
        # Merge collected config with existing entry data to preserve all fields
        entry = self._get_entry()

        # DEBUG: Log fan-related settings before and after merge
        _LOGGER.debug(
            "Options flow completion - entry.data fan settings: fan=%s, fan_mode=%s, fan_on_with_ac=%s",
            entry.data.get("fan"),
            entry.data.get("fan_mode"),
            entry.data.get("fan_on_with_ac"),
        )
        _LOGGER.debug(
            "Options flow completion - collected_config fan settings: fan=%s, fan_mode=%s, fan_on_with_ac=%s",
            self.collected_config.get("fan"),
            self.collected_config.get("fan_mode"),
            self.collected_config.get("fan_on_with_ac"),
        )

        # Clean transient flags before saving
        excluded_flags = self._get_excluded_flags()
        cleaned_collected_config = {
            k: v for k, v in self.collected_config.items() if k not in excluded_flags
        }
        updated_data = {**entry.data, **cleaned_collected_config}

        _LOGGER.debug(
            "Options flow completion - updated_data fan settings: fan=%s, fan_mode=%s, fan_on_with_ac=%s",
            updated_data.get("fan"),
            updated_data.get("fan_mode"),
            updated_data.get("fan_on_with_ac"),
        )

        _LOGGER.debug(
            "Options flow - Calling async_create_entry with %d keys in data",
            len(updated_data),
        )
        _LOGGER.debug(
            "Options flow - Sample of data being saved: fan=%s, fan_mode=%s, fan_on_with_ac=%s, name=%s",
            updated_data.get("fan"),
            updated_data.get("fan_mode"),
            updated_data.get("fan_on_with_ac"),
            updated_data.get("name"),
        )

        result = self.async_create_entry(
            title="",  # Empty title for options flow
            data=updated_data,
        )

        _LOGGER.debug("Options flow - async_create_entry returned: %s", result)
        return result

    async def async_step_dual_stage_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle dual stage options."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_current_config()
        schema_dict: dict[Any, Any] = {}

        # Always show auxiliary heater option
        schema_dict[
            vol.Optional(CONF_AUX_HEATER, default=current_config.get(CONF_AUX_HEATER))
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))

        # Always show auxiliary heating timeout
        schema_dict[
            vol.Optional(
                CONF_AUX_HEATING_TIMEOUT,
                default=current_config.get(CONF_AUX_HEATING_TIMEOUT),
            )
        ] = selector.DurationSelector(
            selector.DurationSelectorConfig(allow_negative=False)
        )

        # Always show dual mode option
        schema_dict[
            vol.Optional(
                CONF_AUX_HEATING_DUAL_MODE,
                default=current_config.get(CONF_AUX_HEATING_DUAL_MODE, False),
            )
        ] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="dual_stage_options",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_floor_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delegate floor heating options to shared FloorSteps handler."""
        current_config = self._get_current_config()
        return await self.floor_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            current_config,
        )

    async def async_step_fan_toggle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle fan toggle configuration in options flow."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        return self.async_show_form(
            step_id="fan_toggle",
            data_schema=get_fan_toggle_schema(),
        )

    async def async_step_humidity_toggle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity toggle configuration in options flow."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        return self.async_show_form(
            step_id="humidity_toggle",
            data_schema=get_humidity_toggle_schema(),
        )

    async def async_step_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle unified features configuration for all system types in options flow.

        Present a single combined step where the user picks which feature
        areas to configure. The available features are automatically determined
        based on the system type.
        """
        if user_input is not None:
            # Process the submission and continue
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_current_config()
        system_type = current_config.get(CONF_SYSTEM_TYPE)

        # Determine which feature toggles should be pre-checked based on
        # whether those features are already configured
        feature_defaults = {}

        # Fan: check if fan entity is configured
        if current_config.get(CONF_FAN):
            feature_defaults["configure_fan"] = True

        # Humidity: check if humidity sensor is configured
        if current_config.get(CONF_HUMIDITY_SENSOR):
            feature_defaults["configure_humidity"] = True

        # Floor heating: check if floor sensor is configured
        if current_config.get(CONF_FLOOR_SENSOR):
            feature_defaults["configure_floor_heating"] = True

        # Openings: check if openings list exists and is not empty
        if current_config.get("openings"):
            feature_defaults["configure_openings"] = True

        # Presets: check if any presets are configured
        # Presets can be stored in two formats:
        # 1. "presets" list: ["away", "home", "sleep"]
        # 2. Preset config keys: "away_temp", "home_temp", etc.
        has_presets_list = bool(current_config.get("presets"))
        preset_temp_keys = [
            "away_temp",
            "home_temp",
            "sleep_temp",
            "activity_temp",
            "comfort_temp",
            "eco_temp",
            "boost_temp",
        ]
        has_preset_config = any(current_config.get(key) for key in preset_temp_keys)
        if has_presets_list or has_preset_config:
            feature_defaults["configure_presets"] = True

        return self.async_show_form(
            step_id="features",
            data_schema=get_features_schema(
                system_type,
                {
                    **feature_defaults,
                    **self.collected_config,
                },
            ),
            description_placeholders={
                "subtitle": "Choose which features to configure for your system"
            },
        )

    async def async_step_fan_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle fan options."""
        # Use merged config to get latest values (from both .data, .options, and current session)
        current_config = {**self._get_current_config(), **self.collected_config}
        return await self.fan_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            current_config,
        )

    async def async_step_humidity_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity options."""
        current_config = self._get_current_config()
        return await self.humidity_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            current_config,
        )

    async def async_step_advanced_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced options configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()
        current_config = self._get_current_config()
        effective_system_type = self.collected_config.get(
            CONF_SYSTEM_TYPE,
            current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
        )
        schema_dict: dict[Any, Any] = {}

        # Temperature limits - always show with sensible defaults
        schema_dict[
            vol.Optional(CONF_MIN_TEMP, default=current_config.get(CONF_MIN_TEMP, 7))
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        schema_dict[
            vol.Optional(CONF_MAX_TEMP, default=current_config.get(CONF_MAX_TEMP, 35))
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        # Target temperatures - always optional with no default to avoid making it look required
        schema_dict[vol.Optional(CONF_TARGET_TEMP)] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        # Tolerance settings - always show with sensible defaults
        schema_dict[
            vol.Optional(
                CONF_COLD_TOLERANCE,
                default=current_config.get(CONF_COLD_TOLERANCE, 0.3),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_HOT_TOLERANCE,
                default=current_config.get(CONF_HOT_TOLERANCE, 0.3),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
            )
        )

        # Precision and step settings - always show with defaults
        schema_dict[
            vol.Optional(
                CONF_PRECISION, default=current_config.get(CONF_PRECISION, "0.1")
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["0.1", "0.5", "1.0"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_TEMP_STEP, default=current_config.get(CONF_TEMP_STEP, "1.0")
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["0.1", "0.5", "1.0"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # Timing configuration
        # Keep alive - always optional with no default
        schema_dict[vol.Optional(CONF_KEEP_ALIVE)] = selector.DurationSelector(
            selector.DurationSelectorConfig(allow_negative=False)
        )

        # Initial HVAC mode - filter options based on system type
        hvac_mode_options = []
        if effective_system_type != SYSTEM_TYPE_AC_ONLY:
            # Non-AC systems can use heat mode
            hvac_mode_options.extend(["heat", "heat_cool"])

        # All systems can use these modes
        hvac_mode_options.extend(["cool", "off", "fan_only", "dry"])

        schema_dict[vol.Optional(CONF_INITIAL_HVAC_MODE)] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=hvac_mode_options,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # Target temperature ranges for dual stage systems - only for non-AC-only systems
        if effective_system_type != SYSTEM_TYPE_AC_ONLY:
            schema_dict[
                vol.Optional(
                    CONF_TARGET_TEMP_HIGH,
                    default=current_config.get(CONF_TARGET_TEMP_HIGH),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
                )
            )

            schema_dict[
                vol.Optional(
                    CONF_TARGET_TEMP_LOW,
                    default=current_config.get(CONF_TARGET_TEMP_LOW),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
                )
            )

        # Heat/Cool mode settings - only for non-AC-only systems
        if effective_system_type != SYSTEM_TYPE_AC_ONLY:
            schema_dict[
                vol.Optional(
                    CONF_HEAT_COOL_MODE, default=current_config.get(CONF_HEAT_COOL_MODE)
                )
            ] = selector.BooleanSelector()

        return self.async_show_form(
            step_id="advanced_options",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_openings_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle openings options."""
        return await self.openings_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            self._get_merged_config(),
        )

    async def async_step_openings_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the detailed openings config step submissions.

        The OpeningsSteps helper renders the detailed form using the step id
        `openings_config`. Home Assistant will call
        `async_step_openings_config` on the flow handler when that form is
        submitted, so we must delegate back to the helper to process the
        submission and advance the flow.
        """
        return await self.openings_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            self._get_merged_config(),
        )

    async def async_step_preset_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle preset selection step in options flow."""
        return await self.presets_steps.async_step_selection(
            self, user_input, self.collected_config, self._determine_options_next_step
        )

    async def async_step_heat_cool_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle heat/cool mode configuration in options flow."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        return self.async_show_form(
            step_id="heat_cool_mode",
            data_schema=get_heat_cool_mode_schema(),
        )

    def _has_both_heating_and_cooling(self) -> bool:
        """Check if system has both heating and cooling capability in options flow."""
        # Prefer collected overrides, fall back to stored entry
        current_config = self._get_current_config()
        has_heater = bool(
            self.collected_config.get(CONF_HEATER) or current_config.get(CONF_HEATER)
        )
        has_cooler = bool(
            self.collected_config.get(CONF_COOLER) or current_config.get(CONF_COOLER)
        )
        has_heat_pump = bool(
            self.collected_config.get(CONF_HEAT_PUMP_COOLING)
            or current_config.get(CONF_HEAT_PUMP_COOLING)
        )
        has_ac_mode = bool(
            self.collected_config.get(CONF_AC_MODE) or current_config.get(CONF_AC_MODE)
        )

        return has_heater and (has_cooler or has_heat_pump or has_ac_mode)

    async def async_step_presets(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle presets configuration in options flow."""
        return await self.presets_steps.async_step_options(
            self, user_input, self.collected_config, self._determine_options_next_step
        )

    def _get_entry(self):
        """Return the active config entry.

        Home Assistant will set `self.config_entry` on the options flow handler when
        running inside Home Assistant. We avoid assigning that attribute ourselves to
        prevent the deprecation warning; fall back to the initially passed entry for
        tests and early access.
        """
        # Avoid triggering the base class `config_entry` property, which may
        # access Home Assistant internals that are not available during
        # test-time initialization. Check the instance dict first to see if
        # Home Assistant has already set the attribute on this object.
        #
        # NOTE: We intentionally do not assign ``self.config_entry`` in
        # __init__ to avoid the Home Assistant runtime deprecation warning
        # about custom integrations setting this attribute explicitly.
        # Instead Home Assistant will set the attribute on the handler at
        # runtime; tests and code that need the entry during construction
        # should use this private fallback. This keeps the runtime code
        # warning-free while preserving test behavior.
        if "config_entry" in self.__dict__:
            return self.__dict__["config_entry"]
        return self._init_config_entry

    def _get_merged_config(self):
        """Get merged configuration from entry data and options.

        Returns configuration with options taking priority over data.
        This ensures that updated options are used instead of stale data.
        """
        entry = self._get_entry()
        merged_config = dict(entry.data)
        merged_config.update(entry.options)
        return merged_config

    @property
    def config_entry(self):
        """Compatibility property for tests.

        Return the config entry set by Home Assistant if present on the
        instance, otherwise fall back to the initially passed entry. This
        avoids assigning the attribute ourselves (which triggers the
        deprecation warning) while still supporting tests that access
        ``handler.config_entry`` directly.
        """
        if "config_entry" in self.__dict__:
            return self.__dict__["config_entry"]
        return self._init_config_entry


# Backward compatibility alias for tests
DualSmartThermostatOptionsFlow = OptionsFlowHandler
