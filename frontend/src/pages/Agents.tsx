import { createSignal, For, onMount, Show } from 'solid-js';

type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
};

type McpTool = {
  name: string;
  description: string;
  server: string;
};

export default function Agents() {
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [availableTools, setAvailableTools] = createSignal<McpTool[]>([]);
  
  // UI State
  const [isEditing, setIsEditing] = createSignal(false);
  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [providerOptions, setProviderOptions] = createSignal<string[]>([]);
  
  // Form state
  const [formName, setFormName] = createSignal("");
  const [formPrompt, setFormPrompt] = createSignal("");
  const [formProvider, setFormProvider] = createSignal("openai");
  const [formModel, setFormModel] = createSignal("gpt-4o");
  const [formTools, setFormTools] = createSignal<string[]>([]);

  const loadAgents = async () => {
    const res = await fetch('/api/agents/');
    setAgents(await res.json());
  };

  const loadTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      setAvailableTools(await res.json());
    } catch (e) {
      console.error("Failed to load tools", e);
    }
  };

  onMount(async () => {
    loadAgents();
    loadTools();
    try {
      const res = await fetch('/api/models/supported');
      const data = await res.json();
      setProviderOptions(data);
    } catch (e) {}
  });

  const openCreate = () => {
    setFormName("");
    setFormPrompt("");
    setFormProvider("openai");
    setFormModel("gpt-4o");
    setFormTools([]);
    setEditingId(null);
    setIsEditing(true);
  };

  const openEdit = (agent: Agent) => {
    setFormName(agent.name);
    setFormPrompt(agent.system_prompt);
    setFormProvider(agent.provider);
    setFormModel(agent.model);
    setFormTools(agent.enabled_tools);
    setEditingId(agent.id);
    setIsEditing(true);
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    
    const payload = {
      name: formName(),
      system_prompt: formPrompt(),
      provider: formProvider(),
      model: formModel(),
      enabled_tools: formTools()
    };

    if (editingId()) {
      await fetch(`/api/agents/${editingId()}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      await fetch('/api/agents/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    
    setIsEditing(false);
    loadAgents();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete agent?")) return;
    await fetch(`/api/agents/${id}`, { method: 'DELETE' });
    loadAgents();
  };

  const toggleTool = (toolName: string) => {
    const current = formTools();
    if (current.includes(toolName)) {
      setFormTools(current.filter(t => t !== toolName));
    } else {
      setFormTools([...current, toolName]);
    }
  };

  return (
    <div class="p-6 h-full overflow-y-auto bg-gray-50">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Agents</h2>
          <p class="text-gray-500 text-sm">Manage your AI assistants and their capabilities</p>
        </div>
        <button 
          onClick={openCreate}
          class="bg-emerald-600 text-white px-4 py-2 rounded-xl font-medium hover:bg-emerald-700 transition-colors shadow-sm flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Create Agent
        </button>
      </div>

      <Show when={isEditing()}>
        <div class="mb-8 bg-white border rounded-2xl shadow-lg overflow-hidden">
          <div class="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
            <h3 class="font-bold text-lg text-gray-800">{editingId() ? 'Edit Agent' : 'New Agent'}</h3>
            <button onClick={() => setIsEditing(false)} class="text-gray-400 hover:text-gray-600">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <form onSubmit={handleSubmit} class="p-6 space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Name</label>
                <input 
                  class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                  value={formName()}
                  onInput={e => setFormName(e.currentTarget.value)}
                  placeholder="e.g. Coding Assistant"
                  required
                />
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-2">Provider</label>
                  <select 
                    class="w-full border rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-emerald-500 outline-none"
                    value={formProvider()}
                    onChange={e => setFormProvider(e.currentTarget.value)}
                  >
                    <For each={providerOptions()}>
                      {(opt) => <option value={opt}>{opt}</option>}
                    </For>
                  </select>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-gray-700 mb-2">Model</label>
                  <input 
                    class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                    value={formModel()}
                    onInput={e => setFormModel(e.currentTarget.value)}
                    placeholder="e.g. gpt-4o"
                  />
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">System Prompt</label>
              <textarea 
                class="w-full border rounded-lg px-3 py-2 h-32 focus:ring-2 focus:ring-emerald-500 outline-none font-mono text-sm"
                value={formPrompt()}
                onInput={e => setFormPrompt(e.currentTarget.value)}
                placeholder="You are a helpful assistant..."
                required
              />
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-3">Enabled Tools (MCP)</label>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                <For each={availableTools()}>
                  {tool => (
                    <label class={`flex items-start p-3 border rounded-lg cursor-pointer transition-all ${
                      formTools().includes(tool.name) 
                      ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500' 
                      : 'hover:bg-gray-50'
                    }`}>
                      <input 
                        type="checkbox" 
                        class="mt-1 mr-3 text-emerald-600 focus:ring-emerald-500 rounded"
                        checked={formTools().includes(tool.name)}
                        onChange={() => toggleTool(tool.name)}
                      />
                      <div>
                        <div class="font-medium text-sm text-gray-900">{tool.name}</div>
                        <div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{tool.description}</div>
                        <div class="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">{tool.server}</div>
                      </div>
                    </label>
                  )}
                </For>
                <Show when={availableTools().length === 0}>
                  <div class="col-span-full text-center py-4 text-gray-500 text-sm bg-gray-50 rounded border border-dashed">
                    No MCP tools found. Configure MCP servers in Settings.
                  </div>
                </Show>
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4 border-t">
              <button 
                type="button" 
                onClick={() => setIsEditing(false)} 
                class="px-5 py-2.5 rounded-lg text-gray-600 hover:bg-gray-100 font-medium transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                class="bg-emerald-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-emerald-700 shadow-md transition-all transform active:scale-95"
              >
                {editingId() ? 'Update Agent' : 'Create Agent'}
              </button>
            </div>
          </form>
        </div>
      </Show>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <For each={agents()}>
          {agent => (
            <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
              <div class="flex justify-between items-start mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-lg shadow-inner">
                    {agent.name.charAt(0)}
                  </div>
                  <div>
                    <h3 class="font-bold text-gray-800">{agent.name}</h3>
                    <div class="flex items-center gap-1.5 text-xs text-gray-500">
                      <span class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600 font-medium">{agent.provider}</span>
                      <span>•</span>
                      <span>{agent.model}</span>
                    </div>
                  </div>
                </div>
                <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => openEdit(agent)}
                    class="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    onClick={() => handleDelete(agent.id)}
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
                  {agent.system_prompt}
                </p>
              </div>
              
              <div class="flex items-center gap-2 overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 shrink-0">TOOLS</span>
                <div class="flex flex-wrap gap-1">
                  <For each={agent.enabled_tools.slice(0, 3)}>
                    {tool => (
                      <span class="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-100">
                        {tool}
                      </span>
                    )}
                  </For>
                  <Show when={agent.enabled_tools.length > 3}>
                    <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                      +{agent.enabled_tools.length - 3}
                    </span>
                  </Show>
                  <Show when={agent.enabled_tools.length === 0}>
                    <span class="text-[10px] text-gray-400 italic">No tools enabled</span>
                  </Show>
                </div>
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
