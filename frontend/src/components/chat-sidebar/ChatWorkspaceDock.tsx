import { For, Show, createEffect, createMemo, createSignal } from 'solid-js';
import ChatSidebarResources from '../ChatSidebarResources';
import { formatWorkspaceCountLabel, getWorkspaceSourceReadinessCounts } from './sidebarFilters';
import type { ChatSidebarProps } from './types';

type ChatWorkspaceDockProps = Pick<
  ChatSidebarProps,
  | 'workspaces'
  | 'selectedWorkspaceId'
  | 'workspaceSources'
  | 'workspaceArtifacts'
  | 'workspaceNotes'
  | 'workspaceMemories'
  | 'workspaceMemoryCandidates'
  | 'workspaceSourceMode'
  | 'selectedWorkspaceSourceIds'
  | 'groundingMode'
  | 'workspaceLoading'
  | 'sourcesLoading'
  | 'artifactsLoading'
  | 'notesLoading'
  | 'memoriesLoading'
  | 'memorySuggestionsEnabled'
  | 'onNewChat'
  | 'onSelectWorkspace'
  | 'onCreateWorkspace'
  | 'onWorkspaceSourceModeChange'
  | 'onToggleWorkspaceSource'
  | 'onGroundingModeChange'
  | 'onCheckWorkspaceSources'
  | 'onCheckWorkspaceSource'
  | 'onLoadChat'
  | 'onSaveLastAssistantAsWorkspaceNote'
  | 'onSuggestWorkspaceMemoryFromLastAssistantMessage'
  | 'onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage'
  | 'onSuggestWorkspaceMemoryCandidateFromNote'
  | 'onCreateWorkspaceMemory'
  | 'onUpdateWorkspaceMemory'
  | 'onBulkUpdateWorkspaceMemoryStatusByType'
  | 'onDeleteWorkspaceMemory'
  | 'onApproveWorkspaceMemoryCandidate'
  | 'onRejectWorkspaceMemoryCandidate'
>;

