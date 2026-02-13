import { For, Show } from 'solid-js';
import { Provider } from '../types';

interface ModelSelectorProps {
  showLLMSelector: boolean;
  setShowLLMSelector: (show: boolean) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  selectedProvider: string;
  setSelectedProvider: (provider: string) => void;
  providers: Provider[];
  showAllModels: boolean;
  setShowAllModels: (show: boolean) => void;
  isRefreshingModels: boolean;
  setIsRefreshingModels: (refreshing: boolean) => void;
  loadProviders: (refresh?: boolean) => Promise<void>;
  providerStorageKey: string;
  modelStorageKey: string;
}

export default function ModelSelector(props: ModelSelectorProps) {
  return (
    <div class="relative">
      <button 
        type="button"
        onClick={(e) => { 
          e.stopPropagation();
          props.setShowLLMSelector(!props.showLLMSelector);
        }}
        class="flex items-center gap-2.5 px-4 py-2.5 bg-background border border-border hover:border-primary/30 hover:bg-primary/5 rounded-2xl transition-all active:scale-95 shadow-sm"
      >
        <div class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
        <span class="text-xs font-bold text-text-primary uppercase tracking-wider">{props.selectedModel || "Select Model"}</span>
        <svg xmlns="http://www.w3.org/2000/svg" class={`h-3.5 w-3.5 text-text-secondary transition-transform duration-300 ${props.showLLMSelector ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <Show when={props.showLLMSelector}>
        <div class="absolute bottom-full left-0 mb-3 w-72 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div class="p-4 border-b border-white/10 flex items-center justify-between bg-white/5">
            <span class="text-xs font-bold text-white/70 uppercase tracking-widest">{props.showAllModels ? 'All Models' : 'Enabled Models'}</span>
            <div class="flex items-center gap-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  props.setShowAllModels(!props.showAllModels);
                }}
                class="text-[10px] px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white/80 font-bold uppercase tracking-wider"
              >
                {props.showAllModels ? 'Enabled' : 'All'}
              </button>
              <Show when={props.isRefreshingModels}>
                <div class="w-4 h-4 border-2 border-white/20 border-t-primary rounded-full animate-spin"></div>
              </Show>
            </div>
          </div>
          <div class="p-2 max-h-80 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-white/10">
            <For each={props.providers.filter(p => {
              const list = props.showAllModels ? (p.models || []) : (p.available_models || []);
              return Array.isArray(list) && list.length > 0;
            })}>
              {provider => (
                <div>
                  <div class="flex items-center justify-between gap-2 px-3 py-2 text-[10px] font-bold text-primary uppercase bg-primary/10 rounded-lg mb-1 tracking-wider">
                    <span>{provider.name}</span>
                    <button
                      type="button"
                      disabled={!provider.supports_model_refresh || props.isRefreshingModels}
                      title={provider.supports_model_refresh ? 'Refresh models for this provider' : 'This provider does not support model refresh'}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!provider.supports_model_refresh) return;
                        props.setIsRefreshingModels(true);
                        props.loadProviders(true).finally(() => props.setIsRefreshingModels(false));
                      }}
                      class={`text-[10px] px-2 py-1 rounded-lg border font-bold uppercase tracking-wider ${
                        provider.supports_model_refresh && !props.isRefreshingModels
                          ? 'border-white/10 bg-white/5 hover:bg-white/10 text-white/80'
                          : 'border-white/10 bg-white/5 text-white/30 cursor-not-allowed'
                      }`}
                    >
                      Refresh
                    </button>
                  </div>
                  <For each={(props.showAllModels ? provider.models : provider.available_models) || []}>
                    {model => (
                      <button
                        onClick={() => {
                          props.setSelectedProvider(provider.name);
                          props.setSelectedModel(model);
                          localStorage.setItem(props.providerStorageKey, provider.name);
                          localStorage.setItem(props.modelStorageKey, model);
                          props.setShowLLMSelector(false);
                        }}
                        class={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-between group ${
                          props.selectedModel === model
                            ? 'bg-primary text-white font-bold shadow-lg shadow-primary/20'
                            : 'hover:bg-white/5 text-gray-300 hover:text-white'
                        }`}
                      >
                        <span>{model}</span>
                        <Show when={props.selectedModel === model}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
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
