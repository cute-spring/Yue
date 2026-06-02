import { ActionState, Attachment, Message } from '../../types';
import { canSubmitChatRequest } from './chatStream';
import { streamAssistantResponse } from './chatSubmissionStream';
import { uploadAttachments } from './chatSubmissionUpload';

type Accessor<T> = () => T;
type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

export type SubmitChatTextOptions = {
  rawText: string;
  requestOverrides?: Record<string, any>;
  currentImages: File[];
  messages: Accessor<Message[]>;
  currentChatId: Accessor<string | null>;
  currentWorkspaceId: Accessor<string | null>;
  selectedProvider: Accessor<string>;
  selectedModel: Accessor<string>;
  selectedAgent: Accessor<string | null>;
  requestedSkill: Accessor<string | null>;
  isDeepThinking: Accessor<boolean>;
  setMessages: Setter<Message[]>;
  setInput: (value: string) => unknown;
  setImageAttachments: (files: File[]) => unknown;
  setIsTyping: (value: boolean) => unknown;
  setLastGenerationOutcome: (value: 'success' | 'aborted' | 'error' | null) => unknown;
  setActiveSkill: (value: { name: string; version: string } | null) => unknown;
  setElapsedTime: (value: number | ((prev: number) => number)) => unknown;
  setCurrentChatId: (value: string | null) => unknown;
  setActionStates: Setter<ActionState[]>;
  setShowLLMSelector: (value: boolean) => void;
  refreshChatMeta: (chatId: string) => Promise<boolean>;
  scheduleMetaRefreshForTitle: (chatId: string) => void;
  toast: {
    error: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
  };
  fileToBase64: (file: File) => Promise<string>;
  setAbortController: (controller: AbortController | null) => void;
  setTimerInterval: (interval: ReturnType<typeof setInterval> | null) => void;
  getTimerInterval: () => ReturnType<typeof setInterval> | null;
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
};

export { uploadAttachments } from './chatSubmissionUpload';

export const submitChatText = async ({
  rawText,
  requestOverrides,
  currentImages,
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
  refreshChatMeta,
  scheduleMetaRefreshForTitle,
  toast,
  fileToBase64,
  setAbortController,
  setTimerInterval,
  getTimerInterval,
  fetchImpl = fetch,
}: SubmitChatTextOptions) => {
  const text = rawText.trim();
  if (!canSubmitChatRequest(text, currentImages.length)) return;

  if (!selectedModel()) {
    setShowLLMSelector(true);
    const last = messages()[messages().length - 1];
    if (!last || last.role !== 'assistant' || last.content !== 'Please select a model before starting a chat.') {
      setMessages([...messages(), { role: 'assistant', content: 'Please select a model before starting a chat.' }]);
    }
    return;
  }

  let uploadedAttachments: Attachment[] = [];
  if (currentImages.length > 0) {
    try {
      uploadedAttachments = await uploadAttachments(currentImages, fetchImpl);
    } catch (e) {
      const message = e instanceof Error ? e.message : '附件上传失败，请稍后重试';
      toast.error(message);
      return;
    }
  }

  const imageFiles = currentImages.filter((file) => file.type.startsWith('image/'));
  let base64Images: string[] = [];
  if (imageFiles.length > 0) {
    try {
      base64Images = await Promise.all(imageFiles.map(fileToBase64));
    } catch (e) {
      console.error('Failed to convert images', e);
      toast.error('Failed to process attached images');
    }
  }

  const nowIso = new Date().toISOString();
  const contextId = currentChatId() || undefined;
  setMessages([...messages(), {
    role: 'user',
    content: text,
    images: base64Images,
    attachments: uploadedAttachments,
    timestamp: nowIso,
    context_id: contextId,
  }]);
  setInput('');
  setImageAttachments([]);
  setIsTyping(true);
  setLastGenerationOutcome(null);
  setActiveSkill(null);
  setElapsedTime(0);
  const startTime = Date.now();
  const timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);
  setTimerInterval(timerInterval);
  setMessages(prev => [...prev, {
    role: 'assistant',
    content: '',
    timestamp: nowIso,
    provider: selectedProvider(),
    model: selectedModel(),
    context_id: contextId,
    continuation_of: typeof requestOverrides?.continuation_of === 'string' ? requestOverrides.continuation_of : undefined,
    continuation_root_id: typeof requestOverrides?.continuation_root_id === 'string' ? requestOverrides.continuation_root_id : undefined,
    continuation_status: typeof requestOverrides?.continuation_of === 'string' ? 'resuming' : undefined,
    content_type: typeof requestOverrides?.continuation_content_type === 'string' ? requestOverrides.continuation_content_type : undefined,
    tools: [],
    tool_calls: [],
    citations: [],
  }]);

  await streamAssistantResponse({
    text,
    base64Images,
    uploadedAttachments,
    requestOverrides,
    currentChatId,
    currentWorkspaceId,
    selectedProvider,
    selectedModel,
    selectedAgent,
    requestedSkill,
    isDeepThinking,
    setMessages,
    setCurrentChatId,
    setActionStates,
    setActiveSkill,
    setLastGenerationOutcome,
    setIsTyping,
    refreshChatMeta,
    scheduleMetaRefreshForTitle,
    toast,
    startTime,
    setAbortController,
    getTimerInterval,
    setTimerInterval,
    fetchImpl,
  });
};
