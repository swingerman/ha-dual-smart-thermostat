# Feature Specification: Separate Temperature Tolerances for Heating and Cooling Modes

**Feature Branch**: `002-separate-tolerances`
**Created**: 2025-10-29
**Status**: Draft
**Input**: User description: "Create a formal specification for implementing separate temperature tolerances for heating and cooling modes in the Home Assistant Dual Smart Thermostat integration (GitHub Issue #407)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Different Tolerances for Heating vs Cooling (Priority: P1)

A homeowner wants tight temperature control during winter heating (±0.3°C for comfort) but loose control during summer cooling (±2.0°C for energy savings). They configure heat_tolerance to 0.3°C and cool_tolerance to 2.0°C. When heating mode is active, the thermostat maintains temperature within ±0.3°C of target. When cooling mode is active, it maintains temperature within ±2.0°C of target.

**Why this priority**: This is the core feature request and delivers immediate value to users who need asymmetric temperature control. It directly addresses the primary use case from Issue #407.

**Independent Test**: Can be fully tested by configuring heat_tolerance and cool_tolerance values, switching between heating and cooling modes, and verifying the thermostat activates/deactivates at the correct temperature thresholds. Delivers independent value even without other features.

**Acceptance Scenarios**:

1. **Given** a thermostat with heat_tolerance=0.3 and cool_tolerance=2.0 configured, **When** in HEAT mode with target temperature 20°C, **Then** heating activates at 19.7°C and deactivates at 20.3°C
2. **Given** a thermostat with heat_tolerance=0.3 and cool_tolerance=2.0 configured, **When** in COOL mode with target temperature 22°C, **Then** cooling activates at 24.0°C and deactivates at 20.0°C
3. **Given** a thermostat with only heat_tolerance=0.5 configured (no cool_tolerance), **When** in COOL mode, **Then** system falls back to legacy cold_tolerance and hot_tolerance values
4. **Given** a thermostat switching from HEAT to COOL mode, **When** mode changes, **Then** tolerance values update immediately without restart

---

### User Story 2 - Maintain Backward Compatibility with Legacy Configurations (Priority: P1)

A user with an existing thermostat configuration using cold_tolerance=0.5 and hot_tolerance=0.5 upgrades to the new version. The thermostat continues to operate exactly as before without any configuration changes. The user sees no difference in behavior unless they explicitly configure the new mode-specific tolerance parameters.

**Why this priority**: Critical for preventing breaking changes to existing deployments. Ensures zero disruption for current users and builds trust for the upgrade path.

**Independent Test**: Can be fully tested by loading an existing configuration with only cold_tolerance and hot_tolerance, verifying operation in all HVAC modes, and confirming behavior is identical to previous version. Delivers value by ensuring upgrade safety.

**Acceptance Scenarios**:

1. **Given** an existing configuration with only cold_tolerance=0.5 and hot_tolerance=0.5, **When** system starts, **Then** heating and cooling modes both use ±0.5°C tolerance ranges
2. **Given** a legacy configuration without mode-specific tolerances, **When** user views configuration UI, **Then** no new fields are required to be filled
3. **Given** a legacy configuration, **When** system operates in any HVAC mode, **Then** behavior is identical to previous software version
4. **Given** a user upgrades from old version to new version, **When** configuration is loaded, **Then** no migration or conversion is needed

---

### User Story 3 - Configure Tolerances Through UI (Priority: P2)

A user accesses the thermostat's options flow in Home Assistant UI and navigates to the Advanced Settings step. They see input fields for heat_tolerance and cool_tolerance alongside existing advanced settings. Each field shows the current value with helpful descriptions explaining what each tolerance controls and that they override legacy tolerances when specified.

**Why this priority**: Essential for usability but can be delivered after core logic is working. Users need UI access to configure the feature, but internal validation and testing can proceed without complete UI.

**Independent Test**: Can be fully tested by navigating through options flow to advanced settings, entering tolerance values, saving configuration, and verifying values persist and are applied to runtime behavior. Delivers value by making the feature accessible to end users.

**Acceptance Scenarios**:

