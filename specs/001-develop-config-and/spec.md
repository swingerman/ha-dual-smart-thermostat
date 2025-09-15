# Feature Specification: Develop config and options flow for dual_smart_thermostat

**Feature Branch**: `001-develop-config-and`
**Created**: 2025-09-15
**Status**: Draft
**Input**: User description: "Develop config and options flow for dual_smart_thermostat integration. Flows must cover all current configuration options. Config and options flows should be the same except options flow omits the name input. Include three main steps: system type selection, core settings for chosen system type, features configuration (list of features). Features depend on system type. After main steps, include per-feature configuration steps in order; presets must be last (after openings). System types: Simple heater, AC only, Heater with cooler, Heat pump. Features: Fan configuration, Humidity options, Openings options, Floor heating options, Presets options. When reconfiguring, preselect already configured features and prefill saved data."
 ## ⚡ Quick Guidelines

 ## User Scenarios & Testing *(mandatory)*

 ### Primary User Story
 As a Home Assistant user who has installed the `dual_smart_thermostat` integration, I want to create and later reconfigure thermostat instances using the Home Assistant UI so that I can model my home's HVAC setup (simple heater, AC-only, heater+cooler, or heat pump) and enable additional features (fan control, humidity automation, openings handling, floor heating, presets) with sensible defaults and clear per-feature settings. The configuration flow should guide me step-by-step; the options flow should mirror the config flow but omit editable name input and prefill previously saved values.
### Acceptance Scenarios

1. Happy path — initial config
	- Given: No existing `dual_smart_thermostat` entries.
	- When: User starts the integration config flow in the Home Assistant UI and proceeds through the steps using valid inputs.
	- Then: The flow presents (a) Step 1: system type selection, (b) Step 2: core settings for the chosen system type, (c) Step 3: feature selection. After feature selection the flow shows per-feature configuration steps in the required order (features chosen only; `openings` must appear before `presets`, and `presets` must be last). On finish, a config entry is created with the selected values persisted.

2. Options flow mirrors config flow and pre-fills values
	- Given: An existing config entry with a saved `name`, `system_type`, `features`, and `feature_settings`.
	- When: The user opens the integration's Options (reconfigure) from Home Assistant.
	- Then: The options flow omits the `name` input, presents the remaining steps in the same order as the config flow, preselects previously enabled features, and pre-fills every input with the saved values. Submitting the flow updates the existing entry rather than creating a new one.

3. System-type-specific feature visibility
	- Given: The user chooses a specific `system_type` (e.g., `ac_only` or `heat_pump`).
	- When: The user reaches the feature-selection step.
	- Then: The features list shows only features applicable to the chosen system type (features that are not applicable are either hidden or disabled with explanatory text). Selecting only applicable features leads to per-feature steps only for those features.

4. Feature ordering guidance (non-blocking)
	- Given: Some features have a recommended configuration order or logical prerequisites (for example, `presets` are configured after `openings` because presets may reference openings).
	- When: The user enables features out-of-order or enables a feature that logically expects another feature to be configured first.
	- Then: The flow DOES NOT block the user from enabling features; instead it provides clear, non-blocking guidance (informational text or a warning) and may offer to auto-enable or re-order subsequent configuration steps to follow recommended order. The implementation must validate configuration consistency at submission time and show actionable validation errors if a final configuration is inconsistent (for example, a preset referring to an opening that was never configured).

5. Feature configuration ordering enforced
	- Given: The user enabled `openings` and `presets` features.
	- When: The flow displays per-feature configuration steps.
	- Then: The `openings` configuration step appears before the `presets` configuration step and `presets` is the final feature step. This order must be preserved in both config and options flows.

6. Entity selector permissiveness and empty selectors
	- Given: The Home Assistant instance has entities that could be used for selectors (sensors, binary_sensors, switches).
	- When: The flow shows an entity selector (e.g., humidity sensor selector).
	- Then: The selector uses domain-only or otherwise permissive filters so valid entities are selectable. If no matching entities exist, the flow still allows the user to continue by leaving the selector blank (if optional) or shows a clear error/help text (if required). The behavior must match between config and options flows.

7. Defaults for feature options
	- Given: The user opens a per-feature configuration step and does not change optional numeric options (e.g., humidity target, min, max, tolerances).
	- When: The user submits the step.
	- Then: Sensible defaults are applied and persisted. Defaults used in the config flow must match those used in the options flow.

8. Cancel and partial flows do not persist
	- Given: The user starts the config or options flow and fills some steps.
	- When: The user cancels before finishing.
	- Then: No partial configuration is persisted; the existing config entry (if any) remains unchanged. The flow may store temporary state only for the duration of the flow and must discard it on cancel.

9. Validation and error handling
	- Given: The user supplies invalid or out-of-range values (for example, humidity min >= max, numeric fields outside allowed ranges, required selectors empty when they are mandatory).
	- When: The user attempts to submit the step or finish the flow.
	- Then: The flow blocks submission, highlights the invalid fields, and shows clear, actionable error messages. The flow prevents creating/updating the config entry until validation passes.

