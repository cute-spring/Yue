import { For, Show } from 'solid-js';
import { Agent } from '../types';

interface AgentCardProps {
  agent: Agent;
  onEdit: (agent: Agent) => void;
  onDelete: (id: string) => void;
}

export function AgentCard(props: AgentCardProps) {
  return (
    <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
      <div class="flex justify-between items-start mb-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-lg shadow-inner">
            {props.agent.name.charAt(0)}
          </div>
          <div>
            <h3 class="font-bold text-gray-800">{props.agent.name}</h3>
            <div class="flex items-center gap-1.5 text-xs text-gray-500">
              <span class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600 font-medium">{props.agent.provider}</span>
              <span>•</span>
              <span>{props.agent.model}</span>
            </div>
          </div>
        </div>
        <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            onClick={() => props.onEdit(props.agent)}
            class="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
            title="Edit"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button 
            onClick={() => props.onDelete(props.agent.id)}
            class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
      
      <div class="bg-gray-50 p-3 rounded-xl mb-4 border border-gray-100">
        <p class="text-xs text-gray-600 font-mono line-clamp-3 leading-relaxed">
          {props.agent.system_prompt}
        </p>
      </div>
      
      <div class="flex items-center gap-2 overflow-hidden">
        <span class="text-xs font-semibold text-gray-400 shrink-0">TOOLS</span>
        <div class="flex flex-wrap gap-1">
          <For each={props.agent.enabled_tools.slice(0, 3)}>
            {tool => (
              <span class="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-100">
                {tool}
              </span>
            )}
          </For>
          <Show when={props.agent.enabled_tools.length > 3}>
            <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
              +{props.agent.enabled_tools.length - 3}
            </span>
          </Show>
          <Show when={props.agent.enabled_tools.length === 0}>
            <span class="text-[10px] text-gray-400 italic">No tools enabled</span>
          </Show>
        </div>
      </div>
      <Show when={props.agent.doc_roots && props.agent.doc_roots.length > 0}>
        <div class="flex items-center gap-2 mt-2 overflow-hidden">
          <span class="text-xs font-semibold text-gray-400 shrink-0">SCOPE</span>
          <div class="flex flex-wrap gap-1">
            <For each={props.agent.doc_roots?.slice(0, 2) || []}>
              {root => (
                <span class="text-[10px] bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-100">
                  {root}
                </span>
              )}
            </For>
            <Show when={(props.agent.doc_roots?.length || 0) > 2}>
              <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                +{(props.agent.doc_roots?.length || 0) - 2}
              </span>
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
