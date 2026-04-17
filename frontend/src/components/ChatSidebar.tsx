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
  onCleanup(() => {
    if (persistTimer) window.clearTimeout(persistTimer);
  });

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
        <div class="p-4 bg-slate-50/80 border-b border-border flex items-center gap-2 sticky top-0 z-20 backdrop-blur-md">
          <div class="flex-1 relative">
            <input 
              type="text" 
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
              placeholder="Search chats..." 
              class="w-full bg-white border border-border rounded-lg pl-9 pr-3 py-2 text-xs focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all shadow-sm" 
            />
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 absolute left-3 top-2.5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button 
            onClick={props.onNewChat} 
            class="bg-primary hover:bg-primary-dark text-white p-2.5 rounded-lg transition-all active:scale-95 shadow-sm shadow-primary/20"
            title="New Chat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>

        <div class="px-4 py-3 border-b border-border bg-white flex gap-2 overflow-x-auto no-scrollbar scroll-smooth">
          <button
            onClick={() => setDatePreset('all')}
            class={`px-2.5 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === 'all' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            ALL
          </button>
          <button
            onClick={() => setDatePreset('today')}
            class={`px-2.5 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === 'today' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            TODAY
          </button>
          <button
            onClick={() => setDatePreset('7d')}
            class={`px-2.5 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === '7d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            7D
          </button>
          <button
            onClick={() => setDatePreset('30d')}
            class={`px-2.5 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${
              datePreset() === '30d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            30D
          </button>
          <Show when={activeFilterCount() > 0}>
            <button 
              onClick={clearFilters} 
              class="px-2.5 py-1 text-[10px] font-bold rounded bg-rose-50 text-rose-600 hover:bg-rose-100 transition-all whitespace-nowrap border border-rose-100"
            >
              CLEAR
            </button>
          </Show>
        </div>

        <div class="overflow-y-auto flex-1 no-scrollbar scroll-smooth pb-20">
          <Show when={props.chats.length > 0}>
            <div class="px-4 py-2 text-[10px] border-b border-border bg-slate-50/30 text-text-secondary flex items-center justify-between font-medium">
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
                  class={`w-full px-4 py-2 sticky top-0 z-10 text-left flex items-center justify-between border-b transition-colors backdrop-blur-md ${
                    group.isToday 
                      ? 'bg-blue-50/90 border-blue-100 text-blue-600' 
                      : 'bg-slate-50/90 border-slate-100 text-slate-500'
                  }`}
                  aria-expanded={!(collapsedGroups()[group.key] ?? !group.isToday)}
                  aria-label={`Toggle date group ${group.label}`}
                >
                  <span class="text-[10px] font-black uppercase tracking-[0.15em] flex items-center gap-2">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class={`w-3 h-3 transition-transform duration-300 ${(collapsedGroups()[group.key] ?? !group.isToday) ? 'rotate-0' : 'rotate-90'}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
                    </svg>
                    {group.isToday ? 'Today' : group.label}
                  </span>
                  <span class={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                    group.isToday ? 'bg-blue-100 text-blue-700' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {group.chats.length}
                  </span>
                </button>
                <Show when={!(collapsedGroups()[group.key] ?? !group.isToday)}>
                  <div class="divide-y divide-slate-50">
                    <For each={group.chats}>
                      {chat => (
                        <div 
                          class={`px-4 py-3 cursor-pointer group flex justify-between items-start transition-all border-l-2 ${
                            props.currentChatId === chat.id 
                              ? 'bg-blue-50/40 border-l-blue-500' 
                              : 'bg-white border-l-transparent hover:bg-slate-50/80 hover:border-l-slate-200'
                          }`}
                          onClick={() => props.onLoadChat(chat.id)}
                        >
                          <div class="flex-1 min-w-0">
                            <div class="flex justify-between items-start mb-0.5">
                              <h3 class={`text-sm truncate pr-2 ${
                                props.currentChatId === chat.id ? 'font-bold text-slate-900' : 'font-semibold text-slate-700 group-hover:text-blue-600'
                              }`}>
                                {chat.title}
                              </h3>
                              <span class="text-[9px] text-slate-400 font-medium whitespace-nowrap pt-0.5">
                                {parseServerDate(chat.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            
                            <Show when={chat.summary}>
                              <p class="text-[11px] text-slate-500 line-clamp-2 leading-relaxed mb-2">
                                {chat.summary}
                              </p>
                            </Show>
                            
                            <div class="flex flex-wrap gap-1 items-center">
                              <Show when={chat.tags && chat.tags.length > 0}>
                                <For each={(chat.tags || []).slice(0, 3)}>
                                  {(tag) => (
                                    <span class="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[9px] font-bold rounded uppercase tracking-tighter group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                                      {tag}
                                    </span>
                                  )}
                                </For>
                              </Show>
                              <Show when={chat.tags && chat.tags.length > 3}>
                                <span class="text-[9px] text-slate-400 font-bold">+{chat.tags!.length - 3}</span>
                              </Show>
                            </div>
                          </div>
                          
                          <div class="flex flex-col gap-1 ml-2 translate-x-2 opacity-0 group-hover:translate-x-0 group-hover:opacity-100 transition-all duration-200">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                props.onGenerateSummary(chat.id);
                              }}
                              class="text-slate-400 hover:text-blue-600 p-1 bg-white shadow-sm border border-slate-100 rounded-md transition-colors"
                              title="Generate summary"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8M8 14h5M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3V8a2 2 0 012-2z" />
                              </svg>
                            </button>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                props.onDeleteChat(chat.id);
                              }}
                              class="text-slate-400 hover:text-red-500 p-1 bg-white shadow-sm border border-slate-100 rounded-md transition-colors"
                              title="Delete session"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
