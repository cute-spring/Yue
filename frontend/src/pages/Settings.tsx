import { createSignal, For, onCleanup, onMount, Show } from 'solid-js';
import { ConfirmModal } from '../components/ConfirmModal';
import { GeneralSettingsTab } from './settings/components/GeneralSettingsTab';
import { LlmSettingsTab } from './settings/components/LlmSettingsTab';
import { McpSettingsTab } from './settings/components/McpSettingsTab';
import {
  DEFAULT_FEATURE_FLAGS,
  DEFAULT_PREFERENCES,
  type Agent,
  type CustomModel,
  type DocAccess,
  type FeatureFlags,
  type LLMProvider,
  type LlmForm,
  type McpStatus,
  type McpTemplate,
  type McpTool,
  type NewCustomModelDraft,
  type Preferences,
} from './settings/types';
import { useSettingsData } from './settings/useSettingsData';
import { useSettingsGeneral } from './settings/useSettingsGeneral';
import { useSettingsLlm } from './settings/useSettingsLlm';
import { useSettingsMcp } from './settings/useSettingsMcp';

type Tab = 'general' | 'mcp' | 'llm';
type ConfirmDeleteState = { id: string; type: 'model' | 'mcp' } | null;
type ToastState = {
  type: 'success' | 'error';
  message: string;
  actionLabel?: string;
  action?: () => void;
} | null;

const TAB_LABEL: Record<Tab, string> = {
  general: 'General',
  mcp: 'MCP',
  llm: 'Models',
};

