import type { JSX } from 'solid-js';
import { Show, createEffect, createSignal } from 'solid-js';
import { Message, WorkspaceCaptureSuggestion, WorkspaceMemoryCandidate, WorkspaceNote } from '../../types';
import MessageAssistantMetaBadges from './MessageAssistantMetaBadges';

interface MessageAssistantFooterProps {
  content: string;
  speechState: string;
  modelLabel: string;
  visionBadge: { label: string; className: string } | null;
  msg: Message;
  isTyping: boolean;
  speechControl: JSX.Element;
  onExport: (event: MouseEvent) => void;
  onCollapse: () => void;
  onRegenerate: () => void;
  workspaceCaptureSuggestion?: WorkspaceCaptureSuggestion | null;
  onSaveWorkspaceNote?: () => Promise<WorkspaceNote | null>;
  onSuggestWorkspaceMemoryCandidate?: () => Promise<WorkspaceMemoryCandidate | null>;
  onTrackWorkspaceCaptureTelemetry?: (payload: {
    event_type: string;
    source?: string;
    workspace_id?: string | null;
    assistant_message_id?: number | string | null;
    assistant_turn_id?: string | null;
    run_id?: string | null;
    note_id?: string | null;
    candidate_id?: string | null;
    accepted?: boolean | null;
    metadata?: Record<string, any>;
  }) => Promise<void> | void;
}

