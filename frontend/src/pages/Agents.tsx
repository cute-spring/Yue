import { createSignal, For, onMount, Show } from 'solid-js';
import ModelSwitcher, { type ProviderInfo } from '../components/ModelSwitcher';

type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
  doc_root?: string;
};

type McpTool = {
  id: string;
  name: string;
  description: string;
  server: string;
};

export default function Agents() {
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [availableTools, setAvailableTools] = createSignal<McpTool[]>([]);
  const [mcpStatus, setMcpStatus] = createSignal<{name:string;enabled:boolean;connected:boolean;transport:string;last_error?:string}[]>([]);
  
  // UI State
  const [isEditing, setIsEditing] = createSignal(false);
  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [providers, setProviders] = createSignal<ProviderInfo[]>([]);
  const [submitError, setSubmitError] = createSignal<string | null>(null);
  
  // Form state
  const [formName, setFormName] = createSignal("");
  const [formPrompt, setFormPrompt] = createSignal("");
  const [formProvider, setFormProvider] = createSignal("openai");
  const [formModel, setFormModel] = createSignal("gpt-4o");
  const [formTools, setFormTools] = createSignal<string[]>([]);
  const [formDocRoot, setFormDocRoot] = createSignal("");

  const modelsOf = (p: ProviderInfo): string[] => {
    const list = (p.available_models && p.available_models.length > 0) ? p.available_models : p.models;
    return Array.from(new Set((list || []).filter(Boolean)));
  };

  const pickDefaultModel = (catalog: ProviderInfo[]) => {
    for (const p of catalog) {
      const ms = modelsOf(p);
      if (ms.length > 0) {
        setFormProvider(p.name);
        setFormModel(ms[0]);
        return;
      }
    }
  };

  const ensureSelectionValid = (catalog: ProviderInfo[]) => {
    const provider = formProvider();
    const model = formModel();

    if (!provider || !model) {
      pickDefaultModel(catalog);
      return;
    }

    const byProvider = catalog.find(p => p.name === provider);
    if (byProvider) {
      const ms = modelsOf(byProvider);
      if (ms.includes(model)) return;
      if (ms.length > 0) {
        setFormModel(ms[0]);
        return;
      }
    }

    const byModel = catalog.find(p => modelsOf(p).includes(model));
    if (byModel) {
      setFormProvider(byModel.name);
      return;
    }

    pickDefaultModel(catalog);
  };

  const loadAgents = async () => {
    try {
      const res = await fetch('/api/agents/');
      if (!res.ok) throw new Error(await res.text());
      setAgents(await res.json());
    } catch (e) {
      console.error("Failed to load agents", e);
    }
  };

  const loadTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      setAvailableTools(await res.json());
    } catch (e) {
      console.error("Failed to load tools", e);
    }
  };

  const loadMcpStatus = async () => {
    try {
      const res = await fetch('/api/mcp/status');
      if (!res.ok) return;
      setMcpStatus(await res.json());
    } catch (e) {}
  };

  const statusByServer = () => {
    const map: Record<string, {enabled:boolean;connected:boolean;transport?:string;last_error?:string}> = {};
    for (const s of mcpStatus()) {
      map[s.name] = s;
    }
    return map;
  };

  const toolsByServer = () => {
    const groups: Record<string, McpTool[]> = {};
    for (const t of availableTools()) {
      groups[t.server] = groups[t.server] || [];
      groups[t.server].push(t);
    }
    const entries = Object.entries(groups);
    entries.sort(([a], [b]) => a.localeCompare(b));
    for (const [, list] of entries) {
      list.sort((x, y) => x.name.localeCompare(y.name));
    }
    return entries;
  };

  const loadProviderCatalog = async (refresh = false) => {
    try {
      const res = await fetch(`/api/models/providers${refresh ? '?refresh=1' : ''}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setProviders(data);
      ensureSelectionValid(data || []);
    } catch (e) {}
  };

  onMount(async () => {
    loadAgents();
    loadTools();
    loadMcpStatus();
    loadProviderCatalog();
  });

  const openCreate = () => {
    setFormName("");
    setFormPrompt("");
    setFormProvider(formProvider() || "openai");
    setFormModel(formModel() || "gpt-4o");
    setFormTools([]);
    setFormDocRoot("");
    setSubmitError(null);
    setEditingId(null);
    setIsEditing(true);
    ensureSelectionValid(providers());
  };

  const openEdit = (agent: Agent) => {
    setFormName(agent.name);
    setFormPrompt(agent.system_prompt);
    setFormProvider(agent.provider);
    setFormModel(agent.model);
    setFormTools(agent.enabled_tools);
    setFormDocRoot(agent.doc_root || "");
    setSubmitError(null);
    setEditingId(agent.id);
    setIsEditing(true);
    ensureSelectionValid(providers());
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    setSubmitError(null);
    
    const payload = {
      name: formName(),
      system_prompt: formPrompt(),
      provider: formProvider(),
      model: formModel(),
      enabled_tools: formTools(),
      doc_root: formDocRoot() || undefined
    };

    try {
      const res = editingId()
        ? await fetch(`/api/agents/${editingId()}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
        : await fetch('/api/agents/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
      if (!res.ok) {
        setSubmitError(await res.text());
        return;
      }
    } catch (e: any) {
      setSubmitError(String(e?.message || e));
      return;
    }
    
    setIsEditing(false);
    await loadAgents();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete agent?")) return;
    await fetch(`/api/agents/${id}`, { method: 'DELETE' });
    loadAgents();
  };

  const toggleTool = (toolId: string) => {
    const current = formTools();
    // Also handle legacy name entries by removing both id and name if present
    const legacyName = toolId.includes(":") ? toolId.split(":").slice(1).join(":") : toolId;
    const hasId = current.includes(toolId);
    const hasLegacy = current.includes(legacyName);
    if (hasId || hasLegacy) {
      setFormTools(current.filter(t => t !== toolId && t !== legacyName));
    } else {
      setFormTools([...current, toolId]);
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
            <Show when={submitError()}>
              <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 whitespace-pre-wrap">
                {submitError()}
              </div>
            </Show>
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
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Model</label>
                <Show
                  when={providers().length > 0}
                  fallback={
                    <div class="grid grid-cols-2 gap-4">
                      <input
                        class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                        value={formProvider()}
                        onInput={e => setFormProvider(e.currentTarget.value)}
                        placeholder="provider (e.g. openai)"
                      />
                      <input
                        class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
                        value={formModel()}
                        onInput={e => setFormModel(e.currentTarget.value)}
                        placeholder="model (e.g. gpt-4o)"
                      />
                    </div>
                  }
                >
                  <ModelSwitcher
                    providers={providers()}
                    selectedModel={formModel()}
                    theme="light"
                    placement="bottom"
                    onRefresh={() => loadProviderCatalog(true)}
                    onSelect={(provider, model) => {
                      setFormProvider(provider);
                      setFormModel(model);
                    }}
                  />
                </Show>
                <div class="text-xs text-gray-500 mt-1">
                  Provider: <span class="font-mono">{formProvider() || "-"}</span>
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
              <label class="block text-sm font-semibold text-gray-700 mb-2">Doc Root (optional)</label>
              <input
                class="w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none font-mono text-sm"
                value={formDocRoot()}
                onInput={e => setFormDocRoot(e.currentTarget.value)}
                placeholder='e.g. docs or /Users/you/path/to/docs'
              />
              <div class="text-xs text-gray-500 mt-1">
                Used by docs_search_markdown/docs_read_markdown when root isn’t provided.
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-3">Enabled Tools (MCP)</label>
              <Show
                when={availableTools().length > 0}
                fallback={
                  <div class="text-center py-4 text-gray-500 text-sm bg-gray-50 rounded border border-dashed">
                    No MCP tools found. Configure MCP servers in Settings.
                  </div>
                }
              >
                <div class="space-y-4">
                  <For each={toolsByServer()}>
                    {([server, tools]) => (
                      <div class="border rounded-xl bg-white">
                        <div class="px-4 py-2 border-b bg-gray-50 flex items-center justify-between">
                          <div class="flex items-center gap-2">
                            <div class="font-semibold text-gray-800">{server}</div>
                            <div class="text-xs text-gray-500">({tools.length})</div>
                          </div>
                          <div class="flex items-center gap-2 text-xs">
                            <Show when={statusByServer()[server]}>
                              <span class={`px-2 py-0.5 rounded-full border ${statusByServer()[server].enabled ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-gray-100 border-gray-200 text-gray-600'}`}>
                                {statusByServer()[server].enabled ? 'Enabled' : 'Disabled'}
                              </span>
                              <span class={`px-2 py-0.5 rounded-full border ${statusByServer()[server].connected ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                                {statusByServer()[server].connected ? 'Online' : 'Offline'}
                              </span>
                            </Show>
                          </div>
                        </div>
                        <div class="p-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          <For each={tools}>
                            {tool => (
                              <label class={`flex items-start p-3 border rounded-lg cursor-pointer transition-all ${
                                (formTools().includes(tool.id) || formTools().includes(tool.name))
                                ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500'
                                : 'hover:bg-gray-50'
                              }`}>
                                <input
                                  type="checkbox"
                                  class="mt-1 mr-3 text-emerald-600 focus:ring-emerald-500 rounded"
                                  checked={formTools().includes(tool.id) || formTools().includes(tool.name)}
                                  onChange={() => toggleTool(tool.id)}
                                />
                                <div>
                                  <div class="font-medium text-sm text-gray-900">{tool.name}</div>
                                  <div class="text-xs text-gray-500 mt-0.5 line-clamp-2">{tool.description}</div>
                                  <div class="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">{tool.id}</div>
                                </div>
                              </label>
                            )}
                          </For>
                        </div>
                      </div>
                    )}
                  </For>
                </div>
              </Show>
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
