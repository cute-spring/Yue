export type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
};

export type LLMProvider = {
  name: string;
  configured: boolean;
  requirements: string[];
  current_model?: string;
  available_models?: string[];
  models?: string[];
  model_capabilities?: Record<string, string[]>;
  explicit_model_capabilities?: Record<string, string[]>;
};

export type McpStatus = {
  name: string;
  enabled: boolean;
  connected: boolean;
  transport: string;
  last_error?: string;
};

export type McpTool = {
  id: string;
  name: string;
  description: string;
  server: string;
};

export type CustomModel = {
  name: string;
  base_url?: string;
  api_key?: string;
  model?: string;
  capabilities?: string[];
};

export type NewCustomModelDraft = {
  name: string;
  provider: string;
  model: string;
  base_url?: string;
  api_key?: string;
  capabilities?: string[];
};

export type Preferences = {
  theme: string;
  language: string;
  default_agent: string;
};

export type DocAccess = {
  allow_roots: string[];
  deny_roots: string[];
};

export type LlmForm = Record<string, any>;
