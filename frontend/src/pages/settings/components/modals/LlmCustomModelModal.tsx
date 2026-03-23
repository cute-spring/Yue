import type { Accessor, Setter } from 'solid-js';
import type { CustomModel, NewCustomModelDraft } from '../../types';

type LlmCustomModelModalProps = {
  newCM: Accessor<NewCustomModelDraft>;
  setNewCM: Setter<NewCustomModelDraft>;
  newCMStatus: Accessor<string>;
  setNewCMStatus: Setter<string>;
  setShowAddCustom: Setter<boolean>;
  setCustomModels: Setter<CustomModel[]>;
};

export function LlmCustomModelModal(props: LlmCustomModelModalProps) {
  return (
    <div data-testid="llm-custom-model-modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="w-[720px] bg-white rounded-2xl border shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b flex justify-between items-center">
          <div class="font-bold text-lg">Add Custom Model</div>
          <button onClick={() => props.setShowAddCustom(false)} class="text-gray-500">
            ✕
          </button>
        </div>
        <div class="p-6 space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Name</div>
              <input
                data-testid="llm-custom-name-input"
                class="w-full border rounded-lg p-2"
                placeholder="my-custom"
                value={props.newCM().name}
                onInput={(e) => props.setNewCM({ ...props.newCM(), name: e.currentTarget.value })}
              />
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Provider</div>
              <select
                data-testid="llm-custom-provider-select"
                class="w-full border rounded-lg p-2"
                value={props.newCM().provider}
                onInput={(e) => props.setNewCM({ ...props.newCM(), provider: e.currentTarget.value })}
              >
                <option value="openai">OpenAI</option>
                <option value="deepseek">DeepSeek</option>
                <option value="gemini">Gemini</option>
                <option value="ollama">Ollama</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Model</div>
              <input
                data-testid="llm-custom-model-input"
                class="w-full border rounded-lg p-2"
                placeholder="gpt-4o"
                value={props.newCM().model}
                onInput={(e) => props.setNewCM({ ...props.newCM(), model: e.currentTarget.value })}
              />
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Base URL (Optional)</div>
              <input
                data-testid="llm-custom-base-url-input"
                class="w-full border rounded-lg p-2"
                placeholder="https://..."
                value={props.newCM().base_url || ''}
                onInput={(e) => props.setNewCM({ ...props.newCM(), base_url: e.currentTarget.value })}
              />
            </div>
          </div>
          <div>
            <div class="text-xs font-bold text-gray-600 mb-1">API Key</div>
            <input
              data-testid="llm-custom-api-key-input"
              class="w-full border rounded-lg p-2"
              type="password"
              placeholder="****"
              value={props.newCM().api_key || ''}
              onInput={(e) => props.setNewCM({ ...props.newCM(), api_key: e.currentTarget.value })}
            />
          </div>
          <div>
            <div class="text-xs font-bold text-gray-600 mb-2">Model Capabilities</div>
            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  class="rounded text-emerald-600 focus:ring-emerald-500"
                  checked={props.newCM().capabilities?.includes('vision')}
                  onChange={(e) => {
                    const caps = new Set(props.newCM().capabilities || []);
                    if (e.currentTarget.checked) caps.add('vision');
                    else caps.delete('vision');
                    props.setNewCM({ ...props.newCM(), capabilities: Array.from(caps) });
                  }}
                />
                Supports Vision (Image input)
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  class="rounded text-emerald-600 focus:ring-emerald-500"
                  checked={props.newCM().capabilities?.includes('reasoning')}
                  onChange={(e) => {
                    const caps = new Set(props.newCM().capabilities || []);
                    if (e.currentTarget.checked) caps.add('reasoning');
                    else caps.delete('reasoning');
                    props.setNewCM({ ...props.newCM(), capabilities: Array.from(caps) });
                  }}
                />
                Supports Deep Thinking (Reasoning)
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  class="rounded text-emerald-600 focus:ring-emerald-500"
                  checked={props.newCM().capabilities?.includes('function_calling')}
                  onChange={(e) => {
                    const caps = new Set(props.newCM().capabilities || []);
                    if (e.currentTarget.checked) caps.add('function_calling');
                    else caps.delete('function_calling');
                    props.setNewCM({ ...props.newCM(), capabilities: Array.from(caps) });
                  }}
                />
                Supports Function Calling (Tools)
              </label>
            </div>
          </div>
          <div class="text-xs text-gray-600">{props.newCMStatus()}</div>
        </div>
        <div class="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={() => props.setShowAddCustom(false)} class="px-3 py-1.5 rounded-lg border">
            Cancel
          </button>
          <button
            onClick={async () => {
              props.setNewCMStatus('Testing...');
              const res = await fetch('/api/models/test/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  base_url: props.newCM().base_url,
                  api_key: props.newCM().api_key,
                  model: props.newCM().model,
                }),
              });
              const data = await res.json();
              props.setNewCMStatus(data.ok ? 'Connection OK' : `Failed: ${data.error || 'Unknown error'}`);
            }}
            class="px-3 py-1.5 rounded-lg border bg-white"
          >
            Test
          </button>
          <button
            data-testid="llm-custom-save-button"
            onClick={async () => {
              if (!props.newCM().name) {
                props.setNewCMStatus('Name is required');
                return;
              }
              await fetch('/api/models/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  name: props.newCM().name,
                  base_url: props.newCM().base_url,
                  api_key: props.newCM().api_key,
                  model: props.newCM().model,
                  capabilities: props.newCM().capabilities,
                }),
              });
              const cmRes = await fetch('/api/models/custom');
              props.setCustomModels(await cmRes.json());
              props.setShowAddCustom(false);
              props.setNewCM({ name: '', provider: 'openai', model: '', capabilities: [] });
              props.setNewCMStatus('');
            }}
            class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
