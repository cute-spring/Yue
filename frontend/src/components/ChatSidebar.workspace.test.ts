import { describe, expect, it } from 'vitest';

import {
  filterChatsByWorkspace,
  getArtifactSourceLabels,
  getResearchArtifactMetadata,
  getWorkspaceEvidenceSummary,
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
      open_questions: ['What is unresolved?'],
      export_paths: ['/tmp/report.md'],
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
      openQuestions: ['What is unresolved?'],
      exportPaths: ['/tmp/report.md'],
    });
  });

  it('resolves artifact source ids to readable labels where possible', () => {
    expect(getArtifactSourceLabels(artifact, sources)).toEqual(['Report.pdf', 'missing_src']);
  });

  it('summarizes selected evidence scope and grounding mode', () => {
    expect(getWorkspaceEvidenceSummary('selected', 'require_sources', sources, ['src_pdf', 'src_missing'])).toBe(
      '1/2 selected sources ready; citations required',
    );
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
