# AC Only Baseline Images

This directory contains baseline images for visual regression testing of the ac_only system type configuration flow.

## Pixel Difference Tolerances

- **Form Screenshots**: 2% pixel difference tolerance
- **Dialog Screenshots**: 1% pixel difference tolerance  
- **Integration List Screenshots**: 3% pixel difference tolerance

## Files

- `config_flow_step1.png` - System type selection step
- `config_flow_step2.png` - Core configuration step (cooler, sensor, tolerances)
- `config_flow_step3.png` - Advanced options step (if present)
- `config_flow_preview.png` - Final preview before completion
- `integration_card.png` - Integration card in integrations list after setup

## Updating Baselines

To update baseline images after legitimate UI changes:

```bash
cd tests/e2e
npx playwright test --update-snapshots
```

## Test Environment

These baselines are captured using:
- Chromium browser in headless mode
- 1280x720 viewport
- Home Assistant running on localhost:8123
- Light theme (default)