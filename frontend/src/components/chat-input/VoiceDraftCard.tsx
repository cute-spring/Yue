import { Show } from 'solid-js';

type VoiceDraftCardProps = {
  visible: boolean;
  providerLabel: string;
  phase: 'idle' | 'recording' | 'finalizing' | 'ready' | 'error';
  isRecording: boolean;
  isProcessing: boolean;
  error: string | null;
  fallbackMessage: string | null;
  previewText: string;
  onInsert: () => void;
  onSend: () => void;
  onCancel: () => void;
};

export default function VoiceDraftCard(props: VoiceDraftCardProps) {
  return (
    <Show when={props.visible}>
      <div class={`mt-2 px-3 py-2 rounded-xl border text-[12px] ${
        props.error
          ? 'border-rose-300 bg-rose-50 text-rose-700'
          : 'border-sky-300 bg-sky-50 text-sky-700'
      }`}>
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <Show when={props.fallbackMessage}>
              <div class="mb-1 inline-flex items-center rounded-full border border-amber-300/70 bg-amber-100/80 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                Using {props.providerLabel}
              </div>
              <div class="mb-1 text-amber-800">{props.fallbackMessage}</div>
            </Show>
            <Show when={!props.error} fallback={<span>{props.error}</span>}>
              <span>
                {props.isRecording
                  ? `Listening with ${props.providerLabel}... pause to finish`
                  : props.isProcessing
                    ? `Processing speech with ${props.providerLabel}...`
                    : props.phase === 'ready'
                      ? `Voice draft ready from ${props.providerLabel}`
                      : `Voice preview from ${props.providerLabel}`}
              </span>
              <Show when={props.phase === 'ready'}>
                <span class="block mt-1 text-sky-800/80">
                  Press Enter to insert, Cmd/Ctrl+Enter to send, or Esc to discard.
                </span>
              </Show>
              <Show when={props.previewText}>
                <span class="block mt-1 text-sky-800/80 italic break-words">
                  {props.previewText}
                </span>
              </Show>
            </Show>
          </div>
          <div class="shrink-0 flex items-center gap-3">
            <Show when={props.phase === 'ready' && !props.error}>
              <button
                type="button"
                class="text-[11px] font-semibold text-sky-700 hover:text-sky-900"
                onClick={() => props.onInsert()}
              >
                Insert (Enter)
              </button>
            </Show>
            <Show when={props.phase === 'ready' && !props.error}>
              <button
                type="button"
                class="text-[11px] font-semibold text-sky-700 hover:text-sky-900"
                onClick={() => props.onSend()}
              >
                Send (Cmd/Ctrl+Enter)
              </button>
            </Show>
            <Show when={props.phase !== 'idle'}>
              <button
                type="button"
                class="text-[11px] font-semibold text-sky-700 hover:text-sky-900"
                onClick={() => props.onCancel()}
              >
                {props.phase === 'ready' ? 'Discard (Esc)' : 'Cancel'}
              </button>
            </Show>
          </div>
        </div>
      </div>
    </Show>
  );
}
