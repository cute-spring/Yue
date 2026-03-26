import { ChatEventEnvelope, ToolCall } from '../../types';

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
      status: 'running' as const,
    };
    if (eventName === 'tool.call.started') {
      calls.set(callId, {
        ...existing,
        tool_name: (ev.tool_name as string) || existing.tool_name,
        args: ev.args ?? existing.args,
        status: 'running',
        sequence: typeof ev.sequence === 'number' ? ev.sequence : existing.sequence,
        ts: typeof ev.ts === 'string' ? ev.ts : existing.ts,
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
        ts: typeof ev.ts === 'string' ? ev.ts : existing.ts,
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
