import { test, expect } from '@playwright/test';

test('Chat history: create, reopen, and delete session', async ({ page }) => {
  const title = `History E2E ${Date.now()}`;

  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__guard__');
    localStorage.setItem('chat.selected_model', 'guard');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill(title);
  await input.press('Enter');

  await expect(page.getByTestId('message-user').filter({ hasText: title })).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('message-assistant').last().getByText('OK', { exact: true })).toBeVisible({ timeout: 15000 });

  const historyItem = page.getByTestId('chat-history-item').filter({ hasText: title }).first();
  await expect(historyItem).toBeVisible({ timeout: 15000 });

  await page.getByTestId('new-chat').click();
  await expect(page.getByText('Empowering your workflow with Yue')).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId('message-user')).toHaveCount(0);

  await historyItem.click();
  await expect(page.getByTestId('message-user').filter({ hasText: title })).toBeVisible({ timeout: 15000 });

  page.once('dialog', d => d.accept());
  await historyItem.hover();
  await historyItem.getByTestId('chat-history-delete').click();
  await expect(page.getByTestId('chat-history-item').filter({ hasText: title })).toHaveCount(0, { timeout: 15000 });
});

