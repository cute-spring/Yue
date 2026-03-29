import { Component, For, Show, createSignal } from 'solid-js';
import { ToolCall } from '../types';

interface ToolCallItemProps {
  toolCall: ToolCall;
}

export const parseToolCallResultPayload = (result: ToolCall['result']): Record<string, any> | null => {
  if (!result) return null;
  if (typeof result === 'object') return result as Record<string, any>;
  if (typeof result !== 'string') return null;
  try {
    return JSON.parse(result) as Record<string, any>;
  } catch {
    return null;
  }
};

export const getScreenshotPreview = (
  toolName: string,
  result: ToolCall['result'],
): { url: string; alt: string } | null => {
  const payload = parseToolCallResultPayload(result);
  if (!payload) return null;
  const artifact = payload.artifact;
  const artifactKind =
    artifact && typeof artifact === 'object' && typeof artifact.kind === 'string'
      ? artifact.kind.toLowerCase()
      : '';
  const isScreenshot =
    toolName === 'browser_screenshot' ||
    toolName === 'builtin:browser_screenshot' ||
    artifactKind === 'screenshot';
  if (!isScreenshot) return null;
  const downloadUrl = typeof payload.download_url === 'string' ? payload.download_url.trim() : '';
  if (!downloadUrl) return null;
  const filename =
    typeof payload.filename === 'string' && payload.filename.trim()
      ? payload.filename.trim()
      : 'browser screenshot';
  return {
    url: downloadUrl,
    alt: filename,
  };
};

export const getDownloadArtifact = (
  toolName: string,
  result: ToolCall['result'],
): { url: string; filename: string; kindLabel: string } | null => {
  const payload = parseToolCallResultPayload(result);
  if (!payload) return null;
  const downloadUrl = typeof payload.download_url === 'string' ? payload.download_url.trim() : '';
  if (!downloadUrl) return null;

  const screenshot = getScreenshotPreview(toolName, result);
  if (screenshot) return null;

  const filename =
    typeof payload.filename === 'string' && payload.filename.trim()
      ? payload.filename.trim()
      : downloadUrl.split('/').pop() || 'exported artifact';
  const extension = filename.includes('.') ? filename.split('.').pop()!.toUpperCase() : 'FILE';
  return {
    url: downloadUrl,
    filename,
    kindLabel: extension,
  };
};

export const isBrowserSnapshotTool = (toolName: string): boolean => {
  return toolName === 'browser_snapshot' || toolName === 'builtin:browser_snapshot';
};

export const isSimpleArgumentValue = (value: unknown): boolean => {
  return (
    value === null ||
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  );
};

export const getArgumentEntries = (
  args: ToolCall['args'],
): Array<{ key: string; value: string }> | null => {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return null;
  const entries = Object.entries(args);
  if (entries.length === 0) return null;
  if (!entries.every(([, value]) => isSimpleArgumentValue(value))) return null;
  return entries.map(([key, value]) => ({
    key,
    value: value === null ? 'null' : String(value),
  }));
};

const getToolSummaryEntries = (toolCall: ToolCall): Array<{ key: string; value: string }> => {
  const entries = getArgumentEntries(toolCall.args) || [];
  const preferredKeys = ['url', 'query', 'file', 'filename', 'format', 'label', 'element_ref'];
  const preferred = preferredKeys
    .map((key) => entries.find((entry) => entry.key === key))
    .filter((entry): entry is { key: string; value: string } => !!entry);
  const fallback = entries.filter((entry) => !preferred.some((item) => item.key === entry.key));
  return [...preferred, ...fallback].slice(0, 2);
};

