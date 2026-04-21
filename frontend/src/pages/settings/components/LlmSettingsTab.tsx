import type { Accessor, Setter } from 'solid-js';
import { For, Show } from 'solid-js';
import type { CustomModel, LLMProvider, LlmForm, ModelTier, NewCustomModelDraft, Preferences } from '../types';
import { normalizeModelTierConfig } from '../types';
import { LlmCustomModelModal } from './modals/LlmCustomModelModal';
import { LlmModelManagerModal } from './modals/LlmModelManagerModal';
import { LlmProviderEditModal } from './modals/LlmProviderEditModal';

type LlmSettingsTabProps = {
  providers: Accessor<LLMProvider[]>;
  llmForm: Accessor<LlmForm>;
  setLlmForm: Setter<LlmForm>;
  customModels: Accessor<CustomModel[]>;
  setCustomModels: Setter<CustomModel[]>;
  prefs: Accessor<Preferences>;
  isRefreshingProviders: Accessor<boolean>;
  setIsRefreshingProviders: Setter<boolean>;
  showAddCustom: Accessor<boolean>;
  setShowAddCustom: Setter<boolean>;
  newCM: Accessor<NewCustomModelDraft>;
  setNewCM: Setter<NewCustomModelDraft>;
  newCMStatus: Accessor<string>;
  setNewCMStatus: Setter<string>;
  showEditProvider: Accessor<boolean>;
  setShowEditProvider: Setter<boolean>;
  editingProvider: Accessor<string>;
  showModelManager: Accessor<boolean>;
  setShowModelManager: Setter<boolean>;
  managingProvider: Accessor<string | null>;
  managedModels: Accessor<string[]>;
  enabledModels: Accessor<Set<string>>;
  setEnabledModels: Setter<Set<string>>;
  capabilityOverrides: Accessor<Record<string, string[]>>;
  setCapabilityOverrides: Setter<Record<string, string[]>>;
  adminModelCapabilities: Accessor<Record<string, string[]>>;
  isLoadingModels: Accessor<boolean>;
  isSavingModels: Accessor<boolean>;
  refreshProviders: () => Promise<void>;
  saveLlmConfig: () => void;
  testProvider: (name: string) => void;
  openProviderEditor: (name: string) => void;
  saveProviderEditor: () => void;
  openModelManager: (provider: LLMProvider) => void;
  saveManagedModels: () => void;
  deleteCustomModel: (name: string) => void;
  testCustomModel: (m: CustomModel) => void;
};

