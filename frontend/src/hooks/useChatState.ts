import { createSignal, onMount } from 'solid-js';
import { ChatSession, Message, ChatEventEnvelope, Agent, ActionState } from '../types';
import { useToast } from '../context/ToastContext';
import {
  applyActionEventToStates,
  buildActionStatesFromEvents,
  buildToolCallsFromEvents,
  canSubmitChatRequest,
  getVisionStreamFeedback,
  normalizeStreamEvent,
  shouldAcceptEvent,
} from './chat/chatStream';
import { submitChatText } from './chat/chatSubmission';

export {
  applyActionEventToStates,
  buildActionStatesFromEvents,
  normalizeStreamEvent,
  buildToolCallsFromEvents,
  shouldAcceptEvent,
  canSubmitChatRequest,
  getVisionStreamFeedback,
};
export type { VisionStreamFeedback } from './chat/chatStream';

export const getAgentVisibleSkills = (agent?: Agent | null): string[] => {
  if (!agent) return [];
  const resolved = Array.isArray(agent.resolved_visible_skills) ? agent.resolved_visible_skills : [];
  if (resolved.length > 0) return resolved;
  return Array.isArray(agent.visible_skills) ? agent.visible_skills : [];
};

export const shouldSkipHistoryFetch = (lastFetchAt: number, now: number, minIntervalMs: number): boolean => {
  if (lastFetchAt <= 0) return false;
  return now - lastFetchAt < minIntervalMs;
};

export type EditQuestionFlowDeps = {
  index: number;
  newContent: string;
  isTyping: boolean;
  currentMessages: Array<Pick<Message, 'role' | 'content'>>;
  currentChatId: string | null;
  fetchImpl: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  truncateLocalMessages: (keepCount: number) => void;
  setInputText: (value: string) => void;
  submitEditedQuestion: (value: string) => Promise<void>;
};

