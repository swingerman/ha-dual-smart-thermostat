# v0.11.0 - Production Ready & Enhanced Flexibility 🚀

> **Stable Release**: Set up your smart thermostat in minutes with complete UI configuration, dynamic template-based presets, and enhanced device support!

## ✨ Major Features

### 🎨 Complete UI Configuration - **Set Up Your Thermostat in Minutes!**

**Configure your entire smart thermostat through Home Assistant's UI with a guided, step-by-step wizard.**

No more complex YAML editing - simply choose your system type, select your devices, and configure features through an intuitive interface.

**Supported System Types:**

- **Simple Heater** - Basic heating-only systems
- **AC Only** - Cooling-only (air conditioning) systems
- **Heat Pump** - Single device for both heating and cooling
- **Heater + Cooler** - Separate heating and cooling devices with dual-mode capability

**Configure Advanced Features:**

- **Floor Heating Control** - Set min/max floor temperature limits with floor sensor
- **Fan Management** - Independent fan control with multiple operating modes
- **Humidity Control** - Dehumidification with target humidity and tolerances
- **Opening Detection** - Auto-pause when windows/doors open with customizable timeouts
- **Preset Modes** - Away, Sleep, Home, Comfort, Eco, Boost, Activity, and Anti-Freeze presets
- **Mode-Specific Tolerances** - Different temperature tolerances for heating vs cooling

**Smart Configuration:**

- Entity selectors show only compatible devices for each field
- Built-in validation prevents configuration errors
- Default values pre-filled for quick setup
- Reconfigure flow lets you change settings anytime without losing data
- Clear descriptions guide you through each option

**Flexibility:**

- YAML configuration still fully supported for power users
- Mix and match: UI for initial setup, YAML for advanced customization
- All features available in both UI and YAML modes

**Get started in minutes:** Add Integration → Dual Smart Thermostat → Follow the wizard!

- Details: #428, #450, #456

---

### 🎯 Template-Based Preset Temperatures
**Dynamic presets that adapt to your needs!**

Configure preset temperatures using Home Assistant templates, enabling dynamic temperature adjustments based on any state in your system.

- Use input_number helpers for easy temperature adjustments
- Reference sensor values for weather-based presets
- Create complex logic with templates
- Fully backward compatible with static temperatures
- Example: `"{{ states('input_number.away_temp') }}"`
- Details: #96, #470

**Use Cases:**

- Seasonal temperature adjustments
- Weather-responsive comfort settings
- Guest mode with customizable temperatures
- Energy-saving schedules via automation

---

### 🔌 Input Boolean Support for Equipment
**More flexibility in device configuration!**

Use `input_boolean` entities in addition to `switch` entities for all equipment controls. Perfect for:

- Virtual thermostats without physical switches
- Testing and development setups
- Integration with third-party systems
- Advanced automation scenarios

Supported for: heater, cooler, auxiliary heater, fan, and dryer controls.

- Details: #493, #497

---

### 🐳 Docker-Based Development Environment
**Professional development workflow for contributors!**

Complete Docker development environment with comprehensive testing and linting support.

- Python 3.13 + Home Assistant 2025.1.0+ guaranteed
- Convenient scripts: `./scripts/docker-test`, `./scripts/docker-lint`
- Multi-version testing capability
- Consistent CI/CD environment
- Details: Developer documentation

---

## 🔨 Improvements & Bug Fixes

### Configuration Experience
- Configuration values now persist correctly between UI flows
- Tolerance fields properly accept all valid values including 0
- Time-based settings (min_cycle_duration, keep_alive) display and save correctly
- Preset management works reliably when adding or removing presets
- Temperature precision and rounding are accurate throughout

### Control Logic
- Heat/cool mode tolerance behavior now works as expected
- Improved keep-alive logic prevents unnecessary device commands
- State transitions work reliably in all operating modes

---

## 📊 By the Numbers

- **26 commits** of improvements
- **17 merged pull requests**
- **4 system types** supported (simple heater, AC only, heat pump, heater+cooler)
- **8 advanced features** available (floor heating, fan, humidity, openings, presets, templates, tolerances, reconfigure)
- **3 major features** in this release
- **100% backward compatible**

---

## 🔄 Migration Guide

**Excellent News**: No migration needed! This release is 100% backward compatible.

**New Capabilities to Explore**:

1. **UI Configuration**: Set up new thermostats through the UI wizard
2. **Template-Based Presets**: Make your presets dynamic with Home Assistant templates
3. **Input Boolean Support**: Use input_boolean entities for equipment controls
4. **Reconfigure Flow**: Modify existing thermostats without recreating them

---

---

## 🙏 Thank You

Huge thanks to our community for:
- Testing v0.10.0 and reporting issues promptly
- Providing detailed bug reports that helped us fix issues quickly
- Contributing feature ideas and use cases
- Supporting the project's development

---

## 📖 Resources

- **Documentation**: [README.md](https://github.com/swingerman/ha-dual-smart-thermostat)
- **Examples**: [examples/](https://github.com/swingerman/ha-dual-smart-thermostat/tree/master/examples)
- **Template Presets Guide**: Check examples for template-based preset patterns
- **Issues**: [GitHub Issues](https://github.com/swingerman/ha-dual-smart-thermostat/issues)

---

## 🔮 What's Next?

Looking ahead to future releases:
- Native climate entity control (#281)
- Enhanced custom preset support (#320)
- Two-stage cooling (#237)
- Additional automation capabilities

---

## 💝 Support This Project

If this integration makes your home more comfortable and efficient, consider supporting development:

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue?style=flat&logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=S6NC9BYVDDJMA&source=url)

Your support helps maintain this integration and develop new features! ☕️

---

**Full Changelog**: https://github.com/swingerman/ha-dual-smart-thermostat/compare/v0.10.0...v0.11.0

---

💙 **Enjoying this integration?** Help others discover it:
- ⭐ Star the repository
- 💬 Share your configuration examples
- 📣 Spread the word in the Home Assistant community
- 🐛 Report bugs to help us improve
