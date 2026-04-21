import { createSignal, onMount, onCleanup, For, Show } from 'solid-js';
import { ConfirmModal } from '../components/ConfirmModal';
import { GeneralSettingsTab } from './settings/components/GeneralSettingsTab';
import { LlmSettingsTab } from './settings/components/LlmSettingsTab';
import { McpSettingsTab } from './settings/components/McpSettingsTab';
import { useSettingsData } from './settings/useSettingsData';
import {
  buildManagedModelsConfig,
  buildRevertedManagedModelsConfig,
  parseMcpManualText,
  splitRootsText,
} from './settings/settingsUtils';
import { publishFeatureFlagsUpdate, publishPreferencesUpdate } from '../utils/preferencesSync';
import type {
  Agent,
  CustomModel,
  DocAccess,
  FeatureFlags,
  LLMProvider,
  LlmForm,
  McpStatus,
  McpTool,
  NewCustomModelDraft,
  Preferences,
} from './settings/types';
import { DEFAULT_FEATURE_FLAGS, DEFAULT_PREFERENCES, normalizeFeatureFlags, normalizePreferences } from './settings/types';

type Tab = 'general' | 'mcp' | 'llm';

  export default function Settings() {
    const { fetchSettingsData } = useSettingsData();
    const [activeTab, setActiveTab] = createSignal<Tab>('general');
    const TAB_LABEL: Record<Tab, { label: string; icon: string }> = {
      general: { label: 'General', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37a1.724 1.724 0 002.572-1.065z' },
      mcp: { label: 'MCP', icon: 'M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z' },
      llm: { label: 'Models', icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z' }
    };
    
    // MCP State
    const [mcpConfig, setMcpConfig] = createSignal("");
    const [mcpStatus, setMcpStatus] = createSignal<McpStatus[]>([]);
    const [mcpTools, setMcpTools] = createSignal<McpTool[]>([]);
    const [expanded, setExpanded] = createSignal<Record<string, boolean>>({});
    const [showManual, setShowManual] = createSignal(false);
    const [manualText, setManualText] = createSignal(`{\n  \"mcpServers\": {\n    \"example-server\": {\n      \"command\": \"npx\",\n      \"args\": [\"-y\", \"mcp-server-example\"]\n    }\n  }\n}`);
    const [showRaw, setShowRaw] = createSignal(false);
    const [showAddMenu, setShowAddMenu] = createSignal(false);
    const [showMarketplace, setShowMarketplace] = createSignal(false);
    const [hoveredServer, setHoveredServer] = createSignal<string | null>(null);
    
    // LLM State
  const [providers, setProviders] = createSignal<LLMProvider[]>([]);
  const [llmForm, setLlmForm] = createSignal<LlmForm>({});
  const [customModels, setCustomModels] = createSignal<CustomModel[]>([]);
    const [showAddCustom, setShowAddCustom] = createSignal(false);
    const [newCM, setNewCM] = createSignal<NewCustomModelDraft>({name:"",provider:"openai",model:"",capabilities:[]});
    const [newCMStatus, setNewCMStatus] = createSignal<string>("");
  const [showEditProvider, setShowEditProvider] = createSignal(false);
  const [editingProvider, setEditingProvider] = createSignal<string>("");
  const [toast, setToast] = createSignal<{type:'success'|'error';message:string;actionLabel?:string;action?:()=>void}|null>(null);
  const [confirmDelete, setConfirmDelete] = createSignal<{id: string, type: 'model' | 'mcp'} | null>(null);
  const showToast = (type:'success'|'error', message:string, actionLabel?:string, action?:()=>void) => {
    setToast({ type, message, actionLabel, action });
    setTimeout(() => setToast(null), 3000);
  };
    
    // Model Management State
    const [showModelManager, setShowModelManager] = createSignal(false);
    const [managingProvider, setManagingProvider] = createSignal<string | null>(null);
    const [managedModels, setManagedModels] = createSignal<string[]>([]);
    const [enabledModels, setEnabledModels] = createSignal<Set<string>>(new Set());
    const [capabilityOverrides, setCapabilityOverrides] = createSignal<Record<string, string[]>>({});
    const [isSavingModels, setIsSavingModels] = createSignal(false);
    const [isRefreshingProviders, setIsRefreshingProviders] = createSignal(false);
    
    // Add loading state and cache for the modal
    const [isLoadingModels, setIsLoadingModels] = createSignal(false);
    const [adminModelsCache, setAdminModelsCache] = createSignal<Record<string, any>>({});
    const [adminModelCapabilities, setAdminModelCapabilities] = createSignal<Record<string, string[]>>({});
    
    // Agents State
    const [agents, setAgents] = createSignal<Agent[]>([]);
  
  // General Preferences State
  const [prefs, setPrefs] = createSignal<Preferences>({
    ...DEFAULT_PREFERENCES
  });
  const [docAccess, setDocAccess] = createSignal<DocAccess>({
    allow_roots: [],
    deny_roots: []
  });
  const [featureFlags, setFeatureFlags] = createSignal<FeatureFlags>({
    ...DEFAULT_FEATURE_FLAGS,
  });
  const [docAllowText, setDocAllowText] = createSignal("");
  const [docDenyText, setDocDenyText] = createSignal("");
  const [isSavingDocAccess, setIsSavingDocAccess] = createSignal(false);

  const fetchData = async () => {
    try {
      const snapshot = await fetchSettingsData();
      setMcpConfig(snapshot.mcpConfigText);
      setMcpStatus(snapshot.mcpStatus);
      setMcpTools(snapshot.mcpTools);
      setProviders(snapshot.providers);
      setLlmForm(snapshot.llmForm);
      setCustomModels(snapshot.customModels);
      setAgents(snapshot.agents);
      setPrefs(snapshot.prefs);
      setDocAccess(snapshot.docAccess);
      setFeatureFlags(snapshot.featureFlags);
      setDocAllowText(snapshot.docAllowText);
      setDocDenyText(snapshot.docDenyText);
    } catch (e) {
      console.error("Failed to load settings", e);
    }
  };

  onMount(fetchData);
  onMount(() => {
    const handleGlobalClick = () => setShowAddMenu(false);
    window.addEventListener('click', handleGlobalClick);
    onCleanup(() => window.removeEventListener('click', handleGlobalClick));
  });

  const saveMcp = async () => {
    try {
      const parsed = JSON.parse(mcpConfig());
      await fetch('/api/mcp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed)
      });
      showToast('success', "MCP Configuration saved!");
      await fetch('/api/mcp/reload', { method: 'POST' });
      const mcpStatusRes = await fetch('/api/mcp/status');
      setMcpStatus(await mcpStatusRes.json());
    } catch (e) {
      showToast('error', "Invalid JSON: " + e);
    }
  };

  const saveLlmConfig = async () => {
    await postLlmConfig(llmForm());
    showToast('success', 'LLM settings saved');
  };

  const postLlmConfig = async (nextConfig: LlmForm) => {
    setLlmForm(nextConfig);
    await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextConfig)
    });
    await fetchData();
  };

  const refreshProviders = async () => {
    setIsRefreshingProviders(true);
    try {
      const providersRes = await fetch('/api/models/providers?refresh=1');
      setProviders(await providersRes.json());
      showToast('success', 'Models refreshed from providers');
    } catch (e) {
      showToast('error', 'Failed to refresh models');
    } finally {
      setIsRefreshingProviders(false);
    }
  };

  const savePrefs = async (nextPrefs?: Preferences) => {
    const payload = normalizePreferences(nextPrefs ?? prefs());
    setPrefs(payload);
    await fetch('/api/config/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    publishPreferencesUpdate(payload);
    showToast('success', 'Preferences saved');
  };

  const saveDocAccess = async () => {
    setIsSavingDocAccess(true);
    try {
      const allow = splitRootsText(docAllowText());
      const deny = splitRootsText(docDenyText());
      const res = await fetch('/api/config/doc_access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allow_roots: allow, deny_roots: deny })
      });
      if (!res.ok) {
        showToast('error', 'Failed to save document access');
        return;
      }
      const da = await res.json();
      setDocAccess(da);
      setDocAllowText((da.allow_roots || []).join("\n"));
      setDocDenyText((da.deny_roots || []).join("\n"));
      showToast('success', 'Document access saved');
    } finally {
      setIsSavingDocAccess(false);
    }
  };

  const saveFeatureFlags = async (nextFlags?: FeatureFlags) => {
    const payload = nextFlags ?? featureFlags();
    setFeatureFlags(payload);
    const res = await fetch('/api/config/feature_flags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      showToast('error', 'Failed to save feature flags');
      return;
    }
    const saved = await res.json();
    const normalized = normalizeFeatureFlags(saved);
    setFeatureFlags(normalized);
    publishFeatureFlagsUpdate(normalized);
    showToast('success', 'Feature flags saved');
  };


  const openModelManager = async (provider: LLMProvider) => {
    setManagingProvider(provider.name);
    setShowModelManager(true);
    
    // Check cache first
    if (adminModelsCache()[provider.name]) {
      const data = adminModelsCache()[provider.name];
      setManagedModels(data.models || []);
      setEnabledModels(new Set<string>(data.available_models || []));
      setCapabilityOverrides(data.explicit_model_capabilities || {});
      setAdminModelCapabilities(data.model_capabilities || {});
      return;
    }

    setIsLoadingModels(true);
    try {
      // Fetch full list from new admin endpoint
      const res = await fetch(`/api/models/providers/${provider.name}/models`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      
      setManagedModels(data.models || []);
      setEnabledModels(new Set<string>(data.available_models || []));
      setCapabilityOverrides(data.explicit_model_capabilities || {});
      
      // We also need to store the full capabilities for rendering the badges in the modal
      setAdminModelCapabilities(data.model_capabilities || {});
      
      // Cache the result
      setAdminModelsCache(prev => ({ ...prev, [provider.name]: data }));
    } catch (e: any) {
      console.error("Failed to load models", e);
      showToast('error', `Failed to load models: ${e.message}`);
    } finally {
      setIsLoadingModels(false);
    }
  };
  const openProviderEditor = (name: string) => {
    setEditingProvider(name);
    setShowEditProvider(true);
  };
  const saveProviderEditor = async () => {
    await postLlmConfig(llmForm());
    setShowEditProvider(false);
  };

  const saveManagedModels = async () => {
    const providerName = managingProvider();
    if (!providerName) return;
    setIsSavingModels(true);
    
    try {
      const previous = new Set(enabledModels());
      const previousOverrides = { ...capabilityOverrides() };
      const currentConfig = llmForm();
      const { modelsDict, nextConfig: newConfig, previousMode } = buildManagedModelsConfig(
        currentConfig,
        providerName,
        enabledModels(),
        managedModels(),
        capabilityOverrides(),
      );
      await postLlmConfig(newConfig);
      setShowModelManager(false);
      showToast('success', `Models for ${providerName} updated`, 'Undo', async () => {
        const revertConfig = buildRevertedManagedModelsConfig(
          currentConfig,
          providerName,
          previous,
          previousMode,
          modelsDict,
          managedModels(),
          previousOverrides,
        );
        await postLlmConfig(revertConfig);
        showToast('success', `Reverted ${providerName} models`);
      });
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
      showToast('success', `${name} connection OK`);
    } else {
      showToast('error', `${name} failed: ${data.error || 'Unknown error'}`);
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
      showToast('error', "Failed to toggle server: " + e);
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
      const parsed = parseMcpManualText(manualText());
      if (parsed.kind === 'empty') return;
      if (parsed.kind === 'invalid_json') {
        showToast('error', 'Invalid JSON format');
        return;
      }
      if (parsed.kind === 'no_valid_servers') {
        showToast('error', 'No valid MCP server configuration found in JSON');
        return;
      }
      const arr = parsed.servers;

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
    setConfirmDelete({ id: name, type: 'model' });
  };

  const actualDeleteCustomModel = async (name: string) => {
    await fetch(`/api/models/custom/${name}`, { method: 'DELETE' });
    const cmRes = await fetch('/api/models/custom');
    setCustomModels(await cmRes.json());
    showToast('success', `Custom model ${name} deleted`);
  };

  const deleteMcpServer = async (serverName: string) => {
    setConfirmDelete({ id: serverName, type: 'mcp' });
  };

  const actualDeleteMcpServer = async (serverName: string) => {
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
    if (data.ok) {
      showToast('success', `Custom ${m.name} OK`);
    } else {
      showToast('error', `Custom ${m.name} failed: ${data.error || 'Unknown error'}`);
    }
  };

  return (
    <div class="p-8 h-full flex flex-col bg-gray-50 overflow-hidden">
      <div class="flex justify-between items-center mb-8">
        <div>
          <h2 class="text-3xl font-bold text-gray-800">System Configuration</h2>
          <p class="text-gray-500 mt-1">Manage your workspace, models, and platform settings.</p>
        </div>
        <div class="flex items-center gap-2">
          <div class="text-sm text-gray-500 bg-white px-3 py-1 rounded-full border shadow-sm flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Unified Platform
          </div>
        </div>
      </div>

      <div class="flex flex-1 gap-8 overflow-hidden">
        {/* Sidebar Navigation */}
        <div class="w-64 flex flex-col space-y-1">
          <For each={['general', 'mcp', 'llm']}>
            {(tab) => (
              <button
                onClick={() => setActiveTab(tab as Tab)}
                class={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  activeTab() === tab 
                  ? 'bg-white text-emerald-600 shadow-sm border border-gray-100' 
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={TAB_LABEL[tab as Tab].icon} />
                </svg>
                {TAB_LABEL[tab as Tab].label}
                <Show when={activeTab() === tab}>
                  <div class="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                </Show>
              </button>
            )}
          </For>
        </div>

        {/* Content Area */}
        <div class="flex-1 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-y-auto p-8 relative">
          {/* General Tab */}
          <Show when={activeTab() === 'general'}>
            <GeneralSettingsTab
              prefs={prefs}
              setPrefs={setPrefs}
              agents={agents}
              savePrefs={savePrefs}
              featureFlags={featureFlags}
              setFeatureFlags={setFeatureFlags}
              saveFeatureFlags={saveFeatureFlags}
              docAccess={docAccess}
              docAllowText={docAllowText}
              setDocAllowText={setDocAllowText}
              docDenyText={docDenyText}
              setDocDenyText={setDocDenyText}
              isSavingDocAccess={isSavingDocAccess}
              saveDocAccess={saveDocAccess}
            />
          </Show>

          {/* MCP Tab */}
          <Show when={activeTab() === 'mcp'}>
            <McpSettingsTab
              mcpStatus={mcpStatus}
              mcpTools={mcpTools}
              expanded={expanded}
              setExpanded={setExpanded}
              hoveredServer={hoveredServer}
              setHoveredServer={setHoveredServer}
              showAddMenu={showAddMenu}
              setShowAddMenu={setShowAddMenu}
              showManual={showManual}
              setShowManual={setShowManual}
              manualText={manualText}
              setManualText={setManualText}
              showRaw={showRaw}
              setShowRaw={setShowRaw}
              showMarketplace={showMarketplace}
              setShowMarketplace={setShowMarketplace}
              mcpConfig={mcpConfig}
              setMcpConfig={setMcpConfig}
              reloadMcp={reloadMcp}
              toggleMcpEnabled={toggleMcpEnabled}
              deleteMcpServer={deleteMcpServer}
              confirmManual={confirmManual}
              saveMcp={saveMcp}
            />
          </Show>

          {/* LLM Tab */}
          <Show when={activeTab() === 'llm'}>
            <LlmSettingsTab
              providers={providers}
              llmForm={llmForm}
              setLlmForm={setLlmForm}
              customModels={customModels}
              setCustomModels={setCustomModels}
              prefs={prefs}
              isRefreshingProviders={isRefreshingProviders}
              setIsRefreshingProviders={setIsRefreshingProviders}
              showAddCustom={showAddCustom}
              setShowAddCustom={setShowAddCustom}
              newCM={newCM}
              setNewCM={setNewCM}
              newCMStatus={newCMStatus}
              setNewCMStatus={setNewCMStatus}
              showEditProvider={showEditProvider}
              setShowEditProvider={setShowEditProvider}
              editingProvider={editingProvider}
              showModelManager={showModelManager}
              setShowModelManager={setShowModelManager}
              managingProvider={managingProvider}
              managedModels={managedModels}
              enabledModels={enabledModels}
              setEnabledModels={setEnabledModels}
              capabilityOverrides={capabilityOverrides}
              setCapabilityOverrides={setCapabilityOverrides}
              adminModelCapabilities={adminModelCapabilities}
              isLoadingModels={isLoadingModels}
              isSavingModels={isSavingModels}
              refreshProviders={refreshProviders}
              saveLlmConfig={saveLlmConfig}
              testProvider={testProvider}
              openProviderEditor={openProviderEditor}
              saveProviderEditor={saveProviderEditor}
              openModelManager={openModelManager}
              saveManagedModels={saveManagedModels}
              deleteCustomModel={deleteCustomModel}
              testCustomModel={testCustomModel}
            />
          </Show>
        </div>
      </div>
      <Show when={toast()}>
        <div class="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300" role="status" aria-live="polite">
          <div class={`flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl border transition-all ${
            toast()?.type === 'success' 
              ? 'bg-emerald-50 border-emerald-100 text-emerald-800' 
              : 'bg-red-50 border-red-100 text-red-800'
          }`}>
            <Show when={toast()?.type === 'success'} fallback={
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            }>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </Show>
            <p class="font-medium">{toast()?.message}</p>
            <Show when={toast()?.action}>
              <button 
                onClick={() => { toast()?.action?.(); setToast(null); }}
                class="ml-2 px-3 py-1 bg-white/50 hover:bg-white rounded-lg text-sm font-bold transition-colors"
              >
                {toast()?.actionLabel}
              </button>
            </Show>
            <button class="ml-auto text-gray-400 hover:text-gray-600" onClick={() => setToast(null)}>✕</button>
          </div>
        </div>
      </Show>

      <ConfirmModal
        show={!!confirmDelete()}
        title={confirmDelete()?.type === 'model' ? "Delete Custom Model" : "Delete MCP Server"}
        message={confirmDelete()?.type === 'model' 
          ? `Are you sure you want to delete the custom model "${confirmDelete()?.id}"?`
          : `Are you sure you want to delete the MCP server "${confirmDelete()?.id}"? This action cannot be undone.`
        }
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
        onConfirm={() => {
          const item = confirmDelete();
          if (item) {
            if (item.type === 'model') actualDeleteCustomModel(item.id);
            else actualDeleteMcpServer(item.id);
            setConfirmDelete(null);
          }
        }}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
