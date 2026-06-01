import type { ChatSession, WorkspaceArtifact, WorkspaceSource } from '../types';

export const filterChatsByWorkspace = (
  chats: ChatSession[],
  selectedWorkspaceId: string | null,
): ChatSession[] => {
  if (!selectedWorkspaceId) return chats;
  return chats.filter((chat) => (chat.workspace_id || null) === selectedWorkspaceId);
};

export type ResearchArtifactMetadata = {
  question: string;
  summary: string;
  sourceIds: string[];
  mode: string;
  openQuestions: string[];
  exportPaths: string[];
};

export const getResearchArtifactMetadata = (artifact: WorkspaceArtifact): ResearchArtifactMetadata => {
  const metadata = artifact.artifact_metadata || {};
  return {
    question: typeof metadata.question === 'string' && metadata.question.trim() ? metadata.question : artifact.title,
    summary: typeof metadata.summary === 'string' ? metadata.summary : '',
    sourceIds: Array.isArray(metadata.source_ids)
      ? metadata.source_ids.filter((value: unknown): value is string => typeof value === 'string' && value.length > 0)
      : [],
    mode: typeof metadata.mode === 'string' && metadata.mode.trim() ? metadata.mode : 'normal',
    openQuestions: Array.isArray(metadata.open_questions)
      ? metadata.open_questions.filter((value: unknown): value is string => typeof value === 'string' && value.trim().length > 0)
      : [],
    exportPaths: Array.isArray(metadata.export_paths)
      ? metadata.export_paths.filter((value: unknown): value is string => typeof value === 'string' && value.trim().length > 0)
      : [],
  };
};

export const formatWorkspaceArtifactType = (artifactType: string): string =>
  artifactType
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Artifact';

export const getWorkspaceSourceLabel = (sourceId: string, sources: WorkspaceSource[]): string => {
  const source = sources.find((item) => item.id === sourceId);
  return source?.display_name || source?.source_ref || sourceId;
};

export const formatWorkspaceSourceTool = (tool: string): string => {
  const normalized = tool.trim();
  const labels: Record<string, string> = {
    docs_read_pdf: 'PDF read',
    docs_search_pdf: 'PDF search',
    docs_read: 'Doc read',
    docs_search: 'Doc search',
    excel_profile: 'Excel profile',
    excel_read: 'Excel read',
    excel_query: 'Excel query',
  };
  return labels[normalized] || normalized.replace(/[_-]+/g, ' ');
};

export const getWorkspaceSourceToolLabels = (source: WorkspaceSource, limit = 2): string[] => {
  const tools = Array.isArray(source.source_metadata?.available_tools)
    ? source.source_metadata.available_tools.filter((tool: unknown): tool is string => typeof tool === 'string' && tool.trim().length > 0)
    : [];
  return tools.slice(0, limit).map(formatWorkspaceSourceTool);
};

export const getArtifactSourceLabels = (
  artifact: WorkspaceArtifact,
  sources: WorkspaceSource[],
): string[] => getResearchArtifactMetadata(artifact).sourceIds.map((sourceId) => getWorkspaceSourceLabel(sourceId, sources));

export const getWorkspaceEvidenceSummary = (
  workspaceSourceMode: 'all_ready' | 'selected' | 'none',
  groundingMode: 'normal' | 'prefer_sources' | 'require_sources',
  sources: WorkspaceSource[],
  selectedSourceIds: string[],
): string => {
  const readySources = sources.filter((source) => source.status === 'ready');
  const selectedReadyCount = readySources.filter((source) => selectedSourceIds.includes(source.id)).length;
  const sourceLabel =
    workspaceSourceMode === 'none'
      ? 'No sources will be used'
      : workspaceSourceMode === 'selected'
        ? `${selectedReadyCount}/${selectedSourceIds.length} selected sources ready`
        : `${readySources.length}/${sources.length} sources ready`;
  const groundingLabel =
    groundingMode === 'require_sources'
      ? 'citations required'
      : groundingMode === 'prefer_sources'
        ? 'citations preferred'
        : 'sources optional';
  return `${sourceLabel}; ${groundingLabel}`;
};
