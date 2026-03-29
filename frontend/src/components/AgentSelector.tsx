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
      <div class="absolute bottom-full left-0 mb-4 w-80 bg-surface/98 border border-border/80 rounded-[24px] shadow-[0_18px_40px_rgba(20,35,30,0.14)] overflow-hidden z-50 animate-in slide-in-from-bottom-4 duration-300 backdrop-blur-xl">
        <div class="bg-background/70 px-5 py-3.5 border-b border-border/70 flex items-center justify-between">
          <span class="text-[11px] font-medium text-primary">Mention Intelligence Agent</span>
          <span class="text-[11px] bg-primary/10 text-primary px-2.5 py-0.5 rounded-full font-semibold">@</span>
        </div>
        <div class="max-h-72 overflow-y-auto p-2.5 scrollbar-thin">
          <For each={props.agents}>
            {(agent, index) => (
              <button
                onClick={() => props.onSelect(agent)}
                class={`w-full text-left px-4 py-3.5 flex items-center justify-between rounded-[1rem] transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 ${
                  props.selectedIndex === index() ? 'bg-primary/10 text-text-primary ring-1 ring-primary/18 shadow-sm' : 'hover:bg-background text-text-primary'
                }`}
              >
                <div class="flex items-center gap-3">
                  <div class={`w-9 h-9 rounded-xl flex items-center justify-center text-sm font-semibold ${props.selectedIndex === index() ? 'bg-primary/12 text-primary' : 'bg-primary/10 text-primary'}`}>
                    <Show when={agent.avatar} fallback={agent.name.charAt(0)}>
                      <img src={agent.avatar} alt={agent.name} class="w-full h-full object-cover rounded-xl" />
                    </Show>
                  </div>
                  <div>
                    <span class="font-semibold text-[14px] block">{agent.name}</span>
                    <span class={`text-[11px] block mt-0.5 ${props.selectedIndex === index() ? 'text-text-secondary' : 'text-text-secondary'}`}>Specialized Intelligence</span>
                  </div>
                </div>
                <Show when={props.selectedIndex === index()}>
                  <div class="flex items-center gap-1">
                    <span class="text-[10px] font-medium tracking-tight border border-primary/20 bg-primary/5 text-primary px-2 py-0.5 rounded-full">Enter</span>
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
