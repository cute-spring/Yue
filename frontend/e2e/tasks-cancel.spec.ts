import { test, expect } from '@playwright/test';

test('Tasks SSE cancel stops a running task', async ({ page }) => {
  await page.goto('/');

  const summary = await page.evaluate(async () => {
    async function collectSse(url: string, payload: any, timeoutMs = 20000, onEvent?: (e: any) => Promise<void>) {
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
              if (onEvent) {
                await onEvent(data);
              }
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

    const taskId = `cancel-${Date.now()}`;
    let cancelled = false;
    let sawFailed = false;
    let finalError: string | undefined;

    await collectSse(
      '/api/tasks/stream',
      { parent_chat_id: parentChatId, tasks: [{ id: taskId, prompt: 'slow', provider: '__slow__', model: 'slow' }] },
      20000,
      async (evt) => {
        if (evt?.type === 'task_event' && evt.task_id === taskId && evt.status === 'started' && !cancelled) {
          cancelled = true;
          await fetch('/api/tasks/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ parent_chat_id: parentChatId, task_id: taskId }),
          });
        }
        if (evt?.type === 'task_event' && evt.task_id === taskId && evt.status === 'failed') {
          sawFailed = true;
          finalError = evt.error;
        }
      },
    );

    return { cancelled, sawFailed, finalError };
  });

  expect(summary.cancelled).toBeTruthy();
  expect(summary.sawFailed).toBeTruthy();
  expect(summary.finalError).toBe('cancelled');
});

