import { describe, expect, it } from 'vitest';

import type { WorkspaceUnderstandingSummary } from '../../types';
import WorkspaceUnderstandingPanel, {
  WORKSPACE_UNDERSTANDING_GROUP_DEFINITIONS,
  buildWorkspaceUnderstandingMetrics,
  normalizeWorkspaceUnderstandingGroups,
} from './WorkspaceUnderstandingPanel';

const summary: WorkspaceUnderstandingSummary = {
  workspace_id: 'ws_1',
  groups: [
    {
      group: 'background',
      label: 'Background',
      total_count: 2,
      active_count: 2,
      pending_count: 0,
      representative_items: [],
    },
    {
      group: 'open_questions',
      label: 'Open Questions',
      total_count: 0,
      active_count: 0,
      pending_count: 1,
      representative_items: [],
    },
  ],
  applied_user_memory_preview: [],
};

describe('WorkspaceUnderstandingPanel', () => {
  it('exports a stable component function', () => {
    expect(typeof WorkspaceUnderstandingPanel).toBe('function');
  });

  it('builds compact status metrics from understanding summary first', () => {
    expect(buildWorkspaceUnderstandingMetrics(summary, 9, 8, 3, 4, 5)).toEqual({
      savedUnderstandingCount: 2,
      pendingCount: 1,
      sourceCount: 3,
      noteArtifactCount: 9,
    });
  });

  it('normalizes partial responses into the fixed eight-group order', () => {
    const groups = normalizeWorkspaceUnderstandingGroups(summary);

    expect(groups.map((group) => group.group)).toEqual(
      WORKSPACE_UNDERSTANDING_GROUP_DEFINITIONS.map((group) => group.group),
    );
    expect(groups.find((group) => group.group === 'background')?.total_count).toBe(2);
    expect(groups.find((group) => group.group === 'goals')?.total_count).toBe(0);
    expect(groups.find((group) => group.group === 'current_state')?.label).toBe('Current State');
  });

  it('falls back to existing workspace resource counts before summary loads', () => {
    expect(buildWorkspaceUnderstandingMetrics(null, 9, 8, 3, 4, 5)).toEqual({
      savedUnderstandingCount: 9,
      pendingCount: 8,
      sourceCount: 3,
      noteArtifactCount: 9,
    });
  });
});
