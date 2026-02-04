import { test, expect } from '@playwright/test';

test('Chat shows citations emitted by backend', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__docmain__');
    localStorage.setItem('chat.selected_model', 'docmain');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill('Obsidian 插件');
  await input.press('Enter');

  const citations = page.getByTestId('citations');
  await expect(citations).toBeVisible({ timeout: 15000 });
  await expect(citations.getByTestId('citation-path').filter({ hasText: 'backend/tests/fixtures/doc_agent/alpha.md' })).toBeVisible({ timeout: 15000 });
  await expect(citations.getByTestId('citation-snippet').filter({ hasText: 'Obsidian' })).toBeVisible({ timeout: 15000 });
  await expect(citations.getByTestId('citation-locator').first()).toBeVisible({ timeout: 15000 });
  await expect(citations.getByTestId('citation-reason').first()).toBeVisible({ timeout: 15000 });
  await expect(citations.getByTestId('citation-copy').first()).toBeVisible({ timeout: 15000 });
});
