import { createEffect, createMemo, createSignal, For, onMount, Show } from 'solid-js';
import { ConfirmModal } from '../components/ConfirmModal';
import type { Workspace, WorkspaceMemoryCandidate, WorkspaceMemoryCard, WorkspaceNote } from '../types';

type Note = WorkspaceNote;

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

const formatCandidateStatusLabel = (status?: string | null) => {
  switch (status) {
    case 'approved':
      return 'Approved';
    case 'rejected':
      return 'Rejected';
    case 'pending':
      return 'Pending';
    default:
      return status ? status.replace(/[_-]+/g, ' ') : 'Unknown';
  }
};

const formatCandidateScore = (score?: number | null) => {
  if (score == null || Number.isNaN(Number(score))) return 'n/a';
  return `${Math.round(Number(score) * 100)}%`;
};

const formatPromotionHintLabel = (state?: string | null) => {
  switch (state) {
    case 'ready':
      return 'Memory ready';
    case 'candidate_pending':
      return 'Candidate pending';
    case 'candidate_approved':
      return 'Candidate approved';
    case 'candidate_rejected':
      return 'Candidate rejected';
    case 'promoted':
      return 'Promoted';
    default:
      return state ? state.replace(/[_-]+/g, ' ') : 'Note only';
  }
};