10. Removing a feature on reconfigure
	- Given: A previously enabled feature with persisted settings exists and the user reconfigures the integration.
	- When: The user disables that feature in the options flow and completes the flow.
	- Then: The integration persists the updated features list. The flow should make explicit what happens to data associated with the disabled feature (suggestions: remove associated settings, archive them under a clearly labeled property, or keep them but ignore until re-enabled). The chosen behavior must be documented in the integration's options UI text.

11. Idempotent submissions
	- Given: The user resubmits the same settings multiple times (e.g., clicks finish twice or re-enters the same values)
	- When: The flow processes the submission.
	- Then: Re-submitting does not create duplicate entries; it either completes with no-op or updates the existing entry to the same values; no data corruption occurs.

 ### Edge Cases
 - What happens when [boundary condition]?
 - How does system handle [error scenario]?

- If the user chooses a system type but then deselects a recommended prerequisite feature in a later step that other features logically expect (for example, removing `openings` while `presets` are enabled), the flow should WARN the user and explain consequences. It should offer to remove or archive dependent settings, or offer to re-enable the prerequisite. The flow must not silently lose user data without consent, and it must not aggressively block the user's choice.
- If entity selectors (sensors, switches) are empty because Home Assistant has no matching entities, the flow should allow the user to continue and leave the field blank or provide recommended default behavior; specifically, selectors should use domain-only filters to avoid over-restrictive filtering that hides valid entities.
 ### Functional Requirements
 - **FR-001**: System MUST guide the user through a three-step primary flow during initial setup:
	 - Step 1: System type selection (Simple heater, AC only, Heater with cooler, Heat Pump)
	 - Step 2: Core settings for the chosen system type
	 - Step 3: Features selection (Fan, Humidity, Openings, Floor heating, Presets)
 - **FR-002**: System MUST show per-feature configuration steps after the main three steps, ordered so that `openings` appears before `presets`, and `presets` is the final feature configuration step.
 - **FR-003**: System MUST ensure options flow mirrors the config flow except it omits the `name` input and pre-populates fields with saved configuration when present.
 - **FR-004**: For reconfiguration, already configured features MUST be preselected and their configuration steps prefilled with saved values.
 - **FR-005**: Feature-specific configuration steps MUST be displayed only when the feature is enabled in the features selection step.
 - **FR-006**: Entity selectors used in any step (e.g., humidity sensor selector) MUST use domain-only selectors or sufficiently permissive filters so valid entities are not hidden from the user.
 - **FR-007**: The flow MUST validate configuration consistency and respect recommended ordering between features. Ordering should be used to present configuration steps (for example, `openings` before `presets`). The flow MUST NOT block users from enabling features out-of-order; instead it MUST provide clear guidance and non-blocking warnings and must perform final validation at submit time (for example, if a preset references an opening entity that hasn't been configured, the flow should flag that as a validation error on submit and prevent final persistence until resolved).
 - **FR-008**: The flow MUST persist the final configuration in Home Assistant's config entries format and be reloadable by the integration.
 - **FR-009**: The flow MUST include sensible defaults for feature options where appropriate (e.g., humidity target, min/max, tolerances) and these defaults MUST match between config and options flows.
 - **FR-010**: The flow MUST provide clear error messages and prevent submission when required fields are missing or invalid.
 ### Key Entities *(include if feature involves data)*
 - **ThermostatConfigEntry**: Represents a configured instance of `dual_smart_thermostat`. Key attributes:
	 - `entry_id` (string)
	 - `name` (string)
	 - `system_type` (enum: simple_heater, ac_only, heater_cooler, heat_pump)
	 - `core_settings` (object: fields vary by `system_type`)
	 - `features` (list of enabled features)
	 - `feature_settings` (map from feature -> settings object)
 ## Review & Acceptance Checklist

 ## Execution Status
 - [x] User description parsed
 - [x] Key concepts extracted
 - [x] Ambiguities marked
 - [x] User scenarios defined
 - [x] Requirements generated
 - [x] Entities identified
 - [ ] Review checklist passed

## Implementation cross-reference
This spec maps directly to the code in the repository. When implementing or reviewing, reference these file locations:

- Config flow main handler: `custom_components/dual_smart_thermostat/config_flow.py::ConfigFlowHandler`
- Options flow main handler: `custom_components/dual_smart_thermostat/options_flow.py::OptionsFlowHandler`
- Centralized schema factories: `custom_components/dual_smart_thermostat/schemas.py` (see `get_core_schema`, `get_features_schema`, and per-feature schema functions)
- Feature step handlers: `custom_components/dual_smart_thermostat/feature_steps/` (e.g., `humidity.py`, `fan.py`, `openings.py`, `presets.py`)

Use these references to find the code paths that implement the user stories and acceptance criteria in this spec.
