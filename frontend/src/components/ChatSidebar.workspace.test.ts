import { describe, expect, it } from 'vitest';

import {
  filterChatsByWorkspace,
  formatWorkspaceCountLabel,
  getArtifactSourceLabels,
  getResearchFollowUpCandidates,
  getResearchArtifactMetadata,
  getWorkspaceEvidenceSummary,
  getWorkspaceSourceReadinessCounts,
  getWorkspaceSourceToolLabels,
} from './ChatSidebar.helpers';
import type { ChatSession, WorkspaceArtifact, WorkspaceSource } from '../types';

describe('ChatSidebar workspace filtering', () => {
  const chats: ChatSession[] = [
    {
      id: 'chat-1',
      title: 'Unscoped chat',
      updated_at: '2026-05-30T00:00:00Z',
      workspace_id: null,
    },
    {
      id: 'chat-2',
      title: 'Workspace chat',
      updated_at: '2026-05-30T00:00:00Z',
      workspace_id: 'ws_1',
    },
    {
      id: 'chat-3',
      title: 'Another workspace chat',
      updated_at: '2026-05-30T00:00:00Z',
      workspace_id: 'ws_2',
    },
  ];

  it('returns all chats when no workspace is selected', () => {
    expect(filterChatsByWorkspace(chats, null).map((chat) => chat.id)).toEqual(['chat-1', 'chat-2', 'chat-3']);
  });

  it('returns only chats assigned to the selected workspace', () => {
    expect(filterChatsByWorkspace(chats, 'ws_1').map((chat) => chat.id)).toEqual(['chat-2']);
  });
});

describe('ChatSidebar research artifact helpers', () => {
  const artifact: WorkspaceArtifact = {
    id: 'artifact-1',
    workspace_id: 'ws_1',
    artifact_type: 'research_report',
    title: 'Fallback question',
    artifact_metadata: {
      question: 'What changed?',
      summary: 'The answer summary.',
      source_ids: ['src_pdf', 'missing_src'],
      mode: 'require_sources',
      findings: [
        {
          claim: 'Cited claim',
          evidence_state: 'source_supported',
          citations: [{ source_id: 'src_pdf' }],
        },
        { claim: 'Unsupported claim', evidence_state: 'unsupported' },
      ],
      assumptions: ['Dates are inferred from the current plan.'],
      open_questions: ['What is unresolved?'],
      next_actions: ['Confirm source scope before follow-up research.'],
      export_paths: ['/tmp/report.md'],
      evidence_contract: {
        claim_states: {
          source_supported: 'Source-supported',
          inferred: 'Inferred',
          user_confirmed: 'User-confirmed',
          unsupported: 'Unsupported',
          missing_evidence: 'Missing evidence',
        },
        source_scope_preview: {
          mode: 'require_sources',
          source_ids: ['src_pdf', 'missing_src'],
          source_count: 2,
          unavailable_source_ids: ['missing_src'],
          citation_requirement: 'required',
        },
        citation_warnings: ['missing_src is unavailable'],
        missing_evidence: ['No source confirms the rollout date.'],
        durable_memory_write: 'requires_separate_user_confirmation',
      },
    },
    created_at: '2026-05-30T00:00:00Z',
    updated_at: '2026-05-30T00:00:00Z',
  };

  const sources: WorkspaceSource[] = [
    {
      id: 'src_pdf',
      workspace_id: 'ws_1',
      source_type: 'upload',
      source_ref: 'uploads/chat/report.pdf',
      display_name: 'Report.pdf',
      status: 'ready',
      created_at: '2026-05-30T00:00:00Z',
      updated_at: '2026-05-30T00:00:00Z',
    },
  ];

  it('normalizes research artifact metadata for the detail view', () => {
    expect(getResearchArtifactMetadata(artifact)).toMatchObject({
      question: 'What changed?',
      summary: 'The answer summary.',
      sourceIds: ['src_pdf', 'missing_src'],
      mode: 'require_sources',
      findings: [
        {
          claim: 'Cited claim',
          evidence_state: 'source_supported',
          citations: [{ source_id: 'src_pdf' }],
        },
        { claim: 'Unsupported claim', evidence_state: 'unsupported' },
      ],
      assumptions: ['Dates are inferred from the current plan.'],
      openQuestions: ['What is unresolved?'],
      nextActions: ['Confirm source scope before follow-up research.'],
      exportPaths: ['/tmp/report.md'],
      evidenceContract: {
        claimStates: {
          source_supported: 'Source-supported',
          inferred: 'Inferred',
          user_confirmed: 'User-confirmed',
          unsupported: 'Unsupported',
          missing_evidence: 'Missing evidence',
        },
        sourceScopePreview: {
          mode: 'require_sources',
          source_ids: ['src_pdf', 'missing_src'],
          source_count: 2,
          unavailable_source_ids: ['missing_src'],
          citation_requirement: 'required',
        },
        citationWarnings: ['missing_src is unavailable'],
        missingEvidence: ['No source confirms the rollout date.'],
        durableMemoryWrite: 'requires_separate_user_confirmation',
      },
    });
  });

  it('resolves artifact source ids to readable labels where possible', () => {
    expect(getArtifactSourceLabels(artifact, sources)).toEqual(['Report.pdf', 'missing_src']);
  });

  it('routes research gaps into questionnaire candidates and open decisions into Clarify input', () => {
    expect(getResearchFollowUpCandidates(artifact)).toEqual({
      questionnaireGaps: ['No source confirms the rollout date.'],
      clarifyQuestions: ['What is unresolved?'],
    });
    expect(
      getResearchFollowUpCandidates({
        ...artifact,
        artifact_type: 'session_handoff',
      }),
    ).toEqual({ questionnaireGaps: [], clarifyQuestions: [] });
  });

  it('summarizes selected evidence scope and grounding mode', () => {
    expect(getWorkspaceEvidenceSummary('selected', 'require_sources', sources, ['src_pdf', 'src_missing'])).toBe(
      '1/2 selected sources ready; citations required',
    );
  });

  it('counts ready and attention-needed sources for workspace summaries', () => {
    expect(
      getWorkspaceSourceReadinessCounts([
        sources[0],
        {
          id: 'src_csv',
          workspace_id: 'ws_1',
          source_type: 'upload',
          source_ref: 'uploads/chat/data.csv',
          display_name: 'Data.csv',
          status: 'unsupported_type',
          source_metadata: {},
          created_at: '2026-05-30T00:00:00Z',
          updated_at: '2026-05-30T00:00:00Z',
        },
      ]),
    ).toEqual({
      total: 2,
      ready: 1,
      attention: 1,
      citationReady: 0,
    });
  });

  it('formats singular and plural workspace count labels', () => {
    expect(formatWorkspaceCountLabel(1, 'saved artifact')).toBe('1 saved artifact');
    expect(formatWorkspaceCountLabel(2, 'saved artifact')).toBe('2 saved artifacts');
  });

  it('formats readiness tool labels for source cards', () => {
    expect(
      getWorkspaceSourceToolLabels({
        ...sources[0],
        source_metadata: {
          available_tools: ['docs_read_pdf', 'docs_search_pdf', 'excel_query'],
        },
      }),
    ).toEqual(['PDF read', 'PDF search']);
  });
});
