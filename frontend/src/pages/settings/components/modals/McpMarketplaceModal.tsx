import { createEffect, createMemo, createSignal, For, Show } from 'solid-js';
import type { McpTemplate, McpTemplateValidationResult } from '../../types';
import { buildMcpTemplateInitialValues } from '../../settingsUtils';

type McpMarketplaceModalProps = {
  templates: McpTemplate[];
  onClose: () => void;
  onValidate: (templateId: string, values: Record<string, string>) => Promise<McpTemplateValidationResult>;
  onInstall: (templateId: string, values: Record<string, string>) => Promise<McpTemplateValidationResult>;
};

export function McpMarketplaceModal(props: McpMarketplaceModalProps) {
  const [selectedTemplateId, setSelectedTemplateId] = createSignal(props.templates[0]?.id || '');
  const [values, setValues] = createSignal<Record<string, string>>({});
  const [validation, setValidation] = createSignal<McpTemplateValidationResult | null>(null);
  const [submitError, setSubmitError] = createSignal<string>('');
  const [isValidating, setIsValidating] = createSignal(false);
  const [isInstalling, setIsInstalling] = createSignal(false);

  const selectedTemplate = createMemo(() =>
    props.templates.find((template) => template.id === selectedTemplateId()) || props.templates[0],
  );

  createEffect(() => {
    const template = selectedTemplate();
    if (!template) return;
    setValues(buildMcpTemplateInitialValues(template));
    setValidation(null);
    setSubmitError('');
  });

  const updateValue = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setValidation(null);
    setSubmitError('');
  };

  const validate = async () => {
    const template = selectedTemplate();
    if (!template) return;
    setIsValidating(true);
    setSubmitError('');
    try {
      const result = await props.onValidate(template.id, values());
      setValidation(result);
      if (!result.ok) {
        setSubmitError(result.error || 'Validation failed');
      }
    } finally {
      setIsValidating(false);
    }
  };

  const install = async () => {
    const template = selectedTemplate();
    if (!template) return;
    setIsInstalling(true);
    setSubmitError('');
    try {
      const result = await props.onInstall(template.id, values());
      setValidation(result);
      if (!result.ok) {
        setSubmitError(result.error || 'Install failed');
        return;
      }
      props.onClose();
    } finally {
      setIsInstalling(false);
    }
  };

  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center">
      <div class="w-[960px] max-w-[96vw] max-h-[92vh] overflow-hidden bg-white rounded-xl border shadow-lg flex">
        <div class="w-[280px] border-r bg-gray-50">
          <div class="px-4 py-3 border-b flex items-center justify-between">
            <div class="font-semibold">Add from Marketplace</div>
            <button onClick={props.onClose}>✕</button>
          </div>
          <div class="p-3 space-y-3 overflow-y-auto max-h-[calc(92vh-56px)]">
            <For each={props.templates}>
              {(item) => (
                <button
                  onClick={() => setSelectedTemplateId(item.id)}
                  class={`w-full text-left p-3 rounded-xl border transition-colors ${
                    selectedTemplateId() === item.id
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 bg-white hover:bg-gray-100'
                  }`}
                >
                  <div class="font-semibold">{item.name}</div>
                  <div class="text-xs uppercase tracking-wide text-gray-500 mt-1">
                    {item.provider} · {item.deployment}
                  </div>
                  <div class="text-xs text-gray-600 mt-2">{item.description}</div>
                </button>
              )}
            </For>
          </div>
        </div>
        <div class="flex-1 flex flex-col">
          <div class="px-5 py-4 border-b">
            <div class="text-lg font-semibold">{selectedTemplate()?.name || 'MCP Template'}</div>
            <div class="text-sm text-gray-600 mt-1">
              {selectedTemplate()?.description || 'Choose a template and provide the real command, args, URLs, and auth mapping your company uses.'}
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-5 space-y-5">
            <Show when={selectedTemplate()}>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <For each={selectedTemplate()?.fields || []}>
                  {(field) => (
                    <div class={field.type === 'json' ? 'md:col-span-2' : ''}>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        {field.label}
                        <Show when={field.required}>
                          <span class="text-red-500"> *</span>
                        </Show>
                      </label>
                      <Show
                        when={field.type === 'select'}
                        fallback={
                          field.type === 'json' || field.type === 'textarea' ? (
                            <textarea
                              aria-label={field.label + (field.required ? ' *' : '')}
                              class="w-full min-h-[110px] font-mono text-sm border rounded-lg p-3 bg-gray-50"
                              value={values()[field.key] || ''}
                              placeholder={field.placeholder || undefined}
                              onInput={(e) => updateValue(field.key, e.currentTarget.value)}
                            />
                          ) : (
                            <input
                              type={field.secret ? 'password' : 'text'}
                              aria-label={field.label + (field.required ? ' *' : '')}
                              class="w-full border rounded-lg p-2.5 bg-gray-50"
                              value={values()[field.key] || ''}
                              placeholder={field.placeholder || undefined}
                              onInput={(e) => updateValue(field.key, e.currentTarget.value)}
                            />
                          )
                        }
                      >
                        <select
                          aria-label={field.label + (field.required ? ' *' : '')}
                          class="w-full border rounded-lg p-2.5 bg-gray-50"
                          value={values()[field.key] || ''}
                          onChange={(e) => updateValue(field.key, e.currentTarget.value)}
                        >
                          <For each={field.options}>
                            {(option) => <option value={option}>{option}</option>}
                          </For>
                        </select>
                      </Show>
                      <Show when={field.help_text}>
                        <div class="text-xs text-gray-500 mt-1">{field.help_text}</div>
                      </Show>
                    </div>
                  )}
                </For>
              </div>
            </Show>

            <Show when={submitError()}>
              <div class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {submitError()}
              </div>
            </Show>

            <Show when={validation()?.warnings?.length}>
              <div class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-3">
                <div class="text-sm font-medium text-amber-800">Validation Warnings</div>
                <div class="mt-2 space-y-1 text-sm text-amber-700">
                  <For each={validation()?.warnings || []}>
                    {(warning) => <div>{warning}</div>}
                  </For>
                </div>
              </div>
            </Show>

            <Show when={validation()?.rendered_config}>
              <div>
                <div class="text-sm font-medium text-gray-700 mb-2">Rendered MCP Config Preview</div>
                <pre class="rounded-xl bg-gray-950 text-gray-100 text-xs p-4 overflow-auto whitespace-pre-wrap">
                  {JSON.stringify(validation()?.rendered_config, null, 2)}
                </pre>
              </div>
            </Show>
          </div>
          <div class="px-5 py-4 border-t flex justify-between items-center gap-3">
            <div class="text-xs text-gray-500">
              Secrets are best stored as host env placeholders like <code>${'{JIRA_TOKEN}'}</code>.
            </div>
            <div class="flex items-center gap-2">
              <button onClick={props.onClose} class="px-3 py-1.5 rounded-md border">
                Cancel
              </button>
              <button
                onClick={validate}
                disabled={isValidating() || isInstalling() || !selectedTemplate()}
                class="px-3 py-1.5 rounded-md border bg-white disabled:opacity-60"
              >
                {isValidating() ? 'Validating...' : 'Validate'}
              </button>
              <button
                onClick={install}
                disabled={isValidating() || isInstalling() || !selectedTemplate()}
                class="px-3 py-1.5 rounded-md bg-emerald-600 text-white disabled:opacity-60"
              >
                {isInstalling() ? 'Installing...' : 'Install'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