1. **Given** a user opens the options flow, **When** they reach the advanced settings step, **Then** they see input fields for heat_tolerance and cool_tolerance with current values pre-filled or defaults shown
2. **Given** a user enters heat_tolerance=0.3, **When** they submit the form, **Then** value is validated (0.1-5.0 range) and saved to configuration
3. **Given** a user enters an invalid tolerance value (e.g., 0.05 or 10.0), **When** they submit the form, **Then** system shows validation error message with clear guidance
4. **Given** a user has configured mode-specific tolerances, **When** they view advanced settings later, **Then** their custom values are displayed correctly

---

### User Story 4 - Override Individual Modes While Keeping Legacy Fallbacks (Priority: P3)

A user wants to override only the cooling tolerance while keeping legacy behavior for heating. They configure cold_tolerance=0.5, hot_tolerance=0.5 (legacy), and cool_tolerance=1.5 (override). When in heating mode, the system uses the legacy ±0.5°C tolerance. When in cooling mode, it uses ±1.5°C tolerance.

**Why this priority**: Provides flexibility for advanced users but is not commonly needed. Most users will configure either all mode-specific tolerances or none. This is a nice-to-have for partial migration scenarios.

**Independent Test**: Can be fully tested by configuring legacy tolerances plus one mode-specific override, testing both modes, and verifying each uses the correct tolerance source. Delivers value for users who want incremental adoption of the new feature.

**Acceptance Scenarios**:

1. **Given** cold_tolerance=0.5, hot_tolerance=0.5, and cool_tolerance=1.5 configured, **When** in HEAT mode, **Then** system uses legacy tolerances (±0.5°C)
2. **Given** cold_tolerance=0.5, hot_tolerance=0.5, and cool_tolerance=1.5 configured, **When** in COOL mode, **Then** system uses cool_tolerance (±1.5°C)
3. **Given** only heat_tolerance=0.3 configured without cool_tolerance, **When** in COOL mode, **Then** system falls back to legacy cold_tolerance and hot_tolerance
4. **Given** a mix of legacy and mode-specific tolerances, **When** system selects tolerance, **Then** mode-specific always takes precedence over legacy

---

### Edge Cases

- What happens when current temperature sensor fails or becomes unavailable while using mode-specific tolerances?
  - System should gracefully handle sensor failures as it does currently, not attempting temperature comparisons until sensor recovers

- How does the system handle mode-specific tolerances when floor temperature limits are active?
  - Floor temperature limits should continue to operate independently, overriding tolerance-based decisions when floor protection is needed

- What happens when window/door sensors trigger while using different tolerances for heating vs cooling?
  - Window/door sensor overrides should work identically regardless of which tolerance is active, pausing HVAC operation as expected

- How do preset modes interact with mode-specific tolerances?
  - Presets can override target temperatures, but they should respect the mode-specific tolerance settings for the current HVAC mode

- What happens in HEAT_COOL mode when switching between active heating and active cooling operations?
  - System switches between heat_tolerance (when heating) and cool_tolerance (when cooling) based on current operation, providing per-operation control even in auto mode

- How does fan_hot_tolerance interact with the new heat_tolerance parameter?
  - Fan mode should follow the existing pattern: if fan operates like cooling, it uses cool_tolerance when available, otherwise legacy behavior

- What happens when a user sets extremely different values (e.g., heat_tolerance=0.1, cool_tolerance=5.0)?
  - System should allow any valid values (0.1-5.0) without enforcing relationships, giving users full control while validating reasonable bounds

- How does keep-alive mode interact with mode-specific tolerances?
  - Keep-alive cycles should respect the active tolerance for the current HVAC mode, ensuring proper temperature maintenance

- What happens when user configures heat_tolerance but the system never enters heating mode?
  - Unused tolerance parameters are simply stored in configuration and have no effect; no warnings or errors needed

- How does the system handle the transition period when HVAC mode changes?
  - Tolerance values update immediately when HVAC mode changes, using the new mode's tolerance for next activation/deactivation decision

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support two new optional configuration parameters: heat_tolerance (heating mode tolerance) and cool_tolerance (cooling mode tolerance)

- **FR-002**: System MUST continue to support existing cold_tolerance and hot_tolerance parameters as legacy fallback values

- **FR-003**: System MUST select tolerance values using priority hierarchy:
  - For HEAT mode: (1) heat_tolerance if specified, (2) cold_tolerance + hot_tolerance (legacy), (3) DEFAULT_TOLERANCE (0.3°C)
  - For COOL mode: (1) cool_tolerance if specified, (2) hot_tolerance + cold_tolerance (legacy), (3) DEFAULT_TOLERANCE (0.3°C)
  - For HEAT_COOL mode: (1) heat_tolerance when heating or cool_tolerance when cooling (based on active operation), (2) cold_tolerance + hot_tolerance (legacy), (3) DEFAULT_TOLERANCE (0.3°C)

