import { For, Show, type Accessor, type Setter } from 'solid-js';
import type { CustomModel, NewCustomModelDraft } from '../../types';

type LlmCustomModelsSectionProps = {
  customModels: Accessor<CustomModel[]>;
  deleteCustomModel: (name: string) => void;
  testCustomModel: (model: CustomModel) => void;
  openCustomModelManager: (model: CustomModel) => void;
  setNewCM: Setter<NewCustomModelDraft>;
  setNewCMStatus: Setter<string>;
  setShowAddCustom: Setter<boolean>;
};

export function LlmCustomModelsSection(props: LlmCustomModelsSectionProps) {
  const openEditor = (model: CustomModel) => {
    props.setNewCM({
      name: model.name,
      provider: model.provider || 'openai',
      model: model.model || '',
      base_url: model.base_url || '',
      api_key: '',
      capabilities: model.capabilities || [],
    });
    props.setNewCMStatus('');
    props.setShowAddCustom(true);
  };

  return (
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <h4 class="text-lg font-bold text-slate-900">Custom Models</h4>
          <p class="mt-1 text-sm text-slate-500">
            Overlay models, local endpoints, and one-off gateways live here for quick testing and cleanup.
          </p>
        </div>
        <div class="rounded-xl bg-slate-50 px-3 py-2 text-right">
          <div class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Saved</div>
          <div class="mt-1 text-xl font-semibold text-slate-900">{props.customModels().length}</div>
        </div>
      </div>

      <div class="space-y-3">
        <div class="grid gap-3">
          <For each={props.customModels()}>
            {(model) => (
              <div
                data-testid={`llm-custom-model-${model.name}`}
                class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md"
              >
                <div class="flex flex-col gap-4">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div class="space-y-2 min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <div class="text-lg font-semibold text-slate-900 break-all">{model.name}</div>
                        <span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">
                          Ready
                        </span>
                      </div>
                      <div class="text-sm text-slate-500">
                        Provider: <span class="font-medium uppercase tracking-[0.12em] text-slate-700">{model.provider || 'OpenAI'}</span>
                      </div>
                    </div>

                    <div class="grid grid-cols-2 gap-2 sm:min-w-[180px]">
                      <div class="rounded-xl bg-slate-50 px-3 py-2">
                        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Capabilities</div>
                        <div class="mt-1 text-lg font-semibold text-slate-900">
                          {model.capabilities?.length || 0}
                        </div>
                      </div>
                      <div class="rounded-xl bg-slate-50 px-3 py-2">
                        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Target Model</div>
                        <div class="mt-1 text-lg font-semibold text-slate-900">
                          {model.model ? 'Set' : 'Default'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-[1.2fr_0.8fr]">
                    <div>
                      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Endpoint</div>
                      <div class="mt-2 text-sm leading-6 text-slate-600 break-all">
                        {model.base_url || 'No base URL configured'}
                      </div>
                    </div>
                    <div>
                      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Model Access</div>
                      <div class="mt-2 text-sm leading-6 text-slate-600 break-all">
                        {model.model || 'No model id configured. The endpoint default will be used.'}
                      </div>
                    </div>
                  </div>

                  <Show when={model.capabilities && model.capabilities.length > 0}>
                    <div class="flex flex-wrap gap-1.5">
                      <For each={model.capabilities}>
                        {(cap) => (
                          <span class="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                            {cap === 'function_calling' ? 'Tools' : cap.charAt(0).toUpperCase() + cap.slice(1)}
                          </span>
                        )}
                      </For>
                    </div>
                  </Show>

                  <div class="flex flex-wrap gap-2">
                    <button
                      data-testid={`llm-custom-model-test-${model.name}`}
                      onClick={() => props.testCustomModel(model)}
                      class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                    >
                      Test Connection
                    </button>
                    <button
                      onClick={() => openEditor(model)}
                      class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                    >
                      Edit Settings
                    </button>
                    <button
                      data-testid={`llm-custom-model-manage-${model.name}`}
                      onClick={() => props.openCustomModelManager(model)}
                      class="inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
                      title="Manage the custom endpoint, target model, and capabilities"
                    >
                      Manage Models
                    </button>
                    <button
                      data-testid={`llm-custom-model-delete-${model.name}`}
                      onClick={() => props.deleteCustomModel(model.name)}
                      class="inline-flex items-center justify-center rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            )}
          </For>
          <Show when={props.customModels().length === 0}>
            <div class="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
              No custom models yet. Add one from the provider header above and it will appear here.
            </div>
          </Show>
        </div>
      </div>
    </section>
  );
}