export const runEditQuestionFlow = async ({
  index,
  newContent,
  isTyping,
  currentMessages,
  currentChatId,
  fetchImpl,
  truncateLocalMessages,
  setInputText,
  submitEditedQuestion,
}: EditQuestionFlowDeps): Promise<void> => {
  if (isTyping) return;
  const trimmed = newContent.trim();
  if (!trimmed) {
    throw new Error('Edited question cannot be empty');
  }
  if (index < 0 || index >= currentMessages.length) {
    throw new Error('Invalid message index');
  }
  const targetMessage = currentMessages[index];
  if (targetMessage.role !== 'user') {
    throw new Error('Only user messages can be edited');
  }

  // TODO: Prefer message-id truncation once backend supports it.
  const keepCount = index;

  if (currentChatId) {
    const response = await fetchImpl(`/api/chat/${currentChatId}/truncate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keep_count: keepCount }),
    });
    if (!response.ok) {
      throw new Error(`Failed to truncate chat history (${response.status})`);
    }
  }

  truncateLocalMessages(keepCount);
  setInputText(trimmed);
  await submitEditedQuestion(trimmed);
};

export function useChatState(
  selectedProvider: () => string,
  selectedModel: () => string,
  selectedAgent: () => string | null,
  requestedSkill: () => string | null,
  setShowLLMSelector: (v: boolean) => void
) {
  type HistoryFilters = {
    tags?: string[];
    tagMode?: 'any' | 'all';
    dateFrom?: string;
    dateTo?: string;
  };

  const toast = useToast();
  const [chats, setChats] = createSignal<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = createSignal<string | null>(null);
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [elapsedTime, setElapsedTime] = createSignal(0);
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  const [expandedThoughts, setExpandedThoughts] = createSignal<Record<number, boolean>>({});
  const [imageAttachments, setImageAttachments] = createSignal<File[]>([]);
  const [copiedMessageIndex, setCopiedMessageIndex] = createSignal<number | null>(null);
  const [activeSkill, setActiveSkill] = createSignal<{ name: string; version: string } | null>(null);
  const [actionStates, setActionStates] = createSignal<ActionState[]>([]);
  const [lastGenerationOutcome, setLastGenerationOutcome] = createSignal<'success' | 'aborted' | 'error' | null>(null);
  
  let abortController: AbortController | null = null;
  let timerInterval: any = null;
  let metaRefreshTimers: number[] = [];
  let historyFetchInFlight: Promise<void> | null = null;
  let lastHistoryFetchAt = 0;
  const historyFetchMinIntervalMs = 800;

  const loadHistory = async (force: boolean = false, filters?: HistoryFilters) => {
    if (historyFetchInFlight) {
      await historyFetchInFlight;
      return;
    }
    const now = Date.now();
    if (!force && shouldSkipHistoryFetch(lastHistoryFetchAt, now, historyFetchMinIntervalMs)) {
      return;
    }
    historyFetchInFlight = (async () => {
      try {
        const params = new URLSearchParams();
        if (filters?.tags && filters.tags.length > 0) {
          params.set('tags', filters.tags.join(','));
        }
        if (filters?.tagMode) {
          params.set('tag_mode', filters.tagMode);
        }
        if (filters?.dateFrom) {
          params.set('date_from', filters.dateFrom);
        }
        if (filters?.dateTo) {
          params.set('date_to', filters.dateTo);
        }
        const query = params.toString();
        const res = await fetch(query ? `/api/chat/history?${query}` : '/api/chat/history');
        const data = await res.json();
        setChats(data);
        lastHistoryFetchAt = Date.now();
      } catch (e) {
        console.error("Failed to load history", e);
        toast.error("Failed to load chat history");
      } finally {
        historyFetchInFlight = null;
      }
    })();
    await historyFetchInFlight;
  };

  const clearMetaRefreshTimers = () => {
    for (const timer of metaRefreshTimers) {
      clearTimeout(timer);
    }
    metaRefreshTimers = [];
  };

  const refreshChatMeta = async (chatId: string): Promise<boolean> => {
    try {
      const res = await fetch(`/api/chat/${chatId}/meta`);
      if (!res.ok) {
        return false;
      }
      const meta = await res.json();
      let titleChanged = false;
      setChats(prev => {
        const idx = prev.findIndex(c => c.id === chatId);
        if (idx === -1) {
          return [{ id: meta.id, title: meta.title, summary: meta.summary, updated_at: meta.updated_at }, ...prev];
        }
        const current = prev[idx];
        if (current.title !== meta.title) {
          titleChanged = true;
        }
        if (current.title === meta.title && current.summary === meta.summary && current.updated_at === meta.updated_at) {
          return prev;
        }
        const next = [...prev];
        next[idx] = {
          ...current,
          title: meta.title,
          summary: meta.summary,
          updated_at: meta.updated_at
        };
        return next;
      });
      return titleChanged;
    } catch (e) {
      console.warn("Failed to refresh chat meta", e);
      return false;
    }
  };

  const scheduleMetaRefreshForTitle = (chatId: string) => {
    clearMetaRefreshTimers();
    for (const delay of [1200, 3000]) {
      const timer = window.setTimeout(async () => {
        const changed = await refreshChatMeta(chatId);
        if (changed) {
          clearMetaRefreshTimers();
        }
      }, delay);
      metaRefreshTimers.push(timer);
    }
  };

  const loadChat = async (id: string, isMobile: boolean, setShowHistory: (v: boolean) => void, setSelectedAgent: (v: string | null) => void) => {
    if (isTyping()) stopGeneration();
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
            for (const ev of replayEvents) {
              const turnId = typeof ev.assistant_turn_id === 'string' ? ev.assistant_turn_id : '';
              if (!turnId) continue;
              const bucket = eventsByTurn.get(turnId) || [];
              bucket.push(ev);
              eventsByTurn.set(turnId, bucket);
              if (ev.meta && typeof ev.meta === 'object') {
                metaByTurn.set(turnId, ev.meta as Record<string, any>);
              }
            }
            mergedMessages = mergedMessages.map(msg => {
              if (msg.role !== 'assistant') return msg;
              const turnId = msg.assistant_turn_id;
              if (!turnId) return msg;
              const toolCalls = buildToolCallsFromEvents(eventsByTurn.get(turnId) || []);
              const meta = metaByTurn.get(turnId) || {};
              return { ...msg, ...meta, tool_calls: toolCalls };
            });
          }
        }
      } catch (e) {
        console.warn("Replay events API unavailable, fallback to message history", e);
      }
      try {
        const statesResp = await fetch(`/api/chat/${id}/actions/states`);
        if (statesResp.ok) {
          const stateData = await statesResp.json();
          setActionStates(Array.isArray(stateData) ? stateData : []);
        } else {
          setActionStates(replayActionStates);
        }
      } catch (e) {
        console.warn("Action states API unavailable, fallback to replay events", e);
        setActionStates(replayActionStates);
      }
      setCurrentChatId(data.id);
      setMessages(mergedMessages);
      setSelectedAgent(data.agent_id);
      if (data.active_skill_name && data.active_skill_version) {
        setActiveSkill({ name: data.active_skill_name, version: data.active_skill_version });
      } else {
        setActiveSkill(null);
      }
      if (isMobile) {
        setShowHistory(false);
      }
    } catch (e) {
      console.error("Failed to load chat", e);
      toast.error("Failed to load chat session");
    }
  };

  const startNewChat = (isMobile: boolean, setShowHistory: (v: boolean) => void) => {
    if (isTyping()) stopGeneration();
    clearMetaRefreshTimers();
    setCurrentChatId(null);
    setMessages([]);
    setActionStates([]);
    setInput("");
    if (isMobile) {
      setShowHistory(false);
    }
  };

  const deleteChat = async (id: string) => {
    try {
      await fetch(`/api/chat/${id}`, { method: 'DELETE' });
      await loadHistory(true);
      if (currentChatId() === id) {
        setCurrentChatId(null);
        setMessages([]);
        setActionStates([]);
      }
      toast.success("Chat deleted successfully");
    } catch (e) {
      toast.error("Failed to delete chat");
    }
  };

  const generateSummary = async (chatId: string, force: boolean = false): Promise<string> => {
    try {
      const res = await fetch(`/api/chat/${chatId}/summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force })
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      await loadHistory(true);
      return typeof data?.summary === 'string' ? data.summary : '';
    } catch (e) {
      console.error("Failed to generate summary", e);
      toast.error("Failed to generate summary");
      return '';
    }
  };

  const stopGeneration = () => {
    console.log("Stopping generation...");
    clearMetaRefreshTimers();
    if (abortController) {
      console.log("Aborting fetch request");
      abortController.abort();
      abortController = null;
    }
    setIsTyping(false);
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
    toast.info("Generation stopped");
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const submitText = async (rawText: string) => {
    await submitChatText({
      rawText,
      requestOverrides: undefined,
      currentImages: imageAttachments(),
      messages,
      currentChatId,
      selectedProvider,
      selectedModel,
      selectedAgent,
      requestedSkill,
      isDeepThinking,
      setMessages,
      setInput,
      setImageAttachments,
      setIsTyping,
      setLastGenerationOutcome,
      setActiveSkill,
      setElapsedTime,
      setCurrentChatId,
      setActionStates,
      setShowLLMSelector,
      refreshChatMeta,
      scheduleMetaRefreshForTitle,
      toast,
      fileToBase64,
      setAbortController: (controller) => {
        abortController = controller;
      },
      setTimerInterval: (interval) => {
        timerInterval = interval;
      },
      getTimerInterval: () => timerInterval,
    });
  };

  const submitActionDecision = async (actionState: ActionState, approved: boolean) => {
    const requestedSkill = actionState.skill_version
      ? `${actionState.skill_name}:${actionState.skill_version}`
      : actionState.skill_name;
    const validatedArguments = actionState.payload?.metadata?.validated_arguments;
    const fallbackArguments = actionState.payload?.metadata?.tool_args;
    const requestArguments =
      validatedArguments && typeof validatedArguments === 'object'
        ? validatedArguments
        : (fallbackArguments && typeof fallbackArguments === 'object' ? fallbackArguments : undefined);
    const verb = approved ? 'Approve' : 'Reject';
    const rawText = `${verb} ${actionState.skill_name}.${actionState.action_id}`;

    await submitChatText({
      rawText,
      requestOverrides: {
        requested_skill: requestedSkill,
        requested_action: actionState.action_id,
        requested_action_approved: approved,
        requested_action_approval_token: actionState.approval_token || undefined,
        requested_action_arguments: requestArguments,
      },
      currentImages: [],
      messages,
      currentChatId,
      selectedProvider,
      selectedModel,
      selectedAgent,
      requestedSkill: () => requestedSkill,
      isDeepThinking,
      setMessages,
      setInput,
      setImageAttachments,
      setIsTyping,
      setLastGenerationOutcome,
      setActiveSkill,
      setElapsedTime,
      setCurrentChatId,
      setActionStates,
      setShowLLMSelector,
      refreshChatMeta,
      scheduleMetaRefreshForTitle,
      toast,
      fileToBase64,
      setAbortController: (controller) => {
        abortController = controller;
      },
      setTimerInterval: (interval) => {
        timerInterval = interval;
      },
      getTimerInterval: () => timerInterval,
    });
  };

  const handleSubmit = async (e?: Event) => {
    e?.preventDefault();

    if (isTyping()) {
      stopGeneration();
      return;
    }
    await submitText(input());
  };

  const handleRegenerate = async (index: number) => {
    if (isTyping()) return;
    const historyBefore = messages().slice(0, index);
    const lastUserMsgIndex = historyBefore.findLastIndex(m => m.role === 'user');
    if (lastUserMsgIndex === -1) return;
    const lastUserMsg = historyBefore[lastUserMsgIndex];
    if (currentChatId()) {
      try {
        await fetch(`/api/chat/${currentChatId()}/truncate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keep_count: lastUserMsgIndex })
        });
      } catch (e) {
        console.error("Failed to truncate chat history", e);
      }
    }
    setMessages(messages().slice(0, lastUserMsgIndex));
    setInput(lastUserMsg.content);
    handleSubmit();
  };

  const handleEditQuestion = async (index: number, newContent: string): Promise<void> => {
    try {
      await runEditQuestionFlow({
        index,
        newContent,
        isTyping: isTyping(),
        currentMessages: messages(),
        currentChatId: currentChatId(),
        fetchImpl: fetch,
        truncateLocalMessages: (keepCount) => {
          setMessages(messages().slice(0, keepCount));
        },
        setInputText: setInput,
        submitEditedQuestion: async (value) => {
          await submitText(value);
        },
      });
    } catch (error) {
      console.error('Failed to update question', error);
      toast.error('Failed to update question');
      throw error;
    }
  };

  onMount(() => {
    loadHistory();
  });

  const toggleThought = (index: number) => {
    setExpandedThoughts(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const handleImageUpload = (e: Event) => {
    const target = e.target as HTMLInputElement;
    if (target.files) {
      setImageAttachments(prev => [...prev, ...Array.from(target.files!)]);
    }
  };

  const removeImage = (index: number) => {
    setImageAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const copyUserMessage = (content: string, index: number) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageIndex(index);
    setTimeout(() => setCopiedMessageIndex(null), 2000);
    toast.success("Copied to clipboard");
  };

  const quoteUserMessage = (content: string) => {
    setInput(`> ${content}\n\n${input()}`);
  };

  return {
    chats,
    setChats,
    currentChatId,
    setCurrentChatId,
    messages,
    setMessages,
    input,
    setInput,
    isTyping,
    setIsTyping,
    elapsedTime,
    setElapsedTime,
    isDeepThinking,
    setIsDeepThinking,
    expandedThoughts,
    setExpandedThoughts,
    imageAttachments,
    setImageAttachments,
    copiedMessageIndex,
    setCopiedMessageIndex,
    activeSkill,
    setActiveSkill,
    actionStates,
    setActionStates,
    lastGenerationOutcome,
    loadHistory,
    loadChat,
    startNewChat,
    deleteChat,
    generateSummary,
    stopGeneration,
    submitText,
    submitActionDecision,
    handleSubmit,
    handleRegenerate,
    handleEditQuestion,
    toggleThought,
    handleImageUpload,
    removeImage,
    copyUserMessage,
    quoteUserMessage
  };
}
