import { For, Show } from 'solid-js';
import type { ToolTraceRecord } from '../../types';
import { formatJson, statusTone } from './traceFormatting';

export function TraceTreeNode(props: {
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
