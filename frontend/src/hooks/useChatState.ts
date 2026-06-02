import { createSignal, onMount } from 'solid-js';
import { ChatSession, Message, Agent, ActionState } from '../types';
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
import { createChatHistoryState } from './chat/useChatHistoryState';

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
  setShowLLMSelector: (v: boolean) => void,
  currentWorkspaceId: () => string | null = () => null,
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
  const [actionStates, setActionStates] = createSignal<ActionState[]>([]);
  const [lastGenerationOutcome, setLastGenerationOutcome] = createSignal<'success' | 'aborted' | 'error' | null>(null);
  
  let abortController: AbortController | null = null;
  let timerInterval: any = null;
  const historyState = createChatHistoryState({
    chats,
    setChats,
    currentChatId,
    setCurrentChatId,
    messages,
    setMessages,
    setActionStates,
    setInput,
    setActiveSkill,
    isTyping,
    stopGeneration: () => stopGeneration(),
    toast,
  });

  const stopGeneration = () => {
    console.log("Stopping generation...");
    historyState.clearMetaRefreshTimers();
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

  const submitText = async (rawText: string, requestOverrides?: Record<string, any>) => {
    await submitChatText({
      rawText,
      requestOverrides,
      currentImages: imageAttachments(),
      messages,
      currentChatId,
      currentWorkspaceId,
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
      refreshChatMeta: historyState.refreshChatMeta,
      scheduleMetaRefreshForTitle: historyState.scheduleMetaRefreshForTitle,
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
      currentWorkspaceId,
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
      refreshChatMeta: historyState.refreshChatMeta,
      scheduleMetaRefreshForTitle: historyState.scheduleMetaRefreshForTitle,
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
    historyState.loadHistory();
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
    loadHistory: historyState.loadHistory,
    loadChat: historyState.loadChat,
    startNewChat: historyState.startNewChat,
    deleteChat: historyState.deleteChat,
    generateSummary: historyState.generateSummary,
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