export function ChatWorkspaceDock(props: ChatWorkspaceDockProps) {
  const [isOpen, setIsOpen] = createSignal(false);
  const [showCreateWorkspace, setShowCreateWorkspace] = createSignal(false);
  const [newWorkspaceName, setNewWorkspaceName] = createSignal('');
  const [isResourcesExpanded, setIsResourcesExpanded] = createSignal(false);
  const [isSourcesExpanded, setIsSourcesExpanded] = createSignal(false);
  const [isArtifactsExpanded, setIsArtifactsExpanded] = createSignal(false);
  const [isNotesExpanded, setIsNotesExpanded] = createSignal(false);
  const [isMemoriesExpanded, setIsMemoriesExpanded] = createSignal(false);
  const [panelDefaultsWorkspaceId, setPanelDefaultsWorkspaceId] = createSignal<string | null>(null);
  const [lastWorkspaceNoteCount, setLastWorkspaceNoteCount] = createSignal(0);

  const selectedWorkspace = createMemo(() =>
    props.workspaces.find((workspace) => workspace.id === props.selectedWorkspaceId) || null,
  );
  const workspaceReadiness = createMemo(() => getWorkspaceSourceReadinessCounts(props.workspaceSources));
  const formatWorkspaceDate = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };
  const hasWorkspaceSignal = createMemo(
    () =>
      !!props.selectedWorkspaceId ||
      props.workspaceSources.length > 0 ||
      props.workspaceArtifacts.length > 0 ||
      props.workspaceNotes.length > 0 ||
      props.workspaceMemoryCandidates.length > 0,
  );
  const workspaceHeaderSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'Pick a workspace to group sources, saved work, and related chats.';
    if (props.workspaceLoading || props.sourcesLoading || props.artifactsLoading) return 'Loading workspace context.';

    const readiness = workspaceReadiness();
    const parts: string[] = [];
    if (readiness.total > 0) {
      parts.push(formatWorkspaceCountLabel(readiness.ready, 'ready source'));
      if (readiness.attention > 0) {
        parts.push(
          formatWorkspaceCountLabel(readiness.attention, 'source needing attention', 'sources needing attention'),
        );
      }
    } else {
      parts.push('No sources yet');
    }
    parts.push(
      props.workspaceArtifacts.length > 0
        ? formatWorkspaceCountLabel(props.workspaceArtifacts.length, 'saved artifact')
        : 'No saved artifacts yet',
    );
    parts.push(
      props.workspaceNotes.length > 0
        ? formatWorkspaceCountLabel(props.workspaceNotes.length, 'saved note')
        : 'No saved notes yet',
    );
    return parts.join(' · ');
  });

  createEffect(() => {
    if (!props.selectedWorkspaceId) {
      setPanelDefaultsWorkspaceId(null);
      setIsResourcesExpanded(false);
      setIsSourcesExpanded(false);
      setIsArtifactsExpanded(false);
      setIsNotesExpanded(false);
      setIsMemoriesExpanded(false);
      return;
    }
    if (props.sourcesLoading || props.artifactsLoading || props.notesLoading) return;
    if (panelDefaultsWorkspaceId() === props.selectedWorkspaceId) return;

    const noSourcesYet = props.workspaceSources.length === 0;
    const hasSourceAttention = props.workspaceSources.some((source) => source.status !== 'ready');
    setIsResourcesExpanded(true);
    setIsSourcesExpanded(noSourcesYet || props.workspaceSourceMode === 'selected' || hasSourceAttention);
    setIsArtifactsExpanded(props.workspaceArtifacts.length > 0 && props.workspaceArtifacts.length <= 2);
    setIsNotesExpanded(props.workspaceNotes.length > 0);
    setIsMemoriesExpanded(props.workspaceMemories.length > 0 || props.workspaceMemoryCandidates.length > 0);
    setLastWorkspaceNoteCount(props.workspaceNotes.length);
    setPanelDefaultsWorkspaceId(props.selectedWorkspaceId);
  });

  createEffect(() => {
    if (!props.selectedWorkspaceId || props.notesLoading) return;
    const previousCount = lastWorkspaceNoteCount();
    const nextCount = props.workspaceNotes.length;
    if (nextCount > previousCount) {
      setIsResourcesExpanded(true);
      setIsNotesExpanded(true);
    }
    setLastWorkspaceNoteCount(nextCount);
  });

  const handleCreateWorkspace = async () => {
    const name = newWorkspaceName().trim();
    if (!name) return;
    await props.onCreateWorkspace(name);
    setNewWorkspaceName('');
    setShowCreateWorkspace(false);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen()}
        title="Workspace"
        class={`fixed left-2 top-[21rem] z-[60] flex h-12 w-12 items-center justify-center rounded-xl border text-sm font-black shadow-lg transition-all active:scale-95 lg:left-2 ${
          isOpen()
            ? 'border-primary/30 bg-primary text-white shadow-primary/20'
            : 'border-border bg-surface text-text-secondary hover:bg-primary/10 hover:text-primary'
        }`}
      >
        W
        <Show when={hasWorkspaceSignal()}>
          <span class="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-surface" />
        </Show>
      </button>

      <Show when={isOpen()}>
        <div
          class="fixed inset-0 z-40 bg-black/10 backdrop-blur-[1px] lg:hidden"
          onClick={() => setIsOpen(false)}
        />
        <aside class="fixed bottom-4 left-[4.75rem] top-4 z-[60] flex w-[min(360px,calc(100vw-5.5rem))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div class="border-b border-slate-200 bg-white/95 px-4 py-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Workspace</div>
                <div class="mt-1 truncate text-sm font-semibold text-slate-800" title={selectedWorkspace()?.name || 'All Workspaces'}>
                  {selectedWorkspace()?.name || 'All Workspaces'}
                </div>
                <div class="mt-1 text-[11px] leading-snug text-slate-500">{workspaceHeaderSummary()}</div>
              </div>
              <div class="flex items-center gap-2">
                <Show when={props.workspaceLoading}>
                  <span class="text-[10px] text-slate-400">Loading</span>
                </Show>
                <button
                  type="button"
                  onClick={() => setShowCreateWorkspace((prev) => !prev)}
                  aria-expanded={showCreateWorkspace()}
                  class="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:text-slate-800"
                  title="Create workspace"
                >
                  + New
                </button>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  class="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                  title="Close workspace"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="mt-3 rounded-xl border border-slate-200 bg-slate-50/80">
              <div class="max-h-52 overflow-y-auto p-1.5">
                <button
                  type="button"
                  onClick={() => props.onSelectWorkspace(null)}
                  class={`mb-1 flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                    !props.selectedWorkspaceId
                      ? 'border-primary/25 bg-primary/10 text-slate-900'
                      : 'border-transparent bg-white text-slate-700 hover:border-slate-200 hover:bg-slate-50'
                  }`}
                  title="All Workspaces"
                >
                  <span class="min-w-0">
                    <span class="block truncate text-xs font-bold">All Workspaces</span>
                    <span class="mt-0.5 block truncate text-[10px] font-medium text-slate-500">
                      Show every chat session
                    </span>
                  </span>
                  <span
                    class={`h-2 w-2 shrink-0 rounded-full ${
                      !props.selectedWorkspaceId ? 'bg-primary' : 'bg-slate-300'
                    }`}
                  />
                </button>
                <For
                  each={props.workspaces}
                  fallback={
                    <div class="px-3 py-4 text-center text-xs text-slate-400">
                      No workspaces yet
                    </div>
                  }
                >
                  {(workspace) => {
                    const isSelected = () => props.selectedWorkspaceId === workspace.id;
                    return (
                      <button
                        type="button"
                        onClick={() => props.onSelectWorkspace(workspace.id)}
                        class={`flex w-full items-start justify-between gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                          isSelected()
                            ? 'border-primary/25 bg-primary/10 text-slate-900'
                            : 'border-transparent bg-white text-slate-700 hover:border-slate-200 hover:bg-slate-50'
                        }`}
                        title={workspace.name}
                      >
                        <span class="min-w-0">
                          <span class="block truncate text-xs font-bold">{workspace.name}</span>
                          <span class="mt-0.5 block truncate text-[10px] font-medium text-slate-500">
                            Updated {formatWorkspaceDate(workspace.updated_at) || 'recently'}
                          </span>
                        </span>
                        <span
                          class={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                            isSelected() ? 'bg-primary' : 'bg-slate-300'
                          }`}
                        />
                      </button>
                    );
                  }}
                </For>
              </div>
            </div>
            <Show when={showCreateWorkspace()}>
              <div class="mt-3 flex gap-2">
                <input
                  type="text"
                  value={newWorkspaceName()}
                  onInput={(e) => setNewWorkspaceName(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      void handleCreateWorkspace();
                    }
                    if (e.key === 'Escape') setShowCreateWorkspace(false);
                  }}
                  placeholder="Create workspace"
                  class="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs outline-none transition-all focus:ring-2 focus:ring-primary/20"
                />
                <button
                  onClick={() => void handleCreateWorkspace()}
                  class="rounded-lg bg-primary px-3 py-2 text-[11px] font-bold text-white shadow-sm transition-colors hover:bg-primary-hover active:scale-95"
                  title="Create workspace"
                >
                  Add
                </button>
              </div>
            </Show>
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-4 py-3">
            <div class="mb-3 flex items-center justify-between gap-3">
              <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Resources</div>
              <button
                onClick={props.onNewChat}
                class="shrink-0 rounded-lg bg-primary px-3 py-2 text-[11px] font-bold text-white shadow-sm transition-colors hover:bg-primary-hover active:scale-95"
                title="New Chat"
              >
                New Chat
              </button>
            </div>
            <ChatSidebarResources
              selectedWorkspaceId={props.selectedWorkspaceId}
              workspaceSources={props.workspaceSources}
              workspaceArtifacts={props.workspaceArtifacts}
              workspaceNotes={props.workspaceNotes}
              workspaceMemories={props.workspaceMemories}
              workspaceMemoryCandidates={props.workspaceMemoryCandidates}
              workspaceSourceMode={props.workspaceSourceMode}
              selectedWorkspaceSourceIds={props.selectedWorkspaceSourceIds}
              groundingMode={props.groundingMode}
              sourcesLoading={props.sourcesLoading}
              artifactsLoading={props.artifactsLoading}
              notesLoading={props.notesLoading}
        memoriesLoading={props.memoriesLoading}
        memorySuggestionsEnabled={props.memorySuggestionsEnabled}
        isResourcesExpanded={isResourcesExpanded()}
              isSourcesExpanded={isSourcesExpanded()}
              isArtifactsExpanded={isArtifactsExpanded()}
              isNotesExpanded={isNotesExpanded()}
              isMemoriesExpanded={isMemoriesExpanded()}
              onToggleResources={() => setIsResourcesExpanded((prev) => !prev)}
              onToggleSources={() => setIsSourcesExpanded((prev) => !prev)}
              onToggleArtifacts={() => setIsArtifactsExpanded((prev) => !prev)}
              onToggleNotes={() => setIsNotesExpanded((prev) => !prev)}
              onToggleMemories={() => setIsMemoriesExpanded((prev) => !prev)}
              onWorkspaceSourceModeChange={props.onWorkspaceSourceModeChange}
              onToggleWorkspaceSource={props.onToggleWorkspaceSource}
              onGroundingModeChange={props.onGroundingModeChange}
              onCheckWorkspaceSources={props.onCheckWorkspaceSources}
              onCheckWorkspaceSource={props.onCheckWorkspaceSource}
              onLoadChat={props.onLoadChat}
              onSaveLastAssistantAsWorkspaceNote={props.onSaveLastAssistantAsWorkspaceNote}
              onSuggestWorkspaceMemoryFromLastAssistantMessage={props.onSuggestWorkspaceMemoryFromLastAssistantMessage}
              onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage={props.onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage}
              onSuggestWorkspaceMemoryCandidateFromNote={props.onSuggestWorkspaceMemoryCandidateFromNote}
              onCreateWorkspaceMemory={props.onCreateWorkspaceMemory}
              onUpdateWorkspaceMemory={props.onUpdateWorkspaceMemory}
              onBulkUpdateWorkspaceMemoryStatusByType={props.onBulkUpdateWorkspaceMemoryStatusByType}
              onDeleteWorkspaceMemory={props.onDeleteWorkspaceMemory}
              onApproveWorkspaceMemoryCandidate={props.onApproveWorkspaceMemoryCandidate}
              onRejectWorkspaceMemoryCandidate={props.onRejectWorkspaceMemoryCandidate}
            />
          </div>
        </aside>
      </Show>
    </>
  );
}
