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
  
  // LLM State
  const [providers, setProviders] = createSignal<LLMProvider[]>([]);
  const [llmForm, setLlmForm] = createSignal<Record<string, string>>({});
  
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
      
      // Fetch LLM Providers
      const providersRes = await fetch('/api/models/providers');
      setProviders(await providersRes.json());
      
      // Fetch LLM Config (API Keys etc)
      const llmConfigRes = await fetch('/api/config/llm');
      setLlmForm(await llmConfigRes.json());
      
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

  const saveMcp = async () => {
    try {
      const parsed = JSON.parse(mcpConfig());
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      alert("MCP Configuration saved!");
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
            <div class="flex justify-between items-center border-b pb-2">
              <h3 class="text-xl font-semibold">MCP Integration</h3>
              <p class="text-sm text-gray-500">Model Context Protocol server configurations</p>
            </div>
            <div class="flex-1">
              <textarea
                class="w-full h-[400px] font-mono border rounded-xl p-4 bg-gray-900 text-emerald-400 focus:ring-2 focus:ring-emerald-500 outline-none shadow-inner"
                value={mcpConfig()}
                onInput={e => setMcpConfig(e.currentTarget.value)}
              />
            </div>
            <button 
              onClick={saveMcp}
              class="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition-colors w-fit shadow-md"
            >
              Save MCP Config
            </button>
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
                    </div>
                  </div>
                )}
              </For>
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
