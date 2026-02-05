import { createSignal, onMount, For, Show } from 'solid-js';

type Tab = 'general' | 'mcp' | 'llm';

type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
};

type LLMProvider = {
    name: string;
    configured: boolean;
    requirements: string[];
    current_model?: string;
    available_models?: string[];
    models?: string[];
  };

  export default function Settings() {
    const [activeTab, setActiveTab] = createSignal<Tab>('general');
    const TAB_LABEL: Record<Tab, string> = {
      general: 'General',
      mcp: 'MCP',
      llm: 'Models'
    };
    
    // MCP State
    const [mcpConfig, setMcpConfig] = createSignal("");
    const [mcpStatus, setMcpStatus] = createSignal<{name:string;enabled:boolean;connected:boolean;transport:string;last_error?:string}[]>([]);
    const [mcpTools, setMcpTools] = createSignal<{id:string;name:string;description:string;server:string}[]>([]);
    const [expanded, setExpanded] = createSignal<Record<string, boolean>>({});
    const [showManual, setShowManual] = createSignal(false);
    const [manualText, setManualText] = createSignal(`{\n  \"mcpServers\": {\n    \"example-server\": {\n      \"command\": \"npx\",\n      \"args\": [\"-y\", \"mcp-server-example\"]\n    }\n  }\n}`);
    const [showRaw, setShowRaw] = createSignal(false);
    const [showAddMenu, setShowAddMenu] = createSignal(false);
    const [showMarketplace, setShowMarketplace] = createSignal(false);
    const [hoveredServer, setHoveredServer] = createSignal<string | null>(null);
    
    // LLM State
  const [providers, setProviders] = createSignal<LLMProvider[]>([]);
  const [llmForm, setLlmForm] = createSignal<Record<string, any>>({});
  const [customModels, setCustomModels] = createSignal<{name:string;base_url?:string;api_key?:string;model?:string}[]>([]);
    const [showAddCustom, setShowAddCustom] = createSignal(false);
    const [newCM, setNewCM] = createSignal<{name:string;provider:string;model:string;base_url?:string;api_key?:string}>({name:"",provider:"openai",model:""});
    const [newCMStatus, setNewCMStatus] = createSignal<string>("");
  const [showEditProvider, setShowEditProvider] = createSignal(false);
  const [editingProvider, setEditingProvider] = createSignal<string>("");
  const [toast, setToast] = createSignal<{type:'success'|'error';message:string;actionLabel?:string;action?:()=>void}|null>(null);
  const showToast = (type:'success'|'error', message:string, actionLabel?:string, action?:()=>void) => {
    setToast({ type, message, actionLabel, action });
    setTimeout(() => setToast(null), 3000);
  };
    
    // Model Management State
    const [showModelManager, setShowModelManager] = createSignal(false);
    const [managingProvider, setManagingProvider] = createSignal<string | null>(null);
    const [managedModels, setManagedModels] = createSignal<string[]>([]);
    const [enabledModels, setEnabledModels] = createSignal<Set<string>>(new Set());
    const [isSavingModels, setIsSavingModels] = createSignal(false);
    
    // Agents State
    const [agents, setAgents] = createSignal<Agent[]>([]);
  
  // General Preferences State
  const [prefs, setPrefs] = createSignal({
    theme: 'light',
    language: 'en',
    default_agent: 'default'
  });

  const fetchData = async () => {
    try {
      // Fetch MCP
      const mcpRes = await fetch('/api/mcp/');
      setMcpConfig(JSON.stringify(await mcpRes.json(), null, 2));
      const mcpStatusRes = await fetch('/api/mcp/status');
      setMcpStatus(await mcpStatusRes.json());
      const toolsRes = await fetch('/api/mcp/tools');
      setMcpTools(await toolsRes.json());
      
      // Fetch LLM Providers
      const providersRes = await fetch('/api/models/providers');
      setProviders(await providersRes.json());
      
      // Fetch LLM Config (API Keys etc)
      const llmConfigRes = await fetch('/api/config/llm');
      setLlmForm(await llmConfigRes.json());
      const cmRes = await fetch('/api/models/custom');
      setCustomModels(await cmRes.json());
      
      // Fetch Agents
      const agentsRes = await fetch('/api/agents/');
      setAgents(await agentsRes.json());
      
      // Fetch Preferences
      const prefsRes = await fetch('/api/config/preferences');
      setPrefs(await prefsRes.json());
    } catch (e) {
      console.error("Failed to load settings", e);
    }
  };

  onMount(fetchData);
  onMount(() => {
    const handleGlobalClick = () => setShowAddMenu(false);
    window.addEventListener('click', handleGlobalClick);
    return () => window.removeEventListener('click', handleGlobalClick);
  });

  const saveMcp = async () => {
    try {
      const parsed = JSON.parse(mcpConfig());
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      alert("MCP Configuration saved!");
      await fetch('/api/mcp/reload', { method: 'POST' });
      const mcpStatusRes = await fetch('/api/mcp/status');
      setMcpStatus(await mcpStatusRes.json());
    } catch (e) {
      alert("Invalid JSON: " + e);
    }
  };

  const saveLlmConfig = async () => {
    await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(llmForm())
    });
    showToast('success', 'LLM settings saved');
    fetchData();
  };

  const savePrefs = async () => {
    await fetch('/api/config/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs())
    });
    showToast('success', 'Preferences saved');
  };


  const openModelManager = (provider: LLMProvider) => {
    setManagingProvider(provider.name);
    setManagedModels(provider.models || []);
    setEnabledModels(new Set(provider.available_models || []));
    setShowModelManager(true);
  };
  const openProviderEditor = (name: string) => {
    setEditingProvider(name);
    setShowEditProvider(true);
  };
  const saveProviderEditor = async () => {
    await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(llmForm())
    });
    setShowEditProvider(false);
    fetchData();
  };

  const saveManagedModels = async () => {
    const providerName = managingProvider();
    if (!providerName) return;
    setIsSavingModels(true);
    
    try {
      const previous = new Set(enabledModels());
      const key = `${providerName}_enabled_models`;
      const currentConfig = llmForm();
      const newConfig = { ...currentConfig, [key]: Array.from(enabledModels()) };
      setLlmForm(newConfig);
      
      await fetch('/api/config/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      setShowModelManager(false);
      showToast('success', `Models for ${providerName} updated`, 'Undo', async () => {
        const revertConfig = { ...currentConfig, [key]: Array.from(previous) };
        setLlmForm(revertConfig);
        await fetch('/api/config/llm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(revertConfig)
        });
        showToast('success', `Reverted ${providerName} models`);
        fetchData();
      });
      fetchData();
    } finally {
      setIsSavingModels(false);
    }
  };

  const testProvider = async (name: string) => {
    const res = await fetch(`/api/models/test/${name}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: llmForm()[`${name}_model`] || undefined })
    });
    const data = await res.json();
    if (data.ok) {
      alert(`${name} connection OK`);
    } else {
      alert(`${name} failed: ${data.error || 'Unknown error'}`);
    }
  };

  const toggleMcpEnabled = async (serverName: string, enabled: boolean) => {
    try {
      const parsed = JSON.parse(mcpConfig());
      const updated = parsed.map((cfg: any) => cfg.name === serverName ? { ...cfg, enabled } : cfg);
      setMcpConfig(JSON.stringify(updated, null, 2));
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      });
      await fetch('/api/mcp/reload', { method: 'POST' });
      const mcpStatusRes = await fetch('/api/mcp/status');
      setMcpStatus(await mcpStatusRes.json());
    } catch (e) {
      alert("Failed to toggle server: " + e);
    }
  };
  const reloadMcp = async () => {
    await fetch('/api/mcp/reload', { method: 'POST' });
    const mcpStatusRes = await fetch('/api/mcp/status');
    setMcpStatus(await mcpStatusRes.json());
    const toolsRes = await fetch('/api/mcp/tools');
    setMcpTools(await toolsRes.json());
  };
  const confirmManual = async () => {
    try {
      const text = manualText().trim();
      if (!text) return;
      
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch (e) {
        showToast('error', 'Invalid JSON format');
        return;
      }

      let arr: any[] = [];
      
      // Handle Claude desktop format: { "mcpServers": { "name": { "command": "...", "args": [] } } }
      if (parsed.mcpServers && typeof parsed.mcpServers === 'object') {
        arr = Object.entries(parsed.mcpServers).map(([name, config]: [string, any]) => ({
          name,
          command: config.command,
          args: config.args || [],
          env: config.env || {},
          enabled: true
        }));
      } 
      // Handle array format: [{ "name": "...", "command": "...", "args": [] }]
      else if (Array.isArray(parsed)) {
        arr = parsed.map(item => ({
          name: item.name,
          command: item.command,
          args: item.args || [],
          env: item.env || {},
          enabled: item.enabled !== undefined ? item.enabled : true
        }));
      }
      // Handle single object format (not recommended but supported)
      else if (parsed.name && parsed.command) {
        arr = [{
          name: parsed.name,
          command: parsed.command,
          args: parsed.args || [],
          env: parsed.env || {},
          enabled: true
        }];
      }

      if (arr.length === 0) {
        showToast('error', 'No valid MCP server configuration found in JSON');
        return;
      }

      const res = await fetch('/api/mcp/', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(arr) 
      });

      if (res.ok) {
        showToast('success', `Successfully added ${arr.length} MCP server(s)`);
        await reloadMcp();
        setShowManual(false);
        setManualText('');
      } else {
        const err = await res.json();
        showToast('error', `Failed to save: ${JSON.stringify(err.detail || err)}`);
      }
    } catch (e) {
      console.error('Manual add error:', e);
      showToast('error', `An error occurred: ${e}`);
    }
  };


  const deleteCustomModel = async (name: string) => {
    if (!confirm(`Delete custom model ${name}?`)) return;
    await fetch(`/api/models/custom/${name}`, { method: 'DELETE' });
    const cmRes = await fetch('/api/models/custom');
    setCustomModels(await cmRes.json());
  };

  const deleteMcpServer = async (serverName: string) => {
    if (!confirm(`Are you sure you want to delete MCP server "${serverName}"? This action cannot be undone.`)) return;
    try {
      const res = await fetch(`/api/mcp/${serverName}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('success', `MCP server "${serverName}" deleted`);
        await fetchData(); // Refresh all data
      } else {
        const error = await res.json();
        showToast('error', `Failed to delete: ${error.detail || 'Unknown error'}`);
      }
    } catch (e) {
      showToast('error', `Error deleting server: ${e}`);
    }
  };

  const testCustomModel = async (m: {name:string;base_url?:string;api_key?:string;model?:string}) => {
    const res = await fetch('/api/models/test/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_url: m.base_url, api_key: m.api_key, model: m.model })
    });
    const data = await res.json();
    alert(data.ok ? `Custom ${m.name} OK` : `Custom ${m.name} failed: ${data.error || 'Unknown error'}`);
  };

  return (
    <div class="p-8 h-full flex flex-col bg-gray-50 overflow-hidden">
      <div class="flex justify-between items-center mb-8">
        <h2 class="text-3xl font-bold text-gray-800">System Configuration</h2>
        <div class="text-sm text-gray-500 bg-white px-3 py-1 rounded-full border shadow-sm">
          Unified Platform Settings
        </div>
      </div>

      {/* Tabs */}
      <div class="flex space-x-1 mb-6 bg-gray-200 p-1 rounded-lg w-fit">
        <For each={['general', 'mcp', 'llm']}>
          {(tab) => (
            <button
              onClick={() => setActiveTab(tab as Tab)}
              class={`px-6 py-2 rounded-md text-sm font-medium transition-all ${
                activeTab() === tab 
                ? 'bg-white text-emerald-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
              }`}
            >
              {TAB_LABEL[tab as Tab]}
            </button>
          )}
        </For>
      </div>

      <div class="flex-1 bg-white rounded-xl border shadow-sm overflow-y-auto p-6">
        {/* General Tab */}
        <Show when={activeTab() === 'general'}>
          <div class="max-w-2xl space-y-6">
            <h3 class="text-xl font-semibold border-b pb-2">User Preferences</h3>
            <div class="grid gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Theme</label>
                <select 
                  class="w-full border rounded-lg p-2 bg-gray-50"
                  value={prefs().theme}
                  onChange={e => setPrefs({...prefs(), theme: e.currentTarget.value})}
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">Language</label>
                <select 
                  class="w-full border rounded-lg p-2 bg-gray-50"
                  value={prefs().language}
                  onChange={e => setPrefs({...prefs(), language: e.currentTarget.value})}
                >
                  <option value="en">English</option>
                  <option value="zh">Chinese</option>
                </select>
              </div>
              <div>
                <div class="flex items-center justify-between gap-3 mb-1">
                  <label class="block text-sm font-medium text-gray-700">Default Agent</label>
                  <a href="/agents" class="text-emerald-600 hover:underline text-sm font-medium">
                    Manage agents →
                  </a>
                </div>
                <select 
                  class="w-full border rounded-lg p-2 bg-gray-50"
                  value={prefs().default_agent}
                  onChange={e => setPrefs({...prefs(), default_agent: e.currentTarget.value})}
                >
                  <For each={agents()}>
                    {a => <option value={a.id}>{a.name}</option>}
                  </For>
                </select>
              </div>
            </div>
            <button 
              onClick={savePrefs}
              class="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-md"
            >
              Save Preferences
            </button>
          </div>
        </Show>

        {/* MCP Tab */}
        <Show when={activeTab() === 'mcp'}>
          <div class="h-full flex flex-col space-y-4">
            <div class="flex justify-between items-center">
              <div class="flex items-center gap-2">
                <h3 class="text-xl font-semibold">MCP</h3>
              </div>
              <div class="flex items-center gap-2">
                <button onClick={reloadMcp} class="p-2 rounded-md border bg-white hover:bg-gray-50">↻</button>
                <div class="relative">
                  <button onClick={(e) => { e.stopPropagation(); setShowAddMenu(v => !v); }} class="px-3 py-1.5 rounded-md bg-blue-700 text-white flex items-center gap-2">
                    <span>+ Add</span>
                    <span>▾</span>
                  </button>
                  <Show when={showAddMenu()}>
                    <div class="absolute right-0 mt-2 w-56 bg-white border rounded-lg shadow-xl z-50">
                      <button onClick={(e) => { e.stopPropagation(); setShowAddMenu(false); setShowMarketplace(true); }} class="block w-full text-left px-3 py-2 hover:bg-gray-50">
                        Add from Marketplace
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); setShowAddMenu(false); setShowManual(true); }} class="block w-full text-left px-3 py-2 hover:bg-gray-50">
                        Add Manually
                      </button>
                    </div>
                  </Show>
                </div>
              </div>
            </div>
            <div class="border rounded-xl bg-white">
              <For each={mcpStatus()}>
                {(s) => (
                  <div class="border-b last:border-b-0">
                    <div class="px-4 py-3 flex items-center justify-between relative">
                      <div class="flex items-center gap-3">
                        <button onClick={() => setExpanded(prev => ({ ...prev, [s.name]: !prev[s.name] }))} class="text-gray-500">▸</button>
                        <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center font-bold text-emerald-700">
                          {s.name.charAt(0).toUpperCase()}
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="font-semibold underline cursor-pointer" onMouseEnter={() => setHoveredServer(s.name)} onMouseLeave={() => setHoveredServer(null)}>{s.name}</span>
                          <Show when={s.connected}><span class="text-emerald-600">✓</span></Show>
                          <Show when={!s.connected}>
                            <span class="text-red-600">Failed to start</span>
                            <button onClick={reloadMcp} class="text-blue-600 underline">Retry</button>
                          </Show>
                        </div>
                        <Show when={hoveredServer() === s.name}>
                          <div class="absolute left-20 top-full mt-2 bg-white border rounded-xl shadow-xl w-[420px] z-50">
                            <div class="px-4 py-3 border-b">
                              <div class="font-semibold">{s.name} • From TRAE</div>
                              <div class="text-xs text-gray-500">Update on {new Date().toISOString().slice(0,10)}</div>
                              <div class="text-xs text-gray-600 mt-1">
                                MCP Server — Tools for this integration
                              </div>
                            </div>
                            <div class="py-2">
                              <For each={mcpTools().filter(t => t.server === s.name).slice(0, 2)}>
                                {(t) => (
                                  <div class="px-4 py-2">
                                    <div class="text-sm font-medium">{t.name}</div>
                                    <div class="text-xs text-gray-500">
                                      {t.description?.length ? t.description : 'Tool provided by this server.'}
                                    </div>
                                  </div>
                                )}
                              </For>
                              <Show when={mcpTools().filter(t => t.server === s.name).length === 0}>
                                <div class="px-4 py-3 text-xs text-gray-500">No tools</div>
                              </Show>
                            </div>
                          </div>
                        </Show>
                      </div>
                      <div class="flex items-center gap-3">
                        <input type="checkbox" checked={s.enabled} onChange={e => toggleMcpEnabled(s.name, e.currentTarget.checked)} class="w-4 h-4 text-emerald-600 rounded border-gray-300 focus:ring-emerald-500" />
                        <button 
                          onClick={() => deleteMcpServer(s.name)}
                          class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Delete MCP Server"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <Show when={expanded()[s.name]}>
                      <div class="px-12 pb-4">
                        <div class="text-xs text-gray-500 mb-2">Tools</div>
                        <div class="grid md:grid-cols-2 gap-2">
                          <For each={mcpTools().filter(t => t.server === s.name)}>
                            {(t) => (
                              <div class="p-2 border rounded-lg">
                                <div class="text-sm font-medium">{t.name}</div>
                                <div class="text-xs text-gray-500">{t.description}</div>
                              </div>
                            )}
                          </For>
                          <Show when={mcpTools().filter(t => t.server === s.name).length === 0}>
                            <div class="text-xs text-gray-500">No tools</div>
                          </Show>
                        </div>
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>
            <Show when={showManual()}>
              <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
                <div class="w-[640px] bg-white rounded-xl border shadow-lg">
                  <div class="px-4 py-2 border-b flex justify-between items-center">
                    <div class="font-semibold">Configure Manually</div>
                    <button onClick={() => setShowManual(false)}>✕</button>
                  </div>
                  <div class="p-4">
                    <textarea class="w-full h-64 font-mono border rounded-lg p-3 bg-gray-50" value={manualText()} onInput={e => setManualText(e.currentTarget.value)} />
                    <div class="text-xs text-gray-500 mt-2">Please confirm the source and identify risks before configuration.</div>
                  </div>
                  <div class="px-4 py-3 flex justify-end gap-2 border-t">
                    <button onClick={() => setShowManual(false)} class="px-3 py-1.5 rounded-md border">Cancel</button>
                    <button onClick={confirmManual} class="px-3 py-1.5 rounded-md bg-emerald-600 text-white">Confirm</button>
                  </div>
                </div>
              </div>
            </Show>
            <Show when={showMarketplace()}>
              <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
                <div class="w-[680px] bg-white rounded-xl border shadow-lg">
                  <div class="px-4 py-2 border-b flex justify-between items-center">
                    <div class="font-semibold">Add from Marketplace</div>
                    <button onClick={() => setShowMarketplace(false)}>✕</button>
                  </div>
                  <div class="p-6">
                    <p class="text-sm text-gray-600">Marketplace integration is coming soon. This is a mock dialog.</p>
                    <div class="mt-4 grid grid-cols-2 gap-3">
                      <div class="p-3 border rounded-lg">
                        <div class="font-semibold">Playwright MCP</div>
                        <div class="text-xs text-gray-500">Browser automation tools</div>
                      </div>
                      <div class="p-3 border rounded-lg">
                        <div class="font-semibold">Filesystem MCP</div>
                        <div class="text-xs text-gray-500">File operations</div>
                      </div>
                    </div>
                  </div>
                  <div class="px-4 py-3 flex justify-end gap-2 border-t">
                    <button onClick={() => setShowMarketplace(false)} class="px-3 py-1.5 rounded-md border">Close</button>
                  </div>
                </div>
              </div>
            </Show>
            <Show when={showRaw()}>
              <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
                <div class="w-[800px] bg-white rounded-xl border shadow-lg">
                  <div class="px-4 py-2 border-b flex justify-between items-center">
                    <div class="font-semibold">Raw Config (JSON)</div>
                    <button onClick={() => setShowRaw(false)}>✕</button>
                  </div>
                  <div class="p-4">
                    <textarea class="w-full h-80 font-mono border rounded-lg p-3 bg-gray-50" value={mcpConfig()} onInput={e => setMcpConfig(e.currentTarget.value)} />
                  </div>
                  <div class="px-4 py-3 flex justify-end gap-2 border-t">
                    <button onClick={() => setShowRaw(false)} class="px-3 py-1.5 rounded-md border">Cancel</button>
                    <button onClick={async () => { await saveMcp(); setShowRaw(false); }} class="px-3 py-1.5 rounded-md bg-emerald-600 text-white">Confirm</button>
                  </div>
                </div>
              </div>
            </Show>
          </div>
        </Show>

        {/* LLM Tab */}
        <Show when={activeTab() === 'llm'}>
          <div class="space-y-8 max-w-4xl">
            <div class="border-b pb-2">
              <h3 class="text-xl font-semibold">LLM Provider Configurations</h3>
              <p class="text-sm text-gray-500">Configure API keys and default models</p>
              <div class="mt-2">
                <button 
                  onClick={async () => {
                    const providersRes = await fetch('/api/models/providers?refresh=1');
                    setProviders(await providersRes.json());
                  }}
                  class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                >
                  Refresh Available Models
                </button>
                <button 
                  onClick={() => { 
                    setNewCM({ name: "", provider: "openai", model: "", base_url: "", api_key: "" });
                    setNewCMStatus("");
                    setShowAddCustom(true);
                  }}
                  class="ml-2 text-xs px-3 py-1.5 rounded-lg bg-blue-700 text-white hover:bg-blue-800 shadow-sm inline-flex items-center gap-1"
                >
                  <span>+</span><span>Add Custom (Overlay)</span>
                </button>
              </div>
            </div>
            
            <div class="overflow-x-auto border rounded-xl bg-white">
              <table class="min-w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Provider</th>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Model</th>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Status</th>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Available Models</th>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Requirements</th>
                    <th class="text-left px-4 py-2 font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <For each={providers()}>
                    {(p) => (
                      <tr class="border-t">
                        <td class="px-4 py-2 font-medium text-gray-800 uppercase">{p.name}</td>
                        <td class="px-4 py-2 text-gray-700">
                          {llmForm()[`${p.name}_model`] || p.current_model || '-'}
                        </td>
                        <td class="px-4 py-2">
                          <span class={`text-xs px-2 py-1 rounded-full font-bold uppercase ${p.configured ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                            {p.configured ? 'Connected' : 'Missing Config'}
                          </span>
                        </td>
                        <td class="px-4 py-2 text-gray-700">
                          {p.available_models && p.available_models.length > 0 ? `${p.available_models.length}` : '—'}
                        </td>
                        <td class="px-4 py-2 text-gray-700">
                          {p.requirements.join(', ')}
                        </td>
                        <td class="px-4 py-2">
                          <div class="flex items-center gap-2">
                            <button 
                              onClick={() => testProvider(p.name)}
                              class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                            >
                              Test
                            </button>
                            <button 
                              onClick={() => openProviderEditor(p.name)}
                              class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                            >
                              Edit
                            </button>
                            <button 
                              onClick={() => openModelManager(p)}
                              class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                              disabled={!p.models || p.models.length === 0}
                              title={(!p.models || p.models.length === 0) ? "No models discovered" : "Manage available models"}
                            >
                              Manage
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </For>
                </tbody>
              </table>
            </div>

            {/* Custom Models */}
            <div class="border-t pt-6">
              <h4 class="text-lg font-bold mb-3">Custom Models</h4>
              <div class="space-y-3">
                <div class="space-y-2">
                  <For each={customModels()}>
                    {(m) => (
                      <div class="p-3 border rounded-lg flex items-center justify-between">
                        <div>
                          <div class="font-bold">{m.name}</div>
                          <div class="text-xs text-gray-500">{m.base_url || ''}</div>
                          <div class="text-xs text-gray-500">{m.model || ''}</div>
                        </div>
                        <div class="flex gap-2">
                          <button onClick={()=>testCustomModel(m)} class="text-xs px-2 py-1 rounded border">Test</button>
                          <button onClick={()=>deleteCustomModel(m.name)} class="text-xs px-2 py-1 rounded border text-red-600">Delete</button>
                        </div>
                      </div>
                    )}
                  </For>
                  <Show when={customModels().length === 0}>
                    <div class="text-sm text-gray-500">No custom models. Add one above.</div>
                  </Show>
                </div>
              </div>
            </div>
            <Show when={showAddCustom()}>
              <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                <div class="w-[720px] bg-white rounded-2xl border shadow-xl overflow-hidden">
                  <div class="px-6 py-4 border-b flex justify-between items-center">
                    <div class="font-bold text-lg">Add Custom Model</div>
                    <button onClick={() => setShowAddCustom(false)} class="text-gray-500">✕</button>
                  </div>
                  <div class="p-6 space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div class="text-xs font-bold text-gray-600 mb-1">Name</div>
                        <input class="w-full border rounded-lg p-2" placeholder="my-custom" value={newCM().name} onInput={e => setNewCM({...newCM(), name: e.currentTarget.value})}/>
                      </div>
                      <div>
                        <div class="text-xs font-bold text-gray-600 mb-1">Provider</div>
                        <select class="w-full border rounded-lg p-2" value={newCM().provider} onChange={e => setNewCM({...newCM(), provider: e.currentTarget.value})}>
                          <option value="openai">OpenAI</option>
                          <option value="deepseek">DeepSeek</option>
                          <option value="gemini">Gemini</option>
                          <option value="ollama">Ollama</option>
                        </select>
                      </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div class="text-xs font-bold text-gray-600 mb-1">Model</div>
                        <input class="w-full border rounded-lg p-2" placeholder="gpt-4o" value={newCM().model} onInput={e => setNewCM({...newCM(), model: e.currentTarget.value})}/>
                      </div>
                      <div>
                        <div class="text-xs font-bold text-gray-600 mb-1">Base URL (Optional)</div>
                        <input class="w-full border rounded-lg p-2" placeholder="https://..." value={newCM().base_url || ''} onInput={e => setNewCM({...newCM(), base_url: e.currentTarget.value})}/>
                      </div>
                    </div>
                    <div>
                      <div class="text-xs font-bold text-gray-600 mb-1">API Key</div>
                      <input class="w-full border rounded-lg p-2" type="password" placeholder="****" value={newCM().api_key || ''} onInput={e => setNewCM({...newCM(), api_key: e.currentTarget.value})}/>
                    </div>
                    <div class="text-xs text-gray-600">{newCMStatus()}</div>
                  </div>
                  <div class="px-6 py-4 border-t flex justify-end gap-2">
                    <button onClick={() => setShowAddCustom(false)} class="px-3 py-1.5 rounded-lg border">Cancel</button>
                    <button 
                      onClick={async () => {
                        setNewCMStatus("Testing...")
                        const res = await fetch('/api/models/test/custom', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ base_url: newCM().base_url, api_key: newCM().api_key, model: newCM().model })
                        });
                        const data = await res.json();
                        setNewCMStatus(data.ok ? "Connection OK" : `Failed: ${data.error || 'Unknown error'}`)
                      }} 
                      class="px-3 py-1.5 rounded-lg border bg-white"
                    >
                      Test
                    </button>
                    <button 
                      onClick={async () => {
                        if (!newCM().name) { setNewCMStatus("Name is required"); return; }
                        await fetch('/api/models/custom', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ name: newCM().name, base_url: newCM().base_url, api_key: newCM().api_key, model: newCM().model })
                        });
                        const cmRes = await fetch('/api/models/custom');
                        setCustomModels(await cmRes.json());
                        setShowAddCustom(false);
                        setNewCM({name:"",provider:"openai",model:""});
                        setNewCMStatus("");
                      }} 
                      class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white"
                    >
                      Save
                    </button>
                  </div>
                </div>
              </div>
            </Show>

            {/* Model Manager Modal */}
            <Show when={showModelManager()}>
              <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                <div class="w-[600px] bg-white rounded-2xl border shadow-xl overflow-hidden flex flex-col max-h-[80vh]">
                  <div class="px-6 py-4 border-b flex justify-between items-center bg-gray-50">
                    <div class="font-bold text-lg">Manage Models: {managingProvider()}</div>
                    <button onClick={() => setShowModelManager(false)} class="text-gray-500 hover:text-gray-700">✕</button>
                  </div>
                  
                  <div class="p-4 border-b bg-white flex justify-between items-center">
                    <div class="text-sm text-gray-500">
                      Select models to make available in the chat interface.
                    </div>
                    <div class="flex gap-2">
                      <button 
                        onClick={() => setEnabledModels(new Set(managedModels()))}
                        class="text-xs px-2 py-1 text-emerald-600 hover:bg-emerald-50 rounded"
                      >
                        Select All
                      </button>
                      <button 
                        onClick={() => setEnabledModels(new Set())}
                        class="text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded"
                      >
                        Deselect All
                      </button>
                    </div>
                  </div>

                  <div class="flex-1 overflow-y-auto p-2">
                    <div class="grid grid-cols-1 gap-1">
                      <For each={managedModels()}>
                        {(model) => (
                          <label class="flex items-center gap-3 p-2 hover:bg-gray-50 rounded cursor-pointer transition-colors">
                            <input 
                              type="checkbox" 
                              class="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500 border-gray-300"
                              checked={enabledModels().has(model)} 
                              onChange={(e) => {
                                const newSet = new Set(enabledModels());
                                if (e.currentTarget.checked) {
                                  newSet.add(model);
                                } else {
                                  newSet.delete(model);
                                }
                                setEnabledModels(newSet);
                              }}
                            />
                            <span class={`text-sm ${enabledModels().has(model) ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                              {model}
                            </span>
                          </label>
                        )}
                      </For>
                      <Show when={managedModels().length === 0}>
                        <div class="p-8 text-center text-gray-500">
                          No models found for this provider.
                        </div>
                      </Show>
                    </div>
                  </div>

                  <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-2">
                    <button 
                      onClick={() => setShowModelManager(false)} 
                      class="px-4 py-2 rounded-lg border bg-white hover:bg-gray-50 text-sm font-medium"
                      disabled={isSavingModels()}
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={saveManagedModels} 
                      class="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={isSavingModels()}
                    >
                      {isSavingModels() ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              </div>
            </Show>

            <div class="pt-4 sticky bottom-0 bg-white pb-4">
              <button 
                onClick={saveLlmConfig}
                class="bg-emerald-600 text-white px-10 py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all shadow-lg hover:shadow-emerald-200"
              >
                Save All LLM Settings
              </button>
            </div>
            <Show when={showEditProvider()}>
              <div class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
                <div class="w-[680px] bg-white rounded-2xl border shadow-xl overflow-hidden">
                  <div class="px-6 py-4 border-b flex justify-between items-center">
                    <div class="font-bold text-lg">Edit Provider: {editingProvider()}</div>
                    <button onClick={() => setShowEditProvider(false)} class="text-gray-500">✕</button>
                  </div>
                  <div class="p-6 space-y-4">
                    <Show when={editingProvider() === 'openai'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">OPENAI_API_KEY</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().openai_api_key || ''} onInput={e => setLlmForm({ ...llmForm(), openai_api_key: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">openai_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().openai_model || ''} onInput={e => setLlmForm({ ...llmForm(), openai_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'deepseek'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">DEEPSEEK_API_KEY</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().deepseek_api_key || ''} onInput={e => setLlmForm({ ...llmForm(), deepseek_api_key: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">deepseek_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().deepseek_model || ''} onInput={e => setLlmForm({ ...llmForm(), deepseek_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'gemini'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">GEMINI_API_KEY</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().gemini_api_key || ''} onInput={e => setLlmForm({ ...llmForm(), gemini_api_key: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">GEMINI_BASE_URL</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().gemini_base_url || ''} onInput={e => setLlmForm({ ...llmForm(), gemini_base_url: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">gemini_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().gemini_model || ''} onInput={e => setLlmForm({ ...llmForm(), gemini_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'ollama'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">OLLAMA_BASE_URL</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().ollama_base_url || ''} onInput={e => setLlmForm({ ...llmForm(), ollama_base_url: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">ollama_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().ollama_model || ''} onInput={e => setLlmForm({ ...llmForm(), ollama_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'zhipu'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">ZHIPU_API_KEY</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().zhipu_api_key || ''} onInput={e => setLlmForm({ ...llmForm(), zhipu_api_key: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">ZHIPU_BASE_URL</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().zhipu_base_url || ''} onInput={e => setLlmForm({ ...llmForm(), zhipu_base_url: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">zhipu_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().zhipu_model || ''} onInput={e => setLlmForm({ ...llmForm(), zhipu_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'azure_openai'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_BASE_URL</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().azure_openai_base_url || ''} onInput={e => setLlmForm({ ...llmForm(), azure_openai_base_url: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_DEPLOYMENT</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().azure_openai_deployment || ''} onInput={e => setLlmForm({ ...llmForm(), azure_openai_deployment: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_API_VERSION</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().azure_openai_api_version || ''} onInput={e => setLlmForm({ ...llmForm(), azure_openai_api_version: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_TENANT_ID</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().azure_tenant_id || ''} onInput={e => setLlmForm({ ...llmForm(), azure_tenant_id: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_CLIENT_ID</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().azure_client_id || ''} onInput={e => setLlmForm({ ...llmForm(), azure_client_id: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_CLIENT_SECRET</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().azure_client_secret || ''} onInput={e => setLlmForm({ ...llmForm(), azure_client_secret: e.currentTarget.value })}/>
                        </div>
                        <div class="md:col-span-2">
                          <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_TOKEN (Optional)</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().azure_openai_token || ''} onInput={e => setLlmForm({ ...llmForm(), azure_openai_token: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                    <Show when={editingProvider() === 'litellm'}>
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">LITELLM_BASE_URL</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().litellm_base_url || ''} onInput={e => setLlmForm({ ...llmForm(), litellm_base_url: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">LITELLM_API_KEY</div>
                          <input class="w-full border rounded-lg p-2" type="password" value={llmForm().litellm_api_key || ''} onInput={e => setLlmForm({ ...llmForm(), litellm_api_key: e.currentTarget.value })}/>
                        </div>
                        <div>
                          <div class="text-xs font-bold text-gray-600 mb-1">litellm_model</div>
                          <input class="w-full border rounded-lg p-2" value={llmForm().litellm_model || ''} onInput={e => setLlmForm({ ...llmForm(), litellm_model: e.currentTarget.value })}/>
                        </div>
                      </div>
                    </Show>
                  </div>
                  <div class="px-6 py-4 border-t flex justify-end gap-2">
                    <button onClick={() => setShowEditProvider(false)} class="px-3 py-1.5 rounded-lg border">Cancel</button>
                    <button onClick={saveProviderEditor} class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white">Save</button>
                  </div>
                </div>
              </div>
            </Show>
          </div>
        </Show>
      <Show when={toast()}>
        <div class="fixed bottom-6 right-6 z-50" role="status" aria-live="polite">
          <div class={`px-4 py-3 rounded-xl shadow-lg border transition-all transform ${toast()!.type==='success' ? 'bg-emerald-600 text-white border-emerald-700' : 'bg-red-600 text-white border-red-700'}`}>
            <div class="flex items-center gap-3">
              <div class="w-5 h-5">
                <svg viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.707l-4 4a1 1 0 01-1.414 0l-2-2 1.414-1.414L9 10.586l3.293-3.293 1.414 1.414z"/>
                </svg>
              </div>
              <div class="text-sm font-semibold flex-1">{toast()!.message}</div>
              <Show when={toast()!.actionLabel}>
                <button class="text-xs px-2 py-1 rounded bg-white/20 hover:bg-white/30" onClick={() => { toast()!.action?.(); setToast(null); }}>
                  {toast()!.actionLabel}
                </button>
              </Show>
              <button class="text-white/80 hover:text-white" onClick={() => setToast(null)}>✕</button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  </div>
  );
}
