import { describe, expect, it } from 'vitest';
import { DEFAULT_PREFERENCES, normalizePreferences } from './types';

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
});
