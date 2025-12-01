# Feature Specification: Template-Based Preset Temperatures

**Feature Branch**: `004-template-based-presets`
**Created**: 2025-12-01
**Status**: Draft
**Input**: User description: "Add Home Assistant template support for preset temperatures (away_temp, eco_temp, etc.) allowing dynamic values based on sensors/conditions with reactive evaluation when template entities change, maintaining backward compatibility with static numeric values, supporting both single temperature and range modes (target_temp_low/high)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Static Preset Temperature (Backward Compatibility) (Priority: P1)

A homeowner has configured their thermostat with an "Away" preset set to 16°C using a static numeric value. When they activate the Away preset, the thermostat maintains 16°C until they change presets again.

**Why this priority**: Ensures existing configurations continue working without modification. This is the MVP baseline - if users can't use static values, the system is broken for existing users.

**Independent Test**: Can be fully tested by creating a new thermostat configuration with a numeric preset temperature value (e.g., away_temp: 18) and verifying it maintains that temperature when activated. Delivers value by preserving existing functionality.

**Acceptance Scenarios**:

1. **Given** a thermostat configured with away_temp: 16, **When** the user activates Away preset, **Then** the target temperature becomes 16°C
2. **Given** an existing thermostat with static preset temperatures, **When** the system is upgraded, **Then** all preset temperatures continue working without reconfiguration
3. **Given** a thermostat in Away mode with static temperature, **When** the user switches to another preset, **Then** the temperature changes to the new preset's static value

---

### User Story 2 - Simple Template with Entity Reference (Priority: P2)

A homeowner wants their "Away" preset temperature to be controlled by a helper entity (input_number.away_temperature). They configure away_temp to reference this entity using a template. When they adjust the helper value from 16°C to 18°C, the thermostat automatically updates to the new target without requiring any additional automation.

**Why this priority**: Enables the core dynamic behavior requested by users. This is the first step toward truly dynamic presets and can be independently valuable without complex logic.

**Independent Test**: Can be tested by creating a helper entity (e.g., input_number.away_temp set to 18), configuring a preset with a template referencing that entity, activating the preset, verifying the temperature matches the helper value, changing the helper value to 20, and confirming the thermostat updates automatically. Delivers value by allowing centralized temperature control.

**Acceptance Scenarios**:

1. **Given** away_temp configured as "{{ states('input_number.away_temperature') }}" with helper value 16, **When** Away preset is activated, **Then** target temperature becomes 16°C
2. **Given** Away preset is active with template referencing a helper, **When** the helper value changes from 16 to 18, **Then** the thermostat target temperature automatically updates to 18°C within 5 seconds
3. **Given** the referenced entity becomes unavailable, **When** the template is evaluated, **Then** the thermostat maintains the last known good temperature value

---

### User Story 3 - Seasonal Temperature Logic (Priority: P3)

A homeowner wants different "Away" temperatures for winter (16°C to save heating costs) and summer (26°C to save cooling costs). They configure away_temp with a template using conditional logic based on a season sensor. When the season changes from winter to summer, the Away preset temperature automatically switches from 16°C to 26°C without manual intervention.

**Why this priority**: Delivers the full dynamic preset capability requested in the original user request. While highly valuable, it builds on P2 and requires more complex template logic understanding.

**Independent Test**: Can be tested by creating a season sensor (or input_select with winter/summer options), configuring away_temp with conditional template logic (e.g., "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"), activating Away preset during winter state (verify 16°C), changing season to summer (verify automatic update to 26°C). Delivers value by eliminating need for season-aware automations.

**Acceptance Scenarios**:

1. **Given** away_temp configured with "{% if is_state('sensor.season', 'winter') %}16{% else %}26{% endif %}" and season is winter, **When** Away preset is activated, **Then** target temperature becomes 16°C
2. **Given** Away preset is active with seasonal template and current temperature is 16°C, **When** sensor.season changes from 'winter' to 'summer', **Then** target temperature automatically updates to 26°C
3. **Given** a template uses multiple conditions (season and time of day), **When** any referenced entity changes state, **Then** the template re-evaluates and updates the temperature accordingly

---

### User Story 4 - Temperature Range Mode with Templates (Priority: P3)

A homeowner using heat/cool mode (range mode) wants both the low and high temperature thresholds for their "Eco" preset to adjust based on outdoor temperature. They configure eco_temp_low and eco_temp_high with templates that reference sensor.outdoor_temp. When outdoor temperature changes, both thresholds automatically adjust to maintain energy efficiency.

**Why this priority**: Extends template support to range mode users. While important for dual-mode thermostat users, it's less critical than single temperature mode and can be independently developed.

