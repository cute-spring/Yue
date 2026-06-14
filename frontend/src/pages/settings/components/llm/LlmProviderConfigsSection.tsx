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
  const configuredProviders = () => props.providers().filter((provider) => provider.configured).length;
  const discoveredModels = () =>
    props.providers().reduce((count, provider) => count + (provider.available_models?.length || 0), 0);

  return (
    <section class="space-y-5">
      <div class="overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900 text-white shadow-sm">
        <div class="flex flex-col gap-6 px-6 py-6 lg:flex-row lg:items-end lg:justify-between">
          <div class="space-y-4">
            <div class="inline-flex items-center rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-100">
              Model Control Center
            </div>
            <div class="space-y-2">
              <h3 class="text-2xl font-semibold tracking-tight">LLM Provider Configurations</h3>
              <p class="max-w-2xl text-sm leading-6 text-slate-200">
                Configure API keys, default models, and custom overlays from one place. Provider health, discovery
                status, and model actions stay visible without making the page feel like a spreadsheet.
              </p>
            </div>
            <div class="grid gap-3 sm:grid-cols-3">
              <div class="rounded-xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">Providers</div>
                <div class="mt-2 text-2xl font-semibold text-white">{props.providers().length}</div>
              </div>
              <div class="rounded-xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">Connected</div>
                <div class="mt-2 text-2xl font-semibold text-white">{configuredProviders()}</div>
              </div>
              <div class="rounded-xl border border-white/10 bg-white/10 px-4 py-3 backdrop-blur-sm">
                <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-300">Models Seen</div>
                <div class="mt-2 text-2xl font-semibold text-white">{discoveredModels()}</div>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button
              data-testid="llm-refresh-providers-button"
              onClick={props.refreshProviders}
              disabled={props.isRefreshingProviders()}
              class={`inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-colors ${
                props.isRefreshingProviders()
                  ? 'border-white/10 bg-white/10 text-slate-300 cursor-not-allowed'
                  : 'border-white/15 bg-white text-slate-900 hover:bg-emerald-50'
              }`}
            >
              <Show when={props.isRefreshingProviders()}>
                <div class="h-3.5 w-3.5 rounded-full border-2 border-slate-300 border-t-slate-700 animate-spin"></div>
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
              class="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-sm transition-colors hover:bg-emerald-300"
            >
              <span class="text-base leading-none">+</span>
              <span>Add Custom Model</span>
            </button>
          </div>
        </div>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <For each={props.providers()}>
          {(p) => (
            <article class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
              <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div class="space-y-2">
                    <div class="flex items-center gap-2">
                      <div class="text-lg font-semibold capitalize text-slate-900">{p.name.replace(/_/g, ' ')}</div>
                      <span
                        class={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${
                          p.configured
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {p.configured ? 'Connected' : 'Needs Setup'}
                      </span>
                    </div>
                    <div class="text-sm text-slate-500">
                      Active model: <span class="font-medium text-slate-700">{props.llmForm()[`${p.name}_model`] || p.current_model || 'Not set'}</span>
                    </div>
                  </div>

                  <div class="grid grid-cols-2 gap-2 sm:min-w-[180px]">
                    <div class="rounded-xl bg-slate-50 px-3 py-2">
                      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Visible</div>
                      <div class="mt-1 text-lg font-semibold text-slate-900">
                        {p.available_models?.length || 0}
                      </div>
                    </div>
                    <div class="rounded-xl bg-slate-50 px-3 py-2">
                      <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Catalog</div>
                      <div class="mt-1 text-lg font-semibold text-slate-900">{p.models?.length || 0}</div>
                    </div>
                  </div>
                </div>

                <div class="grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-[1.2fr_0.8fr]">
                  <div>
                    <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Requirements</div>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <For each={p.requirements}>
                        {(requirement) => (
                          <span class="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
                            {requirement}
                          </span>
                        )}
                      </For>
                    </div>
                  </div>
                  <div>
                    <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Model Access</div>
                    <div class="mt-2 text-sm leading-6 text-slate-600">
                      {p.available_models && p.available_models.length > 0
                        ? `${p.available_models.length} models currently enabled for selection.`
                        : 'No discovered models are available yet.'}
                    </div>
                  </div>
                </div>

                <div class="flex flex-wrap gap-2">
                  <button
                    onClick={() => props.testProvider(p.name)}
                    class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    Test Connection
                  </button>
                  <button
                    onClick={() => props.openProviderEditor(p.name)}
                    class="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  >
                    Edit Settings
                  </button>
                  <button
                    onClick={() => props.openModelManager(p)}
                    class={`inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
                      !p.models || p.models.length === 0
                        ? 'cursor-not-allowed bg-slate-100 text-slate-400'
                        : 'bg-slate-900 text-white hover:bg-slate-800'
                    }`}
                    disabled={!p.models || p.models.length === 0}
                    title={(!p.models || p.models.length === 0) ? 'No models discovered' : 'Manage available models'}
                  >
                    Manage Models
                  </button>
                </div>
              </div>
            </article>
          )}
        </For>
      </div>
    </section>
  );
}
