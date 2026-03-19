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
  await page.getByRole('button', { name: /Agent With Skills Directly/i }).click();
  await page.getByRole('button', { name: 'Manual' }).click();
  await page.getByLabel(/planner/i).check();
  await page.getByRole('button', { name: /^Create Agent$/ }).last().click();
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

test('Agent form saves agent_kind and skill_groups with echo', async ({ page }) => {
  let createdAgent: any = null;
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
  await page.route('**/api/skill-groups/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'group-backend', name: 'backend', description: 'backend', skill_refs: ['backend-api-debugger:1.0.0'] }
      ])
    });
  });
  await page.route('**/api/agents/', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(createdAgent ? [createdAgent] : [])
      });
      return;
    }
    const body = route.request().postDataJSON() as any;
    expect(body.agent_kind).toBe('universal');
    expect(body.skill_groups).toEqual(['group-backend']);
    createdAgent = {
      id: 'agent-grouped',
      name: body.name,
      system_prompt: body.system_prompt,
      provider: body.provider,
      model: body.model,
      enabled_tools: body.enabled_tools || [],
      skill_mode: body.skill_mode,
      visible_skills: body.visible_skills || [],
      agent_kind: body.agent_kind,
      skill_groups: body.skill_groups || [],
      extra_visible_skills: body.extra_visible_skills || []
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(createdAgent)
    });
  });

  await page.goto('/agents');
  await page.getByRole('button', { name: 'Create Agent' }).click();
  await page.getByPlaceholder('e.g. Coding Assistant').fill('Grouped Agent');
  await page.getByPlaceholder('You are a helpful assistant...').fill('Grouped mode test');
  await page.getByRole('button', { name: /Agent With Skill Groups/i }).click();
  await page.getByRole('button', { name: 'Auto' }).click();
  await page.getByLabel(/backend/i).check();
  await page.getByRole('button', { name: /^Create Agent$/ }).last().click();
  await expect(page.getByRole('heading', { name: 'Grouped Agent' })).toBeVisible();
});

test('Agent form applies default skill prompt for skill templates', async ({ page }) => {
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
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'planner', version: '1.0.0', description: 'Planning skill' }])
    });
  });
  await page.route('**/api/skill-groups/**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/agents/', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      return;
    }
    const body = route.request().postDataJSON() as any;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'agent-default-prompt',
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
  await page.getByRole('button', { name: /Agent With Skills Directly/i }).click();
  await expect(page.getByPlaceholder('You are a helpful assistant...')).toHaveValue(/capability-aware assistant/i);
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
  await page.route('**/api/skills', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { name: 'planner', version: '1.0.0', description: 'Planning', source_layer: 'user' },
        { name: 'coder', version: '2.1.0', description: 'Coding', source_layer: 'workspace' }
      ])
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
  await expect(page.locator('select option').nth(1)).toContainText('[user]');
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

test('Chat manual mode prefers resolved_visible_skills for selector', async ({ page }) => {
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
  await page.route('**/api/skills', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ name: 'planner', version: '1.0.0', description: 'Planning', source_layer: 'user' }])
    });
  });
  await page.route('**/api/agents/', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'agent-manual-resolved',
          name: 'Manual Resolved Agent',
          system_prompt: 'Manual mode',
          provider: 'openai',
          model: 'gpt-4o',
          enabled_tools: [],
          skill_mode: 'manual',
          visible_skills: [],
          resolved_visible_skills: ['planner:1.0.0']
        }
      ])
    });
  });
  await page.route('**/api/chat/stream', async route => {
    const body = route.request().postDataJSON() as any;
    expect(body.requested_skill).toBe('planner:1.0.0');
    const stream = [
      `data: ${JSON.stringify({ chat_id: 'chat-resolved' })}\n\n`,
      `data: ${JSON.stringify({ event: 'skill_selected', name: 'planner', version: '1.0.0' })}\n\n`,
      `data: ${JSON.stringify({ content: 'Resolved skill applied.' })}\n\n`
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
  await page.getByRole('button', { name: /Manual Resolved Agent/i }).first().click();
  await expect(page.locator('select option')).toHaveCount(2);
  await page.locator('select').selectOption('planner:1.0.0');
  await page.getByRole('button', { name: /Select Model/i }).click();
  await page.getByRole('button', { name: /^gpt-4o$/i }).click();
  await input.fill('Use resolved skill');
  await input.press('Enter');
  await expect(page.getByText('Active: planner@1.0.0')).toBeVisible();
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

test('Skill Groups management page supports list/create/update/delete', async ({ page }) => {
  let groups = [
    {
      id: 'group-1',
      name: 'Backend Group',
      description: 'backend defaults',
      skill_refs: ['backend-api-debugger:1.0.0']
    }
  ];

  await page.route('**/api/skill-groups/**', async route => {
    const method = route.request().method();
    const url = route.request().url();
    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(groups)
      });
      return;
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON() as any;
      const created = {
        id: 'group-2',
        name: body.name,
        description: body.description,
        skill_refs: body.skill_refs || []
      };
      groups = [...groups, created];
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(created)
      });
      return;
    }
    if (method === 'PUT') {
      const body = route.request().postDataJSON() as any;
      const targetId = url.split('/').pop() || '';
      groups = groups.map(item => item.id === targetId ? { ...item, ...body } : item);
      const updated = groups.find(item => item.id === targetId);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(updated)
      });
      return;
    }
    if (method === 'DELETE') {
      const targetId = url.split('/').pop() || '';
      groups = groups.filter(item => item.id !== targetId);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' })
      });
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/skills/**', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { name: 'release-test-planner', version: '1.0.0', description: 'planner' },
        { name: 'backend-api-debugger', version: '1.0.0', description: 'debugger' }
      ])
    });
  });

  await page.goto('/skill-groups');
  await expect(page.getByRole('heading', { name: 'Skill Groups' })).toBeVisible();
  await expect(page.getByText('Skill list')).toBeVisible();
  await expect(page.getByText('Backend Group')).toBeVisible();

  await page.getByPlaceholder('e.g. Backend Defaults').fill('Frontend Group');
  await page.getByPlaceholder('Describe this skill group').fill('frontend defaults');
  const searchInput = page.getByPlaceholder('Search skill list to add');
  await searchInput.fill('release');
  await page.locator('label:has-text("release-test-planner") input[type="checkbox"]').first().check();
  await expect(page.locator('form').getByRole('button', { name: 'release-test-planner:1.0.0' })).toBeVisible();
  await page.locator('form').getByRole('button', { name: /^Create Group$/ }).click();
  await expect(page.getByText('Frontend Group')).toBeVisible();

  await page.getByRole('button', { name: /^Edit$/ }).first().click();
  await page.getByPlaceholder('e.g. Backend Defaults').fill('Backend Group Updated');
  await page.getByRole('button', { name: /^Save Changes$/ }).click();
  await expect(page.getByText('Backend Group Updated')).toBeVisible();

  await page.getByRole('button', { name: /^Delete$/ }).nth(1).click();
  await expect(page.getByRole('heading', { name: 'Delete Skill Group' })).toBeVisible();
  await page.getByRole('button', { name: /^Delete$/ }).last().click();
  await expect(page.getByText('Frontend Group')).toHaveCount(0);
});
