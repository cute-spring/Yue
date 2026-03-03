import { Component, Show, createSignal } from 'solid-js';
import { ToolCall } from '../types';

interface ToolCallItemProps {
  toolCall: ToolCall;
}

const ToolCallItem: Component<ToolCallItemProps> = (props) => {
  const [isExpanded, setIsExpanded] = createSignal(false);

  const getStatusColor = () => {
    switch (props.toolCall.status) {
      case 'running': return 'text-blue-500';
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusBg = () => {
    switch (props.toolCall.status) {
      case 'running': return 'bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800';
      case 'success': return 'bg-green-50 dark:bg-green-900/20 border-green-100 dark:border-green-800';
      case 'error': return 'bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-800';
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
    <div class={`mt-2 border rounded-lg overflow-hidden transition-all duration-200 ${getStatusBg()}`}>
      <div 
        class="px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-black/5 dark:hover:bg-white/5"
        onClick={() => setIsExpanded(!isExpanded())}
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="flex-shrink-0">
            <Show when={props.toolCall.status === 'running'}>
              <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </Show>
            <Show when={props.toolCall.status === 'success'}>
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-green-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
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
          <span class="text-sm font-medium truncate font-mono">
            {formatToolName(props.toolCall.tool_name)}
          </span>
          <Show when={props.toolCall.duration_ms}>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/10 text-gray-500 dark:text-gray-400 font-mono">
              {Math.round(props.toolCall.duration_ms!)}ms
            </span>
          </Show>
        </div>
        
        <div class="flex items-center gap-2">
          <span class={`text-[10px] uppercase font-bold tracking-wider ${getStatusColor()}`}>
            {props.toolCall.status}
          </span>
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            class={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded() ? 'rotate-180' : ''}`} 
            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          >
            <path d="m6 9 6 6 6-6"/>
          </svg>
        </div>
      </div>

      <Show when={isExpanded()}>
        <div class="px-3 pb-3 pt-1 border-t border-black/5 dark:border-white/5 space-y-3">
          <Show when={props.toolCall.args}>
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase mb-1">Arguments</div>
              <pre class="text-[11px] bg-black/5 dark:bg-black/20 p-2 rounded overflow-x-auto font-mono text-gray-700 dark:text-gray-300">
                {JSON.stringify(props.toolCall.args, null, 2)}
              </pre>
            </div>
          </Show>
          
          <Show when={props.toolCall.result}>
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase mb-1">Result</div>
              <pre class="text-[11px] bg-black/5 dark:bg-black/20 p-2 rounded overflow-x-auto font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
                {typeof props.toolCall.result === 'string' ? props.toolCall.result : JSON.stringify(props.toolCall.result, null, 2)}
              </pre>
            </div>
          </Show>

          <Show when={props.toolCall.error}>
            <div>
              <div class="text-[10px] font-bold text-red-400 uppercase mb-1">Error</div>
              <div class="text-[11px] text-red-600 dark:text-red-400 font-mono italic">
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
