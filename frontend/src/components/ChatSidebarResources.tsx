import { For, Show, createMemo } from 'solid-js';
import { WorkspaceArtifact, WorkspaceSource } from '../types';
import {
  formatWorkspaceArtifactType,
  getArtifactSourceLabels,
  getResearchArtifactMetadata,
  getWorkspaceEvidenceSummary,
  getWorkspaceSourceToolLabels,
} from './ChatSidebar.helpers';

type WorkspaceSourceMode = 'all_ready' | 'selected' | 'none';
type GroundingMode = 'normal' | 'prefer_sources' | 'require_sources';

interface ChatSidebarResourcesProps {
  selectedWorkspaceId: string | null;
  workspaceSources: WorkspaceSource[];
  workspaceArtifacts: WorkspaceArtifact[];
  workspaceSourceMode: WorkspaceSourceMode;
  selectedWorkspaceSourceIds: string[];
  groundingMode: GroundingMode;
  sourcesLoading?: boolean;
  artifactsLoading?: boolean;
  isResourcesExpanded: boolean;
  isSourcesExpanded: boolean;
  isArtifactsExpanded: boolean;
  onToggleResources: () => void;
  onToggleSources: () => void;
  onToggleArtifacts: () => void;
  onWorkspaceSourceModeChange: (mode: WorkspaceSourceMode) => void;
  onToggleWorkspaceSource: (sourceId: string) => void;
  onGroundingModeChange: (mode: GroundingMode) => void;
  onCheckWorkspaceSources: () => Promise<void> | void;
  onCheckWorkspaceSource: (sourceId: string) => Promise<void> | void;
  onLoadChat: (id: string) => void;
}

const formatSourceModeLabel = (mode: WorkspaceSourceMode) => {
  switch (mode) {
    case 'all_ready':
      return 'All ready';
    case 'selected':
      return 'Selected only';
    case 'none':
      return 'No sources';
  }
};

const formatGroundingModeLabel = (mode: GroundingMode) => {
  switch (mode) {
    case 'normal':
      return 'Normal';
    case 'prefer_sources':
      return 'Prefer cites';
    case 'require_sources':
      return 'Require cites';
  }
};

