import { describe, expect, it } from 'vitest';

import type { WorkspaceMemoryCandidate } from '../../types';
import InlineMemoryConfirmation, {
  buildInlineMemoryApprovalPayload,
  getCandidateDestinationLabel,
} from './InlineMemoryConfirmation';

const candidate: WorkspaceMemoryCandidate = {
  id: 'candidate_1',
  workspace_id: 'workspace_1',
  memory_type: 'preference',
  scope_type: 'workspace',
  scope_ref: null,
  title: 'Simple workspace',
  content: 'The user prefers a simple, concise Workspace design.',
  status: 'pending',
  score: 0.82,
  suggested_action: null,
  conflict_memory_id: null,
  why_saved: 'User explicitly confirmed this preference.',
  source_session_id: 'chat_1',
  source_message_id: 10,
  reviewed_at: null,
  expires_at: null,
  source: null,
  candidate_metadata: {},
  created_at: '2026-09-08T00:00:00Z',
  updated_at: '2026-09-08T00:00:00Z',
};

describe('InlineMemoryConfirmation', () => {
  it('exports a stable component function', () => {
    expect(typeof InlineMemoryConfirmation).toBe('function');
  });

  it('builds a remember payload for a new memory candidate', () => {
    expect(buildInlineMemoryApprovalPayload(candidate)).toEqual({
      approval_mode: 'create_new',
      target_memory_id: null,
      memory_type: 'preference',
      scope_type: 'workspace',
      scope_ref: null,
      title: 'Simple workspace',
      content: 'The user prefers a simple, concise Workspace design.',
      confidence: 0.82,
      why_saved: 'User explicitly confirmed this preference.',
      expires_at: null,
    });
  });

  it('uses edited title and content before saving', () => {
    expect(
      buildInlineMemoryApprovalPayload(candidate, {
        title: '  Keep workspace simple  ',
        content: '  Keep the Workspace UI simple and non-adaptive.  ',
      }),
    ).toMatchObject({
      title: 'Keep workspace simple',
      content: 'Keep the Workspace UI simple and non-adaptive.',
    });
  });

  it('labels user-scoped memory separately from workspace memory', () => {
    expect(getCandidateDestinationLabel({ ...candidate, scope_type: 'user' })).toBe('About You');
    expect(getCandidateDestinationLabel({ ...candidate, scope_type: 'chat' })).toBe('Just this time');
    expect(getCandidateDestinationLabel(candidate)).toBe('This Workspace');
  });
});
