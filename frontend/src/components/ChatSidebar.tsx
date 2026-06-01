import { For, Show, createEffect, createMemo, createSignal, onCleanup, onMount } from 'solid-js';
import { ChatSession, Workspace, WorkspaceArtifact, WorkspaceSource } from '../types';
import { filterChatsByWorkspace } from './ChatSidebar.helpers';
import ChatSidebarResources from './ChatSidebarResources';

interface ChatSidebarProps {
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

type DatePreset = 'all' | 'today' | '7d' | '30d';
type TagMode = 'any' | 'all';
type FilterState = {
  query: string;
  selectedTags: string[];
  tagMode: TagMode;
  datePreset: DatePreset;
};
type SavedPreset = FilterState & {
  id: string;
  name: string;
};

const FILTER_STATE_PREF_KEY = 'chat_history_filter_state';
const FILTER_PRESETS_PREF_KEY = 'chat_history_filter_presets';

const isDatePreset = (value: unknown): value is DatePreset =>
  value === 'all' || value === 'today' || value === '7d' || value === '30d';

const isTagMode = (value: unknown): value is TagMode => value === 'any' || value === 'all';

const parseServerDate = (value: string): Date => {
  const trimmed = String(value || '').trim();
  if (!trimmed) return new Date(NaN);
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return new Date(trimmed);
  }
  // Backend stores naive UTC in some flows; treat timezone-less timestamps as UTC.
  return new Date(`${trimmed}Z`);
};

const DEFAULT_WIDTH = 260;

