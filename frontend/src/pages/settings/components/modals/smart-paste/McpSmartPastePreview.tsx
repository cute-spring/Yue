import { For, Show, type Accessor } from 'solid-js';
import type { ParsedMcpConfig } from '../../../types';
import { resolveConfidenceTone } from '../McpSmartPasteModal.logic';

type McpSmartPastePreviewProps = {
  phase: Accessor<'preview' | 'saving'>;
  results: Accessor<ParsedMcpConfig[]>;
  saveError: Accessor<string | null>;
  saveSuccess: Accessor<boolean>;
  handleUpdateCandidate: (index: number, updates: Partial<ParsedMcpConfig>) => void;
  handleTransportChange: (index: number, newTransport: 'stdio' | 'streamable_http') => void;
  handleToggleSelected: (index: number) => void;
  handleDeleteCandidate: (index: number) => void;
  handleUpdateHeader: (configIndex: number, key: string, value: string) => void;
  handleRemoveHeader: (configIndex: number, key: string) => void;
  handleAddHeader: (configIndex: number) => void;
  handleUpdateEnv: (configIndex: number, key: string, value: string) => void;
  handleRemoveEnv: (configIndex: number, key: string) => void;
  handleAddEnv: (configIndex: number) => void;
};

const confidenceClass = (confidence: number) => {
  const tone = resolveConfidenceTone(confidence);
  if (tone === 'danger') return 'text-red-600 bg-red-50 border-red-200';
  if (tone === 'warning') return 'text-amber-600 bg-amber-50 border-amber-200';
  return 'text-emerald-600 bg-emerald-50 border-emerald-200';
};

