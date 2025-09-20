/**
 * Global setup for Playwright E2E tests
 * This runs once before all tests and waits for Home Assistant to be ready
 */
async function globalSetup(): Promise<void> {
  console.log('🏠 Starting Home Assistant for E2E tests...');

  // Attempt deterministic provisioning so the integration is present for tests.
  // This appends minimal YAML used by tests. It is safe to run repeatedly.
  try {
    // Resolve script path relative to this file
    const path = await import('path');
    const child = await import('child_process');
    const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'test-setup.js');
    console.log('➡️ Running provisioning script to ensure integration presence:', scriptPath);
    const res = child.spawnSync('node', [scriptPath, '--provision-only'], { stdio: 'inherit' });
    if (res.error) {
      console.log('⚠️ Provisioning script failed to run:', res.error.message);
    } else if (res.status !== 0) {
      console.log('⚠️ Provisioning script exited with non-zero status:', res.status);
    } else {
      console.log('✅ Provisioning script executed (appended test YAML)');
    }
  } catch (err) {
    console.log('⚠️ Could not run provisioning script automatically:', err instanceof Error ? err.message : err);
  }

  // Try a simple HTTP check to the HA states API for a known harmless endpoint.
  // This lets us detect if HA is running and whether we're authorized.
  const http = await import('http');
  const net = await import('net');
  const path = await import('path');

  function checkPortOpen(host: string, port: number, timeout = 2000): Promise<boolean> {
    return new Promise((resolve) => {
      const socket = new net.Socket();
      const timer = setTimeout(() => {
        socket.destroy();
        resolve(false);
      }, timeout);
      socket.once('error', () => {
        clearTimeout(timer);
        resolve(false);
      });
      socket.once('connect', () => {
        clearTimeout(timer);
        socket.end();
        resolve(true);
      });
      socket.connect(port, host);
    });
  }

  // If port 8123 is not open, start a local Home Assistant using our test-setup script.
  const portOpen = await checkPortOpen('127.0.0.1', 8123);
  if (!portOpen) {
    console.log('🔌 Port 8123 is not in use. Starting local Home Assistant for tests...');
    // Start HA in background using our node wrapper which calls hass with --config tests/e2e/ha_config
    const child = await import('child_process');
    const scriptPath = path.resolve(__dirname, '..', '..', 'scripts', 'test-setup.js');
    const haProc = child.spawn('node', [scriptPath], {
      detached: true,
      stdio: 'inherit'
    });
    haProc.unref();
    // Give HA some time to start listening on the port
    console.log('⏳ Waiting for Home Assistant to open port 8123...');
    let waited = 0;
    const maxWait = 120; // seconds
    while (waited < maxWait) {
      const open = await checkPortOpen('127.0.0.1', 8123);
      if (open) break;
      await new Promise(r => setTimeout(r, 1000));
      waited++;
    }
    if (waited >= maxWait) {
      throw new Error('❌ Timed out waiting for Home Assistant to start on port 8123');
    }
    console.log('✅ Home Assistant process started and listening on 8123');
  } else {
    console.log('ℹ️ Port 8123 already in use. Assuming Home Assistant is managed externally.');
  }

  // Finally do a small HTTP GET to the root to ensure the UI is reachable
  const baseUrl = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8123';
  const maxRetries = 30;
  let attempts = 0;
  let reachable = false;
  while (attempts < maxRetries && !reachable) {
    try {
      // await an HTTP GET to /api/ to ensure the server is responsive
      await new Promise<void>((resolve) => {
        const req = http.get(`${baseUrl}/api/`, (res) => {
          // 200/401 both indicate a running HA. 401 means auth required.
          if (res.statusCode && (res.statusCode === 200 || res.statusCode === 401)) {
            reachable = true;
            resolve();
          } else {
            resolve();
          }
        });
        req.on('error', () => resolve());
      });
    } catch {
      // ignore and retry
    }
    if (!reachable) {
      await new Promise(r => setTimeout(r, 2000));
      attempts++;
    }
  }

  if (!reachable) {
    throw new Error('❌ Home Assistant root API not reachable after retries');
  }

  console.log('✅ Global setup completed - Home Assistant is ready (or reachable)');
}

export default globalSetup;
