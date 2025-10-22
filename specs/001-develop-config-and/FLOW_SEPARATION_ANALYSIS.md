# Flow Separation Analysis: Config vs Reconfigure vs Options

Based on [Home Assistant Documentation](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#reconfigure) and [Quality Scale Rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/reconfiguration-flow/)

## Summary of HA Best Practices

### Config Flow
- **Purpose**: Initial integration setup
- **Creates**: New config entry
- **Cannot be changed later**: Name (title)
- **Output**: `async_create_entry()`

### Reconfigure Flow
- **Purpose**: Change **essential, non-optional** configuration that affects core functionality
- **Examples from HA docs**:
  - Device IP address
  - Hostname
  - Port
  - Connection details
  - Core setup parameters
- **Key Point**: "Not optional and not related to authentication"
- **Output**: `async_update_reload_and_abort()` (reloads integration)

### Options Flow
- **Purpose**: Change **optional settings** and user preferences
- **Examples from HA docs**:
  - Update frequency
  - Feature toggles
  - Adjustable non-critical settings
- **Key Point**: "Optional settings that don't fundamentally change how integration connects"
- **Output**: Updates `entry.options` (no reload unless needed)

## Current State Analysis

### What We Have Now

Our current implementation has:
- **Config Flow**: Full wizard with system type, entities, features, openings, presets
- **Options Flow**: Almost identical to config flow (99% same except name field)
- **Reconfigure Flow**: Newly added, reuses config flow steps

### The Problem

1. Options flow does too much (allows changing system type, entities, features)
2. According to HA docs, these are **structural changes** that should be in reconfigure
3. Options should be for **optional, non-critical** settings only

## Proposed Separation for Dual Smart Thermostat

### Config Flow (Initial Setup)
**Steps**:
1. System type selection
2. System-specific config (entities)
3. Features selection
4. Feature-specific config
5. Openings
6. Presets

**What it configures**:
- ✅ Name (cannot be changed later)
- ✅ System type
- ✅ Required entities (heater, cooler, sensor)
- ✅ Optional entities (floor sensor, fan, humidity, etc.)
- ✅ Feature flags (which features are enabled)
- ✅ Structural configuration (openings list, preset list)

---

### Reconfigure Flow (Structural Changes)
**Steps**: Same as config flow (reuses all steps)

**What it allows changing** (essential, structural config):
- ✅ System type (e.g., simple_heater → heat_pump)
- ✅ Entity IDs (switch.heater → switch.new_heater)
- ✅ Which features are enabled/disabled
- ✅ Which sensors are configured (floor, humidity, etc.)
- ✅ Openings list (add/remove window sensors)
- ✅ Presets list (which presets are enabled)
- ❌ Name (preserved from original entry)

**Why these belong in reconfigure**:
- Changing system type requires different entities → structural change
- Changing entity IDs changes how integration connects → core setup parameter
- Enabling/disabling features changes what the integration can do → essential functionality
- These all require integration reload to take effect

---

### Options Flow (Runtime Tuning)
**Steps**: Single-step or minimal multi-step

**What it allows changing** (optional, non-critical settings):
- ✅ Temperature tolerances (cold_tolerance, hot_tolerance)
- ✅ Temperature limits (min_temp, max_temp, target temps)
- ✅ Precision and step values
- ✅ Timing settings (min_duration, keep_alive)
- ✅ Timeout values (opening timeouts, aux heater timeout)
- ✅ Floor temperature limits (min_floor_temp, max_floor_temp) - **IF floor heating already enabled**
- ✅ Preset temperature overrides (change away temp, eco temp) - **IF presets already configured**
- ✅ Fan tolerance settings - **IF fan already enabled**
- ✅ Humidity tolerance settings - **IF humidity already enabled**

**What it does NOT allow**:
- ❌ Changing system type
- ❌ Changing entity IDs
- ❌ Enabling/disabling features (use reconfigure)
- ❌ Adding/removing openings (use reconfigure)
- ❌ Enabling/disabling presets (use reconfigure)

**Why these belong in options**:
- Adjusting tolerances doesn't change what entities are used → optional tuning
- Temperature limits are user preferences → non-critical settings
- Timing values are optimizations → don't change core functionality
- Most can be updated without reload (live updates)

---

## Comparison Matrix

| Configuration Item | Config | Reconfigure | Options |
|-------------------|--------|-------------|---------|
| **Name** | ✅ Set | ❌ Preserved | ❌ No |
| **System Type** | ✅ Set | ✅ Change | ❌ No |
| **Entity IDs** | ✅ Set | ✅ Change | ❌ No |
| **Feature Toggles** | ✅ Set | ✅ Change | ❌ No |
| **Openings List** | ✅ Set | ✅ Change | ❌ No |
| **Presets List** | ✅ Set | ✅ Change | ❌ No |
| **Tolerances** | ✅ Set | ✅ Change | ✅ Adjust |
| **Temp Limits** | ✅ Set | ✅ Change | ✅ Adjust |
| **Timeouts** | ✅ Set | ✅ Change | ✅ Adjust |
| **Preset Temps** | ✅ Set | ✅ Change | ✅ Adjust |
| **Precision/Step** | ✅ Set | ✅ Change | ✅ Adjust |

---

## Implementation Plan

### Phase 1: Reconfigure Flow ✅ COMPLETE
- [x] Add `async_step_reconfigure()` entry point
- [x] Reuse all config flow steps
- [x] Use `async_update_reload_and_abort()` for completion
- [x] Preserve name from original entry
- [x] Clear flow control flags
- [x] Prepopulate forms with current values
- [x] Comprehensive tests

### Phase 2: Simplify Options Flow 🔄 PENDING
**Current State**: Options flow = 99% same as config flow

**Target State**: Simplified single-step or minimal flow

**Changes Needed**:
1. Remove system type selection
2. Remove entity selectors (heater, cooler, sensor, etc.)
3. Remove feature toggles (fan, humidity, floor heating, openings, presets)
4. Remove multi-step wizard logic
5. Keep only runtime tuning parameters:
   - Temperature tolerances
   - Temperature limits
   - Precision/step
   - Timing values
   - Conditional fields based on enabled features:
     - Floor temp limits (if floor_sensor exists)
     - Preset temp overrides (if presets exist)
     - Fan settings (if fan exists)
     - Humidity settings (if humidity_sensor exists)

**Breaking Change**: Yes, this changes what options flow can do
**Migration**: Users directed to use reconfigure for structural changes

### Phase 3: Documentation Updates
- Update spec.md to clarify three-flow separation
- Update architecture.md with reconfigure section
- Create user migration guide
- Update CLAUDE.md

---

## User Experience

### Scenario 1: User wants to change heater entity
**Before**: Options → Change entity ID → Save
**After**: Reconfigure → Change entity ID → Save (reload)
**Impact**: Clearer intent, proper reload

### Scenario 2: User wants to adjust cold tolerance
**Before**: Options → Adjust tolerance → Save
**After**: Options → Adjust tolerance → Save
**Impact**: Same workflow, faster (no reload)

### Scenario 3: User wants to enable floor heating
**Before**: Options → Enable floor heating → Configure → Save
**After**: Reconfigure → Enable floor heating → Configure → Save (reload)
**Impact**: Clearer that this is a structural change

### Scenario 4: User wants to change away preset temp
**Before**: Options → Multi-step wizard → Preset config → Save
**After**: Options → Set away temp → Save
**Impact**: Much simpler workflow

---

## Questions for Clarification

1. **Should reconfigure allow changing ALL settings or just structural ones?**
   - Current implementation: Allows changing everything (full wizard)
   - Alternative: Only show fields that are structural (system type, entities, features)
   - Recommendation: Keep full wizard for consistency with config flow

2. **Should options flow be a single step or multiple steps?**
   - Option A: Single form with all tuning parameters
   - Option B: Multiple steps grouped by feature (basic → floor → presets)
   - Recommendation: Single step with sections for simplicity

3. **How should we handle the migration?**
   - Users accustomed to options flow having all features
   - Need clear messaging: "Use reconfigure to change entities/features"
   - Show helpful error message or redirect?

4. **What about preset temperature overrides?**
   - Changing which presets are enabled → Reconfigure
   - Changing preset temperature values → Options
   - This seems reasonable as temp values are tuning parameters

5. **Should options flow allow changing opening timeouts?**
   - Adding/removing openings → Reconfigure
   - Changing timeout values for existing openings → Options?
   - Or should ALL opening config be in reconfigure only?

---

## Recommendation

Based on HA best practices, I recommend:

1. **Keep current reconfigure implementation** - It properly handles all structural changes
2. **Simplify options flow to Phase 2 plan** - Make it truly for optional tuning only
3. **Single-step options flow** - All tuning parameters in one form with collapsible sections
4. **Clear user messaging** - Help text explaining when to use reconfigure vs options

This aligns with HA quality scale requirements and provides the best UX.
