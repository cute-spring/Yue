import { test, expect } from '@playwright/test';

test('Agents: Smart Generate draft preview and selective apply', async ({ page }) => {
  await page.route('**/api/agents/generate**', async (route) => {
    const body = route.request().postDataJSON?.() as any;
    const updateTools = !!body?.update_tools;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        name: 'PR Reviewer',
        system_prompt: 'Role: PR reviewer\nScope: frontend\nWorkflow: steps\nOutput format: bullets',
        enabled_tools: updateTools ? ['filesystem:write', 'builtin:docs_search'] : (body?.existing_tools || []),
        recommended_tools: ['filesystem:write', 'builtin:docs_search'],
        tool_reasons: {
          'filesystem:write': 'Apply small safe fixes when needed',
          'builtin:docs_search': 'Look up repo conventions in docs'
        },
        tool_risks: {
          'filesystem:write': 'write',
          'builtin:docs_search': 'read'
        }
      })
    });
  });

  await page.goto('/agents');
  await page.getByRole('button', { name: 'Create Agent' }).click();
  await page.getByRole('button', { name: 'Smart Generate' }).click();

  await page.locator('textarea[placeholder^="例如："]').fill('I want an agent to review PRs and apply fixes.');
  const generateButton = page.getByRole('button', { name: '生成草案' });
  await generateButton.evaluate((el: HTMLButtonElement) => el.click());

  await expect(page.getByText('Draft Preview')).toBeVisible({ timeout: 15000 });
  await expect(page.getByText('PR Reviewer', { exact: true })).toBeVisible();
  await expect(page.getByText('WRITE', { exact: true })).toBeVisible();
  await expect(page.getByText('READ', { exact: true })).toBeVisible();

  await expect(page.getByText('Prompt lint warning')).toBeVisible();
  await expect(page.getByText('Tool risk warning')).toBeVisible();

  const applyToolsCheckbox = page.getByLabel('Apply tool selection');
  await applyToolsCheckbox.evaluate((el: HTMLInputElement) => {
    el.checked = false;
    el.dispatchEvent(new Event('change', { bubbles: true }));
  });
  const applyButton = page.getByRole('button', { name: '应用到表单' });
  await applyButton.evaluate((el: HTMLButtonElement) => el.click());
  await expect(page.getByText('Draft Preview')).toHaveCount(0);
});
