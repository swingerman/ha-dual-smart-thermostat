"""Options flow for Dual Smart Thermostat."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import DEGREE
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.helpers import selector
import voluptuous as vol

from .config_validation import validate_config_with_models
from .const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COLD_TOLERANCE,
    CONF_COOL_TOLERANCE,
    CONF_COOLER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEAT_TOLERANCE,
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
)
from .feature_steps import (
    FanSteps,
    FloorSteps,
    HumiditySteps,
    OpeningsSteps,
    PresetsSteps,
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

    def _build_options_schema(self, current_config: dict[str, Any]) -> vol.Schema:
        """Build schema for options flow with runtime tuning parameters.

        This method creates a form with only runtime tuning parameters.
        Structural configuration (system type, entities, features) belongs in reconfigure flow.

        Args:
            current_config: Current configuration from entry.data

        Returns:
            Voluptuous schema for the options form
        """
        schema_dict: dict[Any, Any] = {}

        # === BASIC TOLERANCES (always shown) ===
        schema_dict[
            vol.Optional(
                CONF_COLD_TOLERANCE,
                default=current_config.get(CONF_COLD_TOLERANCE, 0.3),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
                unit_of_measurement=DEGREE,
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
                unit_of_measurement=DEGREE,
            )
        )

        # === TEMPERATURE LIMITS (always shown) ===
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

        schema_dict[
            vol.Optional(CONF_TARGET_TEMP, default=current_config.get(CONF_TARGET_TEMP))
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        # === PRECISION AND STEP (always shown) ===
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

        # === ADVANCED SETTINGS (collapsible section) ===
        advanced_dict: dict[Any, Any] = {}

        # Keep alive
        if current_config.get(CONF_KEEP_ALIVE):
            advanced_dict[
                vol.Optional(
                    CONF_KEEP_ALIVE, default=current_config.get(CONF_KEEP_ALIVE)
                )
            ] = selector.DurationSelector(
                selector.DurationSelectorConfig(allow_negative=False)
            )

        # Initial HVAC mode
        system_type = current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER)
        hvac_mode_options = []
        if system_type != SYSTEM_TYPE_AC_ONLY:
            hvac_mode_options.extend(["heat", "heat_cool"])
        hvac_mode_options.extend(["cool", "off", "fan_only", "dry"])

        if current_config.get(CONF_INITIAL_HVAC_MODE):
            advanced_dict[
                vol.Optional(
                    CONF_INITIAL_HVAC_MODE,
                    default=current_config.get(CONF_INITIAL_HVAC_MODE),
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=hvac_mode_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

        # Target temperature ranges (for heat_cool mode)
        if system_type != SYSTEM_TYPE_AC_ONLY:
            if current_config.get(CONF_TARGET_TEMP_HIGH):
                advanced_dict[
                    vol.Optional(
                        CONF_TARGET_TEMP_HIGH,
                        default=current_config.get(CONF_TARGET_TEMP_HIGH),
                    )
                ] = selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=DEGREE,
                    )
                )

            if current_config.get(CONF_TARGET_TEMP_LOW):
                advanced_dict[
                    vol.Optional(
                        CONF_TARGET_TEMP_LOW,
                        default=current_config.get(CONF_TARGET_TEMP_LOW),
                    )
                ] = selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=DEGREE,
                    )
                )

            # Heat/Cool mode
            if current_config.get(CONF_HEAT_COOL_MODE) is not None:
                advanced_dict[
                    vol.Optional(
                        CONF_HEAT_COOL_MODE,
                        default=current_config.get(CONF_HEAT_COOL_MODE),
                    )
                ] = selector.BooleanSelector()

        # Separate tolerances for heating and cooling
        # Only show for dual-mode systems (heater_cooler and heat_pump)
        if system_type in (SYSTEM_TYPE_HEATER_COOLER, SYSTEM_TYPE_HEAT_PUMP):
            advanced_dict[
                vol.Optional(
                    CONF_HEAT_TOLERANCE,
                    description={
                        "suggested_value": current_config.get(CONF_HEAT_TOLERANCE)
                    },
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    unit_of_measurement=DEGREE,
                )
            )

            advanced_dict[
                vol.Optional(
                    CONF_COOL_TOLERANCE,
                    description={
                        "suggested_value": current_config.get(CONF_COOL_TOLERANCE)
                    },
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0.1,
                    max=5.0,
                    step=0.1,
                    unit_of_measurement=DEGREE,
                )
            )

        # Add advanced settings section if there are any fields
        if advanced_dict:
            schema_dict[vol.Optional("advanced_settings")] = section(
                vol.Schema(advanced_dict), {"collapsed": True}
            )

        return vol.Schema(schema_dict)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle runtime tuning parameters for Dual Smart Thermostat.

        This simplified options flow focuses on runtime parameters only.
        For structural changes (system type, entities, features), use reconfigure flow.
        """
        current_config = self._get_current_config()

        if user_input is not None:
            # Extract advanced settings from section and flatten to top level
            if "advanced_settings" in user_input:
                advanced_settings = user_input.pop("advanced_settings")
                if advanced_settings:
                    user_input.update(advanced_settings)

            # Copy current_config but exclude transient flow state flags
            excluded_flags = self._get_excluded_flags()
            self.collected_config = {
                k: v for k, v in current_config.items() if k not in excluded_flags
            }

            # Clear step flags to allow users to see all steps again
            step_flags = [
                "dual_stage_options_shown",
                "floor_options_shown",
                "fan_options_shown",
                "humidity_options_shown",
                "openings_options_shown",
                "presets_shown",
            ]
            for flag in step_flags:
                self.collected_config.pop(flag, None)

            # Update with user's changes
            self.collected_config.update(user_input)

            # Proceed to multi-step feature configuration if needed
            return await self._determine_options_next_step()

        # Build schema with runtime tuning parameters
        schema = self._build_options_schema(current_config)

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "name": current_config.get("name", "Dual Smart Thermostat")
            },
        )

    async def _determine_options_next_step(self) -> FlowResult:
        """Determine next step for options flow.

        This simplified version only shows multi-step configuration for features
        that are already configured. For enabling/disabling features, use reconfigure flow.

        CRITICAL: Configuration step ordering rules:
        1. Feature-specific tuning (floor, fan, humidity, dual stage)
        2. Openings configuration (depends on system config)
        3. Presets configuration (must be last, depends on all other settings)
        """
        current_config = self._get_current_config()
        system_type = current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER)

        # Show dual stage options if aux heater is configured
        if (
            system_type == SYSTEM_TYPE_DUAL_STAGE or current_config.get(CONF_AUX_HEATER)
        ) and "dual_stage_options_shown" not in self.collected_config:
            self.collected_config["dual_stage_options_shown"] = True
            return await self.async_step_dual_stage_options()

        # Show floor heating options if floor sensor is configured
        if (
            system_type == SYSTEM_TYPE_FLOOR_HEATING
            or current_config.get(CONF_FLOOR_SENSOR)
        ) and "floor_options_shown" not in self.collected_config:
            self.collected_config["floor_options_shown"] = True
            return await self.async_step_floor_options()

        # Show fan options if fan is configured
        if (
            current_config.get(CONF_FAN)
            and "fan_options_shown" not in self.collected_config
        ):
            self.collected_config["fan_options_shown"] = True
            return await self.async_step_fan_options()

        # Show humidity options if humidity sensor is configured
        if (
            current_config.get(CONF_HUMIDITY_SENSOR)
            and "humidity_options_shown" not in self.collected_config
        ):
            self.collected_config["humidity_options_shown"] = True
            return await self.async_step_humidity_options()

        # CRITICAL: Show openings options AFTER all feature configuration is complete
        # Show openings options only if openings are already configured
        if (
            current_config.get("openings")
            and "openings_options_shown" not in self.collected_config
        ):
            self.collected_config["openings_options_shown"] = True
            return await self.async_step_openings_options()

        # Show preset configuration only if presets are already configured
        # Check both "presets" list and preset temperature keys
        preset_temp_keys = [
            "away_temp",
            "home_temp",
            "sleep_temp",
            "activity_temp",
            "comfort_temp",
            "eco_temp",
            "boost_temp",
        ]
        has_presets = current_config.get("presets") or any(
            current_config.get(key) for key in preset_temp_keys
        )

        if has_presets and "presets_shown" not in self.collected_config:
            self.collected_config["presets_shown"] = True
            return await self.async_step_preset_selection()

        # Final step - update the config entry
        entry = self._get_entry()

        # Clean transient flags before saving - from BOTH entry.data and collected_config
        # This is critical because transient flags might be in storage (entry.data)
        excluded_flags = self._get_excluded_flags()
        cleaned_entry_data = {
            k: v for k, v in dict(entry.data).items() if k not in excluded_flags
        }
        cleaned_collected_config = {
            k: v for k, v in self.collected_config.items() if k not in excluded_flags
        }
        updated_data = {**cleaned_entry_data, **cleaned_collected_config}

        # Convert string values from select selectors to proper numeric types
        # SelectSelector always returns strings, but these should be floats
        # (fixes issue #468 where precision/temp_step stored as strings)
        float_keys = [CONF_PRECISION, CONF_TEMP_STEP]
        for key in float_keys:
            if key in updated_data and isinstance(updated_data[key], str):
                try:
                    updated_data[key] = float(updated_data[key])
                except (ValueError, TypeError):
                    pass  # Keep original value if conversion fails

        # Validate configuration using models for type safety
        if not validate_config_with_models(updated_data):
            _LOGGER.warning(
                "Configuration validation failed for %s. "
                "Please check your configuration.",
                updated_data.get("name", "thermostat"),
            )

        return self.async_create_entry(
            title="",
            data=updated_data,  # Empty title for options flow
        )

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
