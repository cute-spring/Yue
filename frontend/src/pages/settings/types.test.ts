import { describe, expect, it } from 'vitest';
import { buildPreferencesFromFormData } from './components/GeneralSettingsTab';
import {
  DEFAULT_FEATURE_FLAGS,
  DEFAULT_MODEL_TIER_CONFIG,
  DEFAULT_PREFERENCES,
  normalizeFeatureFlags,
  normalizeModelTierConfig,
  normalizePreferences,
} from './types';

describe('preferences normalization', () => {
  it('fills missing speech fields with defaults', () => {
    const normalized = normalizePreferences({
      theme: 'dark',
      language: 'zh',
      default_agent: 'agent_1',
    });
    expect(normalized).toEqual({
      ...DEFAULT_PREFERENCES,
      theme: 'dark',
      language: 'zh',
      default_agent: 'agent_1',
    });
  });

  it('clamps speech rate and volume', () => {
    const normalized = normalizePreferences({
      speech_rate: 4,
      speech_volume: -1,
    });
    expect(normalized.speech_rate).toBe(2);
    expect(normalized.speech_volume).toBe(0);
  });

  it('normalizes voice input preferences', () => {
    const normalized = normalizePreferences({
      voice_input_enabled: false,
      voice_input_provider: 'azure',
      voice_input_language: 'zh-CN',
      voice_input_show_interim: false,
    });

    expect(normalized.voice_input_enabled).toBe(false);
    expect(normalized.voice_input_provider).toBe('azure');
    expect(normalized.voice_input_language).toBe('zh-CN');
    expect(normalized.voice_input_show_interim).toBe(false);
  });

  it('normalizes boolean-like string preferences', () => {
    const normalized = normalizePreferences({
      advanced_mode: 'true',
      voice_input_enabled: '0',
      voice_input_show_interim: 'off',
      auto_speech_enabled: 'yes',
    });

    expect(normalized.advanced_mode).toBe(true);
    expect(normalized.voice_input_enabled).toBe(false);
    expect(normalized.voice_input_show_interim).toBe(false);
    expect(normalized.auto_speech_enabled).toBe(true);
  });

  it('fills missing feature flag values with defaults', () => {
    expect(normalizeFeatureFlags({})).toEqual(DEFAULT_FEATURE_FLAGS);
  });

  it('normalizes chat trace feature flags from booleans only', () => {
    const normalized = normalizeFeatureFlags({
      chat_trace_ui_enabled: true,
      chat_trace_raw_enabled: false,
    });

    expect(normalized.chat_trace_ui_enabled).toBe(true);
    expect(normalized.chat_trace_raw_enabled).toBe(false);
  });

  it('fills missing model tier mappings with defaults', () => {
    expect(normalizeModelTierConfig({})).toEqual(DEFAULT_MODEL_TIER_CONFIG);
  });

  it('normalizes model tier mappings from partial payloads', () => {
    expect(
      normalizeModelTierConfig({
        light: { provider: 'openai', model: 'gpt-4o-mini' },
        heavy: { provider: 'anthropic', model: 'claude-3-7-sonnet' },
      }),
    ).toEqual({
      light: { provider: 'openai', model: 'gpt-4o-mini' },
      balanced: DEFAULT_MODEL_TIER_CONFIG.balanced,
      heavy: { provider: 'anthropic', model: 'claude-3-7-sonnet' },
    });
  });

  it('preserves existing voice_input_provider when saving preferences without provider field', () => {
    const formData = new FormData();
    formData.set('theme', 'dark');
    formData.set('language', 'zh');
    formData.set('default_agent', 'agent_1');
    formData.set('voice_input_language', 'zh-CN');

    const next = buildPreferencesFromFormData(formData, {
      ...DEFAULT_PREFERENCES,
      voice_input_provider: 'azure',
    });

    expect(next.voice_input_provider).toBe('azure');
  });
});
