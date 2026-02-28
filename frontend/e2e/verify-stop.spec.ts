import { test, expect } from '@playwright/test';

test('Stop generation functionality', async ({ page }) => {
  // Go to the chat page (assuming port 3000 as per logs)
  await page.goto('http://localhost:3000/');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  const input = page.getByPlaceholder(/You are chatting with/i);
  await expect(input).toBeVisible({ timeout: 15000 });
  
  // Check if we need to select a model
  const modelButton = page.locator('button').filter({ hasText: /Select Model|GPT-|QWEN|DEEPSEEK/i }).first();
  const currentModel = await modelButton.textContent();
  
  if (!currentModel || currentModel.toUpperCase().includes("SELECT MODEL")) {
    await modelButton.click();
    // Wait for the dropdown to appear and click a model button specifically (not the toggle)
    // We target buttons that have text and don't contain 'All' or 'Enabled'
    const dropdownModel = page.locator('div.absolute.bottom-full button').filter({ hasText: /gpt-oss|qwen|deepseek/i }).first();
    await dropdownModel.waitFor({ state: 'visible' });
    await dropdownModel.click();
  }

  // Type a prompt that would trigger a long response
  await input.fill('Write a 500-word essay about the future of AI in 2026.');
  
  // Find the send button
  const sendButton = page.locator('button[type="submit"]');
  await sendButton.click();
  
  // Wait for it to start typing
  // The button should turn into a stop button (rose-500 background)
  // Or we can check if isTyping is true by looking for the stop icon/spinning loader
  const stopButton = page.locator('button[type="submit"].bg-rose-500');
  await expect(stopButton).toBeVisible({ timeout: 5000 });
  
  // Click the stop button
  await stopButton.click();
  
  // Verify that it stopped typing
  // The button should return to its normal state
  await expect(stopButton).not.toBeVisible({ timeout: 5000 });
  
  // Verify that the assistant message is present but potentially incomplete
  const assistantMessages = page.locator('.assistant-message'); // Adjust selector as needed
  // At least one assistant message should be there
  // We can also check for a "stopped" indicator if we add one, but for now we check if typing stopped
});
