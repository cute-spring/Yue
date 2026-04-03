import { expect, test } from '@playwright/test';

test('Trace Inspector entry is hidden when rollback flags are disabled', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Yue/i);

  await page.getByText('Trace Smoke Chat').first().click();

  await expect(page.getByRole('button', { name: /Open trace inspector/i })).toHaveCount(0);
  await expect(page.getByText('Please inspect the last tool chain for this historical run.').first()).toBeVisible();
});
