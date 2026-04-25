import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const BACKEND_PYTHON = path.join(REPO_ROOT, 'backend', '.venv', 'bin', 'python');
const TRACE_SEED_SCRIPT = path.join(REPO_ROOT, 'backend', 'scripts', 'seed_trace_smoke_e2e.py');
const E2E_DATA_DIR = process.env.YUE_E2E_DATA_DIR || '/tmp/yue-e2e-real-data';

const seedTraceSmokeData = () => {
  execFileSync(BACKEND_PYTHON, [TRACE_SEED_SCRIPT, '--data-dir', E2E_DATA_DIR], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      PYTHONPATH: 'backend',
      YUE_DATA_DIR: E2E_DATA_DIR,
    },
    stdio: 'inherit',
  });
};

test('Trace Inspector renders seeded summary and raw trace data', async ({ page, request }) => {
  seedTraceSmokeData();
  await request.post('http://127.0.0.1:8003/api/config/feature_flags', {
    data: {
      chat_trace_ui_enabled: true,
      chat_trace_raw_enabled: true,
    },
  });

  await page.goto('/');
  await expect(page).toHaveTitle(/Yue/i);

  await page.getByText('Trace Smoke Chat').first().click();

  const traceButton = page.getByRole('button', { name: /Open trace inspector/i });
  await expect(traceButton).toBeVisible();
  await traceButton.click();

  const dialog = page.getByRole('dialog', { name: 'Trace Inspector' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Latest Historical Run')).toBeVisible();
  await expect(dialog.getByText('Please inspect the last tool chain for this historical run.').first()).toBeVisible();
  await expect(dialog.locator('article').filter({ hasText: 'docs_search' }).first()).toBeVisible();
  await expect(dialog.locator('article').filter({ hasText: 'summarize_notes' }).first()).toBeVisible();
  await expect(dialog.getByText('Parent-child call structure')).toBeVisible();

  const rawButton = page.getByRole('button', { name: 'Raw' });
  await expect(rawButton).toBeVisible();
  await rawButton.click();

  await expect(dialog.getByText('Raw Mode')).toBeVisible();
  await dialog.getByText('System Prompt').click();
  await expect(dialog.getByText('You are a precise trace analysis assistant.')).toBeVisible();
  await expect(dialog.getByText('Raw payload').first()).toBeVisible();
});
