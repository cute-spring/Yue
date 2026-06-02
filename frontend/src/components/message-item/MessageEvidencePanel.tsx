import { For, Show } from 'solid-js';
import { Message } from '../../types';
import {
  formatCitationSourceLabel,
  getWorkspaceCitationWarning,
  getWorkspaceGroundingSummary,
  getWorkspaceSourceModeLabel,
  getWorkspaceToolingWarning,
} from './evidence';

interface MessageEvidencePanelProps {
  msg: Pick<Message, 'workspace_grounding' | 'citations'>;
}

export default function MessageEvidencePanel(props: MessageEvidencePanelProps) {
  return (
    <>
      <Show when={props.msg.workspace_grounding}>
        <div class="mt-5 rounded-2xl border border-emerald-500/15 bg-emerald-500/[0.04] px-4 py-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-600/80">
                Evidence contract
              </div>
              <div class="mt-1 text-[12px] leading-relaxed text-text-secondary">
                {getWorkspaceGroundingSummary(props.msg)}
              </div>
            </div>
            <span class="shrink-0 rounded-full border border-emerald-500/15 bg-surface/70 px-2 py-0.5 text-[10px] font-bold text-emerald-600">
              {getWorkspaceSourceModeLabel(props.msg.workspace_grounding?.workspace_source_mode)}
            </span>
          </div>
          <Show when={(props.msg.workspace_grounding?.eligible_sources?.length ?? 0) > 0}>
            <div class="mt-3 flex flex-wrap gap-1.5">
              <For each={props.msg.workspace_grounding?.eligible_sources || []}>
                {(source) => (
                  <span class="max-w-full truncate rounded-full border border-border/50 bg-surface/80 px-2 py-0.5 text-[10px] text-text-secondary">
                    {source.display_name || source.id}
                  </span>
                )}
              </For>
            </div>
          </Show>
          <Show when={(props.msg.workspace_grounding?.unavailable_sources?.length ?? 0) > 0}>
            <div class="mt-3">
              <div class="text-[10px] font-black uppercase tracking-[0.2em] text-text-secondary/60">
                Unavailable in this turn
              </div>
              <div class="mt-2 flex flex-wrap gap-1.5">
                <For each={props.msg.workspace_grounding?.unavailable_sources || []}>
                  {(source) => (
                    <span class="max-w-full truncate rounded-full border border-amber-500/15 bg-amber-500/5 px-2 py-0.5 text-[10px] text-amber-700">
                      {source.display_name || source.id}
                    </span>
                  )}
                </For>
              </div>
            </div>
          </Show>
          <Show when={getWorkspaceCitationWarning(props.msg)}>
            <div class="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-[12px] leading-relaxed text-amber-700">
              {getWorkspaceCitationWarning(props.msg)}
            </div>
          </Show>
          <Show when={getWorkspaceToolingWarning(props.msg)}>
            <div class="mt-3 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-[12px] leading-relaxed text-rose-700">
              {getWorkspaceToolingWarning(props.msg)}
            </div>
          </Show>
        </div>
      </Show>

      <Show when={(props.msg.citations?.length ?? 0) > 0}>
        <details class="mt-5 -mx-2 rounded-2xl border border-border/50 bg-black/5 dark:bg-white/5 px-4 py-3">
          <summary class="cursor-pointer text-xs font-black uppercase tracking-[0.2em] text-text-secondary/70">
            Sources ({props.msg.citations?.length ?? 0})
          </summary>
          <div class="mt-3 space-y-2">
            <For each={props.msg.citations || []}>
              {(citation) => (
                <div class="rounded-xl border border-border/40 bg-surface/60 px-3 py-2">
                  <div class="text-xs font-mono text-text-secondary">
                    {formatCitationSourceLabel(citation)}
                  </div>
                  <Show when={typeof citation?.snippet === 'string' && citation.snippet.trim().length > 0}>
                    <pre class="mt-2 max-h-56 overflow-auto whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-text-secondary/80">
                      {citation.snippet}
                    </pre>
                  </Show>
                </div>
              )}
            </For>
          </div>
        </details>
      </Show>
    </>
  );
}
