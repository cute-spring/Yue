import { For, Show } from 'solid-js';
import { Attachment, Message } from '../../types';
import {
  getAttachmentDisplayName,
  getAttachmentMimeType,
  isImageAttachment,
} from './helpers';

interface MessageUserContentProps {
  msg: Message;
  attachments: Attachment[];
  isEditing: boolean;
  editContent: string;
  isSavingEdit: boolean;
  editError: string | null;
  copiedMessageIndex: number | null;
  index: number;
  formattedTime: string;
  onEditInput: (value: string) => void;
  onEditKeyDown: (event: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSubmitEdit: () => void;
  copyUserMessage: (content: string, index: number) => void;
  quoteUserMessage: (content: string) => void;
}

export default function MessageUserContent(props: MessageUserContentProps) {
  return (
    <>
      <Show when={!props.isEditing}>
        <Show when={props.attachments.length > 0}>
          <div class="relative z-10 mb-2 flex flex-wrap gap-2">
            <For each={props.attachments}>
              {(attachment) => (
                <Show
                  when={isImageAttachment(attachment) && !!attachment.url}
                  fallback={
                    <a
                      href={attachment.url || '#'}
                      target="_blank"
                      rel="noreferrer"
                      class="flex min-w-[220px] max-w-[320px] items-center gap-3 rounded-lg border border-white/10 bg-black/5 px-3 py-2 text-left hover:border-primary/30"
                    >
                      <div class="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-[11px] font-bold uppercase text-primary">
                        {getAttachmentDisplayName(attachment).split('.').pop() || 'file'}
                      </div>
                      <div class="min-w-0">
                        <div class="truncate text-[13px] font-semibold text-text-primary">
                          {getAttachmentDisplayName(attachment)}
                        </div>
                        <div class="truncate text-[11px] text-text-secondary/70">
                          {getAttachmentMimeType(attachment)}
                        </div>
                      </div>
                    </a>
                  }
                >
                  <img src={attachment.url!} class="h-auto max-h-64 max-w-full rounded-lg border border-white/10 shadow-sm" alt="User upload" />
                </Show>
              )}
            </For>
          </div>
        </Show>
        <div class="relative select-text whitespace-pre-wrap text-[15px] font-medium leading-relaxed">
          {props.msg.content}
        </div>
        <div class="mt-4 flex items-center justify-between border-t border-primary/10 pt-3">
          <div class="export-exclude flex items-center gap-1.5 -ml-2">
            <button
              class={`rounded-lg p-1.5 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                props.copiedMessageIndex === props.index
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'text-text-secondary/50 hover:bg-primary/10 hover:text-primary'
              }`}
              title={props.copiedMessageIndex === props.index ? 'Copied' : 'Copy'}
              aria-label="Copy message"
              onClick={() => props.copyUserMessage(props.msg.content, props.index)}
            >
              <Show
                when={props.copiedMessageIndex === props.index}
                fallback={
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                }
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
              </Show>
            </button>
            <button
              class="rounded-lg p-1.5 text-text-secondary/50 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 hover:bg-primary/10 hover:text-primary"
              title="Quote"
              aria-label="Quote message"
              onClick={() => props.quoteUserMessage(props.msg.content)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l5 5m-5-5l5-5" />
              </svg>
            </button>
            <button
              class="rounded-lg p-1.5 text-text-secondary/50 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 hover:bg-primary/10 hover:text-primary"
              title="Edit"
              aria-label="Edit message"
              onClick={props.onStartEdit}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5h2m-7 14h12a2 2 0 002-2V7a2 2 0 00-2-2h-3m-4 0H8a2 2 0 00-2 2v3m0 4v3a2 2 0 002 2m8-7l-6 6-4 1 1-4 6-6m3-3l2 2" />
              </svg>
            </button>
          </div>
          <div class="flex items-center gap-1.5 rounded-md border border-primary/10 bg-primary/5 px-2 py-1 text-[10px] font-bold uppercase tracking-tight text-text-secondary/60">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {props.formattedTime}
          </div>
        </div>
      </Show>

      <Show when={props.isEditing}>
        <div class="relative z-20 mt-2 flex w-full min-w-[280px] flex-col gap-3">
          <textarea
            class="min-h-[180px] w-full resize-y rounded-2xl border border-primary/25 bg-background/90 p-4 text-[15px] leading-7 text-text-primary shadow-sm backdrop-blur-md transition focus:border-primary/60 focus:outline-none focus:ring-4 focus:ring-primary/10"
            rows={8}
            value={props.editContent}
            disabled={props.isSavingEdit}
            onInput={(e) => props.onEditInput(e.currentTarget.value)}
            onKeyDown={(e) => {
              void props.onEditKeyDown(e);
            }}
          />
          <Show when={props.editError}>
            <div class="text-xs text-rose-500">{props.editError}</div>
          </Show>
          <div class="flex items-center justify-between gap-3">
            <div class="text-[11px] text-text-secondary/60">Shift + Enter 换行，Cmd/Ctrl + Enter 提交</div>
            <div class="flex justify-end gap-2">
              <button
                disabled={props.isSavingEdit}
                onClick={props.onCancelEdit}
                class="rounded-lg px-3 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-text-secondary/10 disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                disabled={props.isSavingEdit}
                onClick={props.onSubmitEdit}
                class="rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-white shadow-sm transition-colors hover:bg-primary-hover disabled:opacity-60"
              >
                Save & Submit
              </button>
            </div>
          </div>
        </div>
      </Show>
    </>
  );
}
