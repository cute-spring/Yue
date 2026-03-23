import type {
  Agent,
  CustomModel,
  DocAccess,
  LLMProvider,
  LlmForm,
  McpStatus,
  McpTool,
  Preferences,
} from './types';

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
  docAllowText: string;
  docDenyText: string;
};

const defaultPrefs: Preferences = {
  theme: 'light',
  language: 'en',
  default_agent: 'default',
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
    const llmForm = (await llmConfigRes.json()) as LlmForm;

    const customModelsRes = await fetch('/api/models/custom');
    const customModels = (await customModelsRes.json()) as CustomModel[];

    const agentsRes = await fetch('/api/agents/');
    const agents = (await agentsRes.json()) as Agent[];

    const prefsRes = await fetch('/api/config/preferences');
    const prefs = (await prefsRes.json()) as Preferences;

    const docAccessRes = await fetch('/api/config/doc_access');
    const rawDocAccess = await docAccessRes.json();
    const docAccess = normalizeDocAccess(rawDocAccess);

    return {
      mcpConfigText: JSON.stringify(mcpConfig, null, 2),
      mcpStatus,
      mcpTools,
      providers,
      llmForm,
      customModels,
      agents,
      prefs: prefs || defaultPrefs,
      docAccess,
      docAllowText: docAccess.allow_roots.join('\n'),
      docDenyText: docAccess.deny_roots.join('\n'),
    };
  };

  return { fetchSettingsData };
}