export default function Settings() {
  const { fetchSettingsData } = useSettingsData();
  const [activeTab, setActiveTab] = createSignal<Tab>('general');

  const [mcpConfig, setMcpConfig] = createSignal('');
  const [mcpStatus, setMcpStatus] = createSignal<McpStatus[]>([]);
  const [mcpTools, setMcpTools] = createSignal<McpTool[]>([]);
  const [mcpTemplates, setMcpTemplates] = createSignal<McpTemplate[]>([]);
  const [expanded, setExpanded] = createSignal<Record<string, boolean>>({});
  const [showManual, setShowManual] = createSignal(false);
  const [manualText, setManualText] = createSignal(
    `{\n  "mcpServers": {\n    "example-stdio": {\n      "transport": "stdio",\n      "command": "npx",\n      "args": ["-y", "mcp-server-example"]\n    },\n    "example-http": {\n      "transport": "streamable_http",\n      "url": "https://mcp.example.com/stream",\n      "headers": {"Authorization": "\${MCP_TOKEN}"}\n    }\n  }\n}`,
  );
  const [showRaw, setShowRaw] = createSignal(false);
  const [showAddMenu, setShowAddMenu] = createSignal(false);
  const [showMarketplace, setShowMarketplace] = createSignal(false);
  const [showSmartPaste, setShowSmartPaste] = createSignal(false);
  const [hoveredServer, setHoveredServer] = createSignal<string | null>(null);

  const [providers, setProviders] = createSignal<LLMProvider[]>([]);
  const [llmForm, setLlmForm] = createSignal<LlmForm>({});
  const [customModels, setCustomModels] = createSignal<CustomModel[]>([]);
  const [showAddCustom, setShowAddCustom] = createSignal(false);
  const [newCM, setNewCM] = createSignal<NewCustomModelDraft>({
    name: '',
    provider: 'openai',
    model: '',
    capabilities: [],
  });
  const [newCMStatus, setNewCMStatus] = createSignal('');
  const [showEditProvider, setShowEditProvider] = createSignal(false);
  const [editingProvider, setEditingProvider] = createSignal('');
  const [showModelManager, setShowModelManager] = createSignal(false);
  const [managingProvider, setManagingProvider] = createSignal<string | null>(null);
  const [managedModels, setManagedModels] = createSignal<string[]>([]);
  const [enabledModels, setEnabledModels] = createSignal<Set<string>>(new Set());
  const [capabilityOverrides, setCapabilityOverrides] = createSignal<Record<string, string[]>>({});
  const [isSavingModels, setIsSavingModels] = createSignal(false);
  const [isRefreshingProviders, setIsRefreshingProviders] = createSignal(false);
  const [isLoadingModels, setIsLoadingModels] = createSignal(false);
  const [adminModelsCache, setAdminModelsCache] = createSignal<Record<string, any>>({});
  const [adminModelCapabilities, setAdminModelCapabilities] = createSignal<Record<string, string[]>>({});

  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [prefs, setPrefs] = createSignal<Preferences>({ ...DEFAULT_PREFERENCES });
  const [docAccess, setDocAccess] = createSignal<DocAccess>({ allow_roots: [], deny_roots: [] });
  const [featureFlags, setFeatureFlags] = createSignal<FeatureFlags>({ ...DEFAULT_FEATURE_FLAGS });
  const [docAllowText, setDocAllowText] = createSignal('');
  const [docDenyText, setDocDenyText] = createSignal('');
  const [isSavingDocAccess, setIsSavingDocAccess] = createSignal(false);

  const [toast, setToast] = createSignal<ToastState>(null);
  const [confirmDelete, setConfirmDelete] = createSignal<ConfirmDeleteState>(null);

  const showToast = (
    type: 'success' | 'error',
    message: string,
    actionLabel?: string,
    action?: () => void,
  ) => {
    setToast({ type, message, actionLabel, action });
    setTimeout(() => setToast(null), 3000);
  };

  const fetchData = async () => {
    try {
      const snapshot = await fetchSettingsData();
      setMcpConfig(snapshot.mcpConfigText);
      setMcpStatus(snapshot.mcpStatus);
      setMcpTools(snapshot.mcpTools);
      setMcpTemplates(snapshot.mcpTemplates);
      setProviders(snapshot.providers);
      setLlmForm(snapshot.llmForm);
      setCustomModels(snapshot.customModels);
      setAgents(snapshot.agents);
      setPrefs(snapshot.prefs);
      setDocAccess(snapshot.docAccess);
      setFeatureFlags(snapshot.featureFlags);
      setDocAllowText(snapshot.docAllowText);
      setDocDenyText(snapshot.docDenyText);
    } catch (error) {
      console.error('Failed to load settings', error);
    }
  };

  onMount(fetchData);
  onMount(() => {
    const handleGlobalClick = () => setShowAddMenu(false);
    window.addEventListener('click', handleGlobalClick);
    onCleanup(() => window.removeEventListener('click', handleGlobalClick));
  });

  const general = useSettingsGeneral({
    prefs,
    setPrefs,
    featureFlags,
    setFeatureFlags,
    docAllowText,
    setDocAllowText,
    docDenyText,
    setDocDenyText,
    setDocAccess,
    setIsSavingDocAccess,
    showToast,
  });

  const mcp = useSettingsMcp({
    mcpConfig,
    setMcpConfig,
    manualText,
    setManualText,
    setMcpStatus,
    setShowManual,
    setShowSmartPaste,
    fetchData,
    showToast,
  });

  const llm = useSettingsLlm({
    llmForm,
    setLlmForm,
    setProviders,
    setCustomModels,
    setIsRefreshingProviders,
    managingProvider,
    setManagingProvider,
    setShowModelManager,
    managedModels,
    setManagedModels,
    enabledModels,
    setEnabledModels,
    capabilityOverrides,
    setCapabilityOverrides,
    setIsSavingModels,
    setIsLoadingModels,
    adminModelsCache,
    setAdminModelsCache,
    setAdminModelCapabilities,
    setShowEditProvider,
    setEditingProvider,
    showToast,
    fetchData,
  });

  const requestDeleteCustomModel = (name: string) => setConfirmDelete({ id: name, type: 'model' });
  const requestDeleteMcpServer = (serverName: string) => setConfirmDelete({ id: serverName, type: 'mcp' });

  const handleConfirmDelete = async () => {
    const item = confirmDelete();
    if (!item) return;
    if (item.type === 'model') {
      await llm.deleteCustomModel(item.id);
    } else {
      await mcp.deleteMcpServer(item.id);
    }
    setConfirmDelete(null);
  };

  return (
    <div class="p-8 h-full flex flex-col bg-gray-50 overflow-hidden">
      <div class="flex justify-between items-center mb-8">
        <h2 class="text-3xl font-bold text-gray-800">System Configuration</h2>
        <div class="text-sm text-gray-500 bg-white px-3 py-1 rounded-full border shadow-sm">
          Unified Platform Settings
        </div>
      </div>

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
        <Show when={activeTab() === 'general'}>
          <GeneralSettingsTab
            prefs={prefs}
            setPrefs={setPrefs}
            agents={agents}
            savePrefs={general.savePrefs}
            featureFlags={featureFlags}
            setFeatureFlags={setFeatureFlags}
            saveFeatureFlags={general.saveFeatureFlags}
            docAccess={docAccess}
            docAllowText={docAllowText}
            setDocAllowText={setDocAllowText}
            docDenyText={docDenyText}
            setDocDenyText={setDocDenyText}
            isSavingDocAccess={isSavingDocAccess}
            saveDocAccess={general.saveDocAccess}
          />
        </Show>

        <Show when={activeTab() === 'mcp'}>
          <McpSettingsTab
            mcpStatus={mcpStatus}
            mcpTools={mcpTools}
            mcpTemplates={mcpTemplates}
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
            showSmartPaste={showSmartPaste}
            setShowSmartPaste={setShowSmartPaste}
            mcpConfig={mcpConfig}
            setMcpConfig={setMcpConfig}
            reloadMcp={mcp.reloadMcp}
            toggleMcpEnabled={mcp.toggleMcpEnabled}
            deleteMcpServer={requestDeleteMcpServer}
            confirmManual={mcp.confirmManual}
            saveMcp={mcp.saveMcp}
            validateMcpTemplate={mcp.validateMcpTemplate}
            installMcpTemplate={mcp.installMcpTemplate}
            parseMcpSmartPaste={mcp.parseMcpSmartPaste}
            saveMcpSmartPaste={mcp.saveMcpSmartPaste}
          />
        </Show>

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
            refreshProviders={llm.refreshProviders}
            saveLlmConfig={llm.saveLlmConfig}
            testProvider={llm.testProvider}
            openProviderEditor={llm.openProviderEditor}
            saveProviderEditor={llm.saveProviderEditor}
            openModelManager={llm.openModelManager}
            saveManagedModels={llm.saveManagedModels}
            deleteCustomModel={requestDeleteCustomModel}
            testCustomModel={llm.testCustomModel}
          />
        </Show>
      </div>

      <Show when={toast()}>
        <div class="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300" role="status" aria-live="polite">
          <div
            class={`flex items-center gap-3 px-6 py-4 rounded-2xl shadow-2xl border transition-all ${
              toast()?.type === 'success'
                ? 'bg-emerald-50 border-emerald-100 text-emerald-800'
                : 'bg-red-50 border-red-100 text-red-800'
            }`}
          >
            <Show
              when={toast()?.type === 'success'}
              fallback={
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
              }
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </Show>
            <p class="font-medium">{toast()?.message}</p>
            <Show when={toast()?.action}>
              <button
                onClick={() => {
                  toast()?.action?.();
                  setToast(null);
                }}
                class="ml-2 px-3 py-1 bg-white/50 hover:bg-white rounded-lg text-sm font-bold transition-colors"
              >
                {toast()?.actionLabel}
              </button>
            </Show>
            <button class="ml-auto text-gray-400 hover:text-gray-600" onClick={() => setToast(null)}>
              ✕
            </button>
          </div>
        </div>
      </Show>

      <ConfirmModal
        show={!!confirmDelete()}
        title={confirmDelete()?.type === 'model' ? 'Delete Custom Model' : 'Delete MCP Server'}
        message={
          confirmDelete()?.type === 'model'
            ? `Are you sure you want to delete the custom model "${confirmDelete()?.id}"?`
            : `Are you sure you want to delete the MCP server "${confirmDelete()?.id}"? This action cannot be undone.`
        }
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </div>
  );
}
