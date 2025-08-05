"""Options flow for Dual Smart Thermostat."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import DEGREE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
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
    CONF_MAX_FLOOR_TEMP,
    CONF_MAX_TEMP,
    CONF_MIN_DUR,
    CONF_MIN_FLOOR_TEMP,
    CONF_MIN_TEMP,
    CONF_PRECISION,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    CONF_TEMP_STEP,
    DEFAULT_TOLERANCE,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_DUAL_STAGE,
    SYSTEM_TYPE_FLOOR_HEATING,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
    SYSTEM_TYPES,
)
from .feature_steps import FanSteps, HumiditySteps, OpeningsSteps, PresetsSteps
from .schemas import get_fan_toggle_schema, get_humidity_toggle_schema


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
        self.collected_config: dict[str, Any] = {}

        # Initialize feature step handlers
        self.openings_steps = OpeningsSteps()
        self.fan_steps = FanSteps()
        self.humidity_steps = HumiditySteps()
        self.presets_steps = PresetsSteps()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First options step: allow changing (or keeping) the system type."""
        current_config = self._get_entry().data
        current_system_type = current_config.get(
            CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER
        )

        if user_input is not None:
            # If user changed system type, store override in collected_config
            selected_type = user_input.get(CONF_SYSTEM_TYPE, current_system_type)
            self.collected_config = dict(current_config)
            if selected_type != current_system_type:
                self.collected_config[CONF_SYSTEM_TYPE] = selected_type
                self.collected_config["system_type_changed"] = True
            else:
                self.collected_config["system_type_changed"] = False

            # Clear step flags to allow users to see all steps again in options flow
            step_flags = [
                "dual_stage_options_shown",
                "floor_options_shown",
                "ac_only_features_shown",
                "advanced_shown",
                "configure_advanced",  # Clear the advanced toggle state
                "fan_toggle_shown",
                "fan_options_shown",
                "humidity_toggle_shown",
                "humidity_options_shown",
                "openings_options_shown",
                "presets_shown",
                "advanced_options_shown",
            ]
            for flag in step_flags:
                self.collected_config.pop(flag, None)

            # Proceed to core reconfiguration step
            return await self.async_step_core()

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

    async def async_step_core(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Core system entities & tolerances reconfiguration (previous init)."""
        if user_input is not None:
            # Merge edits with any previously stored overrides
            effective_system_type = self.collected_config.get(
                CONF_SYSTEM_TYPE,
                self._get_entry().data.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
            )
            if effective_system_type == SYSTEM_TYPE_AC_ONLY:
                # Enforce AC mode True and discard cooler/heat pump cooling in AC-only
                user_input[CONF_AC_MODE] = True
                user_input.pop(CONF_COOLER, None)
                user_input.pop(CONF_HEAT_PUMP_COOLING, None)
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_entry().data
        # If system type was changed in first step use override for defaults logic if needed later
        effective_system_type = self.collected_config.get(
            CONF_SYSTEM_TYPE,
            current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
        )

        schema_dict: dict[Any, Any] = {}

        # Migration: if AC-only and legacy config stored device as cooler without heater, treat cooler as heater
        if effective_system_type == SYSTEM_TYPE_AC_ONLY:
            legacy_cooler = current_config.get(CONF_COOLER)
            if not current_config.get(CONF_HEATER) and legacy_cooler:
                # Stash into collected_config so it will be saved as heater later
                self.collected_config[CONF_HEATER] = legacy_cooler

        schema_dict[
            vol.Required(
                CONF_HEATER,
                default=(
                    self.collected_config.get(CONF_HEATER)
                    or current_config.get(CONF_HEATER)
                    or current_config.get(CONF_COOLER)
                ),
            )
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))
        schema_dict[
            vol.Required(CONF_SENSOR, default=current_config.get(CONF_SENSOR))
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        if effective_system_type != SYSTEM_TYPE_AC_ONLY:
            schema_dict[
                vol.Optional(CONF_COOLER, default=current_config.get(CONF_COOLER))
            ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))
            schema_dict[
                vol.Optional(
                    CONF_AC_MODE, default=current_config.get(CONF_AC_MODE, False)
                )
            ] = selector.BooleanSelector()
            schema_dict[
                vol.Optional(
                    CONF_HEAT_PUMP_COOLING,
                    default=current_config.get(CONF_HEAT_PUMP_COOLING, False),
                )
            ] = selector.BooleanSelector()
        else:
            # AC-only: hide AC mode (forced true) and heat pump toggle
            self.collected_config[CONF_AC_MODE] = True
        schema_dict[
            vol.Optional(
                CONF_COLD_TOLERANCE,
                default=current_config.get(CONF_COLD_TOLERANCE, DEFAULT_TOLERANCE),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
                min=0.1,
                max=5.0,
            )
        )
        schema_dict[
            vol.Optional(
                CONF_HOT_TOLERANCE,
                default=current_config.get(CONF_HOT_TOLERANCE, DEFAULT_TOLERANCE),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
                min=0.1,
                max=5.0,
            )
        )
        schema_dict[vol.Optional(CONF_MIN_DUR)] = selector.DurationSelector(
            selector.DurationSelectorConfig(allow_negative=False)
        )

        return self.async_show_form(
            step_id="core",
            data_schema=vol.Schema(schema_dict),
        )

    async def _determine_options_next_step(self) -> FlowResult:
        """Determine next step for options flow."""
        current_config = self._get_entry().data
        # If user changed system type earlier, use override; else original persisted
        original_system_type = self.collected_config.get(
            CONF_SYSTEM_TYPE,
            current_config.get(CONF_SYSTEM_TYPE, SYSTEM_TYPE_SIMPLE_HEATER),
        )

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

        # For AC-only systems, show combined features configuration
        if (
            original_system_type == SYSTEM_TYPE_AC_ONLY
            and "ac_only_features_shown" not in self.collected_config
        ):
            self.collected_config["ac_only_features_shown"] = True
            return await self.async_step_ac_only_features()

        # Show fan toggle for other systems with cooling capability
        if (
            original_system_type in [SYSTEM_TYPE_HEATER_COOLER, SYSTEM_TYPE_HEAT_PUMP]
            and "fan_toggle_shown" not in self.collected_config
        ):
            self.collected_config["fan_toggle_shown"] = True
            return await self.async_step_fan_toggle()

        # Show fan options if fan toggle was enabled or if fan is already configured
        if (
            self.collected_config.get("configure_fan") or current_config.get(CONF_FAN)
        ) and "fan_options_shown" not in self.collected_config:
            self.collected_config["fan_options_shown"] = True
            return await self.async_step_fan_options()

        # Show humidity toggle for other systems with cooling capability
        if (
            original_system_type in [SYSTEM_TYPE_HEATER_COOLER, SYSTEM_TYPE_HEAT_PUMP]
            and "humidity_toggle_shown" not in self.collected_config
        ):
            self.collected_config["humidity_toggle_shown"] = True
            return await self.async_step_humidity_toggle()

        # Show humidity options if humidity toggle was enabled or if humidity sensor is already configured
        if (
            self.collected_config.get("configure_humidity")
            or current_config.get(CONF_HUMIDITY_SENSOR)
        ) and "humidity_options_shown" not in self.collected_config:
            self.collected_config["humidity_options_shown"] = True
            return await self.async_step_humidity_options()

        # Show openings options - for AC-only systems only if enabled, for others always
        if original_system_type == SYSTEM_TYPE_AC_ONLY:
            if (
                self.collected_config.get("configure_openings")
                and "openings_options_shown" not in self.collected_config
            ):
                self.collected_config["openings_options_shown"] = True
                return await self.async_step_openings_options()
        else:
            if "openings_options_shown" not in self.collected_config:
                self.collected_config["openings_options_shown"] = True
                return await self.async_step_openings_options()

        # Show preset configuration - for AC-only systems only if enabled, for others always
        if original_system_type == SYSTEM_TYPE_AC_ONLY:
            if (
                self.collected_config.get("configure_presets", True)
                and "presets_shown" not in self.collected_config
            ):
                self.collected_config["presets_shown"] = True
                return await self.async_step_preset_selection()
        else:
            if "presets_shown" not in self.collected_config:
                self.collected_config["presets_shown"] = True
                return await self.async_step_preset_selection()

        # Final step - update the config entry
        return self.async_create_entry(
            title="",  # Empty title for options flow
            data=self.collected_config,
        )

    async def async_step_dual_stage_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle dual stage options."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_entry().data
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
        """Handle floor heating options."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()

        current_config = self._get_entry().data
        schema_dict: dict[Any, Any] = {}

        # Always show floor sensor option
        schema_dict[
            vol.Optional(
                CONF_FLOOR_SENSOR, default=current_config.get(CONF_FLOOR_SENSOR)
            )
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))

        # Always show floor temperature fields with defaults
        schema_dict[
            vol.Optional(
                CONF_MAX_FLOOR_TEMP,
                default=current_config.get(CONF_MAX_FLOOR_TEMP, 28),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        schema_dict[
            vol.Optional(
                CONF_MIN_FLOOR_TEMP,
                default=current_config.get(CONF_MIN_FLOOR_TEMP, 5),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX, unit_of_measurement=DEGREE
            )
        )

        return self.async_show_form(
            step_id="floor_options",
            data_schema=vol.Schema(schema_dict),
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

    async def async_step_ac_only_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle AC-only system features configuration in options flow."""
        if user_input is not None:
            # Check if user wants to show advanced options
            show_advanced = user_input.get("configure_advanced", False)

            # Always update the collected config with user input
            self.collected_config.update(user_input)

            # If user toggled advanced options, redirect to the dedicated advanced options step
            if show_advanced:
                return await self.async_step_advanced_options()

            # Otherwise, clear the advanced toggle flags and continue to next step
            self.collected_config.pop("configure_advanced", None)
            self.collected_config.pop("advanced_shown", None)
            return await self._determine_options_next_step()

        # For initial display in options flow, always start with basic form
        # Reset any advanced state to ensure clean start
        self.collected_config.pop("configure_advanced", None)
        self.collected_config.pop("advanced_shown", None)

        return self.async_show_form(
            step_id="ac_only_features",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "configure_fan", default=False
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        "configure_openings", default=False
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        "configure_humidity", default=False
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        "configure_presets", default=False
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        "configure_advanced", default=False
                    ): selector.BooleanSelector(),
                }
            ),
            description_placeholders={
                "subtitle": "Choose which features to configure for your AC system"
            },
        )

    async def async_step_fan_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle fan options."""
        return await self.fan_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            self._get_entry().data,
        )

    async def async_step_humidity_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle humidity options."""
        return await self.humidity_steps.async_step_options(
            self,
            user_input,
            self.collected_config,
            self._determine_options_next_step,
            self._get_entry().data,
        )

    async def async_step_advanced_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced options configuration."""
        if user_input is not None:
            self.collected_config.update(user_input)
            return await self._determine_options_next_step()
        current_config = self._get_entry().data
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
            self._get_entry().data,
        )

    async def async_step_preset_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle preset selection step in options flow."""
        return await self.presets_steps.async_step_selection(
            self, user_input, self.collected_config, self._determine_options_next_step
        )

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
