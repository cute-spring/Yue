import { For, Show, createEffect, createMemo, createSignal } from 'solid-js';
import {
  WorkspaceArtifact,
  WorkspaceNote,
  WorkspaceMemoryCandidate,
  WorkspaceMemoryCard,
  WorkspaceMemoryDraft,
  WorkspaceSource,
} from '../types';
import {
  formatWorkspaceCountLabel,
  formatWorkspaceArtifactType,
  getArtifactSourceLabels,
  getResearchArtifactMetadata,
  getWorkspaceEvidenceSummary,
  getWorkspaceSourceReadinessCounts,
  getWorkspaceSourceToolLabels,
} from './ChatSidebar.helpers';

type WorkspaceSourceMode = 'all_ready' | 'selected' | 'none';
type GroundingMode = 'normal' | 'prefer_sources' | 'require_sources';

interface ChatSidebarResourcesProps {
  selectedWorkspaceId: string | null;
  workspaceSources: WorkspaceSource[];
  workspaceArtifacts: WorkspaceArtifact[];
  workspaceNotes: WorkspaceNote[];
  workspaceMemories: WorkspaceMemoryCard[];
  workspaceMemoryCandidates: WorkspaceMemoryCandidate[];
  workspaceSourceMode: WorkspaceSourceMode;
  selectedWorkspaceSourceIds: string[];
  groundingMode: GroundingMode;
  sourcesLoading?: boolean;
  artifactsLoading?: boolean;
  notesLoading?: boolean;
  memoriesLoading?: boolean;
  memorySuggestionsEnabled?: boolean;
  isResourcesExpanded: boolean;
  isSourcesExpanded: boolean;
  isArtifactsExpanded: boolean;
  isNotesExpanded: boolean;
  isMemoriesExpanded: boolean;
  onToggleResources: () => void;
  onToggleSources: () => void;
  onToggleArtifacts: () => void;
  onToggleNotes: () => void;
  onToggleMemories: () => void;
  onWorkspaceSourceModeChange: (mode: WorkspaceSourceMode) => void;
  onToggleWorkspaceSource: (sourceId: string) => void;
  onGroundingModeChange: (mode: GroundingMode) => void;
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
}

const formatSourceModeLabel = (mode: WorkspaceSourceMode) => {
  switch (mode) {
    case 'all_ready':
      return 'All ready';
    case 'selected':
      return 'Selected only';
    case 'none':
      return 'No sources';
  }
};

const formatGroundingModeLabel = (mode: GroundingMode) => {
  switch (mode) {
    case 'normal':
      return 'Normal';
    case 'prefer_sources':
      return 'Prefer cites';
    case 'require_sources':
      return 'Require cites';
  }
};

const formatMemoryTypeLabel = (memoryType: string) => {
  switch (memoryType) {
    case 'project_fact':
      return 'Project Fact';
    case 'decision':
      return 'Long-term Decision';
    case 'preference':
      return 'User Preference';
    case 'historical_conclusion':
      return 'Historical Conclusion';
    case 'term':
      return 'Term';
    case 'open_question':
      return 'Open Question';
    case 'recurring_instruction':
      return 'Instruction';
    default:
      return memoryType.replace(/[_-]+/g, ' ');
  }
};

const formatMemoryStatusLabel = (status?: string | null) => {
  switch (status) {
    case 'active':
      return 'Active';
    case 'disabled':
      return 'Disabled';
    case 'archived':
      return 'Archived';
    case 'superseded':
      return 'Superseded';
    default:
      return status ? status.replace(/[_-]+/g, ' ') : 'Unknown';
  }
};

const formatMemoryScopeLabel = (scopeType?: string | null) => {
  switch (scopeType) {
    case 'user':
      return 'User scope';
    case 'workspace':
      return 'Workspace scope';
    case 'project':
      return 'Project scope';
    case 'chat':
      return 'Chat scope';
    default:
      return scopeType ? scopeType.replace(/[_-]+/g, ' ') : 'Workspace scope';
  }
};

const formatDateTimeLabel = (value?: string | null) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const formatCandidateActionLabel = (action?: string | null) => {
  switch (action) {
    case 'replace_existing':
      return 'Replace existing';
    case 'update_existing':
      return 'Update existing';
    case 'create_new':
      return 'Create new';
    default:
      return action ? action.replace(/[_-]+/g, ' ') : 'Review';
  }
};

const formatCandidateScore = (score?: number | null) => {
  if (score == null || Number.isNaN(Number(score))) return 'n/a';
  return `${Math.round(Number(score) * 100)}%`;
};

const formatNoteTypeLabel = (noteType?: string | null) => {
  switch (noteType) {
    case 'summary':
      return 'Summary';
    case 'insight':
      return 'Insight';
    case 'preference':
      return 'Preference';
    case 'decision':
      return 'Decision';
    case 'fact':
      return 'Fact';
    case 'reference':
      return 'Reference';
    case 'todo':
      return 'Todo';
    default:
      return noteType ? noteType.replace(/[_-]+/g, ' ') : 'Note';
  }
};

const formatCaptureTypeLabel = (captureType?: string | null) => {
  switch (captureType) {
    case 'chat_capture':
      return 'From chat';
    case 'source_capture':
      return 'From source';
    case 'legacy_import':
      return 'Imported';
    case 'manual':
      return 'Manual';
    default:
      return captureType ? captureType.replace(/[_-]+/g, ' ') : 'Saved';
  }
};

const formatPromotionHintLabel = (state?: string | null) => {
  switch (state) {
    case 'ready':
      return 'memory-ready';
    case 'candidate_pending':
      return 'candidate pending';
    case 'candidate_approved':
      return 'candidate approved';
    case 'candidate_rejected':
      return 'candidate rejected';
    case 'promoted':
      return 'promoted';
    default:
      return state ? state.replace(/[_-]+/g, ' ') : 'note only';
  }
};

