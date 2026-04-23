import { expect, test } from '@playwright/test';
import { mockBasicChatBootstrap } from './chat-test-helpers';

test('chat history groups by modified date and collapses older dates by default', async ({ page }) => {
  await mockBasicChatBootstrap(page);
  const now = new Date();
  const isoToday = now.toISOString();
  const isoYesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
  const isoOlder = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000).toISOString();

  await page.route('**/api/chat/history', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'chat-today',
          title: 'Today session',
          summary: 'today summary',
          updated_at: isoToday,
          tags: ['today'],
        },
        {
          id: 'chat-yesterday',
          title: 'Yesterday session',
          summary: 'yesterday summary',
          updated_at: isoYesterday,
          tags: ['yesterday'],
        },
        {
          id: 'chat-older',
          title: 'Older session',
          summary: 'older summary',
          updated_at: isoOlder,
          tags: ['older'],
        },
      ]),
    });
  });

  await page.goto('/', { waitUntil: 'networkidle' });

  await expect(page.getByRole('button', { name: 'Toggle date group Today' })).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('button', { name: 'Toggle date group Yesterday' })).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('button', { name: 'Toggle date group Earlier' })).toHaveAttribute('aria-expanded', 'false');

  await expect(page.getByText('Today session')).toBeVisible();
  await expect(page.getByText('Yesterday session')).toBeVisible();
  await expect(page.getByText('Older session')).not.toBeVisible();

  const olderGroupToggle = page.getByRole('button', { name: 'Toggle date group Earlier' });
  await olderGroupToggle.click();
  await expect(page.getByText('Older session')).toBeVisible();
  await expect(olderGroupToggle).toHaveAttribute('aria-expanded', 'true');

  await olderGroupToggle.click();
  await expect(page.getByText('Older session')).not.toBeVisible();
  await expect(olderGroupToggle).toHaveAttribute('aria-expanded', 'false');
});
