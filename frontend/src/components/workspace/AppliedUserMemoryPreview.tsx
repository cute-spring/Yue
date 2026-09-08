import { For, Show } from 'solid-js';

import type { WorkspaceUnderstandingItem } from '../../types';

type AppliedUserMemoryPreviewProps = {
  items: WorkspaceUnderstandingItem[];
};

export default function AppliedUserMemoryPreview(props: AppliedUserMemoryPreviewProps) {
  return (
    <section class="rounded-lg border border-blue-200 bg-blue-50 p-3">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="text-[10px] font-black uppercase tracking-[0.16em] text-blue-600">About You</div>
          <h3 class="mt-1 text-sm font-black text-blue-950">Applied preferences</h3>
        </div>
        <span class="shrink-0 rounded-md border border-blue-200 bg-white px-2 py-0.5 text-[10px] font-bold text-blue-700">
          {props.items.length}
        </span>
      </div>

      <div class="mt-3 space-y-2">
        <Show
          when={props.items.length > 0}
          fallback={
            <p class="text-[12px] leading-5 text-blue-800">
              No cross-workspace preferences are applied here yet.
            </p>
          }
        >
          <For each={props.items.slice(0, 3)}>
            {(item) => (
              <div class="rounded-md border border-blue-100 bg-white px-2.5 py-2">
                <div class="truncate text-[12px] font-bold text-blue-950" title={item.title}>
                  {item.title}
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