export function McpSmartPastePreview(props: McpSmartPastePreviewProps) {
  return (
    <>
      <div class="mb-3 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
        <div class="text-sm font-semibold text-emerald-800 mb-1 flex items-center gap-1.5">
          <span class="text-base">✅</span> Parse Successful
        </div>
        <p class="text-xs text-emerald-700">
          AI has identified the configurations. If they contain <span class="font-mono bg-emerald-100 px-1 rounded">${"{"}ENV_NAME{"}"}</span> placeholders, please make sure to replace them with <b>actual values</b> in the inputs below before saving, otherwise the service might fail to connect.
        </p>
      </div>
      <div class="space-y-3">
        <For each={props.results()}>
          {(config, index) => (
            <div class="border rounded-lg p-3 bg-gray-50">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={config._selected !== false}
                    onChange={() => props.handleToggleSelected(index())}
                    class="h-4 w-4 accent-emerald-600"
                    disabled={props.phase() === 'saving'}
                  />
                  <input
                    type="text"
                    data-testid="smart-paste-name-input"
                    value={config.name}
                    onInput={(e) => props.handleUpdateCandidate(index(), { name: e.currentTarget.value })}
                    class="text-sm font-semibold border rounded px-2 py-0.5 bg-white min-w-[120px]"
                    disabled={props.phase() === 'saving'}
                  />
                  <select
                    value={config.transport}
                    onChange={(e) => props.handleTransportChange(index(), e.currentTarget.value as 'stdio' | 'streamable_http')}
                    class="text-xs border rounded px-1.5 py-0.5 bg-white"
                    disabled={props.phase() === 'saving'}
                  >
                    <option value="stdio">stdio</option>
                    <option value="streamable_http">streamable_http</option>
                  </select>
                  <span class={`text-xs px-1.5 py-0.5 rounded border font-medium ${confidenceClass(config.confidence)}`}>
                    {Math.round(config.confidence * 100)}%
                  </span>
                </div>
                <button
                  onClick={() => props.handleDeleteCandidate(index())}
                  class="text-red-500 hover:text-red-700 text-xs"
                  disabled={props.phase() === 'saving'}
                >
                  ✕
                </button>
              </div>

              <Show when={config.transport === 'stdio'}>
                <div class="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label class="text-gray-500">Command</label>
                    <input
                      type="text"
                      value={config.command || ''}
                      onInput={(e) => props.handleUpdateCandidate(index(), { command: e.currentTarget.value || null })}
                      class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                      disabled={props.phase() === 'saving'}
                    />
                  </div>
                  <div>
                    <label class="text-gray-500">Args (JSON array)</label>
                    <input
                      type="text"
                      value={config.args ? JSON.stringify(config.args) : ''}
                      onInput={(e) => {
                        try {
                          const parsed = JSON.parse(e.currentTarget.value);
                          props.handleUpdateCandidate(index(), { args: Array.isArray(parsed) ? parsed : null });
                        } catch {
                          props.handleUpdateCandidate(index(), { args: null });
                        }
                      }}
                      class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                      disabled={props.phase() === 'saving'}
                    />
                  </div>
                </div>

                <div class="mt-2">
                  <div class="flex items-center justify-between mb-1">
                    <label class="text-xs text-gray-500">Environment Variables</label>
                    <button
                      onClick={() => props.handleAddEnv(index())}
                      class="text-xs text-blue-600 hover:text-blue-800"
                      disabled={props.phase() === 'saving'}
                    >
                      + Add
                    </button>
                  </div>
                  <Show when={config.env && Object.keys(config.env).length > 0}>
                    <div class="space-y-1">
                      <For each={Object.entries(config.env || {})}>
                        {([key, value]) => (
                          <div class="flex items-center gap-1 text-xs">
                            <input
                              type="text"
                              value={key}
                              onInput={(e) => {
                                props.handleRemoveEnv(index(), key);
                                props.handleUpdateEnv(index(), e.currentTarget.value, value as string);
                              }}
                              class="w-2/5 border rounded px-1.5 py-0.5 bg-white font-mono"
                              placeholder="KEY"
                              disabled={props.phase() === 'saving'}
                            />
                            <input
                              type="text"
                              value={value as string}
                              onInput={(e) => props.handleUpdateEnv(index(), key, e.currentTarget.value)}
                              class="flex-1 border rounded px-1.5 py-0.5 bg-white font-mono"
                              placeholder="value"
                              disabled={props.phase() === 'saving'}
                            />
                            <button
                              onClick={() => props.handleRemoveEnv(index(), key)}
                              class="text-red-400 hover:text-red-600 px-1"
                              disabled={props.phase() === 'saving'}
                            >
                              ✕
                            </button>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </div>
              </Show>

              <Show when={config.transport === 'streamable_http'}>
                <div class="text-xs mb-1">
                  <label class="text-gray-500">URL</label>
                  <input
                    type="text"
                    value={config.url || ''}
                    onInput={(e) => props.handleUpdateCandidate(index(), { url: e.currentTarget.value || null })}
                    class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                    disabled={props.phase() === 'saving'}
                  />
                </div>

                <div class="mt-2">
                  <div class="flex items-center justify-between mb-1">
                    <label class="text-xs text-gray-500">Headers</label>
                    <button
                      onClick={() => props.handleAddHeader(index())}
                      class="text-xs text-blue-600 hover:text-blue-800"
                      disabled={props.phase() === 'saving'}
                    >
                      + Add
                    </button>
                  </div>
                  <Show when={config.headers && Object.keys(config.headers).length > 0}>
                    <div class="space-y-1">
                      <For each={Object.entries(config.headers || {})}>
                        {([key, value]) => (
                          <div class="flex items-center gap-1 text-xs">
                            <input
                              type="text"
                              value={key}
                              onInput={(e) => {
                                props.handleRemoveHeader(index(), key);
                                props.handleUpdateHeader(index(), e.currentTarget.value, value);
                              }}
                              class="w-2/5 border rounded px-1.5 py-0.5 bg-white font-mono"
                              placeholder="Header"
                              disabled={props.phase() === 'saving'}
                            />
                            <input
                              type="text"
                              value={value}
                              onInput={(e) => props.handleUpdateHeader(index(), key, e.currentTarget.value)}
                              class="flex-1 border rounded px-1.5 py-0.5 bg-white font-mono"
                              placeholder="value"
                              disabled={props.phase() === 'saving'}
                            />
                            <button
                              onClick={() => props.handleRemoveHeader(index(), key)}
                              class="text-red-400 hover:text-red-600 px-1"
                              disabled={props.phase() === 'saving'}
                            >
                              ✕
                            </button>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </div>
              </Show>

              <Show when={config.hints.length > 0}>
                <div class="mt-2 text-xs text-gray-500">
                  <For each={config.hints}>{(hint) => <div>ℹ {hint}</div>}</For>
                </div>
              </Show>
              <Show when={config.warnings.length > 0}>
                <div class="mt-1 text-xs text-amber-600">
                  <For each={config.warnings}>{(w) => <div>⚠ {w}</div>}</For>
                </div>
              </Show>
              <Show when={config.missing_fields.length > 0}>
                <div class="mt-1 text-xs text-red-500">
                  Missing fields: {config.missing_fields.join(', ')}
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>

      <Show when={props.saveError()}>
        <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {props.saveError()}
        </div>
      </Show>
      <Show when={props.saveSuccess()}>
        <div class="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">
          Save Successful!
        </div>
      </Show>
    </>
  );
}
