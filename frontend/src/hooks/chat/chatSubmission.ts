import { ActionState, Attachment, ChatEventEnvelope, Message } from '../../types';
import {
  applyActionEventToStates,
  buildToolCallsFromEvents,
  canSubmitChatRequest,
  getVisionStreamFeedback,
  normalizeStreamEvent,
  shouldAcceptEvent,
} from './chatStream';

type Accessor<T> = () => T;
type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

export type SubmitChatTextOptions = {
  rawText: string;
  requestOverrides?: Record<string, any>;
  currentImages: File[];
  messages: Accessor<Message[]>;
  currentChatId: Accessor<string | null>;
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

type UploadErrorPayload = {
  detail?: {
    code?: string;
    message?: string;
    max_files?: number;
    max_file_size_bytes?: number;
    allowed_mime_types?: string[];
    allowed_extensions?: string[];
  };
};

const MAX_UPLOAD_FILES_FALLBACK = 10;
const MAX_UPLOAD_FILE_SIZE_FALLBACK_BYTES = 20 * 1024 * 1024;

const formatLimitMb = (bytes: number): string => {
  const value = bytes / 1024 / 1024;
  return Number.isInteger(value) ? `${value}MB` : `${value.toFixed(2)}MB`;
};

const getUploadErrorMessage = (detail?: UploadErrorPayload['detail']): string => {
  const code = detail?.code;
  switch (code) {
    case 'unsupported_file_type':
      return '附件上传失败：文件类型不支持（仅支持图片/PDF/Excel/CSV）';
    case 'too_many_files':
      return `附件上传失败：单次最多上传 ${detail?.max_files || MAX_UPLOAD_FILES_FALLBACK} 个文件`;
    case 'file_too_large':
      return `附件上传失败：文件超过大小限制（${formatLimitMb(detail?.max_file_size_bytes || MAX_UPLOAD_FILE_SIZE_FALLBACK_BYTES)}）`;
    case 'empty_file':
      return '附件上传失败：存在空文件';
    default:
      return '附件上传失败，请稍后重试';
  }
};

export const uploadAttachments = async (
  files: File[],
  fetchImpl: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> = fetch,
): Promise<Attachment[]> => {
  if (files.length === 0) return [];
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const response = await fetchImpl('/api/files', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    let detail: UploadErrorPayload['detail'] | undefined;
    try {
      const payload = (await response.json()) as UploadErrorPayload;
      detail = payload?.detail;
    } catch {
      detail = undefined;
    }
    throw new Error(getUploadErrorMessage(detail));
  }
  const payload = (await response.json()) as { files?: Attachment[] };
  return Array.isArray(payload.files) ? payload.files : [];
};

export const submitChatText = async ({
  rawText,
  requestOverrides,
  currentImages,
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

  const agentId = selectedAgent() || undefined;
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
  let firstTokenTime: number | null = null;

  const timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);
  setTimerInterval(timerInterval);
  setMessages(prev => [...prev, {
    role: 'assistant',
    content: '',
    timestamp: nowIso,
    provider: selectedProvider(),
    model: selectedModel(),
    context_id: contextId,
    tools: [],
    tool_calls: [],
    citations: [],
  }]);

  const abortController = new AbortController();
  setAbortController(abortController);

  try {
    let assistantHadError = false;
    const response = await fetchImpl('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        images: base64Images.length > 0 ? base64Images : undefined,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
        agent_id: agentId,
        requested_skill: requestedSkill() || undefined,
        chat_id: currentChatId(),
        provider: selectedProvider(),
        model: selectedModel(),
        deep_thinking_enabled: isDeepThinking(),
        ...requestOverrides,
      }),
      signal: abortController.signal,
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let accumulatedResponse = '';
    let buffer = '';
    let lastUpdateTime = 0;
    let lineRemainder = '';
    const UPDATE_INTERVAL = 40;
    const seenEventIds = new Set<string>();
    const toolEventsByTurn = new Map<string, ChatEventEnvelope[]>();

    const flushBuffer = () => {
      if (!buffer) return;
      accumulatedResponse += buffer;
      buffer = '';
      setMessages(prev => {
        const next = [...prev];
        const lastIndex = next.length - 1;
        if (lastIndex >= 0) {
          next[lastIndex] = { ...next[lastIndex], content: accumulatedResponse };
        }
        return next;
      });
    };

    const processLine = (line: string) => {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) return;

      const jsonStr = trimmed.slice(6);
      try {
        const rawData = JSON.parse(jsonStr);
        const data = normalizeStreamEvent(rawData);
        if (!shouldAcceptEvent(seenEventIds, data)) return;
        if (data.chat_id) {
          setCurrentChatId(data.chat_id);
          setMessages(prev => prev.map(m => m.context_id ? m : { ...m, context_id: data.chat_id }));
          void refreshChatMeta(String(data.chat_id));
        } else if (data.meta) {
          const metaObj = data.meta as Record<string, any>;
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = {
                ...next[lastIndex],
                ...metaObj,
                run_id: (data.run_id as string | undefined) || metaObj.run_id,
                assistant_turn_id: (data.assistant_turn_id as string | undefined) || metaObj.assistant_turn_id,
              };
            }
            return next;
          });
          const visionFeedback = getVisionStreamFeedback(metaObj);
          if (visionFeedback?.level === 'warning') {
            toast.warning(visionFeedback.message, 3500);
          }
        } else if (data.content || data.thought) {
          if (!firstTokenTime) {
            firstTokenTime = Date.now();
            const ttft = firstTokenTime - startTime;
            setMessages(prev => {
              const next = [...prev];
              const lastIndex = next.length - 1;
              if (lastIndex >= 0) {
                next[lastIndex] = { ...next[lastIndex], ttft };
              }
              return next;
            });
          }
          if (data.content) {
            buffer += data.content;
            const now = Date.now();
            if (now - lastUpdateTime > UPDATE_INTERVAL) {
              flushBuffer();
              lastUpdateTime = now;
            }
          }
          if (data.thought) {
            setMessages(prev => {
              const next = [...prev];
              const lastIndex = next.length - 1;
              if (lastIndex >= 0) {
                const currentThought = next[lastIndex].thought || '';
                next[lastIndex] = { ...next[lastIndex], thought: currentThought + data.thought };
              }
              return next;
            });
          }
        } else if (data.thought_duration) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], thought_duration: data.thought_duration };
            }
            return next;
          });
        } else if (data.total_duration) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], total_duration: data.total_duration * 1000 };
            }
            return next;
          });
        } else if (
          data.prompt_tokens !== undefined ||
          data.completion_tokens !== undefined ||
          data.total_tokens !== undefined ||
          data.tps !== undefined ||
          data.finish_reason !== undefined
        ) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], ...data };
            }
            return next;
          });
        } else if (data.citations) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], citations: data.citations };
            }
            return next;
          });
        } else if (data.event === 'tool.call.started' || data.event === 'tool.call.finished') {
          const turnId = (data.assistant_turn_id as string) || '__current__';
          const bucket = toolEventsByTurn.get(turnId) || [];
          bucket.push(data);
          toolEventsByTurn.set(turnId, bucket);
          const merged = buildToolCallsFromEvents(bucket);
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], tool_calls: merged, assistant_turn_id: data.assistant_turn_id as string | undefined };
            }
            return next;
          });
        } else if (typeof data.event === 'string' && data.event.startsWith('skill.action.')) {
          setActionStates(prev => applyActionEventToStates(prev, data));
        } else if (data.event === 'run.limited') {
          console.warn('Run limited:', data.reason);
        } else if (data.event === 'skill_selected') {
          setActiveSkill({ name: String(data.name || ''), version: String(data.version || '') });
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = {
                ...next[lastIndex],
                active_skill_name: data.name,
                active_skill_version: data.version,
              };
            }
            return next;
          });
        } else if (data.error) {
          assistantHadError = true;
          const errorCode = typeof data.error_code === 'string' ? data.error_code : undefined;
          const visionFeedback = getVisionStreamFeedback(
            {
              supports_vision: data.supports_vision,
              vision_enabled: data.vision_enabled,
              image_count: data.image_count,
              vision_fallback_mode: data.vision_fallback_mode,
            },
            errorCode,
          );
          const errorMessage = visionFeedback?.message || String(data.error);
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = {
                ...next[lastIndex],
                content: `Error: ${errorMessage}`,
                error: errorMessage,
                error_code: errorCode,
                supports_vision: data.supports_vision,
                vision_enabled: data.vision_enabled,
                vision_fallback_mode: data.vision_fallback_mode,
                image_count: data.image_count,
              };
            }
            return next;
          });
          if (visionFeedback?.level === 'error') {
            toast.error(visionFeedback.message);
          }
        }
      } catch (e) {
        console.warn('Failed to parse stream message', e, 'Line:', line, 'JSON:', jsonStr);
      }
    };

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          if (lineRemainder) {
            processLine(lineRemainder);
            lineRemainder = '';
          }
          flushBuffer();
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const combined = lineRemainder + chunk;
        const lines = combined.split('\n');
        lineRemainder = lines.pop() || '';

        for (const line of lines) {
          processLine(line);
        }
      }
    }

    const totalDuration = Date.now() - startTime;
    setMessages(prev => {
      const next = [...prev];
      const lastIndex = next.length - 1;
      if (lastIndex >= 0) {
        next[lastIndex] = { ...next[lastIndex], total_duration: totalDuration };
      }
      return next;
    });
    setLastGenerationOutcome(assistantHadError ? 'error' : 'success');
  } catch (err: any) {
    if (err.name === 'AbortError') {
      console.log('Generation stopped by user');
      setLastGenerationOutcome('aborted');
    } else {
      console.error('Chat error:', err);
      toast.error('Connection error: ' + (err.message || 'Unknown error'));
      setLastGenerationOutcome('error');
    }
  } finally {
    setIsTyping(false);
    const currentTimer = getTimerInterval();
    if (currentTimer) {
      clearInterval(currentTimer);
      setTimerInterval(null);
    }
    setAbortController(null);
    const chatIdForMeta = currentChatId();
    if (chatIdForMeta) {
      scheduleMetaRefreshForTitle(chatIdForMeta);
    }
  }
};
