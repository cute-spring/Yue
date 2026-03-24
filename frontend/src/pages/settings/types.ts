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
  auto_speech_enabled: boolean;
  speech_voice: string;
  speech_rate: number;
  speech_volume: number;
  speech_engine: 'browser' | 'openai';
  speech_openai_voice: string;
  speech_openai_model: string;
};

export const DEFAULT_PREFERENCES: Preferences = {
  theme: 'light',
  language: 'en',
  default_agent: 'default',
  auto_speech_enabled: false,
  speech_voice: '',
  speech_rate: 1.0,
  speech_volume: 1.0,
  speech_engine: 'browser',
  speech_openai_voice: 'alloy',
  speech_openai_model: 'gpt-4o-mini-tts',
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export const normalizePreferences = (value: any): Preferences => {
  const rate = typeof value?.speech_rate === 'number' ? value.speech_rate : Number(value?.speech_rate);
  const volume = typeof value?.speech_volume === 'number' ? value.speech_volume : Number(value?.speech_volume);
  return {
    theme: typeof value?.theme === 'string' ? value.theme : DEFAULT_PREFERENCES.theme,
    language: typeof value?.language === 'string' ? value.language : DEFAULT_PREFERENCES.language,
    default_agent: typeof value?.default_agent === 'string' ? value.default_agent : DEFAULT_PREFERENCES.default_agent,
    auto_speech_enabled: typeof value?.auto_speech_enabled === 'boolean' ? value.auto_speech_enabled : DEFAULT_PREFERENCES.auto_speech_enabled,
    speech_voice: typeof value?.speech_voice === 'string' ? value.speech_voice : DEFAULT_PREFERENCES.speech_voice,
    speech_rate: Number.isFinite(rate) ? clamp(rate, 0.5, 2.0) : DEFAULT_PREFERENCES.speech_rate,
    speech_volume: Number.isFinite(volume) ? clamp(volume, 0, 1) : DEFAULT_PREFERENCES.speech_volume,
    speech_engine: value?.speech_engine === 'openai' ? 'openai' : 'browser',
    speech_openai_voice: typeof value?.speech_openai_voice === 'string' && value.speech_openai_voice.trim()
      ? value.speech_openai_voice
      : DEFAULT_PREFERENCES.speech_openai_voice,
    speech_openai_model: typeof value?.speech_openai_model === 'string' && value.speech_openai_model.trim()
      ? value.speech_openai_model
      : DEFAULT_PREFERENCES.speech_openai_model,
  };
};

export type DocAccess = {
  allow_roots: string[];
  deny_roots: string[];
};

export type LlmForm = Record<string, any>;
