import { Show } from 'solid-js';
import { Agent } from '../../../types';

type ActiveSkill = { name: string; version: string } | null;

type ChatHeaderProps = {
  showHistory: boolean;
  onToggleHistory: () => void;
  currentAgent: Agent | null | undefined;
  activeAgentName: string;
  isTyping: boolean;
  selectedWorkspaceName: string | null;
  activeSkill: ActiveSkill;
  traceUiEnabled: boolean;
  onOpenTrace: () => void;
  showKnowledge: boolean;
  onToggleKnowledge: () => void;
};

export default function ChatHeader(props: ChatHeaderProps) {
  return (
    <div class="h-16 px-6 border-b border-border flex items-center justify-between bg-surface/80 backdrop-blur-md z-10 sticky top-0">
      <div class="flex items-center gap-4 min-w-0">
        <button
          onClick={props.onToggleHistory}
          class="p-2 -ml-2 text-text-secondary hover:bg-primary/10 rounded-xl transition-all active:scale-90"
          title={props.showHistory ? 'Hide History' : 'Show History'}
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div class="flex items-center gap-3.5 truncate">
          <div class="relative">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary font-bold shrink-0 border border-primary/10 shadow-sm overflow-hidden">
              <Show when={props.currentAgent?.avatar} fallback={props.activeAgentName.charAt(0)}>
                <img src={props.currentAgent?.avatar} alt={props.activeAgentName} class="w-full h-full object-cover" />
              </Show>
            </div>
            <div
              class={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-surface ${
                props.isTyping ? 'bg-primary animate-pulse' : 'bg-emerald-500'
              }`}
            />
          </div>
          <div class="truncate">
            <h3 class="font-bold text-text-primary text-base truncate leading-tight">{props.activeAgentName}</h3>
            <p class="text-[11px] text-text-secondary font-medium uppercase tracking-widest opacity-70">
              {props.isTyping ? 'Processing Intelligence...' : 'System Ready'}
            </p>
          </div>
        </div>

        <Show when={props.selectedWorkspaceName}>
          <div class="hidden md:flex items-center">
            <span class="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1 uppercase tracking-wider">
              {props.selectedWorkspaceName}
            </span>
          </div>
        </Show>

        <Show when={props.currentAgent?.skill_mode && props.currentAgent?.skill_mode !== 'off'}>
          <div class="hidden md:flex items-center gap-2 ml-4">
            <span class="text-[10px] uppercase tracking-wider font-bold text-violet-700 bg-violet-100 border border-violet-200 rounded-full px-2 py-1">
              {props.currentAgent?.skill_mode}
            </span>
            <Show when={props.activeSkill}>
              <span class="text-[10px] font-bold text-emerald-700 bg-emerald-100 border border-emerald-200 rounded-full px-2 py-1">
                Active: {props.activeSkill!.name}@{props.activeSkill!.version}
              </span>
            </Show>
          </div>
        </Show>
      </div>

      <div class="flex items-center gap-2">
        <Show when={props.traceUiEnabled}>
          <button
            onClick={props.onOpenTrace}
            class="p-2.5 rounded-xl text-text-secondary hover:bg-primary/10 hover:text-primary transition-all duration-300 active:scale-90"
            title="Open Trace Inspector"
            aria-label="Open trace inspector"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-6m3 6V7m3 10v-4M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </button>
        </Show>
        <button
          onClick={props.onToggleKnowledge}
          class={`p-2.5 rounded-xl transition-all duration-300 active:scale-90 ${
            props.showKnowledge ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-text-secondary hover:bg-primary/10 hover:text-primary'
          }`}
          title="Toggle Knowledge Intelligence"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
