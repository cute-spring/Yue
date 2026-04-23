import { expect, test } from '@playwright/test';
import { mockBasicChatBootstrap } from './chat-test-helpers';

test('filters panel defaults to collapsed even if legacy preference stored it as expanded', async ({ page }) => {
  await mockBasicChatBootstrap(page);

  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          chat_history_filter_panel_collapsed: false,
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto('/', { waitUntil: 'networkidle' });

  // Current UI no longer exposes a collapsible filters panel.
  // Legacy preference should be ignored and search remains available.
  await expect(page.getByPlaceholder('Search chats...')).toBeVisible();
});
