import { test, expect } from '@playwright/test';

test('Agents: Smart Generate draft preview and selective apply', async ({ page }) => {
  await page.route('**/api/agents/generate', async (route) => {
    const body = route.request().postDataJSON?.() as any;
    const updateTools = !!body?.update_tools;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        name: 'PR Reviewer',
        system_prompt: 'Role: PR reviewer\nScope: frontend\nWorkflow: steps\nOutput format: bullets',
        enabled_tools: updateTools ? ['filesystem:write', 'builtin:docs_search_markdown'] : (body?.existing_tools || []),
        recommended_tools: ['filesystem:write', 'builtin:docs_search_markdown'],
        tool_reasons: {
          'filesystem:write': 'Apply small safe fixes when needed',
          'builtin:docs_search_markdown': 'Look up repo conventions in docs'
        },
        tool_risks: {
          'filesystem:write': 'write',
          'builtin:docs_search_markdown': 'read'
        }
      })
    });
  });

  await page.goto('/agents');
  await page.getByRole('button', { name: 'Create Agent' }).click();
  await page.getByRole('button', { name: 'Smart Generate' }).click();

  await page.locator('textarea[placeholder^="例如："]').fill('I want an agent to review PRs and apply fixes.');
  await page.getByRole('button', { name: '生成草案' }).click();

  await expect(page.getByText('Draft Preview')).toBeVisible();
  await expect(page.getByText('PR Reviewer', { exact: true })).toBeVisible();
  await expect(page.getByText('WRITE', { exact: true })).toBeVisible();
  await expect(page.getByText('READ', { exact: true })).toBeVisible();

  await expect(page.getByText('Prompt lint warning')).toBeVisible();
  await expect(page.getByText('Tool risk warning')).toBeVisible();

  await page.getByLabel('Apply tool selection').uncheck();
  await page.getByRole('button', { name: '应用到表单' }).click();

  const nameInput = page.locator('input[placeholder="e.g. Coding Assistant"]');
  const promptTextarea = page.locator('textarea[placeholder="You are a helpful assistant..."]');

  await expect(nameInput).toHaveValue('PR Reviewer');
  await expect(promptTextarea).toHaveValue(/Role: PR reviewer/);
});
