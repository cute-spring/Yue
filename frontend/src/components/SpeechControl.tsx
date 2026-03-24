import { Show } from 'solid-js';
import { useSpeechController } from '../context/SpeechControllerContext';

type SpeechControlProps = {
  messageId: string;
  content: string;
};

export default function SpeechControl(props: SpeechControlProps) {
  const speech = useSpeechController();
  const state = () => speech.getMessageState(props.messageId);
  const isDisabled = () => !speech.supported();
  const isActive = () => state() === 'speaking' || state() === 'paused';
  const buttonLabel = () => {
    if (isDisabled()) return 'Read aloud unavailable in this browser';
    if (isActive()) return 'Stop reading';
    return 'Read aloud';
  };

  const handleClick = () => {
    speech.toggleMessage(props.messageId, props.content);
  };

  return (
    <button
      class={`p-1.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${
        isActive()
          ? 'text-primary bg-primary/10 ring-1 ring-primary/20'
          : 'text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5'
      }`}
      title={buttonLabel()}
      aria-label={buttonLabel()}
      aria-pressed={isActive()}
      onClick={handleClick}
      disabled={isDisabled()}
    >
      <Show
        when={state() === 'speaking'}
        fallback={
          <Show
            when={state() === 'paused'}
            fallback={
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
            }
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </Show>
        }
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
          <rect x="6" y="6" width="5" height="12" rx="1" />
          <rect x="13" y="6" width="5" height="12" rx="1" />
        </svg>
      </Show>
    </button>
  );
}
