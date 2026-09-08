import { For, Show, createMemo } from 'solid-js';

import type { Workspace, WorkspaceUnderstandingGroup, WorkspaceUnderstandingSummary } from '../../types';
import AppliedUserMemoryPreview from './AppliedUserMemoryPreview';
import WorkspaceUnderstandingGroupCard from './WorkspaceUnderstandingGroupCard';

type WorkspaceUnderstandingPanelProps = {
  workspace: Workspace | null;
  summary: WorkspaceUnderstandingSummary | null;
  loading?: boolean;
  error?: string | null;
  sourceCount: number;
  noteCount: number;
  artifactCount: number;
  memoryCount: number;
  pendingCandidateCount: number;
  onRefresh: () => Promise<WorkspaceUnderstandingSummary | null> | void;
  onReviewGroup?: (group: WorkspaceUnderstandingGroup) => void;
};

const metricClass = 'rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm';

export const WORKSPACE_UNDERSTANDING_GROUP_DEFINITIONS = [
  { group: 'background', label: 'Background' },
  { group: 'goals', label: 'Goals' },
  { group: 'decisions', label: 'Decisions' },
  { group: 'constraints', label: 'Constraints' },
  { group: 'preferences', label: 'Preferences' },
  { group: 'terms', label: 'Terms' },
  { group: 'open_questions', label: 'Open Questions' },
  { group: 'current_state', label: 'Current State' },
];

export const normalizeWorkspaceUnderstandingGroups = (
  summary: WorkspaceUnderstandingSummary | null,
): WorkspaceUnderstandingGroup[] => {
  const byGroup = new Map((summary?.groups ?? []).map((group) => [group.group, group]));
  return WORKSPACE_UNDERSTANDING_GROUP_DEFINITIONS.map((definition) => ({
    group: definition.group,
    label: definition.label,
    total_count: 0,
    active_count: 0,
    pending_count: 0,
    representative_items: [],
    ...byGroup.get(definition.group),
  }));
};

export const buildWorkspaceUnderstandingMetrics = (
  summary: WorkspaceUnderstandingSummary | null,
  fallbackMemoryCount: number,
  fallbackPendingCandidateCount: number,
  sourceCount: number,
  noteCount: number,
  artifactCount: number,
) => ({
  savedUnderstandingCount:
    summary?.groups.reduce((total, group) => total + group.total_count, 0) ?? fallbackMemoryCount,
  pendingCount:
    summary?.groups.reduce((total, group) => total + group.pending_count, 0) ?? fallbackPendingCandidateCount,
  sourceCount,
  noteArtifactCount: noteCount + artifactCount,
});

export default function WorkspaceUnderstandingPanel(props: WorkspaceUnderstandingPanelProps) {
  const groups = createMemo(() => normalizeWorkspaceUnderstandingGroups(props.summary));
  const metrics = createMemo(() =>
    buildWorkspaceUnderstandingMetrics(
      props.summary,
      props.memoryCount,
      props.pendingCandidateCount,
      props.sourceCount,
      props.noteCount,
      props.artifactCount,
    ),
  );

  return (
    <section class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-600">
            Workspace Understanding
          </div>
          <h2 class="mt-1 truncate text-sm font-black text-slate-950" title={props.workspace?.name || 'No workspace selected'}>
            {props.workspace?.name || 'No workspace selected'}
          </h2>
        </div>
        <button
          type="button"
          onClick={() => void props.onRefresh()}
          disabled={!props.workspace || props.loading}
          class="shrink-0 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 transition-colors hover:border-slate-300 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          title="Refresh understanding"
        >
          Refresh
        </button>
      </div>

      <Show
        when={props.workspace}
        fallback={
          <div class="rounded-lg border border-dashed border-slate-300 bg-white px-3 py-4 text-[12px] leading-5 text-slate-500">
            Pick a workspace to see what Yue understands about it.
          </div>
        }
      >
        <div class="grid grid-cols-2 gap-2">
          <div class={metricClass}>
            <div class="text-base font-black text-slate-950">{metrics().savedUnderstandingCount}</div>
            <div class="text-[10px] font-semibold text-slate-500">saved items</div>
          </div>
          <div class={metricClass}>
            <div class="text-base font-black text-slate-950">{metrics().pendingCount}</div>
            <div class="text-[10px] font-semibold text-slate-500">pending</div>
          </div>
          <div class={metricClass}>
            <div class="text-base font-black text-slate-950">{metrics().sourceCount}</div>
            <div class="text-[10px] font-semibold text-slate-500">sources</div>
          </div>
          <div class={metricClass}>
            <div class="text-base font-black text-slate-950">{metrics().noteArtifactCount}</div>
            <div class="text-[10px] font-semibold text-slate-500">notes + artifacts</div>
          </div>
        </div>

        <Show when={props.error}>
          <div class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[12px] font-semibold text-red-700">
            Failed to load workspace understanding: {props.error}
          </div>
        </Show>

        <Show when={props.loading}>
          <div class="rounded-lg border border-slate-200 bg-white px-3 py-3 text-[12px] text-slate-500">
            Loading understanding...
          </div>
        </Show>

        <AppliedUserMemoryPreview items={props.summary?.applied_user_memory_preview ?? []} />

        <div class="space-y-2">
          <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
            About This Workspace
          </div>
          <div class="grid gap-2">
            <For each={groups()}>
              {(group) => <WorkspaceUnderstandingGroupCard group={group} onReview={props.onReviewGroup} />}
            </For>
          </div>
        </div>
      </Show>
    </section>
  );
}