export default function Notebook() {
  const [notes, setNotes] = createSignal<Note[]>([]);
  const [workspaces, setWorkspaces] = createSignal<Workspace[]>([]);
  const [workspaceMemories, setWorkspaceMemories] = createSignal<WorkspaceMemoryCard[]>([]);
  const [workspaceCandidates, setWorkspaceCandidates] = createSignal<WorkspaceMemoryCandidate[]>([]);
  const [selectedNote, setSelectedNote] = createSignal<Note | null>(null);

  const [editTitle, setEditTitle] = createSignal('');
  const [editContent, setEditContent] = createSignal('');
  const [saveStatus, setSaveStatus] = createSignal('');
  const [memoryStatus, setMemoryStatus] = createSignal('');
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);

  const [workspaceFilter, setWorkspaceFilter] = createSignal('all');
  const [noteTypeFilter, setNoteTypeFilter] = createSignal('all');
  const [captureTypeFilter, setCaptureTypeFilter] = createSignal('all');
  const [tagFilter, setTagFilter] = createSignal('');

  const loadWorkspaces = async () => {
    try {
      const res = await fetch('/api/workspaces/');
      const data = await res.json();
      setWorkspaces(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load workspaces', e);
    }
  };

  const buildNotesUrl = () => {
    const params = new URLSearchParams({ include_promotion_hints: 'true' });
    if (workspaceFilter() !== 'all') params.set('workspace_id', workspaceFilter());
    if (noteTypeFilter() !== 'all') params.set('note_type', noteTypeFilter());
    if (captureTypeFilter() !== 'all') params.set('capture_type', captureTypeFilter());
    if (tagFilter().trim()) params.set('tags', tagFilter().trim());
    const query = params.toString();
    return `/api/notebook/${query ? `?${query}` : ''}`;
  };

  const loadNotes = async () => {
    try {
      const res = await fetch(buildNotesUrl());
      const data = await res.json();
      const normalized = Array.isArray(data) ? (data as Note[]) : [];
      setNotes(normalized);
      const currentSelectedId = selectedNote()?.id;
      if (currentSelectedId) {
        const refreshed = normalized.find((note) => note.id === currentSelectedId) || null;
        setSelectedNote(refreshed);
        if (refreshed) {
          setEditTitle(refreshed.title);
          setEditContent(refreshed.content);
        }
      }
      return normalized;
    } catch (e) {
      console.error('Failed to load notes', e);
      return [];
    }
  };

  const loadMemoryReviewContext = async (workspaceId: string) => {
    try {
      const [candidatesRes, memoriesRes] = await Promise.all([
        fetch(`/api/workspaces/${workspaceId}/memory-candidates?include_reviewed=true`),
        fetch(`/api/workspaces/${workspaceId}/memory`),
      ]);
      const candidateData = await candidatesRes.json();
      const memoryData = await memoriesRes.json();
      setWorkspaceCandidates(Array.isArray(candidateData) ? candidateData : []);
      setWorkspaceMemories(Array.isArray(memoryData) ? memoryData : []);
    } catch (e) {
      console.error('Failed to load workspace memory review context', e);
      setWorkspaceCandidates([]);
      setWorkspaceMemories([]);
    }
  };

  onMount(() => {
    void loadWorkspaces();
  });

  createEffect(() => {
    workspaceFilter();
    noteTypeFilter();
    captureTypeFilter();
    tagFilter();
    void loadNotes();
  });

  createEffect(() => {
    const workspaceId = selectedNote()?.workspace_id;
    if (!workspaceId) {
      setWorkspaceCandidates([]);
      setWorkspaceMemories([]);
      return;
    }
    void loadMemoryReviewContext(workspaceId);
  });

  const selectedNoteCandidate = createMemo(() => {
    const note = selectedNote();
    if (!note) return null;
    const sourceMetadata = note.source_metadata || {};
    const candidateId =
      typeof sourceMetadata.last_memory_candidate_id === 'string' ? sourceMetadata.last_memory_candidate_id : null;
    return (
      workspaceCandidates().find(
        (candidate) =>
          candidate.id === candidateId ||
          candidate.candidate_metadata?.note_id === note.id,
      ) || null
    );
  });

  const candidateConflictMemory = createMemo(() => {
    const candidate = selectedNoteCandidate();
    if (!candidate?.conflict_memory_id) return null;
    return workspaceMemories().find((memory) => memory.id === candidate.conflict_memory_id) || null;
  });

  const workspaceOptions = createMemo(() => workspaces().map((workspace) => ({ id: workspace.id, name: workspace.name })));
  const noteTypeOptions = ['all', 'summary', 'insight', 'preference', 'decision', 'fact', 'reference', 'todo'];
  const captureTypeOptions = ['all', 'manual', 'chat_capture', 'source_capture', 'legacy_import'];

  const selectNote = (note: Note) => {
    setSelectedNote(note);
    setEditTitle(note.title);
    setEditContent(note.content);
    setSaveStatus('');
    setMemoryStatus('');
  };

  const createNote = async () => {
    const payload = {
      workspace_id: workspaceFilter() !== 'all' ? workspaceFilter() : undefined,
      title: 'Untitled Note',
      content: '',
    };
    try {
      const res = await fetch('/api/notebook/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      await loadNotes();
      selectNote(data);
    } catch (e) {
      console.error('Failed to create note', e);
    }
  };

  const saveNote = async () => {
    const note = selectedNote();
    if (!note) return;
    setSaveStatus('Saving...');
    try {
      const res = await fetch(`/api/notebook/${note.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle(),
          content: editContent(),
        }),
      });
      const data = await res.json();
      setSaveStatus('Saved!');
      setTimeout(() => setSaveStatus(''), 2000);
      setNotes((prev) => prev.map((item) => (item.id === data.id ? data : item)));
      setSelectedNote(data);
    } catch (e) {
      setSaveStatus('Error saving');
      console.error(e);
    }
  };

  const deleteNote = async (id: string) => {
    try {
      await fetch(`/api/notebook/${id}`, { method: 'DELETE' });
      await loadNotes();
      if (selectedNote()?.id === id) setSelectedNote(null);
    } catch (e) {
      console.error(e);
    }
  };

  const refreshSelectedNoteState = async () => {
    await loadNotes();
    const workspaceId = selectedNote()?.workspace_id;
    if (workspaceId) {
      await loadMemoryReviewContext(workspaceId);
    }
  };

  const createMemoryCandidate = async () => {
    const note = selectedNote();
    if (!note?.workspace_id) {
      setMemoryStatus('Workspace note required');
      setTimeout(() => setMemoryStatus(''), 2500);
      return;
    }
    setMemoryStatus('Creating candidate...');
    try {
      const res = await fetch(`/api/workspaces/${note.workspace_id}/notes/${note.id}/memory-candidates`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await refreshSelectedNoteState();
      setMemoryStatus('Candidate created');
      setTimeout(() => setMemoryStatus(''), 2500);
    } catch (e) {
      setMemoryStatus('Candidate failed');
      console.error('Failed to create memory candidate', e);
    }
  };

  const approveCandidate = async (approvalMode?: string) => {
    const note = selectedNote();
    const candidate = selectedNoteCandidate();
    if (!note?.workspace_id || !candidate) return;
    const resolvedMode =
      approvalMode ||
      candidate.suggested_action ||
      (candidate.conflict_memory_id ? 'update_existing' : 'create_new');
    setMemoryStatus('Approving...');
    try {
      const res = await fetch(`/api/workspaces/${note.workspace_id}/memory-candidates/${candidate.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          approval_mode: resolvedMode,
          target_memory_id: candidate.conflict_memory_id || undefined,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await refreshSelectedNoteState();
      setMemoryStatus('Approved');
      setTimeout(() => setMemoryStatus(''), 2500);
    } catch (e) {
      setMemoryStatus('Approval failed');
      console.error('Failed to approve memory candidate', e);
    }
  };

  const rejectCandidate = async () => {
    const note = selectedNote();
    const candidate = selectedNoteCandidate();
    if (!note?.workspace_id || !candidate) return;
    setMemoryStatus('Rejecting...');
    try {
      const res = await fetch(`/api/workspaces/${note.workspace_id}/memory-candidates/${candidate.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Rejected from notebook review' }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await refreshSelectedNoteState();
      setMemoryStatus('Rejected');
      setTimeout(() => setMemoryStatus(''), 2500);
    } catch (e) {
      setMemoryStatus('Reject failed');
      console.error('Failed to reject memory candidate', e);
    }
  };

  return (
    <div class="flex h-full bg-background transition-colors duration-250">
      <div class="w-1/3 border-r border-border bg-surface/50 flex flex-col transition-colors duration-250">
        <div class="border-b border-border bg-surface p-6 transition-colors duration-250">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-xl text-text-primary">Notebook</h2>
            <button
              onClick={createNote}
              class="bg-primary text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-primary-hover active:scale-95 transition-all shadow-lg shadow-primary/10"
            >
              + New Note
            </button>
          </div>
          <div class="mt-4 grid grid-cols-2 gap-2">
            <select
              value={workspaceFilter()}
              onChange={(e) => setWorkspaceFilter(e.currentTarget.value)}
              class="rounded-xl border border-border bg-background px-3 py-2 text-sm text-text-secondary outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="all">All workspaces</option>
              <For each={workspaceOptions()}>
                {(workspace) => <option value={workspace.id}>{workspace.name}</option>}
              </For>
            </select>
            <select
              value={noteTypeFilter()}
              onChange={(e) => setNoteTypeFilter(e.currentTarget.value)}
              class="rounded-xl border border-border bg-background px-3 py-2 text-sm text-text-secondary outline-none focus:ring-2 focus:ring-primary/20"
            >
              <For each={noteTypeOptions}>
                {(option) => <option value={option}>{option === 'all' ? 'All note types' : option}</option>}
              </For>
            </select>
            <select
              value={captureTypeFilter()}
              onChange={(e) => setCaptureTypeFilter(e.currentTarget.value)}
              class="rounded-xl border border-border bg-background px-3 py-2 text-sm text-text-secondary outline-none focus:ring-2 focus:ring-primary/20"
            >
              <For each={captureTypeOptions}>
                {(option) => <option value={option}>{option === 'all' ? 'All capture types' : option}</option>}
              </For>
            </select>
            <input
              type="text"
              value={tagFilter()}
              onInput={(e) => setTagFilter(e.currentTarget.value)}
              placeholder="Filter by tag"
              class="rounded-xl border border-border bg-background px-3 py-2 text-sm text-text-secondary outline-none placeholder:text-text-secondary/40 focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <div class="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border/50">
          <For each={notes()}>
            {(note) => (
              <div
                onClick={() => selectNote(note)}
                class={`p-5 border-b border-border/60 cursor-pointer hover:bg-surface transition-all duration-200 relative group ${
                  selectedNote()?.id === note.id ? 'bg-surface shadow-sm' : ''
                }`}
              >
                <div
                  class={`absolute left-0 top-0 bottom-0 w-1 bg-primary transition-transform duration-300 ${
                    selectedNote()?.id === note.id ? 'scale-y-100' : 'scale-y-0'
                  }`}
                />

                <div class="flex justify-between items-start mb-1">
                  <h3 class={`font-semibold text-base truncate pr-6 ${!note.title ? 'text-text-secondary/50 italic' : 'text-text-primary'}`}>
                    {note.title || 'Untitled Note'}
                  </h3>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDeleteId(note.id);
                    }}
                    class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 rounded-md hover:bg-red-50 transition-all"
                    title="Delete note"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>

                <div class="flex flex-wrap gap-2 mt-2">
                  <Show when={note.note_type}>
                    <span class="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
                      {note.note_type}
                    </span>
                  </Show>
                  <Show when={note.capture_type}>
                    <span class="rounded-full border border-border/70 bg-surface px-2.5 py-1 text-[11px] font-medium text-text-secondary">
                      {note.capture_type}
                    </span>
                  </Show>
                  <Show when={note.promoted_memory_id}>
                    <span class="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-medium text-cyan-700">
                      promoted
                    </span>
                  </Show>
                  <Show when={note.promotion_hint?.state && !note.promoted_memory_id}>
                    <span
                      class={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                        note.promotion_hint?.state === 'ready'
                          ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-700'
                          : note.promotion_hint?.state === 'candidate_pending'
                            ? 'border border-amber-500/20 bg-amber-500/10 text-amber-700'
                            : 'border border-border/70 bg-surface text-text-secondary'
                      }`}
                    >
                      {formatPromotionHintLabel(note.promotion_hint?.state)}
                    </span>
                  </Show>
                </div>

                <Show when={note.tags && note.tags.length}>
                  <div class="mt-2 flex flex-wrap gap-2">
                    <For each={(note.tags || []).slice(0, 3)}>
                      {(tag) => (
                        <span class="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-text-secondary border border-border/70">
                          #{tag}
                        </span>
                      )}
                    </For>
                  </div>
                </Show>

                <p class="text-sm text-text-secondary mt-3 line-clamp-2 leading-relaxed">
                  {note.summary || note.content || 'No content'}
                </p>

                <div class="mt-3 flex items-center justify-between gap-2 text-[11px] text-text-secondary/70 font-medium">
                  <div class="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {new Date(note.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                  </div>
                  <Show when={note.workspace_id}>
                    <span class="truncate text-[10px]" title={note.workspace_id || undefined}>
                      {note.workspace_id}
                    </span>
                  </Show>
                </div>
              </div>
            )}
          </For>

          <Show when={notes().length === 0}>
            <div class="p-12 text-center">
              <div class="w-16 h-16 bg-surface border border-border rounded-2xl flex items-center justify-center mx-auto mb-4 text-text-secondary/30">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <p class="text-text-secondary text-sm">No notes match the current filters.</p>
            </div>
          </Show>
        </div>
      </div>

      <div class="flex-1 flex flex-col bg-surface transition-colors duration-250">
        <Show
          when={selectedNote()}
          fallback={
            <div class="flex-1 flex flex-col items-center justify-center text-text-secondary/30 bg-background/50">
              <div class="w-24 h-24 rounded-3xl border-2 border-dashed border-border flex items-center justify-center mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <p class="text-lg font-medium">Select a note to view or edit</p>
              <p class="text-sm mt-2">All your thoughts, neatly organized in one place.</p>
            </div>
          }
        >
          <div class="px-8 py-6 border-b border-border flex justify-between items-center bg-surface/80 backdrop-blur-sm sticky top-0 z-10">
            <div class="min-w-0 flex-1 pr-6">
              <input
                type="text"
                value={editTitle()}
                onInput={(e) => setEditTitle(e.currentTarget.value)}
                placeholder="Note Title"
                class="text-2xl font-bold text-text-primary bg-transparent border-none focus:ring-0 focus:outline-none w-full placeholder:text-text-secondary/30"
              />
              <div class="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <Show when={selectedNote()?.note_type}>
                  <span class="rounded-full bg-primary/10 px-2.5 py-1 font-semibold uppercase tracking-wide text-primary">
                    {selectedNote()?.note_type}
                  </span>
                </Show>
                <Show when={selectedNote()?.capture_type}>
                  <span class="rounded-full bg-surface px-2.5 py-1 font-medium text-text-secondary border border-border/70">
                    {selectedNote()?.capture_type}
                  </span>
                </Show>
                <Show when={selectedNote()?.workspace_id}>
                  <span class="rounded-full bg-surface px-2.5 py-1 font-medium text-text-secondary border border-border/70">
                    workspace {selectedNote()?.workspace_id}
                  </span>
                </Show>
                <Show when={selectedNote()?.source_session_id}>
                  <span class="rounded-full bg-surface px-2.5 py-1 font-medium text-text-secondary border border-border/70">
                    chat {selectedNote()?.source_session_id}
                  </span>
                </Show>
                <Show when={selectedNote()?.promoted_memory_id}>
                  <span class="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2.5 py-1 font-medium text-cyan-700">
                    promoted to memory
                  </span>
                </Show>
                <Show when={selectedNote()?.promotion_hint?.state && !selectedNote()?.promoted_memory_id}>
                  <span
                    class={`rounded-full px-2.5 py-1 font-medium ${
                      selectedNote()?.promotion_hint?.state === 'ready'
                        ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-700'
                        : selectedNote()?.promotion_hint?.state === 'candidate_pending'
                          ? 'border border-amber-500/20 bg-amber-500/10 text-amber-700'
                          : 'bg-surface text-text-secondary border border-border/70'
                    }`}
                  >
                    {formatPromotionHintLabel(selectedNote()?.promotion_hint?.state)}
                  </span>
                </Show>
              </div>
            </div>
            <div class="flex items-center gap-4">
              <Show when={selectedNote()?.workspace_id && !selectedNote()?.promoted_memory_id && !selectedNoteCandidate()}>
                <button
                  onClick={createMemoryCandidate}
                  class="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-2.5 text-sm font-semibold text-cyan-700 transition-all hover:border-cyan-500/40 hover:bg-cyan-500/10 active:scale-95"
                >
                  {selectedNote()?.promotion_hint?.eligible ? 'Review as Memory' : 'Create Memory Candidate'}
                </button>
              </Show>
              <span class={`text-sm font-medium transition-opacity duration-300 ${saveStatus() ? 'opacity-100' : 'opacity-0'} ${saveStatus() === 'Error saving' ? 'text-red-500' : 'text-primary'}`}>
                {saveStatus()}
              </span>
              <span
                class={`text-sm font-medium transition-opacity duration-300 ${
                  memoryStatus() ? 'opacity-100' : 'opacity-0'
                } ${
                  ['Candidate failed', 'Workspace note required', 'Approval failed', 'Reject failed'].includes(memoryStatus())
                    ? 'text-red-500'
                    : 'text-cyan-700'
                }`}
              >
                {memoryStatus()}
              </span>
              <button
                onClick={saveNote}
                class="bg-primary text-white px-6 py-2.5 rounded-xl font-semibold hover:bg-primary-hover active:scale-95 transition-all shadow-lg shadow-primary/20 flex items-center gap-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Save
              </button>
            </div>
          </div>

          <div class="border-b border-border bg-background/30 px-8 py-4 lg:px-12">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-secondary/70">Summary</p>
            <p class="mt-2 text-sm leading-relaxed text-text-secondary">
              {selectedNote()?.summary || 'No summary generated yet.'}
            </p>
            <Show when={selectedNote()?.tags && (selectedNote()?.tags?.length || 0) > 0}>
              <div class="mt-4 flex flex-wrap gap-2">
                <For each={selectedNote()?.tags || []}>
                  {(tag) => (
                    <span class="rounded-full bg-surface px-2.5 py-1 text-[11px] font-medium text-text-secondary border border-border/70">
                      #{tag}
                    </span>
                  )}
                </For>
              </div>
            </Show>
          </div>

          <Show when={selectedNote()?.promotion_hint && !selectedNote()?.promoted_memory_id && !selectedNoteCandidate()}>
            <div class="border-b border-border bg-emerald-500/[0.04] px-8 py-4 lg:px-12">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700/80">Memory hint</p>
              <p class="mt-2 text-sm leading-relaxed text-text-secondary">
                {selectedNote()?.promotion_hint?.reason_summary || 'This note can stay as a note or move into memory review.'}
              </p>
              <div class="mt-3 flex flex-wrap gap-2 text-[11px]">
                <Show when={selectedNote()?.promotion_hint?.memory_type}>
                  <span class="rounded-full border border-emerald-500/20 bg-white px-2.5 py-1 font-medium text-emerald-700">
                    {selectedNote()?.promotion_hint?.memory_type}
                  </span>
                </Show>
                <Show when={selectedNote()?.promotion_hint?.confidence != null}>
                  <span class="rounded-full border border-border/70 bg-surface px-2.5 py-1 font-medium text-text-secondary">
                    confidence {formatCandidateScore(selectedNote()?.promotion_hint?.confidence)}
                  </span>
                </Show>
                <Show when={selectedNote()?.promotion_hint?.conflict_memory_title}>
                  <span class="rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-1 font-medium text-amber-800">
                    relates to {selectedNote()?.promotion_hint?.conflict_memory_title}
                  </span>
                </Show>
              </div>
            </div>
          </Show>

          <Show when={selectedNoteCandidate()}>
            <div class="border-b border-border bg-cyan-500/[0.04] px-8 py-4 lg:px-12">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-700/80">Memory review</p>
                  <p class="mt-2 text-sm font-semibold text-text-primary">
                    {selectedNoteCandidate()?.title}
                  </p>
                  <div class="mt-2 flex flex-wrap gap-2 text-[11px]">
                    <span class="rounded-full border border-cyan-500/20 bg-white px-2.5 py-1 font-medium text-cyan-700">
                      {formatCandidateStatusLabel(selectedNoteCandidate()?.status)}
                    </span>
                    <span class="rounded-full border border-cyan-500/20 bg-white px-2.5 py-1 font-medium text-cyan-700">
                      {formatCandidateActionLabel(selectedNoteCandidate()?.suggested_action)}
                    </span>
                    <span class="rounded-full border border-border/70 bg-surface px-2.5 py-1 font-medium text-text-secondary">
                      score {formatCandidateScore(selectedNoteCandidate()?.score)}
                    </span>
                  </div>
                  <p class="mt-3 text-sm leading-relaxed text-text-secondary">
                    {selectedNoteCandidate()?.content}
                  </p>
                  <Show when={candidateConflictMemory()}>
                    <div class="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-[12px] leading-relaxed text-amber-800">
                      Possible conflict with existing memory: {candidateConflictMemory()?.title}
                    </div>
                  </Show>
                </div>
                <Show when={selectedNoteCandidate()?.status === 'pending'}>
                  <div class="flex shrink-0 flex-wrap gap-2">
                    <button
                      onClick={() => approveCandidate('create_new')}
                      class="rounded-xl border border-border bg-white px-3 py-2 text-sm font-semibold text-text-primary transition-all hover:border-primary/30 hover:bg-primary/5"
                    >
                      Add as New
                    </button>
                    <Show when={selectedNoteCandidate()?.conflict_memory_id}>
                      <button
                        onClick={() => approveCandidate('replace_existing')}
                        class="rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-800 transition-all hover:border-amber-500/40"
                      >
                        Replace Existing
                      </button>
                      <button
                        onClick={() => approveCandidate('update_existing')}
                        class="rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-800 transition-all hover:border-cyan-500/40"
                      >
                        Update Existing
                      </button>
                    </Show>
                    <button
                      onClick={rejectCandidate}
                      class="rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-sm font-semibold text-rose-700 transition-all hover:border-rose-500/40"
                    >
                      Reject
                    </button>
                  </div>
                </Show>
              </div>
            </div>
          </Show>

          <textarea
            value={editContent()}
            onInput={(e) => setEditContent(e.currentTarget.value)}
            placeholder="Start writing your thoughts..."
            class="flex-1 p-8 lg:p-12 resize-none focus:outline-none text-text-primary bg-transparent leading-relaxed font-sans text-lg placeholder:text-text-secondary/20"
          />
        </Show>
      </div>

      <ConfirmModal
        show={!!confirmDeleteId()}
        title="Delete Note"
        message="Are you sure you want to delete this note? This action cannot be undone."
        confirmText="Delete Note"
        cancelText="Keep Note"
        type="danger"
        onConfirm={() => {
          const id = confirmDeleteId();
          if (id) {
            deleteNote(id);
            setConfirmDeleteId(null);
          }
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
