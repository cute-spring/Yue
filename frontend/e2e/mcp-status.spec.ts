import { test, expect } from '@playwright/test';

test('MCP enable/disable toggles and status updates', async ({ page }) => {
  let mcpConfigs = [{ name: 'fs', command: 'npx', args: ['-y', '@modelcontextprotocol/server-filesystem'], env: {}, enabled: true }];

  await page.route('**/api/mcp/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mcpConfigs) });
      return;
    }
    const next = route.request().postDataJSON() as any;
    mcpConfigs = Array.isArray(next) ? next : Array.isArray(next?.mcpServers) ? next.mcpServers : mcpConfigs;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mcpConfigs) });
  });
  await page.route('**/api/mcp/reload', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });
  await page.route('**/api/mcp/tools', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/mcp/templates', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/mcp/status', async (route) => {
    const status = mcpConfigs.map((cfg: any) => ({
      name: cfg.name,
      enabled: !!cfg.enabled,
      connected: !!cfg.enabled,
      tools_count: 0,
      last_error: null,
    }));
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(status) });
  });

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
