import { For, Show } from 'solid-js';

import type { WorkspaceUnderstandingGroup } from '../../types';

type WorkspaceUnderstandingGroupCardProps = {
  group: WorkspaceUnderstandingGroup;
  onReview?: (group: WorkspaceUnderstandingGroup) => void;
};

const formatItemState = (kind: string, status: string) => {
  if (kind === 'candidate') return 'Pending';
  switch (status) {
    case 'active':
      return 'Saved';
    case 'disabled':
      return 'Disabled';
    case 'archived':
      return 'Archived';
    case 'superseded':
      return 'Superseded';
    default:
      return status ? status.replace(/[_-]+/g, ' ') : 'Saved';
  }
};

const itemStateClass = (kind: string, status: string) => {
  if (kind === 'candidate') return 'bg-amber-50 text-amber-700';
  if (status === 'disabled' || status === 'archived' || status === 'superseded') {
    return 'bg-slate-200 text-slate-600';
  }
  return 'bg-white text-slate-500';
};

export default function WorkspaceUnderstandingGroupCard(props: WorkspaceUnderstandingGroupCardProps) {
  const hasItems = () => props.group.representative_items.length > 0;

  return (
    <section class="min-h-[128px] rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="truncate text-[13px] font-black text-slate-900" title={props.group.label}>
            {props.group.label}
          </h3>
          <div class="mt-1 flex flex-wrap gap-1.5">
            <span class="rounded-md border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
              {props.group.total_count} saved
            </span>
            <Show when={props.group.pending_count > 0}>
              <span class="rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">
                {props.group.pending_count} pending
              </span>
            </Show>
          </div>
        </div>
        <button
          type="button"
          onClick={() => props.onReview?.(props.group)}
          class="shrink-0 rounded-md border border-slate-200 bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800"
          title={`Review ${props.group.label}`}
        >
          Review
        </button>
      </div>

      <div class="mt-3 space-y-1.5">
        <Show
          when={hasItems()}
          fallback={<p class="text-[12px] leading-5 text-slate-400">Nothing saved here yet.</p>}
        >
          <For each={props.group.representative_items.slice(0, 2)}>
            {(item) => (
              <div class="rounded-md border border-slate-100 bg-slate-50 px-2.5 py-2">
                <div class="flex items-center justify-between gap-2">
                  <span class="truncate text-[12px] font-bold text-slate-800" title={item.title}>
                    {item.title}
                  </span>
                  <span
                    class={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${itemStateClass(item.kind, item.status)}`}
                  >
                    {formatItemState(item.kind, item.status)}
                  </span>
                </div>
                <p class="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-600">{item.content}</p>
              </div>
            )}
          </For>
        </Show>
      </div>
    </section>
  );
}