- **FR-004**: System MUST track current HVAC mode to determine which tolerance value to apply

- **FR-005**: System MUST validate tolerance values are floats within range 0.1°C to 5.0°C (inclusive)

- **FR-006**: System MUST allow mode-specific tolerances to remain unset (null/None), using fallback behavior when not specified

- **FR-007**: System MUST NOT require migration or conversion of existing configurations; all existing configurations must work unchanged

- **FR-008**: System MUST update active tolerance immediately when HVAC mode changes, without requiring restart

- **FR-009**: System MUST persist mode-specific tolerance configuration across restarts and reload cycles

- **FR-010**: System MUST expose tolerance settings in the Home Assistant options flow UI with proper validation and error messages

- **FR-011**: System MUST support configuration of tolerances through YAML configuration (for existing YAML users) and through UI configuration flows (for new users)

- **FR-012**: System MUST provide clear UI descriptions explaining that mode-specific tolerances override legacy tolerances when specified

- **FR-013**: For HEAT mode operation, system MUST activate heating when current_temp <= target_temp - active_tolerance

- **FR-014**: For HEAT mode operation, system MUST deactivate heating when current_temp >= target_temp + active_tolerance

- **FR-015**: For COOL mode operation, system MUST activate cooling when current_temp >= target_temp + active_tolerance

- **FR-016**: For COOL mode operation, system MUST deactivate cooling when current_temp <= target_temp - active_tolerance

- **FR-017**: System MUST respect existing safety features (min_cycle_duration, floor temperature limits, opening detection) regardless of which tolerance is active

- **FR-018**: System MUST work correctly with all system types: simple_heater, ac_only, heat_pump, heater_cooler, dual_stage

- **FR-019**: System MUST work correctly with all HVAC modes: HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF

- **FR-020**: FAN_ONLY mode MUST use cool_tolerance when specified, otherwise fall back to legacy hot_tolerance behavior

- **FR-021**: System MUST handle sensor failures gracefully, not attempting tolerance comparisons when current temperature is unavailable

- **FR-022**: System MUST update configuration dependency tracking in tools/focused_config_dependencies.json

- **FR-023**: System MUST provide English translations in custom_components/dual_smart_thermostat/translations/en.json with clear descriptions

- **FR-024**: System MUST pass configuration validation via python tools/config_validator.py

- **FR-025**: System MUST allow any valid tolerance values without enforcing relationships between heat_tolerance and cool_tolerance

### Key Entities *(include if feature involves data)*

- **Configuration Entry**: Stores tolerance settings along with other thermostat configuration
  - Legacy attributes: cold_tolerance (float, defaults to 0.3), hot_tolerance (float, defaults to 0.3)
  - New optional attributes: heat_tolerance (float, optional, 0.1-5.0), cool_tolerance (float, optional, 0.1-5.0)
  - Persistence: Stored in Home Assistant's config entries, persists across restarts

- **Environment Manager**: Determines if temperature is too cold or too hot based on current HVAC mode
  - Current state: Tracks current HVAC mode (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF)
  - Methods: is_too_cold() and is_too_hot() - must consider current mode when selecting tolerance
  - Relationships: Receives configuration from climate entity, provides temperature comparisons to HVAC devices

- **HVAC Mode State**: Represents the current operational mode of the thermostat
  - Values: HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF
  - Usage: Determines which tolerance parameter to apply for temperature comparisons
  - Transitions: Updates when user changes mode or when AUTO mode switches between heating/cooling

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure heat_tolerance=0.3 and cool_tolerance=2.0, and the system maintains temperature within ±0.3°C in heating mode and ±2.0°C in cooling mode

- **SC-002**: 100% of existing thermostat configurations continue to work without modification after upgrade

- **SC-003**: System correctly applies tolerance for all HVAC modes (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY) within 1 control cycle of mode change

- **SC-004**: Users can complete tolerance configuration through UI in under 2 minutes with clear validation feedback

- **SC-005**: All existing safety features (min cycle duration, floor protection, opening detection) continue to work identically with new tolerance system

