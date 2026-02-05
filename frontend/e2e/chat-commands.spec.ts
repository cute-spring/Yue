import { test, expect } from '@playwright/test';

test('Chat slash commands and @mention dropdown', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  // @mention opens dropdown
  await input.fill('@');
  const dropdown = page.locator('div').filter({ hasText: /Mention Intelligence Agent/i }).first();
  await expect(dropdown).toBeVisible();

  // Select first agent and dropdown closes
  const firstItem = dropdown.getByRole('button').first();
  await firstItem.click();
  await expect(dropdown).toHaveCount(0);

  // /help command shows list
  await input.fill('/help');
  await input.press('Enter');
  await expect(page.locator('text=Commands: /help /note /clear')).toBeVisible();

  // /note without assistant message shows fallback
  await input.fill('/note');
  await input.press('Enter');
  const fallback = page.locator('text=No assistant message to save.');
  const saved = page.locator('text=Saved to notes.');
  await expect(fallback.or(saved)).toBeVisible({ timeout: 10000 });
});
