import { Show, createSignal } from 'solid-js';

import type { WorkspaceMemoryCandidate } from '../../types';

export type InlineMemoryConfirmationPayload = {
  approval_mode: string;
  target_memory_id?: string | null;
  memory_type?: string | null;
  scope_type?: string | null;
  scope_ref?: string | null;
  title?: string | null;
  content?: string | null;
  confidence?: number | null;
  why_saved?: string | null;
  expires_at?: string | null;
  pinned?: boolean | null;
};

type InlineMemoryConfirmationProps = {
  candidate: WorkspaceMemoryCandidate;
  busy?: boolean;
  error?: string | null;
  onRemember: (candidate: WorkspaceMemoryCandidate, payload: InlineMemoryConfirmationPayload) => Promise<void> | void;
  onKeepSessionOnly: (candidate: WorkspaceMemoryCandidate) => Promise<void> | void;
};

export const getCandidateDestinationLabel = (candidate: WorkspaceMemoryCandidate) => {
  if (candidate.scope_type === 'user') return 'About You';
  if (candidate.scope_type === 'chat') return 'Just this time';
  return 'This Workspace';
};

export const buildInlineMemoryApprovalPayload = (
  candidate: WorkspaceMemoryCandidate,
  edits?: { title?: string; content?: string },
): InlineMemoryConfirmationPayload => {
  const title = edits?.title?.trim() || candidate.title;
  const content = edits?.content?.trim() || candidate.content;
  return {
    approval_mode:
      candidate.suggested_action || (candidate.conflict_memory_id ? 'update_existing' : 'create_new'),
    target_memory_id: candidate.conflict_memory_id || null,
    memory_type: candidate.memory_type || null,
    scope_type: candidate.scope_type || null,
    scope_ref: candidate.scope_ref || null,
    title,
    content,
    confidence: candidate.score ?? null,
    why_saved: candidate.why_saved || null,
    expires_at: candidate.expires_at || null,
  };
};

export default function InlineMemoryConfirmation(props: InlineMemoryConfirmationProps) {
  const [isEditing, setIsEditing] = createSignal(false);
  const [title, setTitle] = createSignal(props.candidate.title);
  const [content, setContent] = createSignal(props.candidate.content);

  const handleRemember = () =>
    props.onRemember(
      props.candidate,
      buildInlineMemoryApprovalPayload(props.candidate, isEditing() ? { title: title(), content: content() } : undefined),
    );

  return (
    <section class="mt-3 rounded-xl border border-blue-200 bg-white px-3 py-3 shadow-sm">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="text-[10px] font-black uppercase tracking-[0.18em] text-blue-700">Confirm Memory</div>
          <div class="mt-1 text-[11px] leading-snug text-slate-600">
            Yue can remember this for {getCandidateDestinationLabel(props.candidate)}.
          </div>
        </div>
        <span class="shrink-0 rounded-md border border-blue-100 bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">
          {getCandidateDestinationLabel(props.candidate)}
        </span>
      </div>

      <Show
        when={isEditing()}
        fallback={
          <div class="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
            <div class="truncate text-[12px] font-bold text-slate-900" title={props.candidate.title}>
              {props.candidate.title}
            </div>
            <p class="mt-1 text-[12px] leading-5 text-slate-600">{props.candidate.content}</p>
          </div>
        }
      >
        <div class="mt-3 space-y-2">
          <input
            type="text"
            value={title()}
            onInput={(event) => setTitle(event.currentTarget.value)}
            class="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-primary/20"
            aria-label="Memory title"
          />
          <textarea
            value={content()}
            onInput={(event) => setContent(event.currentTarget.value)}
            class="min-h-[88px] w-full resize-y rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs leading-5 text-slate-700 outline-none focus:ring-2 focus:ring-primary/20"
            aria-label="Memory content"
          />
        </div>
      </Show>

      <Show when={props.error}>
        <div class="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
          {props.error}
        </div>
      </Show>

      <div class="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={props.busy}
          onClick={() => void handleRemember()}
          class="rounded-lg border border-blue-200 bg-blue-600 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {props.busy ? 'Saving...' : 'Remember'}
        </button>
        <button
          type="button"
          disabled={props.busy}
          onClick={() => void props.onKeepSessionOnly(props.candidate)}
          class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Just this time
        </button>
        <button
          type="button"
          disabled={props.busy}
          onClick={() => setIsEditing((prev) => !prev)}
          class="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600 hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isEditing() ? 'Cancel edit' : 'Edit'}
        </button>
      </div>
    </section>
  );
}
