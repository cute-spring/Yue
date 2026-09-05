import { defineConfig } from '@playwright/test';

const frontendPort = process.env.YUE_E2E_FRONTEND_PORT || '3020';
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
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    url: frontendUrl,
    reuseExistingServer: true,
    timeout: 120000,
  },
});
