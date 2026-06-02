import { For, type Accessor } from 'solid-js';
import type { SensitiveDetection } from '../McpSmartPasteModal.logic';

type McpSmartPasteSensitiveCheckProps = {
  sensitiveDetections: Accessor<SensitiveDetection[]>;
  replacedText: Accessor<string>;
};

export function McpSmartPasteSensitiveCheck(props: McpSmartPasteSensitiveCheckProps) {
  return (
    <div class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-amber-600 font-semibold">⚠️</span>
        <span class="text-sm font-semibold text-amber-800">
          Detected {props.sensitiveDetections().length} potential sensitive values
        </span>
      </div>
      <p class="text-xs text-amber-700 mb-3">
        It is recommended to replace secrets with environment variable placeholders before parsing. You can set the actual values in the system environment variables later.
      </p>

      <div class="space-y-2 max-h-[200px] overflow-y-auto mb-3">
        <For each={props.sensitiveDetections()}>
          {(det) => (
            <div class="flex items-center gap-2 text-xs bg-white rounded p-2 border border-amber-100">
              <span class="text-red-600 font-mono bg-red-50 px-1.5 py-0.5 rounded max-w-[180px] truncate" title={det.value}>
                {det.value}
              </span>
              <span class="text-gray-400">→</span>
              <span class="text-emerald-600 font-mono bg-emerald-50 px-1.5 py-0.5 rounded">
                {det.placeholder}
              </span>
              <span class="text-gray-400 ml-auto text-[10px]">{det.key}</span>
            </div>
          )}
        </For>
      </div>

      <div class="text-xs text-gray-500 mb-3">
        <div class="font-medium mb-1">Replacement Preview:</div>
        <pre class="bg-white border rounded p-2 max-h-[120px] overflow-y-auto text-[11px] whitespace-pre-wrap font-mono">{props.replacedText()}</pre>
      </div>
    </div>
  );
}
