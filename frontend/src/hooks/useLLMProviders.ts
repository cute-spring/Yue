import { createSignal, onMount } from 'solid-js';
import { Provider } from '../types';
import { useToast } from '../context/ToastContext';

const PROVIDER_STORAGE_KEY = 'yue_selected_provider';
const MODEL_STORAGE_KEY = 'yue_selected_model';

export function useLLMProviders() {
  const toast = useToast();
  const [providers, setProviders] = createSignal<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = createSignal<string>("");
  const [selectedModel, setSelectedModel] = createSignal<string>("");
  const [showLLMSelector, setShowLLMSelector] = createSignal(false);
  const [showAllModels, setShowAllModels] = createSignal(false);
  const [isRefreshingModels, setIsRefreshingModels] = createSignal(false);

  const loadProviders = async (refresh = false) => {
    try {
      const res = await fetch(`/api/models/providers${refresh ? '?refresh=1' : ''}`);
      const data = await res.json();
      setProviders(data);
      if (refresh) {
        toast.success("Models refreshed");
      }

      let currentProvider = data.find((p: any) => p.name === selectedProvider());

      if (!currentProvider && selectedModel()) {
        const providerByModel = data.find((p: any) => (p.available_models || []).includes(selectedModel()));
        if (providerByModel) {
          currentProvider = providerByModel;
          setSelectedProvider(providerByModel.name);
        }
      }

      if (selectedProvider() && (!currentProvider || !currentProvider.configured)) {
        setSelectedProvider("");
        setSelectedModel("");
        localStorage.removeItem(PROVIDER_STORAGE_KEY);
        localStorage.removeItem(MODEL_STORAGE_KEY);
        return;
      }

      if (currentProvider) {
        const availableModels = currentProvider.available_models || [];
        if (selectedModel() && !availableModels.includes(selectedModel())) {
          setSelectedModel("");
          localStorage.removeItem(MODEL_STORAGE_KEY);
        }
      }
    } catch (e) {
      console.error("Failed to load providers", e);
      toast.error("Failed to load AI providers");
    }
  };

  onMount(() => {
    const storedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const storedModel = localStorage.getItem(MODEL_STORAGE_KEY);
    if (storedProvider) setSelectedProvider(storedProvider);
    if (storedModel) setSelectedModel(storedModel);
    loadProviders();
  });

  return {
    providers,
    selectedProvider,
    setSelectedProvider,
    selectedModel,
    setSelectedModel,
    showLLMSelector,
    setShowLLMSelector,
    showAllModels,
    setShowAllModels,
    isRefreshingModels,
    setIsRefreshingModels,
    loadProviders,
    PROVIDER_STORAGE_KEY,
    MODEL_STORAGE_KEY
  };
}
