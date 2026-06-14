import { For, Show } from 'solid-js';
import { Message } from '../../types';
import {
  formatCitationSourceLabel,
  getWorkspaceCitationWarning,
  getWorkspaceGroundingSummary,
  getWorkspaceNoteSummary,
  getWorkspaceMemorySummary,
  getWorkspaceSourceModeLabel,
  getWorkspaceToolingWarning,
} from './evidence';

interface MessageEvidencePanelProps {
  msg: Pick<Message, 'session_used_context' | 'workspace_grounding' | 'workspace_notes' | 'workspace_memory' | 'citations'>;
}

export default function MessageEvidencePanel(props: MessageEvidencePanelProps) {
  return (
    <>
      <Show when={
        props.msg.session_used_context && 
        props.msg.session_used_context.reason !== 'no_context_needed' &&
        props.msg.session_used_context.reason !== 'no_reference_signal'
      }>
        <div class="mt-5 rounded-2xl border border-violet-500/15 bg-violet-500/[0.04] px-4 py-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-[10px] font-black uppercase tracking-[0.2em] text-violet-600/80">
                Used context
              </div>
              <div class="mt-1 text-[12px] leading-relaxed text-text-secondary">
                {props.msg.session_used_context?.reason || 'Yue recalled recent and summarized session context for this reply.'}
              </div>
            </div>
            <span class="shrink-0 rounded-full border border-violet-500/15 bg-surface/70 px-2 py-0.5 text-[10px] font-bold text-violet-600">
              {props.msg.session_used_context?.action || 'loaded'}
            </span>
          </div>
          <Show when={(props.msg.session_used_context?.sections?.length ?? 0) > 0}>
            <div class="mt-3 space-y-2">
              <For each={props.msg.session_used_context?.sections || []}>
                {(section) => (
                  <div class="rounded-xl border border-violet-500/10 bg-white/70 px-3 py-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full border border-violet-100 bg-violet-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-700">
                        {section.label || section.kind || 'context'}
                      </span>
                      <Show when={section.item_count != null}>
                        <span class="text-[10px] text-text-secondary">{section.item_count} items</span>
                      </Show>
                    </div>
                    <Show when={section.summary}>
                      <div class="mt-1 whitespace-pre-wrap text-[11px] leading-relaxed text-text-secondary">
                        {section.summary}
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </Show>

      <Show when={
        props.msg.workspace_grounding && 
        (
          (props.msg.workspace_grounding.eligible_sources?.length ?? 0) > 0 ||
          (props.msg.workspace_grounding.unavailable_sources?.length ?? 0) > 0 ||
          getWorkspaceCitationWarning(props.msg) !== undefined ||
          getWorkspaceToolingWarning(props.msg) !== undefined
        )
      }>
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

      <Show when={props.msg.workspace_notes && (props.msg.workspace_notes.loaded_note_count ?? 0) > 0}>
        <div class="mt-5 rounded-2xl border border-sky-500/15 bg-sky-500/[0.04] px-4 py-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-[10px] font-black uppercase tracking-[0.2em] text-sky-600/80">
                Note recall
              </div>
              <div class="mt-1 text-[12px] leading-relaxed text-text-secondary">
                {getWorkspaceNoteSummary(props.msg)}
              </div>
            </div>
            <span class="shrink-0 rounded-full border border-sky-500/15 bg-surface/70 px-2 py-0.5 text-[10px] font-bold text-sky-600">
              {props.msg.workspace_notes?.loaded_note_count} recalled
            </span>
          </div>
          <Show when={(props.msg.workspace_notes?.loaded_notes?.length ?? 0) > 0}>
            <div class="mt-3 space-y-2">
              <For each={props.msg.workspace_notes?.loaded_notes || []}>
                {(note) => (
                  <div class="rounded-xl border border-sky-500/10 bg-white/70 px-3 py-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full border border-sky-100 bg-sky-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sky-700">
                        {note.note_type || 'note'}
                      </span>
                      <div class="text-[11px] font-semibold text-text-primary">{note.title || note.id}</div>
                    </div>
                    <Show when={note.tags && note.tags.length > 0}>
                      <div class="mt-2 flex flex-wrap gap-1.5">
                        <For each={note.tags || []}>
                          {(tag) => (
                            <span class="rounded-full border border-border/50 bg-surface/80 px-2 py-0.5 text-[10px] text-text-secondary">
                              #{tag}
                            </span>
                          )}
                        </For>
                      </div>
                    </Show>
                    <Show when={note.summary || note.content}>
                      <div class="mt-1 whitespace-pre-wrap text-[11px] leading-relaxed text-text-secondary">
                        {note.summary || note.content}
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
      </Show>

      <Show when={props.msg.workspace_memory && (props.msg.workspace_memory.loaded_memory_count ?? 0) > 0}>
        <div class="mt-5 rounded-2xl border border-cyan-500/15 bg-cyan-500/[0.04] px-4 py-3">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-[10px] font-black uppercase tracking-[0.2em] text-cyan-600/80">
                Memory context
              </div>
              <div class="mt-1 text-[12px] leading-relaxed text-text-secondary">
                {getWorkspaceMemorySummary(props.msg)}
              </div>
            </div>
            <span class="shrink-0 rounded-full border border-cyan-500/15 bg-surface/70 px-2 py-0.5 text-[10px] font-bold text-cyan-600">
              {props.msg.workspace_memory?.loaded_memory_count} loaded
            </span>
          </div>
          <Show when={(props.msg.workspace_memory?.loaded_memories?.length ?? 0) > 0}>
            <div class="mt-3 space-y-2">
              <For each={props.msg.workspace_memory?.loaded_memories || []}>
                {(memory) => (
                  <div class="rounded-xl border border-cyan-500/10 bg-white/70 px-3 py-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full border border-cyan-100 bg-cyan-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-cyan-700">
                        {memory.memory_type || 'memory'}
                      </span>
                      <Show when={memory.scope_type}>
                        <span class="rounded-full border border-border/40 bg-surface/80 px-2 py-0.5 text-[10px] text-text-secondary">
                          {memory.scope_type}
                        </span>
                      </Show>
                      <div class="text-[11px] font-semibold text-text-primary">{memory.title || memory.id}</div>
                    </div>
                    <Show when={memory.content}>
                      <div class="mt-1 whitespace-pre-wrap text-[11px] leading-relaxed text-text-secondary">
                        {memory.content}
                      </div>
                    </Show>
                  </div>
                )}
              </For>
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
