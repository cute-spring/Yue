import { createSignal, onMount } from 'solid-js';
import { ChatSession, Message, ChatEventEnvelope, ToolCall, Agent } from '../types';
import { useToast } from '../context/ToastContext';

export const normalizeStreamEvent = (raw: any): ChatEventEnvelope => {
  if (raw && raw.version === 'v2') {
    const payload = typeof raw.payload === 'object' && raw.payload ? raw.payload : {};
    return { ...payload, ...raw };
  }
  return raw || {};
};

export const eventSortKey = (event: ChatEventEnvelope) => {
  const seq = typeof event.sequence === 'number' ? event.sequence : Number.MAX_SAFE_INTEGER;
  const ts = typeof event.ts === 'string' ? event.ts : '';
  return { seq, ts };
};

export const buildToolCallsFromEvents = (events: ChatEventEnvelope[]): ToolCall[] => {
  const sorted = [...events].sort((a, b) => {
    const ka = eventSortKey(a);
    const kb = eventSortKey(b);
    if (ka.seq !== kb.seq) return ka.seq - kb.seq;
    return ka.ts.localeCompare(kb.ts);
  });
  const calls = new Map<string, ToolCall>();
  for (const ev of sorted) {
    const eventName = ev.event;
    if (eventName !== 'tool.call.started' && eventName !== 'tool.call.finished') continue;
    const callId = ev.call_id as string | undefined;
    if (!callId) continue;
    const existing = calls.get(callId) || {
      call_id: callId,
      tool_name: (ev.tool_name as string) || 'unknown_tool',
      status: 'running' as const
    };
    if (eventName === 'tool.call.started') {
      calls.set(callId, {
        ...existing,
        tool_name: (ev.tool_name as string) || existing.tool_name,
        args: ev.args ?? existing.args,
        status: 'running',
        sequence: typeof ev.sequence === 'number' ? ev.sequence : existing.sequence,
        ts: typeof ev.ts === 'string' ? ev.ts : existing.ts
      });
    } else {
      calls.set(callId, {
        ...existing,
        tool_name: (ev.tool_name as string) || existing.tool_name,
        result: ev.result,
        error: ev.error as string | undefined,
        duration_ms: typeof ev.duration_ms === 'number' ? ev.duration_ms : existing.duration_ms,
        status: (ev.error ? 'error' : 'success') as 'error' | 'success',
        sequence: typeof ev.sequence === 'number' ? ev.sequence : existing.sequence,
        ts: typeof ev.ts === 'string' ? ev.ts : existing.ts
      });
    }
  }
  return [...calls.values()].sort((a, b) => (a.sequence || Number.MAX_SAFE_INTEGER) - (b.sequence || Number.MAX_SAFE_INTEGER));
};

export const shouldAcceptEvent = (seenEventIds: Set<string>, event: ChatEventEnvelope): boolean => {
  const id = typeof event.event_id === 'string' ? event.event_id : '';
  if (!id) return true;
  if (seenEventIds.has(id)) return false;
  seenEventIds.add(id);
  return true;
};

export const canSubmitChatRequest = (inputText: string, imageCount: number): boolean => {
  return inputText.trim().length > 0 || imageCount > 0;
};

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

export type VisionStreamFeedback = {
  level: 'info' | 'warning' | 'error';
  message: string;
};

