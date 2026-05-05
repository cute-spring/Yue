import { describe, expect, it } from 'vitest';
import {
  buildMcpTemplateOnboardingNotes,
  buildManagedModelsConfig,
  buildMcpServersFromParsedInput,
  buildMcpTemplateInitialValues,
  buildRevertedManagedModelsConfig,
  parseMcpManualText,
  splitRootsText,
} from './settingsUtils';

describe('splitRootsText', () => {
  it('trims lines and removes empties', () => {
    expect(splitRootsText(' /a \n\n /b \n')).toEqual(['/a', '/b']);
  });
});

describe('MCP manual parsing', () => {
  it('parses claude desktop mcpServers object', () => {
    const parsed = buildMcpServersFromParsedInput({
      mcpServers: {
        fs: { command: 'npx', args: ['-y', 'x'] },
      },
    });
    expect(parsed).toEqual([
      { name: 'fs', transport: 'stdio', command: 'npx', args: ['-y', 'x'], env: {}, enabled: true },
    ]);
  });

  it('parses array format', () => {
    const result = parseMcpManualText(
      JSON.stringify([{ name: 'a', command: 'npx', args: [], env: {}, enabled: false }]),
    );
    expect(result.kind).toBe('ok');
    if (result.kind === 'ok') {
      expect(result.servers[0].enabled).toBe(false);
      expect(result.servers[0].name).toBe('a');
      expect(result.servers[0].transport).toBe('stdio');
    }
  });

  it('parses streamable_http server in array format', () => {
    const result = parseMcpManualText(
      JSON.stringify([{ name: 'remote', transport: 'streamable_http', url: 'https://mcp.example.com/sse', headers: { Authorization: '${MCP_TOKEN}' } }]),
    );
    expect(result.kind).toBe('ok');
    if (result.kind === 'ok') {
      expect(result.servers[0]).toEqual({
        name: 'remote',
        transport: 'streamable_http',
        url: 'https://mcp.example.com/sse',
        headers: { Authorization: '${MCP_TOKEN}' },
        env: {},
        enabled: true,
      });
    }
  });

  it('returns invalid_json for bad json', () => {
    expect(parseMcpManualText('{')).toEqual({ kind: 'invalid_json' });
  });

  it('returns no_valid_servers when format is unsupported', () => {
    expect(parseMcpManualText(JSON.stringify({ foo: 'bar' }))).toEqual({ kind: 'no_valid_servers' });
  });
});

describe('managed model config builders', () => {
  it('builds allowlist config and applies capability overrides', () => {
    const current = {
      openai_enabled_models_mode: 'all',
      models: { 'openai/gpt-4o': {} },
    };
    const result = buildManagedModelsConfig(
      current,
      'openai',
      new Set(['gpt-4o']),
      ['gpt-4o', 'gpt-4.1'],
      { 'gpt-4.1': ['vision'] },
    );
    expect(result.nextConfig.openai_enabled_models).toEqual(['gpt-4o']);
    expect(result.nextConfig.openai_enabled_models_mode).toBe('allowlist');
    expect(result.nextConfig.models['openai/gpt-4.1'].capabilities).toEqual(['vision']);
  });

  it('rebuilds config for undo path', () => {
    const original = { models: {} as Record<string, any> };
    const reverted = buildRevertedManagedModelsConfig(
      original,
      'openai',
      new Set(['gpt-4.1']),
      'all',
      { 'openai/gpt-4.1': { capabilities: ['reasoning'] } },
      ['gpt-4.1'],
      {},
    );
    expect(reverted.openai_enabled_models).toEqual(['gpt-4.1']);
    expect(reverted.openai_enabled_models_mode).toBe('all');
    expect(reverted.models['openai/gpt-4.1'].capabilities).toBeUndefined();
  });
});

describe('MCP template helpers', () => {
  it('builds initial values from template defaults', () => {
    expect(
      buildMcpTemplateInitialValues({
        id: 'jira-company',
        name: 'Jira MCP',
        description: '',
        provider: 'jira',
        deployment: 'mixed',
        fields: [
          { key: 'serverName', label: 'Server Name', type: 'text', required: true, options: [], default_value: 'jira' },
          { key: 'argsJson', label: 'Args', type: 'json', required: true, options: [], default_value: '["-y","pkg"]' },
        ],
      }),
    ).toEqual({
      serverName: 'jira',
      argsJson: '["-y","pkg"]',
    });
  });

  it('builds jira onboarding notes for the marketplace modal', () => {
    expect(buildMcpTemplateOnboardingNotes('jira-company')).toEqual([
      'Default to base URL plus personal token; username/email should stay optional unless your company MCP requires it.',
      'Keep the server disabled until the real internal Jira MCP package or executable is confirmed.',
      'Start with read-only scope hints such as allowed projects, default JQL, or explicit read-only flags.',
    ]);
  });

  it('builds jira onboarding notes for streamable_http transport', () => {
    expect(buildMcpTemplateOnboardingNotes('jira-company', 'streamable_http')).toEqual([
      'Use your company MCP endpoint URL and keep auth in headers as ${ENV_NAME} placeholders.',
      'Prefer read-only scopes first while verifying tool behavior.',
      'Confirm required headers and proxy/SSL requirements with your platform team.',
    ]);
  });

  it('returns no onboarding notes for templates without custom guidance', () => {
    expect(buildMcpTemplateOnboardingNotes('custom-company-mcp')).toEqual([]);
  });
});
