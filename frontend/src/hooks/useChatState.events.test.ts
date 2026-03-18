import { describe, it, expect } from 'vitest';
import { buildToolCallsFromEvents, normalizeStreamEvent, shouldAcceptEvent, shouldSkipHistoryFetch } from './useChatState';

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

  it('skips redundant history fetch within short interval', () => {
    expect(shouldSkipHistoryFetch(1000, 1500, 800)).toBe(true);
  });

  it('allows history fetch after interval threshold', () => {
    expect(shouldSkipHistoryFetch(1000, 1900, 800)).toBe(false);
  });
});
