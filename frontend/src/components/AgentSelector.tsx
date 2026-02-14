import { For, Show } from 'solid-js';
import { Agent } from '../types';

interface AgentSelectorProps {
  show: boolean;
  agents: Agent[];
  selectedIndex: number;
  onSelect: (agent: Agent) => void;
}

export default function AgentSelector(props: AgentSelectorProps) {
  return (
    <Show when={props.show}>
      <div class="absolute bottom-full left-0 mb-4 w-80 bg-surface border border-border rounded-[24px] shadow-2xl overflow-hidden z-50 animate-in slide-in-from-bottom-4 duration-300 backdrop-blur-xl">
        <div class="bg-primary/5 px-5 py-3 border-b border-border flex items-center justify-between">
          <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Mention Intelligence Agent</span>
          <span class="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">@</span>
        </div>
        <div class="max-h-72 overflow-y-auto p-2 scrollbar-thin">
          <For each={props.agents}>
            {(agent, index) => (
              <button
                onClick={() => props.onSelect(agent)}
                class={`w-full text-left px-4 py-3 flex items-center justify-between rounded-xl transition-all duration-200 ${
                  props.selectedIndex === index() ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[1.02]' : 'hover:bg-primary/5 text-text-primary'
                }`}
              >
                <div class="flex items-center gap-3">
                  <div class={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${props.selectedIndex === index() ? 'bg-white/20' : 'bg-primary/10 text-primary'}`}>
                    <Show when={agent.avatar} fallback={agent.name.charAt(0)}>
                      <img src={agent.avatar} alt={agent.name} class="w-full h-full object-cover rounded-lg" />
                    </Show>
                  </div>
                  <div>
                    <span class="font-bold text-sm block">{agent.name}</span>
                    <span class={`text-[10px] block opacity-70 ${props.selectedIndex === index() ? 'text-white' : 'text-text-secondary'}`}>Specialized Intelligence</span>
                  </div>
                </div>
                <Show when={props.selectedIndex === index()}>
                  <div class="flex items-center gap-1">
                    <span class="text-[9px] font-black tracking-tighter border border-white/30 px-1 rounded">ENTER</span>
                  </div>
                </Show>
              </button>
            )}
          </For>
          <Show when={props.agents.length === 0}>
            <div class="px-4 py-10 text-center">
              <div class="text-text-secondary opacity-30 mb-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <p class="text-sm text-text-secondary italic">No matching agents</p>
            </div>
          </Show>
        </div>
      </div>
    </Show>
  );
}
