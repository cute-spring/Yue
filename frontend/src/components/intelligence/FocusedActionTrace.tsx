import { For, Show } from 'solid-js';

import { ActionState } from '../../types';
import {
  ActionDetailSection,
  canResolveActionState,
  getActionDetailClasses,
  getActionStateArgs,
  getActionStateLabel,
  getActionStateTimestampLabel,
  getActionStateTone,
  getActionStateTraceIdentity,
  getActionStateTracePayload,
  getActionToneClasses,
} from './actionHelpers';

interface FocusedActionTraceProps {
  action: ActionState | null;
  copiedTraceKey: string | null;
  onCopyTrace: () => void | Promise<void>;
  onClearFocus: () => void;
  onResolveAction: (state: ActionState, approved: boolean) => void;
  isTyping: boolean;
  detailSections?: ActionDetailSection[];
}

export default function FocusedActionTrace(props: FocusedActionTraceProps) {
  return (
    <Show when={props.action}>
      {(focusedAction) => {
        const focused = focusedAction();
        const focusedTone = getActionStateTone(focused);
        const focusedArgs = getActionStateArgs(focused);
        const focusedSections = () => props.detailSections || [];
        const focusedIdentity = getActionStateTraceIdentity(focused);
        return (
          <div class="rounded-[1.6rem] border border-primary/18 bg-gradient-to-br from-primary/5 via-surface to-surface p-5 shadow-sm">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-[11px] font-medium text-primary">Focused Trace</div>
                <div class="mt-2 text-[15px] font-semibold text-text-primary break-all leading-snug">
                  {focused.skill_name}.{focused.action_id}
                </div>
                <div class="mt-1.5 font-mono text-[12px] text-text-secondary">
                  {focusedIdentity.label}
                </div>
              </div>
              <div class="flex flex-wrap justify-end gap-2">
                <span class={`rounded-full border px-3 py-1.5 text-[11px] font-semibold ${getActionToneClasses(focusedTone)}`}>
                  {getActionStateLabel(focused)}
                </span>
                <button
                  class="rounded-full border border-border bg-surface px-3.5 py-1.5 text-[11px] font-medium text-text-secondary transition-all hover:text-text-primary"
                  onClick={() => void props.onCopyTrace()}
                >
                  {props.copiedTraceKey === focusedIdentity.key ? 'Trace Copied' : 'Copy Trace'}
                </button>
                <button
                  class="rounded-full border border-border bg-surface px-3.5 py-1.5 text-[11px] font-medium text-text-secondary transition-all hover:text-text-primary"
                  onClick={props.onClearFocus}
                >
                  Clear Focus
                </button>
              </div>
            </div>
            <div class="mt-4 flex flex-wrap gap-2 text-[11px] font-medium text-text-secondary">
              <Show when={focused.skill_version}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">v{focused.skill_version}</span>
              </Show>
              <Show when={focused.lifecycle_phase}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">phase: {focused.lifecycle_phase}</span>
              </Show>
              <Show when={focused.sequence != null}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">seq: {focused.sequence}</span>
              </Show>
              <Show when={getActionStateTimestampLabel(focused)}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">
                  updated: {getActionStateTimestampLabel(focused)}
                </span>
              </Show>
              <Show when={focused.request_id}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">request: {focused.request_id}</span>
              </Show>
              <Show when={focused.approval_token}>
                <span class="rounded-full border border-border/80 bg-background px-2.5 py-1">approval token attached</span>
              </Show>
            </div>
            <Show when={focusedArgs}>
              <div class="mt-4 rounded-xl border border-border/80 bg-background/80 p-3.5">
                <div class="text-[11px] font-medium text-text-secondary">Tool Arguments</div>
                <pre class="mt-2.5 whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-primary">{JSON.stringify(focusedArgs, null, 2)}</pre>
              </div>
            </Show>
            <Show when={focusedSections().length > 0}>
              <div class="mt-4 space-y-3">
                <For each={focusedSections()}>
                  {(section) => (
                    <div class={`rounded-xl border p-3.5 ${getActionDetailClasses(section.tone)}`}>
                      <div class="text-[11px] font-medium text-text-secondary">{section.title}</div>
                      <Show
                        when={section.kind === 'image' && section.href}
                        fallback={
                          <Show
                            when={section.kind === 'link' && section.href}
                            fallback={
                              <pre class="mt-2.5 whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-primary">{section.content}</pre>
                            }
                          >
                            <a
                              href={section.href}
                              target="_blank"
                              rel="noreferrer"
                              class="mt-2.5 inline-flex break-all text-[12px] leading-relaxed text-primary underline decoration-primary/40 underline-offset-2"
                            >
                              {section.content}
                            </a>
                          </Show>
                        }
                      >
                        <a href={section.href} target="_blank" rel="noreferrer" class="mt-3 block">
                          <img
                            src={section.href}
                            alt={section.alt || section.title}
                            class="max-h-80 w-full rounded-xl border border-border/70 bg-white object-contain"
                          />
                        </a>
                      </Show>
                    </div>
                  )}
                </For>
              </div>
            </Show>
            <div class="mt-4 rounded-xl border border-border/80 bg-background/80 p-3.5">
              <div class="flex items-center justify-between gap-3">
                <div class="text-[11px] font-medium text-text-secondary">Raw Trace Payload</div>
                <span class="text-[11px] text-text-secondary">exportable for debugging and handoff</span>
              </div>
              <pre class="mt-2.5 max-h-56 overflow-auto whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-primary">{getActionStateTracePayload(focused)}</pre>
            </div>
            <Show when={canResolveActionState(focused)}>
              <div class="mt-4 flex gap-2">
                <button
                  class="rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-[12px] font-semibold text-emerald-700 transition-all hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={props.isTyping}
                  onClick={() => props.onResolveAction(focused, true)}
                >
                  Approve
                </button>
                <button
                  class="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-[12px] font-semibold text-rose-700 transition-all hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={props.isTyping}
                  onClick={() => props.onResolveAction(focused, false)}
                >
                  Reject
                </button>
              </div>
            </Show>
          </div>
        );
      }}
    </Show>
  );
}
