import type {
  ChatSession,
  Workspace,
  WorkspaceArtifact,
  WorkspaceNote,
  WorkspaceMemoryCandidate,
  WorkspaceMemoryCard,
  WorkspaceMemoryDraft,
  WorkspaceSource,
} from '../../types';

export interface ChatSidebarProps {
  showHistory: boolean;
  setShowHistory: (show: boolean) => void;
  chats: ChatSession[];
  workspaces: Workspace[];
  selectedWorkspaceId: string | null;
  workspaceSources: WorkspaceSource[];
  workspaceArtifacts: WorkspaceArtifact[];
  workspaceNotes: WorkspaceNote[];
  workspaceMemories: WorkspaceMemoryCard[];
  workspaceMemoryCandidates: WorkspaceMemoryCandidate[];
  workspaceSourceMode: 'all_ready' | 'selected' | 'none';
  selectedWorkspaceSourceIds: string[];
  groundingMode: 'normal' | 'prefer_sources' | 'require_sources';
  workspaceLoading?: boolean;
  sourcesLoading?: boolean;
  artifactsLoading?: boolean;
  notesLoading?: boolean;
  memoriesLoading?: boolean;
  memorySuggestionsEnabled?: boolean;
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectWorkspace: (id: string | null) => void;
  onCreateWorkspace: (name: string) => Promise<void> | void;
  onWorkspaceSourceModeChange: (mode: 'all_ready' | 'selected' | 'none') => void;
  onToggleWorkspaceSource: (sourceId: string) => void;
  onGroundingModeChange: (mode: 'normal' | 'prefer_sources' | 'require_sources') => void;
  onCheckWorkspaceSources: () => Promise<void> | void;
  onCheckWorkspaceSource: (sourceId: string) => Promise<void> | void;
  onLoadChat: (id: string) => void;
  onSaveLastAssistantAsWorkspaceNote: () => Promise<WorkspaceNote | null>;
  onSuggestWorkspaceMemoryFromLastAssistantMessage: () => Promise<WorkspaceMemoryDraft | null>;
  onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage: () => Promise<WorkspaceMemoryCandidate | null>;
  onSuggestWorkspaceMemoryCandidateFromNote: (noteId: string) => Promise<WorkspaceMemoryCandidate | null>;
  onCreateWorkspaceMemory: (payload: {
    memory_type: string;
    scope_type?: string;
    scope_ref?: string | null;
    title: string;
    content: string;
    status?: string;
    confidence?: number | null;
    created_by?: string | null;
    why_saved?: string | null;
    pinned?: boolean;
    editable?: boolean;
    revocable?: boolean;
    source_session_id?: string | null;
    source_message_id?: number | null;
    expires_at?: string | null;
    memory_metadata?: Record<string, any>;
  }) => Promise<void> | void;
  onUpdateWorkspaceMemory: (
    memoryId: string,
    payload: {
      memory_type?: string;
      scope_type?: string;
      scope_ref?: string | null;
      title?: string;
      content?: string;
      status?: string;
      confidence?: number | null;
      created_by?: string | null;
      why_saved?: string | null;
      pinned?: boolean;
      editable?: boolean;
      revocable?: boolean;
      source_session_id?: string | null;
      source_message_id?: number | null;
      expires_at?: string | null;
      memory_metadata?: Record<string, any>;
    },
  ) => Promise<void> | void;
  onBulkUpdateWorkspaceMemoryStatusByType: (memoryType: string, status: string) => Promise<void> | void;
  onDeleteWorkspaceMemory: (memoryId: string) => Promise<void> | void;
  onApproveWorkspaceMemoryCandidate: (
    candidateId: string,
    payload: {
      approval_mode: string;
      target_memory_id?: string | null;
      memory_type?: string | null;
      scope_type?: string | null;
      scope_ref?: string | null;
      title?: string | null;
      content?: string | null;
      confidence?: number | null;
      why_saved?: string | null;
      expires_at?: string | null;
      pinned?: boolean | null;
    },
  ) => Promise<void> | void;
  onRejectWorkspaceMemoryCandidate: (candidateId: string, reason?: string | null) => Promise<void> | void;
  onDeleteChat: (id: string) => void;
  onGenerateSummary: (id: string) => void;
}

export type DatePreset = 'all' | 'today' | '7d' | '30d';
export type TagMode = 'any' | 'all';
export type FilterState = {
  query: string;
  selectedTags: string[];
  tagMode: TagMode;
  datePreset: DatePreset;
};
export type SavedPreset = FilterState & {
  id: string;
  name: string;
};

export type ChatSidebarGroup = {
  key: string;
  label: string;
  type: 'today' | 'yesterday' | 'last7days' | 'earlier';
  isToday: boolean;
  chats: ChatSession[];
};
