import { createSignal, onMount } from 'solid-js';
import { Agent } from '../types';
import { useToast } from '../context/ToastContext';

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

  const filteredAgents = () => {
    const filter = agentFilter().toLowerCase();
    return agents().filter(a => a.name.toLowerCase().includes(filter));
  };

  const selectAgent = (agent: Agent, input: string, setInput: (v: string) => void) => {
    const ref = textareaRef?.();
    const pos = ref?.selectionStart || 0;
    const textBefore = input.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');
    
    const newValue = input.substring(0, lastAtPos) + input.substring(pos);
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
