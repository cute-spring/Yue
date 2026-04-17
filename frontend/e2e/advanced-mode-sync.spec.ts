import { expect, test } from '@playwright/test';

test('advanced mode saved in settings becomes visible in chat on return', async ({ page }) => {
  const prefsState: Record<string, unknown> = {
    theme: 'light',
    language: 'en',
    default_agent: 'agent-1',
    advanced_mode: false,
    voice_input_enabled: false,
  };
  const featureFlags = {
    chat_trace_ui_enabled: false,
    chat_trace_raw_enabled: false,
  };
  const agents = [
    { id: 'agent-1', name: 'Agent One', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o', enabled_tools: [] },
  ];
  const providers = [
    {
      name: 'openai',
      configured: true,
      supports_model_refresh: false,
      available_models: ['gpt-4o-mini'],
      models: ['gpt-4o-mini'],
      model_capabilities: {},
    },
  ];

  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'POST') {
      Object.assign(prefsState, route.request().postDataJSON());
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(prefsState),
    });
  });

  await page.route('**/api/config/feature_flags', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(featureFlags),
    });
  });

  await page.route('**/api/config/doc_access', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ allow_roots: [], deny_roots: [] }),
    });
  });

  await page.route('**/api/mcp/', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.route('**/api/mcp/status', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/mcp/tools', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/models/providers', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(providers),
    });
  });

  await page.route('**/api/models/custom', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/models/test/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.route('**/api/config/llm', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });

  await page.route('**/api/agents/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agents),
    });
  });

  await page.route('**/api/chat/history', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/skills', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.goto('/settings');
  await expect(page.locator('input[name="advanced_mode"]')).not.toBeChecked();

  await page.locator('input[name="advanced_mode"]').check();
  await page.getByTestId('settings-save-preferences').click();

  await page.getByRole('link', { name: 'Chat' }).click();
  await expect(page.getByRole('button', { name: 'Open trace inspector' })).toBeVisible();
});

