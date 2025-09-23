#!/usr/bin/env node
const http = require('http');
const timeoutMs = 180000; // 3 minutes
const intervalMs = 3000;

function isHealthy() {
  return new Promise((resolve) => {
    const req = http.get({ host: '127.0.0.1', port: 8123, path: '/manifest.json', timeout: 2000 }, (res) => {
      resolve(res.statusCode === 200 || res.statusCode === 401);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

const start = Date.now();
process.stdout.write('⏳ Waiting for Home Assistant to be healthy');
let dots = 0;
async function tick() {
  const ok = await isHealthy();
  if (ok) {
    console.log('\n✅ Home Assistant is healthy');
    process.exit(0);
  }
  if (Date.now() - start > timeoutMs) {
    console.error('\n❌ Timed out waiting for Home Assistant to be healthy');
    process.exit(1);
  }
  process.stdout.write('.');
  dots = (dots + 1) % 10;
  setTimeout(tick, intervalMs);
}
tick();


