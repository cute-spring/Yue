import { afterEach, describe, expect, it, vi } from 'vitest';

const isolatedEnvironment = {
  YUE_E2E_BACKEND_PORT: '18421',
  YUE_E2E_FRONTEND_PORT: '3421',
  YUE_E2E_DATA_DIR: '/tmp/yue-e2e-mocked-contract',
};

afterEach(() => {
  for (const name of Object.keys(isolatedEnvironment)) {
    delete process.env[name];
  }
  vi.resetModules();
});

describe('mocked Playwright configuration', () => {
  it('requires the per-run isolation environment', async () => {
    await expect(import('./playwright.mocked.config')).rejects.toThrow(
      'YUE_E2E_',
    );
  });

  it('starts isolated frontend and backend services', async () => {
    Object.assign(process.env, isolatedEnvironment);
    const { default: config } = await import('./playwright.mocked.config');

    expect(config.webServer).toHaveLength(2);
    expect(config.webServer).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ reuseExistingServer: false }),
        expect.objectContaining({
          reuseExistingServer: false,
          command: expect.stringContaining('YUE_DATA_DIR='),
        }),
      ]),
    );
    expect(config.use?.baseURL).toBe('http://127.0.0.1:3421');
    expect(config.webServer?.[0].command).toContain('YUE_DATA_DIR=/tmp/yue-e2e-mocked-contract');
    expect(config.webServer?.[0].command).toContain('--port 18421');
  });
});
