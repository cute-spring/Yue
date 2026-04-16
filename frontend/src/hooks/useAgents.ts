import { createSignal, onMount } from 'solid-js';
import { Agent } from '../types';
import { useToast } from '../context/ToastContext';

export interface SlashAgentSelectorState {
  show: boolean;
  filter: string;
}

export type AgentSelectorKeyAction = 'next' | 'previous' | 'select' | 'close' | 'submit' | 'none';

export const deriveSlashAgentSelectorState = (input: string, cursorPos: number): SlashAgentSelectorState => {
  const safeCursor = Math.max(0, Math.min(cursorPos, input.length));
  const textBefore = input.substring(0, safeCursor);

  if (!textBefore.startsWith('/')) {
    return { show: false, filter: '' };
  }

  const filter = textBefore.substring(1);
  if (/\s/.test(filter)) {
    return { show: false, filter: '' };
  }

  return { show: true, filter };
};

export const filterAgentsByQuery = (agents: Agent[], query: string): Agent[] => {
  const filter = query.toLowerCase();
  return agents.filter((agent) => agent.name.toLowerCase().includes(filter));
};

export const getAgentSelectorKeyAction = (
  showSelector: boolean,
  matchCount: number,
  key: string,
  shiftKey: boolean,
): AgentSelectorKeyAction => {
  if (!showSelector) return 'none';
  if (key === 'Escape') return 'close';
  if (matchCount === 0) {
    return key === 'Enter' && !shiftKey ? 'submit' : 'none';
  }
  if (key === 'ArrowDown') return 'next';
  if (key === 'ArrowUp') return 'previous';
  if (key === 'Enter') return 'select';
  return 'none';
};

export const rewriteInputAfterSlashAgentSelection = (input: string, cursorPos: number): string => {
  const safeCursor = Math.max(0, Math.min(cursorPos, input.length));
  const textBefore = input.substring(0, safeCursor);
  if (!textBefore.startsWith('/')) return input;

  const firstWhitespacePos = input.search(/\s/);
  const tokenEnd = firstWhitespacePos === -1 ? input.length : firstWhitespacePos;
  const remaining = input.substring(tokenEnd);
  return remaining.trimStart();
};

export function useAgents(textareaRef?: () => HTMLTextAreaElement | undefined) {
  const toast = useToast();
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string | null>(null);
  const [showAgentSelector, setShowAgentSelector] = createSignal(false);
  const [agentFilter, setAgentFilter] = createSignal("");
  const [selectedIndex, setSelectedIndex] = createSignal(0);

  const loadAgents = async () => {
    try {
      const res = await fetch('/api/agents/');
      const data = await res.json();
      setAgents(data);
    } catch (e) {
      console.error("Failed to load agents", e);
      toast.error("Failed to load agents");
    }
  };

  const filteredAgents = () => filterAgentsByQuery(agents(), agentFilter());

  const selectAgent = (agent: Agent, input: string, setInput: (v: string) => void) => {
    const ref = textareaRef?.();
    const pos = ref?.selectionStart || 0;
    const newValue = rewriteInputAfterSlashAgentSelection(input, pos);
    setInput(newValue);
    setSelectedAgent(agent.id);
    setShowAgentSelector(false);
  };

  onMount(() => {
    loadAgents();
  });

  return {
    agents,
    selectedAgent,
    setSelectedAgent,
    showAgentSelector,
    setShowAgentSelector,
    agentFilter,
    setAgentFilter,
    selectedIndex,
    setSelectedIndex,
    loadAgents,
    filteredAgents,
    selectAgent
  };
}
