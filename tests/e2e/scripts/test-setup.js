#!/usr/bin/env node

/**
 * Test setup script for Home Assistant integration
 * This script starts Home Assistant locally for E2E testing purposes
 * Based on lovelace-fluid-level-background-card implementation
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Configuration directories
const HA_CONFIG_DIR = path.join(__dirname, '..', 'ha_config');

// Ensure HA config directory exists
if (!fs.existsSync(HA_CONFIG_DIR)) {
  console.error('❌ HA config directory not found:', HA_CONFIG_DIR);
  console.error('   Please ensure tests/e2e/ha_config exists with proper configuration.yaml');
  process.exit(1);
}

// Initialize Home Assistant configuration if needed
function ensureConfig() {
  const configFile = path.join(HA_CONFIG_DIR, 'configuration.yaml');

  if (!fs.existsSync(configFile)) {
    console.log('🔧 Creating Home Assistant configuration...');

    const basicConfig = `# Basic Home Assistant configuration for E2E testing
homeassistant:
  name: "E2E Test Home"
  latitude: 52.3676
  longitude: 4.9041
  elevation: 43
  unit_system: metric
  time_zone: "Europe/Amsterdam"
  
  # Disable authentication for testing
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - ::1
        - 172.16.0.0/12
        - 192.168.0.0/16
        - 10.0.0.0/8
      allow_bypass_login: true

# Enable frontend
frontend:
  themes: !include_dir_merge_named themes

# Enable Home Assistant Cloud
cloud:

# Configuration validation
config:

# Logging
logger:
  default: info
  logs:
    homeassistant.core: debug

# HTTP configuration
http:
  server_port: 8123
  cors_allowed_origins:
    - http://localhost:3000
    - http://127.0.0.1:3000

# System health
system_health:

# Sun tracking
sun:

# Enable mobile app support
mobile_app:

# Default config
automation: !include automations.yaml
script: !include scripts.yaml
scene: !include scenes.yaml

# Test sensors for the dual smart thermostat component
sensor:
  - platform: template
    sensors:
      test_temperature_sensor:
        friendly_name: "Test Temperature Sensor"
        unit_of_measurement: "°C"
        value_template: "{{ 22.5 }}"
      test_humidity_sensor:
        friendly_name: "Test Humidity Sensor"
        unit_of_measurement: "%"
        value_template: "{{ 65 }}"

# Input helpers for testing
input_number:
  target_temp:
    name: Target Temperature
    min: 5
    max: 35
    step: 0.5
    initial: 21
    unit_of_measurement: "°C"
    icon: mdi:thermometer

input_boolean:
  hvac_mode:
    name: HVAC Mode
    initial: false
    icon: mdi:power

# Test switch entities
switch:
  - platform: template
    switches:
      test_heater:
        friendly_name: "Test Heater"
        value_template: "{{ is_state('input_boolean.hvac_mode', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          target:
            entity_id: input_boolean.hvac_mode
        turn_off:
          service: input_boolean.turn_off
          target:
            entity_id: input_boolean.hvac_mode
      test_cooler:
        friendly_name: "Test Cooler"  
        value_template: "{{ is_state('input_boolean.hvac_mode', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          target:
            entity_id: input_boolean.hvac_mode
        turn_off:
          service: input_boolean.turn_off
          target:
            entity_id: input_boolean.hvac_mode
`;

    fs.writeFileSync(configFile, basicConfig);
    
    // Create empty default files
    const emptyFiles = ['automations.yaml', 'scripts.yaml', 'scenes.yaml'];
    emptyFiles.forEach(file => {
      const filePath = path.join(HA_CONFIG_DIR, file);
      if (!fs.existsSync(filePath)) {
        fs.writeFileSync(filePath, '# Auto-generated empty file\n[]');
      }
    });

    console.log('✅ Configuration created successfully');
  }

  return Promise.resolve();
}

// Recursively copy a directory (synchronous). Overwrites destination files.
function copyRecursiveSync(src, dest) {
  if (!fs.existsSync(src)) return;
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    const entries = fs.readdirSync(src);
    entries.forEach((entry) => {
      const srcPath = path.join(src, entry);
      const destPath = path.join(dest, entry);
      const entryStat = fs.statSync(srcPath);
      if (entryStat.isDirectory()) {
        copyRecursiveSync(srcPath, destPath);
      } else if (entryStat.isFile()) {
        fs.copyFileSync(srcPath, destPath);
      }
    });
  } else if (stat.isFile()) {
    // src is a single file
    const parent = path.dirname(dest);
    if (!fs.existsSync(parent)) fs.mkdirSync(parent, { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

// Add test resources to existing configuration if not present
function addTestResources() {
  const configFile = path.join(HA_CONFIG_DIR, 'configuration.yaml');
  
  if (!fs.existsSync(configFile)) {
    console.log('⚠️  Configuration file not found, skipping resource addition');
    return;
  }
  // No-op: we now rely on ha_config/configuration.yaml containing the
  // placeholder climate entry. This avoids runtime mutation of the test
  // configuration and makes test runs deterministic.
  console.log('ℹ️ addTestResources is a no-op; using existing ha_config/configuration.yaml');
  // Ensure the custom component from the repository is available in the
  // HA config directory so YAML platform entries are loaded at Home
  // Assistant startup. We copy/overwrite files from the repo's
  // `custom_components/dual_smart_thermostat` into the test HA config.
  try {
  // Resolve repo root reliably: tests/e2e/scripts -> repo root is three levels up
  const repoRoot = path.join(__dirname, '..', '..', '..');
  const repoCustomComponent = path.join(repoRoot, 'custom_components', 'dual_smart_thermostat');
    const destCustomComponentsDir = path.join(HA_CONFIG_DIR, 'custom_components');
    const destCustomComponent = path.join(destCustomComponentsDir, 'dual_smart_thermostat');

    if (fs.existsSync(repoCustomComponent)) {
      console.log(`📦 Copying custom component into HA config: ${repoCustomComponent} -> ${destCustomComponent}`);
      copyRecursiveSync(repoCustomComponent, destCustomComponent);
      console.log('✅ Custom component copied into HA config');
    } else {
      console.log('⚠️ Repository custom_components/dual_smart_thermostat not found, skipping copy');
    }
  } catch (err) {
    console.error('❌ Failed to copy custom component into HA config:', err.message);
  }
  // Apply TEST_HA_PORT override if provided so tests can start HA on an alternate port
  try { applyTestPortOverride(); } catch (e) { /* ignore */ }
}

