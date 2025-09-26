#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const haConfig = path.join(__dirname, '..', 'ha_config');
const storageDir = path.join(haConfig, '.storage');
const entries = path.join(storageDir, 'core.config_entries');

console.log('🧹 Resetting Home Assistant persisted config (core.config_entries)');
try {
  if (fs.existsSync(entries)) {
    fs.rmSync(entries);
    console.log('✅ Deleted', entries);
  } else {
    console.log('ℹ️ No core.config_entries to delete');
  }
} catch (e) {
  console.error('❌ Failed to remove core.config_entries:', e.message);
}

console.log('🔄 Restarting Home Assistant containers');
spawnSync('npm', ['run', 'ha:restart'], { stdio: 'inherit', cwd: path.join(__dirname, '..') });
spawnSync('npm', ['run', 'ha:wait'], { stdio: 'inherit', cwd: path.join(__dirname, '..') });

console.log('✅ Reset complete');


