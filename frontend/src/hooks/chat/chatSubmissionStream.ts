import { ActionState, ChatEventEnvelope, Message } from '../../types';
import {
  applyActionEventToStates,
  applyChartArtifactEventToMessages,
  buildToolCallsFromEvents,
  getVisionStreamFeedback,
  normalizeStreamEvent,
  shouldAcceptEvent,
} from './chatStream';

type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

type StreamAssistantResponseOptions = {
  text: string;
  base64Images: string[];
  uploadedAttachments: any[];
  requestOverrides?: Record<string, any>;
  currentChatId: () => string | null;
  currentWorkspaceId: () => string | null;
  selectedProvider: () => string;
  selectedModel: () => string;
  selectedAgent: () => string | null;
  requestedSkill: () => string | null;
  isDeepThinking: () => boolean;
  setMessages: Setter<Message[]>;
  setCurrentChatId: (value: string | null) => unknown;
  setActionStates: Setter<ActionState[]>;
  setActiveSkill: (value: { name: string; version: string } | null) => unknown;
  setLastGenerationOutcome: (value: 'success' | 'aborted' | 'error' | null) => unknown;
  setIsTyping: (value: boolean) => unknown;
  refreshChatMeta: (chatId: string) => Promise<boolean>;
  scheduleMetaRefreshForTitle: (chatId: string) => void;
  toast: {
    error: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
  };
  startTime: number;
  setAbortController: (controller: AbortController | null) => void;
  getTimerInterval: () => ReturnType<typeof setInterval> | null;
  setTimerInterval: (interval: ReturnType<typeof setInterval> | null) => void;
  fetchImpl?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
};

export async function streamAssistantResponse({
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
  fetchImpl = fetch,
}: StreamAssistantResponseOptions) {
  const agentId = selectedAgent() || undefined;
  const abortController = new AbortController();
  setAbortController(abortController);

  try {
    let assistantHadError = false;
    let firstTokenTime: number | null = null;
    const response = await fetchImpl('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        images: base64Images.length > 0 ? base64Images : undefined,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
        workspace_id: currentWorkspaceId() || undefined,
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
              const current = next[lastIndex];
              const nextContinuationStatus = current.continuation_of
                ? (data.finish_reason === 'length' ? 'truncated' : 'continued')
                : (data.finish_reason === 'length' ? 'truncated' : current.continuation_status);
              next[lastIndex] = { ...current, ...data, continuation_status: nextContinuationStatus };
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
        } else if (data.workspace_grounding) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], workspace_grounding: data.workspace_grounding };
            }
            return next;
          });
        } else if (data.session_used_context) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], session_used_context: data.session_used_context };
            }
            return next;
          });
        } else if (data.workspace_notes) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], workspace_notes: data.workspace_notes };
            }
            return next;
          });
        } else if (data.workspace_memory) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], workspace_memory: data.workspace_memory };
            }
            return next;
          });
        } else if (data.workspace_capture_suggestion) {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            if (lastIndex >= 0) {
              next[lastIndex] = { ...next[lastIndex], workspace_capture_suggestion: data.workspace_capture_suggestion };
            }
            return next;
          });
        } else if (data.event === 'artifact.chart.created') {
          flushBuffer();
          setMessages(prev => applyChartArtifactEventToMessages(prev, data));
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
}