// If TEST_HA_PORT is specified, update configuration.yaml's http.server_port value
function applyTestPortOverride() {
  const configFile = path.join(HA_CONFIG_DIR, 'configuration.yaml');
  const port = process.env.TEST_HA_PORT;
  if (!port) return;
  try {
    if (!fs.existsSync(configFile)) return;
    let content = fs.readFileSync(configFile, 'utf8');
    // Simple regex to replace server_port under http: section.
    // This handles the common pattern: http:\n  server_port: 8123
    const replaced = content.replace(/(http:\s*[\r\n]+(?:[ \t].*\n)*?)(server_port:)[ \t]*\d+/m, (m, p1, p2) => {
      return p1 + p2 + ' ' + port;
    });
    if (replaced !== content) {
      fs.writeFileSync(configFile, replaced, 'utf8');
      console.log(`🔧 Overrode Home Assistant http.server_port to ${port} in ${configFile}`);
    } else {
      // If pattern didn't match, try a simpler replacement
      const simple = content.replace(/server_port:[ \t]*\d+/, `server_port: ${port}`);
      if (simple !== content) {
        fs.writeFileSync(configFile, simple, 'utf8');
        console.log(`🔧 Set Home Assistant server_port to ${port} in ${configFile}`);
      }
    }
  } catch (err) {
    console.error('❌ Failed to apply TEST_HA_PORT override:', err.message);
  }
}

// Function to start Home Assistant
async function startHomeAssistant() {
  console.log('🏠 Starting Home Assistant locally for E2E tests...');

  try {
    await ensureConfig();
    addTestResources();

    // Start Home Assistant with hass command
    const haProcess = spawn('hass', [
      '--config', HA_CONFIG_DIR,
      '--debug'
    ], {
      stdio: 'inherit',
      env: {
        ...process.env,
        PYTHONPATH: process.env.PYTHONPATH || ''
      }
    });

    haProcess.on('error', (error) => {
      if (error.code === 'ENOENT') {
        console.error('❌ Home Assistant not found. Please install Home Assistant:');
        console.error('   pip install homeassistant');
        console.error('   OR use Docker: npm run test:setup-docker');
      } else {
        console.error('❌ Failed to start Home Assistant:', error.message);
      }
      process.exit(1);
    });

    haProcess.on('exit', (code) => {
      console.log(`🏠 Home Assistant exited with code ${code}`);
      if (code !== 0 && code !== null) {
        console.error('❌ Home Assistant failed to start properly');
        process.exit(code || 1);
      }
    });

    // Handle cleanup on process termination
    const cleanup = () => {
      console.log('🛑 Stopping Home Assistant...');
      haProcess.kill('SIGTERM');
      setTimeout(() => {
        haProcess.kill('SIGKILL');
        process.exit(0);
      }, 5000);
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    // Wait for Home Assistant to be ready
    console.log('⏳ Waiting for Home Assistant to be ready...');
    console.log('   Home Assistant will be available at: http://localhost:8123');
    console.log('   Press Ctrl+C to stop');

  } catch (error) {
    console.error('❌ Failed to setup Home Assistant:', error.message);
    process.exit(1);
  }
}

// If run directly, start HA
if (require.main === module) {
  const command = process.argv[2];

  if (command === '--help' || command === '-h') {
    console.log('Usage: node test-setup.js [command]');
    console.log('');
    console.log('Commands:');
    console.log('  (none)           Start Home Assistant for testing');
    console.log('  --provision-only Only append test resources to configuration.yaml and exit');
    console.log('  --help, -h       Show this help message');
    console.log('');
    console.log('Environment:');
    console.log('  HA config:  tests/e2e/ha_config/');
    console.log('  HA URL:     http://localhost:8123');
    process.exit(0);
  }

  if (command === '--provision-only') {
    ensureConfig()
      .then(() => {
        addTestResources();
        console.log('✅ Provision-only mode completed. Exiting.');
        process.exit(0);
      })
      .catch(err => {
        console.error('❌ Provision-only failed:', err);
        process.exit(1);
      });
    
  }

  startHomeAssistant().catch(error => {
    console.error('❌ Startup failed:', error);
    process.exit(1);
  });
}

module.exports = { startHomeAssistant, ensureConfig, addTestResources };