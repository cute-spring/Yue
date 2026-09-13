import { defineConfig } from '@playwright/test';

import { resolveE2eFrontendPort } from './src/utils/backendPython';

const frontendPort = resolveE2eFrontendPort(process.env);
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
    reuseExistingServer: false,
    timeout: 120000,
  },
});
