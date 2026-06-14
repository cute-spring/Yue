import { buildManagedModelsConfig, buildRevertedManagedModelsConfig } from './settingsUtils';
import { buildCustomModelTestPayload } from './customModelUtils';
import type { CustomModel, LLMProvider, LlmForm } from './types';

type Accessor<T> = () => T;
type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

type ToastFn = (
  type: 'success' | 'error',
  message: string,
  actionLabel?: string,
  action?: () => void,
) => void;

type UseSettingsLlmOptions = {
  llmForm: Accessor<LlmForm>;
  setLlmForm: Setter<LlmForm>;
  setProviders: Setter<LLMProvider[]>;
  setCustomModels: Setter<CustomModel[]>;
  setIsRefreshingProviders: Setter<boolean>;
  managingProvider: Accessor<string | null>;
  setManagingProvider: Setter<string | null>;
  setShowModelManager: Setter<boolean>;
  managedModels: Accessor<string[]>;
  setManagedModels: Setter<string[]>;
  enabledModels: Accessor<Set<string>>;
  setEnabledModels: Setter<Set<string>>;
  capabilityOverrides: Accessor<Record<string, string[]>>;
  setCapabilityOverrides: Setter<Record<string, string[]>>;
  setIsSavingModels: Setter<boolean>;
  setIsLoadingModels: Setter<boolean>;
  setModelManagerError: Setter<string>;
  adminModelsCache: Accessor<Record<string, any>>;
  setAdminModelsCache: Setter<Record<string, any>>;
  setAdminModelCapabilities: Setter<Record<string, string[]>>;
  setShowEditProvider: Setter<boolean>;
  setEditingProvider: Setter<string>;
  showToast: ToastFn;
  fetchData: () => Promise<void>;
};

