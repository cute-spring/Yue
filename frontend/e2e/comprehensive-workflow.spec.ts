import { test, expect } from '@playwright/test';

test('Comprehensive User Workflow', async ({ page }) => {
  await page.route('**/api/models/providers**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { name: 'openai', configured: true, supports_model_refresh: false, available_models: ['gpt-4o'], models: ['gpt-4o'] },
      ]),
    });
  });

  // 1. Navigation and Landing
  await page.goto('/');
  await expect(page).toHaveTitle(/Yue/i);
  
  // 2. Navigate to Notebook
  await page.getByTitle('Notebook').click();
  await expect(page).toHaveURL(/\/notebook/);
  await expect(page.locator('h2:has-text("Notebook")')).toBeVisible();

  // 3. Navigate to Agents
  await page.getByTitle('Agents').click();
  await expect(page).toHaveURL(/\/agents/);
  await expect(page.locator('h2:has-text("Agents")')).toBeVisible();
  
  // 4. Create an Agent (Interaction)
  await page.getByRole('button', { name: /Create Agent/i }).first().click();
  
  // Fill form
  await page.getByPlaceholder(/e.g. Coding Assistant/i).fill('E2E Test Agent');
  await page.locator('textarea').first().fill('You are an E2E test agent.');

  // Ensure a model is selected if the form still shows the placeholder selector.
  const modelSelector = page.getByRole('button', { name: /Select Model/i }).first();
  if (await modelSelector.isVisible().catch(() => false)) {
    await modelSelector.click();
    await page.getByRole('button', { name: /^All$/i }).first().click().catch(() => {});
    await page.getByRole('button', { name: /gpt|qwen|deepseek/i }).first().click();
  }
  
  // Click Create Agent in the modal form.
  await page.getByRole('button', { name: /^Create Agent$/ }).last().click();
  
  // Verify agent exists in list
  await expect(page.getByRole('heading', { name: 'E2E Test Agent' }).first()).toBeVisible();

  // 5. Navigate to Settings
  await page.getByTitle('Settings').click();
  await expect(page).toHaveURL(/\/settings/);
  await expect(page.locator('h2:has-text("System Configuration")')).toBeVisible();
  
  // 6. Toggle Theme (Settings Persistence)
  // Get initial theme from data-theme on html tag
  const initialTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  await page.getByTitle(/Mode/i).click();
  const newTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
  expect(initialTheme).not.toBe(newTheme);

  // 7. Chat Message Sending
  await page.getByTitle('Chat').click();
  await expect(page).toHaveURL(/\/$/);

  await page.evaluate(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o');
  });
  await page.reload({ waitUntil: 'networkidle' });

  const input = page.locator('textarea');
  await input.fill('Hello Yue');
  const sendButton = page.getByRole('button', { name: 'Send Message' });
  await expect(sendButton).toBeEnabled();
  await sendButton.click();
  
  // Check for chat bubble (user message)
  await expect(page.getByText('Hello Yue').first()).toBeVisible({ timeout: 10000 });
  
  // Wait for assistant to finish typing
  await expect(page.locator('text=System Ready')).toBeVisible({ timeout: 30000 });
  
  // 8. Test Slash Command
  await input.fill('/help');
  await input.press('Enter');
  await expect(page.locator('text=Commands:')).toBeVisible();
});
