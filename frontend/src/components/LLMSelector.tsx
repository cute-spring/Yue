import { For, Show } from 'solid-js';
import { Provider } from '../types';

interface LLMSelectorProps {
  show: boolean;
  setShow: (show: boolean) => void;
  selectedModel: string;
  onSelectModel: (provider: string, model: string) => void;
  selectedProvider: string;
  providers: Provider[];
  showAllModels: boolean;
  setShowAllModels: (show: boolean) => void;
  isRefreshingModels: boolean;
  onRefreshModels: () => Promise<void>;
}

export const getModelCapabilityBadges = (provider: Provider, model: string): string[] => {
  const capabilities = provider.model_capabilities?.[model] || [];
  const badges: string[] = [];
  if (capabilities.includes('vision')) {
    badges.push('Vision');
  }
  return badges;
};

export default function LLMSelector(props: LLMSelectorProps) {
  return (
    <div class="relative">
      <button 
        type="button"
        onClick={(e) => { 
          e.stopPropagation();
          props.setShow(!props.show);
        }}
        class="flex items-center gap-2.5 px-4 py-2.5 bg-background/90 border border-border/80 hover:border-primary/25 hover:bg-primary/5 rounded-2xl transition-all duration-200 active:scale-[0.98] shadow-sm hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
      >
        <div class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
        <span class="text-[12px] font-semibold text-text-primary">{props.selectedModel || "Select Model"}</span>
        <svg xmlns="http://www.w3.org/2000/svg" class={`h-3.5 w-3.5 text-text-secondary transition-transform duration-300 ${props.show ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <Show when={props.show}>
        <div class="absolute bottom-full left-0 mb-3 w-72 bg-surface/98 backdrop-blur-xl border border-border/80 rounded-[1.4rem] shadow-[0_18px_40px_rgba(20,35,30,0.14)] z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div class="p-4 border-b border-border/70 flex items-center justify-between bg-background/65">
            <span class="text-[11px] font-medium text-text-secondary">{props.showAllModels ? 'All Models' : 'Enabled Models'}</span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  props.setShowAllModels(!props.showAllModels);
                }}
                class="text-[11px] px-2.5 py-1 rounded-lg border border-border/80 bg-surface hover:bg-background text-text-secondary font-medium transition-colors"
              >
                {props.showAllModels ? 'Enabled' : 'All'}
              </button>
              <Show when={props.isRefreshingModels}>
                <div class="w-4 h-4 border-2 border-border border-t-primary rounded-full animate-spin"></div>
              </Show>
            </div>
          </div>
          <div class="p-2.5 max-h-80 overflow-y-auto space-y-2 scrollbar-thin scrollbar-thumb-border/60">
            <For each={props.providers.filter(p => {
              const list = props.showAllModels ? (p.models || []) : (p.available_models || []);
              return Array.isArray(list) && list.length > 0;
            })}>
              {provider => (
                <div>
                  <div class="flex items-center justify-between gap-2 px-3 py-2 text-[11px] font-medium text-primary bg-primary/7 rounded-xl mb-1.5">
                    <span>{provider.name}</span>
                    <button
                      type="button"
                      disabled={!provider.supports_model_refresh || props.isRefreshingModels}
                      title={provider.supports_model_refresh ? 'Refresh models for this provider' : 'This provider does not support model refresh'}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!provider.supports_model_refresh) return;
                        props.onRefreshModels();
                      }}
                      class={`text-[11px] px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                        provider.supports_model_refresh && !props.isRefreshingModels
                          ? 'border-border/80 bg-surface hover:bg-background text-text-secondary'
                          : 'border-border/70 bg-background text-text-secondary/40 cursor-not-allowed'
                      }`}
                    >
                      Refresh
                    </button>
                  </div>
                  <For each={(props.showAllModels ? provider.models : provider.available_models) || []}>
                    {model => (
                      <button
                        onClick={() => {
                          props.onSelectModel(provider.name, model);
                          props.setShow(false);
                        }}
                        class={`w-full text-left px-4 py-3 rounded-xl text-[14px] transition-all duration-200 flex items-center justify-between group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 ${
                          props.selectedModel === model
                            ? 'bg-primary/10 text-text-primary font-semibold ring-1 ring-primary/18'
                            : 'hover:bg-background text-text-primary'
                        }`}
                      >
                        <div class="flex items-center gap-2">
                          <span>{model}</span>
                          <For each={getModelCapabilityBadges(provider, model)}>
                            {badge => (
                              <span class="text-[10px] px-2 py-0.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
                                {badge}
                              </span>
                            )}
                          </For>
                        </div>
                        <Show when={props.selectedModel === model}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-primary" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                          </svg>
                        </Show>
                      </button>
                    )}
                  </For>
                </div>
              )}
            </For>
          </div>
        </div>
      </Show>
    </div>
  );
}
