import type { ChatSession } from '../../types';
import { filterChatsByWorkspace, formatWorkspaceCountLabel, getWorkspaceSourceReadinessCounts } from '../ChatSidebar.helpers';
import type { ChatSidebarGroup, DatePreset, FilterState, SavedPreset, TagMode } from './types';

export const FILTER_STATE_PREF_KEY = 'chat_history_filter_state';
export const FILTER_PRESETS_PREF_KEY = 'chat_history_filter_presets';
export const DEFAULT_WIDTH = 260;

export const isDatePreset = (value: unknown): value is DatePreset =>
  value === 'all' || value === 'today' || value === '7d' || value === '30d';

export const isTagMode = (value: unknown): value is TagMode => value === 'any' || value === 'all';

export const parseServerDate = (value: string): Date => {
  const trimmed = String(value || '').trim();
  if (!trimmed) return new Date(NaN);
  if (/[zZ]$|[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return new Date(trimmed);
  }
  return new Date(`${trimmed}Z`);
};

export const matchesDatePreset = (iso: string, preset: DatePreset) => {
  if (preset === 'all') return true;
  const date = parseServerDate(iso);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (preset === 'today') return date >= startOfToday;
  const days = preset === '7d' ? 7 : 30;
  const threshold = new Date(startOfToday);
  threshold.setDate(threshold.getDate() - (days - 1));
  return date >= threshold;
};

export const buildFilteredChats = (
  chats: ChatSession[],
  selectedWorkspaceId: string | null,
  filters: FilterState,
): ChatSession[] => {
  const query = filters.query.trim().toLowerCase();
  const tags = filters.selectedTags;
  const mode = filters.tagMode;
  return filterChatsByWorkspace(chats, selectedWorkspaceId).filter((chat) => {
    if (!matchesDatePreset(chat.updated_at, filters.datePreset)) return false;
    if (query) {
      const haystack = `${chat.title} ${chat.summary || ''} ${(chat.tags || []).join(' ')}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    if (tags.length > 0) {
      const chatTags = chat.tags || [];
      if (mode === 'all') {
        if (!tags.every((tag) => chatTags.includes(tag))) return false;
      } else if (!tags.some((tag) => chatTags.includes(tag))) {
        return false;
      }
    }
    return true;
  });
};

export const buildGroupedChats = (filteredChats: ChatSession[]): ChatSidebarGroup[] => {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfLast7Days = new Date(startOfToday);
  startOfLast7Days.setDate(startOfLast7Days.getDate() - 7);

  const groups: ChatSidebarGroup[] = [
    { key: 'today', label: 'Today', type: 'today', isToday: true, chats: [] },
    { key: 'yesterday', label: 'Yesterday', type: 'yesterday', isToday: false, chats: [] },
    { key: 'last7days', label: 'Last 7 Days', type: 'last7days', isToday: false, chats: [] },
    { key: 'earlier', label: 'Earlier', type: 'earlier', isToday: false, chats: [] },
  ];

  for (const chat of filteredChats) {
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

  return groups.filter((group) => group.chats.length > 0);
};

export const buildCurrentFilterState = (
  query: string,
  selectedTags: string[],
  tagMode: TagMode,
  datePreset: DatePreset,
): FilterState => ({
  query,
  selectedTags,
  tagMode,
  datePreset,
});

export const getActiveFilterCount = (selectedWorkspaceId: string | null, filters: FilterState): number => {
  let count = 0;
  if (selectedWorkspaceId) count += 1;
  if (filters.query.trim()) count += 1;
  if (filters.selectedTags.length > 0) count += 1;
  if (filters.datePreset !== 'all') count += 1;
  if (filters.tagMode !== 'any') count += 1;
  return count;
};

export const formatChatTime = (iso: string, groupType: string) => {
  const dt = parseServerDate(iso);
  if (groupType === 'today') {
    return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  if (groupType === 'yesterday') {
    return 'Yesterday';
  }
  return dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

export const parseSavedPresets = (rawPresets: unknown): SavedPreset[] => {
  if (!Array.isArray(rawPresets)) return [];
  return rawPresets
    .filter((preset: unknown) => !!preset && typeof preset === 'object')
    .map((preset: any) => ({
      id: typeof preset.id === 'string' ? preset.id : crypto.randomUUID(),
      name: typeof preset.name === 'string' && preset.name.trim() ? preset.name.trim() : 'Preset',
      query: typeof preset.query === 'string' ? preset.query : '',
      selectedTags: Array.isArray(preset.selectedTags)
        ? preset.selectedTags.filter((value: unknown): value is string => typeof value === 'string')
        : [],
      tagMode: isTagMode(preset.tagMode) ? preset.tagMode : 'any',
      datePreset: isDatePreset(preset.datePreset) ? preset.datePreset : 'all',
    }))
    .slice(0, 12);
};

export const parseFilterState = (rawState: unknown): FilterState => ({
  query: typeof (rawState as any)?.query === 'string' ? (rawState as any).query : '',
  selectedTags: Array.isArray((rawState as any)?.selectedTags)
    ? (rawState as any).selectedTags.filter((value: unknown): value is string => typeof value === 'string')
    : [],
  tagMode: isTagMode((rawState as any)?.tagMode) ? (rawState as any).tagMode : 'any',
  datePreset: isDatePreset((rawState as any)?.datePreset) ? (rawState as any).datePreset : 'all',
});

export { formatWorkspaceCountLabel, getWorkspaceSourceReadinessCounts };
