type McpMarketplaceModalProps = {
  onClose: () => void;
};

export function McpMarketplaceModal(props: McpMarketplaceModalProps) {
  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
      <div class="w-[680px] bg-white rounded-xl border shadow-lg">
        <div class="px-4 py-2 border-b flex justify-between items-center">
          <div class="font-semibold">Add from Marketplace</div>
          <button onClick={props.onClose}>✕</button>
        </div>
        <div class="p-6">
          <p class="text-sm text-gray-600">Marketplace integration is coming soon. This is a mock dialog.</p>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div class="p-3 border rounded-lg">
              <div class="font-semibold">Playwright MCP</div>
              <div class="text-xs text-gray-500">Browser automation tools</div>
            </div>
            <div class="p-3 border rounded-lg">
              <div class="font-semibold">Filesystem MCP</div>
              <div class="text-xs text-gray-500">File operations</div>
            </div>
          </div>
        </div>
        <div class="px-4 py-3 flex justify-end gap-2 border-t">
          <button onClick={props.onClose} class="px-3 py-1.5 rounded-md border">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
