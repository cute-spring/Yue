import { describe, it, expect } from 'vitest';
import {
  applyActionEventToStates,
  buildActionStatesFromEvents,
  buildToolCallsFromEvents,
  normalizeStreamEvent,
  runEditQuestionFlow,
  shouldAcceptEvent,
  shouldSkipHistoryFetch,
} from './useChatState';

describe('useChatState event helpers', () => {
  it('dedupes by event_id for reconnect duplicates', () => {
    const seen = new Set<string>();
    const event = { version: 'v2', event_id: 'evt_1', event: 'tool.call.started', call_id: 'call_1' };
    expect(shouldAcceptEvent(seen, event)).toBe(true);
    expect(shouldAcceptEvent(seen, event)).toBe(false);
  });

  it('normalizes v2 envelope with payload fields', () => {
    const normalized = normalizeStreamEvent({
      version: 'v2',
      event_id: 'evt_meta_1',
      event: 'meta',
      payload: {
        meta: {
          reasoning_enabled: true
        }
      }
    });
    expect(normalized.meta?.reasoning_enabled).toBe(true);
    expect(normalized.event_id).toBe('evt_meta_1');
  });

  it('orders out-of-order tool events by sequence and merges final status', () => {
    const events = [
      { event: 'tool.call.finished', event_id: 'evt_2', sequence: 20, ts: '2026-03-15T10:00:02Z', call_id: 'call_1', tool_name: 'docs_search', result: 'ok' },
      { event: 'tool.call.started', event_id: 'evt_1', sequence: 10, ts: '2026-03-15T10:00:01Z', call_id: 'call_1', tool_name: 'docs_search', args: { q: 'reasoning' } }
    ];
    const merged = buildToolCallsFromEvents(events);
    expect(merged).toHaveLength(1);
    expect(merged[0].call_id).toBe('call_1');
    expect(merged[0].status).toBe('success');
    expect(merged[0].sequence).toBe(20);
    expect(merged[0].args).toEqual({ q: 'reasoning' });
  });

  it('builds current action states from skill action events', () => {
    const events = [
      {
        event: 'skill.action.result',
        event_id: 'evt_1',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
        skill_name: 'action-skill',
        action_id: 'generate',
        invocation_id: 'invoke:action-skill:1.0.0:generate:req-1',
        lifecycle_phase: 'preflight',
        lifecycle_status: 'preflight_approval_required',
        status: 'approval_required',
      },
      {
        event: 'skill.action.result',
        event_id: 'evt_2',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
        skill_name: 'action-skill',
        action_id: 'generate',
        invocation_id: 'invoke:action-skill:1.0.0:generate:req-1',
        lifecycle_phase: 'execution',
        lifecycle_status: 'awaiting_approval',
        status: 'awaiting_approval',
        approval_token: 'approval:token',
      }
    ];
    const states = buildActionStatesFromEvents(events);
    expect(states).toHaveLength(1);
    expect(states[0].lifecycle_status).toBe('awaiting_approval');
    expect(states[0].approval_token).toBe('approval:token');
    expect(states[0].invocation_id).toBe('invoke:action-skill:1.0.0:generate:req-1');
    expect(states[0].payload?.event).toBe('skill.action.result');
  });

  it('applies later action events as in-place state updates', () => {
    const initial = [
      {
        skill_name: 'action-skill',
        action_id: 'generate',
        invocation_id: 'invoke:action-skill:1.0.0:generate:req-1',
        lifecycle_status: 'awaiting_approval',
        status: 'awaiting_approval',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      }
    ];
    const next = applyActionEventToStates(initial, {
      event: 'skill.action.result',
      event_id: 'evt_3',
      sequence: 30,
      ts: '2026-03-28T10:00:03Z',
      skill_name: 'action-skill',
      action_id: 'generate',
      invocation_id: 'invoke:action-skill:1.0.0:generate:req-1',
      lifecycle_phase: 'execution',
      lifecycle_status: 'skipped',
      status: 'skipped',
    });
    expect(next).toHaveLength(1);
    expect(next[0].lifecycle_status).toBe('skipped');
    expect(next[0].sequence).toBe(30);
  });

  it('keeps separate states for separate invocation ids of the same action', () => {
    const states = buildActionStatesFromEvents([
      {
        event: 'skill.action.result',
        event_id: 'evt_1',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
        skill_name: 'action-skill',
        action_id: 'generate',
        invocation_id: 'invoke:action-skill:1.0.0:generate:req-1',
        lifecycle_phase: 'execution',
        lifecycle_status: 'skipped',
        status: 'skipped',
      },
      {
        event: 'skill.action.result',
        event_id: 'evt_2',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
        skill_name: 'action-skill',
        action_id: 'generate',
        invocation_id: 'invoke:action-skill:1.0.0:generate:req-2',
        lifecycle_phase: 'execution',
        lifecycle_status: 'succeeded',
        status: 'succeeded',
      },
    ]);

    expect(states).toHaveLength(2);
    expect(states.map((state) => state.invocation_id)).toEqual([
      'invoke:action-skill:1.0.0:generate:req-1',
      'invoke:action-skill:1.0.0:generate:req-2',
    ]);
  });

  it('skips redundant history fetch within short interval', () => {
    expect(shouldSkipHistoryFetch(1000, 1500, 800)).toBe(true);
  });

  it('allows history fetch after interval threshold', () => {
    expect(shouldSkipHistoryFetch(1000, 1900, 800)).toBe(false);
  });
});

