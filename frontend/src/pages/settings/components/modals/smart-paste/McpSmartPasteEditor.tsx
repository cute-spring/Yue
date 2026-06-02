import { Show, type Accessor } from 'solid-js';

type McpSmartPasteEditorProps = {
  phase: Accessor<'idle' | 'parsing'>;
  rawText: Accessor<string>;
  setRawText: (value: string) => void;
  parseHint: Accessor<string>;
  parseError: Accessor<string | null>;
  textareaRef: (element: HTMLTextAreaElement) => void;
};

export function McpSmartPasteEditor(props: McpSmartPasteEditorProps) {
  return (
    <>
      <div class="mb-4 space-y-3">
        <div class="p-3 bg-blue-50 border border-blue-100 rounded-lg">
          <div class="text-sm font-semibold text-blue-800 mb-1 flex items-center gap-1.5">
            <span class="text-base">💡</span> Smart Paste Guide
          </div>
          <ul class="text-xs text-blue-700 space-y-1 list-disc list-inside">
            <li>Paste <span class="font-mono bg-blue-100 px-1 rounded">Claude Desktop</span> JSON configuration directly.</li>
            <li>Supports command-line instructions including <span class="font-mono bg-blue-100 px-1 rounded">npx</span> or <span class="font-mono bg-blue-100 px-1 rounded">docker</span>.</li>
            <li>Supports <span class="font-mono bg-blue-100 px-1 rounded">HTTP/SSE</span> connection URLs.</li>
            <li>You can even describe it in natural language, e.g., "Add a local Python-based MCP service".</li>
            <li class="font-medium">Security: Secrets will be automatically replaced with placeholders. Please fill in actual values in the preview later.</li>
          </ul>
        </div>
      </div>

      <textarea
        ref={props.textareaRef}
        data-testid="smart-paste-textarea"
        class="w-full min-h-[180px] font-mono text-sm border rounded-lg p-3 bg-gray-50 resize-y"
        value={props.rawText()}
        onInput={(e) => props.setRawText(e.currentTarget.value)}
        placeholder={`{
  "mcpServers": {
    "example": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-example"]
    }
  }
}`}
        disabled={props.phase() === 'parsing'}
      />

      <Show when={props.phase() === 'parsing'}>
        <div class="flex items-center gap-2 text-sm text-blue-600 mt-3">
          <div class="animate-spin h-4 w-4 border-2 border-blue-300 border-t-blue-600 rounded-full" />
          <span>{props.parseHint() || 'Analyzing...'}</span>
        </div>
      </Show>

      <div class="text-xs text-gray-400 mt-1">Security: tokens / passwords will be replaced with ${"{"}ENV_NAME{"}"} placeholders</div>

      <Show when={props.parseError()}>
        <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {props.parseError()}
        </div>
      </Show>
    </>
  );
}
