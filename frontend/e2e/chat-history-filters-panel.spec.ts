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

  const toggle = page.getByRole('button', { name: 'Expand filters panel' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByPlaceholder('Search title, summary, tags...')).toHaveCount(0);
});