export const getVisionStreamFeedback = (
  meta: Record<string, any> = {},
  errorCode?: string | null,
): VisionStreamFeedback | null => {
  if (errorCode === 'MODEL_VISION_UNSUPPORTED') {
    return {
      level: 'error',
      message: '当前模型不支持视觉能力。请切换到带 Vision 标识的模型后重试。',
    };
  }
  const fallbackMode = typeof meta.vision_fallback_mode === 'string' ? meta.vision_fallback_mode : '';
  const imageCount = typeof meta.image_count === 'number' ? meta.image_count : 0;
  const supportsVision = typeof meta.supports_vision === 'boolean' ? meta.supports_vision : null;
  const visionEnabled = typeof meta.vision_enabled === 'boolean' ? meta.vision_enabled : null;
  if (fallbackMode === 'text_only' && imageCount > 0) {
    return {
      level: 'warning',
      message: '当前模型不支持视觉，已自动降级为纯文本回复。建议切换到支持 Vision 的模型。',
    };
  }
  if (imageCount > 0 && supportsVision === false && visionEnabled === false) {
    return {
      level: 'warning',
      message: '当前模型未开启视觉处理，图片内容可能未参与回答。',
    };
  }
  return null;
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

  const handleSubmit = async (e?: Event) => {
    e?.preventDefault();

    if (isTyping()) {
      stopGeneration();
      return;
    }

    const text = input().trim();
    const currentImages = imageAttachments();
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
    let base64Images: string[] = [];
    if (currentImages.length > 0) {
      try {
        base64Images = await Promise.all(currentImages.map(fileToBase64));
      } catch (e) {
        console.error("Failed to convert images", e);
        toast.error("Failed to process attached images");
      }
    }

    const nowIso = new Date().toISOString();
    const contextId = currentChatId() || undefined;
    setMessages([...messages(), { role: 'user', content: text, images: base64Images, timestamp: nowIso, context_id: contextId }]);
    setInput("");
    setImageAttachments([]);
    setIsTyping(true);
    setLastGenerationOutcome(null);
    setActiveSkill(null);
    setElapsedTime(0);
    const startTime = Date.now();
    let firstTokenTime: number | null = null;

    timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);
    setMessages(prev => [...prev, { 
      role: 'assistant', 
      content: "", 
      timestamp: nowIso, 
      provider: selectedProvider(), 
      model: selectedModel(), 
      context_id: contextId, 
      tools: [], 
      tool_calls: [],
      citations: [] 
    }]);

    abortController = new AbortController();

    try {
      let assistantHadError = false;
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          images: base64Images.length > 0 ? base64Images : undefined,
          agent_id: agentId,
          requested_skill: requestedSkill() || undefined,
          chat_id: currentChatId(),
          provider: selectedProvider(),
          model: selectedModel(),
          deep_thinking_enabled: isDeepThinking(),
        }),
        signal: abortController.signal
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = "";
      let buffer = "";
      let lastUpdateTime = 0;
      let lineRemainder = ""; // Buffer for partial lines
      const UPDATE_INTERVAL = 40; // ~25fps for smoothness
      const seenEventIds = new Set<string>();
      const toolEventsByTurn = new Map<string, ChatEventEnvelope[]>();

      const flushBuffer = () => {
        if (buffer) {
          accumulatedResponse += buffer;
          buffer = "";
          setMessages(prev => {
            const newMsgs = [...prev];
            const lastIndex = newMsgs.length - 1;
            if (lastIndex >= 0) {
              newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
            }
            return newMsgs;
          });
        }
      };

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            // Process any remaining partial line
            if (lineRemainder) {
              processLine(lineRemainder);
              lineRemainder = "";
            }
            flushBuffer();
            break;
          }

          // Use stream: true to handle split multi-byte characters
          const chunk = decoder.decode(value, { stream: true });
          const combined = lineRemainder + chunk;
          const lines = combined.split('\n');
          
          // The last element is potentially a partial line
          lineRemainder = lines.pop() || "";
          
          for (const line of lines) {
            processLine(line);
          }
        }
      }

      function processLine(line: string) {
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
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], ...metaObj, run_id: (data.run_id as string | undefined) || metaObj.run_id, assistant_turn_id: (data.assistant_turn_id as string | undefined) || metaObj.assistant_turn_id };
              }
              return newMsgs;
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
                const newMsgs = [...prev];
                const lastIndex = newMsgs.length - 1;
                if (lastIndex >= 0) {
                  newMsgs[lastIndex] = { ...newMsgs[lastIndex], ttft };
                }
                return newMsgs;
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
              // Handle structured thought if present
              setMessages(prev => {
                const newMsgs = [...prev];
                const lastIndex = newMsgs.length - 1;
                if (lastIndex >= 0) {
                  const currentThought = newMsgs[lastIndex].thought || "";
                  newMsgs[lastIndex] = { ...newMsgs[lastIndex], thought: currentThought + data.thought };
                }
                return newMsgs;
              });
            }
          } else if (data.thought_duration) {
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], thought_duration: data.thought_duration };
              }
              return newMsgs;
            });
          } else if (data.total_duration) {
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration: data.total_duration * 1000 };
              }
              return newMsgs;
            });
          } else if (data.prompt_tokens !== undefined || data.completion_tokens !== undefined || data.total_tokens !== undefined || data.tps !== undefined || data.finish_reason !== undefined) {
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], ...data };
              }
              return newMsgs;
            });
          } else if (data.citations) {
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], citations: data.citations };
              }
              return newMsgs;
            });
          } else if (data.event === "tool.call.started") {
            const turnId = (data.assistant_turn_id as string) || "__current__";
            const bucket = toolEventsByTurn.get(turnId) || [];
            bucket.push(data);
            toolEventsByTurn.set(turnId, bucket);
            const merged = buildToolCallsFromEvents(bucket);
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], tool_calls: merged, assistant_turn_id: data.assistant_turn_id as string | undefined };
              }
              return newMsgs;
            });
          } else if (data.event === "tool.call.finished") {
            const turnId = (data.assistant_turn_id as string) || "__current__";
            const bucket = toolEventsByTurn.get(turnId) || [];
            bucket.push(data);
            toolEventsByTurn.set(turnId, bucket);
            const merged = buildToolCallsFromEvents(bucket);
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = { ...newMsgs[lastIndex], tool_calls: merged, assistant_turn_id: data.assistant_turn_id as string | undefined };
              }
              return newMsgs;
            });
          } else if (data.event === "run.limited") {
            // Handled via the content update from the backend friendly message, 
            // but we could also set a flag here if needed.
            console.warn("Run limited:", data.reason);
          } else if (data.event === "skill_selected") {
            setActiveSkill({ name: String(data.name || ""), version: String(data.version || "") });
            setMessages(prev => {
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = {
                  ...newMsgs[lastIndex],
                  active_skill_name: data.name,
                  active_skill_version: data.version
                };
              }
              return newMsgs;
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
              const newMsgs = [...prev];
              const lastIndex = newMsgs.length - 1;
              if (lastIndex >= 0) {
                newMsgs[lastIndex] = {
                  ...newMsgs[lastIndex],
                  content: `Error: ${errorMessage}`,
                  error: errorMessage,
                  error_code: errorCode,
                  supports_vision: data.supports_vision,
                  vision_enabled: data.vision_enabled,
                  vision_fallback_mode: data.vision_fallback_mode,
                  image_count: data.image_count,
                };
              }
              return newMsgs;
            });
            if (visionFeedback?.level === 'error') {
              toast.error(visionFeedback.message);
            }
          }
        } catch (e) {
          console.warn("Failed to parse stream message", e, "Line:", line, "JSON:", jsonStr);
        }
      }
      const total_duration = Date.now() - startTime;
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIndex = newMsgs.length - 1;
        if (lastIndex >= 0) {
          newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration };
        }
        return newMsgs;
      });
      if (assistantHadError) {
        setLastGenerationOutcome('error');
      } else {
        setLastGenerationOutcome('success');
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user');
        setLastGenerationOutcome('aborted');
      } else {
        console.error("Chat error:", err);
        toast.error("Connection error: " + (err.message || "Unknown error"));
        setLastGenerationOutcome('error');
      }
    } finally {
      setIsTyping(false);
      clearInterval(timerInterval);
      abortController = null;
      const chatIdForMeta = currentChatId();
      if (chatIdForMeta) {
        scheduleMetaRefreshForTitle(chatIdForMeta);
      }
    }
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
    handleSubmit,
    handleRegenerate,
    toggleThought,
    handleImageUpload,
    removeImage,
    copyUserMessage,
    quoteUserMessage
  };
}
