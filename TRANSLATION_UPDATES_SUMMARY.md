# Translation Updates Summary

## Overview
Updated the openings scope configuration to use proper Home Assistant translation keys instead of hardcoded English labels, enabling full internationalization support.

## Changes Made

### 1. Translation Files Updated

#### English translations (`translations/en.json`)
- Added `selector.openings_scope.options` section with translatable scope options:
  - `all`: "All HVAC modes"
  - `cool`: "Cooling only"
  - `heat`: "Heating only"
  - `heat_cool`: "Heat/Cool mode"
  - `fan_only`: "Fan only"
  - `dry`: "Dry mode"

#### Slovak translations (`translations/sk.json`)
- Added `selector.openings_scope.options` section with Slovak translations:
  - `all`: "Všetky HVAC režimy"
  - `cool`: "Iba chladenie"
  - `heat`: "Iba vykurovanie"
  - `heat_cool`: "Režim vykurovanie/chladenie"
  - `fan_only`: "Iba ventilátor"
  - `dry`: "Režim sušenia"

### 2. Code Changes

#### openings.py
- Updated scope options generation to use string values instead of dictionaries with labels
- Changed from hardcoded English labels to translatable selector options
- Maintained all existing adaptive logic for system-aware scope generation

### 3. Test Updates

#### test_scope_generation.py
- Updated helper function `extract_scope_options_from_schema()` to handle both old and new formats
- Updated all test methods to work with string-based options instead of dictionary-based options
- All 6 scope generation tests now pass

#### test_step_ordering.py
- Updated scope option extraction to handle the new translation format
- All 4 step ordering tests now pass

### 4. Documentation Updates

#### README.md
- Enhanced openings scope documentation with:
  - Explanation of adaptive scope options
  - Examples by system type
  - Internationalization support details
  - Current supported languages

## Verification

### Tests Passing
- ✅ 6 scope generation tests
- ✅ 4 step ordering tests
- ✅ 11 total openings tests
- ✅ All related configuration flow tests

### Translation Demo
Created and verified translation functionality showing proper scope options in both English and Slovak for all system configurations.

## Benefits

1. **Proper Internationalization**: Scope options now use Home Assistant's translation system
2. **Maintainable**: Adding new languages only requires updating translation files
3. **Consistent**: Follows Home Assistant UI translation patterns
4. **User-Friendly**: Scope options appear in user's selected language
5. **Backward Compatible**: Existing configurations continue to work

## Impact

- No breaking changes to existing configurations
- Users will see scope options in their configured Home Assistant language
- Easier for community to add translations for additional languages
- Maintains all existing adaptive scope generation logic
