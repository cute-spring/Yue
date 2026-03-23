import { expect, test } from '@playwright/test';

test('General settings save path commits updated preferences', async ({ page }) => {
  let prefsState = {
    theme: 'light',
    language: 'en',
    default_agent: 'agent-1',
  };
  const agents = [
    { id: 'agent-1', name: 'Agent One', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o', enabled_tools: [] },
  ];

  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(prefsState) });
      return;
    }
    if (route.request().method() === 'POST') {
      prefsState = route.request().postDataJSON() as typeof prefsState;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(prefsState) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/config/doc_access', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ allow_roots: [], deny_roots: [] }) });
  });
  await page.route('**/api/agents/', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(agents) });
  });
  await page.route('**/api/mcp/**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/models/providers**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/custom', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/test/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/settings');

  const setSelectValue = async (testId: string, value: string) => {
    await page.getByTestId(testId).selectOption(value);
  };

  await setSelectValue('settings-theme-select', 'dark');
  await setSelectValue('settings-language-select', 'zh');
  await setSelectValue('settings-default-agent-select', 'agent-1');

  const requestPromise = page.waitForRequest(
    (req) => req.url().includes('/api/config/preferences') && req.method() === 'POST',
  );
  await page.getByTestId('settings-save-preferences').click();

  const request = await requestPromise;
  const body = request.postDataJSON() as typeof prefsState;
  expect(body.theme).toBe('dark');
  expect(body.language).toBe('zh');
  expect(body.default_agent).toBe('agent-1');
});
