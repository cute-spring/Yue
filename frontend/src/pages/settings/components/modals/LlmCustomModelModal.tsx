import { createSignal, type Accessor, type Setter } from 'solid-js';
import {
  buildCustomModelCreatePayload,
  buildCustomModelTestPayload,
  normalizeCustomModelDraft,
  validateCustomModelDraft,
} from '../../customModelUtils';
import type { CustomModel, LLMProvider, NewCustomModelDraft } from '../../types';

type LlmCustomModelModalProps = {
  newCM: Accessor<NewCustomModelDraft>;
  setNewCM: Setter<NewCustomModelDraft>;
  newCMStatus: Accessor<string>;
  setNewCMStatus: Setter<string>;
  setShowAddCustom: Setter<boolean>;
  setCustomModels: Setter<CustomModel[]>;
  setProviders: Setter<LLMProvider[]>;
};

export function LlmCustomModelModal(props: LlmCustomModelModalProps) {
  const [isTesting, setIsTesting] = createSignal(false);
  const isEditing = () => Boolean(props.newCM().name?.trim());

  const applyLocalPreset = () => {
    props.setNewCM({
      ...props.newCM(),
      name: props.newCM().name || 'local-openai',
      provider: 'openai',
      model: props.newCM().model || '',
      base_url: props.newCM().base_url || 'http://localhost:8080/v1',
      api_key: props.newCM().api_key || '',
    });
    props.setNewCMStatus('Local OpenAI-compatible defaults applied');
  };

  const testCustomModel = async () => {
    const validationError = validateCustomModelDraft(props.newCM());
    if (validationError) {
      props.setNewCMStatus(validationError);
      return;
    }

    const normalizedDraft = normalizeCustomModelDraft(props.newCM());
    props.setNewCM(normalizedDraft);
    props.setNewCMStatus('Testing...');
    setIsTesting(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const res = await fetch('/api/models/test/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildCustomModelTestPayload(normalizedDraft)),
        signal: controller.signal,
      });
      const data = await res.json();
      props.setNewCMStatus(data.ok ? 'Connection OK' : `Failed: ${data.error || 'Unknown error'}`);
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === 'AbortError';
      props.setNewCMStatus(
        isAbort
          ? 'Failed: connection timed out after 15 seconds'
          : `Failed: ${error instanceof Error ? error.message : 'Request error'}`,
      );
    } finally {
      window.clearTimeout(timeout);
      setIsTesting(false);
    }
  };

  const saveCustomModel = async () => {
    const validationError = validateCustomModelDraft(props.newCM());
    if (validationError) {
      props.setNewCMStatus(validationError);
      return;
    }

    const normalizedDraft = normalizeCustomModelDraft(props.newCM());
    props.setNewCM(normalizedDraft);
    await fetch('/api/models/custom', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildCustomModelCreatePayload(normalizedDraft)),
    });
    const cmRes = await fetch('/api/models/custom');
    props.setCustomModels(await cmRes.json());
    const providersRes = await fetch('/api/models/providers?refresh=1');
    props.setProviders(await providersRes.json());
    props.setShowAddCustom(false);
    props.setNewCM({ name: '', provider: 'openai', model: '', base_url: '', api_key: '', capabilities: [] });
    props.setNewCMStatus('');
  };

  return (
    <div data-testid="llm-custom-model-modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="w-[720px] bg-white rounded-2xl border shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b flex justify-between items-center">
          <div class="font-bold text-lg">{isEditing() ? 'Edit Custom Model' : 'Custom Model'}</div>
          <button onClick={() => props.setShowAddCustom(false)} class="text-gray-500">
            ✕
          </button>
        </div>
        <form class="p-6 space-y-4" autocomplete="off" onSubmit={(e) => e.preventDefault()}>
          <div class="rounded-lg border border-emerald-100 bg-emerald-50 px-4 py-3 flex items-center justify-between gap-3">
            <div>
              <div class="text-sm font-bold text-emerald-900">Local OpenAI-compatible server</div>
              <div class="text-xs text-emerald-700">Uses http://localhost:8080/v1 with no API key.</div>
            </div>
            <button
              type="button"
              onClick={applyLocalPreset}
              class="shrink-0 text-xs px-3 py-1.5 rounded-md border border-emerald-200 bg-white text-emerald-800 hover:bg-emerald-100"
            >
              Use local defaults
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Name</div>
              <input
                data-testid="llm-custom-name-input"
                class="w-full border rounded-lg p-2"
                placeholder="my-custom"
                name="custom-model-display-name"
                autocomplete="off"
                autocapitalize="off"
                autocorrect="off"
                spellcheck={false}
                value={props.newCM().name}
                onInput={(e) => props.setNewCM({ ...props.newCM(), name: e.currentTarget.value })}
              />
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Provider</div>
              <select
                data-testid="llm-custom-provider-select"
                class="w-full border rounded-lg p-2"
                name="custom-model-provider"
                autocomplete="off"
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
              <div class="text-xs font-bold text-gray-600 mb-1">Model (Optional)</div>
              <input
                data-testid="llm-custom-model-input"
                class="w-full border rounded-lg p-2"
                placeholder="Leave blank to use the server default"
                name="custom-model-id"
                autocomplete="off"
                autocapitalize="off"
                autocorrect="off"
                spellcheck={false}
                value={props.newCM().model || ''}
                onInput={(e) => props.setNewCM({ ...props.newCM(), model: e.currentTarget.value })}
              />
            </div>
            <div>
              <div class="text-xs font-bold text-gray-600 mb-1">Endpoint Base URL (Optional)</div>
              <input
                data-testid="llm-custom-base-url-input"
                class="w-full border rounded-lg p-2"
                type="url"
                placeholder="http://localhost:8080/v1"
                name="custom-model-endpoint-url"
                autocomplete="url"
                autocapitalize="off"
                autocorrect="off"
                spellcheck={false}
                value={props.newCM().base_url || ''}
                onInput={(e) => props.setNewCM({ ...props.newCM(), base_url: e.currentTarget.value })}
              />
              <div class="mt-1 text-[11px] text-gray-500">
                Paste either the base URL or a full /chat/completions URL; it will be normalized.
              </div>
            </div>
          </div>
          <div>
            <div class="text-xs font-bold text-gray-600 mb-1">API Key (Optional)</div>
            <input
              data-testid="llm-custom-api-key-input"
              class="w-full border rounded-lg p-2"
              type="password"
              placeholder="Optional for local OpenAI-compatible servers"
              name="custom-model-api-key"
              autocomplete="new-password"
              autocapitalize="off"
              autocorrect="off"
              spellcheck={false}
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
        </form>
        <div class="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={() => props.setShowAddCustom(false)} class="px-3 py-1.5 rounded-lg border">
            Cancel
          </button>
          <button
            onClick={testCustomModel}
            disabled={isTesting()}
            class={`px-3 py-1.5 rounded-lg border ${
              isTesting() ? 'bg-gray-50 text-gray-400 cursor-not-allowed' : 'bg-white'
            }`}
          >
            {isTesting() ? 'Testing...' : 'Test'}
          </button>
          <button
            data-testid="llm-custom-save-button"
            onClick={saveCustomModel}
            class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white"
          >
            Save Model
          </button>
        </div>
      </div>
    </div>
  );
}
