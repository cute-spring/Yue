import type { Page } from '@playwright/test';

export const installClipboardCapture = async (page: Page) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: {
        writeText: async (text: string) => {
          (window as any).__copiedText = text;
        },
      },
      configurable: true,
    });
  });
};

export const mockBasicChatBootstrap = async (page: Page) => {
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          name: 'openai',
          configured: true,
          available_models: ['gpt-4o-mini'],
          models: ['gpt-4o-mini'],
        },
      ]),
    });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/skills', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/chat/history', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
};

export const mockChatSession = async (
  page: Page,
  session: {
    id: string;
    title: string;
    updated_at: string;
    messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  },
) => {
  await page.route(`**/api/chat/${session.id}`, async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: session.id,
        agent_id: null,
        messages: session.messages,
      }),
    });
  });
  await page.route(`**/api/chat/${session.id}/events`, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route(`**/api/chat/${session.id}/actions/states`, async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/chat/history', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: session.id,
          title: session.title,
          summary: null,
          updated_at: session.updated_at,
        },
      ]),
    });
  });
};
