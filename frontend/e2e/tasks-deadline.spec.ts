import { test, expect } from '@playwright/test';

test('Tasks SSE deadline: task fails with deadline_exceeded', async ({ page }) => {
  await page.goto('/');

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

    const taskId = `deadline-${Date.now()}`;
    const deadlineTs = Date.now() / 1000 + 0.05;

    const events = await collectSse(
      '/api/tasks/stream',
      {
        parent_chat_id: parentChatId,
        tasks: [{ id: taskId, prompt: 'slow', provider: '__slow__', model: 'slow', deadline_ts: deadlineTs }],
      },
      20000,
    );

    const taskEvents = events.filter((e: any) => e.type === 'task_event' && e.task_id === taskId);
    const failed = taskEvents.some((e: any) => e.status === 'failed' && e.error === 'deadline_exceeded');

    const finals = events.filter((e: any) => e.type === 'task_result');
    const result = finals.length ? finals[finals.length - 1].result : null;
    const t0 = result?.tasks?.[0];

    return {
      failed,
      finalStatus: t0?.status,
      finalError: t0?.error,
    };
  });

  expect(summary.failed).toBeTruthy();
  expect(summary.finalStatus).toBe('failed');
  expect(summary.finalError).toBe('deadline_exceeded');
});

