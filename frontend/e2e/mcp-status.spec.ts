import { test, expect } from '@playwright/test';

test('MCP enable/disable toggles and status updates', async ({ page }) => {
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Mcp' }).click();

  const card = page.locator('div').filter({ hasText: 'filesystem' }).first();
  await expect(card).toBeVisible();

  const checkbox = card.getByRole('checkbox');
  // Toggle to Offline
  if (await checkbox.isChecked()) {
    await checkbox.uncheck();
  } else {
    // If already disabled, enable then disable to verify both states
    await checkbox.check();
    await expect(card.getByText(/Online/i)).toBeVisible();
    await checkbox.uncheck();
  }
  await page.waitForFunction(async () => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    const fs = data.find((x: any) => x.name === 'filesystem');
    return fs && fs.enabled === false && fs.connected === false;
  }, { timeout: 15000 });

  // Toggle back to Online
  await checkbox.check();
  await page.waitForFunction(async () => {
    const res = await fetch('/api/mcp/status');
    const data = await res.json();
    const fs = data.find((x: any) => x.name === 'filesystem');
    return fs && fs.enabled === true && fs.connected === true;
  }, { timeout: 15000 });
});
