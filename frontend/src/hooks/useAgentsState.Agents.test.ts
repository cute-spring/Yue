import { describe, expect, test } from 'vitest';

import { buildAgentPayload, resolveAgentModelFormState } from './useAgentsState';


describe('buildAgentPayload', () => {
  test('includes agent kind and skill group fields', () => {
    const payload = buildAgentPayload({
      name: 'Agent',
      systemPrompt: 'Prompt',
      modelSelectionMode: 'tier',
      modelTier: 'balanced',
      provider: 'openai',
      model: 'gpt-4o',
      enabledTools: ['builtin:docs_read'],
      voiceInputEnabled: true,
      voiceInputProvider: 'azure',
      voiceAzureRegion: 'eastus',
      voiceAzureEndpointId: 'endpoint-1',
      voiceAzureApiKey: 'secret',
      skillMode: 'manual',
      visibleSkills: ['planner:1.0.0'],
      agentKind: 'universal',
      skillGroups: ['group-1'],
      extraVisibleSkills: ['coder:1.0.0'],
      docRoots: ['/tmp/docs'],
      docFilePatternsText: '**/*.md\n#ignored\n',
    });

    expect(payload.agent_kind).toBe('universal');
    expect(payload.model_selection_mode).toBe('tier');
    expect(payload.model_tier).toBe('balanced');
    expect(payload.skill_groups).toEqual(['group-1']);
    expect(payload.extra_visible_skills).toEqual(['coder:1.0.0']);
    expect(payload.visible_skills).toEqual(['planner:1.0.0']);
    expect(payload.doc_file_patterns).toEqual(['**/*.md']);
    expect(payload.voice_input_provider).toBe('azure');
    expect(payload.voice_azure_config).toEqual({
      region: 'eastus',
      endpoint_id: 'endpoint-1',
      api_key: 'secret',
    });
  });

  test('defaults create flow to tier mode', () => {
    expect(resolveAgentModelFormState()).toEqual({
      modelSelectionMode: 'tier',
      modelTier: 'balanced',
      provider: 'openai',
      model: 'gpt-4o',
    });
  });

  test('keeps direct mode when editing legacy agent without tier fields', () => {
    expect(
      resolveAgentModelFormState({
        provider: 'deepseek',
        model: 'deepseek-chat',
      }),
    ).toEqual({
      modelSelectionMode: 'direct',
      modelTier: 'balanced',
      provider: 'deepseek',
      model: 'deepseek-chat',
    });
  });

  test('keeps direct mode when explicit override is present alongside tier metadata', () => {
    expect(
      resolveAgentModelFormState({
        provider: 'openai',
        model: 'gpt-4o',
        model_selection_mode: 'direct',
        model_tier: 'heavy',
      }),
    ).toEqual({
      modelSelectionMode: 'direct',
      modelTier: 'heavy',
      provider: 'openai',
      model: 'gpt-4o',
    });
  });

  test('infers tier mode from persisted tier metadata when selection mode is absent', () => {
    expect(
      resolveAgentModelFormState({
        provider: 'anthropic',
        model: 'claude-3-7-sonnet',
        model_tier: 'heavy',
      }),
    ).toEqual({
      modelSelectionMode: 'tier',
      modelTier: 'heavy',
      provider: 'anthropic',
      model: 'claude-3-7-sonnet',
    });
  });
});
