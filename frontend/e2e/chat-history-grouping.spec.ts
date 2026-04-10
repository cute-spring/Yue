import { expect, test } from '@playwright/test';
import { mockBasicChatBootstrap } from './chat-test-helpers';

test('chat history groups by modified date and collapses older dates by default', async ({ page }) => {
  await mockBasicChatBootstrap(page);

  await page.route('**/api/chat/history', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'chat-today',
          title: 'Today session',
          summary: 'today summary',
          updated_at: '2026-04-11T09:00:00+08:00',
          tags: ['today'],
        },
        {
          id: 'chat-yesterday',
          title: 'Yesterday session',
          summary: 'yesterday summary',
          updated_at: '2026-04-10T09:00:00+08:00',
          tags: ['yesterday'],
        },
        {
          id: 'chat-older',
          title: 'Older session',
          summary: 'older summary',
          updated_at: '2026-03-29T09:00:00+08:00',
          tags: ['older'],
        },
      ]),
    });
  });

  await page.goto('/', { waitUntil: 'networkidle' });

  await expect(page.getByRole('button', { name: 'Toggle date group 4/11/2026' })).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('button', { name: 'Toggle date group 4/10/2026' })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('button', { name: 'Toggle date group 3/29/2026' })).toHaveAttribute('aria-expanded', 'false');

  await expect(page.getByText('Today session')).toBeVisible();
  await expect(page.getByText('Yesterday session')).not.toBeVisible();
  await expect(page.getByText('Older session')).not.toBeVisible();

  const olderGroupToggle = page.getByRole('button', { name: 'Toggle date group 3/29/2026' });
  await olderGroupToggle.click();
  await expect(page.getByText('Older session')).toBeVisible();
  await expect(olderGroupToggle).toHaveAttribute('aria-expanded', 'true');

  await olderGroupToggle.click();
  await expect(page.getByText('Older session')).not.toBeVisible();
  await expect(olderGroupToggle).toHaveAttribute('aria-expanded', 'false');
});
