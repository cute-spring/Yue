import { test, expect } from '@playwright/test';

test('Docs no_hit: no citations panel and explicit no evidence text', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__docmain_nohit__');
    localStorage.setItem('chat.selected_model', 'docmain_nohit');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill('不存在的关键词 12345');
  await input.press('Enter');

  const lastAssistant = page.getByTestId('message-assistant').last();
  await expect(lastAssistant).toContainText('未在已配置的文档范围内找到可引用的依据', { timeout: 15000 });
  await expect(lastAssistant.getByTestId('citations')).toHaveCount(0);
  await expect(lastAssistant.getByTestId('gaps')).toBeVisible({ timeout: 15000 });
});
