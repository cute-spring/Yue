import { test, expect } from '@playwright/test';

test('smart paste parses stdio config and saves disabled entry', async ({ page }) => {
  const mcpConfigs: any[] = [];
  const featureFlagsState: Record<string, boolean> = {
    chat_trace_ui_enabled: false,
    chat_trace_raw_enabled: false,
    mcp_smart_paste_enabled: true,
  };

  await page.route('**/api/config/feature_flags', async (route) => {
    if (route.request().method() === 'POST') {
      Object.assign(featureFlagsState, route.request().postDataJSON());
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(featureFlagsState),
    });
  });

  await page.route('**/api/config/preferences', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ theme: 'light', language: 'en', default_agent: 'default', advanced_mode: false }),
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
    if (route.request().method() === 'POST') {
      const payload = route.request().postDataJSON() as any[];
      mcpConfigs.push(...payload);
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mcpConfigs.length ? mcpConfigs : []) });
  });

  await page.route('**/api/mcp/reload', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'reloaded' }) });
  });

  await page.route('**/api/mcp/status**', async (route) => {
    const status = mcpConfigs.map((cfg: any) => ({
      name: cfg.name,
      enabled: cfg.enabled !== false,
      connected: false,
      transport: cfg.transport || 'stdio',
      last_error: null,
    }));
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(status) });
  });

  await page.route('**/api/mcp/tools', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/mcp/templates', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/mcp/parse', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        parse_mode: 'rule',
        results: [
          {
            name: 'filesystem',
            transport: 'stdio',
            command: 'npx',
            args: ['-y', '@anthropic/mcp-server-filesystem'],
            url: null,
            headers: null,
            env: null,
            enabled: false,
            timeout: 60.0,
            min_version: null,
            confidence: 0.95,
            hints: ['已识别为 stdio 模式'],
            warnings: [],
            missing_fields: [],
            source_index: 0,
          },
        ],
      }),
    });
  });

  await page.route('**/api/models/providers', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/api/agents', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.goto('/settings');
  await page.getByRole('button', { name: 'MCP' }).click();

  await page.getByTestId('mcp-add-menu-button').click();
  await page.getByTestId('mcp-smart-paste-button').click();

  await page.getByTestId('smart-paste-textarea').fill('npx -y @anthropic/mcp-server-filesystem');
  await page.getByTestId('smart-paste-parse-btn').click();

  await expect(page.getByTestId('smart-paste-name-input')).toHaveValue('filesystem');
  await expect(page.getByText('95%')).toBeVisible();

  await page.getByTestId('smart-paste-save-btn').click();

  await expect(page.getByText('filesystem')).toBeVisible();
});
