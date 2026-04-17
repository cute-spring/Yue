export type ModelTier = 'light' | 'balanced' | 'heavy';
export type ModelTierConfigEntry = {
  provider: string;
  model: string;
};

export type ModelTierConfig = Record<ModelTier, ModelTierConfigEntry>;

export type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  model_selection_mode?: 'tier' | 'direct';
  model_tier?: ModelTier;
  enabled_tools: string[];
  voice_input_enabled?: boolean;
  voice_input_provider?: 'browser' | 'azure';
  voice_azure_config?: {
    region?: string;
    endpoint_id?: string;
    api_key?: string;
    api_key_configured?: boolean;
  } | null;
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
  advanced_mode: boolean;
  voice_input_enabled: boolean;
  voice_input_provider: 'browser' | 'azure';
  voice_input_language: string;
  voice_input_show_interim: boolean;
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
  advanced_mode: false,
  voice_input_enabled: true,
  voice_input_provider: 'browser',
  voice_input_language: 'auto',
  voice_input_show_interim: true,
  auto_speech_enabled: false,
  speech_voice: '',
  speech_rate: 1.0,
  speech_volume: 1.0,
  speech_engine: 'browser',
  speech_openai_voice: 'alloy',
  speech_openai_model: 'gpt-4o-mini-tts',
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const toBoolean = (value: unknown, fallback: boolean): boolean => {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
    if (['false', '0', 'no', 'off'].includes(normalized)) return false;
  }
  if (value === null || value === undefined) return fallback;
  return Boolean(value);
};

export const normalizePreferences = (value: any): Preferences => {
  const rate = typeof value?.speech_rate === 'number' ? value.speech_rate : Number(value?.speech_rate);
  const volume = typeof value?.speech_volume === 'number' ? value.speech_volume : Number(value?.speech_volume);
  return {
    theme: typeof value?.theme === 'string' ? value.theme : DEFAULT_PREFERENCES.theme,
    language: typeof value?.language === 'string' ? value.language : DEFAULT_PREFERENCES.language,
    default_agent: typeof value?.default_agent === 'string' ? value.default_agent : DEFAULT_PREFERENCES.default_agent,
    advanced_mode: toBoolean(value?.advanced_mode, DEFAULT_PREFERENCES.advanced_mode),
    voice_input_enabled: toBoolean(value?.voice_input_enabled, DEFAULT_PREFERENCES.voice_input_enabled),
    voice_input_provider: value?.voice_input_provider === 'azure' ? 'azure' : 'browser',
    voice_input_language: typeof value?.voice_input_language === 'string' && value.voice_input_language.trim()
      ? value.voice_input_language
      : DEFAULT_PREFERENCES.voice_input_language,
    voice_input_show_interim: toBoolean(value?.voice_input_show_interim, DEFAULT_PREFERENCES.voice_input_show_interim),
    auto_speech_enabled: toBoolean(value?.auto_speech_enabled, DEFAULT_PREFERENCES.auto_speech_enabled),
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

export type FeatureFlags = {
  chat_trace_ui_enabled: boolean;
  chat_trace_raw_enabled: boolean;
};

export const DEFAULT_FEATURE_FLAGS: FeatureFlags = {
  chat_trace_ui_enabled: false,
  chat_trace_raw_enabled: false,
};

export const DEFAULT_MODEL_TIER_CONFIG: ModelTierConfig = {
  light: { provider: 'openai', model: 'gpt-4o-mini' },
  balanced: { provider: 'openai', model: 'gpt-4o' },
  heavy: { provider: 'openai', model: 'gpt-4.1' },
};

export const normalizeFeatureFlags = (value: any): FeatureFlags => ({
  chat_trace_ui_enabled: typeof value?.chat_trace_ui_enabled === 'boolean'
    ? value.chat_trace_ui_enabled
    : DEFAULT_FEATURE_FLAGS.chat_trace_ui_enabled,
  chat_trace_raw_enabled: typeof value?.chat_trace_raw_enabled === 'boolean'
    ? value.chat_trace_raw_enabled
    : DEFAULT_FEATURE_FLAGS.chat_trace_raw_enabled,
});

const normalizeModelTierEntry = (value: any, fallback: ModelTierConfigEntry): ModelTierConfigEntry => ({
  provider: typeof value?.provider === 'string' && value.provider.trim() ? value.provider : fallback.provider,
  model: typeof value?.model === 'string' && value.model.trim() ? value.model : fallback.model,
});

export const normalizeModelTierConfig = (value: any): ModelTierConfig => ({
  light: normalizeModelTierEntry(value?.light, DEFAULT_MODEL_TIER_CONFIG.light),
  balanced: normalizeModelTierEntry(value?.balanced, DEFAULT_MODEL_TIER_CONFIG.balanced),
  heavy: normalizeModelTierEntry(value?.heavy, DEFAULT_MODEL_TIER_CONFIG.heavy),
});

export type LlmForm = Record<string, any>;
