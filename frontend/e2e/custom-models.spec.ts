import { test, expect } from '@playwright/test';

test('Custom Models CRUD UI flow', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Models' }).click();

  // Open overlay and add
  await page.getByRole('button', { name: /Add Custom \(Overlay\)/i }).click();
  await page.getByPlaceholder('my-custom').fill('e2e-custom');
  await page.getByRole('combobox').first().selectOption('openai');
  await page.getByPlaceholder('gpt-4o').fill('x-large');
  await page.getByPlaceholder('https://...').fill('https://api.example.com/v1');
  await page.getByPlaceholder('****').fill('****masked****');
  await page.getByRole('button', { name: 'Test' }).click();
  await page.getByRole('button', { name: 'Save', exact: true }).first().click();

  // Should appear in list
  const item = page.locator('div').filter({ hasText: 'e2e-custom' }).first();
  await expect(item).toBeVisible();

  // Delete
  await page.evaluate(() => { (window as any).confirm = () => true; });
  await item.locator('button', { hasText: 'Delete' }).first().click();
  await expect(page.getByText('e2e-custom', { exact: true })).toHaveCount(0, { timeout: 10000 });
});
