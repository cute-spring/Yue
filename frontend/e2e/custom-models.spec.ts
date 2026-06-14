import { test, expect } from '@playwright/test';

test('Custom Models CRUD UI flow', async ({ page }) => {
  await page.route('**/api/models/test/custom', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto('/settings');
  await page.getByRole('button', { name: 'Models' }).click();

  // Open overlay and add
  await page.getByRole('button', { name: /Add Custom \(Overlay\)/i }).click();
  await page.getByTestId('llm-custom-name-input').fill('e2e-custom');
  await page.getByTestId('llm-custom-provider-select').selectOption('openai');
  await page.getByTestId('llm-custom-model-input').fill('x-large');
  await page.getByTestId('llm-custom-base-url-input').fill('https://api.example.com/v1');
  await page.getByRole('button', { name: 'Test' }).last().click();
  await expect(page.getByText('Connection OK')).toBeVisible();
  await page.getByRole('button', { name: 'Save', exact: true }).last().click();

  // Should appear in list
  const item = page.getByTestId('llm-custom-model-e2e-custom');
  await expect(item).toBeVisible();
  await expect(item).toContainText('openai');

  // Delete
  await page.getByTestId('llm-custom-model-delete-e2e-custom').click();
  await page.locator('button').filter({ hasText: /^Delete$/ }).last().click();
  await expect(page.getByText('e2e-custom', { exact: true })).toHaveCount(0, { timeout: 10000 });
});
