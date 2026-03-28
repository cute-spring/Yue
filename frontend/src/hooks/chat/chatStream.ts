import { ActionState, ChatEventEnvelope, ToolCall } from '../../types';

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

const isSkillActionEvent = (event: ChatEventEnvelope): boolean => {
  return typeof event.event === 'string' && event.event.startsWith('skill.action.');
};

const actionStateKey = (state: Pick<ActionState, 'skill_name' | 'action_id' | 'invocation_id'>): string => {
  if (typeof state.invocation_id === 'string' && state.invocation_id) {
    return state.invocation_id;
  }
  return `${state.skill_name}::${state.action_id}`;
};

export const applyActionEventToStates = (
  currentStates: ActionState[],
  event: ChatEventEnvelope,
): ActionState[] => {
  if (!isSkillActionEvent(event)) return currentStates;
  const skillName = typeof event.skill_name === 'string' ? event.skill_name : '';
  const actionId = typeof event.action_id === 'string' ? event.action_id : '';
  const lifecycleStatus = typeof event.lifecycle_status === 'string' ? event.lifecycle_status : '';
  if (!skillName || !actionId || !lifecycleStatus) return currentStates;

  const invocationId = typeof event.invocation_id === 'string' ? event.invocation_id : '';
  const key = actionStateKey({ skill_name: skillName, action_id: actionId, invocation_id: invocationId });
  const nextMap = new Map(currentStates.map(state => [actionStateKey(state), state]));
  const legacyKey = `${skillName}::${actionId}`;
  const existing = nextMap.get(key) || (invocationId ? nextMap.get(legacyKey) : undefined);
  if (invocationId && key !== legacyKey) {
    nextMap.delete(legacyKey);
  }
  const eventTs = typeof event.ts === 'string' ? event.ts : undefined;
  const nextState: ActionState = {
    ...existing,
    skill_name: skillName,
    skill_version: typeof event.skill_version === 'string' ? event.skill_version : existing?.skill_version,
    action_id: actionId,
    invocation_id: invocationId || existing?.invocation_id,
    approval_token: typeof event.approval_token === 'string' ? event.approval_token : existing?.approval_token,
    request_id: typeof event.request_id === 'string' ? event.request_id : existing?.request_id,
    run_id: typeof event.run_id === 'string' ? event.run_id : existing?.run_id,
    assistant_turn_id: typeof event.assistant_turn_id === 'string' ? event.assistant_turn_id : existing?.assistant_turn_id,
    lifecycle_phase: typeof event.lifecycle_phase === 'string' ? event.lifecycle_phase : existing?.lifecycle_phase,
    lifecycle_status: lifecycleStatus,
    status: typeof event.status === 'string' ? event.status : existing?.status,
    payload: event,
    sequence: typeof event.sequence === 'number' ? event.sequence : existing?.sequence,
    ts: eventTs || existing?.ts,
    created_at: existing?.created_at || eventTs,
    updated_at: eventTs || existing?.updated_at,
  };
  nextMap.set(key, nextState);

  return [...nextMap.values()].sort((a, b) => {
    const seqA = typeof a.sequence === 'number' ? a.sequence : Number.MAX_SAFE_INTEGER;
    const seqB = typeof b.sequence === 'number' ? b.sequence : Number.MAX_SAFE_INTEGER;
    if (seqA !== seqB) return seqA - seqB;
    return (a.ts || '').localeCompare(b.ts || '');
  });
};

export const buildActionStatesFromEvents = (events: ChatEventEnvelope[]): ActionState[] => {
  const sorted = [...events].sort((a, b) => {
    const ka = eventSortKey(a);
    const kb = eventSortKey(b);
    if (ka.seq !== kb.seq) return ka.seq - kb.seq;
    return ka.ts.localeCompare(kb.ts);
  });
  return sorted.reduce<ActionState[]>((states, event) => applyActionEventToStates(states, event), []);
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
