import { describe, expect, it } from 'vitest';
import {
  buildCustomModelCreatePayload,
  buildCustomModelTestPayload,
  normalizeCustomModelDraft,
  validateCustomModelDraft,
} from './customModelUtils';

describe('custom model payload builders', () => {
  const draft = {
    name: 'demo-custom',
    provider: 'deepseek',
    model: 'deepseek-chat',
    base_url: 'https://api.example.com/v1',
    api_key: 'sk-demo',
    capabilities: ['vision'],
  };

  it('includes provider when creating a custom model', () => {
    expect(buildCustomModelCreatePayload(draft)).toEqual({
      name: 'demo-custom',
      provider: 'deepseek',
      model: 'deepseek-chat',
      base_url: 'https://api.example.com/v1',
      api_key: 'sk-demo',
      capabilities: ['vision'],
    });
  });

  it('tests the draft values directly', () => {
    expect(buildCustomModelTestPayload(draft)).toEqual({
      provider: 'deepseek',
      model: 'deepseek-chat',
      base_url: 'https://api.example.com/v1',
      api_key: 'sk-demo',
    });
  });

  it('normalizes chat completion endpoints into provider base URLs', () => {
    expect(
      normalizeCustomModelDraft({
        name: ' local ',
        provider: 'openai',
        model: ' default ',
        base_url: ' http://localhost:8080/v1/chat/completions ',
        api_key: ' ',
        capabilities: [],
      }),
    ).toEqual({
      name: 'local',
      provider: 'openai',
      model: 'default',
      base_url: 'http://localhost:8080/v1',
      api_key: undefined,
      capabilities: [],
    });
  });

  it('validates required fields with user-facing messages', () => {
    expect(validateCustomModelDraft({ name: '', provider: 'openai', model: '', capabilities: [] })).toBe(
      'Name is required',
    );
    expect(validateCustomModelDraft({ name: 'local', provider: 'openai', model: '', capabilities: [] })).toBeNull();
    expect(
      validateCustomModelDraft({
        name: 'local',
        provider: 'openai',
        model: 'default',
        base_url: 'localhost:8080/v1',
        capabilities: [],
      }),
    ).toBe('Base URL must start with http:// or https://');
  });

  it('omits empty model ids from create and test payloads', () => {
    const optionalModelDraft = {
      name: 'local-openai',
      provider: 'openai',
      model: '   ',
      base_url: 'http://localhost:8080/v1',
      api_key: '',
      capabilities: [],
    };

    expect(buildCustomModelCreatePayload(optionalModelDraft)).toEqual({
      name: 'local-openai',
      provider: 'openai',
      model: undefined,
      base_url: 'http://localhost:8080/v1',
      api_key: undefined,
      capabilities: [],
    });

    expect(buildCustomModelTestPayload(optionalModelDraft)).toEqual({
      provider: 'openai',
      model: undefined,
      base_url: 'http://localhost:8080/v1',
      api_key: undefined,
    });
  });
});
