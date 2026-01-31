import { createSignal, For, onMount } from 'solid-js';

type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
};

export default function Agents() {
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [isCreating, setIsCreating] = createSignal(false);
  const [providerOptions, setProviderOptions] = createSignal<string[]>([]);
  
  // Form state
  const [newName, setNewName] = createSignal("");
  const [newPrompt, setNewPrompt] = createSignal("");
  const [newProvider, setNewProvider] = createSignal("openai");
  const [newModel, setNewModel] = createSignal("gpt-4o");
  const [newTools, setNewTools] = createSignal(""); // Comma separated for now

  const loadAgents = async () => {
    const res = await fetch('/api/agents/');
    setAgents(await res.json());
  };

  onMount(async () => {
    loadAgents();
    try {
      const res = await fetch('/api/models/supported');
      const data = await res.json();
      setProviderOptions(data);
    } catch (e) {}
  });

  const handleCreate = async (e: Event) => {
    e.preventDefault();
    const tools = newTools().split(',').map(t => t.trim()).filter(Boolean);
    
    await fetch('/api/agents/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: newName(),
        system_prompt: newPrompt(),
        provider: newProvider(),
        model: newModel(),
        enabled_tools: tools
      })
    });
    
    setIsCreating(false);
    setNewName("");
    setNewPrompt("");
    setNewProvider("openai");
    setNewModel("gpt-4o");
    setNewTools("");
    loadAgents();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete agent?")) return;
    await fetch(`/api/agents/${id}`, { method: 'DELETE' });
    loadAgents();
  };

  return (
    <div class="p-6 h-full overflow-y-auto">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold">Agents</h2>
        <button 
          onClick={() => setIsCreating(true)}
          class="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700"
        >
          Create Agent
        </button>
      </div>

      {isCreating() && (
        <div class="mb-8 p-4 bg-white border rounded shadow">
          <h3 class="font-bold mb-4">New Agent</h3>
          <form onSubmit={handleCreate} class="space-y-4">
            <div>
              <label class="block text-sm font-medium mb-1">Name</label>
              <input 
                class="w-full border rounded p-2"
                value={newName()}
                onInput={e => setNewName(e.currentTarget.value)}
                required
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">System Prompt</label>
              <textarea 
                class="w-full border rounded p-2 h-24"
                value={newPrompt()}
                onInput={e => setNewPrompt(e.currentTarget.value)}
                required
              />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">Provider</label>
                <select 
                  class="w-full border rounded p-2"
                  value={newProvider()}
                  onChange={e => setNewProvider(e.currentTarget.value)}
                >
                  <For each={providerOptions()}>
                    {(opt) => <option value={opt}>{opt}</option>}
                  </For>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Model Name</label>
                <input 
                  class="w-full border rounded p-2"
                  value={newModel()}
                  onInput={e => setNewModel(e.currentTarget.value)}
                  placeholder="e.g. gpt-4o, llama3"
                />
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Tools (comma separated)</label>
              <input 
                class="w-full border rounded p-2"
                value={newTools()}
                onInput={e => setNewTools(e.currentTarget.value)}
                placeholder="filesystem:read_file, filesystem:list_directory"
              />
            </div>
            <div class="flex gap-2">
              <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
              <button type="button" onClick={() => setIsCreating(false)} class="bg-gray-300 px-4 py-2 rounded">Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div class="grid gap-4">
        <For each={agents()}>
          {agent => (
            <div class="bg-white p-4 rounded border shadow-sm">
              <div class="flex justify-between items-start">
                <div>
                  <h3 class="font-bold text-lg">{agent.name}</h3>
                  <p class="text-gray-500 text-sm mb-2">ID: {agent.id}</p>
                </div>
                <button onClick={() => handleDelete(agent.id)} class="text-red-600 hover:text-red-800">Delete</button>
              </div>
              <div class="bg-gray-50 p-2 rounded text-sm font-mono mb-2 whitespace-pre-wrap">
                {agent.system_prompt}
              </div>
              <div class="text-sm mb-2">
                <span class="font-semibold">Model:</span> {agent.provider}:{agent.model}
              </div>
              <div class="text-sm">
                <span class="font-semibold">Tools:</span> {agent.enabled_tools.join(", ") || "None"}
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
