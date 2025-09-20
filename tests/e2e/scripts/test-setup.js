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

// Add test resources to existing configuration if not present
function addTestResources() {
  const configFile = path.join(HA_CONFIG_DIR, 'configuration.yaml');
  
  if (!fs.existsSync(configFile)) {
    console.log('⚠️  Configuration file not found, skipping resource addition');
    return;
  }

  let config = fs.readFileSync(configFile, 'utf8');

  // Check if dual smart thermostat is already configured
  if (!config.includes('dual_smart_thermostat')) {
    console.log('🔧 Adding dual smart thermostat test configuration...');

    const testThermostat = `
# Dual Smart Thermostat test configuration
climate:
  - platform: dual_smart_thermostat
    name: Test Dual Smart Thermostat
    heater: switch.test_heater
    cooler: switch.test_cooler
    target_sensor: sensor.test_temperature_sensor
    min_temp: 7
    max_temp: 35
    target_temp: 21
    precision: 0.1
    initial_hvac_mode: "off"
`;

    fs.appendFileSync(configFile, testThermostat);
    console.log('✅ Test thermostat configuration added');
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
      '--log-level', 'info',
      '--verbose'
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
    console.log('  (none)      Start Home Assistant for testing');
    console.log('  --help, -h  Show this help message');
    console.log('');
    console.log('Environment:');
    console.log('  HA config:  tests/e2e/ha_config/');
    console.log('  HA URL:     http://localhost:8123');
    process.exit(0);
  }
  
  startHomeAssistant().catch(error => {
    console.error('❌ Startup failed:', error);
    process.exit(1);
  });
}

module.exports = { startHomeAssistant, ensureConfig, addTestResources };