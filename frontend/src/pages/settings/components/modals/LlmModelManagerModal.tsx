import type { Accessor, Setter } from 'solid-js';
import { For, Show } from 'solid-js';

type LlmModelManagerModalProps = {
  managingProvider: Accessor<string | null>;
  managedModels: Accessor<string[]>;
  enabledModels: Accessor<Set<string>>;
  setEnabledModels: Setter<Set<string>>;
  capabilityOverrides: Accessor<Record<string, string[]>>;
  setCapabilityOverrides: Setter<Record<string, string[]>>;
  adminModelCapabilities: Accessor<Record<string, string[]>>;
  isLoadingModels: Accessor<boolean>;
  isSavingModels: Accessor<boolean>;
  onClose: () => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onSave: () => void;
};

export function LlmModelManagerModal(props: LlmModelManagerModalProps) {
  return (
    <div data-testid="llm-model-manager-modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="w-[600px] bg-white rounded-2xl border shadow-xl overflow-hidden flex flex-col max-h-[80vh]">
        <div class="px-6 py-4 border-b flex justify-between items-center bg-gray-50">
          <div class="font-bold text-lg">Manage Models: {props.managingProvider()}</div>
          <button onClick={props.onClose} class="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div class="p-4 border-b bg-white flex justify-between items-center">
          <div class="text-sm text-gray-500">Select models to make available in the chat interface.</div>
          <div class="flex gap-2">
            <button
              onClick={props.onSelectAll}
              class="text-xs px-2 py-1 text-emerald-600 hover:bg-emerald-50 rounded"
            >
              Select All
            </button>
            <button
              onClick={props.onDeselectAll}
              class="text-xs px-2 py-1 text-red-600 hover:bg-red-50 rounded"
            >
              Deselect All
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-2">
          <Show
            when={!props.isLoadingModels()}
            fallback={
              <div class="flex justify-center items-center py-10">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
              </div>
            }
          >
            <div class="grid grid-cols-1 gap-1">
              <For each={props.managedModels()}>
                {(model) => {
                  const inferredCaps = () => props.adminModelCapabilities()[model] || [];
                  const explicitCaps = () => props.capabilityOverrides()[model];
                  const hasOverride = () => explicitCaps() !== undefined;
                  const activeCaps = () => explicitCaps() ?? inferredCaps();

                  const toggleCap = (cap: string, e: Event) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const currentActive = new Set(activeCaps());
                    if (currentActive.has(cap)) currentActive.delete(cap);
                    else currentActive.add(cap);
                    props.setCapabilityOverrides({
                      ...props.capabilityOverrides(),
                      [model]: Array.from(currentActive),
                    });
                  };

                  const resetCaps = (e: Event) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const newOverrides = { ...props.capabilityOverrides() };
                    delete newOverrides[model];
                    props.setCapabilityOverrides(newOverrides);
                  };

                  return (
                    <div class="flex items-center justify-between p-2 hover:bg-gray-50 rounded transition-colors group">
                      <label class="flex items-center gap-3 cursor-pointer flex-1 min-w-0">
                        <input
                          type="checkbox"
                          class="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500 border-gray-300"
                          checked={props.enabledModels().has(model)}
                          onChange={(e) => {
                            const newSet = new Set(props.enabledModels());
                            if (e.currentTarget.checked) newSet.add(model);
                            else newSet.delete(model);
                            props.setEnabledModels(newSet);
                          }}
                        />
                        <span
                          class={`text-sm truncate ${props.enabledModels().has(model) ? 'text-gray-900 font-medium' : 'text-gray-500'}`}
                        >
                          {model}
                        </span>
                      </label>
                      <div class="flex items-center gap-1.5 ml-4">
                        <For each={['vision', 'reasoning', 'function_calling']}>
                          {(cap) => {
                            const isActive = () => activeCaps().includes(cap);
                            const label = cap === 'function_calling' ? 'Tools' : cap.charAt(0).toUpperCase() + cap.slice(1);

                            return (
                              <button
                                onClick={(e) => toggleCap(cap, e)}
                                class={`text-[10px] px-2 py-0.5 rounded border transition-colors ${
                                  isActive()
                                    ? hasOverride()
                                      ? 'bg-emerald-100 border-emerald-300 text-emerald-700 font-medium'
                                      : 'bg-gray-100 border-gray-200 text-gray-600'
                                    : 'bg-transparent border-gray-100 text-gray-400 hover:border-gray-300'
                                }`}
                                title={isActive() ? `Supports ${label}` : `Does not support ${label}`}
                              >
                                {label}
                              </button>
                            );
                          }}
                        </For>
                        <Show when={hasOverride()}>
                          <button
                            onClick={resetCaps}
                            class="ml-1 text-[10px] text-gray-400 hover:text-red-500"
                            title="Reset to auto-inferred capabilities"
                          >
                            ↺ Reset
                          </button>
                        </Show>
                      </div>
                    </div>
                  );
                }}
              </For>
              <Show when={props.managedModels().length === 0}>
                <div class="p-8 text-center text-gray-500">No models found for this provider.</div>
              </Show>
            </div>
          </Show>
        </div>

        <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-2">
          <button
            onClick={props.onClose}
            class="px-4 py-2 rounded-lg border bg-white hover:bg-gray-50 text-sm font-medium"
            disabled={props.isSavingModels()}
          >
            Cancel
          </button>
          <button
            data-testid="llm-model-manager-save-button"
            onClick={props.onSave}
            class="px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={props.isSavingModels()}
          >
            {props.isSavingModels() ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
