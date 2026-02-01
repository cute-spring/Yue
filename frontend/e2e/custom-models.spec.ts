import { test, expect } from '@playwright/test';

test('Custom Models CRUD UI flow', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Llm' }).click();

  // Add / Update
  await page.getByPlaceholder('Name', { exact: true }).fill('e2e-custom');
  await page.getByPlaceholder('Base URL', { exact: true }).fill('https://api.example.com/v1');
  await page.getByPlaceholder('API Key', { exact: true }).fill('****masked****');
  await page.getByPlaceholder('Model', { exact: true }).fill('x-large');
  await page.getByRole('button', { name: /Add \/ Update/i }).click();

  // Should appear in list
  const item = page.locator('div').filter({ hasText: 'e2e-custom' }).first();
  await expect(item).toBeVisible();

  // Test connection (capture alert)
  page.once('dialog', async (dialog) => {
    await dialog.accept();
  });
  await page.getByRole('button', { name: 'Test', exact: true }).last().click();

  // Delete
  await page.evaluate(() => { (window as any).confirm = () => true; });
  await page.getByRole('button', { name: /Delete/i }).last().click();

  // Should be removed
  await expect(page.locator('div').filter({ hasText: 'e2e-custom' }).first()).toHaveCount(0, { timeout: 10000 });
});
