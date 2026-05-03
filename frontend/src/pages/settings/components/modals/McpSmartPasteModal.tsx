import { createSignal, For, Show, onCleanup } from 'solid-js';
import type { ParsedMcpConfig, SmartPasteResponse } from '../../types';
import { validateSmartPasteInput, applyTransportChange, findNameConflicts, resolveConfidenceTone, detectSensitiveValues, applyReplacements } from './McpSmartPasteModal.logic';
import type { SensitiveDetection } from './McpSmartPasteModal.logic';

type Phase = 'idle' | 'sensitive_check' | 'parsing' | 'preview' | 'saving';

type McpSmartPasteModalProps = {
  existingNames: string[];
  onClose: () => void;
  onParse: (rawText: string, signal: AbortSignal) => Promise<SmartPasteResponse>;
  onSave: (configs: ParsedMcpConfig[]) => Promise<void>;
};

export function McpSmartPasteModal(props: McpSmartPasteModalProps) {
  const [phase, setPhase] = createSignal<Phase>('idle');
  const [rawText, setRawText] = createSignal('');
  const [results, setResults] = createSignal<ParsedMcpConfig[]>([]);
  const [parseError, setParseError] = createSignal<string | null>(null);
  const [saveError, setSaveError] = createSignal<string | null>(null);
  const [saveSuccess, setSaveSuccess] = createSignal(false);
  const [sensitiveDetections, setSensitiveDetections] = createSignal<SensitiveDetection[]>([]);
  const [replacedText, setReplacedText] = createSignal('');
  let abortController: AbortController | null = null;
  let textareaRef: HTMLTextAreaElement | undefined;

  onCleanup(() => {
    if (abortController) {
      abortController.abort();
    }
  });

  const doParse = async (text: string) => {
    setPhase('parsing');
    abortController = new AbortController();

    try {
      const response = await props.onParse(text, abortController.signal);
      if (response.ok && response.results.length > 0) {
        setResults(response.results);
        setPhase('preview');
      } else {
        setParseError(response.error || '无法从输入中解析出有效的 MCP 配置');
        setPhase('idle');
      }
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        setPhase('idle');
        return;
      }
      setParseError(e?.message || '解析失败，请重试');
      setPhase('idle');
    }
  };

  const handleParse = async () => {
    const validation = validateSmartPasteInput(rawText());
    if (validation.kind === 'empty') {
      return;
    }
    if (validation.kind === 'too_long') {
      setParseError('输入文本过长，请精简后重试');
      return;
    }

    setParseError(null);

    const detections = detectSensitiveValues(rawText());
    if (detections.length > 0) {
      setSensitiveDetections(detections);
      setReplacedText(applyReplacements(rawText(), detections));
      setPhase('sensitive_check');
      return;
    }

    await doParse(rawText());
  };

  const handleCancelParse = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    setPhase('idle');
  };

  const handleSensitiveReplaceAll = () => {
    const cleanText = applyReplacements(rawText(), sensitiveDetections());
    setRawText(cleanText);
    setPhase('idle');
    doParse(cleanText);
  };

  const handleSensitiveSendAnyway = () => {
    setPhase('idle');
    doParse(rawText());
  };

  const handleSensitiveBackToEdit = () => {
    setPhase('idle');
  };

  const handleRetry = () => {
    setPhase('idle');
    setParseError(null);
  };

  const handleUpdateCandidate = (index: number, updates: Partial<ParsedMcpConfig>) => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const handleTransportChange = (index: number, newTransport: 'stdio' | 'streamable_http') => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = applyTransportChange(next[index], newTransport);
      return next;
    });
  };

  const handleToggleSelected = (index: number) => {
    setResults((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], _selected: !next[index]._selected };
      return next;
    });
  };

  const handleDeleteCandidate = (index: number) => {
    setResults((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateHeader = (configIndex: number, key: string, value: string) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      if (value === '' && !(key in headers)) return prev;
      headers[key] = value;
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleRemoveHeader = (configIndex: number, key: string) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      delete headers[key];
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleAddHeader = (configIndex: number) => {
    setResults((prev) => {
      const next = [...prev];
      const headers = { ...(next[configIndex].headers || {}) };
      let i = 0;
      while (`header_${i}` in headers) i++;
      headers[`header_${i}`] = '';
      next[configIndex] = { ...next[configIndex], headers };
      return next;
    });
  };

  const handleUpdateEnv = (configIndex: number, key: string, value: string) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      if (value === '' && !(key in env)) return prev;
      env[key] = value;
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleRemoveEnv = (configIndex: number, key: string) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      delete env[key];
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleAddEnv = (configIndex: number) => {
    setResults((prev) => {
      const next = [...prev];
      const env = { ...(next[configIndex].env || {}) };
      let i = 0;
      while (`ENV_${i}` in env) i++;
      env[`ENV_${i}`] = '';
      next[configIndex] = { ...next[configIndex], env };
      return next;
    });
  };

  const handleSave = async () => {
    const selected = results().filter((r) => r._selected !== false);
    if (selected.length === 0) {
      setSaveError('请至少选择一个配置进行保存');
      return;
    }

    const conflicts = findNameConflicts(props.existingNames, selected);
    if (conflicts.length > 0) {
      setSaveError(`配置名称已存在: ${conflicts.join(', ')}`);
      return;
    }

    setPhase('saving');
    setSaveError(null);

    try {
      await props.onSave(selected);
      setSaveSuccess(true);
      setTimeout(() => props.onClose(), 1000);
    } catch (e: any) {
      setSaveError(e?.message || '保存失败');
      setPhase('preview');
    }
  };

  const confidenceClass = (confidence: number) => {
    const tone = resolveConfidenceTone(confidence);
    if (tone === 'danger') return 'text-red-600 bg-red-50 border-red-200';
    if (tone === 'warning') return 'text-amber-600 bg-amber-50 border-amber-200';
    return 'text-emerald-600 bg-emerald-50 border-emerald-200';
  };

  return (
    <div class="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={props.onClose}>
      <div class="w-[720px] max-h-[85vh] bg-white rounded-xl border shadow-xl flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div class="px-4 py-3 border-b flex justify-between items-center shrink-0">
          <div class="font-semibold text-lg">Smart Paste (AI)</div>
          <button onClick={props.onClose} class="text-gray-400 hover:text-gray-600 text-xl leading-none">✕</button>
        </div>

        <div class="flex-1 overflow-y-auto p-4">
          <Show when={phase() === 'sensitive_check'}>
            <div class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-amber-600 font-semibold">⚠️</span>
                <span class="text-sm font-semibold text-amber-800">
                  检测到 {sensitiveDetections().length} 处疑似敏感信息
                </span>
              </div>
              <p class="text-xs text-amber-700 mb-3">
                建议在发送解析前替换为环境变量占位符，保护密钥安全。替换后可在系统环境变量中设置真实值。
              </p>

              <div class="space-y-2 max-h-[200px] overflow-y-auto mb-3">
                <For each={sensitiveDetections()}>
                  {(det) => (
                    <div class="flex items-center gap-2 text-xs bg-white rounded p-2 border border-amber-100">
                      <span class="text-red-600 font-mono bg-red-50 px-1.5 py-0.5 rounded max-w-[180px] truncate" title={det.value}>
                        {det.value}
                      </span>
                      <span class="text-gray-400">→</span>
                      <span class="text-emerald-600 font-mono bg-emerald-50 px-1.5 py-0.5 rounded">
                        {det.placeholder}
                      </span>
                      <span class="text-gray-400 ml-auto text-[10px]">{det.key}</span>
                    </div>
                  )}
                </For>
              </div>

              <div class="text-xs text-gray-500 mb-3">
                <div class="font-medium mb-1">替换后预览：</div>
                <pre class="bg-white border rounded p-2 max-h-[120px] overflow-y-auto text-[11px] whitespace-pre-wrap font-mono">{replacedText()}</pre>
              </div>
            </div>
          </Show>

          <Show when={phase() === 'idle' || phase() === 'parsing'}>
            <div class="text-sm text-gray-500 mb-3">
              粘贴你的 MCP 配置信息，支持 Claude Desktop JSON、命令行片段、HTTP 端点或自然语言描述
            </div>
            <textarea
              ref={textareaRef}
              data-testid="smart-paste-textarea"
              class="w-full min-h-[180px] font-mono text-sm border rounded-lg p-3 bg-gray-50 resize-y"
              value={rawText()}
              onInput={(e) => setRawText(e.currentTarget.value)}
              placeholder={`{
  "mcpServers": {
    "example": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-example"]
    }
  }
}`}
              disabled={phase() === 'parsing'}
            />
            <div class="text-xs text-gray-400 mt-1">密钥安全：token / 密码会自动转为 $&#123;ENV_NAME&#125; 占位符</div>

            <Show when={parseError()}>
              <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {parseError()}
              </div>
            </Show>
          </Show>

          <Show when={phase() === 'preview' || phase() === 'saving'}>
            <div class="text-sm text-gray-500 mb-3">
              解析完成，确认以下配置后保存：
            </div>
            <div class="space-y-3">
              <For each={results()}>
                {(config, index) => (
                  <div class="border rounded-lg p-3 bg-gray-50">
                    <div class="flex items-center justify-between mb-2">
                      <div class="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={config._selected !== false}
                          onChange={() => handleToggleSelected(index())}
                          class="h-4 w-4 accent-emerald-600"
                          disabled={phase() === 'saving'}
                        />
                        <input
                          type="text"
                          data-testid="smart-paste-name-input"
                          value={config.name}
                          onInput={(e) => handleUpdateCandidate(index(), { name: e.currentTarget.value })}
                          class="text-sm font-semibold border rounded px-2 py-0.5 bg-white min-w-[120px]"
                          disabled={phase() === 'saving'}
                        />
                        <select
                          value={config.transport}
                          onChange={(e) => handleTransportChange(index(), e.currentTarget.value as any)}
                          class="text-xs border rounded px-1.5 py-0.5 bg-white"
                          disabled={phase() === 'saving'}
                        >
                          <option value="stdio">stdio</option>
                          <option value="streamable_http">streamable_http</option>
                        </select>
                        <span class={`text-xs px-1.5 py-0.5 rounded border font-medium ${confidenceClass(config.confidence)}`}>
                          {Math.round(config.confidence * 100)}%
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeleteCandidate(index())}
                        class="text-red-500 hover:text-red-700 text-xs"
                        disabled={phase() === 'saving'}
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
                            onInput={(e) => handleUpdateCandidate(index(), { command: e.currentTarget.value || null })}
                            class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                            disabled={phase() === 'saving'}
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
                                handleUpdateCandidate(index(), { args: Array.isArray(parsed) ? parsed : null });
                              } catch {
                                handleUpdateCandidate(index(), { args: null });
                              }
                            }}
                            class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                            disabled={phase() === 'saving'}
                          />
                        </div>
                      </div>

                      <div class="mt-2">
                        <div class="flex items-center justify-between mb-1">
                          <label class="text-xs text-gray-500">Environment Variables</label>
                          <button
                            onClick={() => handleAddEnv(index())}
                            class="text-xs text-blue-600 hover:text-blue-800"
                            disabled={phase() === 'saving'}
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
                                      handleRemoveEnv(index(), key);
                                      handleUpdateEnv(index(), e.currentTarget.value, value as string);
                                    }}
                                    class="w-2/5 border rounded px-1.5 py-0.5 bg-white font-mono"
                                    placeholder="KEY"
                                    disabled={phase() === 'saving'}
                                  />
                                  <input
                                    type="text"
                                    value={value as string}
                                    onInput={(e) => handleUpdateEnv(index(), key, e.currentTarget.value)}
                                    class="flex-1 border rounded px-1.5 py-0.5 bg-white font-mono"
                                    placeholder="value"
                                    disabled={phase() === 'saving'}
                                  />
                                  <button
                                    onClick={() => handleRemoveEnv(index(), key)}
                                    class="text-red-400 hover:text-red-600 px-1"
                                    disabled={phase() === 'saving'}
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
                          onInput={(e) => handleUpdateCandidate(index(), { url: e.currentTarget.value || null })}
                          class="w-full border rounded px-2 py-0.5 bg-white font-mono"
                          disabled={phase() === 'saving'}
                        />
                      </div>

                      <div class="mt-2">
                        <div class="flex items-center justify-between mb-1">
                          <label class="text-xs text-gray-500">Headers</label>
                          <button
                            onClick={() => handleAddHeader(index())}
                            class="text-xs text-blue-600 hover:text-blue-800"
                            disabled={phase() === 'saving'}
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
                                      handleRemoveHeader(index(), key);
                                      handleUpdateHeader(index(), e.currentTarget.value, value);
                                    }}
                                    class="w-2/5 border rounded px-1.5 py-0.5 bg-white font-mono"
                                    placeholder="Header"
                                    disabled={phase() === 'saving'}
                                  />
                                  <input
                                    type="text"
                                    value={value}
                                    onInput={(e) => handleUpdateHeader(index(), key, e.currentTarget.value)}
                                    class="flex-1 border rounded px-1.5 py-0.5 bg-white font-mono"
                                    placeholder="value"
                                    disabled={phase() === 'saving'}
                                  />
                                  <button
                                    onClick={() => handleRemoveHeader(index(), key)}
                                    class="text-red-400 hover:text-red-600 px-1"
                                    disabled={phase() === 'saving'}
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
                        缺少字段: {config.missing_fields.join(', ')}
                      </div>
                    </Show>
                  </div>
                )}
              </For>
            </div>

            <Show when={saveError()}>
              <div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {saveError()}
              </div>
            </Show>
            <Show when={saveSuccess()}>
              <div class="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700">
                保存成功！
              </div>
            </Show>
          </Show>
        </div>

        <div class="px-4 py-3 flex justify-between gap-2 border-t shrink-0">
          <div>
            <Show when={phase() === 'parsing'}>
              <button onClick={handleCancelParse} class="px-3 py-1.5 rounded-md border text-sm">
                取消
              </button>
            </Show>
          </div>
          <div class="flex gap-2">
            <Show when={phase() === 'sensitive_check'}>
              <button onClick={handleSensitiveBackToEdit} class="px-3 py-1.5 rounded-md border text-sm">
                返回编辑
              </button>
              <div class="flex gap-2">
                <button onClick={handleSensitiveSendAnyway} class="px-3 py-1.5 rounded-md border text-sm text-gray-500">
                  跳过，直接发送
                </button>
                <button onClick={handleSensitiveReplaceAll} class="px-4 py-1.5 rounded-md bg-amber-600 text-white text-sm">
                  一键全部替换
                </button>
              </div>
            </Show>
            <Show when={phase() === 'idle'}>
              <button onClick={props.onClose} class="px-3 py-1.5 rounded-md border text-sm">
                取消
              </button>
              <button
                onClick={handleParse}
                disabled={!rawText().trim()}
                data-testid="smart-paste-parse-btn"
                class="px-4 py-1.5 rounded-md bg-blue-700 text-white text-sm disabled:opacity-50"
              >
                AI 解析
              </button>
            </Show>
            <Show when={phase() === 'preview'}>
              <button onClick={() => { setPhase('idle'); setParseError(null); }} class="px-3 py-1.5 rounded-md border text-sm">
                重新解析
              </button>
              <button
                onClick={handleSave}
                disabled={results().length === 0}
                data-testid="smart-paste-save-btn"
                class="px-4 py-1.5 rounded-md bg-emerald-600 text-white text-sm disabled:opacity-50"
              >
                确认并保存
              </button>
            </Show>
            <Show when={phase() === 'preview' && parseError()}>
              <button onClick={handleRetry} class="px-3 py-1.5 rounded-md border text-sm">
                重试
              </button>
            </Show>
            <Show when={phase() === 'saving'}>
              <div class="flex items-center gap-2 text-sm text-gray-500">
                <div class="animate-spin h-4 w-4 border-2 border-gray-300 border-t-emerald-600 rounded-full" />
                保存中...
              </div>
            </Show>
          </div>
        </div>
      </div>
    </div>
  );
}