describe('handleEditQuestion flow', () => {
  it('truncates then submits edited text when truncate succeeds', async () => {
    const calls: string[] = [];
    const fetchCalls: Array<{ url: string; body: any }> = [];
    const messages = [
      { role: 'user', content: 'Q1' },
      { role: 'assistant', content: 'A1' },
      { role: 'user', content: 'Q2' },
      { role: 'assistant', content: 'A2' },
    ];

    await runEditQuestionFlow({
      index: 2,
      newContent: '  Edited Q2  ',
      isTyping: false,
      currentMessages: messages,
      currentChatId: 'chat-1',
      fetchImpl: async (url, init) => {
        fetchCalls.push({ url: String(url), body: JSON.parse(String(init?.body || '{}')) });
        return new Response(JSON.stringify({ status: 'success' }), { status: 200 });
      },
      truncateLocalMessages: (keepCount) => calls.push(`truncate:${keepCount}`),
      setInputText: (value) => calls.push(`input:${value}`),
      submitEditedQuestion: async () => {
        calls.push('submit');
      },
    });

    expect(fetchCalls).toEqual([
      {
        url: '/api/chat/chat-1/truncate',
        body: { keep_count: 2 },
      },
    ]);
    expect(calls).toEqual(['truncate:2', 'input:Edited Q2', 'submit']);
  });

  it('throws and does not mutate local state when truncate returns non-ok', async () => {
    const calls: string[] = [];

    await expect(
      runEditQuestionFlow({
        index: 2,
        newContent: 'Edited',
        isTyping: false,
        currentMessages: [
          { role: 'user', content: 'Q1' },
          { role: 'assistant', content: 'A1' },
          { role: 'user', content: 'Q2' },
        ],
        currentChatId: 'chat-1',
        fetchImpl: async () => new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }),
        truncateLocalMessages: () => calls.push('truncate'),
        setInputText: () => calls.push('input'),
        submitEditedQuestion: async () => {
          calls.push('submit');
        },
      }),
    ).rejects.toThrow();

    expect(calls).toEqual([]);
  });

  it('throws on fetch rejection and does not submit', async () => {
    const calls: string[] = [];

    await expect(
      runEditQuestionFlow({
        index: 0,
        newContent: 'Edited',
        isTyping: false,
        currentMessages: [{ role: 'user', content: 'Q1' }],
        currentChatId: 'chat-1',
        fetchImpl: async () => {
          throw new Error('network');
        },
        truncateLocalMessages: () => calls.push('truncate'),
        setInputText: () => calls.push('input'),
        submitEditedQuestion: async () => {
          calls.push('submit');
        },
      }),
    ).rejects.toThrow('network');

    expect(calls).toEqual([]);
  });
});