export default function ChatSidebar(props: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = createSignal('');
  const [selectedTags, setSelectedTags] = createSignal<string[]>([]);
  const [tagMode, setTagMode] = createSignal<'any' | 'all'>('any');
  const [datePreset, setDatePreset] = createSignal<'all' | 'today' | '7d' | '30d'>('all');
  const [collapsedGroups, setCollapsedGroups] = createSignal<Record<string, boolean>>({});
  const [savedPresets, setSavedPresets] = createSignal<SavedPreset[]>([]);
  const [prefsReady, setPrefsReady] = createSignal(false);
  const [newWorkspaceName, setNewWorkspaceName] = createSignal('');
  const [showCreateWorkspace, setShowCreateWorkspace] = createSignal(false);
  const [isResourcesExpanded, setIsResourcesExpanded] = createSignal(false);
  const [isSourcesExpanded, setIsSourcesExpanded] = createSignal(false);
  const [isArtifactsExpanded, setIsArtifactsExpanded] = createSignal(false);

  const matchesDatePreset = (iso: string) => {
    const preset = datePreset();
    if (preset === 'all') return true;
    const date = parseServerDate(iso);
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (preset === 'today') {
      return date >= startOfToday;
    }
    const days = preset === '7d' ? 7 : 30;
    const threshold = new Date(startOfToday);
    threshold.setDate(threshold.getDate() - (days - 1));
    return date >= threshold;
  };

  const filteredChats = createMemo(() => {
    const query = searchQuery().trim().toLowerCase();
    const tags = selectedTags();
    const mode = tagMode();

    return filterChatsByWorkspace(props.chats, props.selectedWorkspaceId).filter((chat) => {
      if (!matchesDatePreset(chat.updated_at)) return false;

      if (query) {
        const haystack = `${chat.title} ${chat.summary || ''} ${(chat.tags || []).join(' ')}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }

      if (tags.length > 0) {
        const chatTags = chat.tags || [];
        if (mode === 'all') {
          if (!tags.every(tag => chatTags.includes(tag))) return false;
        } else if (!tags.some(tag => chatTags.includes(tag))) {
          return false;
        }
      }

      return true;
    });
  });

  const groupedChats = createMemo(() => {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    const startOfYesterday = new Date(startOfToday);
    startOfYesterday.setDate(startOfYesterday.getDate() - 1);
    
    const startOfLast7Days = new Date(startOfToday);
    startOfLast7Days.setDate(startOfLast7Days.getDate() - 7);

    const groups = [
      { key: 'today', label: 'Today', type: 'today', isToday: true, chats: [] as ChatSession[] },
      { key: 'yesterday', label: 'Yesterday', type: 'yesterday', isToday: false, chats: [] as ChatSession[] },
      { key: 'last7days', label: 'Last 7 Days', type: 'last7days', isToday: false, chats: [] as ChatSession[] },
      { key: 'earlier', label: 'Earlier', type: 'earlier', isToday: false, chats: [] as ChatSession[] }
    ];

    for (const chat of filteredChats()) {
      const dt = parseServerDate(chat.updated_at);
      if (dt >= startOfToday) {
        groups[0].chats.push(chat);
      } else if (dt >= startOfYesterday) {
        groups[1].chats.push(chat);
      } else if (dt >= startOfLast7Days) {
        groups[2].chats.push(chat);
      } else {
        groups[3].chats.push(chat);
      }
    }

    return groups.filter(g => g.chats.length > 0);
  });

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedTags([]);
    setTagMode('any');
    setDatePreset('all');
  };

  const isGroupCollapsed = (group: { key: string, chats: ChatSession[] }) => {
    const manualState = collapsedGroups()[group.key];
    if (manualState !== undefined) return manualState;
    // Auto-expand group containing the active chat
    if (props.currentChatId && group.chats.some(c => c.id === props.currentChatId)) return false;
    // Default strategy: expand Today and Yesterday, collapse older groups to reduce cognitive load
    return group.key !== 'today' && group.key !== 'yesterday';
  };

  const toggleGroup = (key: string) => {
    const group = groupedChats().find(g => g.key === key);
    if (!group) return;
    const currentlyCollapsed = isGroupCollapsed(group);
    setCollapsedGroups(prev => ({ ...prev, [key]: !currentlyCollapsed }));
  };

  const buildCurrentFilterState = (): FilterState => ({
    query: searchQuery(),
    selectedTags: selectedTags(),
    tagMode: tagMode(),
    datePreset: datePreset(),
  });

  const applyFilterState = (state: FilterState) => {
    setSearchQuery(state.query);
    setSelectedTags(state.selectedTags);
    setTagMode(state.tagMode);
    setDatePreset(state.datePreset);
  };

  const loadFilterPreferences = async () => {
    try {
      let nextState: FilterState = {
        query: '',
        selectedTags: [],
        tagMode: 'any',
        datePreset: 'all',
      };
      const res = await fetch('/api/config/preferences');
      if (!res.ok) return;
      const prefs = await res.json();
      const rawState = prefs?.[FILTER_STATE_PREF_KEY];
      if (rawState && typeof rawState === 'object') {
        nextState = {
          query: typeof rawState.query === 'string' ? rawState.query : '',
          selectedTags: Array.isArray(rawState.selectedTags) ? rawState.selectedTags.filter((v: unknown): v is string => typeof v === 'string') : [],
          tagMode: isTagMode(rawState.tagMode) ? rawState.tagMode : 'any',
          datePreset: isDatePreset(rawState.datePreset) ? rawState.datePreset : 'all',
        };
        applyFilterState(nextState);
      }

      const rawPresets = prefs?.[FILTER_PRESETS_PREF_KEY];
      if (Array.isArray(rawPresets)) {
        const parsedPresets = rawPresets
          .filter((p: unknown) => !!p && typeof p === 'object')
          .map((p: any) => ({
            id: typeof p.id === 'string' ? p.id : crypto.randomUUID(),
            name: typeof p.name === 'string' && p.name.trim() ? p.name.trim() : 'Preset',
            query: typeof p.query === 'string' ? p.query : '',
            selectedTags: Array.isArray(p.selectedTags) ? p.selectedTags.filter((v: unknown): v is string => typeof v === 'string') : [],
            tagMode: isTagMode(p.tagMode) ? p.tagMode : 'any',
            datePreset: isDatePreset(p.datePreset) ? p.datePreset : 'all',
          }));
        setSavedPresets(parsedPresets.slice(0, 12));
      }
    } catch (e) {
      console.warn('Failed to load chat history filter preferences', e);
    } finally {
      setPrefsReady(true);
    }
  };

  const persistFilterPreferences = async (state: FilterState, presets: SavedPreset[]) => {
    try {
      await fetch('/api/config/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          [FILTER_STATE_PREF_KEY]: state,
          [FILTER_PRESETS_PREF_KEY]: presets,
        }),
      });
    } catch (e) {
      console.warn('Failed to persist chat history filter preferences', e);
    }
  };

  onMount(() => {
    void loadFilterPreferences();
  });

  let persistTimer: number | null = null;
  createEffect(() => {
    if (!prefsReady()) return;
    const state = buildCurrentFilterState();
    const presets = savedPresets();
    if (persistTimer) {
      window.clearTimeout(persistTimer);
    }
    persistTimer = window.setTimeout(() => {
      void persistFilterPreferences(state, presets);
    }, 350);
  });

  createEffect(() => {
    if (!props.selectedWorkspaceId) {
      setIsResourcesExpanded(false);
      setIsSourcesExpanded(false);
      setIsArtifactsExpanded(false);
      return;
    }

    const shouldExpandSources = props.workspaceSources.length > 0
      && (props.workspaceSourceMode === 'selected'
        || props.workspaceSources.some((source) => source.status !== 'ready'));
    const shouldExpandArtifacts = props.workspaceArtifacts.length > 0 && props.workspaceArtifacts.length <= 2;

    setIsResourcesExpanded((prev) => prev || shouldExpandSources);
    setIsSourcesExpanded((prev) => prev || shouldExpandSources);
    setIsArtifactsExpanded((prev) => prev || shouldExpandArtifacts);
  });

  onCleanup(() => {
    if (persistTimer) window.clearTimeout(persistTimer);
  });

  const activeFilterCount = createMemo(() => {
    let count = 0;
    if (props.selectedWorkspaceId) count += 1;
    if (searchQuery().trim()) count += 1;
    if (selectedTags().length > 0) count += 1;
    if (datePreset() !== 'all') count += 1;
    if (tagMode() !== 'any') count += 1;
    return count;
  });

  const formatChatTime = (iso: string, groupType: string) => {
    const dt = parseServerDate(iso);
    if (groupType === 'today') {
      return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    if (groupType === 'yesterday') {
      return 'Yesterday';
    }
    return dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const selectedWorkspace = createMemo(() =>
    props.workspaces.find((workspace) => workspace.id === props.selectedWorkspaceId) || null
  );

  const handleCreateWorkspace = async () => {
    const name = newWorkspaceName().trim();
    if (!name) return;
    await props.onCreateWorkspace(name);
    setNewWorkspaceName('');
    setShowCreateWorkspace(false);
  };

  const toggleResources = () => setIsResourcesExpanded((prev) => !prev);
  const toggleSources = () => setIsSourcesExpanded((prev) => !prev);
  const toggleArtifacts = () => setIsArtifactsExpanded((prev) => !prev);

  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 left-0 bg-white transform transition-all ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showHistory ? 'translate-x-0 opacity-100 shadow-2xl lg:shadow-none border-r border-slate-200' : '-translate-x-full lg:translate-x-0'}
      `}
      style={{ 
        width: props.showHistory ? `${DEFAULT_WIDTH}px` : '0px',
        "transition-duration": '300ms'
      }}
    >
      <div 
        class="h-full flex flex-col bg-white overflow-hidden transition-opacity duration-300"
        style={{ 
          width: `${DEFAULT_WIDTH}px`,
          opacity: props.showHistory ? 1 : 0,
          "pointer-events": props.showHistory ? 'auto' : 'none'
        }}
      >
        <div class="border-b border-slate-200 bg-slate-50">
          <div class="px-4 py-3 border-b border-slate-200 bg-white/90">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Workspace</div>
                <div class="mt-1 truncate text-sm font-semibold text-slate-800" title={selectedWorkspace()?.name || 'All Workspaces'}>
                  {selectedWorkspace()?.name || 'All Workspaces'}
                </div>
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
              </div>
            </div>
            <div class="mt-2">
              <select
                value={props.selectedWorkspaceId || ''}
                onChange={(e) => props.onSelectWorkspace(e.currentTarget.value || null)}
                class="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-primary/20 outline-none transition-all"
              >
                <option value="">All Workspaces</option>
                <For each={props.workspaces}>
                  {(workspace) => <option value={workspace.id}>{workspace.name}</option>}
                </For>
              </select>
            </div>
            <Show when={showCreateWorkspace()}>
              <div class="mt-2 flex gap-2">
                <input
                  type="text"
                  value={newWorkspaceName()}
                  onInput={(e) => setNewWorkspaceName(e.currentTarget.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      void handleCreateWorkspace();
                    }
                    if (e.key === 'Escape') {
                      setShowCreateWorkspace(false);
                    }
                  }}
                  placeholder="Create workspace"
                  class="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-primary/20 outline-none transition-all"
                />
                <button
                  onClick={() => void handleCreateWorkspace()}
                  class="px-3 py-2 bg-primary text-white rounded-lg text-[11px] font-bold shadow-sm hover:bg-primary-hover transition-colors active:scale-95"
                  title="Create workspace"
                >
                  Add
                </button>
              </div>
            </Show>
          </div>

          <div class="px-4 py-3 border-b border-slate-200 bg-white">
            <div class="flex items-center gap-2">
              <div class="flex-1 relative">
                <input 
                  type="text" 
                  value={searchQuery()}
                  onInput={(e) => setSearchQuery(e.currentTarget.value)}
                  placeholder="Search chats..." 
                  class="w-full bg-white border border-slate-200 rounded-lg px-8 py-2 text-xs focus:ring-2 focus:ring-primary/20 outline-none transition-all shadow-sm" 
                />
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 absolute left-2.5 top-2.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <Show when={searchQuery()}>
                  <button 
                    onClick={() => setSearchQuery('')}
                    class="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 transition-colors"
                    title="Clear search"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </Show>
              </div>
              <button 
                onClick={props.onNewChat} 
                class="bg-primary hover:bg-primary-hover text-white p-2 rounded-lg transition-colors active:scale-95 shadow-sm"
                title="New Chat"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>

            <ChatSidebarResources
              selectedWorkspaceId={props.selectedWorkspaceId}
              workspaceSources={props.workspaceSources}
              workspaceArtifacts={props.workspaceArtifacts}
              workspaceSourceMode={props.workspaceSourceMode}
              selectedWorkspaceSourceIds={props.selectedWorkspaceSourceIds}
              groundingMode={props.groundingMode}
              sourcesLoading={props.sourcesLoading}
              artifactsLoading={props.artifactsLoading}
              isResourcesExpanded={isResourcesExpanded()}
              isSourcesExpanded={isSourcesExpanded()}
              isArtifactsExpanded={isArtifactsExpanded()}
              onToggleResources={toggleResources}
              onToggleSources={toggleSources}
              onToggleArtifacts={toggleArtifacts}
              onWorkspaceSourceModeChange={props.onWorkspaceSourceModeChange}
              onToggleWorkspaceSource={props.onToggleWorkspaceSource}
              onGroundingModeChange={props.onGroundingModeChange}
              onCheckWorkspaceSources={props.onCheckWorkspaceSources}
              onCheckWorkspaceSource={props.onCheckWorkspaceSource}
              onLoadChat={props.onLoadChat}
            />
          </div>
        </div>

        <div class="px-4 py-3 border-b border-slate-100 bg-white flex gap-2 overflow-x-auto no-scrollbar">
          <button
            onClick={() => setDatePreset('all')}
            class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === 'all' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            ALL
          </button>
          <button
            onClick={() => setDatePreset('today')}
            class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === 'today' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            TODAY
          </button>
          <button
            onClick={() => setDatePreset('7d')}
            class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === '7d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            7D
          </button>
          <button
            onClick={() => setDatePreset('30d')}
            class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === '30d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            30D
          </button>
        </div>

        <div class="overflow-y-auto flex-1 no-scrollbar bg-white relative">
          <Show when={props.chats.length > 0 && activeFilterCount() > 0}>
            <div class="px-4 py-2 text-[10px] border-b border-slate-100 bg-slate-50/50 text-slate-500 flex items-center justify-between font-medium">
              <span>
                {filteredChats().length} sessions · {activeFilterCount()} active
              </span>
            </div>
          </Show>
          <For each={groupedChats()}>
            {(group) => (
              <section>
                <button
                  onClick={() => toggleGroup(group.key)}
                  class={`w-full sticky top-0 z-10 px-4 py-2 text-[10px] font-black uppercase tracking-widest border-y flex justify-between items-center ${
                    group.type === 'today' 
                      ? 'text-primary border-primary/10 bg-surface/95 backdrop-blur-sm' 
                      : 'text-slate-500 border-slate-100 bg-slate-50/90 backdrop-blur-sm'
                  }`}
                  aria-expanded={!isGroupCollapsed(group)}
                  aria-label={`Toggle date group ${group.label}`}
                >
                  <span class="flex items-center gap-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class={`w-3 h-3 transition-transform duration-200 ${isGroupCollapsed(group) ? 'rotate-90' : 'rotate-0'}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
                    </svg>
                    {group.label}
                  </span>
                  <span class={`px-1.5 py-0.5 rounded text-[9px] ${
                    group.type === 'today' ? 'bg-primary/10 text-primary' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {group.chats.length} {group.chats.length === 1 ? 'chat' : 'chats'}
                  </span>
                </button>
                <Show when={!isGroupCollapsed(group)}>
                  <div class="divide-y divide-slate-50">
                    <For each={group.chats}>
                      {chat => (
                        <div 
                          class={`px-4 py-3 cursor-pointer group flex justify-between items-start transition-colors relative border-l-4 ${
                            props.currentChatId === chat.id 
                              ? 'bg-primary/5 border-l-primary' 
                              : 'bg-white border-l-transparent hover:bg-slate-50'
                          }`}
                          onClick={() => props.onLoadChat(chat.id)}
                        >
                          <div class="flex-1 min-w-0">
                            <div class="flex justify-between items-start mb-1">
                              <h3 class={`text-sm truncate pr-2 transition-colors ${
                                props.currentChatId === chat.id ? 'font-bold text-slate-800' : 'font-semibold text-slate-700 group-hover:text-primary'
                              }`}>
                                {chat.title}
                              </h3>
                              <span class="text-[9px] text-slate-400 font-medium whitespace-nowrap shrink-0 pt-0.5">
                                {formatChatTime(chat.updated_at, group.type)}
                              </span>
                            </div>
                            
                            <Show when={chat.summary}>
                              <div class="text-[11px] text-slate-500 line-clamp-1 mb-2">
                                {chat.summary}
                              </div>
                            </Show>
                            
                            <div class="flex flex-wrap gap-1 items-center">
                              <Show when={chat.workspace_id && !props.selectedWorkspaceId}>
                                <span class="px-1.5 py-0.5 text-[9px] font-semibold rounded uppercase tracking-tighter bg-amber-50 text-amber-700 border border-amber-200/70">
                                  workspace
                                </span>
                              </Show>
                              <Show when={chat.tags && chat.tags.length > 0}>
                                <For each={(chat.tags || []).slice(0, 3)}>
                                  {(tag) => (
                                    <span class={`px-1.5 py-0.5 text-[9px] font-semibold rounded uppercase tracking-tighter bg-slate-100 text-slate-500 border border-slate-200/60`}>
                                      {tag}
                                    </span>
                                  )}
                                </For>
                              </Show>
                              <Show when={chat.tags && chat.tags.length > 3}>
                                <span class="px-1.5 py-0.5 bg-slate-100 text-slate-400 border border-slate-200/60 text-[9px] font-semibold rounded">
                                  +{chat.tags!.length - 3}
                                </span>
                              </Show>
                            </div>
                          </div>
                          
                          <div class="absolute right-2 bottom-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                props.onGenerateSummary(chat.id);
                              }}
                              class="p-1.5 bg-white text-slate-400 hover:text-primary rounded shadow-sm border border-slate-200"
                              title="Generate summary"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8M8 14h5M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3V8a2 2 0 012-2z" />
                              </svg>
                            </button>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                props.onDeleteChat(chat.id);
                              }}
                              class="p-1.5 bg-white text-slate-400 hover:text-rose-500 rounded shadow-sm border border-slate-200"
                              title="Delete session"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      )}
                    </For>
                  </div>
                </Show>
              </section>
            )}
          </For>
          <Show when={props.chats.length > 0 && filteredChats().length === 0}>
             <div class="p-8 text-center">
                <p class="text-sm text-slate-400 italic mb-3">No chats match your current filters</p>
                <button 
                  onClick={clearFilters}
                  class="text-xs text-primary font-bold hover:underline active:scale-95 transition-transform inline-block"
                >
                  Clear all filters
                </button>
             </div>
          </Show>
          <Show when={props.chats.length === 0}>
             <div class="p-8 text-center text-sm text-slate-400 italic">No recent chats</div>
          </Show>
        </div>
        <div class="p-3 bg-slate-50 border-t border-slate-200 text-center">
          <span class="text-[10px] text-slate-400 font-medium italic">Showing {filteredChats().length} sessions</span>
        </div>
      </div>
      
      {/* Toggle Handle - Fixed width mode, no resize */}
      <div
        class={`absolute top-0 -right-2 w-4 h-full z-50 group hidden lg:block select-none`}
      >
        {/* The interactive handle strip */}
        <div 
          class={`absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 w-1.5 h-24 rounded-full transition-all duration-300 flex items-center justify-center
            bg-slate-200/50 group-hover:bg-primary/40 group-hover:h-32 group-hover:w-2`}
        >
          {/* Action Button (Click to toggle) */}
          <div 
            onClick={(e) => {
              e.stopPropagation();
              props.setShowHistory(!props.showHistory);
            }}
            class="absolute inset-0 cursor-pointer flex items-center justify-center"
            title={props.showHistory ? "Collapse" : "Expand"}
          >
            <div class={`w-5 h-10 bg-white border border-slate-200 rounded-full shadow-md flex items-center justify-center transition-all duration-300 transform 
              ${props.showHistory ? 'opacity-0 group-hover:opacity-100 rotate-0' : 'opacity-100 rotate-180 translate-x-1.5'}`}>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-primary font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" d="M15 19l-7-7 7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
