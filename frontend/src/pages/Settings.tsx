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
};

export default function Settings() {
  const [activeTab, setActiveTab] = createSignal<Tab>('general');
  
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
  const [llmForm, setLlmForm] = createSignal<Record<string, string>>({});
  const [customModels, setCustomModels] = createSignal<{name:string;base_url?:string;api_key?:string;model?:string}[]>([]);
  const [cmDraft, setCmDraft] = createSignal<{name:string;base_url?:string;api_key?:string;model?:string}>({name:""});
  
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
    alert("LLM Configuration saved!");
    fetchData();
  };

  const savePrefs = async () => {
    await fetch('/api/config/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs())
    });
    alert("Preferences saved!");
  };

  const handleLlmInput = (key: string, value: string) => {
    setLlmForm(prev => ({ ...prev, [key]: value }));
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
      const parsed = JSON.parse(manualText());
      const arr = Array.isArray(parsed) ? parsed : (parsed.mcpServers ? Object.keys(parsed.mcpServers).map(k => ({ name: k, ...parsed.mcpServers[k] })) : []);
      await fetch('/api/mcp/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(arr) });
      await reloadMcp();
      setShowManual(false);
    } catch (e) {
      alert('Invalid JSON');
    }
  };

  const saveCustomModel = async () => {
    if (!cmDraft().name) {
      alert("Name is required");
      return;
    }
    await fetch('/api/models/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cmDraft())
    });
    const cmRes = await fetch('/api/models/custom');
    setCustomModels(await cmRes.json());
    setCmDraft({name:""});
  };

  const deleteCustomModel = async (name: string) => {
    if (!confirm(`Delete custom model ${name}?`)) return;
    await fetch(`/api/models/custom/${name}`, { method: 'DELETE' });
    const cmRes = await fetch('/api/models/custom');
    setCustomModels(await cmRes.json());
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
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
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
                    <div class="absolute right-0 mt-2 w-56 bg-white border rounded-lg shadow-xl">
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
                      <label class="flex items-center gap-2">
                        <input type="checkbox" checked={s.enabled} onChange={e => toggleMcpEnabled(s.name, e.currentTarget.checked)} />
                      </label>
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
            </div>
            
            <div class="grid gap-8">
              <For each={providers()}>
                {(p) => (
                  <div class="p-6 border rounded-2xl bg-white shadow-sm hover:shadow-md transition-shadow">
                    <div class="flex justify-between items-center mb-6">
                      <div class="flex items-center gap-3">
                        <div class={`w-3 h-3 rounded-full ${p.configured ? 'bg-emerald-500' : 'bg-gray-300 animate-pulse'}`}></div>
                        <h4 class="text-lg font-bold text-gray-800 uppercase tracking-wider">{p.name}</h4>
                      </div>
                      <span class={`text-xs px-2 py-1 rounded-full font-bold uppercase ${p.configured ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {p.configured ? 'Connected' : 'Missing Config'}
                      </span>
                    </div>

                    <div class="space-y-4">
                      {/* API Key Input */}
                      <Show when={p.requirements.some(r => r.includes('API_KEY'))}>
                        <div>
                          <label class="block text-xs font-bold text-gray-500 uppercase mb-1">API Key</label>
                          <input 
                            type="password"
                            class="w-full border rounded-lg p-2.5 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                            placeholder={`Enter ${p.name} API Key`}
                            value={llmForm()[`${p.name}_api_key`] || ''}
                            onInput={e => handleLlmInput(`${p.name}_api_key`, e.currentTarget.value)}
                          />
                        </div>
                      </Show>

                      {/* Model Input */}
                      <div>
                        <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Default Model</label>
                        <input 
                          class="w-full border rounded-lg p-2.5 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                          placeholder={`e.g. ${p.name === 'openai' ? 'gpt-4o' : p.name === 'zhipu' ? 'glm-4' : 'llama3'}`}
                          value={llmForm()[`${p.name}_model`] || ''}
                          onInput={e => handleLlmInput(`${p.name}_model`, e.currentTarget.value)}
                        />
                      </div>

                      {/* Base URL Input (Optional) */}
                      <Show when={p.requirements.some(r => r.includes('BASE_URL'))}>
                        <div>
                          <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Base URL (Optional)</label>
                          <input 
                            class="w-full border rounded-lg p-2.5 bg-gray-50 focus:bg-white focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                            placeholder="https://..."
                            value={llmForm()[`${p.name}_base_url`] || ''}
                            onInput={e => handleLlmInput(`${p.name}_base_url`, e.currentTarget.value)}
                          />
                        </div>
                      </Show>
                      <div class="pt-2">
                        <button 
                          onClick={() => testProvider(p.name)}
                          class="text-sm px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                        >
                          Test Connection
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </For>
            </div>

            {/* Custom Models */}
            <div class="border-t pt-6">
              <h4 class="text-lg font-bold mb-3">Custom Models</h4>
              <div class="space-y-3">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <input class="border rounded-lg p-2" placeholder="Name" value={cmDraft().name} onInput={e=>setCmDraft({...cmDraft(), name: e.currentTarget.value})}/>
                  <input class="border rounded-lg p-2" placeholder="Base URL" value={cmDraft().base_url || ''} onInput={e=>setCmDraft({...cmDraft(), base_url: e.currentTarget.value})}/>
                  <input type="password" class="border rounded-lg p-2" placeholder="API Key" value={cmDraft().api_key || ''} onInput={e=>setCmDraft({...cmDraft(), api_key: e.currentTarget.value})}/>
                  <input class="border rounded-lg p-2" placeholder="Model" value={cmDraft().model || ''} onInput={e=>setCmDraft({...cmDraft(), model: e.currentTarget.value})}/>
                </div>
                <div>
                  <button onClick={saveCustomModel} class="text-sm px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700">Add / Update</button>
                </div>
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

            <div class="pt-4 sticky bottom-0 bg-white pb-4">
              <button 
                onClick={saveLlmConfig}
                class="bg-emerald-600 text-white px-10 py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all shadow-lg hover:shadow-emerald-200"
              >
                Save All LLM Settings
              </button>
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}