**Independent Test**: Can be tested by configuring a thermostat in heat_cool mode, setting eco_temp_low to "{{ states('sensor.outdoor_temp') | float - 2 }}" and eco_temp_high to "{{ states('sensor.outdoor_temp') | float + 4 }}", simulating outdoor_temp at 20°C (verify range 18-24°C), changing outdoor_temp to 25°C (verify range updates to 23-29°C). Delivers value by enabling dynamic comfort zones based on external conditions.

**Acceptance Scenarios**:

1. **Given** a heat/cool thermostat with eco_temp_low and eco_temp_high configured as templates, **When** Eco preset is activated, **Then** both low and high targets are set based on template evaluation
2. **Given** Eco preset is active in range mode, **When** the outdoor temperature sensor changes, **Then** both target_temp_low and target_temp_high update automatically
3. **Given** range mode with one static value (temp_low: 18) and one template (temp_high), **When** preset is activated, **Then** static value remains constant while template evaluates dynamically

---

### User Story 5 - Configuration with Template Validation (Priority: P2)

A user is configuring a new thermostat and wants to use a template for the Away preset temperature. During configuration, they enter an invalid template with syntax errors. The system detects the error and displays a clear message explaining the syntax problem before allowing them to save.

**Why this priority**: Prevents configuration errors at setup time. Critical for user experience - catching errors early prevents frustration and support requests. Must be available when users first configure templates (P2 features).

**Independent Test**: Can be tested by starting the configuration flow, selecting a preset, entering an invalid template string (e.g., "{{ invalid syntax"), attempting to save, and verifying that a clear error message is displayed and configuration is not saved until corrected. Delivers value by preventing broken configurations.

**Acceptance Scenarios**:

1. **Given** a user is configuring a preset temperature, **When** they enter "{{ states('sensor.temp'", **Then** a validation error is displayed indicating unclosed template brackets
2. **Given** a user enters a valid template with proper syntax, **When** they save the configuration, **Then** the template is accepted and saved without errors
3. **Given** a user enters a plain numeric value, **When** they save the configuration, **Then** it is accepted as a static value without template validation

---

### User Story 6 - Preset Switching with Template Cleanup (Priority: P4)

A homeowner has configured multiple presets, each using different templates referencing different sensors (Away uses sensor.away_temp, Eco uses sensor.eco_temp). When they switch from Away to Eco preset, the system stops monitoring sensor.away_temp and begins monitoring sensor.eco_temp for changes.

**Why this priority**: Important for system health and resource management, but not directly visible to end users. Can be validated through testing without impacting core functionality. Lower priority because it's a behind-the-scenes quality concern.

**Independent Test**: Can be tested by configuring two presets with different template entities, activating the first preset, verifying the first sensor is monitored, switching to the second preset, verifying the first sensor is no longer monitored and the second sensor is now monitored. Delivers value by preventing resource leaks and ensuring system stability.

**Acceptance Scenarios**:

1. **Given** Away preset is active with template monitoring sensor.away_temp, **When** user switches to Eco preset using sensor.eco_temp, **Then** sensor.away_temp is no longer monitored
2. **Given** multiple presets configured with templates, **When** user switches between presets, **Then** only the current preset's template entities are monitored
3. **Given** a preset with templates is active, **When** user sets preset to "None", **Then** all template entity monitoring stops

---

### Edge Cases

- **What happens when a template references a non-existent entity?** The system should fail template evaluation gracefully, keep the last known good value, and log a warning for debugging.

- **What happens when a template evaluation takes too long?** Evaluation should complete within a reasonable timeout (e.g., 1 second), and if it exceeds this, the system should keep the previous value and log a performance warning.

- **How does the system handle rapid entity state changes?** If a template entity changes state multiple times in quick succession, each change should trigger re-evaluation, but the system should remain stable and update to the final value.

- **What happens when a user changes a template in the options flow?** The old template's entity listeners should be cleaned up immediately and replaced with listeners for entities in the new template.

- **How does the system handle templates that return non-numeric values?** If a template evaluates to a non-numeric result (e.g., "unknown", "unavailable"), the evaluation should fail gracefully and keep the previous numeric value.

- **What happens during thermostat startup if a template entity is not yet available?** The system should use a reasonable default (e.g., 20°C) until the entity becomes available and the template can be evaluated successfully.

- **How does the system handle complex templates with multiple entity references?** All referenced entities should be tracked, and a change to any of them should trigger template re-evaluation.

