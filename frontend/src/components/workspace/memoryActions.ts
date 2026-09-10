import type { WorkspaceMemoryCandidate, WorkspaceMemoryCandidateAction } from '../../types';

export const resolveWorkspaceMemoryCandidateAction = (
  candidate: Pick<WorkspaceMemoryCandidate, 'suggested_action' | 'conflict_memory_id'>,
): WorkspaceMemoryCandidateAction =>
  candidate.suggested_action || (candidate.conflict_memory_id ? 'update_existing' : 'create_new');

export const formatWorkspaceMemoryCandidateAction = (action?: WorkspaceMemoryCandidateAction | null) => {
  switch (action) {
    case 'archive_existing':
      return 'Archive existing';
    case 'replace_existing':
      return 'Replace existing';
    case 'update_existing':
      return 'Update existing';
    case 'create_new':
      return 'Create new';
    default:
      return 'Review';
  }
};

export const getWorkspaceMemoryCandidateConfirmationCopy = (
  action: WorkspaceMemoryCandidateAction,
  destination: string,
) => {
  switch (action) {
    case 'archive_existing':
      return 'Yue can archive the conflicting memory so it stops shaping future replies.';
    case 'replace_existing':
      return `Yue can replace the conflicting memory for ${destination}.`;
    case 'update_existing':
      return `Yue can update the conflicting memory for ${destination}.`;
    default:
      return `Yue can remember this for ${destination}.`;
  }
};