export function useSettingsLlm(options: UseSettingsLlmOptions) {
  const postLlmConfig = async (nextConfig: LlmForm) => {
    options.setLlmForm(nextConfig);
    await fetch('/api/config/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nextConfig),
    });
    await options.fetchData();
  };

  const saveLlmConfig = async () => {
    await postLlmConfig(options.llmForm());
    options.showToast('success', 'LLM settings saved');
  };

  const refreshProviders = async () => {
    options.setIsRefreshingProviders(true);
    try {
      const providersRes = await fetch('/api/models/providers?refresh=1');
      options.setProviders(await providersRes.json());
      options.showToast('success', 'Models refreshed from providers');
    } catch {
      options.showToast('error', 'Failed to refresh models');
    } finally {
      options.setIsRefreshingProviders(false);
    }
  };

  const openModelManager = async (provider: LLMProvider) => {
    options.setManagingProvider(provider.name);
    options.setShowModelManager(true);
    options.setManagedModels([]);
    options.setEnabledModels(new Set<string>());
    options.setCapabilityOverrides({});
    options.setAdminModelCapabilities({});
    options.setModelManagerError('');

    if (options.adminModelsCache()[provider.name]) {
      const data = options.adminModelsCache()[provider.name];
      options.setManagedModels(data.models || []);
      options.setEnabledModels(new Set<string>(data.available_models || []));
      options.setCapabilityOverrides(data.explicit_model_capabilities || {});
      options.setAdminModelCapabilities(data.model_capabilities || {});
      return;
    }

    options.setIsLoadingModels(true);
    try {
      const res = await fetch(`/api/models/providers/${provider.name}/models`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      options.setManagedModels(data.models || []);
      options.setEnabledModels(new Set<string>(data.available_models || []));
      options.setCapabilityOverrides(data.explicit_model_capabilities || {});
      options.setAdminModelCapabilities(data.model_capabilities || {});
      options.setAdminModelsCache((prev) => ({ ...prev, [provider.name]: data }));
    } catch (error: any) {
      console.error('Failed to load models', error);
      const message = `Failed to load models: ${error.message}`;
      options.setManagedModels([]);
      options.setEnabledModels(new Set<string>());
      options.setCapabilityOverrides({});
      options.setAdminModelCapabilities({});
      options.setModelManagerError(message);
      options.showToast('error', message);
    } finally {
      options.setIsLoadingModels(false);
    }
  };

  const openCustomModelManager = async (model: CustomModel) => {
    options.setManagingProvider('custom');
    options.setShowModelManager(true);
    options.setManagedModels([]);
    options.setEnabledModels(new Set<string>());
    options.setCapabilityOverrides({});
    options.setAdminModelCapabilities({});
    options.setModelManagerError('');
    options.setIsLoadingModels(true);

    try {
      const res = await fetch(`/api/models/custom/${encodeURIComponent(model.name)}/models?refresh=1`);
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      options.setManagedModels(data.models || []);
      options.setEnabledModels(new Set<string>(data.available_models || []));
      options.setCapabilityOverrides(data.explicit_model_capabilities || {});
      options.setAdminModelCapabilities(data.model_capabilities || {});
      options.setAdminModelsCache((prev) => ({ ...prev, [`custom:${model.name}`]: data }));
    } catch (error: any) {
      console.error('Failed to load custom models', error);
      const message = `Failed to load models for ${model.name}: ${error.message}. Please restart the Yue backend if this happened after a code update.`;
      options.setManagedModels([]);
      options.setEnabledModels(new Set<string>());
      options.setCapabilityOverrides({});
      options.setAdminModelCapabilities({});
      options.setModelManagerError(message);
      options.showToast('error', message);
    } finally {
      options.setIsLoadingModels(false);
    }
  };

  const openProviderEditor = (name: string) => {
    options.setEditingProvider(name);
    options.setShowEditProvider(true);
  };

  const saveProviderEditor = async () => {
    await postLlmConfig(options.llmForm());
    options.setShowEditProvider(false);
  };

  const saveManagedModels = async () => {
    const providerName = options.managingProvider();
    if (!providerName) return;
    options.setIsSavingModels(true);
    try {
      const previous = new Set(options.enabledModels());
      const previousOverrides = { ...options.capabilityOverrides() };
      const currentConfig = options.llmForm();
      const { modelsDict, nextConfig: newConfig, previousMode } = buildManagedModelsConfig(
        currentConfig,
        providerName,
        options.enabledModels(),
        options.managedModels(),
        options.capabilityOverrides(),
      );
      await postLlmConfig(newConfig);
      options.setShowModelManager(false);
      options.showToast('success', `Models for ${providerName} updated`, 'Undo', async () => {
        const revertConfig = buildRevertedManagedModelsConfig(
          currentConfig,
          providerName,
          previous,
          previousMode,
          modelsDict,
          options.managedModels(),
          previousOverrides,
        );
        await postLlmConfig(revertConfig);
        options.showToast('success', `Reverted ${providerName} models`);
      });
    } finally {
      options.setIsSavingModels(false);
    }
  };

  const testProvider = async (name: string) => {
    const res = await fetch(`/api/models/test/${name}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: options.llmForm()[`${name}_model`] || undefined }),
    });
    const data = await res.json();
    if (data.ok) {
      options.showToast('success', `${name} connection OK`);
    } else {
      options.showToast('error', `${name} failed: ${data.error || 'Unknown error'}`);
    }
  };

  const deleteCustomModel = async (name: string) => {
    await fetch(`/api/models/custom/${name}`, { method: 'DELETE' });
    const response = await fetch('/api/models/custom');
    options.setCustomModels(await response.json());
    options.showToast('success', `Custom model ${name} deleted`);
  };

  const testCustomModel = async (model: { name: string; base_url?: string; api_key?: string; model?: string }) => {
    const res = await fetch('/api/models/test/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildCustomModelTestPayload(model)),
    });
    const data = await res.json();
    if (data.ok) {
      options.showToast('success', `Custom ${model.name} OK`);
    } else {
      options.showToast('error', `Custom ${model.name} failed: ${data.error || 'Unknown error'}`);
    }
  };

  return {
    saveLlmConfig,
    refreshProviders,
    openModelManager,
    openProviderEditor,
    saveProviderEditor,
    saveManagedModels,
    testProvider,
    deleteCustomModel,
    testCustomModel,
    openCustomModelManager,
  };
}
