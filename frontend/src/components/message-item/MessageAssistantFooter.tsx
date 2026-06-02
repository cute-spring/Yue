import type { JSX } from 'solid-js';
import { Show } from 'solid-js';
import { Message } from '../../types';
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
}

export default function MessageAssistantFooter(props: MessageAssistantFooterProps) {
  return (
    <div class="export-exclude mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/10 pt-3">
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
  );
}