const ToolCallItem: Component<ToolCallItemProps> = (props) => {
  const screenshotPayload = () => getScreenshotPreview(props.toolCall.tool_name, props.toolCall.result);
  const downloadArtifact = () => getDownloadArtifact(props.toolCall.tool_name, props.toolCall.result);
  const argumentEntries = () => getArgumentEntries(props.toolCall.args);
  const summaryEntries = () => getToolSummaryEntries(props.toolCall);
  const isVisualArtifactTool = () =>
    !!screenshotPayload() || !!downloadArtifact() || isBrowserSnapshotTool(props.toolCall.tool_name);
  const [isExpanded, setIsExpanded] = createSignal(false);
  const shouldShowRawResult = () => props.toolCall.result && !isVisualArtifactTool();
  const canExpand = () => !!props.toolCall.error || (!!props.toolCall.args && !isVisualArtifactTool()) || (!!props.toolCall.result && !isVisualArtifactTool());

  const getStatusColor = () => {
    switch (props.toolCall.status) {
      case 'running': return 'text-blue-700 dark:text-blue-300';
      case 'success': return 'text-emerald-800 dark:text-emerald-300';
      case 'error': return 'text-red-700 dark:text-red-300';
      default: return 'text-gray-700 dark:text-gray-300';
    }
  };

  const getStatusBg = () => {
    switch (props.toolCall.status) {
      case 'running': return 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800';
      case 'success': return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-800';
      case 'error': return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
      default: return 'bg-gray-50 dark:bg-gray-800 border-gray-100 dark:border-gray-700';
    }
  };

  const formatToolName = (name: string) => {
    // Remove mcp__ prefix and sanitization if present
    if (name.startsWith('mcp__')) {
      const parts = name.split('__');
      if (parts.length >= 3) {
        return `${parts[1]}:${parts[2]}`;
      }
    }
    return name;
  };

  return (
    <div class={`mt-2 rounded-2xl border transition-all duration-200 ${getStatusBg()}`}>
      <div 
        class={`px-4 py-3 flex items-start justify-between gap-3 ${canExpand() ? 'cursor-pointer hover:bg-black/5 dark:hover:bg-white/5' : ''}`}
        onClick={() => canExpand() && setIsExpanded(!isExpanded())}
      >
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-3 min-w-0">
            <div class="flex-shrink-0">
              <Show when={props.toolCall.status === 'running'}>
                <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </Show>
              <Show when={props.toolCall.status === 'success'}>
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-emerald-600 dark:text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
              </Show>
              <Show when={props.toolCall.status === 'error'}>
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
              </Show>
            </div>
            <span class="text-[14px] font-semibold truncate font-mono text-text-primary">
              {formatToolName(props.toolCall.tool_name)}
            </span>
            <Show when={props.toolCall.duration_ms}>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-white/75 text-text-secondary font-mono border border-black/5">
                {Math.round(props.toolCall.duration_ms!)}ms
              </span>
            </Show>
            <span class={`text-[10px] font-semibold uppercase tracking-[0.14em] ${getStatusColor()}`}>
              {props.toolCall.status}
            </span>
          </div>
          <Show when={summaryEntries().length > 0}>
            <div class="mt-2 flex flex-wrap gap-2 pl-7">
              <For each={summaryEntries()}>
                {(entry) => (
                  <div class="inline-flex max-w-full items-center gap-1.5 rounded-full bg-white/65 px-2.5 py-1 text-[10px] text-text-secondary border border-black/5">
                    <span class="font-semibold uppercase tracking-[0.12em] text-text-secondary/70">{entry.key}</span>
                    <span class="truncate font-mono text-text-primary/85 max-w-[26rem]">{entry.value}</span>
                  </div>
                )}
              </For>
            </div>
          </Show>
        </div>
        
        <Show when={canExpand()}>
          <div class="flex items-center gap-2 pt-0.5">
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              class={`w-4 h-4 text-text-secondary/60 transition-transform duration-200 ${isExpanded() ? 'rotate-180' : ''}`} 
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            >
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
        </Show>
      </div>

      <Show when={isExpanded()}>
        <div class="px-4 pb-4 pt-2 border-t border-black/5 space-y-3">
          <Show when={props.toolCall.args && !isVisualArtifactTool()}>
            <div>
              <div class="text-[11px] font-medium text-text-secondary mb-1.5">Arguments</div>
              <Show
                when={argumentEntries()}
                fallback={
                  <pre class="text-[12px] bg-white/70 dark:bg-black/20 p-3 rounded-xl overflow-x-auto font-mono text-text-primary dark:text-gray-200 border border-black/5 dark:border-white/10 leading-relaxed">
                    {JSON.stringify(props.toolCall.args, null, 2)}
                  </pre>
                }
              >
                {(entries) => (
                  <div class="grid gap-2 rounded-2xl border border-black/5 bg-white/70 p-3 shadow-sm">
                    <For each={entries()}>
                      {(entry) => (
                        <div class="rounded-xl border border-border/60 bg-white/70 px-3 py-2">
                          <span class="block text-[11px] font-semibold uppercase tracking-[0.12em] text-text-secondary/80">
                            {entry.key}
                          </span>
                          <span class="mt-1 block break-words text-left font-mono text-[12px] text-text-primary">
                            {entry.value}
                          </span>
                        </div>
                      )}
                    </For>
                  </div>
                )}
              </Show>
            </div>
          </Show>
          
          <Show when={props.toolCall.result && !isVisualArtifactTool()}>
            <div>
              <div class="text-[11px] font-medium text-text-secondary mb-1.5">Result</div>
              <Show when={shouldShowRawResult()}>
                <pre class="text-[12px] bg-white/75 dark:bg-black/20 p-3 rounded-xl overflow-x-auto font-mono text-text-primary dark:text-gray-200 whitespace-pre-wrap max-h-60 overflow-y-auto border border-black/5 dark:border-white/10 leading-relaxed">
                  {typeof props.toolCall.result === 'string' ? props.toolCall.result : JSON.stringify(props.toolCall.result, null, 2)}
                </pre>
              </Show>
            </div>
          </Show>

          <Show when={props.toolCall.error}>
            <div>
              <div class="text-[11px] font-medium text-red-500 mb-1.5">Error</div>
              <div class="text-[12px] text-red-600 dark:text-red-400 font-mono italic leading-relaxed">
                {props.toolCall.error}
              </div>
            </div>
          </Show>
        </div>
      </Show>

    </div>
  );
};

export default ToolCallItem;
