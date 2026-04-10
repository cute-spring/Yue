import type { Page } from '@playwright/test';

export const defaultChatProviders = [
  {
    name: 'openai',
    configured: true,
    available_models: ['gpt-4o-mini'],
    models: ['gpt-4o-mini'],
  },
];

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
      body: JSON.stringify(defaultChatProviders),
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

export const mockChatBootstrap = async (
  page: Page,
  {
    prefs,
    agents,
    providers = defaultChatProviders,
    tokenResponse,
  }: {
    prefs: Record<string, unknown>;
    agents: Array<Record<string, unknown>>;
    providers?: Array<Record<string, unknown>>;
    tokenResponse?: { status: number; body: Record<string, unknown> | string };
  },
) => {
  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(prefs),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(prefs) });
  });
  await page.route('**/api/agents/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agents),
    });
  });
  await page.route('**/api/models/providers**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(providers),
    });
  });
  await page.route('**/api/chat/history', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await page.route('**/api/skills', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
  });
  await page.route('**/api/chat/stream', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        'event: content.delta',
        `data: ${JSON.stringify({ delta: 'ok' })}`,
        '',
        'event: content.done',
        `data: ${JSON.stringify({})}`,
        '',
      ].join('\n'),
    });
  });
  await page.route('**/api/speech/stt/token**', async (route) => {
    if (!tokenResponse) {
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'missing mock' }) });
      return;
    }
    await route.fulfill({
      status: tokenResponse.status,
      contentType: typeof tokenResponse.body === 'string' ? 'text/plain' : 'application/json',
      body: typeof tokenResponse.body === 'string' ? tokenResponse.body : JSON.stringify(tokenResponse.body),
    });
  });
};

export const mockConfigPreferences = async (page: Page, prefs: Record<string, unknown>) => {
  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(prefs),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(prefs) });
  });
};

export const mockDocAccess = async (
  page: Page,
  docAccess: { allow_roots: string[]; deny_roots: string[] },
) => {
  await page.route('**/api/config/doc_access', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(docAccess),
    });
  });
};

export const mockAgentsList = async (page: Page, agents: Array<Record<string, unknown>>) => {
  await page.route('**/api/agents/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agents),
    });
  });
};

export const mockModelProviders = async (page: Page, providers: Array<Record<string, unknown>>) => {
  await page.route('**/api/models/providers**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(providers),
    });
  });
};

export const mockSkills = async (page: Page, skills: Array<Record<string, unknown>>) => {
  await page.route('**/api/skills', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(skills),
    });
  });
};

export const mockMcpTools = async (page: Page, tools: Array<Record<string, unknown>>) => {
  await page.route('**/api/mcp/tools', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(tools),
    });
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
