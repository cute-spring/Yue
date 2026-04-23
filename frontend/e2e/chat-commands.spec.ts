import { test, expect } from '@playwright/test';
import { installClipboardCapture, mockBasicChatBootstrap, mockChatSession } from './chat-test-helpers';

test('Chat slash commands and @mention dropdown', async ({ page }) => {
  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible();

  // @mention opens slash/mention picker
  await input.fill('@');
  const dropdown = page.locator('div').filter({ hasText: /Slash Agent Picker/i }).first();
  await expect(dropdown).toBeVisible();

  // Select first agent and dropdown closes
  const firstItem = dropdown.getByRole('button').first();
  await firstItem.click();
  await expect(dropdown).toHaveCount(0);

  // /help command shows list
  await input.fill('/help');
  await input.press('Enter');
  await expect(page.locator('text=Commands: /help /note /clear')).toBeVisible();

  // /note without assistant message shows fallback
  await input.fill('/note');
  await input.press('Enter');
  const fallback = page.locator('text=No assistant message to save.');
  const saved = page.locator('text=Saved to notes.');
  await expect(fallback.or(saved)).toBeVisible({ timeout: 10000 });
});

test('Chat code block copy button writes assistant code to clipboard', async ({ page }) => {
  await installClipboardCapture(page);
  await mockBasicChatBootstrap(page);
  await mockChatSession(page, {
    id: 'chat-copy',
    title: 'HTML preview copy regression',
    updated_at: new Date().toISOString(),
    messages: [
      { role: 'user', content: 'Show me html preview' },
      {
        role: 'assistant',
        content: [
          '```html',
          '<!doctype html>',
          '<html>',
          '  <body><h1>Copy me</h1></body>',
          '</html>',
          '```',
        ].join('\n'),
      },
    ],
  });

  await page.goto('/');
  await page.getByText('HTML preview copy regression').click();

  const copyButton = page.locator('button[title="Copy code"]').first();
  await expect(copyButton).toBeVisible({ timeout: 15000 });
  await copyButton.click();

  await expect.poll(
    async () => page.evaluate(() => (window as any).__copiedText || ''),
    { timeout: 10000 },
  ).toContain('<!doctype html>');
  await expect.poll(
    async () => page.evaluate(() => (window as any).__copiedText || ''),
    { timeout: 10000 },
  ).toContain('Copy me');
});
