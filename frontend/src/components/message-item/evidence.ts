import { Message } from '../../types';

type WorkspaceEvidenceMessage = Pick<Message, 'workspace_grounding' | 'citations'>;

export const getWorkspaceGroundingModeLabel = (mode?: string | null): string => {
  if (mode === 'require_sources') return 'Citations required';
  if (mode === 'prefer_sources') return 'Citations preferred';
  return 'Sources optional';
};

export const getWorkspaceSourceModeLabel = (mode?: string | null): string => {
  if (mode === 'selected') return 'Selected sources';
  if (mode === 'none') return 'No workspace sources';
  return 'All ready sources';
};

export const getWorkspaceGroundingSummary = (msg: WorkspaceEvidenceMessage): string => {
  const grounding = msg.workspace_grounding;
  if (!grounding) return '';
  const eligibleCount = grounding.eligible_sources?.length ?? 0;
  const unavailableCount = grounding.unavailable_sources?.length ?? 0;
  const citationCount = msg.citations?.length ?? 0;
  const sourceMode = getWorkspaceSourceModeLabel(grounding.workspace_source_mode);
  const groundingMode = getWorkspaceGroundingModeLabel(grounding.grounding_mode);
  if (grounding.workspace_source_mode === 'none') {
    return `${sourceMode}; ${groundingMode}`;
  }
  const eligibleText = `${eligibleCount} eligible source${eligibleCount === 1 ? '' : 's'}`;
  const unavailableText = unavailableCount > 0 ? `, ${unavailableCount} unavailable` : '';
  const citationText = citationCount > 0 ? `${citationCount} citations attached` : 'No citations attached';
  return `${sourceMode}; ${groundingMode}; ${eligibleText}${unavailableText}; ${citationText}`;
};

export const getWorkspaceToolingWarning = (msg: Pick<Message, 'workspace_grounding'>): string => {
  const warning = msg.workspace_grounding?.tooling_warning;
  return typeof warning === 'string' ? warning : '';
};

export const getWorkspaceCitationWarning = (msg: WorkspaceEvidenceMessage): string => {
  const grounding = msg.workspace_grounding;
  if (!grounding || grounding.grounding_mode !== 'require_sources') return '';
  const citationCount = msg.citations?.length ?? 0;
  if (citationCount > 0) return '';
  const eligibleCount = grounding.eligible_sources?.length ?? 0;
  if (eligibleCount === 0) {
    return 'Citation-required mode was active, but no eligible workspace sources were available for this turn.';
  }
  return 'Citation-required mode was active. If this answer makes source-specific claims without citations, treat it as needing follow-up verification.';
};

export const formatCitationSourceLabel = (citation: {
  path?: unknown;
  start_line?: unknown;
  end_line?: unknown;
  start_page?: unknown;
  end_page?: unknown;
}): string => {
  const path = typeof citation.path === 'string' ? citation.path : '';
  const startLine = typeof citation.start_line === 'number' ? citation.start_line : null;
  const endLine = typeof citation.end_line === 'number' ? citation.end_line : null;
  const startPage = typeof citation.start_page === 'number' ? citation.start_page : null;
  const endPage = typeof citation.end_page === 'number' ? citation.end_page : null;
  if (path && startLine !== null && endLine !== null) return `${path}#L${startLine}-L${endLine}`;
  if (path && startPage !== null && endPage !== null) return `${path}#P${startPage}-P${endPage}`;
  return path || 'Unknown source';
};
