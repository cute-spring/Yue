import type { Accessor, Setter } from 'solid-js';
import { Show } from 'solid-js';
import type { LlmForm } from '../../types';

type LlmProviderEditModalProps = {
  editingProvider: Accessor<string>;
  llmForm: Accessor<LlmForm>;
  setLlmForm: Setter<LlmForm>;
  onClose: () => void;
  onSave: () => void;
};

export function LlmProviderEditModal(props: LlmProviderEditModalProps) {
  return (
    <div data-testid="llm-provider-edit-modal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="w-[680px] bg-white rounded-2xl border shadow-xl overflow-hidden">
        <div class="px-6 py-4 border-b flex justify-between items-center">
          <div class="font-bold text-lg">Edit Provider: {props.editingProvider()}</div>
          <button onClick={props.onClose} class="text-gray-500">
            ✕
          </button>
        </div>
        <div class="p-6 space-y-4">
          <Show when={props.editingProvider() === 'openai'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">OPENAI_API_KEY</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().openai_api_key || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), openai_api_key: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">OPENAI_BASE_URL (Optional)</div>
                <input
                  class="w-full border rounded-lg p-2"
                  placeholder="https://openrouter.ai/api/v1"
                  value={props.llmForm().openai_base_url || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), openai_base_url: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">openai_model</div>
                <input
                  data-testid="llm-openai-model-input"
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().openai_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), openai_model: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'deepseek'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">DEEPSEEK_API_KEY</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().deepseek_api_key || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), deepseek_api_key: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">deepseek_model</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().deepseek_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), deepseek_model: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'gemini'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">GEMINI_API_KEY</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().gemini_api_key || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), gemini_api_key: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">GEMINI_BASE_URL</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().gemini_base_url || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), gemini_base_url: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">gemini_model</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().gemini_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), gemini_model: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'ollama'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">OLLAMA_BASE_URL</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().ollama_base_url || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), ollama_base_url: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">ollama_model</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().ollama_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), ollama_model: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'zhipu'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">ZHIPU_API_KEY</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().zhipu_api_key || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), zhipu_api_key: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">ZHIPU_BASE_URL</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().zhipu_base_url || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), zhipu_base_url: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">zhipu_model</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().zhipu_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), zhipu_model: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'azure_openai'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_ENDPOINT</div>
                <input
                  class="w-full border rounded-lg p-2"
                  placeholder="https://xxx.openai.azure.com"
                  value={props.llmForm().azure_openai_endpoint || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), azure_openai_endpoint: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_BASE_URL (Resource Path)</div>
                <input
                  class="w-full border rounded-lg p-2"
                  placeholder="https://xxx.openai.azure.com/openai"
                  value={props.llmForm().azure_openai_base_url || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), azure_openai_base_url: e.currentTarget.value })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_DEPLOYMENT (Chat)</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().azure_openai_deployment || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), azure_openai_deployment: e.currentTarget.value })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_EMBEDDING_DEPLOYMENT</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().azure_openai_embedding_deployment || ''}
                  onInput={(e) =>
                    props.setLlmForm({
                      ...props.llmForm(),
                      azure_openai_embedding_deployment: e.currentTarget.value,
                    })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_API_VERSION</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().azure_openai_api_version || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), azure_openai_api_version: e.currentTarget.value })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_TENANT_ID</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().azure_tenant_id || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), azure_tenant_id: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_CLIENT_ID</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().azure_client_id || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), azure_client_id: e.currentTarget.value })}
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_CLIENT_SECRET</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().azure_client_secret || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), azure_client_secret: e.currentTarget.value })
                  }
                />
              </div>
              <div class="md:col-span-2">
                <div class="text-xs font-bold text-gray-600 mb-1">AZURE_OPENAI_TOKEN (Optional)</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().azure_openai_token || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), azure_openai_token: e.currentTarget.value })}
                />
              </div>
            </div>
          </Show>
          <Show when={props.editingProvider() === 'litellm'}>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">LITELLM_BASE_URL</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().litellm_base_url || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), litellm_base_url: e.currentTarget.value })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">LITELLM_API_KEY</div>
                <input
                  class="w-full border rounded-lg p-2"
                  type="password"
                  value={props.llmForm().litellm_api_key || ''}
                  onInput={(e) =>
                    props.setLlmForm({ ...props.llmForm(), litellm_api_key: e.currentTarget.value })
                  }
                />
              </div>
              <div>
                <div class="text-xs font-bold text-gray-600 mb-1">litellm_model</div>
                <input
                  class="w-full border rounded-lg p-2"
                  value={props.llmForm().litellm_model || ''}
                  onInput={(e) => props.setLlmForm({ ...props.llmForm(), litellm_model: e.currentTarget.value })}
                  />
              </div>
            </div>
          </Show>
        </div>
        <div class="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={props.onClose} class="px-3 py-1.5 rounded-lg border">
            Cancel
          </button>
          <button data-testid="llm-provider-save-button" onClick={props.onSave} class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white">
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
