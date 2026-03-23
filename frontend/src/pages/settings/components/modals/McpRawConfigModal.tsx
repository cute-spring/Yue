type McpRawConfigModalProps = {
  mcpConfig: string;
  setMcpConfig: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
};

export function McpRawConfigModal(props: McpRawConfigModalProps) {
  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
      <div class="w-[800px] bg-white rounded-xl border shadow-lg">
        <div class="px-4 py-2 border-b flex justify-between items-center">
          <div class="font-semibold">Raw Config (JSON)</div>
          <button onClick={props.onClose}>✕</button>
        </div>
        <div class="p-4">
          <textarea
            data-testid="mcp-raw-textarea"
            class="w-full h-80 font-mono border rounded-lg p-3 bg-gray-50"
            value={props.mcpConfig}
            onInput={(e) => props.setMcpConfig(e.currentTarget.value)}
          />
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
