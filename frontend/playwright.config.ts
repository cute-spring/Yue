import { defineConfig } from '@playwright/test';

const e2eDataDir = process.env.YUE_E2E_DATA_DIR || '/tmp/yue-e2e-real-data';

export default defineConfig({
  testDir: 'e2e',
  timeout: 30000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
    timezoneId: 'Asia/Shanghai',
  },
  webServer: [
    {
      command: `cd ../backend && rm -f ${e2eDataDir}/yue.db ${e2eDataDir}/yue.db-wal ${e2eDataDir}/yue.db-shm && PYTHONPATH=. YUE_DATA_DIR=${e2eDataDir} .venv/bin/python scripts/seed_trace_smoke_e2e.py --data-dir ${e2eDataDir} && PYTHONPATH=. YUE_DATA_DIR=${e2eDataDir} uvicorn app.main:app --host 127.0.0.1 --port 8003`,
      url: 'http://127.0.0.1:8003/docs',
      reuseExistingServer: true,
      timeout: 120000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 3000',
      url: 'http://127.0.0.1:3000',
      reuseExistingServer: true,
      timeout: 120000,
    },
  ],
  reporter: [['list']],
});
