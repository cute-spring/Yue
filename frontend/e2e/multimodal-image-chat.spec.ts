import { expect, test } from '@playwright/test';

test('shows image upload affordance in chat input', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();
  const uploadButton = page.getByRole('button', { name: 'Upload images' });
  await expect(uploadButton).toBeVisible();
});
