import { createEffect, createMemo, createSignal, onCleanup, onMount } from 'solid-js';
import type { ChatSidebarProps, FilterState, SavedPreset } from './types';
import {
  buildCurrentFilterState,
  buildFilteredChats,
  buildGroupedChats,
  FILTER_PRESETS_PREF_KEY,
  FILTER_STATE_PREF_KEY,
  getActiveFilterCount,
  parseFilterState,
  parseSavedPresets,
} from './sidebarFilters';

export function useChatSidebarState(props: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = createSignal('');
  const [selectedTags, setSelectedTags] = createSignal<string[]>([]);
  const [tagMode, setTagMode] = createSignal<'any' | 'all'>('any');
  const [datePreset, setDatePreset] = createSignal<'all' | 'today' | '7d' | '30d'>('all');
  const [collapsedGroups, setCollapsedGroups] = createSignal<Record<string, boolean>>({});
  const [savedPresets, setSavedPresets] = createSignal<SavedPreset[]>([]);
  const [prefsReady, setPrefsReady] = createSignal(false);

  const filters = createMemo<FilterState>(() =>
    buildCurrentFilterState(searchQuery(), selectedTags(), tagMode(), datePreset()),
  );
  const filteredChats = createMemo(() => buildFilteredChats(props.chats, props.selectedWorkspaceId, filters()));
  const groupedChats = createMemo(() => buildGroupedChats(filteredChats()));
  const activeFilterCount = createMemo(() => getActiveFilterCount(props.selectedWorkspaceId, filters()));

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedTags([]);
    setTagMode('any');
    setDatePreset('all');
  };

  const isGroupCollapsed = (group: { key: string; chats: { id: string }[] }) => {
    const manualState = collapsedGroups()[group.key];
    if (manualState !== undefined) return manualState;
    if (props.currentChatId && group.chats.some((chat) => chat.id === props.currentChatId)) return false;
    return group.key !== 'today' && group.key !== 'yesterday';
  };

  const toggleGroup = (key: string) => {
    const group = groupedChats().find((item) => item.key === key);
    if (!group) return;
    const currentlyCollapsed = isGroupCollapsed(group);
    setCollapsedGroups((prev) => ({ ...prev, [key]: !currentlyCollapsed }));
  };

  const applyFilterState = (state: FilterState) => {
    setSearchQuery(state.query);
    setSelectedTags(state.selectedTags);
    setTagMode(state.tagMode);
    setDatePreset(state.datePreset);
  };

  const loadFilterPreferences = async () => {
    try {
      const res = await fetch('/api/config/preferences');
      if (!res.ok) return;
      const prefs = await res.json();
      applyFilterState(parseFilterState(prefs?.[FILTER_STATE_PREF_KEY]));
      setSavedPresets(parseSavedPresets(prefs?.[FILTER_PRESETS_PREF_KEY]));
    } catch (error) {
      console.warn('Failed to load chat history filter preferences', error);
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
    } catch (error) {
      console.warn('Failed to persist chat history filter preferences', error);
    }
  };

  onMount(() => {
    void loadFilterPreferences();
  });

  let persistTimer: number | null = null;
  createEffect(() => {
    if (!prefsReady()) return;
    const state = filters();
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

  return {
    searchQuery,
    setSearchQuery,
    selectedTags,
    setSelectedTags,
    tagMode,
    setTagMode,
    datePreset,
    setDatePreset,
    groupedChats,
    filteredChats,
    activeFilterCount,
    clearFilters,
    isGroupCollapsed,
    toggleGroup,
  };
}
