import { createRoot } from 'solid-js';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

import type { Agent } from '../types';
import { buildAgentPayload, resolveAgentModelFormState, useAgentsState } from './useAgentsState';

const originalWindow = (globalThis as any).window;
const originalFetch = globalThis.fetch;

beforeEach(() => {
  (globalThis as any).window = {
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/api/agents/')) return new Response(JSON.stringify([]));
    if (url.includes('/api/mcp/tools')) return new Response(JSON.stringify([]));
    if (url.includes('/api/models/providers')) return new Response(JSON.stringify([]));
    if (url.includes('/api/config/doc_access')) return new Response(JSON.stringify({}));
    if (url.includes('/api/skills/reload')) return new Response(JSON.stringify({}));
    if (url.includes('/api/skills')) return new Response(JSON.stringify([]));
    if (url.includes('/api/skill-groups/')) return new Response(JSON.stringify([]));
    return new Response(JSON.stringify({}));
  }) as typeof fetch;
});

afterEach(() => {
  (globalThis as any).window = originalWindow;
  globalThis.fetch = originalFetch;
});


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

  test('openEdit should preserve persisted voice input provider instead of forcing browser', () => {
    const agent = {
      id: 'a-1',
      name: 'Agent A',
      system_prompt: 'prompt',
      provider: 'openai',
      model: 'gpt-4o',
      enabled_tools: [],
      voice_input_enabled: true,
      voice_input_provider: 'azure',
    } as Agent;

    createRoot(dispose => {
      const state = useAgentsState();
      state.openEdit(agent);
      expect(state.formVoiceInputProvider()).toBe('azure');
      dispose();
    });
  });
});
