import type { LlmForm, McpTemplate } from './types';

export type McpServerConfig = {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
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
    return Object.entries(parsed.mcpServers).map(([name, config]: [string, any]) => ({
      name,
      command: config.command,
      args: config.args || [],
      env: config.env || {},
      enabled: true,
    }));
  }

  if (Array.isArray(parsed)) {
    return parsed.map((item) => ({
      name: item.name,
      command: item.command,
      args: item.args || [],
      env: item.env || {},
      enabled: item.enabled !== undefined ? item.enabled : true,
    }));
  }

  if (parsed?.name && parsed?.command) {
    return [
      {
        name: parsed.name,
        command: parsed.command,
        args: parsed.args || [],
        env: parsed.env || {},
        enabled: true,
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
