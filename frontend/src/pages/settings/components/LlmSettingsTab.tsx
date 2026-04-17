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

  return (
    <div class="space-y-8 max-w-4xl">
      <div class="border-b pb-2">
        <h3 class="text-xl font-semibold">LLM Provider Configurations</h3>
        <p class="text-sm text-gray-500">Configure API keys and default models</p>
        <div class="mt-2">
          <button
              data-testid="llm-refresh-providers-button"
              onClick={props.refreshProviders}
              disabled={props.isRefreshingProviders()}
              class={`text-xs px-3 py-1.5 rounded-md border flex items-center gap-2 transition-colors ${
                props.isRefreshingProviders()
                  ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
                  : 'bg-white hover:bg-gray-50 text-gray-700'
              }`}
            >
              <Show when={props.isRefreshingProviders()}>
                <div class="w-3 h-3 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></div>
              </Show>
              {props.isRefreshingProviders() ? 'Refreshing...' : 'Refresh Available Models'}
            </button>
            <button
              data-testid="llm-add-custom-button"
              onClick={() => {
                props.setNewCM({ name: '', provider: 'openai', model: '', base_url: '', api_key: '' });
                props.setNewCMStatus('');
                props.setShowAddCustom(true);
              }}
              class="ml-2 text-xs px-3 py-1.5 rounded-lg bg-blue-700 text-white hover:bg-blue-800 shadow-sm inline-flex items-center gap-1"
            >
              <span>+</span>
              <span>Add Custom (Overlay)</span>
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
              <For each={props.providers()}>
                {(p) => (
                  <tr class="border-t">
                    <td class="px-4 py-2 font-medium text-gray-800 uppercase">{p.name}</td>
                    <td class="px-4 py-2 text-gray-700">
                      {props.llmForm()[`${p.name}_model`] || p.current_model || '-'}
                    </td>
                    <td class="px-4 py-2">
                      <span
                        class={`text-xs px-2 py-1 rounded-full font-bold uppercase ${
                          p.configured ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {p.configured ? 'Connected' : 'Missing Config'}
                      </span>
                    </td>
                    <td class="px-4 py-2 text-gray-700">
                      {p.available_models && p.available_models.length > 0 ? `${p.available_models.length}` : '—'}
                    </td>
                    <td class="px-4 py-2 text-gray-700">{p.requirements.join(', ')}</td>
                    <td class="px-4 py-2">
                      <div class="flex items-center gap-2">
                        <button
                          onClick={() => props.testProvider(p.name)}
                          class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                        >
                          Test
                        </button>
                        <button
                          onClick={() => props.openProviderEditor(p.name)}
                          class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => props.openModelManager(p)}
                          class="text-xs px-3 py-1.5 rounded-md border bg-white hover:bg-gray-50 text-gray-700"
                          disabled={!p.models || p.models.length === 0}
                          title={(!p.models || p.models.length === 0) ? 'No models discovered' : 'Manage available models'}
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

        <div class="border-t pt-6">
          <h4 class="text-lg font-bold mb-3">Custom Models</h4>
          <div class="space-y-3">
            <div class="space-y-2">
              <For each={props.customModels()}>
                {(m) => (
                  <div class="p-3 border rounded-lg flex items-center justify-between">
                    <div>
                      <div class="font-bold">{m.name}</div>
                      <div class="text-xs text-gray-500">{m.base_url || ''}</div>
                      <div class="text-xs text-gray-500">{m.model || ''}</div>
                      <Show when={m.capabilities && m.capabilities.length > 0}>
                        <div class="flex gap-1 mt-1">
                          <For each={m.capabilities}>
                            {(cap) => (
                              <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                                {cap === 'function_calling' ? 'Tools' : cap.charAt(0).toUpperCase() + cap.slice(1)}
                              </span>
                            )}
                          </For>
                        </div>
                      </Show>
                    </div>
                    <div class="flex gap-2">
                      <button onClick={() => props.testCustomModel(m)} class="text-xs px-2 py-1 rounded border">
                        Test
                      </button>
                      <button
                        onClick={() => props.deleteCustomModel(m.name)}
                        class="text-xs px-2 py-1 rounded border text-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                )}
              </For>
              <Show when={props.customModels().length === 0}>
                <div class="text-sm text-gray-500">No custom models. Add one above.</div>
              </Show>
            </div>
          </div>
        </div>

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

      <div class="border-t pt-6">
        <h4 class="text-lg font-bold mb-3">Model Preference Tiers</h4>
        <p class="text-sm text-gray-500 mb-4">Configure the provider/model mapped to `light`, `balanced`, and `heavy` agent preferences.</p>
        <div class="space-y-3">
          <For each={tierEntries()}>
            {({ tier, label }) => {
              const modelTiers = () => normalizeModelTierConfig(props.llmForm().model_tiers);
              const availableModels = () => props.providers().find(p => p.name === modelTiers()[tier].provider)?.models || [];

              return (
                <div class="grid grid-cols-1 md:grid-cols-[140px_180px_1fr] gap-3 border rounded-xl bg-gray-50 p-4">
                  <div>
                    <div class="text-xs font-black uppercase tracking-[0.18em] text-gray-500">{label}</div>
                    <div class="text-[11px] text-gray-500 mt-1">Agent tier mapping</div>
                  </div>
                  <div>
                    <div class="text-xs font-bold text-gray-600 mb-1">Provider</div>
                    <select
                      class="w-full border rounded-lg p-2 bg-white"
                      value={modelTiers()[tier].provider}
                      onInput={(e) => updateModelTier(tier, 'provider', e.currentTarget.value)}
                    >
                      <For each={props.providers()}>
                        {(provider) => <option value={provider.name}>{provider.name}</option>}
                      </For>
                    </select>
                  </div>
                  <div>
                    <div class="text-xs font-bold text-gray-600 mb-1">Model</div>
                    <select
                      class="w-full border rounded-lg p-2 bg-white"
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
              );
            }}
          </For>
        </div>
      </div>

      <div class="border-t pt-6">
        <h4 class="text-lg font-bold mb-3 flex items-center gap-2">
          <span class="p-1 bg-emerald-100 text-emerald-600 rounded">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1z"
                  clip-rule="evenodd"
                />
              </svg>
            </span>
            Global Network & Timeout
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-xl border border-gray-100">
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">PROXY_URL</div>
              <input
                class="w-full border rounded-lg p-2 bg-white"
                placeholder="http://127.0.0.1:7890"
                value={props.llmForm().proxy_url || ''}
                onInput={(e) => props.setLlmForm({ ...props.llmForm(), proxy_url: e.currentTarget.value })}
              />
              <div class="text-[10px] text-gray-400 mt-1">HTTP/HTTPS proxy for LLM requests</div>
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">NO_PROXY</div>
              <input
                class="w-full border rounded-lg p-2 bg-white"
                placeholder="e.g. *.openai.azure.com"
                value={props.llmForm().no_proxy || ''}
                onInput={(e) => props.setLlmForm({ ...props.llmForm(), no_proxy: e.currentTarget.value })}
              />
              <div class="text-[10px] text-gray-400 mt-1">Bypass list (loopback included by default)</div>
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">SSL_CERT_FILE</div>
              <input
                class="w-full border rounded-lg p-2 bg-white"
                placeholder="/path/to/cert.pem"
                value={props.llmForm().ssl_cert_file || ''}
                onInput={(e) => props.setLlmForm({ ...props.llmForm(), ssl_cert_file: e.currentTarget.value })}
              />
              <div class="text-[10px] text-gray-400 mt-1">Custom CA certificate bundle path</div>
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">REQUEST_TIMEOUT (s)</div>
              <input
                type="number"
                class="w-full border rounded-lg p-2 bg-white"
                placeholder="60"
                value={props.llmForm().llm_request_timeout || ''}
                onInput={(e) => props.setLlmForm({ ...props.llmForm(), llm_request_timeout: e.currentTarget.value })}
              />
              <div class="text-[10px] text-gray-400 mt-1">Timeout in seconds (default: 60)</div>
            </div>
          </div>
        </div>

        <div class="border-t pt-6">
          <h4 class="text-lg font-bold mb-3 flex items-center gap-2">
            <span class="p-1 bg-blue-100 text-blue-600 rounded">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 2a1 1 0 00-1 1v1.07A7.002 7.002 0 003 10a7 7 0 0014 0 7.002 7.002 0 00-6-6.93V3a1 1 0 00-1-1z" />
              </svg>
            </span>
            Session Meta Behavior
          </h4>
          <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <label class="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                checked={Boolean(props.llmForm().meta_use_runtime_model_for_title)}
                onChange={(e) =>
                  props.setLlmForm({ ...props.llmForm(), meta_use_runtime_model_for_title: e.currentTarget.checked })
                }
              />
              <div>
                <div class="text-sm font-semibold text-gray-800">meta_use_runtime_model_for_title</div>
                <div class="text-xs text-gray-600 mt-1">
                  开启后，标题生成会优先使用当前会话运行时所选模型；关闭后，标题与摘要都优先走 Meta 固定模型配置。
                </div>
              </div>
            </label>
          </div>
        </div>

      <div class="pt-4 sticky bottom-0 bg-white pb-4">
        <button
          onClick={props.saveLlmConfig}
          class="bg-emerald-600 text-white px-10 py-3 rounded-xl font-bold hover:bg-emerald-700 transition-all shadow-lg hover:shadow-emerald-200"
        >
          Save All LLM Settings
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
    </div>
  );
}
