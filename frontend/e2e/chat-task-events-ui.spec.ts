import { test, expect } from '@playwright/test';

test('Chat shows task_event progress in UI', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__toolcall__');
    localStorage.setItem('chat.selected_model', 'toolcall');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill('run deterministic subtask');
  await input.press('Enter');

  const panel = page.getByTestId('task-runs');
  await expect(panel).toBeVisible({ timeout: 15000 });

  await expect(panel.getByTestId('task-id').filter({ hasText: 'subtask-1' })).toBeVisible({ timeout: 15000 });
  await expect(panel.getByTestId('task-status').filter({ hasText: 'completed' })).toBeVisible({ timeout: 15000 });
  await expect(panel.getByTestId('task-run').getByText('OK', { exact: true })).toBeVisible({ timeout: 15000 });
});
