import type {
  Agent,
  CustomModel,
  DocAccess,
  LLMProvider,
  LlmForm,
  McpStatus,
  McpTool,
  FeatureFlags,
  Preferences,
} from './types';
import { DEFAULT_PREFERENCES, normalizeFeatureFlags, normalizeModelTierConfig, normalizePreferences } from './types';

export type SettingsDataSnapshot = {
  mcpConfigText: string;
  mcpStatus: McpStatus[];
  mcpTools: McpTool[];
  providers: LLMProvider[];
  llmForm: LlmForm;
  customModels: CustomModel[];
  agents: Agent[];
  prefs: Preferences;
  docAccess: DocAccess;
  featureFlags: FeatureFlags;
  docAllowText: string;
  docDenyText: string;
};

const normalizeDocAccess = (value: any): DocAccess => ({
  allow_roots: Array.isArray(value?.allow_roots) ? value.allow_roots : [],
  deny_roots: Array.isArray(value?.deny_roots) ? value.deny_roots : [],
});

export function useSettingsData() {
  const fetchSettingsData = async (): Promise<SettingsDataSnapshot> => {
    const mcpRes = await fetch('/api/mcp/');
    const mcpConfig = await mcpRes.json();

    const mcpStatusRes = await fetch('/api/mcp/status');
    const mcpStatus = (await mcpStatusRes.json()) as McpStatus[];

    const toolsRes = await fetch('/api/mcp/tools');
    const mcpTools = (await toolsRes.json()) as McpTool[];

    const providersRes = await fetch('/api/models/providers');
    const providers = (await providersRes.json()) as LLMProvider[];

    const llmConfigRes = await fetch('/api/config/llm');
    const llmFormRaw = (await llmConfigRes.json()) as LlmForm;
    const llmForm = {
      ...llmFormRaw,
      model_tiers: normalizeModelTierConfig(llmFormRaw?.model_tiers),
    } as LlmForm;

    const customModelsRes = await fetch('/api/models/custom');
    const customModels = (await customModelsRes.json()) as CustomModel[];

    const agentsRes = await fetch('/api/agents/');
    const agents = (await agentsRes.json()) as Agent[];

    const prefsRes = await fetch('/api/config/preferences');
    const prefsRaw = (await prefsRes.json()) as Preferences;

    const docAccessRes = await fetch('/api/config/doc_access');
    const rawDocAccess = await docAccessRes.json();
    const docAccess = normalizeDocAccess(rawDocAccess);

    const featureFlagsRes = await fetch('/api/config/feature_flags');
    const rawFeatureFlags = await featureFlagsRes.json();
    const featureFlags = normalizeFeatureFlags(rawFeatureFlags);

    return {
      mcpConfigText: JSON.stringify(mcpConfig, null, 2),
      mcpStatus,
      mcpTools,
      providers,
      llmForm,
      customModels,
      agents,
      prefs: normalizePreferences(prefsRaw || DEFAULT_PREFERENCES),
      docAccess,
      featureFlags,
      docAllowText: docAccess.allow_roots.join('\n'),
      docDenyText: docAccess.deny_roots.join('\n'),
    };
  };

  return { fetchSettingsData };
}
