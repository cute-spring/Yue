import { createRoot, createSignal } from 'solid-js';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { WorkspaceUnderstandingSummary } from '../../../types';
import { useWorkspaceUnderstanding } from './useWorkspaceUnderstanding';

const originalFetch = globalThis.fetch;
const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

const makeSummary = (workspaceId: string): WorkspaceUnderstandingSummary => ({
  workspace_id: workspaceId,
  groups: [
    {
      group: 'background',
      label: 'Background',
      total_count: 1,
      active_count: 1,
      pending_count: 0,
      representative_items: [
        {
          id: `mem-${workspaceId}`,
          kind: 'memory',
          title: 'Project background',
          content: 'Yue should remember durable workspace context.',
          status: 'active',
          memory_type: 'project_fact',
          scope_type: 'workspace',
          updated_at: '2026-09-07T00:00:00Z',
        },
      ],
    },
  ],
  applied_user_memory_preview: [],
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe('useWorkspaceUnderstanding', () => {
  it('loads the selected workspace understanding summary', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(makeSummary('ws_1')))) as typeof fetch;

    await createRoot(async (dispose) => {
      const [selectedWorkspaceId] = createSignal<string | null>('ws_1');
      const state = useWorkspaceUnderstanding({ selectedWorkspaceId });

      await state.refreshWorkspaceUnderstanding();

      expect(globalThis.fetch).toHaveBeenCalledWith('/api/workspaces/ws_1/understanding');
      expect(state.workspaceUnderstanding()?.workspace_id).toBe('ws_1');
      expect(state.workspaceUnderstandingLoading()).toBe(false);
      expect(state.workspaceUnderstandingError()).toBeNull();
      dispose();
    });
  });

  it('resets state when refresh is called without a workspace', async () => {
    globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(makeSummary('ws_1')))) as typeof fetch;

    await createRoot(async (dispose) => {
      const [selectedWorkspaceId] = createSignal<string | null>('ws_1');
      const state = useWorkspaceUnderstanding({ selectedWorkspaceId });

      await state.refreshWorkspaceUnderstanding();
      expect(state.workspaceUnderstanding()?.workspace_id).toBe('ws_1');

      // Vitest resolves Solid to the server build in this repo, so signal-driven
      // effect reruns are covered through the hook's public refresh seam here.
      await state.refreshWorkspaceUnderstanding(null);

      expect(state.workspaceUnderstanding()).toBeNull();
      expect(state.workspaceUnderstandingLoading()).toBe(false);
      expect(state.workspaceUnderstandingError()).toBeNull();
      dispose();
    });
  });

  it('exposes error state when loading fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    globalThis.fetch = vi.fn(async () => new Response('missing', { status: 404 })) as typeof fetch;

    await createRoot(async (dispose) => {
      const [selectedWorkspaceId] = createSignal<string | null>('missing');
      const state = useWorkspaceUnderstanding({ selectedWorkspaceId });

      await state.refreshWorkspaceUnderstanding();

      expect(state.workspaceUnderstanding()).toBeNull();
      expect(state.workspaceUnderstandingLoading()).toBe(false);
      expect(state.workspaceUnderstandingError()).toBe('HTTP 404');
      expect(consoleError).toHaveBeenCalled();
      dispose();
    });
  });

  it('keeps stale responses from replacing the latest workspace summary', async () => {
    let resolveFirst: ((response: Response) => void) | undefined;
    globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('ws_slow')) {
        return new Promise<Response>((resolve) => {
          resolveFirst = resolve;
        });
      }
      return Promise.resolve(new Response(JSON.stringify(makeSummary('ws_fast'))));
    }) as typeof fetch;

    await createRoot(async (dispose) => {
      const [selectedWorkspaceId] = createSignal<string | null>('ws_slow');
      const state = useWorkspaceUnderstanding({ selectedWorkspaceId });

      const slowRequest = state.refreshWorkspaceUnderstanding();
      await flush();
      await state.refreshWorkspaceUnderstanding('ws_fast');

      expect(state.workspaceUnderstanding()?.workspace_id).toBe('ws_fast');

      resolveFirst?.(new Response(JSON.stringify(makeSummary('ws_slow'))));
      await slowRequest;
      await flush();

      expect(state.workspaceUnderstanding()?.workspace_id).toBe('ws_fast');
      dispose();
    });
  });
});
