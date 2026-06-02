import type { ChatSession, Workspace, WorkspaceArtifact, WorkspaceSource } from '../../types';

export interface ChatSidebarProps {
  showHistory: boolean;
  setShowHistory: (show: boolean) => void;
  chats: ChatSession[];
  workspaces: Workspace[];
  selectedWorkspaceId: string | null;
  workspaceSources: WorkspaceSource[];
  workspaceArtifacts: WorkspaceArtifact[];
  workspaceSourceMode: 'all_ready' | 'selected' | 'none';
  selectedWorkspaceSourceIds: string[];
  groundingMode: 'normal' | 'prefer_sources' | 'require_sources';
  workspaceLoading?: boolean;
  sourcesLoading?: boolean;
  artifactsLoading?: boolean;
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
