import { expect, test } from '@playwright/test';
import { mockBasicChatBootstrap } from './chat-test-helpers';

test('edit old question truncates subsequent history and resubmits', async ({ page }) => {
  await mockBasicChatBootstrap(page);

  const chatId = 'chat-edit-1';
  const initialMessages = [
    { role: 'user', content: 'Q1 original' },
    { role: 'assistant', content: 'A1 original' },
    { role: 'user', content: 'Q2 original' },
    { role: 'assistant', content: 'A2 original' },
  ];

  let truncateCalls = 0;
  let truncateKeepCount: number | null = null;
  let streamCalls = 0;
  let streamMessage = '';

  await page.route('**/api/chat/history', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: chatId,
          title: 'Editable chat history',
          summary: null,
          updated_at: new Date().toISOString(),
        },
      ]),
    });
  });

  await page.route(`**/api/chat/${chatId}`, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: chatId,
        agent_id: null,
        messages: initialMessages,
      }),
    });
  });

  await page.route(`**/api/chat/${chatId}/events`, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route(`**/api/chat/${chatId}/actions/states`, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route(`**/api/chat/${chatId}/truncate`, async route => {
    truncateCalls += 1;
    const body = route.request().postDataJSON() as { keep_count?: number };
    truncateKeepCount = typeof body.keep_count === 'number' ? body.keep_count : null;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.route('**/api/chat/stream', async route => {
    streamCalls += 1;
    const body = route.request().postDataJSON() as { message?: string; chat_id?: string | null };
    streamMessage = body.message ?? '';

    const stream = [
      `data: ${JSON.stringify({ chat_id: chatId })}\n\n`,
      `data: ${JSON.stringify({ content: 'A1 edited branch' })}\n\n`,
    ].join('');

    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: stream,
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini');
    localStorage.setItem('selected_provider', 'openai');
    localStorage.setItem('selected_model', 'gpt-4o-mini');
  });

  await page.goto('/', { waitUntil: 'networkidle' });
  await page.getByText('Editable chat history').first().click();

  await expect(page.getByText('Q1 original')).toBeVisible({ timeout: 15000 });
  await expect(page.getByText('Q2 original')).toBeVisible();
  await expect(page.getByText('A2 original')).toBeVisible();

  await page.getByLabel('Edit message').first().click();
  const editor = page.locator('textarea').first();
  await editor.fill('Q1 edited');
  await page.getByRole('button', { name: 'Save & Submit' }).click();

  await expect(page.getByText('Q1 edited')).toBeVisible({ timeout: 15000 });
  await expect(page.getByText('A1 edited branch')).toBeVisible({ timeout: 15000 });

  await expect(page.getByText('Q2 original')).toHaveCount(0);
  await expect(page.getByText('A2 original')).toHaveCount(0);

  expect(truncateCalls).toBe(1);
  expect(truncateKeepCount).toBe(0);
  expect(streamCalls).toBe(1);
  expect(streamMessage).toBe('Q1 edited');
});
