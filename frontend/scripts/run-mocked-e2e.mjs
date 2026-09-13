import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:net';
import { spawn } from 'node:child_process';

async function reservePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(String(address.port));
      });
    });
  });
}

const [backendPort, frontendPort] = await Promise.all([reservePort(), reservePort()]);
const dataDir = mkdtempSync(join(tmpdir(), 'yue-e2e-mocked-'));
const command = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const child = spawn(
  command,
  ['playwright', 'test', '--config=playwright.mocked.config.ts', ...process.argv.slice(2)],
  {
    stdio: 'inherit',
    env: {
      ...process.env,
      YUE_E2E_BACKEND_PORT: backendPort,
      YUE_E2E_FRONTEND_PORT: frontendPort,
      YUE_E2E_DATA_DIR: dataDir,
    },
  },
);

child.once('error', (error) => {
  console.error(error);
  process.exitCode = 1;
});
child.once('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0);
});
