import { describe, expect, it } from 'vitest';
import { getModelCapabilityBadges } from './LLMSelector';

describe('LLMSelector vision capability badges', () => {
  it('returns Vision badge when model has vision capability', () => {
    const badges = getModelCapabilityBadges(
      {
        name: 'openai',
        supports_model_refresh: true,
        models: ['gpt-4o'],
        available_models: ['gpt-4o'],
        model_capabilities: {
          'gpt-4o': ['vision', 'reasoning'],
        },
      },
      'gpt-4o',
    );
    expect(badges).toContain('Vision');
  });

  it('returns empty badges when capability is not declared', () => {
    const badges = getModelCapabilityBadges(
      {
        name: 'openai',
        supports_model_refresh: true,
        models: ['gpt-4o-mini'],
        available_models: ['gpt-4o-mini'],
      },
      'gpt-4o-mini',
    );
    expect(badges).toEqual([]);
  });
});
