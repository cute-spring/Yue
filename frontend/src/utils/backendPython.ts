type E2eEnvironment = Record<string, string | undefined>;

const resolvePort = (value: string | undefined, fallback: number): number => {
  const port = Number(value);
  return Number.isInteger(port) && port > 0 && port <= 65535 ? port : fallback;
};

export const resolveBackendPython = (env: E2eEnvironment): string =>
  env.YUE_E2E_BACKEND_PYTHON || 'backend/.venv/bin/python';

export const resolveE2eBackendPort = (env: E2eEnvironment): number =>
  resolvePort(env.YUE_E2E_BACKEND_PORT, 8013);

export const resolveE2eFrontendPort = (env: E2eEnvironment): number =>
  resolvePort(env.YUE_E2E_FRONTEND_PORT, 3010);
