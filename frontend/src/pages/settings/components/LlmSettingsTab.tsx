import type { Accessor, Setter } from 'solid-js';
import { Show } from 'solid-js';
import type { CustomModel, LLMProvider, LlmForm, NewCustomModelDraft, Preferences } from '../types';
import { LlmCustomModelModal } from './modals/LlmCustomModelModal';
import { LlmModelManagerModal } from './modals/LlmModelManagerModal';
import { LlmProviderEditModal } from './modals/LlmProviderEditModal';
import { LlmCustomModelsSection } from './llm/LlmCustomModelsSection';
import { LlmProviderConfigsSection } from './llm/LlmProviderConfigsSection';
import { LlmRuntimeSettingsSection } from './llm/LlmRuntimeSettingsSection';
import { LlmTierSettingsSection } from './llm/LlmTierSettingsSection';

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
  return (
    <div class="space-y-8 max-w-4xl">
      <LlmProviderConfigsSection
        providers={props.providers}
        llmForm={props.llmForm}
        isRefreshingProviders={props.isRefreshingProviders}
        setNewCM={props.setNewCM}
        setNewCMStatus={props.setNewCMStatus}
        setShowAddCustom={props.setShowAddCustom}
        refreshProviders={props.refreshProviders}
        testProvider={props.testProvider}
        openProviderEditor={props.openProviderEditor}
        openModelManager={props.openModelManager}
      />

      <LlmCustomModelsSection
        customModels={props.customModels}
        deleteCustomModel={props.deleteCustomModel}
        testCustomModel={props.testCustomModel}
      />

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

      <LlmTierSettingsSection
        providers={props.providers}
        llmForm={props.llmForm}
        setLlmForm={props.setLlmForm}
      />

      <LlmRuntimeSettingsSection
        llmForm={props.llmForm}
        setLlmForm={props.setLlmForm}
        onSave={props.saveLlmConfig}
      />

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
