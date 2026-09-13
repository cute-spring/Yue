import { defineConfig } from '@playwright/test';

import { resolveBackendPython, resolveE2eBackendPort, resolveE2eFrontendPort } from './src/utils/backendPython';

const e2eDataDir = process.env.YUE_E2E_DATA_DIR || '/tmp/yue-e2e-real-data';
const backendPort = resolveE2eBackendPort(process.env);
const frontendPort = resolveE2eFrontendPort(process.env);
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
  webServer: [
    {
      command: `rm -f ${e2eDataDir}/yue.db ${e2eDataDir}/yue.db-wal ${e2eDataDir}/yue.db-shm && PYTHONPATH=backend YUE_DATA_DIR=${e2eDataDir} ${backendPython} backend/scripts/seed_trace_smoke_e2e.py --data-dir ${e2eDataDir} && PYTHONPATH=backend YUE_DATA_DIR=${e2eDataDir} ${backendPython} -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: '..',
      url: `${backendUrl}/api/health/`,
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
  reporter: [['list']],
});
