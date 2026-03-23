type McpManualModalProps = {
  manualText: string;
  setManualText: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
};

export function McpManualModal(props: McpManualModalProps) {
  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
      <div class="w-[640px] bg-white rounded-xl border shadow-lg">
        <div class="px-4 py-2 border-b flex justify-between items-center">
          <div class="font-semibold">Configure Manually</div>
          <button onClick={props.onClose}>✕</button>
        </div>
        <div class="p-4">
          <textarea
            data-testid="mcp-manual-textarea"
            class="w-full h-64 font-mono border rounded-lg p-3 bg-gray-50"
            value={props.manualText}
            onInput={(e) => props.setManualText(e.currentTarget.value)}
          />
          <div class="text-xs text-gray-500 mt-2">
            Please confirm the source and identify risks before configuration.
          </div>
        </div>
        <div class="px-4 py-3 flex justify-end gap-2 border-t">
          <button onClick={props.onClose} class="px-3 py-1.5 rounded-md border">
            Cancel
          </button>
          <button onClick={props.onConfirm} class="px-3 py-1.5 rounded-md bg-emerald-600 text-white">
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
