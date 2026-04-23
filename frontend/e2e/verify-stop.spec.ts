import { test, expect } from '@playwright/test';

test('Stop generation functionality', async ({ page }) => {
  await page.goto('http://localhost:3000/');
  await page.waitForLoadState('networkidle');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible({ timeout: 15000 });

  // Resolve and pre-select a model via local storage to avoid dropdown flakiness.
  const firstModel = await page.evaluate(async () => {
    const res = await fetch('/api/models/providers');
    const providers = await res.json();
    for (const provider of providers || []) {
      const models = (provider.available_models?.length ? provider.available_models : provider.models) || [];
      if (models.length > 0) {
        return { provider: provider.name, model: models[0] };
      }
    }
    return null;
  });
  expect(firstModel).toBeTruthy();
  await page.evaluate(({ provider, model }) => {
    localStorage.setItem('yue_selected_provider', provider);
    localStorage.setItem('yue_selected_model', model);
  }, firstModel as { provider: string; model: string });
  await page.reload({ waitUntil: 'networkidle' });
  await expect(input).toBeVisible({ timeout: 15000 });

  await input.fill('Write a 500-word essay about the future of AI in 2026.');
  const submitButton = page.locator('button[type="submit"]');
  await submitButton.click();

  const stopButton = page.locator('button[type="submit"][title=\"Stop Generation\"]');
  await expect(stopButton).toBeVisible({ timeout: 10000 });
  await stopButton.click();
  await expect(page.locator('button[type="submit"][title=\"Send Message\"]')).toBeVisible({ timeout: 10000 });
});
