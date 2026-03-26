import { describe, expect, test } from 'vitest';

import { buildAgentPayload } from './useAgentsState';


describe('buildAgentPayload', () => {
  test('includes agent kind and skill group fields', () => {
    const payload = buildAgentPayload({
      name: 'Agent',
      systemPrompt: 'Prompt',
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
});
