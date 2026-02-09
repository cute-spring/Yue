import { test, expect } from '@playwright/test';

test('Comprehensive User Workflow', async ({ page }) => {
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
  
  // Click Create Agent in the form (it has type="submit")
  await page.locator('form button[type="submit"]').click();
  
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

  // Select a model first to enable chatting
  const modelSelector = page.getByRole('button', { name: /Select Model/i });
  if (await modelSelector.isVisible()) {
    await modelSelector.click();
    // Select the first available model (e.g., deepseek-chat or any other)
    await page.locator('button').filter({ hasText: /deepseek-chat|gpt-4|gpt-oss/i }).first().click();
  }

  const input = page.locator('textarea');
  await input.fill('Hello Yue');
  await input.press('Enter');
  
  // Check for chat bubble (user message)
  await expect(page.locator('div').filter({ hasText: /^Hello Yue$/ }).first()).toBeVisible({ timeout: 10000 });
  
  // 8. Test Slash Command
  await input.fill('/help');
  await input.press('Enter');
  await expect(page.locator('text=Commands:')).toBeVisible();
});
