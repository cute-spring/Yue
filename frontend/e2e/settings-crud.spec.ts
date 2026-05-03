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
      transport: 'stdio',
      command: 'npx',
      args: ['-y', 'mcp-local'],
      env: {},
      enabled: true,
    },
  ];
  const mcpTools = [
    { id: 'tool-1', name: 'Read File', description: 'Read a file', server: 'local-server' },
  ];
  const mcpTemplates = [
    {
      id: 'jira-company',
      name: 'Jira MCP',
      description: 'Template for Jira Cloud or internal Jira Server/Data Center. Use this when your company has its own Jira host or MCP wrapper.',
      provider: 'jira',
      deployment: 'mixed',
      fields: [
        { key: 'serverName', label: 'Server Name', type: 'text', required: true, options: [], default_value: 'company-jira' },
        { key: 'transport', label: 'Transport', type: 'select', required: true, options: ['stdio', 'streamable_http'], default_value: 'stdio', help_text: 'Use stdio for local process servers, or streamable_http for remote MCP endpoints.' },
        { key: 'deployment', label: 'Deployment', type: 'select', required: true, options: ['cloud', 'self_hosted'], default_value: 'self_hosted', help_text: 'Choose the style that best matches your Jira environment.' },
        { key: 'command', label: 'Command', type: 'text', required: true, options: [], default_value: 'npx' },
        { key: 'argsJson', label: 'Args (JSON Array)', type: 'json', required: true, options: [], default_value: '["-y", "your-company-jira-mcp-package"]', help_text: 'Replace the placeholder package or executable with the real Jira MCP implementation your company uses.' },
        { key: 'baseUrl', label: 'Jira Base URL', type: 'text', required: true, options: [], default_value: 'https://jira.company.internal' },
        { key: 'baseUrlEnvKey', label: 'Base URL Env Key', type: 'text', required: true, options: [], default_value: 'JIRA_BASE_URL', help_text: 'Use the exact env var name expected by your Jira MCP server.' },
        { key: 'username', label: 'Username / Email (Optional)', type: 'text', required: false, options: [], default_value: '' },
        { key: 'usernameEnvKey', label: 'Username Env Key', type: 'text', required: false, options: [], default_value: 'JIRA_USERNAME', help_text: 'Leave the username blank if your MCP server authenticates with only a personal token.' },
        { key: 'secretEnvVar', label: 'Host Personal Token Env Var', type: 'text', required: true, options: [], default_value: 'JIRA_TOKEN', help_text: 'The rendered config stores ${ENV_NAME} so the personal token stays outside Yue.' },
        { key: 'tokenEnvKey', label: 'Personal Token Env Key For MCP Server', type: 'text', required: true, options: [], default_value: 'JIRA_TOKEN', help_text: 'Use the exact personal-token env var name expected by your Jira MCP server.' },
        { key: 'extraEnvJson', label: 'Extra Env (JSON Object)', type: 'json', required: false, options: [], default_value: '{}', help_text: 'Optional extra env vars such as project scopes, read-only flags, PAT mode, or SSL flags.' },
        { key: 'url', label: 'Streamable HTTP URL', type: 'text', required: false, options: [], default_value: '', help_text: 'Required when transport is streamable_http.' },
        { key: 'headersJson', label: 'Headers (JSON Object)', type: 'json', required: false, options: [], default_value: '{"Authorization":"${JIRA_TOKEN}"}', help_text: 'Optional request headers for streamable_http. Use placeholders like ${ENV_NAME} for secrets.' },
      ],
    },
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
          transport: server.transport || 'stdio',
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
  await page.route('**/api/mcp/templates', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mcpTemplates),
    });
  });
  await page.route('**/api/mcp/validate', async (route) => {
    const body = route.request().postDataJSON() as any;
    const values = body.values || {};
    if (values.transport === 'streamable_http') {
      const rendered = {
        name: values.serverName || 'company-jira-http',
        transport: 'streamable_http',
        url: values.url || 'https://mcp.example.com/stream',
        enabled: true,
        headers: JSON.parse(values.headersJson || '{}'),
      };
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          rendered_config: rendered,
          warnings: ['Set JIRA_TOKEN in the host environment before reload.'],
        }),
      });
      return;
    }
    const env: Record<string, string> = {
      [values.baseUrlEnvKey || 'JIRA_BASE_URL']: values.baseUrl || '',
      [values.tokenEnvKey || 'JIRA_TOKEN']: `\${${values.secretEnvVar || 'JIRA_TOKEN'}}`,
    };
    if (values.username) {
      env[values.usernameEnvKey || 'JIRA_USERNAME'] = values.username;
    }
    const rendered = {
      name: values.serverName || 'company-jira',
      command: values.command || 'npx',
      args: JSON.parse(values.argsJson || '[]'),
      transport: 'stdio',
      enabled: true,
      env,
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        rendered_config: rendered,
        warnings: ['Set JIRA_TOKEN in the host environment before reload.'],
      }),
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

  await page.getByTestId('mcp-add-menu-button').click();
  await page.getByRole('button', { name: 'Add from Marketplace' }).click();
  await expect(page.getByText('Recommended onboarding defaults')).toBeVisible();
  await expect(
    page.getByText(
      'Default to base URL plus personal token; username/email should stay optional unless your company MCP requires it.',
    ),
  ).toBeVisible();
  await expect(
    page.getByText('Keep the server disabled until the real internal Jira MCP package or executable is confirmed.'),
  ).toBeVisible();
  await page.getByLabel('Server Name *').fill('corp-jira');
  await page.getByLabel('Args (JSON Array) *').fill('["-y","corp-jira-mcp"]');
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByText('Rendered MCP Config Preview')).toBeVisible();
  await page.getByRole('button', { name: 'Install' }).click();
  await expect(page.getByText('Installed MCP server "corp-jira"')).toBeVisible();
  await expect(page.getByText('corp-jira', { exact: true })).toBeVisible();
  await expect(page.getByText('stdio')).toBeVisible();

  await page.getByTestId('mcp-add-menu-button').click();
  await page.getByRole('button', { name: 'Add from Marketplace' }).click();
  await page.getByLabel('Transport *').selectOption('streamable_http');
  await expect(
    page.getByText('Use your company MCP endpoint URL and keep auth in headers as ${ENV_NAME} placeholders.'),
  ).toBeVisible();
  await page.getByLabel('Server Name *').fill('corp-jira-http');
  await page.getByLabel('Streamable HTTP URL').fill('https://mcp.company.internal/stream');
  await page.getByRole('button', { name: 'Validate' }).click();
  await expect(page.getByText('"transport": "streamable_http"')).toBeVisible();
  await expect(page.getByText('"url": "https://mcp.company.internal/stream"')).toBeVisible();
  await page.getByRole('button', { name: 'Install' }).click();
  await expect(page.getByText('Installed MCP server "corp-jira-http"')).toBeVisible();
  await expect(page.getByText('corp-jira-http', { exact: true })).toBeVisible();
  await expect(page.getByText('streamable_http')).toBeVisible();

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
