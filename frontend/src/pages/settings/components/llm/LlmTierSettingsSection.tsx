import { For, Show, type Accessor, type Setter } from 'solid-js';
import type { LLMProvider, LlmForm, ModelTier } from '../../types';
import { normalizeModelTierConfig } from '../../types';

type LlmTierSettingsSectionProps = {
  providers: Accessor<LLMProvider[]>;
  llmForm: Accessor<LlmForm>;
  setLlmForm: Setter<LlmForm>;
};

export function LlmTierSettingsSection(props: LlmTierSettingsSectionProps) {
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
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div class="mb-4">
        <h4 class="text-lg font-bold text-slate-900">Model Preference Tiers</h4>
        <p class="mt-1 text-sm text-slate-500">
          Configure the provider and model used for `light`, `balanced`, and `heavy` agent preferences.
        </p>
      </div>
      <div class="space-y-3">
        <For each={tierEntries()}>
          {({ tier, label }) => {
            const modelTiers = () => normalizeModelTierConfig(props.llmForm().model_tiers);
            const availableModels = () => props.providers().find(p => p.name === modelTiers()[tier].provider)?.models || [];

            return (
              <div class="grid grid-cols-1 gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 xl:grid-cols-[160px_220px_minmax(0,1fr)]">
                <div>
                  <div class="text-xs font-black uppercase tracking-[0.18em] text-slate-500">{label}</div>
                  <div class="mt-1 text-[11px] text-slate-500">Agent tier mapping</div>
                </div>
                <div>
                  <div class="mb-1 text-xs font-bold text-slate-600">Provider</div>
                  <select
                    class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
                    value={modelTiers()[tier].provider}
                    onInput={(e) => updateModelTier(tier, 'provider', e.currentTarget.value)}
                  >
                    <For each={props.providers()}>
                      {(provider) => <option value={provider.name}>{provider.name}</option>}
                    </For>
                  </select>
                </div>
                <div>
                  <div class="mb-1 text-xs font-bold text-slate-600">Model</div>
                  <select
                    class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
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
    </section>
  );
}
