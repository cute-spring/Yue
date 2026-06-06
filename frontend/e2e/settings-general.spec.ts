import { expect, test } from '@playwright/test';
import { mockAgentsList, mockConfigPreferences, mockDocAccess, mockMcpTools, mockModelProviders } from './chat-test-helpers';

test('General settings save path commits updated preferences', async ({ page }) => {
  let prefsState = {
    theme: 'light',
    language: 'en',
    default_agent: 'agent-1',
    capture_suggestions_enabled: true,
    memory_suggestions_enabled: true,
    note_recall_enabled: true,
  };
  const agents = [
    { id: 'agent-1', name: 'Agent One', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o', enabled_tools: [] },
  ];

  await mockConfigPreferences(page, prefsState);
  await mockDocAccess(page, { allow_roots: [], deny_roots: [] });
  await mockAgentsList(page, agents);
  await mockMcpTools(page, []);
  await mockModelProviders(page, []);
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
  await page.locator('input[name="advanced_mode"]').check();
  await page.locator('input[name="capture_suggestions_enabled"]').uncheck();
  await page.locator('input[name="memory_suggestions_enabled"]').uncheck();
  await page.locator('input[name="note_recall_enabled"]').uncheck();

  const requestPromise = page.waitForRequest(
    (req) => req.url().includes('/api/config/preferences') && req.method() === 'POST',
  );
  await page.getByTestId('settings-save-preferences').click();

  const request = await requestPromise;
  const body = request.postDataJSON() as typeof prefsState;
  expect(body.theme).toBe('dark');
  expect(body.language).toBe('zh');
  expect(body.default_agent).toBe('agent-1');
  expect(body.advanced_mode).toBe(true);
  expect(body.capture_suggestions_enabled).toBe(false);
  expect(body.memory_suggestions_enabled).toBe(false);
  expect(body.note_recall_enabled).toBe(false);
});
