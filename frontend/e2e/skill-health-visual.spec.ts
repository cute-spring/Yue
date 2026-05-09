import { test, expect } from '@playwright/test';

const mockPreflightRecords = [
  {
    skill_name: 'ok-skill',
    skill_version: '1.0.0',
    skill_ref: 'ok-skill:1.0.0',
    source_path: '/tmp/ok-skill',
    source_layer: 'workspace',
    status: 'available',
    issues: [],
    warnings: [],
    suggestions: ['Keep this skill updated.'],
    status_message: 'Ready to mount.',
    next_action: 'Mount this skill to the default agent.',
    visible_in_default_agent: false,
    setup_capable: false,
    setup_required: false,
    trust_status: 'untrusted',
    setup_status: 'not_needed',
    setup_supported_runtimes: [],
    setup_status_message: 'No trusted setup contract declared.',
    setup_next_action: 'Use Mount if preflight is available.',
    checked_at: '2026-04-25T00:00:00Z',
  },
  {
    skill_name: 'fix-skill',
    skill_version: '1.0.0',
    skill_ref: 'fix-skill:1.0.0',
    source_path: '/tmp/fix-skill',
    source_layer: 'user',
    status: 'needs_fix',
    issues: ['missing binary: python3'],
    warnings: ['Outdated schema version.'],
    suggestions: ['Install python3.'],
    status_message: 'missing binary',
    next_action: 'Resolve listed issues, then rerun preflight.',
    visible_in_default_agent: false,
    setup_capable: true,
    setup_required: true,
    trust_status: 'untrusted',
    setup_status: 'available',
    setup_supported_runtimes: ['python'],
    setup_runtime: 'python',
    setup_status_message: 'Setup requires explicit trust.',
    setup_next_action: 'Trust this skill, then run setup.',
    last_setup_commands: ['python -m venv .yue/python/venv'],
    checked_at: '2026-04-25T00:00:00Z',
  },
  {
    skill_name: 'retry-skill',
    skill_version: '2.0.0',
    skill_ref: 'retry-skill:2.0.0',
    source_path: '/tmp/retry-skill',
    source_layer: 'workspace',
    status: 'needs_fix',
    issues: [],
    warnings: [],
    suggestions: ['Check network connectivity.'],
    status_message: 'Ready to mount.',
    next_action: 'Mount this skill to the default agent.',
    visible_in_default_agent: false,
    setup_capable: true,
    setup_required: true,
    trust_status: 'trusted',
    setup_status: 'failed',
    setup_supported_runtimes: ['node'],
    setup_runtime: 'node',
    setup_status_message: 'pip install failed',
    setup_next_action: 'Fix setup issues, then rerun setup.',
    setup_last_error: 'pip install failed',
    last_setup_commands: ['npm install --prefix .yue/node'],
    setup_audit_summary: { total: 1, succeeded: 0, failed: 1, total_duration_ms: 2450 },
    checked_at: '2026-04-25T00:00:00Z',
  },
  {
    skill_name: 'excalidraw-diagram-generator',
    skill_version: '1.0.0',
    skill_ref: 'excalidraw-diagram-generator:1.0.0',
    source_path: '/tmp/excalidraw',
    source_layer: 'workspace',
    status: 'available',
    issues: [],
    warnings: [],
    suggestions: [],
    status_message: 'Ready to mount.',
    next_action: 'Mount this skill to the default agent.',
    visible_in_default_agent: true,
    setup_capable: false,
    setup_required: false,
    trust_status: 'untrusted',
    setup_status: 'not_needed',
    setup_supported_runtimes: [],
    excalidraw_health: {
      effective_level: 'L2',
      levels: ['L1', 'L2', 'L3'],
      blockers: [
        {
          code: 'script_dependency_missing',
          title: 'Script dependency missing',
          detail: 'Missing Python packages.',
          fix_command: 'python scripts/install-deps.py',
          fix_path: '/tmp/excalidraw/scripts',
        },
      ],
    },
    checked_at: '2026-04-25T00:00:00Z',
  },
  {
    skill_name: 'setup-done-skill',
    skill_version: '1.0.0',
    skill_ref: 'setup-done-skill:1.0.0',
    source_path: '/tmp/setup-done',
    source_layer: 'workspace',
    status: 'available',
    issues: [],
    warnings: [],
    suggestions: [],
    status_message: 'Ready to mount.',
    next_action: 'Mount this skill to the default agent.',
    visible_in_default_agent: true,
    setup_capable: true,
    setup_required: false,
    trust_status: 'trusted',
    setup_status: 'succeeded',
    setup_supported_runtimes: ['python'],
    setup_runtime: 'python',
    setup_status_message: 'Trusted setup completed.',
    setup_next_action: 'Setup is complete.',
    setup_audit_summary: { total: 1, succeeded: 1, failed: 0, total_duration_ms: 1200 },
    checked_at: '2026-04-25T00:00:00Z',
  },
];

