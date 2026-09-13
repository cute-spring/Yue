import { describe, expect, it } from 'vitest';

import { resolveBackendPython, resolveE2eBackendPort, resolveE2eFrontendPort } from './backendPython';

describe('E2E runtime configuration', () => {
  it('uses isolated default ports and the worktree backend virtualenv', () => {
    expect(resolveBackendPython({})).toBe('backend/.venv/bin/python');
    expect(resolveE2eBackendPort({})).toBe(8013);
    expect(resolveE2eFrontendPort({})).toBe(3010);
  });

  it('honors explicit E2E runtime overrides', () => {
    const env = {
      YUE_E2E_BACKEND_PYTHON: '/tmp/yue-e2e-python',
      YUE_E2E_BACKEND_PORT: '8137',
      YUE_E2E_FRONTEND_PORT: '3127',
    };

    expect(resolveBackendPython(env)).toBe('/tmp/yue-e2e-python');
    expect(resolveE2eBackendPort(env)).toBe(8137);
    expect(resolveE2eFrontendPort(env)).toBe(3127);
  });

  it('uses the CI Python executable when no E2E-specific override is set', () => {
    expect(resolveBackendPython({ PYTHON_BIN: 'python' })).toBe('python');
  });
});
