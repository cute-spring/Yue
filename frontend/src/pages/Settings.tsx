import { createSignal, onMount, For } from 'solid-js';

export default function Settings() {
  const [jsonConfig, setJsonConfig] = createSignal("");
  const [providers, setProviders] = createSignal<{name: string, configured: boolean, requirements: string[]}[]>([]);

  onMount(async () => {
    try {
      const res = await fetch('/api/mcp/');
      const data = await res.json();
      setJsonConfig(JSON.stringify(data, null, 2));
    } catch (e) {
      console.error("Failed to load configs", e);
    }
    try {
      const res = await fetch('/api/models/providers');
      const data = await res.json();
      setProviders(data);
    } catch (e) {}
  });

  const handleSave = async () => {
    try {
      const parsed = JSON.parse(jsonConfig());
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      alert("Saved! Please restart the backend to apply changes.");
    } catch (e) {
      alert("Invalid JSON: " + e);
    }
  };

  return (
    <div class="p-6 h-full overflow-y-auto">
      <h2 class="text-2xl font-bold mb-6">MCP Settings</h2>
      <div class="mb-6">
        <h3 class="text-lg font-semibold mb-2">LLM Providers</h3>
        <div class="grid md:grid-cols-2 gap-3">
          <For each={providers()}>
            {(p) => (
              <div class="border rounded p-3 bg-white">
                <div class="flex justify-between">
                  <span class="font-medium">{p.name}</span>
                  <span class={p.configured ? 'text-emerald-600' : 'text-gray-500'}>{p.configured ? 'configured' : 'not configured'}</span>
                </div>
                <div class="text-xs text-gray-600 mt-2">requirements: {p.requirements.join(', ')}</div>
              </div>
            )}
          </For>
        </div>
      </div>
      
      <div class="mb-4 h-[calc(100%-100px)]">
        <p class="text-gray-600 mb-2">Configure MCP servers (JSON)</p>
        <textarea
          class="w-full h-full font-mono border p-4 rounded bg-gray-50 resize-none"
          value={jsonConfig()}
          onInput={e => setJsonConfig(e.currentTarget.value)}
        />
      </div>
      
      <button 
        onClick={handleSave}
        class="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
      >
        Save Configuration
      </button>
    </div>
  );
}
