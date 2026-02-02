import { test, expect } from '@playwright/test';

test('MCP enable/disable toggles and status updates', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'MCP' }).click();

  // Ensure status is loaded and pick the first server name
  await page.waitForFunction(async () => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    return Array.isArray(data) && data.length > 0;
  });
  const serverName = await page.evaluate(async () => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    return data[0].name;
  });

  const checkbox = page.locator('input[type="checkbox"]').first();
  // Toggle to Offline
  if (await checkbox.isChecked()) {
    await checkbox.uncheck();
  } else {
    // If already disabled, enable then disable to verify both states
    await checkbox.check();
    await checkbox.uncheck();
  }
  await page.waitForFunction(async (name) => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    const fs = data.find((x: any) => x.name === name);
    return fs && fs.enabled === false && fs.connected === false;
  }, serverName, { timeout: 15000 });

  // Toggle back to Online
  await checkbox.check();
  await page.waitForFunction(async (name) => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    const fs = data.find((x: any) => x.name === name);
    return fs && fs.enabled === true && fs.connected === true;
  }, serverName, { timeout: 15000 });
});