- **What happens when a user removes the thermostat entity?** All template listeners should be cleaned up to prevent memory leaks and resource consumption.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept numeric values for preset temperatures (e.g., 16, 20.5) to maintain backward compatibility
- **FR-002**: System MUST accept template strings for preset temperatures (e.g., "{{ states('sensor.temp') }}")
- **FR-003**: System MUST distinguish between static numeric values and template strings automatically without requiring explicit type declaration
- **FR-004**: System MUST support templates for single temperature mode (temperature field)
- **FR-005**: System MUST support templates for temperature range mode (target_temp_low and target_temp_high fields)
- **FR-006**: System MUST re-evaluate templates automatically when any referenced entity changes state
- **FR-007**: System MUST update the thermostat target temperature within 5 seconds when a template entity changes
- **FR-008**: System MUST validate template syntax (structure and grammar) during configuration before saving; entity existence is not validated at configuration time
- **FR-009**: System MUST display clear error messages when template syntax is invalid
- **FR-010**: System MUST handle template evaluation errors gracefully without crashing or becoming unresponsive
- **FR-011**: System MUST retain the last successfully evaluated temperature when template evaluation fails
- **FR-012**: System MUST log template evaluation failures including: template string, referenced entity IDs, error message, and previous value kept for fallback
- **FR-013**: System MUST stop monitoring template entities when a preset is deactivated
- **FR-014**: System MUST start monitoring new template entities when a preset is activated
- **FR-015**: System MUST clean up all template entity monitoring when the thermostat is removed
- **FR-016**: Users MUST be able to modify preset templates through the options flow
- **FR-017**: System MUST support all standard Home Assistant template syntax and functions
- **FR-018**: Users MUST receive inline help text with 2-3 common template pattern examples (static value, entity reference, conditional logic) displayed below each preset temperature input field in the configuration interface
- **FR-019**: System MUST use 20°C (68°F) as the default fallback temperature when template evaluation fails and no previous successful evaluation exists

### Key Entities *(include if feature involves data)*

- **Preset Configuration**: Represents temperature settings for a specific preset mode (Away, Eco, Comfort, etc.). Key attributes include preset name, temperature value (static or template), temperature low/high values (for range mode), and associated template entity references.

- **Template Entity Reference**: Tracks which Home Assistant entities (sensors, helpers, input_numbers) are referenced by templates in active presets. Used to determine which entities need state change monitoring.

- **Template Evaluation Result**: Stores the outcome of evaluating a template, including the calculated temperature value, evaluation success/failure status, timestamp, and any error details. Used to maintain last known good values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure preset temperatures using static numeric values and have them work identically to the current implementation (100% backward compatibility)
- **SC-002**: Users can configure preset temperatures using templates referencing Home Assistant entities and have the temperatures automatically update when those entities change
- **SC-003**: Template re-evaluation and temperature update occurs within 5 seconds of referenced entity state change
- **SC-004**: System remains stable and responsive when template evaluation fails (no crashes, no preset deactivation, maintains previous temperature)
- **SC-005**: Configuration validation catches at least 95% of common template syntax errors before saving
- **SC-006**: Users can successfully configure seasonal temperature logic using conditional templates in a single configuration step (without requiring external automations)
- **SC-007**: Memory usage does not increase when template monitoring is active (proper listener cleanup verified through testing)
- **SC-008**: Users can discover and understand how to use templates through in-configuration guidance (measured by reduced support requests or user feedback)

## Clarifications

### Session 2025-12-01

- Q: What format should the template guidance take in the configuration interface? → A: Inline help text with examples showing 2-3 common patterns below the input field
- Q: What information should be logged when a template evaluation fails? → A: Template string, entity IDs referenced, error message, previous value kept
- Q: Should configuration validation check if template-referenced entities exist at save time? → A: No - Validate syntax only; entity existence checked at runtime with fallback behavior

### Assumptions

1. **Template Syntax**: Assumes users have basic familiarity with Home Assistant template syntax or can learn from provided examples. The system will provide inline help and examples during configuration.

2. **Entity Availability**: Assumes that entities referenced in templates are generally available during normal operation. When entities are temporarily unavailable (e.g., during startup or network issues), the system falls back to the last known good value.

3. **Performance Expectations**: Assumes template evaluation completes within 1 second under normal conditions. Complex templates with many entity references may take longer but should remain under 2 seconds.

4. **Configuration Persistence**: Assumes templates are stored as strings in the configuration entry and survive Home Assistant restarts without modification.

5. **User Expertise**: Assumes that users configuring templates have sufficient permissions to view and reference other Home Assistant entities in their templates.

6. **Default Fallback**: When no previous value exists and template evaluation fails, the system assumes a safe default of 20°C (68°F) to prevent extreme heating/cooling.

7. **Entity Change Frequency**: Assumes template entities (sensors, helpers) change state at reasonable intervals (not multiple times per second). Rapid changes are handled but may cause frequent control cycle triggers.

8. **Range Mode Behavior**: Assumes that in range mode (heat/cool), users want both temp_low and temp_high to be independently configurable as either static or template values.
