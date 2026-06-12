import { Accessor, Setter, createEffect, createMemo, createSignal } from 'solid-js';
import {
  Message,
  Workspace,
  WorkspaceArtifact,
  WorkspaceNote,
  WorkspaceMemoryCandidate,
  WorkspaceMemoryCard,
  WorkspaceMemoryDraft,
  WorkspaceSource,
} from '../../../types';

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
  note_recall_enabled?: boolean;
  capture_suggestions_enabled?: boolean;
  memory_suggestions_enabled?: boolean;
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
  const [workspaceNotes, setWorkspaceNotes] = createSignal<WorkspaceNote[]>([]);
  const [workspaceMemories, setWorkspaceMemories] = createSignal<WorkspaceMemoryCard[]>([]);
  const [workspaceMemoryCandidates, setWorkspaceMemoryCandidates] = createSignal<WorkspaceMemoryCandidate[]>([]);
  const [workspaceSourceMode, setWorkspaceSourceMode] = createSignal<WorkspaceSourceMode>('all_ready');
  const [selectedWorkspaceSourceIds, setSelectedWorkspaceSourceIds] = createSignal<string[]>([]);
  const [groundingMode, setGroundingMode] = createSignal<GroundingMode>('normal');
  const [workspaceLoading, setWorkspaceLoading] = createSignal(false);
  const [sourcesLoading, setSourcesLoading] = createSignal(false);
  const [artifactsLoading, setArtifactsLoading] = createSignal(false);
  const [notesLoading, setNotesLoading] = createSignal(false);
  const [memoriesLoading, setMemoriesLoading] = createSignal(false);

  const selectedWorkspace = createMemo(
    () => workspaces().find((workspace) => workspace.id === args.selectedWorkspaceId()) || null,
  );

  const readErrorDetail = async (res: Response) => {
    try {
      const payload = await res.json();
      if (typeof payload?.detail === 'string' && payload.detail.trim()) {
        return payload.detail.trim();
      }
    } catch {
      // Ignore non-JSON error bodies and fall back to status text.
    }
    return `HTTP ${res.status}`;
  };

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

  const loadWorkspaceNotes = async (workspaceId: string | null) => {
    if (!workspaceId) {
      setWorkspaceNotes([]);
      return;
    }

    setNotesLoading(true);
    try {
      const params = new URLSearchParams({ workspace_id: workspaceId, include_promotion_hints: 'true' });
      const res = await fetch(`/api/notebook/?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setWorkspaceNotes(Array.isArray(data) ? (data as WorkspaceNote[]) : []);
    } catch (e) {
      console.error('Failed to load workspace notes', e);
      args.toast.error('Failed to load workspace notes');
      setWorkspaceNotes([]);
    } finally {
      setNotesLoading(false);
    }
  };

  const loadWorkspaceMemories = async (workspaceId: string | null) => {
    if (!workspaceId) {
      setWorkspaceMemories([]);
      setWorkspaceMemoryCandidates([]);
      return;
    }

    setMemoriesLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/memory`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setWorkspaceMemories(Array.isArray(data) ? (data as WorkspaceMemoryCard[]) : []);

      const candidateRes = await fetch(`/api/workspaces/${workspaceId}/memory-candidates`);
      if (!candidateRes.ok) throw new Error(`HTTP ${candidateRes.status}`);
      const candidateData = await candidateRes.json();
      setWorkspaceMemoryCandidates(Array.isArray(candidateData) ? (candidateData as WorkspaceMemoryCandidate[]) : []);
    } catch (e) {
      console.error('Failed to load workspace memories', e);
      args.toast.error('Failed to load workspace memories');
      setWorkspaceMemories([]);
      setWorkspaceMemoryCandidates([]);
    } finally {
      setMemoriesLoading(false);
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

  const trackWorkspaceCaptureTelemetry = async (payload: {
    event_type: string;
    source?: string;
    chat_id?: string | null;
    workspace_id?: string | null;
    assistant_message_id?: number | string | null;
    assistant_turn_id?: string | null;
    run_id?: string | null;
    note_id?: string | null;
    candidate_id?: string | null;
    accepted?: boolean | null;
    metadata?: Record<string, any>;
  }) => {
    const chatId = payload.chat_id ?? args.currentChatId();
    if (!chatId) return;
    try {
      await fetch(`/api/chat/${chatId}/capture-events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: payload.workspace_id ?? args.selectedWorkspaceId(),
          event_type: payload.event_type,
          source: payload.source || 'chat',
          assistant_message_id: payload.assistant_message_id ?? undefined,
          assistant_turn_id: payload.assistant_turn_id ?? undefined,
          run_id: payload.run_id ?? undefined,
          note_id: payload.note_id ?? undefined,
          candidate_id: payload.candidate_id ?? undefined,
          accepted: payload.accepted ?? undefined,
          metadata: payload.metadata || {},
        }),
      });
    } catch (error) {
      console.warn('Failed to track workspace capture telemetry', error);
    }
  };

  const effectiveWorkspaceSourceIds = () => {
    if (workspaceSourceMode() === 'none') return [];
    if (workspaceSourceMode() === 'selected') return selectedWorkspaceSourceIds();
    return workspaceSources()
      .filter((source) => source.status === 'ready')
      .map((source) => source.id);
  };

  const saveLastAssistantAsWorkspaceNote = async (): Promise<WorkspaceNote | null> => {
    const workspaceId = args.selectedWorkspaceId();
    const chatId = args.currentChatId();
    const lastAssistantMsg = [...args.messages()].reverse().find((message) => message.role === 'assistant');

    if (!workspaceId || !chatId || !lastAssistantMsg) {
      args.toast.error('No workspace assistant message to save.', 3000);
      return null;
    }

    const res = await fetch(`/api/workspaces/${workspaceId}/notes/from-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        message_id: typeof lastAssistantMsg.id === 'number' ? lastAssistantMsg.id : undefined,
        source_ids: effectiveWorkspaceSourceIds(),
        citation_refs: lastAssistantMsg.citations || [],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const note = (await res.json()) as WorkspaceNote;
    await loadWorkspaceNotes(workspaceId);
    await trackWorkspaceCaptureTelemetry({
      event_type: 'note_saved',
      source: 'chat_command',
      workspace_id: workspaceId,
      assistant_message_id: lastAssistantMsg.id,
      assistant_turn_id: lastAssistantMsg.assistant_turn_id || null,
      run_id: lastAssistantMsg.run_id || null,
      note_id: note.id,
      accepted: true,
    });
    return note;
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

  const suggestWorkspaceMemoryFromLastAssistantMessage = async (): Promise<WorkspaceMemoryDraft | null> => {
    const workspaceId = args.selectedWorkspaceId();
    const chatId = args.currentChatId();
    const lastAssistantMsg = [...args.messages()].reverse().find((message) => message.role === 'assistant');

    if (!workspaceId || !chatId || !lastAssistantMsg) {
      args.toast.error('No workspace assistant message to review as memory.', 3000);
      return null;
    }

    const res = await fetch(`/api/workspaces/${workspaceId}/memory/suggest-from-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        message_id: typeof lastAssistantMsg.id === 'number' ? lastAssistantMsg.id : undefined,
        source_ids: effectiveWorkspaceSourceIds(),
        citation_refs: lastAssistantMsg.citations || [],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as WorkspaceMemoryDraft;
  };

  const suggestWorkspaceMemoryCandidateFromLastAssistantMessage = async (): Promise<WorkspaceMemoryCandidate | null> => {
    const workspaceId = args.selectedWorkspaceId();
    const chatId = args.currentChatId();
    const lastAssistantMsg = [...args.messages()].reverse().find((message) => message.role === 'assistant');

    if (!workspaceId || !chatId || !lastAssistantMsg) {
      args.toast.error('No workspace assistant message to review as memory.', 3000);
      return null;
    }

    const res = await fetch(`/api/workspaces/${workspaceId}/memory-candidates/suggest-from-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        message_id: typeof lastAssistantMsg.id === 'number' ? lastAssistantMsg.id : undefined,
        source_ids: effectiveWorkspaceSourceIds(),
        citation_refs: lastAssistantMsg.citations || [],
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const candidate = (await res.json()) as WorkspaceMemoryCandidate;
    await loadWorkspaceMemories(workspaceId);
    await trackWorkspaceCaptureTelemetry({
      event_type: 'memory_candidate_created',
      source: 'assistant_reply',
      workspace_id: workspaceId,
      assistant_message_id: lastAssistantMsg.id,
      assistant_turn_id: lastAssistantMsg.assistant_turn_id || null,
      run_id: lastAssistantMsg.run_id || null,
      candidate_id: candidate.id,
      accepted: true,
      metadata: { suggested_action: candidate.suggested_action || null },
    });
    return candidate;
  };

  const suggestWorkspaceMemoryCandidateFromNote = async (noteId: string): Promise<WorkspaceMemoryCandidate | null> => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/notes/${noteId}/memory-candidates`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const candidate = (await res.json()) as WorkspaceMemoryCandidate;
    await Promise.all([loadWorkspaceNotes(workspaceId), loadWorkspaceMemories(workspaceId)]);
    await trackWorkspaceCaptureTelemetry({
      event_type: 'memory_candidate_created',
      source: 'workspace_note',
      workspace_id: workspaceId,
      note_id: noteId,
      candidate_id: candidate.id,
      accepted: true,
      metadata: { suggested_action: candidate.suggested_action || null },
    });
    return candidate;
  };

  const createWorkspaceMemory = async (payload: {
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
  }) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
  };

  const updateWorkspaceMemory = async (
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
  ) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/memory/${memoryId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
  };

  const approveWorkspaceMemoryCandidate = async (
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
  ) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const trackedCandidate =
      workspaceMemoryCandidates().find((candidate) => candidate.id === candidateId) || null;
    const res = await fetch(`/api/workspaces/${workspaceId}/memory-candidates/${candidateId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
    await trackWorkspaceCaptureTelemetry({
      event_type: 'memory_candidate_promoted',
      source: trackedCandidate?.candidate_metadata?.note_id ? 'workspace_note' : 'assistant_reply',
      workspace_id: workspaceId,
      candidate_id: candidateId,
      note_id:
        typeof trackedCandidate?.candidate_metadata?.note_id === 'string'
          ? trackedCandidate?.candidate_metadata?.note_id
          : null,
      accepted: true,
      metadata: { approval_mode: payload.approval_mode, target_memory_id: payload.target_memory_id || null },
    });
  };

  const rejectWorkspaceMemoryCandidate = async (candidateId: string, reason?: string | null) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/memory-candidates/${candidateId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || undefined }),
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
  };

  const bulkUpdateWorkspaceMemoryStatusByType = async (memoryType: string, status: string) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/memory/bulk-status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ memory_type: memoryType, status }),
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
  };

  const deleteWorkspaceMemory = async (memoryId: string) => {
    const workspaceId = args.selectedWorkspaceId();
    if (!workspaceId) throw new Error('No workspace selected');
    const res = await fetch(`/api/workspaces/${workspaceId}/memory/${memoryId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(await readErrorDetail(res));
    await loadWorkspaceMemories(workspaceId);
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

  createEffect(() => {
    void loadWorkspaceNotes(args.selectedWorkspaceId());
  });

  createEffect(() => {
    void loadWorkspaceMemories(args.selectedWorkspaceId());
  });

  return {
    workspaces,
    workspaceSources,
    workspaceArtifacts,
    workspaceNotes,
    workspaceMemories,
    workspaceMemoryCandidates,
    workspaceSourceMode,
    setWorkspaceSourceMode,
    selectedWorkspaceSourceIds,
    groundingMode,
    setGroundingMode,
    workspaceLoading,
    sourcesLoading,
    artifactsLoading,
    notesLoading,
    memoriesLoading,
    selectedWorkspace,
    loadWorkspaces,
    loadWorkspaceNotes,
    loadWorkspaceMemories,
    checkWorkspaceSources,
    checkWorkspaceSource,
    handleSelectWorkspace,
    toggleWorkspaceSource,
    buildWorkspaceRequestOverrides,
    saveLastAssistantAsWorkspaceNote,
    saveLastAssistantAsResearchArtifact,
    suggestWorkspaceMemoryFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromNote,
    createWorkspaceMemory,
    updateWorkspaceMemory,
    bulkUpdateWorkspaceMemoryStatusByType,
    deleteWorkspaceMemory,
    approveWorkspaceMemoryCandidate,
    rejectWorkspaceMemoryCandidate,
    handleCreateWorkspace,
    trackWorkspaceCaptureTelemetry,
  };
}
