import { expect, test } from '@playwright/test';

test('Settings page supports create, edit, and delete flows across tabs', async ({ page }) => {
  let prefsState = {
    theme: 'light',
    language: 'en',
    default_agent: 'agent-1',
  };
  let docAccessState = {
    allow_roots: ['/workspace'],
    deny_roots: ['/workspace/private'],
  };
  let mcpServers = [
    {
      name: 'local-server',
      command: 'npx',
      args: ['-y', 'mcp-local'],
      env: {},
      enabled: true,
    },
  ];
  const mcpTools = [
    { id: 'tool-1', name: 'Read File', description: 'Read a file', server: 'local-server' },
  ];
  let providers = [
    {
      name: 'openai',
      configured: true,
      requirements: ['OPENAI_API_KEY'],
      current_model: 'gpt-4o',
      available_models: ['gpt-4o', 'gpt-4.1'],
      models: ['gpt-4o', 'gpt-4.1'],
      model_capabilities: {
        'gpt-4o': ['vision', 'reasoning'],
        'gpt-4.1': ['reasoning'],
      },
      explicit_model_capabilities: {},
    },
  ];
  let llmConfig: Record<string, any> = {
    openai_api_key: 'sk-test',
    openai_model: 'gpt-4o',
    models: {},
    openai_enabled_models: ['gpt-4o'],
    openai_enabled_models_mode: 'allowlist',
    proxy_url: '',
    no_proxy: '',
    ssl_cert_file: '',
    llm_request_timeout: 60,
    meta_use_runtime_model_for_title: false,
  };
  let customModels = [
    {
      name: 'baseline-custom',
      base_url: 'https://custom.example.com/v1',
      api_key: 'secret',
      model: 'x-large',
      capabilities: ['vision'],
    },
  ];
  const agents = [
    { id: 'agent-1', name: 'Agent One', system_prompt: 'sys', provider: 'openai', model: 'gpt-4o', enabled_tools: [] },
  ];

  await page.route('**/api/mcp/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mcpServers),
      });
      return;
    }
    if (route.request().method() === 'POST') {
      mcpServers = route.request().postDataJSON() as any[];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mcpServers),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/mcp/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(
        mcpServers.map((server) => ({
          name: server.name,
          enabled: server.enabled,
          connected: server.enabled,
          transport: 'stdio',
        })),
      ),
    });
  });
  await page.route('**/api/mcp/tools', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mcpTools),
    });
  });
  await page.route('**/api/mcp/reload', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/mcp/**', async (route) => {
    if (route.request().method() === 'DELETE') {
      const url = new URL(route.request().url());
      const name = decodeURIComponent(url.pathname.split('/').pop() || '');
      mcpServers = mcpServers.filter((server) => server.name !== name);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }
    await route.fallback();
  });

  await page.route('**/api/models/providers**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(providers),
    });
  });
  await page.route('**/api/config/llm', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(llmConfig),
      });
      return;
    }
    if (route.request().method() === 'POST') {
      llmConfig = route.request().postDataJSON() as Record<string, any>;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(llmConfig),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/models/custom', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(customModels),
      });
      return;
    }
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as any;
      customModels = customModels.filter((model) => model.name !== body.name).concat(body);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/models/custom/**', async (route) => {
    if (route.request().method() === 'DELETE') {
      const url = new URL(route.request().url());
      const name = decodeURIComponent(url.pathname.split('/').pop() || '');
      customModels = customModels.filter((model) => model.name !== name);
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/models/test/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.route('**/api/config/preferences', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(prefsState),
      });
      return;
    }
    if (route.request().method() === 'POST') {
      prefsState = route.request().postDataJSON() as typeof prefsState;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(prefsState),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/config/doc_access', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(docAccessState),
      });
      return;
    }
    if (route.request().method() === 'POST') {
      docAccessState = route.request().postDataJSON() as typeof docAccessState;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(docAccessState),
      });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/agents/', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agents),
    });
  });

  await page.goto('/settings');

  await expect(page.getByRole('button', { name: 'General' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'MCP' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Models' })).toBeVisible();

  await page.getByRole('button', { name: 'MCP' }).click();
  await page.getByTestId('mcp-add-menu-button').click();
  await page.getByTestId('mcp-add-manual-button').click();
  await page.getByTestId('mcp-manual-textarea').fill(
    JSON.stringify({
      mcpServers: {
        added_server: {
          command: 'npx',
          args: ['-y', 'mcp-added'],
        },
      },
    }),
  );
  await page.getByRole('button', { name: 'Confirm' }).last().click();
  await expect(page.getByText('Successfully added 1 MCP server(s)')).toBeVisible();
  await expect(page.getByText('added_server')).toBeVisible();

  await page.getByRole('button', { name: /Delete MCP Server/i }).last().click();
  await page.getByRole('button', { name: 'Delete' }).last().click();
  await expect(page.getByText('added_server')).toHaveCount(0, { timeout: 10000 });

  await page.getByRole('button', { name: 'Models' }).click();
  await page.getByRole('button', { name: 'Edit' }).click();
  await page.getByTestId('llm-provider-edit-modal').getByTestId('llm-openai-model-input').fill('gpt-4.1');
  await page.getByTestId('llm-provider-edit-modal').getByTestId('llm-provider-save-button').click();
  await expect.poll(() => llmConfig.openai_model).toBe('gpt-4.1');
  await expect(page.getByText('baseline-custom')).toBeVisible();

  await page.getByTestId('llm-add-custom-button').click();
  await page.getByTestId('llm-custom-model-modal').getByTestId('llm-custom-name-input').fill('browser-custom');
  await page.getByTestId('llm-custom-model-modal').getByTestId('llm-custom-model-input').fill('gpt-4o-mini');
  await page.getByTestId('llm-custom-model-modal').getByTestId('llm-custom-base-url-input').fill('https://custom.browser/v1');
  await page.getByTestId('llm-custom-model-modal').getByTestId('llm-custom-api-key-input').fill('sk-browser');
  await page.getByTestId('llm-custom-model-modal').getByTestId('llm-custom-save-button').click();
  await expect(page.getByText('browser-custom')).toBeVisible();
  await expect.poll(() => customModels.some((model) => model.name === 'browser-custom')).toBeTruthy();

  await page.getByRole('button', { name: 'Delete' }).last().click();
  await page.getByRole('button', { name: 'Delete' }).last().click();
  await expect(page.getByText('browser-custom')).toHaveCount(0, { timeout: 10000 });
});
