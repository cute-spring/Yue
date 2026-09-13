import { defineConfig } from '@playwright/test';

import { resolveBackendPython } from './src/utils/backendPython';

function requireIsolationEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required isolated mocked E2E environment variable: ${name}`);
  }
  return value;
}

const e2eDataDir = requireIsolationEnvironment('YUE_E2E_DATA_DIR');
const backendPort = requireIsolationEnvironment('YUE_E2E_BACKEND_PORT');
const frontendPort = requireIsolationEnvironment('YUE_E2E_FRONTEND_PORT');
const backendPython = resolveBackendPython(process.env);
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: 'e2e',
  timeout: 30000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: frontendUrl,
    headless: true,
    timezoneId: 'Asia/Shanghai',
  },
  reporter: [['list']],
  webServer: [
    {
      command: `rm -f ${e2eDataDir}/yue.db ${e2eDataDir}/yue.db-wal ${e2eDataDir}/yue.db-shm && PYTHONPATH=backend YUE_DATA_DIR=${e2eDataDir} ${backendPython} backend/scripts/seed_trace_smoke_e2e.py --data-dir ${e2eDataDir} && PYTHONPATH=backend YUE_DATA_DIR=${e2eDataDir} ${backendPython} -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `${backendUrl}/docs`,
      cwd: '..',
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: `YUE_BACKEND_URL=${backendUrl} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
