import { defineConfig } from '@playwright/test';

const e2eDataDir = process.env.YUE_E2E_DATA_DIR || '/tmp/yue-e2e-real-data';
const backendPort = process.env.YUE_E2E_BACKEND_PORT || '8013';
const frontendPort = process.env.YUE_E2E_FRONTEND_PORT || '3010';
const backendUrl = `http://127.0.0.1:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: 'e2e',
  testMatch: 'chat-history-timezone-real.spec.ts',
  timeout: 45000,
  retries: 0,
  use: {
    baseURL: frontendUrl,
    headless: true,
    timezoneId: 'Asia/Shanghai',
  },
  reporter: [['list']],
  webServer: [
    {
      command: `YUE_DATA_DIR=${e2eDataDir} PYTHONPATH=backend backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      url: `${backendUrl}/api/health/`,
      cwd: '..',
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: `YUE_BACKEND_URL=${backendUrl} npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: frontendUrl,
      cwd: '.',
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