export default function ChatSidebarResources(props: ChatSidebarResourcesProps) {
  const [isMemoryEditorOpen, setIsMemoryEditorOpen] = createSignal(false);
  const [editingMemoryId, setEditingMemoryId] = createSignal<string | null>(null);
  const [memoryTypeInput, setMemoryTypeInput] = createSignal('project_fact');
  const [memoryScopeTypeInput, setMemoryScopeTypeInput] = createSignal('workspace');
  const [memoryScopeRefInput, setMemoryScopeRefInput] = createSignal('');
  const [memoryTitleInput, setMemoryTitleInput] = createSignal('');
  const [memoryContentInput, setMemoryContentInput] = createSignal('');
  const [memoryStatusInput, setMemoryStatusInput] = createSignal('active');
  const [memoryConfidenceInput, setMemoryConfidenceInput] = createSignal('0.7');
  const [memoryWhySavedInput, setMemoryWhySavedInput] = createSignal('');
  const [memoryPinnedInput, setMemoryPinnedInput] = createSignal(false);
  const [memoryEditableInput, setMemoryEditableInput] = createSignal(true);
  const [memoryRevocableInput, setMemoryRevocableInput] = createSignal(true);
  const [memoryExpiresAtInput, setMemoryExpiresAtInput] = createSignal('');
  const [memorySourceSessionIdInput, setMemorySourceSessionIdInput] = createSignal('');
  const [memorySourceMessageIdInput, setMemorySourceMessageIdInput] = createSignal('');
  const [memoryMetadataInput, setMemoryMetadataInput] = createSignal('{}');
  const [isMemorySubmitting, setIsMemorySubmitting] = createSignal(false);
  const [candidateActionMemoryId, setCandidateActionMemoryId] = createSignal<string | null>(null);
  const [memoryError, setMemoryError] = createSignal<string | null>(null);
  const [noteActionId, setNoteActionId] = createSignal<string | null>(null);
  const [noteFeedback, setNoteFeedback] = createSignal<string | null>(null);
  const [noteError, setNoteError] = createSignal<string | null>(null);

  createEffect(() => {
    props.selectedWorkspaceId;
    setNoteFeedback(null);
    setNoteError(null);
    setMemoryError(null);
  });

  const sourceReadiness = createMemo(() => getWorkspaceSourceReadinessCounts(props.workspaceSources));
  const sourcesReadyCount = createMemo(() => sourceReadiness().citationReady || sourceReadiness().ready);
  const sourcesAttentionCount = createMemo(() => sourceReadiness().attention);

  const latestArtifactTitle = createMemo(() => props.workspaceArtifacts[0]?.title || null);
  const latestNoteTitle = createMemo(() => props.workspaceNotes[0]?.title || null);
  const latestMemoryTitle = createMemo(() => props.workspaceMemories[0]?.title || null);
  const activeMemoryCount = createMemo(() => props.workspaceMemories.filter((memory) => memory.status === 'active').length);
  const disabledMemoryCount = createMemo(() => props.workspaceMemories.filter((memory) => memory.status === 'disabled').length);
  const pendingCandidates = createMemo(() =>
    props.workspaceMemoryCandidates.filter((candidate) => candidate.status === 'pending'),
  );
  const pendingCandidateCount = createMemo(
    () => pendingCandidates().length,
  );
  const promotedNoteCount = createMemo(
    () => props.workspaceNotes.filter((note) => Boolean(note.promoted_memory_id)).length,
  );
  const memoryGroups = createMemo(() => {
    const order = ['project_fact', 'preference', 'decision', 'historical_conclusion', 'recurring_instruction', 'term', 'open_question'];
    return order
      .map((memoryType) => ({
        memoryType,
        label: formatMemoryTypeLabel(memoryType),
        items: props.workspaceMemories.filter((memory) => memory.memory_type === memoryType),
      }))
      .filter((group) => group.items.length > 0);
  });

  const resetMemoryEditor = () => {
    setEditingMemoryId(null);
    setMemoryTypeInput('project_fact');
    setMemoryScopeTypeInput('workspace');
    setMemoryScopeRefInput('');
    setMemoryTitleInput('');
    setMemoryContentInput('');
    setMemoryStatusInput('active');
    setMemoryConfidenceInput('0.7');
    setMemoryWhySavedInput('');
    setMemoryPinnedInput(false);
    setMemoryEditableInput(true);
    setMemoryRevocableInput(true);
    setMemoryExpiresAtInput('');
    setMemorySourceSessionIdInput('');
    setMemorySourceMessageIdInput('');
    setMemoryMetadataInput('{}');
    setMemoryError(null);
  };

  const openCreateMemoryEditor = () => {
    resetMemoryEditor();
    setIsMemoryEditorOpen(true);
  };

  const openEditMemoryEditor = (memory: WorkspaceMemoryCard) => {
    setEditingMemoryId(memory.id);
    setMemoryTypeInput(memory.memory_type || 'project_fact');
    setMemoryScopeTypeInput(memory.scope_type || 'workspace');
    setMemoryScopeRefInput(memory.scope_ref || '');
    setMemoryTitleInput(memory.title || '');
    setMemoryContentInput(memory.content || '');
    setMemoryStatusInput(memory.status || 'active');
    setMemoryConfidenceInput(
      memory.confidence == null || Number.isNaN(Number(memory.confidence)) ? '' : String(memory.confidence),
    );
    setMemoryWhySavedInput(memory.why_saved || '');
    setMemoryPinnedInput(Boolean(memory.pinned));
    setMemoryEditableInput(memory.editable !== false);
    setMemoryRevocableInput(memory.revocable !== false);
    setMemoryExpiresAtInput(memory.expires_at ? String(memory.expires_at).slice(0, 16) : '');
    setMemorySourceSessionIdInput(memory.source_session_id || '');
    setMemorySourceMessageIdInput(
      memory.source_message_id == null ? '' : String(memory.source_message_id),
    );
    setMemoryMetadataInput(JSON.stringify(memory.memory_metadata || {}, null, 2));
    setMemoryError(null);
    setIsMemoryEditorOpen(true);
  };

  const resourcesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'Choose a workspace to see the materials and saved work that support this chat.';
    if (props.sourcesLoading || props.artifactsLoading || props.memoriesLoading) return 'Loading workspace context...';
    const parts: string[] = [];
    if (props.workspaceSources.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(sourcesReadyCount(), 'source')} ready for grounding`);
      if (sourcesAttentionCount() > 0) {
        parts.push(`${formatWorkspaceCountLabel(sourcesAttentionCount(), 'source')} needs attention`);
      }
    } else {
      parts.push('Add sources to ground answers');
    }
    if (props.workspaceArtifacts.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(props.workspaceArtifacts.length, 'saved artifact')}`);
    } else {
      parts.push('No saved artifacts yet');
    }
    if (props.workspaceNotes.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(props.workspaceNotes.length, 'saved note')}`);
    } else {
      parts.push('No notes captured yet');
    }
    if (props.workspaceMemories.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(activeMemoryCount(), 'active memory card')}`);
    } else {
      parts.push('No memory cards yet');
    }
    return parts.join(' · ');
  });

  const sourcesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    if (props.sourcesLoading) return 'Loading workspace materials...';
    if (props.workspaceSources.length === 0) return 'No sources yet';
    const parts = [`${formatWorkspaceCountLabel(sourcesReadyCount(), 'source')} ready`];
    if (sourcesAttentionCount() > 0) {
      parts.push(`${formatWorkspaceCountLabel(sourcesAttentionCount(), 'source')} needs attention`);
    }
    return parts.join(' · ');
  });

  const artifactsSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    if (props.artifactsLoading) return 'Loading saved work...';
    if (latestArtifactTitle()) return `Latest: ${latestArtifactTitle()}`;
    return props.workspaceArtifacts.length > 0
      ? formatWorkspaceCountLabel(props.workspaceArtifacts.length, 'saved artifact')
      : 'No saved artifacts yet';
  });
  const notesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    if (props.notesLoading) return 'Loading saved notes...';
    const parts: string[] = [];
    if (latestNoteTitle()) {
      parts.push(`Latest: ${latestNoteTitle()}`);
    } else if (props.workspaceNotes.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(props.workspaceNotes.length, 'saved note')}`);
    } else {
      parts.push('No saved notes yet');
    }
    if (promotedNoteCount() > 0) {
      parts.push(`${formatWorkspaceCountLabel(promotedNoteCount(), 'promoted note')}`);
    }
    return parts.join(' · ');
  });
  const memoriesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    if (props.memoriesLoading) return 'Loading workspace memory...';
    const parts: string[] = [];
    if (latestMemoryTitle()) {
      parts.push(`Latest: ${latestMemoryTitle()}`);
    } else if (props.workspaceMemories.length > 0) {
      parts.push(`${formatWorkspaceCountLabel(activeMemoryCount(), 'active memory card')}`);
    } else {
      parts.push('No memory cards yet');
    }
    if (disabledMemoryCount() > 0) {
      parts.push(`${formatWorkspaceCountLabel(disabledMemoryCount(), 'disabled memory card')}`);
    }
    if (pendingCandidateCount() > 0) {
      parts.push(`${formatWorkspaceCountLabel(pendingCandidateCount(), 'pending candidate')}`);
    }
    return parts.join(' · ');
  });

  const evidenceSummary = createMemo(() =>
    getWorkspaceEvidenceSummary(
      props.workspaceSourceMode,
      props.groundingMode,
      props.workspaceSources,
      props.selectedWorkspaceSourceIds,
    )
  );
  const selectedReadyCount = createMemo(
    () => props.workspaceSources.filter((source) => source.status === 'ready' && props.selectedWorkspaceSourceIds.includes(source.id)).length,
  );
  const sourceSelectionSummary = createMemo(() => {
    if (props.workspaceSourceMode === 'none') return 'Workspace sources are off for this chat.';
    if (props.workspaceSourceMode === 'selected') {
      return `${selectedReadyCount()} ready of ${props.selectedWorkspaceSourceIds.length} selected`;
    }
    return `${sourcesReadyCount()} ready sources currently available`;
  });
  const resourcesEmptyHint = createMemo(() => {
    if (!props.selectedWorkspaceId) {
      return 'Select a workspace first, then add a file or continue a saved chat inside it.';
    }
    if (props.sourcesLoading || props.artifactsLoading || props.memoriesLoading) {
      return 'Checking the workspace so the source and artifact lists stay current.';
    }
    if (
      props.workspaceSources.length === 0 &&
      props.workspaceArtifacts.length === 0 &&
      props.workspaceNotes.length === 0 &&
      props.workspaceMemories.length === 0 &&
      props.workspaceMemoryCandidates.length === 0
    ) {
      return 'Start by asking a question in this workspace or upload a file in chat to give it context.';
    }
    if (props.workspaceSources.length === 0) {
      return 'This workspace has saved work, but no source materials yet.';
    }
    if (props.workspaceArtifacts.length === 0) {
      return 'Saved notes, reports, and research outputs will appear here after a workspace run.';
    }
    if (props.workspaceNotes.length === 0) {
      return 'Capture a strong assistant reply as a note so this workspace can reuse it later.';
    }
    if (props.workspaceMemories.length === 0 && props.workspaceMemoryCandidates.length === 0) {
      return 'Save stable facts and preferences here so the workspace gets better over time.';
    }
    return '';
  });
  const formatSourceStatus = (status?: string | null) => {
    switch (status) {
      case 'ready':
        return 'Ready';
      case 'missing':
        return 'Missing';
      case 'unsupported_type':
        return 'Unsupported';
      case 'needs_permission':
        return 'Needs permission';
      case 'processing':
        return 'Processing';
      default:
        return status ? status.replace(/[_-]+/g, ' ') : 'Unknown';
    }
  };

  const handleSuggestMemory = async () => {
    try {
      setMemoryError(null);
      const draft = await props.onSuggestWorkspaceMemoryFromLastAssistantMessage();
      if (!draft) return;
      setEditingMemoryId(null);
      setMemoryTypeInput(draft.memory_type || 'project_fact');
      setMemoryScopeTypeInput(draft.scope_type || 'workspace');
      setMemoryScopeRefInput(draft.scope_ref || '');
      setMemoryTitleInput(draft.title || '');
      setMemoryContentInput(draft.content || '');
      setMemoryStatusInput('active');
      setMemoryConfidenceInput(
        draft.confidence == null || Number.isNaN(Number(draft.confidence)) ? '' : String(draft.confidence),
      );
      setMemoryWhySavedInput(draft.why_saved || '');
      setMemoryPinnedInput(false);
      setMemoryEditableInput(true);
      setMemoryRevocableInput(true);
      setMemoryExpiresAtInput(draft.expires_at ? String(draft.expires_at).slice(0, 16) : '');
      setMemorySourceSessionIdInput(draft.source_session_id || '');
      setMemorySourceMessageIdInput(draft.source_message_id == null ? '' : String(draft.source_message_id));
      setMemoryMetadataInput(JSON.stringify(draft.memory_metadata || {}, null, 2));
      setIsMemoryEditorOpen(true);
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to build memory draft');
    }
  };

  const handleSuggestCandidate = async () => {
    try {
      setMemoryError(null);
      const candidate = await props.onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage();
      if (!candidate) return;
      setIsMemoryEditorOpen(false);
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to create memory candidate');
    }
  };

  const handleSaveNote = async () => {
    try {
      setNoteError(null);
      setNoteFeedback(null);
      const note = await props.onSaveLastAssistantAsWorkspaceNote();
      if (!note) return;
      const promotionHint = note.promotion_hint;
      const savedTitle = note.title ? `Saved note: ${note.title}` : 'Saved latest reply as note.';
      if (props.memorySuggestionsEnabled !== false && promotionHint?.eligible && promotionHint.state === 'ready') {
        setNoteFeedback(`${savedTitle} Ready for memory review.`);
      } else {
        setNoteFeedback(savedTitle);
      }
    } catch (error) {
      setNoteError(error instanceof Error ? error.message : 'Failed to save note');
    }
  };

  const handleSuggestCandidateFromNote = async (note: WorkspaceNote) => {
    setNoteActionId(note.id);
    setNoteError(null);
    setNoteFeedback(null);
    try {
      const candidate = await props.onSuggestWorkspaceMemoryCandidateFromNote(note.id);
      if (!candidate) return;
      setNoteFeedback(`Created memory candidate from “${note.title}”.`);
    } catch (error) {
      setNoteError(error instanceof Error ? error.message : 'Failed to create note memory candidate');
    } finally {
      setNoteActionId(null);
    }
  };

  const handleSubmitMemory = async () => {
    const title = memoryTitleInput().trim();
    const content = memoryContentInput().trim();
    if (!title || !content) {
      setMemoryError('Title and content are required.');
      return;
    }

    let metadata: Record<string, any> = {};
    try {
      metadata = memoryMetadataInput().trim() ? JSON.parse(memoryMetadataInput()) : {};
    } catch {
      setMemoryError('Metadata must be valid JSON.');
      return;
    }

    const confidenceRaw = memoryConfidenceInput().trim();
    const confidenceValue =
      confidenceRaw === '' ? null : Number.isNaN(Number(confidenceRaw)) ? null : Number(confidenceRaw);
    const sourceMessageValue =
      memorySourceMessageIdInput().trim() === '' ? null : Number(memorySourceMessageIdInput().trim());
    const expiresAtValue = memoryExpiresAtInput().trim() || null;

    setIsMemorySubmitting(true);
    setMemoryError(null);
    try {
      const payload = {
        memory_type: memoryTypeInput(),
        scope_type: memoryScopeTypeInput(),
        scope_ref: memoryScopeRefInput().trim() || null,
        title,
        content,
        status: memoryStatusInput(),
        confidence: confidenceValue,
        created_by: 'user',
        why_saved: memoryWhySavedInput().trim() || null,
        pinned: memoryPinnedInput(),
        editable: memoryEditableInput(),
        revocable: memoryRevocableInput(),
        source_session_id: memorySourceSessionIdInput().trim() || null,
        source_message_id: Number.isNaN(sourceMessageValue as number) ? null : sourceMessageValue,
        expires_at: expiresAtValue,
        memory_metadata: metadata,
      };
      if (editingMemoryId()) {
        await props.onUpdateWorkspaceMemory(editingMemoryId()!, payload);
      } else {
        await props.onCreateWorkspaceMemory(payload);
      }
      resetMemoryEditor();
      setIsMemoryEditorOpen(false);
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to save memory card');
    } finally {
      setIsMemorySubmitting(false);
    }
  };

  const handleToggleMemoryStatus = async (memory: WorkspaceMemoryCard) => {
    const nextStatus = memory.status === 'disabled' ? 'active' : 'disabled';
    await props.onUpdateWorkspaceMemory(memory.id, { status: nextStatus });
  };

  const handleDisableMemoryType = async (memoryType: string) => {
    await props.onBulkUpdateWorkspaceMemoryStatusByType(memoryType, 'disabled');
  };

  const handleApproveCandidate = async (
    candidate: WorkspaceMemoryCandidate,
    approvalMode?: string | null,
  ) => {
    const resolvedMode =
      approvalMode ||
      candidate.suggested_action ||
      (candidate.conflict_memory_id ? 'update_existing' : 'create_new');
    setCandidateActionMemoryId(candidate.id);
    setMemoryError(null);
    try {
      await props.onApproveWorkspaceMemoryCandidate(candidate.id, {
        approval_mode: resolvedMode,
        target_memory_id: candidate.conflict_memory_id || null,
        memory_type: candidate.memory_type || null,
        scope_type: candidate.scope_type || null,
        scope_ref: candidate.scope_ref || null,
        title: candidate.title || null,
        content: candidate.content || null,
        confidence: candidate.score ?? null,
        why_saved: candidate.why_saved || null,
        expires_at: candidate.expires_at || null,
      });
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to approve memory candidate');
    } finally {
      setCandidateActionMemoryId(null);
    }
  };

  const handleRejectCandidate = async (candidateId: string) => {
    setCandidateActionMemoryId(candidateId);
    setMemoryError(null);
    try {
      await props.onRejectWorkspaceMemoryCandidate(candidateId, 'Rejected from workspace memory review');
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : 'Failed to reject memory candidate');
    } finally {
      setCandidateActionMemoryId(null);
    }
  };

  return (
    <div class="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
      <button
        type="button"
        onClick={props.onToggleResources}
        aria-expanded={props.isResourcesExpanded}
        class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-white/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <div class="min-w-0">
          <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Resources</div>
          <div class="mt-1 line-clamp-2 text-[11px] leading-snug text-slate-600">
            {resourcesSummary()}
          </div>
          <Show when={resourcesEmptyHint()}>
            <div class="mt-1 line-clamp-2 text-[10px] leading-snug text-slate-400">
              {resourcesEmptyHint()}
            </div>
          </Show>
          <Show when={props.selectedWorkspaceId}>
            <div class="mt-2 flex flex-wrap gap-1">
              <span class="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] font-semibold text-slate-600">
                {formatSourceModeLabel(props.workspaceSourceMode)}
              </span>
              <span class="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] font-semibold text-slate-600">
                {formatGroundingModeLabel(props.groundingMode)}
              </span>
            </div>
          </Show>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isResourcesExpanded ? 'rotate-90' : 'rotate-0'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <Show when={props.isResourcesExpanded && props.selectedWorkspaceId}>
        <div class="border-t border-slate-200 px-3 py-3">
          <div class="rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleSources}
              aria-expanded={props.isSourcesExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Sources</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {sourcesSummary()}
                </div>
                <div class="mt-1 text-[10px] leading-snug text-slate-400">
                  {formatSourceModeLabel(props.workspaceSourceMode)} · {formatGroundingModeLabel(props.groundingMode)} · {sourceSelectionSummary()}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isSourcesExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isSourcesExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <div class="mb-2 mt-3 grid grid-cols-2 gap-2">
                  <select
                    value={props.workspaceSourceMode}
                    onChange={(e) => props.onWorkspaceSourceModeChange(e.currentTarget.value as WorkspaceSourceMode)}
                    class="bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="all_ready">All ready</option>
                    <option value="selected">Selected</option>
                    <option value="none">No sources</option>
                  </select>
                  <select
                    value={props.groundingMode}
                    onChange={(e) => props.onGroundingModeChange(e.currentTarget.value as GroundingMode)}
                    class="bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="normal">Normal</option>
                    <option value="prefer_sources">Prefer cites</option>
                    <option value="require_sources">Require cites</option>
                  </select>
                </div>
                <div class="mb-2 flex items-center justify-between gap-2 rounded-lg border border-blue-100 bg-blue-50/70 px-2.5 py-2 text-[10px] leading-snug text-blue-700">
                  <span class="min-w-0 flex-1">{evidenceSummary()}</span>
                  <button
                    type="button"
                    onClick={() => void props.onCheckWorkspaceSources()}
                    class="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold text-primary transition-colors hover:bg-white/70 hover:text-primary-hover"
                  >
                    Check
                  </button>
                </div>
                <Show
                  when={!props.sourcesLoading}
                  fallback={<div class="text-[11px] text-slate-400 italic">Loading workspace materials...</div>}
                >
                  <Show
                    when={props.workspaceSources.length > 0}
                    fallback={
                      <div class="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-[11px] leading-relaxed text-slate-500">
                        No sources yet. Upload a file in chat or attach a local document to give this workspace evidence.
                      </div>
                    }
                  >
                    <div class="space-y-2 max-h-36 overflow-y-auto no-scrollbar pr-1">
                      <For each={props.workspaceSources}>
                        {(source) => (
                          <div class="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 transition-colors hover:border-slate-200 hover:bg-white">
                            <div class="flex items-start gap-2">
                              <Show when={props.workspaceSourceMode === 'selected'}>
                                <input
                                  type="checkbox"
                                  checked={props.selectedWorkspaceSourceIds.includes(source.id)}
                                  onChange={() => props.onToggleWorkspaceSource(source.id)}
                                  class="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-primary"
                                />
                              </Show>
                              <div class="min-w-0 flex-1">
                                <div
                                  class="truncate text-[11px] font-semibold text-slate-700"
                                  title={source.display_name || source.source_ref}
                                >
                                  {source.display_name || source.source_ref}
                                </div>
                                <div class="mt-1 flex items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">{source.source_type}</span>
                                  <Show when={source.status}>
                                    <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">{formatSourceStatus(source.status)}</span>
                                  </Show>
                                  <Show when={source.source_metadata?.readiness_error_message}>
                                    <span class="truncate text-[9px] normal-case tracking-normal text-rose-500">
                                      {source.source_metadata?.readiness_error_message}
                                    </span>
                                  </Show>
                                </div>
                                <Show when={source.source_metadata?.citation_capable || getWorkspaceSourceToolLabels(source).length > 0}>
                                  <div class="mt-1 flex flex-wrap gap-1">
                                    <Show when={source.source_metadata?.citation_capable}>
                                      <span class="rounded-full border border-emerald-100 bg-emerald-50 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-700">
                                        cite-ready
                                      </span>
                                    </Show>
                                    <For each={getWorkspaceSourceToolLabels(source)}>
                                      {(toolLabel) => (
                                        <span class="rounded-full border border-blue-100 bg-blue-50 px-1.5 py-0.5 text-[9px] font-semibold text-blue-700">
                                          {toolLabel}
                                        </span>
                                      )}
                                    </For>
                                  </div>
                                </Show>
                              </div>
                              <button
                                type="button"
                                onClick={() => void props.onCheckWorkspaceSource(source.id)}
                                class="rounded-md px-1.5 py-0.5 text-[10px] font-bold text-slate-400 transition-colors hover:bg-white hover:text-primary"
                              >
                                Retry
                              </button>
                            </div>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>

          <div class="mt-2 rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleArtifacts}
              aria-expanded={props.isArtifactsExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Artifacts</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {props.workspaceArtifacts.length} total
                </div>
                <div class="mt-1 truncate text-[10px] text-slate-400" title={artifactsSummary()}>
                  {artifactsSummary()}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isArtifactsExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isArtifactsExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <Show
                  when={!props.artifactsLoading}
                  fallback={<div class="mt-3 text-[11px] text-slate-400 italic">Loading saved work...</div>}
                >
                  <Show
                    when={props.workspaceArtifacts.length > 0}
                    fallback={
                      <div class="mt-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-[11px] leading-relaxed text-slate-500">
                        No saved artifacts yet. Research notes, reports, and linked outputs will appear here after a workspace run.
                      </div>
                    }
                  >
                    <div class="mt-3 space-y-2 max-h-72 overflow-y-auto no-scrollbar pr-1">
                      <For each={props.workspaceArtifacts}>
                        {(artifact) => {
                          const metadata = createMemo(() => getResearchArtifactMetadata(artifact));
                          const sourceLabels = createMemo(() => getArtifactSourceLabels(artifact, props.workspaceSources));
                          return (
                            <details
                              open={props.workspaceArtifacts.length === 1}
                              class="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 transition-colors hover:border-slate-200 hover:bg-white"
                            >
                              <summary class="cursor-pointer list-none">
                                <div class="flex items-start justify-between gap-2">
                                  <div class="min-w-0 truncate text-[11px] font-semibold text-slate-700" title={artifact.title}>
                                    {artifact.title}
                                  </div>
                                  <span class="shrink-0 text-[9px] font-bold uppercase tracking-wide text-blue-500">
                                    Detail
                                  </span>
                                </div>
                                <div class="mt-1 flex items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">
                                    {formatWorkspaceArtifactType(artifact.artifact_type)}
                                  </span>
                                  <Show when={artifact.artifact_path}>
                                    <span
                                      class="truncate text-[9px] normal-case tracking-normal text-slate-400"
                                      title={artifact.artifact_path || undefined}
                                    >
                                      {artifact.artifact_path}
                                    </span>
                                  </Show>
                                </div>
                              </summary>

                              <div class="mt-3 rounded-xl border border-blue-100 bg-gradient-to-br from-white to-blue-50/70 p-3 shadow-sm">
                                <div class="min-w-0">
                                  <div class="text-[10px] font-black uppercase tracking-[0.18em] text-blue-500">
                                    Research detail
                                  </div>
                                  <div class="mt-1 text-[12px] font-bold leading-snug text-slate-800">
                                    {metadata().question}
                                  </div>
                                </div>

                                <div class="mt-2 flex flex-wrap gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                    {formatWorkspaceArtifactType(artifact.artifact_type)}
                                  </span>
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                    {metadata().mode}
                                  </span>
                                  <Show when={artifact.source_session_id}>
                                    <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                      linked chat
                                    </span>
                                  </Show>
                                </div>

                                <Show when={metadata().summary}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Summary</div>
                                    <p class="mt-1 max-h-28 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate-700">
                                      {metadata().summary}
                                    </p>
                                  </div>
                                </Show>

                                <Show when={sourceLabels().length > 0}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Sources</div>
                                    <div class="mt-1 flex flex-wrap gap-1">
                                      <For each={sourceLabels()}>
                                        {(label) => (
                                          <span class="max-w-full truncate rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-600">
                                            {label}
                                          </span>
                                        )}
                                      </For>
                                    </div>
                                  </div>
                                </Show>

                                <Show when={metadata().openQuestions.length > 0}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Open questions</div>
                                    <div class="mt-1 space-y-1">
                                      <For each={metadata().openQuestions}>
                                        {(question) => (
                                          <div class="rounded-lg bg-white/80 px-2 py-1 text-[10px] leading-snug text-slate-600">
                                            {question}
                                          </div>
                                        )}
                                      </For>
                                    </div>
                                  </div>
                                </Show>

                                <Show when={artifact.source_session_id || artifact.source_message_id || metadata().exportPaths.length > 0}>
                                  <div class="mt-3 border-t border-blue-100 pt-2 text-[10px] leading-relaxed text-slate-500">
                                    <Show when={artifact.source_session_id}>
                                      <div class="flex items-center justify-between gap-2">
                                        <span class="truncate">Chat: {artifact.source_session_id}</span>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const chatId = artifact.source_session_id;
                                            if (chatId) props.onLoadChat(chatId);
                                          }}
                                          class="shrink-0 rounded-full border border-blue-100 bg-white px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-blue-600 hover:border-blue-200 hover:bg-blue-50"
                                        >
                                          Open chat
                                        </button>
                                      </div>
                                    </Show>
                                    <Show when={artifact.source_message_id}>
                                      <div>Message: {artifact.source_message_id}</div>
                                    </Show>
                                    <Show when={metadata().exportPaths.length > 0}>
                                      <div>Exports: {metadata().exportPaths.join(', ')}</div>
                                    </Show>
                                  </div>
                                </Show>
                              </div>
                            </details>
                          );
                        }}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>

          <div class="mt-2 rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleNotes}
              aria-expanded={props.isNotesExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Notes</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {props.workspaceNotes.length} total
                </div>
                <div class="mt-1 truncate text-[10px] text-slate-400" title={notesSummary()}>
                  {notesSummary()}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isNotesExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isNotesExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <div class="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleSaveNote()}
                    class="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 hover:border-emerald-300 hover:bg-emerald-100"
                  >
                    Save last reply
                  </button>
                </div>

                <Show when={noteFeedback()}>
                  <div class="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] text-emerald-700">
                    {noteFeedback()}
                  </div>
                </Show>

                <Show when={noteError()}>
                  <div class="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
                    {noteError()}
                  </div>
                </Show>

                <Show
                  when={!props.notesLoading}
                  fallback={<div class="mt-3 text-[11px] text-slate-400 italic">Loading saved notes...</div>}
                >
                  <Show
                    when={props.workspaceNotes.length > 0}
                    fallback={
                      <div class="mt-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-[11px] leading-relaxed text-slate-500">
                        No saved notes yet. Capture a strong assistant answer here to create reusable workspace context.
                      </div>
                    }
                  >
                    <div class="mt-3 space-y-2 max-h-72 overflow-y-auto no-scrollbar pr-1">
                      <For each={props.workspaceNotes}>
                        {(note) => {
                          const isActing = createMemo(() => noteActionId() === note.id);
                          const candidateForNote = createMemo(
                            () =>
                              props.workspaceMemoryCandidates.find(
                                (candidate) =>
                                  candidate.id === note.promotion_hint?.candidate_id ||
                                  candidate.id === note.source_metadata?.last_memory_candidate_id ||
                                  candidate.candidate_metadata?.note_id === note.id,
                              ) || null,
                          );
                          const hasPendingCandidate = createMemo(
                            () => candidateForNote()?.status === 'pending' || note.promotion_hint?.state === 'candidate_pending',
                          );
                          return (
                            <div class="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 shadow-sm">
                              <div class="flex items-start justify-between gap-2">
                                <div class="min-w-0">
                                  <div class="truncate text-[12px] font-semibold text-slate-800" title={note.title}>
                                    {note.title}
                                  </div>
                                  <div class="mt-1 flex flex-wrap items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                    <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                      {formatNoteTypeLabel(note.note_type)}
                                    </span>
                                    <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                      {formatCaptureTypeLabel(note.capture_type)}
                                    </span>
                                    <Show when={note.promoted_memory_id}>
                                      <span class="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
                                        promoted
                                      </span>
                                    </Show>
                                    <Show when={note.promotion_hint?.state && !note.promoted_memory_id}>
                                      <span
                                        class={`rounded border px-1.5 py-0.5 ${
                                          note.promotion_hint?.state === 'ready'
                                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                                            : note.promotion_hint?.state === 'candidate_pending'
                                              ? 'border-amber-200 bg-amber-50 text-amber-700'
                                              : 'border-slate-200 bg-white text-slate-500'
                                        }`}
                                      >
                                        {note.promotion_hint?.state === 'ready' && props.memorySuggestionsEnabled === false
                                          ? 'note only'
                                          : formatPromotionHintLabel(note.promotion_hint?.state)}
                                      </span>
                                    </Show>
                                  </div>
                                </div>
                              </div>

                              <Show when={note.tags && note.tags.length > 0}>
                                <div class="mt-2 flex flex-wrap gap-1">
                                  <For each={note.tags || []}>
                                    {(tag) => (
                                      <span class="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-600">
                                        {tag}
                                      </span>
                                    )}
                                  </For>
                                </div>
                              </Show>

                              <Show when={note.summary || note.content}>
                                <p class="mt-3 whitespace-pre-wrap text-[11px] leading-relaxed text-slate-700">
                                  {note.summary || note.content}
                                </p>
                              </Show>

                              <Show
                                when={
                                  props.memorySuggestionsEnabled !== false &&
                                  note.promotion_hint?.reason_summary &&
                                  !note.promoted_memory_id
                                }
                              >
                                <div class="mt-3 rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[10px] leading-relaxed text-slate-600">
                                  {note.promotion_hint?.reason_summary}
                                </div>
                              </Show>

                              <Show when={note.source_session_id || note.source_message_id || note.citation_refs?.length}>
                                <div class="mt-3 border-t border-slate-200 pt-2 text-[10px] leading-relaxed text-slate-500">
                                  <Show when={note.source_session_id}>
                                    <div class="flex items-center justify-between gap-2">
                                      <span class="truncate">Chat: {note.source_session_id}</span>
                                      <button
                                        type="button"
                                        onClick={() => {
                                          const chatId = note.source_session_id;
                                          if (chatId) props.onLoadChat(chatId);
                                        }}
                                        class="shrink-0 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                                      >
                                        Open chat
                                      </button>
                                    </div>
                                  </Show>
                                  <Show when={note.source_message_id}>
                                    <div>Message: {note.source_message_id}</div>
                                  </Show>
                                  <Show when={(note.citation_refs?.length || 0) > 0}>
                                    <div>Citations: {note.citation_refs?.length}</div>
                                  </Show>
                                </div>
                              </Show>

                              <Show
                                when={
                                  !note.promoted_memory_id &&
                                  (props.memorySuggestionsEnabled !== false || hasPendingCandidate())
                                }
                              >
                                <div class="mt-3 flex flex-wrap gap-2">
                                  <Show
                                    when={!hasPendingCandidate()}
                                    fallback={
                                      <span class="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700">
                                        Candidate pending
                                      </span>
                                    }
                                  >
                                    <button
                                      type="button"
                                      disabled={isActing()}
                                      onClick={() => void handleSuggestCandidateFromNote(note)}
                                      class="rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-blue-700 hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                      {isActing()
                                        ? 'Working...'
                                        : note.promotion_hint?.eligible
                                          ? 'Review as memory'
                                          : 'Create memory candidate'}
                                    </button>
                                  </Show>
                                </div>
                              </Show>
                            </div>
                          );
                        }}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>

          <div class="mt-2 rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleMemories}
              aria-expanded={props.isMemoriesExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Memory</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {props.workspaceMemories.length} total
                </div>
                <div class="mt-1 truncate text-[10px] text-slate-400" title={memoriesSummary()}>
                  {memoriesSummary()}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isMemoriesExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isMemoriesExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <div class="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={openCreateMemoryEditor}
                    class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:text-slate-800"
                  >
                    + Add card
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleSuggestCandidate()}
                    class="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 hover:border-emerald-300 hover:bg-emerald-100"
                  >
                    Review last reply
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleSuggestMemory()}
                    class="rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-blue-700 hover:border-blue-300 hover:bg-blue-100"
                  >
                    Open draft
                  </button>
                </div>

                <Show when={memoryError()}>
                  <div class="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
                    {memoryError()}
                  </div>
                </Show>

                <Show when={isMemoryEditorOpen()}>
                  <div class="mt-3 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3">
                    <div class="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-700">
                      {editingMemoryId() ? 'Edit memory card' : 'New memory card'}
                    </div>
                    <div class="mt-3 grid grid-cols-2 gap-2">
                      <select
                        value={memoryTypeInput()}
                        onChange={(e) => setMemoryTypeInput(e.currentTarget.value)}
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="project_fact">Project Fact</option>
                        <option value="preference">User Preference</option>
                        <option value="decision">Long-term Decision</option>
                        <option value="historical_conclusion">Historical Conclusion</option>
                        <option value="recurring_instruction">Recurring Instruction</option>
                        <option value="term">Term</option>
                        <option value="open_question">Open Question</option>
                      </select>
                      <select
                        value={memoryStatusInput()}
                        onChange={(e) => setMemoryStatusInput(e.currentTarget.value)}
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="active">Active</option>
                        <option value="disabled">Disabled</option>
                        <option value="archived">Archived</option>
                        <option value="superseded">Superseded</option>
                      </select>
                      <select
                        value={memoryScopeTypeInput()}
                        onChange={(e) => setMemoryScopeTypeInput(e.currentTarget.value)}
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      >
                        <option value="workspace">Workspace scope</option>
                        <option value="user">User scope</option>
                        <option value="project">Project scope</option>
                        <option value="chat">Chat scope</option>
                      </select>
                      <input
                        type="text"
                        value={memoryScopeRefInput()}
                        onInput={(e) => setMemoryScopeRefInput(e.currentTarget.value)}
                        placeholder="Scope ref (optional)"
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <input
                      type="text"
                      value={memoryTitleInput()}
                      onInput={(e) => setMemoryTitleInput(e.currentTarget.value)}
                      placeholder="Memory title"
                      class="mt-2 w-full rounded-lg border border-emerald-100 bg-white px-3 py-2 text-[12px] outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    <textarea
                      value={memoryContentInput()}
                      onInput={(e) => setMemoryContentInput(e.currentTarget.value)}
                      placeholder="What should this workspace remember?"
                      rows={4}
                      class="mt-2 w-full rounded-lg border border-emerald-100 bg-white px-3 py-2 text-[12px] leading-relaxed outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    <textarea
                      value={memoryWhySavedInput()}
                      onInput={(e) => setMemoryWhySavedInput(e.currentTarget.value)}
                      placeholder="Why should Yue keep this card?"
                      rows={2}
                      class="mt-2 w-full rounded-lg border border-emerald-100 bg-white px-3 py-2 text-[11px] leading-relaxed outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    <div class="mt-2 grid grid-cols-3 gap-2">
                      <input
                        type="text"
                        value={memoryConfidenceInput()}
                        onInput={(e) => setMemoryConfidenceInput(e.currentTarget.value)}
                        placeholder="Confidence"
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <input
                        type="text"
                        value={memorySourceSessionIdInput()}
                        onInput={(e) => setMemorySourceSessionIdInput(e.currentTarget.value)}
                        placeholder="Source chat id"
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <input
                        type="text"
                        value={memorySourceMessageIdInput()}
                        onInput={(e) => setMemorySourceMessageIdInput(e.currentTarget.value)}
                        placeholder="Source message id"
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <div class="mt-2 grid grid-cols-2 gap-2">
                      <input
                        type="datetime-local"
                        value={memoryExpiresAtInput()}
                        onInput={(e) => setMemoryExpiresAtInput(e.currentTarget.value)}
                        class="rounded-lg border border-emerald-100 bg-white px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <div class="grid grid-cols-2 gap-2 rounded-lg border border-emerald-100 bg-white px-3 py-2 text-[10px] text-slate-600">
                        <label class="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={memoryPinnedInput()}
                            onChange={(e) => setMemoryPinnedInput(e.currentTarget.checked)}
                          />
                          Pinned
                        </label>
                        <label class="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={memoryEditableInput()}
                            onChange={(e) => setMemoryEditableInput(e.currentTarget.checked)}
                          />
                          Editable
                        </label>
                        <label class="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={memoryRevocableInput()}
                            onChange={(e) => setMemoryRevocableInput(e.currentTarget.checked)}
                          />
                          Revocable
                        </label>
                      </div>
                    </div>
                    <textarea
                      value={memoryMetadataInput()}
                      onInput={(e) => setMemoryMetadataInput(e.currentTarget.value)}
                      rows={3}
                      placeholder='{"source_ids": ["src_1"]}'
                      class="mt-2 w-full rounded-lg border border-emerald-100 bg-white px-3 py-2 font-mono text-[11px] leading-relaxed outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    <div class="mt-3 flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          resetMemoryEditor();
                          setIsMemoryEditorOpen(false);
                        }}
                        class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:border-slate-300 hover:text-slate-800"
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        disabled={isMemorySubmitting()}
                        onClick={() => void handleSubmitMemory()}
                        class="rounded-lg bg-primary px-3 py-1.5 text-[11px] font-bold text-white shadow-sm transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isMemorySubmitting() ? 'Saving...' : editingMemoryId() ? 'Update card' : 'Save card'}
                      </button>
                    </div>
                  </div>
                </Show>

                <div class="mt-3 rounded-xl border border-blue-100 bg-blue-50/55 p-3">
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <div class="text-[10px] font-black uppercase tracking-[0.18em] text-blue-700">Candidates</div>
                      <div class="mt-1 text-[11px] leading-snug text-blue-800">
                        Review suggested memories before they affect future workspace chats.
                      </div>
                    </div>
                    <span class="rounded-full border border-blue-200 bg-white px-2 py-0.5 text-[10px] font-bold text-blue-700">
                      {pendingCandidateCount()} pending
                    </span>
                  </div>

                  <Show
                    when={pendingCandidates().length > 0}
                    fallback={
                      <div class="mt-3 rounded-lg border border-dashed border-blue-200 bg-white/70 px-3 py-3 text-[11px] leading-relaxed text-blue-700/80">
                        No pending candidates right now. Use “Review last reply” when an assistant answer contains a reusable fact, preference, or decision.
                      </div>
                    }
                  >
                    <div class="mt-3 space-y-2">
                      <For each={pendingCandidates()}>
                        {(candidate) => {
                          const conflictMemory = createMemo(
                            () => props.workspaceMemories.find((memory) => memory.id === candidate.conflict_memory_id) || null,
                          );
                          const candidateReasons = createMemo(() => {
                            const reasons = candidate.candidate_metadata?.score_reasons;
                            return Array.isArray(reasons) ? reasons.map((item) => String(item)) : [];
                          });
                          const conflictReasons = createMemo(() => {
                            const reasons = candidate.candidate_metadata?.conflict_reasons;
                            return Array.isArray(reasons) ? reasons.map((item) => String(item)) : [];
                          });
                          const isActing = createMemo(() => candidateActionMemoryId() === candidate.id);
                          return (
                            <div class="rounded-xl border border-blue-100 bg-white px-3 py-3 shadow-sm">
                              <div class="flex items-start justify-between gap-2">
                                <div class="min-w-0">
                                  <div class="truncate text-[12px] font-semibold text-slate-800" title={candidate.title}>
                                    {candidate.title}
                                  </div>
                                  <div class="mt-1 flex flex-wrap items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                    <span class="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5">
                                      {formatMemoryTypeLabel(candidate.memory_type)}
                                    </span>
                                    <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                      {formatMemoryScopeLabel(candidate.scope_type)}
                                    </span>
                                    <span class="rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-blue-700">
                                      {formatCandidateActionLabel(candidate.suggested_action)}
                                    </span>
                                    <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5 normal-case tracking-normal">
                                      score {formatCandidateScore(candidate.score)}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              <p class="mt-3 whitespace-pre-wrap text-[11px] leading-relaxed text-slate-700">
                                {candidate.content}
                              </p>

                              <Show when={candidate.why_saved}>
                                <div class="mt-3 rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-2 text-[10px] leading-relaxed text-slate-600">
                                  {candidate.why_saved}
                                </div>
                              </Show>

                              <Show when={candidateReasons().length > 0}>
                                <div class="mt-3 flex flex-wrap gap-1">
                                  <For each={candidateReasons()}>
                                    {(reason) => (
                                      <span class="rounded-full border border-blue-100 bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700">
                                        {reason}
                                      </span>
                                    )}
                                  </For>
                                </div>
                              </Show>

                              <Show when={conflictMemory()}>
                                <div class="mt-3 rounded-lg border border-amber-100 bg-amber-50/70 px-2.5 py-2">
                                  <div class="text-[10px] font-bold uppercase tracking-wide text-amber-700">
                                    Possible conflict
                                  </div>
                                  <div class="mt-1 text-[11px] text-amber-800">
                                    Existing card: {conflictMemory()!.title}
                                  </div>
                                  <Show when={conflictReasons().length > 0}>
                                    <div class="mt-1 flex flex-wrap gap-1">
                                      <For each={conflictReasons()}>
                                        {(reason) => (
                                          <span class="rounded-full border border-amber-200 bg-white px-2 py-0.5 text-[10px] text-amber-700">
                                            {reason}
                                          </span>
                                        )}
                                      </For>
                                    </div>
                                  </Show>
                                </div>
                              </Show>

                              <Show when={candidate.expires_at || candidate.source_session_id || candidate.source_message_id != null}>
                                <div class="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500">
                                  <Show when={candidate.expires_at}>
                                    <span>Expires {formatDateTimeLabel(candidate.expires_at)}</span>
                                  </Show>
                                  <Show when={candidate.source_session_id}>
                                    <span>Chat {candidate.source_session_id}</span>
                                  </Show>
                                  <Show when={candidate.source_message_id != null}>
                                    <span>Message {candidate.source_message_id}</span>
                                  </Show>
                                </div>
                              </Show>

                              <div class="mt-3 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  disabled={isActing()}
                                  onClick={() => void handleApproveCandidate(candidate, 'create_new')}
                                  class="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-700 hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  Add as new
                                </button>
                                <Show when={candidate.conflict_memory_id}>
                                  <button
                                    type="button"
                                    disabled={isActing()}
                                    onClick={() => void handleApproveCandidate(candidate, 'replace_existing')}
                                    class="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700 hover:border-amber-300 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    Replace existing
                                  </button>
                                  <button
                                    type="button"
                                    disabled={isActing()}
                                    onClick={() => void handleApproveCandidate(candidate, 'update_existing')}
                                    class="rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-blue-700 hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    Update existing
                                  </button>
                                </Show>
                                <button
                                  type="button"
                                  disabled={isActing()}
                                  onClick={() => void handleRejectCandidate(candidate.id)}
                                  class="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-rose-700 hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {isActing() ? 'Working...' : 'Dismiss'}
                                </button>
                              </div>
                            </div>
                          );
                        }}
                      </For>
                    </div>
                  </Show>
                </div>

                <Show
                  when={!props.memoriesLoading}
                  fallback={<div class="mt-3 text-[11px] text-slate-400 italic">Loading workspace memory...</div>}
                >
                  <Show when={props.workspaceMemories.length === 0}>
                    <div class="mt-3 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-[11px] leading-relaxed text-slate-500">
                      No memory cards yet. Save stable facts, preferences, and decisions so future workspace chats can reuse them.
                    </div>
                  </Show>
                  <Show when={props.workspaceMemories.length > 0}>
                    <div class="mt-3 space-y-3 max-h-80 overflow-y-auto pr-1">
                      <For each={memoryGroups()}>
                        {(group) => (
                          <div>
                            <div class="mb-2 flex items-center justify-between gap-2">
                              <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
                                {group.label}
                              </div>
                              <button
                                type="button"
                                disabled={!group.items.some((memory) => memory.editable !== false)}
                                onClick={() => void handleDisableMemoryType(group.memoryType)}
                                title={!group.items.some((memory) => memory.editable !== false) ? 'All cards in this group are locked for editing.' : undefined}
                                class="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-slate-500 hover:border-slate-300 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Disable all
                              </button>
                            </div>
                            <div class="space-y-2">
                              <For each={group.items}>
                                {(memory) => (
                                  <details class="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 transition-colors hover:border-slate-200 hover:bg-white">
                                    <summary class="cursor-pointer list-none">
                                      <div class="flex items-start justify-between gap-2">
                                        <div class="min-w-0">
                                          <div class="truncate text-[11px] font-semibold text-slate-700" title={memory.title}>
                                            {memory.title}
                                          </div>
                                          <div class="mt-1 flex flex-wrap items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                            <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                              {formatMemoryTypeLabel(memory.memory_type)}
                                            </span>
                                            <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                              {formatMemoryScopeLabel(memory.scope_type)}
                                            </span>
                                            <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5">
                                              {formatMemoryStatusLabel(memory.status)}
                                            </span>
                                          <Show when={memory.confidence != null}>
                                            <span class="rounded border border-slate-200 bg-white px-1.5 py-0.5 normal-case tracking-normal">
                                              conf {Number(memory.confidence).toFixed(2)}
                                            </span>
                                          </Show>
                                          <Show when={memory.pinned}>
                                            <span class="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 normal-case tracking-normal text-amber-700">
                                              pinned
                                            </span>
                                          </Show>
                                          <Show when={memory.supersedes_memory_id}>
                                            <span class="rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 normal-case tracking-normal text-blue-700">
                                              replaces older card
                                            </span>
                                          </Show>
                                        </div>
                                      </div>
                                        <span class="shrink-0 text-[9px] font-bold uppercase tracking-wide text-emerald-600">
                                          Detail
                                        </span>
                                      </div>
                                    </summary>

                                    <div class="mt-3 space-y-3 rounded-xl border border-emerald-100 bg-gradient-to-br from-white to-emerald-50/70 p-3 shadow-sm">
                                      <p class="whitespace-pre-wrap text-[11px] leading-relaxed text-slate-700">
                                        {memory.content}
                                      </p>

                                      <Show when={memory.why_saved}>
                                        <div class="rounded-lg border border-emerald-100 bg-white px-2.5 py-2 text-[10px] leading-relaxed text-slate-600">
                                          {memory.why_saved}
                                        </div>
                                      </Show>

                                      <Show when={memory.memory_metadata && Object.keys(memory.memory_metadata || {}).length > 0}>
                                        <pre class="max-h-28 overflow-auto rounded-lg border border-emerald-100 bg-white px-2 py-2 font-mono text-[10px] leading-relaxed text-slate-500">
                                          {JSON.stringify(memory.memory_metadata || {}, null, 2)}
                                        </pre>
                                      </Show>

                                      <div class="flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
                                        <Show when={memory.source_session_id}>
                                          <button
                                            type="button"
                                            onClick={() => {
                                              if (memory.source_session_id) props.onLoadChat(memory.source_session_id);
                                            }}
                                            class="rounded-full border border-emerald-100 bg-white px-2 py-0.5 font-bold uppercase tracking-wide text-emerald-700 hover:border-emerald-200 hover:bg-emerald-50"
                                          >
                                            Open source chat
                                          </button>
                                        </Show>
                                        <Show when={memory.source_message_id != null}>
                                          <span>Message: {memory.source_message_id}</span>
                                        </Show>
                                        <Show when={memory.last_used_at}>
                                          <span>Last loaded: {formatDateTimeLabel(memory.last_used_at)}</span>
                                        </Show>
                                        <Show when={memory.expires_at}>
                                          <span>Expires: {formatDateTimeLabel(memory.expires_at)}</span>
                                        </Show>
                                        <Show when={memory.editable === false}>
                                          <span>Locked editing</span>
                                        </Show>
                                        <Show when={memory.revocable === false}>
                                          <span>Not revocable</span>
                                        </Show>
                                      </div>

                                      <div class="flex flex-wrap gap-2">
                                        <button
                                          type="button"
                                          disabled={memory.editable === false}
                                          onClick={() => openEditMemoryEditor(memory)}
                                          title={memory.editable === false ? 'This memory card is locked for editing.' : undefined}
                                          class="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                          {memory.editable === false ? 'Locked' : 'Edit'}
                                        </button>
                                        <button
                                          type="button"
                                          disabled={memory.editable === false}
                                          onClick={() => void handleToggleMemoryStatus(memory)}
                                          title={memory.editable === false ? 'This memory card is locked for editing.' : undefined}
                                          class="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-700 hover:border-amber-300 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                          {memory.status === 'disabled' ? 'Enable' : 'Disable'}
                                        </button>
                                        <button
                                          type="button"
                                          disabled={memory.revocable === false}
                                          onClick={() => void props.onDeleteWorkspaceMemory(memory.id)}
                                          title={memory.revocable === false ? 'This memory card cannot be deleted or replaced.' : undefined}
                                          class="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-rose-700 hover:border-rose-300 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                          {memory.revocable === false ? 'Protected' : 'Delete'}
                                        </button>
                                      </div>
                                    </div>
                                  </details>
                                )}
                              </For>
                            </div>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
