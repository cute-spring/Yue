import { For, Show, type Accessor } from 'solid-js';
import type { CustomModel } from '../../types';

type LlmCustomModelsSectionProps = {
  customModels: Accessor<CustomModel[]>;
  deleteCustomModel: (name: string) => void;
  testCustomModel: (model: CustomModel) => void;
};

export function LlmCustomModelsSection(props: LlmCustomModelsSectionProps) {
  return (
    <div class="border-t pt-6">
      <h4 class="text-lg font-bold mb-3">Custom Models</h4>
      <div class="space-y-3">
        <div class="space-y-2">
          <For each={props.customModels()}>
            {(model) => (
              <div class="p-3 border rounded-lg flex items-center justify-between">
                <div>
                  <div class="font-bold">{model.name}</div>
                  <div class="text-xs text-gray-500">{model.base_url || ''}</div>
                  <div class="text-xs text-gray-500">{model.model || ''}</div>
                  <Show when={model.capabilities && model.capabilities.length > 0}>
                    <div class="flex gap-1 mt-1">
                      <For each={model.capabilities}>
                        {(cap) => (
                          <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                            {cap === 'function_calling' ? 'Tools' : cap.charAt(0).toUpperCase() + cap.slice(1)}
                          </span>
                        )}
                      </For>
                    </div>
                  </Show>
                </div>
                <div class="flex gap-2">
                  <button onClick={() => props.testCustomModel(model)} class="text-xs px-2 py-1 rounded border">
                    Test
                  </button>
                  <button
                    onClick={() => props.deleteCustomModel(model.name)}
                    class="text-xs px-2 py-1 rounded border text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </For>
          <Show when={props.customModels().length === 0}>
            <div class="text-sm text-gray-500">No custom models. Add one above.</div>
          </Show>
        </div>
      </div>
    </div>
  );
}
