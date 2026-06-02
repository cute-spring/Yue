import { For, Show, type Accessor, type Setter } from 'solid-js';
import type { LLMProvider, LlmForm, NewCustomModelDraft } from '../../types';

type LlmProviderConfigsSectionProps = {
  providers: Accessor<LLMProvider[]>;
  llmForm: Accessor<LlmForm>;
  isRefreshingProviders: Accessor<boolean>;
  setNewCM: Setter<NewCustomModelDraft>;
  setNewCMStatus: Setter<string>;
  setShowAddCustom: Setter<boolean>;
  refreshProviders: () => Promise<void>;
  testProvider: (name: string) => void;
  openProviderEditor: (name: string) => void;
  openModelManager: (provider: LLMProvider) => void;
};

export function LlmProviderConfigsSection(props: LlmProviderConfigsSectionProps) {
  return (
    <>
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
    </>
  );
}
