import { expect, test } from '@playwright/test';

test('Trace Inspector renders seeded summary and raw trace data', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/Yue/i);

  await page.getByText('Trace Smoke Chat').first().click();

  const traceButton = page.getByRole('button', { name: /Open trace inspector/i });
  await expect(traceButton).toBeVisible();
  await traceButton.click();

  const dialog = page.getByRole('dialog', { name: 'Trace Inspector' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('Latest Historical Run')).toBeVisible();
  await expect(dialog.getByText('Please inspect the last tool chain for this historical run.').first()).toBeVisible();
  await expect(dialog.locator('article').filter({ hasText: 'docs_search' }).first()).toBeVisible();
  await expect(dialog.locator('article').filter({ hasText: 'summarize_notes' }).first()).toBeVisible();
  await expect(dialog.getByText('Parent-child call structure')).toBeVisible();

  const rawButton = page.getByRole('button', { name: 'Raw' });
  await expect(rawButton).toBeVisible();
  await rawButton.click();

  await expect(dialog.getByText('Raw Mode')).toBeVisible();
  await dialog.getByText('System Prompt').click();
  await expect(dialog.getByText('You are a precise trace analysis assistant.')).toBeVisible();
  await expect(dialog.getByText('Raw payload').first()).toBeVisible();
});