export function LlmSettingsTab(props: LlmSettingsTabProps) {
  const tierEntries = (): Array<{ tier: ModelTier; label: string }> => ([
    { tier: 'light', label: 'Light' },
    { tier: 'balanced', label: 'Balanced' },
    { tier: 'heavy', label: 'Heavy' },
  ]);

  const updateModelTier = (tier: ModelTier, key: 'provider' | 'model', value: string) => {
    const current = normalizeModelTierConfig(props.llmForm().model_tiers);
    props.setLlmForm({
      ...props.llmForm(),
      model_tiers: {
        ...current,
        [tier]: {
          ...current[tier],
          [key]: value,
        },
      },
    });
  };

  const LlmSection = (sectionProps: { title: string; description?: string; children: any; icon?: string; action?: any }) => (
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <Show when={sectionProps.icon}>
            <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={sectionProps.icon} />
              </svg>
            </div>
          </Show>
          <div>
            <h3 class="text-lg font-bold text-gray-800">{sectionProps.title}</h3>
            <Show when={sectionProps.description}>
              <p class="text-xs text-gray-500 mt-0.5">{sectionProps.description}</p>
            </Show>
          </div>
        </div>
        <Show when={sectionProps.action}>{sectionProps.action}</Show>
      </div>
      <div class="">{sectionProps.children}</div>
    </div>
  );

  return (
    <div class="space-y-12 max-w-5xl pb-20">
      <LlmSection 
        title="LLM Providers" 
        description="Configure API keys and model discovery for each supported platform."
        icon="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        action={
          <div class="flex items-center gap-2">
            <button
              data-testid="llm-refresh-providers-button"
              onClick={props.refreshProviders}
              disabled={props.isRefreshingProviders()}
              class={`text-xs px-3 py-1.5 rounded-xl border flex items-center gap-2 transition-all font-bold ${
                props.isRefreshingProviders()
                  ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                  : 'bg-white hover:bg-gray-50 text-gray-700 shadow-sm'
              }`}
            >
              <Show when={props.isRefreshingProviders()} fallback={<span>↻</span>}>
                <div class="w-3 h-3 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
              </Show>
              {props.isRefreshingProviders() ? 'Refreshing...' : 'Refresh Models'}
            </button>
            <button
              data-testid="llm-add-custom-button"
              onClick={() => {
                props.setNewCM({ name: '', provider: 'openai', model: '', base_url: '', api_key: '' });
                props.setNewCMStatus('');
                props.setShowAddCustom(true);
              }}
              class="text-xs px-3 py-1.5 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm font-bold flex items-center gap-1 transition-all active:scale-95"
            >
              <span>+ Add Custom</span>
            </button>
          </div>
        }
      >
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <For each={props.providers()}>
            {(p) => (
              <div class="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-all group flex flex-col justify-between">
                <div>
                  <div class="flex items-center justify-between mb-3">
                    <span class="text-xs font-black uppercase tracking-widest text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md">{p.name}</span>
                    <Show when={p.configured} fallback={<span class="text-[10px] text-gray-400 font-bold uppercase tracking-wider bg-gray-100 px-2 py-1 rounded-md">Missing Config</span>}>
                      <span class="text-[10px] text-emerald-700 font-bold uppercase tracking-wider bg-emerald-100 px-2 py-1 rounded-md flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        Connected
                      </span>
                    </Show>
                  </div>
                  <div class="space-y-2 mb-4">
                    <div class="flex items-center justify-between">
                      <span class="text-xs text-gray-500 font-medium">Primary Model</span>
                      <span class="text-xs font-bold text-gray-800 truncate max-w-[120px]" title={props.llmForm()[`${p.name}_model`] || p.current_model}>
                        {props.llmForm()[`${p.name}_model`] || p.current_model || '—'}
                      </span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-xs text-gray-500 font-medium">Discovered</span>
                      <span class="text-xs font-bold text-gray-800">{p.available_models?.length || 0} models</span>
                    </div>
                    <Show when={p.requirements && p.requirements.length > 0}>
                      <div class="flex items-center justify-between">
                        <span class="text-xs text-gray-500 font-medium">Auth</span>
                        <span class="text-[10px] font-mono text-gray-400 truncate max-w-[120px]" title={p.requirements.join(', ')}>{p.requirements.join(', ')}</span>
                      </div>
                    </Show>
                  </div>
                </div>
                <div class="flex items-center gap-2 pt-3 border-t border-gray-50 mt-auto">
                  <button
                    onClick={() => props.testProvider(p.name)}
                    class="flex-1 text-xs py-2 rounded-xl border border-gray-100 bg-gray-50 hover:bg-gray-100 text-gray-700 font-bold transition-all"
                  >
                    Test
                  </button>
                  <button
                    onClick={() => props.openProviderEditor(p.name)}
                    class="flex-1 text-xs py-2 rounded-xl border border-gray-100 bg-gray-50 hover:bg-gray-100 text-gray-700 font-bold transition-all"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => props.openModelManager(p)}
                    disabled={!p.models || p.models.length === 0}
                    class="p-2 rounded-xl border border-gray-100 bg-gray-50 hover:bg-gray-100 text-gray-700 font-bold transition-all disabled:opacity-30"
                    title="Manage available models"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M5 4a1 1 0 00-2 0v7.268a2 2 0 000 3.464V16a1 1 0 102 0v-1.268a2 2 0 000-3.464V4zM11 4a1 1 0 10-2 0v1.268a2 2 0 000 3.464V16a1 1 0 102 0V8.732a2 2 0 000-3.464V4zM16 3a1 1 0 011 1v7.268a2 2 0 010 3.464V16a1 1 0 11-2 0v-1.268a2 2 0 010-3.464V4a1 1 0 011-1z" />
                    </svg>
                  </button>
                </div>
              </div>
            )}
          </For>
        </div>
      </LlmSection>

      <Show when={props.customModels().length > 0}>
        <LlmSection 
          title="Custom Model Endpoints" 
          description="Directly integrate with OpenAI-compatible providers like Groq, Together, or local proxies."
          icon="M13 10V3L4 14h7v7l9-11h-7z"
        >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <For each={props.customModels()}>
              {(m) => (
                <div class="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-all group">
                  <div class="flex items-start justify-between mb-4">
                    <div class="space-y-1 overflow-hidden">
                      <h4 class="text-sm font-bold text-gray-800 truncate" title={m.name}>{m.name}</h4>
                      <p class="text-[10px] text-gray-400 font-mono truncate" title={m.base_url}>{m.base_url}</p>
                    </div>
                    <div class="flex gap-1">
                      <button onClick={() => props.testCustomModel(m)} class="p-1.5 rounded-lg border border-gray-100 bg-gray-50 text-gray-600 hover:bg-emerald-50 hover:text-emerald-600 transition-all" title="Test Connection">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M11.3 1.047a1 1 0 01.897.447l6 10A1 1 0 0117.31 13H13v7a1 1 0 01-1.88.464l-9-15a1 1 0 011.24-1.322L8 5.645V2a1 1 0 011-1h2.3z" clip-rule="evenodd" />
                        </svg>
                      </button>
                      <button onClick={() => props.deleteCustomModel(m.name)} class="p-1.5 rounded-lg border border-gray-100 bg-gray-50 text-gray-600 hover:bg-rose-50 hover:text-rose-600 transition-all" title="Delete Model">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div class="flex items-center justify-between mb-3">
                    <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest bg-gray-100 px-2 py-1 rounded-md">{m.model || 'Auto'}</span>
                  </div>
                  <Show when={m.capabilities && m.capabilities.length > 0}>
                    <div class="flex flex-wrap gap-1">
                      <For each={m.capabilities}>
                        {(cap) => (
                          <span class="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-100">
                            {cap === 'function_calling' ? 'Tools' : cap}
                          </span>
                        )}
                      </For>
                    </div>
                  </Show>
                </div>
              )}
            </For>
          </div>
        </LlmSection>
      </Show>

      <LlmSection 
        title="Model Preference Tiers" 
        description="Map your agents' performance tiers to specific provider/model combinations."
        icon="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      >
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <For each={tierEntries()}>
            {({ tier, label }) => {
              const modelTiers = () => normalizeModelTierConfig(props.llmForm().model_tiers);
              const availableModels = () => props.providers().find(p => p.name === modelTiers()[tier].provider)?.models || [];

              return (
                <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-4">
                  <div class="flex items-center gap-2 mb-2">
                    <div class={`w-2 h-2 rounded-full ${tier === 'light' ? 'bg-sky-400' : tier === 'balanced' ? 'bg-emerald-400' : 'bg-purple-500'}`}></div>
                    <h4 class="text-sm font-black uppercase tracking-widest text-gray-500">{label}</h4>
                  </div>
                  
                  <div class="space-y-3">
                    <div>
                      <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">Provider</label>
                      <select
                        class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm font-medium focus:ring-2 focus:ring-emerald-500 outline-none"
                        value={modelTiers()[tier].provider}
                        onInput={(e) => updateModelTier(tier, 'provider', e.currentTarget.value)}
                      >
                        <For each={props.providers()}>
                          {(provider) => <option value={provider.name}>{provider.name}</option>}
                        </For>
                      </select>
                    </div>
                    <div>
                      <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">Model</label>
                      <select
                        class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm font-medium focus:ring-2 focus:ring-emerald-500 outline-none"
                        value={modelTiers()[tier].model}
                        onInput={(e) => updateModelTier(tier, 'model', e.currentTarget.value)}
                      >
                        <Show when={availableModels().length === 0}>
                          <option value="" disabled>No models discovered</option>
                        </Show>
                        <For each={availableModels()}>
                          {(model) => <option value={model}>{model}</option>}
                        </For>
                        <Show when={modelTiers()[tier].model && !availableModels().includes(modelTiers()[tier].model)}>
                          <option value={modelTiers()[tier].model}>{modelTiers()[tier].model} (Current)</option>
                        </Show>
                      </select>
                    </div>
                  </div>
                </div>
              );
            }}
          </For>
        </div>
      </LlmSection>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <LlmSection 
          title="Network & Timeouts" 
          description="Global connectivity settings for all LLM providers."
          icon="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
        >
          <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm space-y-4">
            <div class="grid grid-cols-1 gap-4">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">Proxy URL</label>
                  <input
                    class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder="http://127.0.0.1:7890"
                    value={props.llmForm().proxy_url || ''}
                    onInput={(e) => props.setLlmForm({ ...props.llmForm(), proxy_url: e.currentTarget.value })}
                  />
                </div>
                <div>
                  <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">No Proxy</label>
                  <input
                    class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                    placeholder="localhost, *.azure.com"
                    value={props.llmForm().no_proxy || ''}
                    onInput={(e) => props.setLlmForm({ ...props.llmForm(), no_proxy: e.currentTarget.value })}
                  />
                </div>
              </div>
              <div>
                <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">SSL Cert File</label>
                <input
                  class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="/path/to/cert.pem"
                  value={props.llmForm().ssl_cert_file || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), ssl_cert_file: e.currentTarget.value })}
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5">Request Timeout (s)</label>
                <input
                  type="number"
                  class="w-full border border-gray-200 rounded-xl p-2 bg-gray-50 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
                  placeholder="60"
                  value={props.llmForm().llm_request_timeout || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), llm_request_timeout: e.currentTarget.value })}
                />
              </div>
            </div>
          </div>
        </LlmSection>

        <LlmSection 
          title="Session Intelligence" 
          description="Configure how Yue handles metadata and title generation."
          icon="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        >
          <div class="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm h-full">
            <label class="flex items-start gap-4 p-4 bg-blue-50/50 rounded-2xl border border-blue-100 cursor-pointer hover:bg-blue-50 transition-all group">
              <div class="mt-1">
                <input
                  type="checkbox"
                  class="h-5 w-5 rounded border-blue-200 text-blue-600 focus:ring-blue-500 accent-blue-600"
                  checked={Boolean(props.llmForm().meta_use_runtime_model_for_title)}
                  onChange={(e) =>
                    props.setLlmForm({ ...props.llmForm(), meta_use_runtime_model_for_title: e.currentTarget.checked })
                  }
                />
              </div>
              <div class="space-y-1">
                <div class="text-sm font-bold text-blue-900">Dynamic Title Generation</div>
                <div class="text-xs text-blue-700/70 leading-relaxed">
                  When enabled, Yue will use the model currently selected in the chat for title generation. When disabled, it uses the fixed Meta model configuration.
                </div>
              </div>
            </label>
          </div>
        </LlmSection>
      </div>

      <div class="fixed bottom-8 right-8 z-40">
        <button
          onClick={props.saveLlmConfig}
          class="bg-emerald-600 text-white px-8 py-3 rounded-2xl font-bold hover:bg-emerald-700 transition-all shadow-xl hover:shadow-emerald-200 active:scale-95 flex items-center gap-2 border border-emerald-500/20"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
          Save Model Settings
        </button>
      </div>

      <Show when={props.showEditProvider()}>
        <LlmProviderEditModal
          editingProvider={props.editingProvider}
          llmForm={props.llmForm}
          setLlmForm={props.setLlmForm}
          onClose={() => props.setShowEditProvider(false)}
          onSave={props.saveProviderEditor}
        />
      </Show>

      <Show when={props.showAddCustom()}>
        <LlmCustomModelModal
          newCM={props.newCM}
          setNewCM={props.setNewCM}
          newCMStatus={props.newCMStatus}
          setNewCMStatus={props.setNewCMStatus}
          setShowAddCustom={props.setShowAddCustom}
          setCustomModels={props.setCustomModels}
        />
      </Show>

      <Show when={props.showModelManager()}>
        <LlmModelManagerModal
          managingProvider={props.managingProvider}
          managedModels={props.managedModels}
          enabledModels={props.enabledModels}
          setEnabledModels={props.setEnabledModels}
          capabilityOverrides={props.capabilityOverrides}
          setCapabilityOverrides={props.setCapabilityOverrides}
          adminModelCapabilities={props.adminModelCapabilities}
          isLoadingModels={props.isLoadingModels}
          isSavingModels={props.isSavingModels}
          onClose={() => props.setShowModelManager(false)}
          onSelectAll={() => props.setEnabledModels(new Set(props.managedModels()))}
          onDeselectAll={() => props.setEnabledModels(new Set())}
          onSave={props.saveManagedModels}
        />
      </Show>
    </div>
  );
}
