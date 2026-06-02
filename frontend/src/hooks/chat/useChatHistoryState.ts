import type { Accessor } from 'solid-js';
import type { ActionState, ChatEventEnvelope, ChatSession, Message } from '../../types';
import { buildActionStatesFromEvents, buildToolCallsFromEvents, normalizeStreamEvent } from './chatStream';

type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

export type HistoryFilters = {
  tags?: string[];
  tagMode?: 'any' | 'all';
  dateFrom?: string;
  dateTo?: string;
};

type ToastLike = {
  success: (message: string) => void;
  error: (message: string) => void;
};

type UseChatHistoryStateOptions = {
  chats: Accessor<ChatSession[]>;
  setChats: Setter<ChatSession[]>;
  currentChatId: Accessor<string | null>;
  setCurrentChatId: Setter<string | null>;
  messages: Accessor<Message[]>;
  setMessages: Setter<Message[]>;
  setActionStates: Setter<ActionState[]>;
  setInput: Setter<string>;
  setActiveSkill: Setter<{ name: string; version: string } | null>;
  isTyping: Accessor<boolean>;
  stopGeneration: () => void;
  toast: ToastLike;
};

export function createChatHistoryState(options: UseChatHistoryStateOptions) {
  let metaRefreshTimers: number[] = [];
  let historyFetchInFlight: Promise<void> | null = null;
  let lastHistoryFetchAt = 0;
  const historyFetchMinIntervalMs = 800;

  const shouldSkipHistoryFetch = (now: number): boolean => {
    if (lastHistoryFetchAt <= 0) return false;
    return now - lastHistoryFetchAt < historyFetchMinIntervalMs;
  };

  const loadHistory = async (force = false, filters?: HistoryFilters) => {
    if (historyFetchInFlight) {
      await historyFetchInFlight;
      return;
    }
    const now = Date.now();
    if (!force && shouldSkipHistoryFetch(now)) return;
    historyFetchInFlight = (async () => {
      try {
        const params = new URLSearchParams();
        if (filters?.tags?.length) params.set('tags', filters.tags.join(','));
        if (filters?.tagMode) params.set('tag_mode', filters.tagMode);
        if (filters?.dateFrom) params.set('date_from', filters.dateFrom);
        if (filters?.dateTo) params.set('date_to', filters.dateTo);
        const query = params.toString();
        const res = await fetch(query ? `/api/chat/history?${query}` : '/api/chat/history');
        options.setChats(await res.json());
        lastHistoryFetchAt = Date.now();
      } catch (error) {
        console.error('Failed to load history', error);
        options.toast.error('Failed to load chat history');
      } finally {
        historyFetchInFlight = null;
      }
    })();
    await historyFetchInFlight;
  };

  const clearMetaRefreshTimers = () => {
    for (const timer of metaRefreshTimers) clearTimeout(timer);
    metaRefreshTimers = [];
  };

  const refreshChatMeta = async (chatId: string): Promise<boolean> => {
    try {
      const res = await fetch(`/api/chat/${chatId}/meta`);
      if (!res.ok) return false;
      const meta = await res.json();
      let titleChanged = false;
      options.setChats((prev) => {
        const idx = prev.findIndex((chat) => chat.id === chatId);
        if (idx === -1) {
          return [{ id: meta.id, title: meta.title, summary: meta.summary, updated_at: meta.updated_at }, ...prev];
        }
        const current = prev[idx];
        if (current.title !== meta.title) titleChanged = true;
        if (current.title === meta.title && current.summary === meta.summary && current.updated_at === meta.updated_at) {
          return prev;
        }
        const next = [...prev];
        next[idx] = { ...current, title: meta.title, summary: meta.summary, updated_at: meta.updated_at };
        return next;
      });
      return titleChanged;
    } catch (error) {
      console.warn('Failed to refresh chat meta', error);
      return false;
    }
  };

  const scheduleMetaRefreshForTitle = (chatId: string) => {
    clearMetaRefreshTimers();
    for (const delay of [1200, 3000]) {
      const timer = window.setTimeout(async () => {
        const changed = await refreshChatMeta(chatId);
        if (changed) clearMetaRefreshTimers();
      }, delay);
      metaRefreshTimers.push(timer);
    }
  };

  const loadChat = async (
    id: string,
    isMobile: boolean,
    setShowHistory: (value: boolean) => void,
    setSelectedAgent: (value: string | null) => void,
    setSelectedWorkspaceId?: (value: string | null) => void,
  ) => {
    if (options.isTyping()) options.stopGeneration();
    try {
      const res = await fetch(`/api/chat/${id}`);
      const data = await res.json();
      let mergedMessages: Message[] = data.messages || [];
      let replayActionStates: ActionState[] = [];
      try {
        const eventsResp = await fetch(`/api/chat/${id}/events`);
        if (eventsResp.ok) {
          const replayEventsRaw = await eventsResp.json();
          if (Array.isArray(replayEventsRaw) && replayEventsRaw.length > 0) {
            const replayEvents = replayEventsRaw.map(normalizeStreamEvent);
            replayActionStates = buildActionStatesFromEvents(replayEvents);
            const eventsByTurn = new Map<string, ChatEventEnvelope[]>();
            const metaByTurn = new Map<string, Record<string, any>>();
            for (const event of replayEvents) {
              const turnId = typeof event.assistant_turn_id === 'string' ? event.assistant_turn_id : '';
              if (!turnId) continue;
              const bucket = eventsByTurn.get(turnId) || [];
              bucket.push(event);
              eventsByTurn.set(turnId, bucket);
              if (event.meta && typeof event.meta === 'object') {
                metaByTurn.set(turnId, event.meta as Record<string, any>);
              }
            }
            mergedMessages = mergedMessages.map((message) => {
              if (message.role !== 'assistant') return message;
              const turnId = message.assistant_turn_id;
              if (!turnId) return message;
              const toolCalls = buildToolCallsFromEvents(eventsByTurn.get(turnId) || []);
              const meta = metaByTurn.get(turnId) || {};
              return { ...message, ...meta, tool_calls: toolCalls };
            });
          }
        }
      } catch (error) {
        console.warn('Replay events API unavailable, fallback to message history', error);
      }
      try {
        const statesResp = await fetch(`/api/chat/${id}/actions/states`);
        if (statesResp.ok) {
          const stateData = await statesResp.json();
          options.setActionStates(Array.isArray(stateData) ? stateData : []);
        } else {
          options.setActionStates(replayActionStates);
        }
      } catch (error) {
        console.warn('Action states API unavailable, fallback to replay events', error);
        options.setActionStates(replayActionStates);
      }
      options.setCurrentChatId(data.id);
      options.setMessages(mergedMessages);
      setSelectedAgent(data.agent_id);
      setSelectedWorkspaceId?.(data.workspace_id || null);
      if (data.active_skill_name && data.active_skill_version) {
        options.setActiveSkill({ name: data.active_skill_name, version: data.active_skill_version });
      } else {
        options.setActiveSkill(null);
      }
      if (isMobile) setShowHistory(false);
    } catch (error) {
      console.error('Failed to load chat', error);
      options.toast.error('Failed to load chat session');
    }
  };

  const startNewChat = (isMobile: boolean, setShowHistory: (value: boolean) => void) => {
    if (options.isTyping()) options.stopGeneration();
    clearMetaRefreshTimers();
    options.setCurrentChatId(null);
    options.setMessages([]);
    options.setActionStates([]);
    options.setInput('');
    if (isMobile) setShowHistory(false);
  };

  const deleteChat = async (id: string) => {
    try {
      await fetch(`/api/chat/${id}`, { method: 'DELETE' });
      await loadHistory(true);
      if (options.currentChatId() === id) {
        options.setCurrentChatId(null);
        options.setMessages([]);
        options.setActionStates([]);
      }
      options.toast.success('Chat deleted successfully');
    } catch {
      options.toast.error('Failed to delete chat');
    }
  };

  const generateSummary = async (chatId: string, force = false): Promise<string> => {
    try {
      const res = await fetch(`/api/chat/${chatId}/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      await loadHistory(true);
      return typeof data?.summary === 'string' ? data.summary : '';
    } catch (error) {
      console.error('Failed to generate summary', error);
      options.toast.error('Failed to generate summary');
      return '';
    }
  };

  return {
    loadHistory,
    clearMetaRefreshTimers,
    refreshChatMeta,
    scheduleMetaRefreshForTitle,
    loadChat,
    startNewChat,
    deleteChat,
    generateSummary,
  };
}
