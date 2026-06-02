import { createEffect, createMemo, createSignal, onCleanup } from 'solid-js';
import type { ChatTraceBundle } from '../../types';
import { buildTraceTree, normalizeTraceError } from './traceFormatting';

type UseChatTraceBundleOptions = {
  open: boolean;
  chatId: string | null;
  rawEnabled: boolean;
};

export function useChatTraceBundle(options: UseChatTraceBundleOptions) {
  const [bundle, setBundle] = createSignal<ChatTraceBundle | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);
  const [viewMode, setViewMode] = createSignal<'summary' | 'raw'>('summary');
  let requestSeq = 0;

  const toolCountLabel = createMemo(() => {
    const count = bundle()?.tool_traces.length || 0;
    return `${count} tool call${count === 1 ? '' : 's'}`;
  });

  const traceTree = createMemo(() => buildTraceTree(bundle()?.tool_traces || []));
  const rootTraces = createMemo(() => traceTree().get(null) || []);

  createEffect(() => {
    if (options.rawEnabled) return;
    if (viewMode() === 'raw') setViewMode('summary');
  });

  createEffect(() => {
    const open = options.open;
    const chatId = options.chatId;
    const mode = viewMode();
    if (!open) {
      setBundle(null);
      setLoading(false);
      setError(null);
      return;
    }
    if (!chatId) {
      setBundle(null);
      setError('Open an existing chat to inspect its trace summary.');
      setLoading(false);
      return;
    }

    const current = ++requestSeq;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setBundle(null);
    onCleanup(() => controller.abort());

    const search = new URLSearchParams({ mode });
    void fetch(`/api/chat/${encodeURIComponent(chatId)}/trace/bundle?${search.toString()}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
      .then(async (res) => {
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}));
          throw new Error(normalizeTraceError(res.status, payload?.detail));
        }
        return res.json();
      })
      .then((data: ChatTraceBundle) => {
        if (current !== requestSeq) return;
        setBundle(data);
      })
      .catch((err) => {
        if (current !== requestSeq) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setBundle(null);
        setError(err instanceof Error ? err.message : 'Failed to load trace summary');
      })
      .finally(() => {
        if (current !== requestSeq) return;
        setLoading(false);
      });
  });

  return {
    bundle,
    loading,
    error,
    viewMode,
    setViewMode,
    toolCountLabel,
    traceTree,
    rootTraces,
  };
}