export default function ChatSidebarResources(props: ChatSidebarResourcesProps) {
  const sourcesReadyCount = createMemo(() =>
    props.workspaceSources.filter((source) => source.source_metadata?.citation_capable || source.status === 'ready').length
  );

  const latestArtifactTitle = createMemo(() => props.workspaceArtifacts[0]?.title || null);

  const resourcesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'Select a workspace to manage sources and artifacts.';
    const parts = [
      `${props.workspaceSources.length} sources`,
      `${props.workspaceArtifacts.length} artifacts`,
    ];
    if (props.workspaceSources.length > 0) parts.push(`${sourcesReadyCount()} ready`);
    return parts.join(' · ');
  });

  const sourcesSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    return `${props.workspaceSources.length} total · ${sourcesReadyCount()} ready`;
  });

  const artifactsSummary = createMemo(() => {
    if (!props.selectedWorkspaceId) return 'No workspace selected';
    if (latestArtifactTitle()) return `Latest: ${latestArtifactTitle()}`;
    return props.workspaceArtifacts.length > 0 ? `${props.workspaceArtifacts.length} artifacts` : 'No artifacts yet';
  });

  const evidenceSummary = createMemo(() =>
    getWorkspaceEvidenceSummary(
      props.workspaceSourceMode,
      props.groundingMode,
      props.workspaceSources,
      props.selectedWorkspaceSourceIds,
    )
  );

  return (
    <div class="mt-3 rounded-xl border border-slate-200 bg-slate-50/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
      <button
        type="button"
        onClick={props.onToggleResources}
        aria-expanded={props.isResourcesExpanded}
        class="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors hover:bg-white/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <div class="min-w-0">
          <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Resources</div>
          <div class="mt-1 line-clamp-2 text-[11px] leading-snug text-slate-600">
            {resourcesSummary()}
          </div>
          <Show when={props.selectedWorkspaceId}>
            <div class="mt-2 flex flex-wrap gap-1">
              <span class="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] font-semibold text-slate-600">
                {formatSourceModeLabel(props.workspaceSourceMode)}
              </span>
              <span class="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] font-semibold text-slate-600">
                {formatGroundingModeLabel(props.groundingMode)}
              </span>
            </div>
          </Show>
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isResourcesExpanded ? 'rotate-90' : 'rotate-0'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <Show when={props.isResourcesExpanded && props.selectedWorkspaceId}>
        <div class="border-t border-slate-200 px-3 py-3">
          <div class="rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleSources}
              aria-expanded={props.isSourcesExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Sources</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {sourcesSummary()}
                </div>
                <div class="mt-1 text-[10px] text-slate-400">
                  {formatSourceModeLabel(props.workspaceSourceMode)} · {formatGroundingModeLabel(props.groundingMode)}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isSourcesExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isSourcesExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <div class="mb-2 mt-3 grid grid-cols-2 gap-2">
                  <select
                    value={props.workspaceSourceMode}
                    onChange={(e) => props.onWorkspaceSourceModeChange(e.currentTarget.value as WorkspaceSourceMode)}
                    class="bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="all_ready">All ready</option>
                    <option value="selected">Selected</option>
                    <option value="none">No sources</option>
                  </select>
                  <select
                    value={props.groundingMode}
                    onChange={(e) => props.onGroundingModeChange(e.currentTarget.value as GroundingMode)}
                    class="bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="normal">Normal</option>
                    <option value="prefer_sources">Prefer cites</option>
                    <option value="require_sources">Require cites</option>
                  </select>
                </div>
                <div class="mb-2 flex items-center justify-between gap-2 rounded-lg border border-blue-100 bg-blue-50/70 px-2.5 py-2 text-[10px] leading-snug text-blue-700">
                  <span class="min-w-0 flex-1">{evidenceSummary()}</span>
                  <button
                    type="button"
                    onClick={() => void props.onCheckWorkspaceSources()}
                    class="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold text-primary transition-colors hover:bg-white/70 hover:text-primary-hover"
                  >
                    Check
                  </button>
                </div>
                <Show
                  when={!props.sourcesLoading}
                  fallback={<div class="text-[11px] text-slate-400 italic">Loading sources...</div>}
                >
                  <Show
                    when={props.workspaceSources.length > 0}
                    fallback={<div class="text-[11px] text-slate-400 italic">No sources registered yet.</div>}
                  >
                    <div class="space-y-2 max-h-36 overflow-y-auto no-scrollbar pr-1">
                      <For each={props.workspaceSources}>
                        {(source) => (
                          <div class="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 transition-colors hover:border-slate-200 hover:bg-white">
                            <div class="flex items-start gap-2">
                              <Show when={props.workspaceSourceMode === 'selected'}>
                                <input
                                  type="checkbox"
                                  checked={props.selectedWorkspaceSourceIds.includes(source.id)}
                                  onChange={() => props.onToggleWorkspaceSource(source.id)}
                                  class="mt-0.5 h-3.5 w-3.5 rounded border-slate-300 text-primary"
                                />
                              </Show>
                              <div class="min-w-0 flex-1">
                                <div
                                  class="truncate text-[11px] font-semibold text-slate-700"
                                  title={source.display_name || source.source_ref}
                                >
                                  {source.display_name || source.source_ref}
                                </div>
                                <div class="mt-1 flex items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">{source.source_type}</span>
                                  <Show when={source.status}>
                                    <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">{source.status}</span>
                                  </Show>
                                  <Show when={source.source_metadata?.readiness_error_message}>
                                    <span class="truncate text-[9px] normal-case tracking-normal text-rose-500">
                                      {source.source_metadata?.readiness_error_message}
                                    </span>
                                  </Show>
                                </div>
                                <Show when={source.source_metadata?.citation_capable || getWorkspaceSourceToolLabels(source).length > 0}>
                                  <div class="mt-1 flex flex-wrap gap-1">
                                    <Show when={source.source_metadata?.citation_capable}>
                                      <span class="rounded-full border border-emerald-100 bg-emerald-50 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-700">
                                        cite-ready
                                      </span>
                                    </Show>
                                    <For each={getWorkspaceSourceToolLabels(source)}>
                                      {(toolLabel) => (
                                        <span class="rounded-full border border-blue-100 bg-blue-50 px-1.5 py-0.5 text-[9px] font-semibold text-blue-700">
                                          {toolLabel}
                                        </span>
                                      )}
                                    </For>
                                  </div>
                                </Show>
                              </div>
                              <button
                                type="button"
                                onClick={() => void props.onCheckWorkspaceSource(source.id)}
                                class="rounded-md px-1.5 py-0.5 text-[10px] font-bold text-slate-400 transition-colors hover:bg-white hover:text-primary"
                              >
                                Retry
                              </button>
                            </div>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>

          <div class="mt-2 rounded-lg border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
            <button
              type="button"
              onClick={props.onToggleArtifacts}
              aria-expanded={props.isArtifactsExpanded}
              class="flex w-full items-start justify-between gap-2 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            >
              <div class="min-w-0">
                <div class="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Artifacts</div>
                <div class="mt-1 text-[11px] text-slate-600">
                  {props.workspaceArtifacts.length} total
                </div>
                <div class="mt-1 truncate text-[10px] text-slate-400" title={artifactsSummary()}>
                  {artifactsSummary()}
                </div>
              </div>
              <svg
                xmlns="http://www.w3.org/2000/svg"
                class={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition-transform ${props.isArtifactsExpanded ? 'rotate-90' : 'rotate-0'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <Show when={props.isArtifactsExpanded}>
              <div class="border-t border-slate-100 px-3 pb-3">
                <Show
                  when={!props.artifactsLoading}
                  fallback={<div class="mt-3 text-[11px] text-slate-400 italic">Loading artifacts...</div>}
                >
                  <Show
                    when={props.workspaceArtifacts.length > 0}
                    fallback={<div class="mt-3 text-[11px] text-slate-400 italic">No artifacts registered yet.</div>}
                  >
                    <div class="mt-3 space-y-2 max-h-72 overflow-y-auto no-scrollbar pr-1">
                      <For each={props.workspaceArtifacts}>
                        {(artifact) => {
                          const metadata = createMemo(() => getResearchArtifactMetadata(artifact));
                          const sourceLabels = createMemo(() => getArtifactSourceLabels(artifact, props.workspaceSources));
                          return (
                            <details
                              open={props.workspaceArtifacts.length === 1}
                              class="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2 transition-colors hover:border-slate-200 hover:bg-white"
                            >
                              <summary class="cursor-pointer list-none">
                                <div class="flex items-start justify-between gap-2">
                                  <div class="min-w-0 truncate text-[11px] font-semibold text-slate-700" title={artifact.title}>
                                    {artifact.title}
                                  </div>
                                  <span class="shrink-0 text-[9px] font-bold uppercase tracking-wide text-blue-500">
                                    Detail
                                  </span>
                                </div>
                                <div class="mt-1 flex items-center gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-slate-200">
                                    {formatWorkspaceArtifactType(artifact.artifact_type)}
                                  </span>
                                  <Show when={artifact.artifact_path}>
                                    <span
                                      class="truncate text-[9px] normal-case tracking-normal text-slate-400"
                                      title={artifact.artifact_path || undefined}
                                    >
                                      {artifact.artifact_path}
                                    </span>
                                  </Show>
                                </div>
                              </summary>

                              <div class="mt-3 rounded-xl border border-blue-100 bg-gradient-to-br from-white to-blue-50/70 p-3 shadow-sm">
                                <div class="min-w-0">
                                  <div class="text-[10px] font-black uppercase tracking-[0.18em] text-blue-500">
                                    Research detail
                                  </div>
                                  <div class="mt-1 text-[12px] font-bold leading-snug text-slate-800">
                                    {metadata().question}
                                  </div>
                                </div>

                                <div class="mt-2 flex flex-wrap gap-1.5 text-[9px] uppercase tracking-wide text-slate-500">
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                    {formatWorkspaceArtifactType(artifact.artifact_type)}
                                  </span>
                                  <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                    {metadata().mode}
                                  </span>
                                  <Show when={artifact.source_session_id}>
                                    <span class="rounded bg-white px-1.5 py-0.5 border border-blue-100">
                                      linked chat
                                    </span>
                                  </Show>
                                </div>

                                <Show when={metadata().summary}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Summary</div>
                                    <p class="mt-1 max-h-28 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate-700">
                                      {metadata().summary}
                                    </p>
                                  </div>
                                </Show>

                                <Show when={sourceLabels().length > 0}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Sources</div>
                                    <div class="mt-1 flex flex-wrap gap-1">
                                      <For each={sourceLabels()}>
                                        {(label) => (
                                          <span class="max-w-full truncate rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-600">
                                            {label}
                                          </span>
                                        )}
                                      </For>
                                    </div>
                                  </div>
                                </Show>

                                <Show when={metadata().openQuestions.length > 0}>
                                  <div class="mt-3">
                                    <div class="text-[10px] font-bold uppercase tracking-wide text-slate-500">Open questions</div>
                                    <div class="mt-1 space-y-1">
                                      <For each={metadata().openQuestions}>
                                        {(question) => (
                                          <div class="rounded-lg bg-white/80 px-2 py-1 text-[10px] leading-snug text-slate-600">
                                            {question}
                                          </div>
                                        )}
                                      </For>
                                    </div>
                                  </div>
                                </Show>

                                <Show when={artifact.source_session_id || artifact.source_message_id || metadata().exportPaths.length > 0}>
                                  <div class="mt-3 border-t border-blue-100 pt-2 text-[10px] leading-relaxed text-slate-500">
                                    <Show when={artifact.source_session_id}>
                                      <div class="flex items-center justify-between gap-2">
                                        <span class="truncate">Chat: {artifact.source_session_id}</span>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const chatId = artifact.source_session_id;
                                            if (chatId) props.onLoadChat(chatId);
                                          }}
                                          class="shrink-0 rounded-full border border-blue-100 bg-white px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-blue-600 hover:border-blue-200 hover:bg-blue-50"
                                        >
                                          Open chat
                                        </button>
                                      </div>
                                    </Show>
                                    <Show when={artifact.source_message_id}>
                                      <div>Message: {artifact.source_message_id}</div>
                                    </Show>
                                    <Show when={metadata().exportPaths.length > 0}>
                                      <div>Exports: {metadata().exportPaths.join(', ')}</div>
                                    </Show>
                                  </div>
                                </Show>
                              </div>
                            </details>
                          );
                        }}
                      </For>
                    </div>
                  </Show>
                </Show>
              </div>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
