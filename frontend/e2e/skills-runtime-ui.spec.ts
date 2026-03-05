import { test, expect } from '@playwright/test';

test('Agents form supports skill_mode and visible_skills payload', async ({ page }) => {
  await page.route('**/api/mcp/tools', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'openai', supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }])
    });
  });
  await page.route('**/api/config/doc_access', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ allow_roots: [], deny_roots: [] })
    });
  });
  await page.route('**/api/skills', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { name: 'planner', version: '1.0.0', description: 'Planning skill' },
        { name: 'coder', version: '2.1.0', description: 'Coding skill' }
      ])
    });
  });
  await page.route('**/api/agents/', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
      return;
    }
    const body = route.request().postDataJSON() as any;
    expect(body.skill_mode).toBe('manual');
    expect(body.visible_skills).toEqual(expect.arrayContaining(['planner:1.0.0']));
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'agent-manual',
        name: body.name,
        system_prompt: body.system_prompt,
        provider: body.provider,
        model: body.model,
        enabled_tools: body.enabled_tools || [],
        skill_mode: body.skill_mode,
        visible_skills: body.visible_skills || []
      })
    });
  });

  await page.goto('/agents');
  await page.getByRole('button', { name: 'Create Agent' }).click();
  await page.getByPlaceholder('e.g. Coding Assistant').fill('Manual Skill Agent');
  await page.getByPlaceholder('You are a helpful assistant...').fill('Manual mode test');
  await page.getByRole('button', { name: 'Manual' }).click();
  await page.getByLabel(/planner/i).check();
  await page.locator('form button[type="submit"]').click();
});

test('Agents list shows skill badges only for manual and auto modes', async ({ page }) => {
  await page.route('**/api/mcp/tools', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'openai', supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }])
    });
  });
  await page.route('**/api/config/doc_access', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ allow_roots: [], deny_roots: [] }) });
  });
  await page.route('**/api/skills', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'agent-off',
          name: 'Off Agent',
          system_prompt: 'Off',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'off',
          visible_skills: []
        },
        {
          id: 'agent-manual',
          name: 'Manual Agent',
          system_prompt: 'Manual',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'manual',
          visible_skills: ['planner:1.0.0']
        },
        {
          id: 'agent-auto',
          name: 'Auto Agent',
          system_prompt: 'Auto',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'auto',
          visible_skills: ['planner:1.0.0', 'coder:2.1.0']
        }
      ])
    });
  });

  await page.goto('/agents');
  await expect(page.getByRole('heading', { name: 'Off Agent' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Manual Agent' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Auto Agent' })).toBeVisible();
  await expect(page.getByText('manual').first()).toBeVisible();
  await expect(page.getByText('auto').first()).toBeVisible();
});

test('Chat sends requested_skill and renders active skill indicator', async ({ page }) => {
  await page.route('**/api/chat/history', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'openai', supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }])
    });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'agent-manual',
          name: 'Manual Skill Agent',
          system_prompt: 'Manual mode',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'manual',
          visible_skills: ['planner:1.0.0', 'coder:2.1.0']
        }
      ])
    });
  });
  await page.route('**/api/chat/stream', async route => {
    const body = route.request().postDataJSON() as any;
    expect(body.requested_skill).toBe('planner:1.0.0');
    const stream = [
      `data: ${JSON.stringify({ chat_id: 'chat-1' })}\n\n`,
      `data: ${JSON.stringify({ event: 'skill_selected', name: 'planner', version: '1.0.0' })}\n\n`,
      `data: ${JSON.stringify({ content: 'Skill applied.' })}\n\n`
    ].join('');
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: stream
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await input.fill('@');
  await page.getByRole('button', { name: /Manual Skill Agent/i }).first().click();

  await page.locator('select').selectOption('planner:1.0.0');
  await page.getByRole('button', { name: /Select Model/i }).click();
  await page.getByRole('button', { name: /^gpt-4o$/i }).click();
  await input.fill('Use planning flow');
  await input.press('Enter');

  await expect(page.getByText('Active: planner@1.0.0')).toBeVisible();
});

test('Chat manual mode falls back cleanly for invalid requested skill', async ({ page }) => {
  await page.route('**/api/chat/history', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'openai', supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }])
    });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'agent-manual',
          name: 'Manual Skill Agent',
          system_prompt: 'Manual mode',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'manual',
          visible_skills: ['planner:1.0.0']
        }
      ])
    });
  });
  await page.route('**/api/chat/stream', async route => {
    const body = route.request().postDataJSON() as any;
    expect(body.requested_skill).toBe('missing:9.9.9');
    const stream = [
      `data: ${JSON.stringify({ chat_id: 'chat-fallback' })}\n\n`,
      `data: ${JSON.stringify({ content: 'Fallback to legacy completed.' })}\n\n`
    ].join('');
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: stream
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await input.fill('@');
  await page.getByRole('button', { name: /Manual Skill Agent/i }).first().click();
  await page.locator('select').selectOption({ label: 'No skill selected' });
  await page.evaluate(() => {
    const select = document.querySelector('select') as HTMLSelectElement | null;
    if (select) {
      const option = document.createElement('option');
      option.value = 'missing:9.9.9';
      option.text = 'missing:9.9.9';
      select.add(option);
      select.value = 'missing:9.9.9';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  await page.getByRole('button', { name: /Select Model/i }).click();
  await page.getByRole('button', { name: /^gpt-4o$/i }).click();
  await input.fill('Try missing skill');
  await input.press('Enter');

  await expect(page.getByText('Fallback to legacy completed.')).toBeVisible();
  await expect(page.getByText(/Active:/)).toHaveCount(0);
});

test('Allowlist agent exposes skill selector while non-allowlist agent does not', async ({ page }) => {
  await page.route('**/api/chat/history', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/models/providers**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'openai', supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }])
    });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'agent-off',
          name: 'Legacy Agent',
          system_prompt: 'Legacy',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'off',
          visible_skills: []
        },
        {
          id: 'agent-manual',
          name: 'Allowlist Agent',
          system_prompt: 'Manual',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'manual',
          visible_skills: ['planner:1.0.0']
        }
      ])
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await input.fill('@');
  await page.getByRole('button', { name: /Legacy Agent/i }).first().click();
  await expect(page.locator('select')).toHaveCount(0);

  await input.fill('@');
  await page.getByRole('button', { name: /Allowlist Agent/i }).first().click();
  await expect(page.locator('select')).toHaveCount(1);
  await expect(page.locator('select option')).toHaveCount(2);
});
