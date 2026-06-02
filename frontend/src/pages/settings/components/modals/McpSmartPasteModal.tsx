import { Show } from 'solid-js';
import type { ParsedMcpConfig, SmartPasteResponse } from '../../types';
import { McpSmartPasteEditor } from './smart-paste/McpSmartPasteEditor';
import { McpSmartPastePreview } from './smart-paste/McpSmartPastePreview';
import { McpSmartPasteSensitiveCheck } from './smart-paste/McpSmartPasteSensitiveCheck';
import { useMcpSmartPasteState } from './smart-paste/useMcpSmartPasteState';

type McpSmartPasteModalProps = {
  existingNames: string[];
  onClose: () => void;
  onParse: (rawText: string, signal: AbortSignal) => Promise<SmartPasteResponse>;
  onSave: (configs: ParsedMcpConfig[]) => Promise<void>;
};

export function McpSmartPasteModal(props: McpSmartPasteModalProps) {
  const state = useMcpSmartPasteState(props);

  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={props.onClose}>
      <div class="w-[720px] max-h-[85vh] bg-white rounded-xl border shadow-xl flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div class="px-4 py-3 border-b flex justify-between items-center shrink-0">
          <div class="font-semibold text-lg">Smart Paste (AI)</div>
          <button onClick={props.onClose} class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          <Show when={state.phase() === 'sensitive_check'}>
            <McpSmartPasteSensitiveCheck
              sensitiveDetections={state.sensitiveDetections}
              replacedText={state.replacedText}
            />
          </Show>

          <Show when={state.phase() === 'idle' || state.phase() === 'parsing'}>
            <McpSmartPasteEditor
              phase={() => state.phase() === 'parsing' ? 'parsing' : 'idle'}
              rawText={state.rawText}
              setRawText={state.setRawText}
              parseHint={state.parseHint}
              parseError={state.parseError}
              textareaRef={() => {}}
            />
          </Show>

          <Show when={state.phase() === 'preview' || state.phase() === 'saving'}>
            <McpSmartPastePreview
              phase={() => state.phase() === 'saving' ? 'saving' : 'preview'}
              results={state.results}
              saveError={state.saveError}
              saveSuccess={state.saveSuccess}
              handleUpdateCandidate={state.handleUpdateCandidate}
              handleTransportChange={state.handleTransportChange}
              handleToggleSelected={state.handleToggleSelected}
              handleDeleteCandidate={state.handleDeleteCandidate}
              handleUpdateHeader={state.handleUpdateHeader}
              handleRemoveHeader={state.handleRemoveHeader}
              handleAddHeader={state.handleAddHeader}
              handleUpdateEnv={state.handleUpdateEnv}
              handleRemoveEnv={state.handleRemoveEnv}
              handleAddEnv={state.handleAddEnv}
            />
          </Show>
        </div>

        <div class="px-4 py-3 flex justify-between gap-2 border-t shrink-0">
          <div>
            <Show when={state.phase() === 'parsing'}>
              <button onClick={state.handleCancelParse} class="px-3 py-1.5 rounded-md border text-sm">
                Cancel
              </button>
            </Show>
          </div>
          <div class="flex gap-2">
            <Show when={state.phase() === 'sensitive_check'}>
              <button onClick={state.handleSensitiveBackToEdit} class="px-3 py-1.5 rounded-md border text-sm">
                Back to Edit
              </button>
              <div class="flex gap-2">
                <button onClick={state.handleSensitiveSendAnyway} class="px-3 py-1.5 rounded-md border text-sm text-gray-500">
                  Skip and Send
                </button>
                <button onClick={state.handleSensitiveReplaceAll} class="px-4 py-1.5 rounded-md bg-amber-600 text-white text-sm">
                  Replace All
                </button>
              </div>
            </Show>
            <Show when={state.phase() === 'idle'}>
              <button onClick={props.onClose} class="px-3 py-1.5 rounded-md border text-sm">
                Cancel
              </button>
              <button
                onClick={() => { void state.handleParse(); }}
                disabled={!state.rawText().trim()}
                data-testid="smart-paste-parse-btn"
                class="px-4 py-1.5 rounded-md bg-blue-700 text-white text-sm disabled:opacity-50"
              >
                AI Parse
              </button>
            </Show>
            <Show when={state.phase() === 'preview'}>
              <button onClick={state.handleReparse} class="px-3 py-1.5 rounded-md border text-sm">
                Reparse
              </button>
              <button
                onClick={() => { void state.handleSave(); }}
                disabled={state.results().length === 0}
                data-testid="smart-paste-save-btn"
                class="px-4 py-1.5 rounded-md bg-emerald-600 text-white text-sm disabled:opacity-50"
              >
                Confirm and Save
              </button>
            </Show>
            <Show when={state.phase() === 'preview' && state.parseError()}>
              <button onClick={state.handleRetry} class="px-3 py-1.5 rounded-md border text-sm">
                Retry
              </button>
            </Show>
            <Show when={state.phase() === 'saving'}>
              <div class="flex items-center gap-2 text-sm text-gray-500">
                <div class="animate-spin h-4 w-4 border-2 border-gray-300 border-t-emerald-600 rounded-full" />
                Saving...
              </div>
            </Show>
          </div>
        </div>
      </div>
    </div>
  );
}
