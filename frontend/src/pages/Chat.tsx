import { createSignal, For, onMount, Show } from 'solid-js';
import { marked } from 'marked';

type Agent = {
  id: string;
  name: string;
};

export default function Chat() {
  const [messages, setMessages] = createSignal<{role: string, content: string}[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string>("");
  const [showAgentSelector, setShowAgentSelector] = createSignal(false);
  const [agentFilter, setAgentFilter] = createSignal("");
  const [selectedIndex, setSelectedIndex] = createSignal(0);

  const filteredAgents = () => {
    const filter = agentFilter().toLowerCase();
    return agents().filter(a => a.name.toLowerCase().includes(filter));
  };

  const handleInput = (e: InputEvent & { currentTarget: HTMLInputElement }) => {
    const value = e.currentTarget.value;
    const pos = e.currentTarget.selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');

    if (lastAtPos !== -1 && (lastAtPos === 0 || textBefore[lastAtPos - 1] === ' ')) {
      setShowAgentSelector(true);
      setAgentFilter(textBefore.substring(lastAtPos + 1));
      setSelectedIndex(0);
    } else {
      setShowAgentSelector(false);
    }
    setInput(value);
  };

  const handleKeyDown = (e: KeyboardEvent & { currentTarget: HTMLInputElement }) => {
    if (showAgentSelector()) {
      const list = filteredAgents();
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() + 1) % list.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() - 1 + list.length) % list.length);
      } else if (e.key === 'Enter' && list.length > 0) {
        e.preventDefault();
        selectAgent(list[selectedIndex()]);
      } else if (e.key === 'Escape') {
        setShowAgentSelector(false);
      }
    }
  };

  const selectAgent = (agent: Agent) => {
    const value = input();
    const pos = (document.activeElement as HTMLInputElement).selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');
    
    const newValue = value.substring(0, lastAtPos) + value.substring(pos);
    setInput(newValue);
    setSelectedAgent(agent.id);
    setShowAgentSelector(false);
  };

  onMount(async () => {
    try {
      const res = await fetch('/api/agents/');
      const data = await res.json();
      setAgents(data);
      if (data.length > 0) setSelectedAgent(data[0].id);
    } catch (e) {
      console.error("Failed to load agents", e);
    }
  });

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    const text = input().trim();
    if (!text) return;
    
    // Use selected agent or fallback to default if none selected (though UI enforces selection if list not empty)
    const agentId = selectedAgent() || 'default';

    setMessages([...messages(), { role: 'user', content: text }]);
    setInput("");
    setIsTyping(true);
    setMessages(prev => [...prev, { role: 'assistant', content: "" }]);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          agent_id: agentId,
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                accumulatedResponse += data.content;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  const lastIndex = newMsgs.length - 1;
                  newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
                  return newMsgs;
                });
              } catch (e) {}
            }
          }
        }
      }
    } catch (err) {
      console.error("Chat error:", err);
    } finally {
      setIsTyping(false);
    }
  };

  const activeAgentName = () => {
    const agent = agents().find(a => a.id === selectedAgent());
    return agent ? agent.name : 'Default Agent';
  };

  return (
    <div class="flex flex-col h-full bg-gray-50">
      <div class="p-4 border-b flex items-center justify-between bg-white shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 font-bold text-xl">
            {activeAgentName().charAt(0)}
          </div>
          <div>
            <h3 class="font-bold text-gray-800">{activeAgentName()}</h3>
            <p class="text-xs text-gray-500">Active Agent</p>
          </div>
        </div>
        
        <div class="flex items-center gap-2">
          <label class="text-sm font-medium text-gray-600">Switch Agent:</label>
          <select 
            class="border rounded-lg px-3 py-1.5 bg-gray-50 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            value={selectedAgent()}
            onChange={(e) => setSelectedAgent(e.currentTarget.value)}
          >
            <option value="">Select an Agent</option>
            <For each={agents()}>
              {agent => <option value={agent.id}>{agent.name}</option>}
            </For>
          </select>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto p-6 space-y-4">
        <For each={messages()}>
          {(msg) => (
            <div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div class={`max-w-[80%] px-4 py-2 rounded-2xl shadow-sm ${
                msg.role === 'user' ? 'bg-emerald-600 text-white' : 'bg-white text-gray-800 border'
              }`}>
                {msg.role === 'user' ? (
                   <div>{msg.content}</div>
                ) : (
                   <div innerHTML={marked.parse(msg.content) as string} class="prose prose-sm max-w-none" />
                )}
              </div>
            </div>
          )}
        </For>
      </div>

      <div class="p-6 bg-white border-t relative">
        <Show when={showAgentSelector()}>
          <div class="absolute bottom-full left-6 mb-2 w-64 bg-white border rounded-xl shadow-xl overflow-hidden z-10">
            <div class="bg-gray-50 px-4 py-2 border-b">
              <span class="text-xs font-bold text-gray-500 uppercase">Select Agent</span>
            </div>
            <div class="max-h-60 overflow-y-auto">
              <For each={filteredAgents()}>
                {(agent, index) => (
                  <button
                    onClick={() => selectAgent(agent)}
                    class={`w-full text-left px-4 py-3 flex items-center justify-between transition-colors ${
                      selectedIndex() === index() ? 'bg-emerald-50 text-emerald-700' : 'hover:bg-gray-50'
                    }`}
                  >
                    <span class="font-medium">{agent.name}</span>
                    <Show when={selectedIndex() === index()}>
                      <span class="text-xs bg-emerald-100 px-2 py-0.5 rounded text-emerald-600">Enter</span>
                    </Show>
                  </button>
                )}
              </For>
              <Show when={filteredAgents().length === 0}>
                <div class="px-4 py-3 text-sm text-gray-500 italic">No agents found</div>
              </Show>
            </div>
          </div>
        </Show>

        <form onSubmit={handleSubmit} class="max-w-4xl mx-auto flex gap-4">
          <input
            type="text"
            value={input()}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (use @ to switch agent)"
            class="flex-1 border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-sm"
          />
          <button 
            type="submit"
            disabled={isTyping()}
            class="bg-emerald-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-emerald-700 transition-colors disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