async function mockSkillPreflightApi(page: any, overrides: any = {}) {
  await page.route('**/api/skill-preflight', async (route: any) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: mockPreflightRecords }),
      });
      return;
    }
    await route.continue();
  });

  await page.route('**/api/skill-preflight/rescan', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        summary: { total: 5, available: 3, needs_fix: 2, unavailable: 0 },
        items: mockPreflightRecords,
      }),
    });
  });
}

test.describe('SkillHealth visual regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/mcp/tools', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/models/providers**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ name: 'openai', configured: true, supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] }]),
      });
    });
    await page.route('**/api/config/doc_access', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ allow_roots: [], deny_roots: [] }) });
    });
    await page.route('**/api/skills', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/api/agents/', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await mockSkillPreflightApi(page);
  });

  test('renders page title and filter controls', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByRole('heading', { name: 'Skill Health' })).toBeVisible();
    await expect(page.getByPlaceholder('Search by skill, issue, suggestion')).toBeVisible();
    await expect(page.locator('select').nth(0)).toHaveValue('all');
    await expect(page.locator('select').nth(1)).toHaveValue('all');
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Rescan' })).toBeVisible();
  });

  test('shows available and non-available sections with correct counts', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText(/可用 \(3\)/)).toBeVisible();
    await expect(page.getByText(/不可用（含原因） \(2\)/)).toBeVisible();
    await expect(page.getByText('5 visible')).toBeVisible();
  });

  test('displays record details for an available skill', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('ok-skill:1.0.0')).toBeVisible();
    await expect(page.getByText('Layer: workspace')).toBeVisible();
    await expect(page.getByText('Suggestions: Keep this skill updated.')).toBeVisible();
  });

  test('displays record details for a needs_fix skill with issues', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('fix-skill:1.0.0')).toBeVisible();
    await expect(page.getByText('Issues: missing binary: python3')).toBeVisible();
    await expect(page.getByText('Suggestions: Install python3.')).toBeVisible();
    await expect(page.getByText('Warnings: Outdated schema version.')).toBeVisible();
  });

  test('mount button is enabled for available and disabled for needs_fix', async ({ page }) => {
    await page.goto('/skill-health');
    const mountButtons = page.getByRole('button', { name: 'Mount' });
    await expect(mountButtons.first()).toBeEnabled();
    const needsFixButton = page.getByRole('button', { name: 'Needs Fix' });
    await expect(needsFixButton.nth(0)).toBeDisabled();
  });

  test('shows Trust & Setup button for setup-capable untrusted skill', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByRole('button', { name: 'Trust & Setup' }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: 'Trust & Setup' }).first()).toBeEnabled();
  });

  test('shows Retry Setup button for trusted skill with failed setup', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByRole('button', { name: 'Retry Setup' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry Setup' })).toBeEnabled();
  });

  test('shows Setup Complete (disabled) for succeeded setup', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByRole('button', { name: 'Setup Complete' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Setup Complete' })).toBeDisabled();
  });

  test('shows Setup Unsupported (disabled) for non-setup-capable skills', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByRole('button', { name: 'Setup Unsupported' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Setup Unsupported' })).toBeDisabled();
  });

  test('displays setup status messages correctly', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Setup status: No trusted setup contract declared.')).toBeVisible();
    await expect(page.getByText('Setup status: Setup requires explicit trust.')).toBeVisible();
    await expect(page.getByText('Setup status: pip install failed')).toBeVisible();
    await expect(page.getByText('Setup status: Trusted setup completed.')).toBeVisible();
  });

  test('displays trust status messages', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Trusted: No').first()).toBeVisible();
    await expect(page.getByText('Trusted: Yes').first()).toBeVisible();
  });

  test('displays last failure message for failed setup', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Last failure: pip install failed')).toBeVisible();
  });

  test('displays setup support messages', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Trusted setup support: Not supported.').first()).toBeVisible();
    await expect(page.getByText('Trusted setup support: Supported (python).').first()).toBeVisible();
    await expect(page.getByText('Trusted setup support: Supported (node).')).toBeVisible();
  });

  test('displays excalidraw health section with blockers and fix commands', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Excalidraw Level: L2 (L1/L2/L3)')).toBeVisible();
    await expect(page.getByText('Blockers: Script dependency missing')).toBeVisible();
    await expect(page.getByText('Fix Commands: python scripts/install-deps.py')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Copy Fix Commands' })).toBeVisible();
  });

  test('visibility label shows correctly', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Hidden in default agent').first()).toBeVisible();
    await expect(page.getByText('Visible in default agent').first()).toBeVisible();
  });

  test('status filter changes visible records', async ({ page }) => {
    await page.goto('/skill-health');
    await page.locator('select').nth(0).selectOption('needs_fix');
    await expect(page.getByText('ok-skill:1.0.0')).not.toBeVisible();
    await expect(page.getByText('fix-skill:1.0.0')).toBeVisible();
    await expect(page.getByText('retry-skill:2.0.0')).toBeVisible();
  });

  test('layer filter shows available layers and filters records', async ({ page }) => {
    await page.goto('/skill-health');
    await page.locator('select').nth(1).selectOption('user');
    await expect(page.getByText('fix-skill:1.0.0')).toBeVisible();
    await expect(page.getByText('ok-skill:1.0.0')).not.toBeVisible();
  });

  test('search input filters records by skill name', async ({ page }) => {
    await page.goto('/skill-health');
    await page.getByPlaceholder('Search by skill, issue, suggestion').fill('retry');
    await expect(page.getByText('retry-skill:2.0.0')).toBeVisible();
    await expect(page.getByText('ok-skill:1.0.0')).not.toBeVisible();
    await expect(page.getByText('fix-skill:1.0.0')).not.toBeVisible();
  });

  test('search input filters records by issue text', async ({ page }) => {
    await page.goto('/skill-health');
    await page.getByPlaceholder('Search by skill, issue, suggestion').fill('python3');
    await expect(page.getByText('fix-skill:1.0.0')).toBeVisible();
    await expect(page.getByText('ok-skill:1.0.0')).not.toBeVisible();
  });

  test('mount action sends API request and shows success notice', async ({ page }) => {
    let mountRequested = false;
    await page.route('**/api/skill-preflight/ok-skill:1.0.0/mount', async (route) => {
      mountRequested = true;
      const body = route.request().postDataJSON() as any;
      expect(body.agent_id).toBe('builtin-action-lab');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ mount_status: 'mounted' }),
      });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Mount' }).first().click();
    await expect(page.getByText('Mount result: mounted')).toBeVisible();
    expect(mountRequested).toBe(true);
  });

  test('mount failure shows error notice', async ({ page }) => {
    await page.route('**/api/skill-preflight/ok-skill:1.0.0/mount', async (route) => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'skill_preflight_not_mountable' }),
      });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Mount' }).first().click();
    await expect(page.getByText('Fix preflight issues first, then retry mount.')).toBeVisible();
  });

  test('trust and setup flow sends API requests in order', async ({ page }) => {
    const calls: string[] = [];
    await page.route('**/api/skill-preflight/fix-skill:1.0.0/trust', async (route) => {
      calls.push('trust');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item: { ...mockPreflightRecords[1], trust_status: 'trusted' } }),
      });
    });
    await page.route('**/api/skill-preflight/fix-skill:1.0.0/setup', async (route) => {
      calls.push('setup');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item: { ...mockPreflightRecords[1], trust_status: 'trusted', setup_status: 'succeeded' } }),
      });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Trust & Setup' }).first().click();
    await expect(page.getByText('Trust & Setup result: succeeded')).toBeVisible();
    expect(calls).toEqual(['trust', 'setup']);
  });

  test('trust rejects before setup if trust fails', async ({ page }) => {
    let setupCalled = false;
    await page.route('**/api/skill-preflight/fix-skill:1.0.0/trust', async (route) => {
      await route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ detail: { code: 'skill_setup_requires_trust', message: 'Not trusted.' } }),
      });
    });
    await page.route('**/api/skill-preflight/fix-skill:1.0.0/setup', async (route) => {
      setupCalled = true;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Trust & Setup' }).first().click();
    await expect(page.getByText('Trust this skill before running setup.')).toBeVisible();
    expect(setupCalled).toBe(false);
  });

  test('retry setup flow for failed skill', async ({ page }) => {
    await page.route('**/api/skill-preflight/retry-skill:2.0.0/trust', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item: { ...mockPreflightRecords[2], trust_status: 'trusted' } }),
      });
    });
    await page.route('**/api/skill-preflight/retry-skill:2.0.0/setup', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item: { ...mockPreflightRecords[2], trust_status: 'trusted', setup_status: 'succeeded' } }),
      });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Retry Setup' }).click();
    await expect(page.getByText('Trust & Setup result: succeeded')).toBeVisible();
  });

  test('rescan action calls API and updates records count', async ({ page }) => {
    let rescanRequested = false;
    await page.route('**/api/skill-preflight/rescan', async (route) => {
      rescanRequested = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: { total: 2, available: 1, needs_fix: 1, unavailable: 0 },
          items: mockPreflightRecords.slice(0, 2),
        }),
      });
    });

    await page.goto('/skill-health');
    await page.getByRole('button', { name: 'Rescan' }).click();
    await expect(page.getByText('Rescan complete: 1 available, 1 needs_fix, 0 unavailable.')).toBeVisible();
    expect(rescanRequested).toBe(true);
  });

  test('network error on load shows error notice', async ({ page }) => {
    await page.route('**/api/skill-preflight', async (route) => {
      if (route.request().method() === 'GET') {
        await route.abort('failed');
        return;
      }
      await route.continue();
    });

    await page.goto('/skill-health');
    await expect(page.getByText('Failed to load skill preflight records.')).toBeVisible();
  });

  test('setup next action field is displayed when present', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.getByText('Next: Trust this skill, then run setup.').first()).toBeVisible();
    await expect(page.getByText('Next: Fix setup issues, then rerun setup.')).toBeVisible();
    await expect(page.getByText('Next: Setup is complete.')).toBeVisible();
  });

  test('status badges are rendered correctly', async ({ page }) => {
    await page.goto('/skill-health');
    await expect(page.locator('span:has-text("available")').first()).toBeVisible();
    await expect(page.locator('span:has-text("needs_fix")').first()).toBeVisible();
  });
});