- **SC-006**: Configuration persists correctly through restart cycles - 100% of configured tolerance values restore accurately

- **SC-007**: System works correctly with all four system types (simple_heater, ac_only, heat_pump, heater_cooler) and two-stage heating

- **SC-008**: Tolerance validation prevents invalid values (< 0.1°C or > 5.0°C) with clear error messages

- **SC-009**: Users can override only cooling tolerance while keeping legacy heating behavior, or vice versa

- **SC-010**: System documentation and UI descriptions clearly explain tolerance priority and override behavior

## Constraints

### Technical Constraints

- Must maintain compatibility with Home Assistant 2025.1.0 and later versions
- Must work with Python 3.13 runtime environment
- Must integrate with existing climate entity patterns and Home Assistant configuration flow APIs
- Must respect existing min_cycle_duration timing to prevent equipment damage
- Must work within Home Assistant's async execution model
- Must handle entity availability and sensor failure scenarios gracefully
- Cannot modify Home Assistant core or climate platform base classes

### Backward Compatibility Constraints

- Zero breaking changes to existing configurations allowed
- All existing YAML configurations must work unchanged
- No migration scripts required - automatic fallback behavior must handle all cases
- Default behavior without new parameters must match current implementation exactly
- Cannot change behavior of cold_tolerance and hot_tolerance when used alone

### User Experience Constraints

- Configuration UI must be intuitive for non-technical users
- Validation errors must provide clear, actionable guidance
- Documentation must explain tolerance priority hierarchy clearly
- Changes should be discoverable but not force users to reconfigure existing systems

### Safety Constraints

- Must not allow configurations that could damage HVAC equipment (min cycle duration still enforced)
- Must not allow tolerance values that could cause excessive cycling (minimum 0.1°C enforced)
- Must not allow values that could cause runaway behavior (maximum 5.0°C enforced)
- Must handle sensor failures without attempting invalid comparisons

## Assumptions

- Users understand the difference between heating and cooling modes and want different control behavior
- Default tolerance values of 0.3°C for both cold_tolerance and hot_tolerance provide sensible working defaults for new installations
- The tolerance values represent the full range (so ±tolerance from target, not tolerance on each side)
- Users prefer explicit opt-in for new mode-specific features rather than automatic conversion of existing configurations
- Most users will configure all mode-specific tolerances together, but partial configuration should be supported
- English translations are sufficient for initial release; localization framework supports future translations
- Configuration validation at entry time is preferred over runtime errors
- In HEAT_COOL (auto) mode, using heat_tolerance when heating and cool_tolerance when cooling provides appropriate flexibility
- FAN_ONLY mode behavior is similar to cooling operation, so cool_tolerance is the logical default
- Floor temperature protection and opening detection should override tolerance-based decisions (existing behavior maintained)
- Placing tolerance settings in the Advanced Settings step is appropriate since they are optional configuration parameters

## Dependencies

### Internal Dependencies

- Requires modification to const.py (configuration constants)
- Requires modification to environment_manager.py (tolerance selection logic)
- Requires modification to climate.py (HVAC mode tracking)
- Requires modification to options_flow.py (UI configuration step)
- Requires modification to translations/en.json (UI strings)
- Depends on existing schemas.py patterns for configuration validation
- Depends on existing state_manager.py for persistence support

### External Dependencies

- Home Assistant core platform (climate component)
- Home Assistant config flow framework
- voluptuous library for schema validation (already used)
- Home Assistant's entity lifecycle and state restoration mechanisms

### Configuration Dependencies

- heat_tolerance and cool_tolerance are independent optional parameters
- When mode-specific tolerance is not set, falls back to cold_tolerance and hot_tolerance (which default to 0.3°C)
- cold_tolerance and hot_tolerance now default to 0.3°C for new installations (Decision 3)
- No enforced relationships between heat_tolerance and cool_tolerance values
- Configuration tools/focused_config_dependencies.json must document these relationships
- Configuration validation script must verify parameter combinations are valid

## Out of Scope

The following items are explicitly excluded from this feature:

