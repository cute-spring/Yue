import { For, Show, createEffect, createMemo, createSignal, onCleanup } from 'solid-js';
import type { ChatTraceBundle, ToolTraceRecord, TraceFieldPolicy } from '../types';

export const CHAT_TRACE_SHELL_TITLE = 'Trace Inspector';

type ChatTraceShellProps = {
  open: boolean;
  chatId: string | null;
  rawEnabled: boolean;
  onClose: () => void;
};

const formatJson = (value: unknown): string => {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const formatTimestamp = (value?: string | null): string => {
  if (!value) return '';
  return value.replace('T', ' ').replace('Z', ' UTC');
};

const formatBytes = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

const policyTone = (exposure: TraceFieldPolicy['exposure']): string => {
  if (exposure === 'raw_only') return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-emerald-100 text-emerald-700 border-emerald-200';
};

const normalizeTraceError = (status: number, detail?: string): string => {
  if (status === 404) return 'No saved trace summary is available for this chat yet.';
  if (status === 403) return detail || 'Trace access is currently restricted.';
  return detail || `HTTP ${status}`;
};

const statusTone = (status: ToolTraceRecord['status']): string => {
  if (status === 'success') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  if (status === 'error') return 'bg-rose-100 text-rose-700 border-rose-200';
  if (status === 'cancelled') return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

const buildTraceTree = (traces: ToolTraceRecord[]): Map<string | null, ToolTraceRecord[]> => {
  const tree = new Map<string | null, ToolTraceRecord[]>();
  for (const trace of traces) {
    const key = trace.parent_trace_id || null;
    const bucket = tree.get(key) || [];
    bucket.push(trace);
    tree.set(key, bucket);
  }
  for (const [, bucket] of tree) {
    bucket.sort((a, b) => a.call_index - b.call_index);
  }
  return tree;
};

function TraceTreeNode(props: {
  trace: ToolTraceRecord;
  tree: Map<string | null, ToolTraceRecord[]>;
  rawMode: boolean;
}) {
  const children = () => props.tree.get(props.trace.trace_id) || [];

  return (
    <li class="space-y-2">
      <div class="rounded-xl border border-border bg-surface px-4 py-3">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="text-sm font-semibold text-text-primary">{props.trace.tool_name}</div>
            <div class="text-xs text-text-secondary">
              #{props.trace.call_index} · depth {props.trace.chain_depth}
            </div>
          </div>
          <span class={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(props.trace.status)}`}>
            {props.trace.status}
          </span>
        </div>
        <div class="mt-2 grid grid-cols-2 gap-3 text-xs text-text-secondary">
          <div>
            <div class="uppercase tracking-wide">Trace</div>
            <div class="break-all text-text-primary">{props.trace.trace_id}</div>
          </div>
          <div>
            <div class="uppercase tracking-wide">Parent</div>
            <div class="break-all text-text-primary">{props.trace.parent_trace_id || '-'}</div>
          </div>
        </div>
        <Show when={props.rawMode}>
          <details class="mt-3 rounded-lg border border-border bg-background/70 px-3 py-2">
            <summary class="cursor-pointer text-xs font-medium text-text-primary">Raw payload</summary>
            <pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-text-secondary">
              {formatJson({
                input_arguments: props.trace.input_arguments,
                output_result: props.trace.output_result,
                error_type: props.trace.error_type,
                error_message: props.trace.error_message,
                error_stack: props.trace.error_stack,
              })}
            </pre>
          </details>
        </Show>
      </div>
      <Show when={children().length > 0}>
        <ul class="ml-4 space-y-2 border-l border-border pl-4">
          <For each={children()}>
            {(child) => <TraceTreeNode trace={child} tree={props.tree} rawMode={props.rawMode} />}
          </For>
        </ul>
      </Show>
    </li>
  );
}

export default function ChatTraceShell(props: ChatTraceShellProps) {
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
    if (props.rawEnabled) return;
    if (viewMode() === 'raw') {
      setViewMode('summary');
    }
  });

  createEffect(() => {
    const open = props.open;
    const chatId = props.chatId;
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
      headers: {
        Accept: 'application/json',
      },
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

  return (
    <Show when={props.open}>
      <div class="fixed inset-0 z-40 pointer-events-none" aria-hidden={!props.open}>
        <div class="absolute inset-0 bg-black/30 backdrop-blur-[2px] pointer-events-auto" onClick={props.onClose} />
        <aside
          class="absolute right-0 top-0 h-full w-full max-w-xl border-l border-border bg-surface shadow-2xl pointer-events-auto flex flex-col"
          role="dialog"
          aria-modal="true"
          aria-label={CHAT_TRACE_SHELL_TITLE}
        >
          <div class="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <p class="text-[11px] uppercase tracking-[0.24em] text-text-secondary font-semibold">Debug Surface</p>
              <h2 class="text-lg font-semibold text-text-primary">{CHAT_TRACE_SHELL_TITLE}</h2>
            </div>
            <div class="flex items-center gap-2">
              <button
                type="button"
                class={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                  viewMode() === 'summary'
                    ? 'border-primary bg-primary text-white'
                    : 'border-border text-text-secondary hover:bg-primary/10 hover:text-primary'
                }`}
                onClick={() => setViewMode('summary')}
                aria-pressed={viewMode() === 'summary'}
              >
                Summary
              </button>
              <Show when={props.rawEnabled}>
                <button
                  type="button"
                  class={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    viewMode() === 'raw'
                      ? 'border-primary bg-primary text-white'
                      : 'border-border text-text-secondary hover:bg-primary/10 hover:text-primary'
                  }`}
                  onClick={() => setViewMode('raw')}
                  aria-pressed={viewMode() === 'raw'}
                >
                  Raw
                </button>
              </Show>
              <button
                type="button"
                class="rounded-xl px-3 py-2 text-sm font-medium text-text-secondary hover:bg-primary/10 hover:text-primary transition-colors"
                onClick={props.onClose}
                aria-label="Close trace inspector"
              >
                Close
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-auto px-5 py-6 space-y-4">
            <Show when={loading()}>
              <div class="rounded-2xl border border-border bg-background/70 p-5 text-sm text-text-secondary" aria-live="polite">
                Loading trace summary...
              </div>
            </Show>

            <Show when={error()}>
              <div class="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700" aria-live="polite">
                {error()}
              </div>
            </Show>

            <Show when={bundle()}>
              {(resolvedBundle) => (
                <>
                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                          {viewMode() === 'raw' ? 'Raw Mode' : 'Summary Mode'}
                        </p>
                        <h3 class="text-base font-semibold text-text-primary">Latest Historical Run</h3>
                      </div>
                      <span class="rounded-full border border-border px-3 py-1 text-xs font-medium text-text-secondary">
                        {toolCountLabel()}
                      </span>
                    </div>
                    <div class="grid grid-cols-2 gap-3 text-sm">
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Request</div>
                        <div class="font-medium text-text-primary break-all">
                          {resolvedBundle().snapshot.request_id}
                        </div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Captured</div>
                        <div class="font-medium text-text-primary">
                          {formatTimestamp(resolvedBundle().snapshot.created_at) || '-'}
                        </div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Run</div>
                        <div class="font-medium text-text-primary break-all">{resolvedBundle().run_id}</div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Turn</div>
                        <div class="font-medium text-text-primary break-all">{resolvedBundle().assistant_turn_id}</div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Provider</div>
                        <div class="font-medium text-text-primary">{resolvedBundle().snapshot.provider || '-'}</div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Model</div>
                        <div class="font-medium text-text-primary">{resolvedBundle().snapshot.model || '-'}</div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Agent</div>
                        <div class="font-medium text-text-primary">{resolvedBundle().snapshot.agent_id || '-'}</div>
                      </div>
                      <div class="rounded-xl bg-surface px-3 py-2 border border-border">
                        <div class="text-text-secondary text-xs uppercase tracking-wide">Requested Skill</div>
                        <div class="font-medium text-text-primary">
                          {resolvedBundle().snapshot.requested_skill || '-'}
                        </div>
                      </div>
                    </div>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Request Snapshot
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">User Message</h3>
                    </div>
                    <div class="max-h-48 overflow-auto rounded-xl bg-surface px-4 py-3 border border-border text-sm text-text-primary whitespace-pre-wrap break-words">
                      {resolvedBundle().snapshot.user_message || '(empty)'}
                    </div>
                    <Show when={resolvedBundle().snapshot.redaction && Object.keys(resolvedBundle().snapshot.redaction).length > 0}>
                      <div class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                        Some request fields are redacted in summary mode.
                      </div>
                    </Show>
                    <Show when={viewMode() === 'raw'}>
                      <details class="rounded-xl border border-border bg-surface px-4 py-3">
                        <summary class="cursor-pointer text-sm font-medium text-text-primary">System Prompt</summary>
                        <pre class="mt-3 max-h-48 overflow-auto text-xs text-text-secondary whitespace-pre-wrap">
                          {resolvedBundle().snapshot.system_prompt || '(empty)'}
                        </pre>
                      </details>
                    </Show>
                    <details class="rounded-xl border border-border bg-surface px-4 py-3">
                      <summary class="cursor-pointer text-sm font-medium text-text-primary">Runtime Flags</summary>
                      <pre class="mt-3 max-h-48 overflow-auto text-xs text-text-secondary whitespace-pre-wrap">{formatJson(resolvedBundle().snapshot.runtime_flags)}</pre>
                    </details>
                    <details class="rounded-xl border border-border bg-surface px-4 py-3">
                      <summary class="cursor-pointer text-sm font-medium text-text-primary">Tool Context</summary>
                      <pre class="mt-3 max-h-48 overflow-auto text-xs text-text-secondary whitespace-pre-wrap">{formatJson(resolvedBundle().snapshot.tool_context)}</pre>
                    </details>
                    <details class="rounded-xl border border-border bg-surface px-4 py-3">
                      <summary class="cursor-pointer text-sm font-medium text-text-primary">Skill Context</summary>
                      <pre class="mt-3 max-h-48 overflow-auto text-xs text-text-secondary whitespace-pre-wrap">{formatJson(resolvedBundle().snapshot.skill_context)}</pre>
                    </details>
                    <details class="rounded-xl border border-border bg-surface px-4 py-3">
                      <summary class="cursor-pointer text-sm font-medium text-text-primary">Truncation Metadata</summary>
                      <pre class="mt-3 max-h-48 overflow-auto text-xs text-text-secondary whitespace-pre-wrap">{formatJson(resolvedBundle().snapshot.truncation)}</pre>
                    </details>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Trace Tree
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">Parent-child call structure</h3>
                    </div>
                    <Show
                      when={rootTraces().length > 0}
                      fallback={
                        <div class="rounded-xl border border-dashed border-border px-4 py-5 text-sm text-text-secondary">
                          No rooted trace tree is available for this run.
                        </div>
                      }
                    >
                      <ul class="space-y-3">
                        <For each={rootTraces()}>
                          {(trace) => (
                            <TraceTreeNode trace={trace} tree={traceTree()} rawMode={viewMode() === 'raw'} />
                          )}
                        </For>
                      </ul>
                    </Show>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Request History
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">Conversation Inputs</h3>
                    </div>
                    <Show
                      when={resolvedBundle().snapshot.message_history.length > 0}
                      fallback={
                        <div class="rounded-xl border border-dashed border-border px-4 py-5 text-sm text-text-secondary">
                          No summarized message history was captured for this request.
                        </div>
                      }
                    >
                      <div class="space-y-3">
                        <For each={resolvedBundle().snapshot.message_history}>
                          {(item, index) => (
                            <article class="rounded-xl border border-border bg-surface px-4 py-4 space-y-2">
                              <div class="flex items-start justify-between gap-4">
                                <div>
                                  <div class="text-sm font-semibold text-text-primary">
                                    #{index() + 1} {item.role}
                                  </div>
                                  <div class="text-xs text-text-secondary uppercase tracking-wide">
                                    {item.content_type}
                                  </div>
                                </div>
                                <div class="flex items-center gap-2">
                                  <Show when={item.image_count > 0}>
                                    <span class="rounded-full border border-border px-2.5 py-1 text-xs font-medium text-text-secondary">
                                      {item.image_count} image{item.image_count === 1 ? '' : 's'}
                                    </span>
                                  </Show>
                                  <Show when={item.truncated}>
                                    <span class="rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                                      truncated
                                    </span>
                                  </Show>
                                </div>
                              </div>
                              <div class="max-h-36 overflow-auto text-sm text-text-secondary whitespace-pre-wrap break-words">
                                {item.content_summary || '(no summary available)'}
                              </div>
                            </article>
                          )}
                        </For>
                      </div>
                    </Show>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Attachments
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">Captured Inputs</h3>
                    </div>
                    <Show
                      when={resolvedBundle().snapshot.attachments.length > 0}
                      fallback={
                        <div class="rounded-xl border border-dashed border-border px-4 py-5 text-sm text-text-secondary">
                          No attachments were captured for this request.
                        </div>
                      }
                    >
                      <div class="space-y-3">
                        <For each={resolvedBundle().snapshot.attachments}>
                          {(attachment, index) => (
                            <article class="rounded-xl border border-border bg-surface px-4 py-4 space-y-2">
                              <div class="flex items-start justify-between gap-4">
                                <div>
                                  <div class="text-sm font-semibold text-text-primary">
                                    #{index() + 1} {attachment.name || attachment.kind}
                                  </div>
                                  <div class="text-xs text-text-secondary uppercase tracking-wide">
                                    {attachment.content_type || attachment.kind}
                                  </div>
                                </div>
                                <Show when={attachment.redacted}>
                                  <span class="rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800">
                                    redacted
                                  </span>
                                </Show>
                              </div>
                              <div class="grid grid-cols-2 gap-3 text-xs text-text-secondary">
                                <div>
                                  <div class="uppercase tracking-wide">Kind</div>
                                  <div class="text-text-primary">{attachment.kind}</div>
                                </div>
                                <div>
                                  <div class="uppercase tracking-wide">Size</div>
                                  <div class="text-text-primary">{formatBytes(attachment.size_bytes)}</div>
                                </div>
                              </div>
                            </article>
                          )}
                        </For>
                      </div>
                    </Show>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Field Exposure
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">Summary View Policy</h3>
                    </div>
                    <Show
                      when={resolvedBundle().field_policies.length > 0}
                      fallback={
                        <div class="rounded-xl border border-dashed border-border px-4 py-5 text-sm text-text-secondary">
                          No field exposure policy metadata is available.
                        </div>
                      }
                    >
                      <div class="space-y-3">
                        <For each={resolvedBundle().field_policies}>
                          {(policy) => (
                            <article class="rounded-xl border border-border bg-surface px-4 py-4 space-y-2">
                              <div class="flex items-start justify-between gap-4">
                                <div class="text-sm font-semibold text-text-primary break-all">{policy.field_name}</div>
                                <span class={`rounded-full border px-2.5 py-1 text-xs font-semibold ${policyTone(policy.exposure)}`}>
                                  {policy.exposure}
                                </span>
                              </div>
                              <div class="text-sm text-text-secondary">
                                {policy.reason || 'No additional reason was provided for this exposure rule.'}
                              </div>
                            </article>
                          )}
                        </For>
                      </div>
                    </Show>
                  </section>

                  <section class="rounded-2xl border border-border bg-background/70 p-5 space-y-3">
                    <div>
                      <p class="text-[11px] uppercase tracking-[0.2em] text-text-secondary font-semibold">
                        Tool Trace
                      </p>
                      <h3 class="text-base font-semibold text-text-primary">Read-only Summary</h3>
                    </div>
                    <Show
                      when={resolvedBundle().tool_traces.length > 0}
                      fallback={
                        <div class="rounded-xl border border-dashed border-border px-4 py-5 text-sm text-text-secondary">
                          No tool calls were recorded for this run.
                        </div>
                      }
                    >
                      <div class="space-y-3">
                        <For each={resolvedBundle().tool_traces}>
                          {(trace) => (
                            <article class="rounded-xl border border-border bg-surface px-4 py-4 space-y-3">
                              <div class="flex items-start justify-between gap-4">
                                <div>
                                  <div class="text-sm font-semibold text-text-primary">{trace.tool_name}</div>
                                  <div class="text-xs text-text-secondary">
                                    #{trace.call_index} {trace.call_id ? `· ${trace.call_id}` : ''}
                                  </div>
                                </div>
                                <span class={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(trace.status)}`}>
                                  {trace.status}
                                </span>
                              </div>
                              <div class="grid grid-cols-2 gap-3 text-xs text-text-secondary">
                                <div>
                                  <div class="uppercase tracking-wide">Started</div>
                                  <div class="text-text-primary">{formatTimestamp(trace.started_at) || '-'}</div>
                                </div>
                                <div>
                                  <div class="uppercase tracking-wide">Finished</div>
                                  <div class="text-text-primary">{formatTimestamp(trace.finished_at) || '-'}</div>
                                </div>
                                <div>
                                  <div class="uppercase tracking-wide">Duration</div>
                                  <div class="text-text-primary">{trace.duration_ms != null ? `${Math.round(trace.duration_ms)} ms` : '-'}</div>
                                </div>
                                <div>
                                  <div class="uppercase tracking-wide">Depth</div>
                                  <div class="text-text-primary">{trace.chain_depth}</div>
                                </div>
                              </div>
                              <Show when={trace.error_message}>
                                <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                                  {trace.error_message}
                                </div>
                              </Show>
                              <Show when={viewMode() === 'raw'}>
                                <details class="rounded-lg border border-border bg-background/70 px-3 py-2">
                                  <summary class="cursor-pointer text-sm font-medium text-text-primary">Raw tool payload</summary>
                                  <pre class="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-text-secondary">
                                    {formatJson({
                                      input_arguments: trace.input_arguments,
                                      output_result: trace.output_result,
                                      error_type: trace.error_type,
                                      error_message: trace.error_message,
                                      error_stack: trace.error_stack,
                                      raw_event_id: trace.raw_event_id,
                                    })}
                                  </pre>
                                </details>
                              </Show>
                            </article>
                          )}
                        </For>
                      </div>
                    </Show>
                  </section>
                </>
              )}
            </Show>
          </div>

          <div class="border-t border-border px-5 py-3 text-xs text-text-secondary">
            Read-only historical trace view. This panel does not retry, re-run, or modify any chat execution.
          </div>
        </aside>
      </div>
    </Show>
  );
}
