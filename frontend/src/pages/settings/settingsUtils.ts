import type { LlmForm, McpTemplate } from './types';

export type McpServerConfig = {
  name: string;
  transport?: 'stdio' | 'streamable_http';
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  url?: string;
  headers?: Record<string, string>;
  enabled: boolean;
};

type ParseMcpManualTextResult =
  | { kind: 'empty' }
  | { kind: 'invalid_json' }
  | { kind: 'no_valid_servers' }
  | { kind: 'ok'; servers: McpServerConfig[] };

export const splitRootsText = (input: string): string[] =>
  input
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);

export const buildMcpServersFromParsedInput = (parsed: any): McpServerConfig[] => {
  if (parsed?.mcpServers && typeof parsed.mcpServers === 'object') {
    const servers: McpServerConfig[] = [];
    Object.entries(parsed.mcpServers).forEach(([name, config]: [string, any]) => {
      if (!config || typeof config !== 'object') return;
      const transport = config.transport === 'streamable_http' ? 'streamable_http' : 'stdio';
      if (transport === 'streamable_http') {
        if (!config.url) return;
        servers.push({
          name,
          transport,
          url: config.url,
          headers: config.headers || {},
          env: config.env || {},
          enabled: config.enabled !== undefined ? config.enabled : true,
        });
        return;
      }
      if (!config.command) return;
      servers.push({
        name,
        transport: 'stdio',
        command: config.command,
        args: config.args || [],
        env: config.env || {},
        enabled: config.enabled !== undefined ? config.enabled : true,
      });
    });
    return servers;
  }

  if (Array.isArray(parsed)) {
    const servers: McpServerConfig[] = [];
    parsed.forEach((item) => {
      if (!item || typeof item !== 'object' || !item.name) return;
      const transport = item.transport === 'streamable_http' ? 'streamable_http' : 'stdio';
      if (transport === 'streamable_http') {
        if (!item.url) return;
        servers.push({
          name: item.name,
          transport,
          url: item.url,
          headers: item.headers || {},
          env: item.env || {},
          enabled: item.enabled !== undefined ? item.enabled : true,
        });
        return;
      }
      if (!item.command) return;
      servers.push({
        name: item.name,
        transport: 'stdio',
        command: item.command,
        args: item.args || [],
        env: item.env || {},
        enabled: item.enabled !== undefined ? item.enabled : true,
      });
    });
    return servers;
  }

  if (parsed?.name && (parsed?.command || parsed?.url)) {
    const transport = parsed.transport === 'streamable_http' ? 'streamable_http' : 'stdio';
    if (transport === 'streamable_http' && parsed?.url) {
      return [
        {
          name: parsed.name,
          transport,
          url: parsed.url,
          headers: parsed.headers || {},
          env: parsed.env || {},
          enabled: parsed.enabled !== undefined ? parsed.enabled : true,
        },
      ];
    }
    if (!parsed?.command) return [];
    return [
      {
        name: parsed.name,
        transport: 'stdio',
        command: parsed.command,
        args: parsed.args || [],
        env: parsed.env || {},
        enabled: parsed.enabled !== undefined ? parsed.enabled : true,
      },
    ];
  }

  return [];
};

export const parseMcpManualText = (input: string): ParseMcpManualTextResult => {
  const text = input.trim();
  if (!text) return { kind: 'empty' };

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { kind: 'invalid_json' };
  }

  const servers = buildMcpServersFromParsedInput(parsed);
  if (servers.length === 0) return { kind: 'no_valid_servers' };
  return { kind: 'ok', servers };
};

export const buildMcpTemplateInitialValues = (template: McpTemplate): Record<string, string> =>
  Object.fromEntries(
    template.fields.map((field) => [
      field.key,
      field.default_value === undefined || field.default_value === null ? '' : String(field.default_value),
    ]),
  );

export const buildMcpTemplateOnboardingNotes = (
  templateId: string,
  transport: 'stdio' | 'streamable_http' = 'stdio',
): string[] => {
  if (templateId === 'jira-company') {
    if (transport === 'streamable_http') {
      return [
        'Use your company MCP endpoint URL and keep auth in headers as ${ENV_NAME} placeholders.',
        'Prefer read-only scopes first while verifying tool behavior.',
        'Confirm required headers and proxy/SSL requirements with your platform team.',
      ];
    }
    return [
      'Default to base URL plus personal token; username/email should stay optional unless your company MCP requires it.',
      'Keep the server disabled until the real internal Jira MCP package or executable is confirmed.',
      'Start with read-only scope hints such as allowed projects, default JQL, or explicit read-only flags.',
    ];
  }
  return [];
};

export const mergeModelCapabilityOverrides = (
  baseModels: Record<string, any>,
  providerName: string,
  managedModels: string[],
  capabilityOverrides: Record<string, string[]>,
): Record<string, any> => {
  const modelsDict = { ...baseModels };
  managedModels.forEach((model) => {
    const fullId = `${providerName}/${model}`;
    const overrides = capabilityOverrides[model];
    if (overrides) {
      modelsDict[fullId] = { ...(modelsDict[fullId] || {}), capabilities: overrides };
      return;
    }
    if (modelsDict[fullId]) {
      delete modelsDict[fullId].capabilities;
    }
  });
  return modelsDict;
};

export const buildManagedModelsConfig = (
  currentConfig: LlmForm,
  providerName: string,
  enabledModels: Set<string>,
  managedModels: string[],
  capabilityOverrides: Record<string, string[]>,
) => {
  const key = `${providerName}_enabled_models`;
  const modeKey = `${providerName}_enabled_models_mode`;
  const modelsDict = mergeModelCapabilityOverrides(
    currentConfig.models || {},
    providerName,
    managedModels,
    capabilityOverrides,
  );
  const nextConfig = {
    ...currentConfig,
    [key]: Array.from(enabledModels),
    [modeKey]: 'allowlist',
    models: modelsDict,
  };
  return { key, modeKey, modelsDict, nextConfig, previousMode: currentConfig[modeKey] };
};

export const buildRevertedManagedModelsConfig = (
  originalConfig: LlmForm,
  providerName: string,
  previousEnabledModels: Set<string>,
  previousMode: any,
  modelsDictAtSave: Record<string, any>,
  managedModels: string[],
  previousCapabilityOverrides: Record<string, string[]>,
) => {
  const key = `${providerName}_enabled_models`;
  const modeKey = `${providerName}_enabled_models_mode`;
  const revertModelsDict = mergeModelCapabilityOverrides(
    modelsDictAtSave,
    providerName,
    managedModels,
    previousCapabilityOverrides,
  );
  return {
    ...originalConfig,
    [key]: Array.from(previousEnabledModels),
    [modeKey]: previousMode,
    models: revertModelsDict,
  };
};