- **heat_cool_tolerance parameter**: Not implemented in this version (Decision 1); HEAT_COOL mode uses heat_tolerance/cool_tolerance based on active operation
- **Dedicated tolerance settings UI step**: Tolerance settings integrated into existing Advanced Settings step (Decision 2)
- Different tolerance values per preset mode (presets can override target temp, but not tolerance)
- Automatic migration or conversion of cold_tolerance/hot_tolerance to mode-specific equivalents
- Warning users about "suboptimal" tolerance configurations (e.g., heat_tolerance > cool_tolerance)
- Time-based or schedule-based tolerance adjustment (use presets or automations for this)
- Sensor-based dynamic tolerance adjustment (requires separate feature)
- Separate tolerances for fan_on_diff or fan_off_diff (uses existing fan_hot_tolerance pattern)
- UI indicators showing which tolerance is currently active (may be added in future)
- Historical tolerance usage tracking or reporting
- Different tolerance values for auxiliary heater vs primary heater in dual-stage systems
- Tolerance configuration at device level vs climate entity level (entity level only)
- Export/import of tolerance presets or templates
- Tolerance learning or recommendation based on usage patterns

## Design Decisions (Resolved)

### Decision 1: HEAT_COOL Mode Behavior
**Decision**: Option B - Only support falling back to heat_tolerance/cool_tolerance based on active operation

**Rationale**: In HEAT_COOL (auto) mode, the system will use heat_tolerance when actively heating and cool_tolerance when actively cooling. This provides users with flexible per-operation control even in auto mode. The heat_cool_tolerance parameter will NOT be implemented in this version.

**Implementation Impact**:
- No heat_cool_tolerance configuration parameter needed
- Environment manager uses heat_tolerance or cool_tolerance based on current HVAC action (heating vs cooling)
- Simpler implementation with clear behavior

### Decision 2: UI Placement
**Decision**: Option A - Added to existing advanced settings step in options flow

**Rationale**: Tolerance settings will be added to the existing "Advanced Settings" step in the options flow. This keeps related configuration together and avoids adding another navigation step for users.

**Implementation Impact**:
- Modify existing advanced settings step handler
- Add heat_tolerance and cool_tolerance fields to advanced settings form
- No new flow step or navigation logic needed

### Decision 3: New Installation Defaults
**Decision**: Option B - Default both cold_tolerance and hot_tolerance to 0.3°C automatically, with defaults also used in config flows

**Rationale**: Simplifies setup for new users by providing sensible working defaults out of the box. Users can still customize if needed, but get functional behavior immediately.

**Implementation Impact**:
- Default cold_tolerance = 0.3°C
- Default hot_tolerance = 0.3°C
- Apply these defaults in both initial config flow and options flow
- Users can override defaults at any time
- Backward compatibility maintained: existing configs keep their configured values

## Risks and Mitigations

### Risk: Breaking Existing Configurations

**Impact**: High - Users' thermostats could malfunction
**Likelihood**: Low
**Mitigation**: Comprehensive backward compatibility testing with existing configurations, E2E persistence tests, maintain exact legacy behavior as fallback

### Risk: Confusing User Experience

**Impact**: Medium - Users may not understand tolerance priority hierarchy
**Likelihood**: Medium
**Mitigation**: Clear UI descriptions, documentation with examples, validation that guides users toward correct configuration

### Risk: Configuration Complexity

**Impact**: Medium - Too many tolerance parameters may overwhelm users
**Likelihood**: Medium
**Mitigation**: Make all new parameters optional, pre-fill current values in UI, provide sensible fallback behavior

### Risk: Mode-Switching Edge Cases

**Impact**: Medium - Unexpected behavior when switching between HVAC modes
**Likelihood**: Low
**Mitigation**: Immediate tolerance update on mode change, comprehensive integration tests covering all mode transitions

### Risk: Performance Impact

**Impact**: Low - Additional logic might slow control loops
**Likelihood**: Very Low
**Mitigation**: Tolerance selection is simple lookup, minimal computational overhead, existing async patterns maintained

### Risk: Testing Coverage Gaps

**Impact**: High - Untested edge cases could cause runtime failures
**Likelihood**: Medium
**Mitigation**: Comprehensive test strategy covering unit, integration, E2E, and functional tests for all system types and modes

## Testing Strategy

### Unit Testing

**Focus**: Core tolerance selection logic in environment_manager.py

