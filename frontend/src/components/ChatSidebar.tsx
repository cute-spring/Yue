import { For, Show, createEffect, createMemo, createSignal, onCleanup, onMount } from 'solid-js';
import { ChatSession } from '../types';

interface ChatSidebarProps {
  showHistory: boolean;
  chats: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
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

export default function ChatSidebar(props: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = createSignal('');
  const [selectedTags, setSelectedTags] = createSignal<string[]>([]);
  const [tagMode, setTagMode] = createSignal<'any' | 'all'>('any');
  const [datePreset, setDatePreset] = createSignal<'all' | 'today' | '7d' | '30d'>('all');
  const [collapsedGroups, setCollapsedGroups] = createSignal<Record<string, boolean>>({});
  const [savedPresets, setSavedPresets] = createSignal<SavedPreset[]>([]);
  const [prefsReady, setPrefsReady] = createSignal(false);
  const [filtersCollapsed, setFiltersCollapsed] = createSignal(true);
  const [showAllAvailableTags, setShowAllAvailableTags] = createSignal(false);

  const availableTags = createMemo(() => {
    const counts = new Map<string, number>();
    for (const chat of props.chats) {
      for (const tag of chat.tags || []) {
        counts.set(tag, (counts.get(tag) || 0) + 1);
      }
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([tag]) => tag)
      .slice(0, 12);
  });
  const visibleAvailableTags = createMemo(() =>
    showAllAvailableTags() ? availableTags() : availableTags().slice(0, 6)
  );

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

    return props.chats.filter((chat) => {
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
    const groups = new Map<string, { label: string; isToday: boolean; chats: ChatSession[]; sortDate: number }>();
    const now = new Date();
    const todayKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;

    for (const chat of filteredChats()) {
      const dt = parseServerDate(chat.updated_at);
      const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
      const isToday = key === todayKey;
      if (!groups.has(key)) {
        groups.set(key, {
          label: dt.toLocaleDateString(),
          isToday,
          chats: [],
          sortDate: new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()).getTime(),
        });
      }
      groups.get(key)!.chats.push(chat);
    }

    return [...groups.entries()]
      .sort((a, b) => b[1].sortDate - a[1].sortDate)
      .map(([key, value]) => ({ key, ...value }));
  });

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedTags([]);
    setTagMode('any');
    setDatePreset('all');
  };

  const toggleGroup = (key: string) => {
    const group = groupedChats().find(g => g.key === key);
    const defaultCollapsed = group ? !group.isToday : false;
    setCollapsedGroups(prev => {
      const current = prev[key] ?? defaultCollapsed;
      return { ...prev, [key]: !current };
    });
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

  const hasActiveFilters = (state: FilterState) =>
    Boolean(state.query.trim()) ||
    state.selectedTags.length > 0 ||
    state.tagMode !== 'any' ||
    state.datePreset !== 'all';

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
      // Filters should start collapsed by default; only auto-expand when a saved filter is active.
      setFiltersCollapsed(!hasActiveFilters(nextState));
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
  onCleanup(() => {
    if (persistTimer) window.clearTimeout(persistTimer);
  });

  const saveCurrentPreset = () => {
    const defaultName = `Preset ${savedPresets().length + 1}`;
    const name = window.prompt('Preset name', defaultName)?.trim();
    if (!name) return;
    const nextPreset: SavedPreset = {
      id: crypto.randomUUID(),
      name,
      ...buildCurrentFilterState(),
    };
    setSavedPresets(prev => [nextPreset, ...prev].slice(0, 12));
  };

  const applySavedPreset = (preset: SavedPreset) => {
    applyFilterState({
      query: preset.query,
      selectedTags: preset.selectedTags,
      tagMode: preset.tagMode,
      datePreset: preset.datePreset,
    });
  };

  const deleteSavedPreset = (id: string) => {
    setSavedPresets(prev => prev.filter(p => p.id !== id));
  };

  const activeFilterCount = createMemo(() => {
    let count = 0;
    if (searchQuery().trim()) count += 1;
    if (selectedTags().length > 0) count += 1;
    if (datePreset() !== 'all') count += 1;
    if (tagMode() !== 'any') count += 1;
    return count;
  });

  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 left-0 bg-surface border-r border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showHistory ? 'translate-x-0 w-sidebar opacity-100' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
      `}
    >
      <div class="w-sidebar h-full flex flex-col">
        <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
          <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
            <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            Chat History
          </h2>
          <button 
            onClick={props.onNewChat} 
            class="group relative p-2 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-xl transition-all duration-300 active:scale-90 shadow-sm hover:shadow-primary/20"
            title="New Chat Session"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <div class="px-4 py-2 border-b border-border bg-surface/70">
          <button
            onClick={() => setFiltersCollapsed(v => !v)}
            class="w-full flex items-center justify-between text-left py-1.5 px-1 rounded hover:bg-primary/5 transition-colors"
            aria-expanded={!filtersCollapsed()}
            aria-label={filtersCollapsed() ? 'Expand filters panel' : 'Collapse filters panel'}
          >
            <span class="text-[11px] uppercase tracking-[0.12em] font-semibold text-text-secondary">
              Filters
            </span>
            <span class="text-text-secondary">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`w-4 h-4 transition-transform duration-200 ${filtersCollapsed() ? 'rotate-0' : 'rotate-90'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M9 6l6 6-6 6" />
              </svg>
            </span>
          </button>
          <Show when={!filtersCollapsed()}>
          <div class="space-y-2">
          <input
            value={searchQuery()}
            onInput={(e) => setSearchQuery(e.currentTarget.value)}
            class="w-full text-sm rounded-lg border border-border bg-surface px-3 py-2 outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            placeholder="Search title, summary, tags..."
          />
          <div class="flex items-center gap-1.5">
            <button
              onClick={() => setDatePreset('all')}
              class={`text-[10px] px-2 py-1 rounded ${datePreset() === 'all' ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}`}
            >
              All
            </button>
            <button
              onClick={() => setDatePreset('today')}
              class={`text-[10px] px-2 py-1 rounded ${datePreset() === 'today' ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}`}
            >
              Today
            </button>
            <button
              onClick={() => setDatePreset('7d')}
              class={`text-[10px] px-2 py-1 rounded ${datePreset() === '7d' ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}`}
            >
              7d
            </button>
            <button
              onClick={() => setDatePreset('30d')}
              class={`text-[10px] px-2 py-1 rounded ${datePreset() === '30d' ? 'bg-primary text-white' : 'bg-primary/10 text-primary'}`}
            >
              30d
            </button>
          </div>
          <Show when={selectedTags().length > 0}>
            <div class="flex flex-wrap gap-1.5">
              <For each={selectedTags()}>
                {(tag) => (
                  <button
                    onClick={() => toggleTag(tag)}
                    class="text-[10px] px-2 py-1 rounded bg-primary text-white hover:bg-primary/90"
                    title={`Remove #${tag}`}
                  >
                    #{tag} ×
                  </button>
                )}
              </For>
            </div>
          </Show>
          <Show when={availableTags().length > 0}>
            <div class="flex flex-wrap gap-1.5">
              <For each={visibleAvailableTags()}>
                {(tag) => (
                  <button
                    onClick={() => toggleTag(tag)}
                    class={`text-[10px] px-2 py-1 rounded transition-colors ${
                      selectedTags().includes(tag) ? 'hidden' : 'bg-primary/10 text-primary hover:bg-primary/20'
                    }`}
                    aria-pressed={selectedTags().includes(tag)}
                  >
                    #{tag}
                  </button>
                )}
              </For>
              <Show when={availableTags().length > 6}>
                <button
                  onClick={() => setShowAllAvailableTags(v => !v)}
                  class="text-[10px] px-2 py-1 rounded border border-border text-text-secondary hover:text-primary hover:border-primary/30"
                >
                  {showAllAvailableTags() ? 'Collapse' : `+More (${availableTags().length - 6})`}
                </button>
              </Show>
            </div>
          </Show>
          <div class="flex items-center justify-between">
            <button
              onClick={() => setTagMode(tagMode() === 'any' ? 'all' : 'any')}
              class="text-[10px] px-2 py-1 rounded bg-surface border border-border text-text-secondary hover:text-primary"
              title="Toggle tag matching mode"
            >
              Tag mode: {tagMode().toUpperCase()}
            </button>
            <Show when={searchQuery() || selectedTags().length > 0 || datePreset() !== 'all'}>
              <button onClick={clearFilters} class="text-[10px] text-primary hover:underline">
                Clear
              </button>
            </Show>
          </div>
          <div class="flex items-center justify-between gap-2">
            <span class="text-[10px] uppercase tracking-[0.1em] text-text-secondary">Presets</span>
            <button
              onClick={saveCurrentPreset}
              class="text-[10px] px-2 py-1 rounded border border-border text-text-secondary hover:text-primary hover:border-primary/30"
            >
              Save Current
            </button>
          </div>
          <Show when={savedPresets().length > 0}>
            <div class="space-y-1 max-h-24 overflow-y-auto pr-1">
              <For each={savedPresets()}>
                {(preset) => (
                  <div class="flex items-center justify-between gap-1 rounded border border-border px-2 py-1">
                    <button
                      onClick={() => applySavedPreset(preset)}
                      class="text-[10px] text-text-primary hover:text-primary truncate text-left flex-1"
                      title={`Apply preset: ${preset.name}`}
                    >
                      {preset.name}
                    </button>
                    <button
                      onClick={() => deleteSavedPreset(preset.id)}
                      class="text-[10px] text-text-secondary hover:text-red-500"
                      aria-label={`Delete preset ${preset.name}`}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </For>
            </div>
          </Show>
          </div>
          </Show>
        </div>
        <div class="overflow-y-auto flex-1 pb-20 scrollbar-thin scrollbar-thumb-border">
          <Show when={props.chats.length > 0}>
            <div class="px-3 py-1.5 text-[10px] border-b border-border bg-surface/60 text-text-secondary flex items-center justify-between">
              <span>
                {filteredChats().length} chats · filters: {activeFilterCount()} · {datePreset().toUpperCase()}
              </span>
              <Show when={activeFilterCount() > 0}>
                <button onClick={clearFilters} class="text-primary hover:underline">Clear</button>
              </Show>
            </div>
          </Show>
          <For each={groupedChats()}>
            {(group) => (
              <section>
                <button
                  onClick={() => toggleGroup(group.key)}
                  class="w-full px-3 py-2 sticky top-0 z-[1] bg-background/95 backdrop-blur text-left flex items-center justify-between border-b border-border hover:bg-primary/5 active:bg-primary/10 transition-colors"
                  aria-expanded={!(collapsedGroups()[group.key] ?? !group.isToday)}
                  aria-label={`Toggle date group ${group.label}`}
                >
                  <span class="text-[10px] uppercase tracking-[0.12em] font-semibold text-text-secondary flex items-center gap-1.5">
                    <span class="text-text-secondary">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        class={`w-3.5 h-3.5 transition-transform duration-200 ${(collapsedGroups()[group.key] ?? !group.isToday) ? 'rotate-0' : 'rotate-90'}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.2" d="M9 6l6 6-6 6" />
                      </svg>
                    </span>
                    {group.label} ({group.chats.length})
                  </span>
                </button>
                <Show when={!(collapsedGroups()[group.key] ?? !group.isToday)}>
                  <For each={group.chats}>
                    {chat => (
                      <div 
                        class={`px-3 py-2 border-b border-border cursor-pointer hover:bg-primary/5 group flex justify-between items-start transition-colors ${
                          props.currentChatId === chat.id ? 'bg-primary/10 border-l-4 border-l-primary' : 'border-l-4 border-l-transparent'
                        }`}
                        onClick={() => props.onLoadChat(chat.id)}
                      >
                        <div class="flex-1 min-w-0">
                          <h3 class={`text-sm font-medium truncate ${props.currentChatId === chat.id ? 'text-primary' : 'text-text-primary'}`}>{chat.title}</h3>
                          <Show when={chat.summary}>
                            <p class="text-[10px] text-text-secondary mt-1 line-clamp-2">{chat.summary}</p>
                          </Show>
                          <Show when={chat.tags && chat.tags.length > 0}>
                            <div class="mt-1 flex flex-wrap gap-1">
                              <For each={(chat.tags || []).slice(0, 3)}>
                                {(tag) => (
                                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                                    #{tag}
                                  </span>
                                )}
                              </For>
                            </div>
                          </Show>
                          <p class="text-[10px] text-text-secondary mt-1">{parseServerDate(chat.updated_at).toLocaleDateString()}</p>
                        </div>
                        <div class="flex items-start gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onGenerateSummary(chat.id);
                            }}
                            class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-primary p-1 transition-all"
                            title="Generate summary"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8M8 14h5M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3V8a2 2 0 012-2z" />
                            </svg>
                          </button>
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onDeleteChat(chat.id);
                            }}
                            class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 transition-all"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )}
                  </For>
                </Show>
              </section>
            )}
          </For>
          <Show when={filteredChats().length === 0}>
             <div class="p-8 text-center text-sm text-text-secondary italic">No chats match your current filters</div>
          </Show>
          <Show when={props.chats.length === 0}>
             <div class="p-8 text-center text-sm text-text-secondary italic">No recent chats</div>
          </Show>
        </div>
      </div>
    </div>
  );
}
