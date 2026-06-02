import { For, Show, type Accessor } from 'solid-js';

import { getFileExtension, isImageFile, removeAttachmentAt } from './attachmentUtils';

type AttachmentPreviewStripProps = {
  files: File[];
  previewUrls: Accessor<string[]>;
  attachmentCompositionHint: Accessor<string>;
  visionCapabilityHint: Accessor<string>;
  formatSize: (size: number) => string;
  setFiles: (files: File[]) => void;
};

export default function AttachmentPreviewStrip(props: AttachmentPreviewStripProps) {
  return (
    <>
      <Show when={props.files.length > 0}>
        <div class="mt-2 px-2">
          <Show when={props.attachmentCompositionHint()}>
            <div class="mb-2 px-1 text-[12px] font-medium text-text-secondary">
              {props.attachmentCompositionHint()}
            </div>
          </Show>
          <div class="flex items-center gap-2 overflow-x-auto">
            <For each={props.files}>
              {(file: File, index: () => number) => (
                <div class="flex items-center gap-2 px-2 py-1.5 rounded-xl border border-border bg-surface text-xs min-w-[200px]">
                  <Show
                    when={isImageFile(file)}
                    fallback={
                      <div class="w-10 h-10 rounded-lg border border-border/60 bg-background/50 shrink-0 flex items-center justify-center text-[10px] font-bold text-text-secondary uppercase">
                        {getFileExtension(file.name).replace('.', '') || 'file'}
                      </div>
                    }
                  >
                    <img
                      src={props.previewUrls()[index()]}
                      alt={file.name}
                      class="w-10 h-10 rounded-lg object-cover border border-border/60 bg-background/50 shrink-0"
                    />
                  </Show>
                  <div class="min-w-0 flex-1">
                    <div class="max-w-[150px] truncate font-semibold text-text-primary">{file.name}</div>
                    <div class="text-text-secondary">{props.formatSize(file.size)}</div>
                  </div>
                  <button
                    type="button"
                    class="text-text-secondary hover:text-rose-500"
                    onClick={() => props.setFiles(removeAttachmentAt(props.files, index()))}
                  >
                    ×
                  </button>
                </div>
              )}
            </For>
            <button
              type="button"
              class="px-3 py-1.5 rounded-xl border border-border text-xs text-text-secondary hover:text-rose-500"
              onClick={() => props.setFiles([])}
            >
              Clear
            </button>
          </div>
        </div>
      </Show>
      <Show when={props.visionCapabilityHint()}>
        <div class="mt-2 px-3 py-2 rounded-xl border border-amber-400/30 bg-amber-500/10 text-[12px] text-amber-700">
          {props.visionCapabilityHint()}
        </div>
      </Show>
    </>
  );
}
