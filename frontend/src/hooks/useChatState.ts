import { createSignal, onMount } from 'solid-js';
import { ChatSession, Message, ChatEventEnvelope, Agent } from '../types';
import { useToast } from '../context/ToastContext';
import {
  buildToolCallsFromEvents,
  canSubmitChatRequest,
  getVisionStreamFeedback,
  normalizeStreamEvent,
  shouldAcceptEvent,
} from './chat/chatStream';
import { submitChatText } from './chat/chatSubmission';

export {
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

export function useChatState(
  selectedProvider: () => string,
  selectedModel: () => string,
  selectedAgent: () => string | null,
  requestedSkill: () => string | null,
  setShowLLMSelector: (v: boolean) => void
) {
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
  const [lastGenerationOutcome, setLastGenerationOutcome] = createSignal<'success' | 'aborted' | 'error' | null>(null);
  
  let abortController: AbortController | null = null;
  let timerInterval: any = null;
  let metaRefreshTimers: number[] = [];
  let historyFetchInFlight: Promise<void> | null = null;
  let lastHistoryFetchAt = 0;
  const historyFetchMinIntervalMs = 800;

  const loadHistory = async (force: boolean = false) => {
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
        const res = await fetch('/api/chat/history');
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
      try {
        const eventsResp = await fetch(`/api/chat/${id}/events`);
        if (eventsResp.ok) {
          const replayEventsRaw = await eventsResp.json();
          if (Array.isArray(replayEventsRaw) && replayEventsRaw.length > 0) {
            const replayEvents = replayEventsRaw.map(normalizeStreamEvent);
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
    lastGenerationOutcome,
    loadHistory,
    loadChat,
    startNewChat,
    deleteChat,
    generateSummary,
    stopGeneration,
    submitText,
    handleSubmit,
    handleRegenerate,
    toggleThought,
    handleImageUpload,
    removeImage,
    copyUserMessage,
    quoteUserMessage
  };
}
