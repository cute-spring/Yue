import { test, expect } from '@playwright/test';

test('Docs denied: no citations panel and explicit denied text', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__docmain_denied__');
    localStorage.setItem('chat.selected_model', 'docmain_denied');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill('读取被拒绝的文档');
  await input.press('Enter');

  const lastAssistant = page.getByTestId('message-assistant').last();
  await expect(lastAssistant).toContainText('文档访问被拒绝', { timeout: 15000 });
  await expect(lastAssistant.getByTestId('citations')).toHaveCount(0);
  await expect(lastAssistant.getByTestId('gaps')).toBeVisible({ timeout: 15000 });
});
