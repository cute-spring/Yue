import { createSignal, For, onMount } from 'solid-js';
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

  return (
    <div class="flex flex-col h-full">
      <div class="p-4 border-b flex items-center gap-4 bg-white">
        <label class="font-bold text-gray-700">Agent:</label>
        <select 
          class="border rounded px-2 py-1"
          value={selectedAgent()}
          onChange={(e) => setSelectedAgent(e.currentTarget.value)}
        >
          <option value="">Select an Agent</option>
          <For each={agents()}>
            {agent => <option value={agent.id}>{agent.name}</option>}
          </For>
        </select>
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

      <div class="p-6 bg-white border-t">
        <form onSubmit={handleSubmit} class="max-w-4xl mx-auto flex gap-4">
          <input
            type="text"
            value={input()}
            onInput={(e) => setInput(e.currentTarget.value)}
            placeholder="Type your message..."
            class="flex-1 border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-500"
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
