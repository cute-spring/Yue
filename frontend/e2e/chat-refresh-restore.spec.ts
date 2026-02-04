import { test, expect } from '@playwright/test';

test('Chat refresh restore: history persists and can reopen after reload', async ({ page }) => {
  const marker = `refresh-${Date.now()}`;

  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__echo__');
    localStorage.setItem('chat.selected_model', 'echo');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill(marker);
  await input.press('Enter');

  const lastAssistant = page.getByTestId('message-assistant').last();
  await expect(lastAssistant).toContainText(`ECHO:${marker}`, { timeout: 15000 });

  await page.reload();
  await expect(page.getByTestId('chat-history')).toBeVisible();

  const historyItem = page.getByTestId('chat-history-item').filter({ hasText: marker }).first();
  await expect(historyItem).toBeVisible({ timeout: 15000 });
  await historyItem.click();

  await expect(page.getByTestId('message-user').filter({ hasText: marker })).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('message-assistant').filter({ hasText: `ECHO:${marker}` })).toBeVisible({ timeout: 15000 });
});

