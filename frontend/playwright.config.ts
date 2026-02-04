import { defineConfig } from '@playwright/test';

const isCI = Boolean((globalThis as any).process?.env?.CI);

export default defineConfig({
  testDir: 'e2e',
  timeout: 30000,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
  },
  webServer: [
    {
      command: 'python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8003',
      url: 'http://127.0.0.1:8003/api/mcp/status',
      reuseExistingServer: !isCI,
      cwd: '../backend',
      timeout: 120000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 3000',
      url: 'http://127.0.0.1:3000/',
      reuseExistingServer: !isCI,
      timeout: 120000,
    },
  ],
  reporter: [['list']],
});