- Test get_active_tolerance_for_mode() with all HVAC modes (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF)
- Test backward compatibility: only cold_tolerance and hot_tolerance configured
- Test tolerance override: mode-specific tolerance overrides legacy
- Test selection priority: verify correct fallback chain for each mode
- Test partial configuration: only heat_tolerance set, only cool_tolerance set
- Test validation: values within 0.1-5.0 range, float type handling
- Test null/None handling: missing tolerance parameters
- Test mode switching: tolerance updates when HVAC mode changes

**Test Files**: Add to tests/managers/test_environment_manager.py or create tests/test_tolerance_selection.py

### Config Flow Testing

**Focus**: UI integration and persistence

- Test options flow includes tolerance settings step
- Test values persist from config to options flow
- Test validation works (0.1-5.0 range, float type)
- Test default values display correctly (existing cold/hot tolerance shown)
- Test form submission with valid and invalid values
- Test error messages are clear and actionable
- Test optional fields can be left empty
- Test pre-filling of current values

**Test Files**: Add to tests/config_flow/test_options_flow.py

### E2E Persistence Testing

**Focus**: End-to-end configuration persistence

- Add test cases to tests/config_flow/test_e2e_simple_heater_persistence.py
- Add test cases to tests/config_flow/test_e2e_ac_only_persistence.py
- Add test cases to tests/config_flow/test_e2e_heat_pump_persistence.py
- Add test cases to tests/config_flow/test_e2e_heater_cooler_persistence.py
- Test tolerance values persist through restarts
- Test config → options flow → runtime persistence
- Test all system types handle tolerances correctly
- Test mixed legacy and mode-specific tolerance configurations persist

### Integration Testing

**Focus**: Feature combinations and interactions

- Add to tests/config_flow/test_simple_heater_features_integration.py
- Add to tests/config_flow/test_ac_only_features_integration.py
- Add to tests/config_flow/test_heat_pump_features_integration.py
- Add to tests/config_flow/test_heater_cooler_features_integration.py
- Test tolerance settings with different system types
- Test interaction with fan_hot_tolerance
- Test interaction with presets (target temp changes, tolerance stays)
- Test interaction with opening detection (overrides tolerance)
- Test interaction with floor temperature limits (overrides tolerance)

### Functional Testing

**Focus**: Runtime behavior verification

- Test heating mode respects heat_tolerance
- Test cooling mode respects cool_tolerance
- Test heat/cool mode uses heat_tolerance when heating and cool_tolerance when cooling
- Test heat/cool mode falls back to legacy tolerances when mode-specific not set
- Test fan mode behavior with cool_tolerance
- Test all HVAC modes switch correctly
- Test legacy configuration behavior unchanged
- Test partial override configurations
- Test sensor failure handling
- Test mode transitions and tolerance updates

**Test Files**: Add to existing tests/test_heater_mode.py, tests/test_cooler_mode.py, tests/test_heat_pump_mode.py

### Validation Testing

**Focus**: Configuration validation and dependencies

- Run python tools/config_validator.py
- Verify tools/focused_config_dependencies.json updated correctly
- Test validation catches invalid values (< 0.1, > 5.0)
- Test validation accepts valid values (0.1-5.0)
- Test validation allows optional parameters to be unset

## Acceptance Criteria

The feature is complete and ready for release when:

1. All 25 functional requirements (FR-001 through FR-025) are implemented and verified
2. All 10 success criteria (SC-001 through SC-010) are measured and pass
3. All priority P1 user stories have passing acceptance scenarios
4. Backward compatibility testing confirms zero breaking changes to existing configurations
5. All code passes linting (isort, black, flake8, codespell)
6. Test suite passes with 100% of existing tests passing
7. New code has >95% test coverage
8. E2E persistence tests pass for all system types (simple_heater, ac_only, heat_pump, heater_cooler)
9. Configuration validator (python tools/config_validator.py) passes
10. Documentation updated: README.md, tools/focused_config_dependencies.json, docs/config/CRITICAL_CONFIG_DEPENDENCIES.md
11. Translations updated: custom_components/dual_smart_thermostat/translations/en.json
12. Manual testing confirms:
    - Tolerance configuration through UI works intuitively
    - Mode-specific tolerances apply correctly in runtime
    - Legacy configurations work unchanged
    - All HVAC modes respect appropriate tolerances
    - All safety features (min cycle, floor protection, opening detection) still work
13. All three open questions are resolved with explicit decisions documented
14. Code review completed with no blocking issues
15. Feature deployed to test environment and verified by at least one user from Issue #407
