import { test, expect } from '@playwright/test';

test('Tasks SSE stream returns task_event and task_result', async ({ page }) => {
  await page.goto('/');

  await page.waitForFunction(async () => {
    const res = await fetch('/api/chat/history');
    return res.ok;
  }, undefined, { timeout: 15000 });

  const summary = await page.evaluate(async () => {
    async function collectSse(url: string, payload: any, timeoutMs = 20000) {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

    const parentEvents = await collectSse(
      '/api/chat/stream',
      { message: 'parent', provider: '__guard__', model: 'guard' },
      15000,
    );
    const parentChatId = parentEvents.find((e: any) => typeof e.chat_id === 'string' && e.chat_id)?.chat_id as
      | string
      | undefined;
    if (!parentChatId) {
      throw new Error('missing_parent_chat_id');
    }

    const events = await collectSse(
      '/api/tasks/stream',
      {
        parent_chat_id: parentChatId,
        tasks: [{ prompt: 'ping', provider: '__guard__', model: 'guard' }],
      },
      20000,
    );

    const taskEvents = events.filter((e: any) => e.type === 'task_event');
    const started = taskEvents.some((e: any) => e.status === 'started');
    const running = taskEvents.some((e: any) => e.status === 'running');
    const completed = taskEvents.some((e: any) => e.status === 'completed');

    const final = events.filter((e: any) => e.type === 'task_result');
    const result = final.length ? final[final.length - 1].result : null;
    const output = result?.tasks?.[0]?.output || '';

    return {
      started,
      running,
      completed,
      hasResult: Boolean(result),
      okInOutput: typeof output === 'string' && output.includes('OK'),
    };
  });

  expect(summary.started).toBeTruthy();
  expect(summary.running).toBeTruthy();
  expect(summary.completed).toBeTruthy();
  expect(summary.hasResult).toBeTruthy();
  expect(summary.okInOutput).toBeTruthy();
});

