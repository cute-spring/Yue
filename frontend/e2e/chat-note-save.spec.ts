import { test, expect } from '@playwright/test';

test('Chat /note saves assistant message into Notebook', async ({ page }) => {
  const marker = `note-${Date.now()}`;
  const expectedTitlePrefix = `ECHO:${marker}`;

  await page.addInitScript(() => {
    localStorage.setItem('chat.selected_provider', '__echo__');
    localStorage.setItem('chat.selected_model', 'echo');
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/Ask Yue anything/i);
  await expect(input).toBeVisible();

  await input.fill(marker);
  await input.press('Enter');

  const lastAssistant = page.getByTestId('message-assistant').last();
  await expect(lastAssistant).toContainText(expectedTitlePrefix, { timeout: 15000 });

  await input.fill('/note');
  await input.press('Enter');
  await expect(page.getByText('Saved to notes.')).toBeVisible({ timeout: 15000 });

  await page.goto('/notebook');
  await expect(page.getByTestId('notebook-sidebar')).toBeVisible({ timeout: 15000 });

  const noteItem = page.getByTestId('notebook-note-item').filter({ hasText: expectedTitlePrefix }).first();
  await expect(noteItem).toBeVisible({ timeout: 15000 });

  page.once('dialog', d => d.accept());
  await noteItem.hover();
  await noteItem.getByTestId('notebook-note-delete').click();
  await expect(page.getByTestId('notebook-note-item').filter({ hasText: expectedTitlePrefix })).toHaveCount(0, { timeout: 15000 });
});

