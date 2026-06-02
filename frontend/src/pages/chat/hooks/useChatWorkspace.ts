import { Accessor, Setter, createEffect, createMemo, createSignal } from 'solid-js';
import { Message, Workspace, WorkspaceArtifact, WorkspaceSource } from '../../../types';

type WorkspaceSourceMode = 'all_ready' | 'selected' | 'none';
type GroundingMode = 'normal' | 'prefer_sources' | 'require_sources';

type ToastLike = {
  error: (message: string, duration?: number) => void;
  success: (message: string, duration?: number) => void;
};

type WorkspaceRequestOverrides = {
  workspace_source_mode?: WorkspaceSourceMode;
  selected_workspace_source_ids?: string[];
  grounding_mode?: GroundingMode;
};

type UseChatWorkspaceArgs = {
  toast: ToastLike;
  selectedWorkspaceId: Accessor<string | null>;
  setSelectedWorkspaceId: Setter<string | null>;
  startNewChat: (isMobile: boolean, setShowHistory: (value: boolean) => void) => void;
  isMobile: Accessor<boolean>;
  setShowHistory: (value: boolean) => void;
  currentChatId: Accessor<string | null>;
  messages: Accessor<Message[]>;
};

export function useChatWorkspace(args: UseChatWorkspaceArgs) {
  const [workspaces, setWorkspaces] = createSignal<Workspace[]>([]);
  const [workspaceSources, setWorkspaceSources] = createSignal<WorkspaceSource[]>([]);
  const [workspaceArtifacts, setWorkspaceArtifacts] = createSignal<WorkspaceArtifact[]>([]);
  const [workspaceSourceMode, setWorkspaceSourceMode] = createSignal<WorkspaceSourceMode>('all_ready');
  const [selectedWorkspaceSourceIds, setSelectedWorkspaceSourceIds] = createSignal<string[]>([]);
  const [groundingMode, setGroundingMode] = createSignal<GroundingMode>('normal');
  const [workspaceLoading, setWorkspaceLoading] = createSignal(false);
  const [sourcesLoading, setSourcesLoading] = createSignal(false);
  const [artifactsLoading, setArtifactsLoading] = createSignal(false);

  const selectedWorkspace = createMemo(
    () => workspaces().find((workspace) => workspace.id === args.selectedWorkspaceId()) || null,
  );

  const loadWorkspaces = async (preferredWorkspaceId?: string | null) => {
    setWorkspaceLoading(true);
    try {
      const res = await fetch('/api/workspaces/');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const next = Array.isArray(data) ? (data as Workspace[]) : [];
      setWorkspaces(next);

      const preferred =
        preferredWorkspaceId === undefined ? args.selectedWorkspaceId() : preferredWorkspaceId;

      if (preferred && next.some((workspace) => workspace.id === preferred)) {
        args.setSelectedWorkspaceId(preferred);
      } else if (preferred === null) {
        args.setSelectedWorkspaceId(null);
      } else if (
        args.selectedWorkspaceId() &&
        !next.some((workspace) => workspace.id === args.selectedWorkspaceId())
      ) {
        args.setSelectedWorkspaceId(null);
      }
    } catch (e) {
      console.error('Failed to load workspaces', e);
      args.toast.error('Failed to load workspaces');
    } finally {
      setWorkspaceLoading(false);
    }
  };

  const loadWorkspaceSources = async (workspaceId: string | null) => {
    if (!workspaceId) {
      setWorkspaceSources([]);
      return;
    }

    setSourcesLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/sources`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const next = Array.isArray(data) ? (data as WorkspaceSource[]) : [];
      setWorkspaceSources(next);
      setSelectedWorkspaceSourceIds((prev) =>
        prev.filter((id) => next.some((source) => source.id === id)),
      );
    } catch (e) {
      console.error('Failed to load workspace sources', e);
      args.toast.error('Failed to load workspace sources');
      setWorkspaceSources([]);
    } finally {
      setSourcesLoading(false);
    }
  };

  const checkWorkspaceSources = async () => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) return;

    setSourcesLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/sources/check`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceSources(workspaceId);
      args.toast.success('Workspace sources checked');
    } catch (e) {
      console.error('Failed to check workspace sources', e);
      args.toast.error('Failed to check workspace sources');
    } finally {
      setSourcesLoading(false);
    }
  };

  const checkWorkspaceSource = async (sourceId: string) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) return;

    setSourcesLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/sources/${sourceId}/check`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceSources(workspaceId);
    } catch (e) {
      console.error('Failed to check workspace source', e);
      args.toast.error('Failed to check workspace source');
    } finally {
      setSourcesLoading(false);
    }
  };

  const loadWorkspaceArtifacts = async (workspaceId: string | null) => {
    if (!workspaceId) {
      setWorkspaceArtifacts([]);
      return;
    }

    setArtifactsLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/artifacts`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setWorkspaceArtifacts(Array.isArray(data) ? (data as WorkspaceArtifact[]) : []);
    } catch (e) {
      console.error('Failed to load workspace artifacts', e);
      args.toast.error('Failed to load workspace artifacts');
      setWorkspaceArtifacts([]);
    } finally {
      setArtifactsLoading(false);
    }
  };

  const handleSelectWorkspace = (workspaceId: string | null) => {
    if (args.selectedWorkspaceId() === workspaceId) return;

    args.setSelectedWorkspaceId(workspaceId);
    setWorkspaceSourceMode('all_ready');
    setSelectedWorkspaceSourceIds([]);
    setGroundingMode('normal');
    args.startNewChat(args.isMobile(), args.setShowHistory);
  };

  const toggleWorkspaceSource = (sourceId: string) => {
    setSelectedWorkspaceSourceIds((prev) =>
      prev.includes(sourceId) ? prev.filter((id) => id !== sourceId) : [...prev, sourceId],
    );
  };

  const buildWorkspaceRequestOverrides = (): WorkspaceRequestOverrides => {
    if (!args.selectedWorkspaceId()) return {};
    return {
      workspace_source_mode: workspaceSourceMode(),
      selected_workspace_source_ids:
        workspaceSourceMode() === 'selected' ? selectedWorkspaceSourceIds() : undefined,
      grounding_mode: groundingMode(),
    };
  };

  const effectiveWorkspaceSourceIds = () => {
    if (workspaceSourceMode() === 'none') return [];
    if (workspaceSourceMode() === 'selected') return selectedWorkspaceSourceIds();
    return workspaceSources()
      .filter((source) => source.status === 'ready')
      .map((source) => source.id);
  };

  const saveLastAssistantAsWorkspaceNote = async () => {
    const workspaceId = args.selectedWorkspaceId();
    const chatId = args.currentChatId();
    const lastAssistantMsg = [...args.messages()].reverse().find((message) => message.role === 'assistant');

    if (!workspaceId || !chatId || !lastAssistantMsg) {
      args.toast.error('No workspace assistant message to save.', 3000);
      return;
    }

    const res = await fetch(`/api/workspaces/${workspaceId}/notes/from-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        message_id: typeof lastAssistantMsg.id === 'number' ? lastAssistantMsg.id : undefined,
        title: lastAssistantMsg.content.slice(0, 60) || 'Workspace note',
        source_ids: effectiveWorkspaceSourceIds(),
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  };

  const saveLastAssistantAsResearchArtifact = async () => {
    const workspaceId = args.selectedWorkspaceId();
    const chatId = args.currentChatId();
    const lastAssistantMsg = [...args.messages()].reverse().find((message) => message.role === 'assistant');

    if (!workspaceId || !chatId || !lastAssistantMsg) {
      args.toast.error('No workspace assistant message to save.', 3000);
      return;
    }

    const question =
      [...args.messages()].reverse().find((message) => message.role === 'user')?.content ||
      'Workspace research artifact';
    const res = await fetch(`/api/workspaces/${workspaceId}/research-artifacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        summary: lastAssistantMsg.content,
        source_ids: effectiveWorkspaceSourceIds(),
        mode: groundingMode(),
        source_session_id: chatId,
        source_message_id: typeof lastAssistantMsg.id === 'number' ? lastAssistantMsg.id : undefined,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await loadWorkspaceArtifacts(workspaceId);
  };

  const handleCreateWorkspace = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;

    try {
      const res = await fetch('/api/workspaces/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const workspace = (await res.json()) as Workspace;
      await loadWorkspaces(workspace.id);
      args.setSelectedWorkspaceId(workspace.id);
      args.startNewChat(args.isMobile(), args.setShowHistory);
      args.toast.success('Workspace created');
    } catch (e) {
      console.error('Failed to create workspace', e);
      args.toast.error('Failed to create workspace');
    }
  };

  createEffect(() => {
    void loadWorkspaceSources(args.selectedWorkspaceId());
  });

  createEffect(() => {
    void loadWorkspaceArtifacts(args.selectedWorkspaceId());
  });

  return {
    workspaces,
    workspaceSources,
    workspaceArtifacts,
    workspaceSourceMode,
    setWorkspaceSourceMode,
    selectedWorkspaceSourceIds,
    groundingMode,
    setGroundingMode,
    workspaceLoading,
    sourcesLoading,
    artifactsLoading,
    selectedWorkspace,
    loadWorkspaces,
    checkWorkspaceSources,
    checkWorkspaceSource,
    handleSelectWorkspace,
    toggleWorkspaceSource,
    buildWorkspaceRequestOverrides,
    saveLastAssistantAsWorkspaceNote,
    saveLastAssistantAsResearchArtifact,
    handleCreateWorkspace,
  };
}
