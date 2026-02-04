import { test, expect } from '@playwright/test';

test('Chat SSE includes trace_id and propagates to task_event', async ({ page }) => {
  await page.goto('/');

  const summary = await page.evaluate(async () => {
    async function collectSse(url: string, payload: any, headers: Record<string, string>, timeoutMs = 20000) {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify(payload),
      });
      if (!res.ok || !res.body) {
        throw new Error(`bad_response:${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      const events: any[] = [];
      let buf = '';
      const start = Date.now();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data && typeof data === 'object') {
              events.push(data);
            }
          } catch {}
        }
        if (Date.now() - start > timeoutMs) break;
      }
      return events;
    }

    const traceId = `trace-e2e-${Date.now()}`;
    const events = await collectSse(
      '/api/chat/stream',
      { message: 'Obsidian 插件', agent_id: 'builtin-doc-orchestrator', provider: '__docmain__', model: 'docmain' },
      { 'X-Request-Id': traceId },
      25000,
    );

    const firstTraceId = events.find((e: any) => typeof e.trace_id === 'string' && e.trace_id)?.trace_id as string | undefined;
    const taskEvents = events.filter((e: any) => e.type === 'task_event');
    const uniqueTaskTraceIds = Array.from(new Set(taskEvents.map((e: any) => e.trace_id).filter(Boolean)));
    const citationsEvent = events.find((e: any) => Array.isArray(e.citations));
    const citations = citationsEvent?.citations || [];

    return {
      traceId,
      firstTraceId,
      taskEventsCount: taskEvents.length,
      uniqueTaskTraceIds,
      citationsCount: Array.isArray(citations) ? citations.length : 0,
    };
  });

  expect(summary.firstTraceId).toBe(summary.traceId);
  expect(summary.taskEventsCount).toBeGreaterThan(0);
  expect(summary.uniqueTaskTraceIds).toEqual([summary.traceId]);
  expect(summary.citationsCount).toBeGreaterThan(0);
});

