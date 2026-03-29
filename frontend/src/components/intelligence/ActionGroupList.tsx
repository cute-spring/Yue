import { For, Show } from 'solid-js';

import { ActionState } from '../../types';
import {
  ActionStateGroup,
  EXPANDED_VISIBLE_INVOCATIONS,
  canResolveActionState,
  getActionDetailClasses,
  getActionStateArgs,
  getActionStateDetailSections,
  getActionStateDisplayId,
  getActionStateLabel,
  getActionStateTimestampLabel,
  getActionStateTone,
  getActionStateTraceIdentity,
  getActionToneClasses,
  getHiddenActionGroupCount,
  getVisibleActionGroupStates,
} from './actionHelpers';

interface ActionGroupListProps {
  groups: ActionStateGroup[];
  focusedActionKey: string | null;
  isGroupExpanded: (groupKey: string) => boolean;
  getVisibleInvocationCount: (groupKey: string) => number;
  onToggleGroupExpanded: (groupKey: string) => void;
  onShowMoreInvocations: (groupKey: string) => void;
  onFocusAction: (actionKey: string) => void;
  onResolveAction: (state: ActionState, approved: boolean) => void;
  isTyping: boolean;
}

export default function ActionGroupList(props: ActionGroupListProps) {
  return (
    <For each={props.groups}>
      {(group) => {
        const latestTone = getActionStateTone(group.latest);
        const expanded = props.isGroupExpanded(group.key);
        const visibleStates = getVisibleActionGroupStates(group, expanded, props.getVisibleInvocationCount(group.key));
        const hiddenCount = getHiddenActionGroupCount(group, expanded, props.getVisibleInvocationCount(group.key));
        return (
          <div class="px-5 py-5 bg-background/88 border border-border/70 rounded-[1.4rem] transition-all shadow-sm">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="text-[14px] font-semibold text-text-primary break-all leading-snug">
                  {group.label}
                </div>
                <div class="mt-1.5 text-[12px] leading-relaxed text-text-secondary">
                  {group.states.length > 1
                    ? `${group.states.length} invocations tracked for this tool-backed action.`
                    : 'Single invocation tracked for this tool-backed action.'}
                </div>
              </div>
              <span class={`shrink-0 rounded-full border px-3 py-1.5 text-[11px] font-semibold ${getActionToneClasses(latestTone)}`}>
                Latest: {getActionStateLabel(group.latest)}
              </span>
            </div>
            <div class="mt-4 flex items-center justify-between gap-3">
              <div class="text-[12px] text-text-secondary">
                {expanded
                  ? `Showing ${visibleStates.length} of ${group.states.length} invocations`
                  : `Showing latest invocation of ${group.states.length}`}
              </div>
              <Show when={group.states.length > 1}>
                <button
                  class="rounded-full border border-border bg-surface px-3.5 py-1.5 text-[11px] font-medium text-text-secondary transition-all hover:text-text-primary"
                  onClick={() => props.onToggleGroupExpanded(group.key)}
                >
                  {expanded ? 'Collapse History' : 'Expand History'}
                </button>
              </Show>
            </div>
            <div class="mt-4 space-y-3">
              <For each={visibleStates}>
                {(action, index) => {
                  const tone = getActionStateTone(action);
                  const actionArgs = getActionStateArgs(action);
                  const actionDetailSections = getActionStateDetailSections(action);
                  const actionTraceIdentity = getActionStateTraceIdentity(action);
                  return (
                    <div class="rounded-[1.2rem] border border-border/80 bg-surface/80 p-4 shadow-sm">
                      <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0">
                          <div class="text-[11px] font-medium text-text-secondary">
                            Invocation {group.states.length - index()}
                          </div>
                          <div class="mt-1.5 font-mono text-[12px] text-text-primary">
                            {getActionStateDisplayId(action)}
                          </div>
                        </div>
                        <span class={`shrink-0 rounded-full border px-3 py-1.5 text-[11px] font-semibold ${getActionToneClasses(tone)}`}>
                          {getActionStateLabel(action)}
                        </span>
                      </div>
                      <div class="mt-3.5 flex flex-wrap gap-2 text-[11px] font-medium text-text-secondary">
                        <Show when={action.skill_version}>
                          <span class="rounded-full bg-background px-2.5 py-1 border border-border/80">v{action.skill_version}</span>
                        </Show>
                        <Show when={action.lifecycle_phase}>
                          <span class="rounded-full bg-background px-2.5 py-1 border border-border/80">
                            phase: {action.lifecycle_phase}
                          </span>
                        </Show>
                        <Show when={action.sequence != null}>
                          <span class="rounded-full bg-background px-2.5 py-1 border border-border/80">
                            seq: {action.sequence}
                          </span>
                        </Show>
                        <Show when={action.approval_token}>
                          <span class="rounded-full bg-background px-2.5 py-1 border border-border/80">
                            approval token attached
                          </span>
                        </Show>
                        <Show when={getActionStateTimestampLabel(action)}>
                          <span class="rounded-full bg-background px-2.5 py-1 border border-border/80">
                            updated: {getActionStateTimestampLabel(action)}
                          </span>
                        </Show>
                      </div>
                      <Show when={actionArgs}>
                        <div class="mt-4 rounded-xl border border-border/80 bg-background/80 p-3.5">
                          <div class="text-[11px] font-medium text-text-secondary">Tool Arguments</div>
                          <pre class="mt-2.5 whitespace-pre-wrap break-words text-[12px] leading-relaxed text-text-primary">{JSON.stringify(actionArgs, null, 2)}</pre>
                        </div>
                      </Show>
                      <Show when={actionDetailSections.length > 0}>
                        <div class="mt-4 space-y-3">
                          <For each={actionDetailSections}>
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
                                      class="max-h-72 w-full rounded-xl border border-border/70 bg-white object-contain"
                                    />
                                  </a>
                                </Show>
                              </div>
                            )}
                          </For>
                        </div>
                      </Show>
                      <Show when={canResolveActionState(action)}>
                        <div class="mt-4 flex gap-2">
                          <button
                            class="rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-[12px] font-semibold text-emerald-700 transition-all hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={props.isTyping}
                            onClick={() => props.onResolveAction(action, true)}
                          >
                            Approve
                          </button>
                          <button
                            class="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-[12px] font-semibold text-rose-700 transition-all hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={props.isTyping}
                            onClick={() => props.onResolveAction(action, false)}
                          >
                            Reject
                          </button>
                        </div>
                      </Show>
                      <div class="mt-4 flex justify-end">
                        <button
                          class={`rounded-full border px-3.5 py-1.5 text-[11px] font-medium transition-all ${
                            props.focusedActionKey === actionTraceIdentity.key
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border bg-surface text-text-secondary hover:text-text-primary'
                          }`}
                          onClick={() => props.onFocusAction(actionTraceIdentity.key)}
                        >
                          {props.focusedActionKey === actionTraceIdentity.key ? 'Focused Trace' : 'Inspect Trace'}
                        </button>
                      </div>
                    </div>
                  );
                }}
              </For>
            </div>
            <Show when={expanded && hiddenCount > 0}>
              <div class="mt-4 flex justify-center">
                <button
                  class="rounded-full border border-border bg-surface px-3.5 py-1.5 text-[11px] font-medium text-text-secondary transition-all hover:text-text-primary"
                  onClick={() => props.onShowMoreInvocations(group.key)}
                >
                  Show {Math.min(EXPANDED_VISIBLE_INVOCATIONS, hiddenCount)} More
                </button>
              </div>
            </Show>
          </div>
        );
      }}
    </For>
  );
}