export default function MessageAssistantFooter(props: MessageAssistantFooterProps) {
  const [isSavingNote, setIsSavingNote] = createSignal(false);
  const [isCreatingCandidate, setIsCreatingCandidate] = createSignal(false);
  const [captureFeedback, setCaptureFeedback] = createSignal<string | null>(null);
  const [captureError, setCaptureError] = createSignal<string | null>(null);
  const [isDismissed, setIsDismissed] = createSignal(false);
  const [trackedSuggestionKey, setTrackedSuggestionKey] = createSignal<string | null>(null);

  createEffect(() => {
    props.msg.id;
    props.workspaceCaptureSuggestion;
    setCaptureFeedback(null);
    setCaptureError(null);
    setIsSavingNote(false);
    setIsCreatingCandidate(false);
    setIsDismissed(false);
  });

  createEffect(() => {
    const suggestion = props.workspaceCaptureSuggestion;
    if (!suggestion || isDismissed()) return;
    const key = [
      props.msg.id ?? 'message',
      props.msg.assistant_turn_id ?? 'turn',
      suggestion.reason,
      suggestion.show_note_action ? 'note' : 'no-note',
      suggestion.show_memory_action ? 'memory' : 'no-memory',
    ].join(':');
    if (trackedSuggestionKey() === key) return;
    setTrackedSuggestionKey(key);
    void props.onTrackWorkspaceCaptureTelemetry?.({
      event_type: 'suggestion_shown',
      source: 'assistant_reply',
      workspace_id: suggestion.workspace_id || null,
      assistant_message_id: props.msg.id ?? null,
      assistant_turn_id: props.msg.assistant_turn_id || null,
      run_id: props.msg.run_id || null,
      metadata: {
        reason: suggestion.reason,
        show_note_action: suggestion.show_note_action,
        show_memory_action: suggestion.show_memory_action,
        source: suggestion.source || null,
      },
    });
  });

  const handleSaveWorkspaceNote = async () => {
    if (!props.onSaveWorkspaceNote) return;
    setIsSavingNote(true);
    setCaptureError(null);
    try {
      const note = await props.onSaveWorkspaceNote();
      if (note) {
        setCaptureFeedback(note.title ? `Saved note: ${note.title}` : 'Saved as workspace note.');
      }
    } catch (error) {
      setCaptureError(error instanceof Error ? error.message : 'Failed to save workspace note');
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleSuggestWorkspaceMemory = async () => {
    if (!props.onSuggestWorkspaceMemoryCandidate) return;
    setIsCreatingCandidate(true);
    setCaptureError(null);
    try {
      const candidate = await props.onSuggestWorkspaceMemoryCandidate();
      if (candidate) {
        setCaptureFeedback(candidate.title ? `Memory candidate ready: ${candidate.title}` : 'Memory candidate created.');
      }
    } catch (error) {
      setCaptureError(error instanceof Error ? error.message : 'Failed to create memory candidate');
    } finally {
      setIsCreatingCandidate(false);
    }
  };

  const handleDismissSuggestion = () => {
    setIsDismissed(true);
    void props.onTrackWorkspaceCaptureTelemetry?.({
      event_type: 'suggestion_dismissed',
      source: 'assistant_reply',
      workspace_id: props.workspaceCaptureSuggestion?.workspace_id || null,
      assistant_message_id: props.msg.id ?? null,
      assistant_turn_id: props.msg.assistant_turn_id || null,
      run_id: props.msg.run_id || null,
      accepted: false,
      metadata: {
        reason: props.workspaceCaptureSuggestion?.reason || null,
      },
    });
  };

  return (
    <div class="export-exclude mt-4 border-t border-border/10 pt-3">
      <Show when={props.workspaceCaptureSuggestion && !isDismissed()}>
        <div class="mb-3 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-3">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-700">Worth keeping</div>
              <div class="mt-1 text-[11px] leading-snug text-emerald-900/80">
                {props.workspaceCaptureSuggestion?.reason}
              </div>
            </div>
            <button
              type="button"
              onClick={handleDismissSuggestion}
              class="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700/70 hover:bg-white/60 hover:text-emerald-800"
            >
              Dismiss
            </button>
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            <Show when={props.workspaceCaptureSuggestion?.show_note_action}>
              <button
                type="button"
                disabled={isSavingNote()}
                onClick={() => void handleSaveWorkspaceNote()}
                class="rounded-lg border border-emerald-200 bg-white px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSavingNote() ? 'Saving...' : 'Save as note'}
              </button>
            </Show>
            <Show when={props.workspaceCaptureSuggestion?.show_memory_action}>
              <button
                type="button"
                disabled={isCreatingCandidate()}
                onClick={() => void handleSuggestWorkspaceMemory()}
                class="rounded-lg border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-blue-700 hover:border-blue-300 hover:bg-blue-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreatingCandidate() ? 'Reviewing...' : 'Review as memory'}
              </button>
            </Show>
          </div>
          <Show when={captureFeedback()}>
            <div class="mt-3 rounded-lg border border-emerald-200 bg-white px-3 py-2 text-[11px] text-emerald-700">
              {captureFeedback()}
            </div>
          </Show>
          <Show when={captureError()}>
            <div class="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
              {captureError()}
            </div>
          </Show>
        </div>
      </Show>

      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-1.5 -ml-1.5">
          <button
            class="rounded-lg p-1.5 text-text-secondary/40 transition-all hover:bg-black/5 hover:text-primary dark:hover:bg-white/5"
            title="Copy"
            onClick={() => navigator.clipboard.writeText(props.content)}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
          </button>
          {props.speechControl}
          <Show when={props.speechState === 'speaking' || props.speechState === 'paused'}>
            <div class="flex items-center gap-1.5 rounded-md border border-primary/20 bg-primary/5 px-2 py-1 text-[10px] font-semibold text-primary">
              <span class={`h-1.5 w-1.5 rounded-full ${props.speechState === 'speaking' ? 'bg-primary animate-pulse' : 'bg-primary/60'}`} />
              {props.speechState === 'speaking' ? 'Speaking' : 'Paused'}
            </div>
          </Show>
          <button
            class="rounded-lg p-1.5 text-text-secondary/40 transition-all hover:bg-black/5 hover:text-primary dark:hover:bg-white/5"
            title="Download/Export"
            onClick={props.onExport}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
          <button
            class="rounded-lg p-1.5 text-text-secondary/40 transition-all hover:bg-black/5 hover:text-primary dark:hover:bg-white/5"
            title="Collapse message"
            onClick={props.onCollapse}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            class="rounded-lg p-1.5 text-text-secondary/40 transition-all hover:bg-black/5 hover:text-primary dark:hover:bg-white/5"
            title="Regenerate"
            onClick={props.onRegenerate}
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>

        <div class="flex items-center gap-2">
          <MessageAssistantMetaBadges
            msg={props.msg}
            isTyping={props.isTyping}
            modelLabel={props.modelLabel}
            visionBadge={props.visionBadge}
          />
        </div>
      </div>
    </div>
  );
}
