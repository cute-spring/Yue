import { For, Show } from 'solid-js';
import { SmartDraft } from '../types';

interface SmartGenerateModalProps {
  showSmartGenerate: boolean;
  setShowSmartGenerate: (show: boolean) => void;
  smartDraft: () => SmartDraft | null;
  setSmartDraft: (draft: SmartDraft | null) => void;
  smartDescription: () => string;
  setSmartDescription: (desc: string) => void;
  smartUpdateTools: () => boolean;
  setSmartUpdateTools: (update: boolean) => void;
  smartIsGenerating: () => boolean;
  smartError: () => string | null;
  smartApplyName: () => boolean;
  setSmartApplyName: (apply: boolean) => void;
  smartApplyPrompt: () => boolean;
  setSmartApplyPrompt: (apply: boolean) => void;
  smartApplyTools: () => boolean;
  setSmartApplyTools: (apply: boolean) => void;
  smartPromptLint: () => string[];
  smartRiskSummary: () => { hasWrite: boolean; hasNetwork: boolean };
  runSmartGenerate: () => Promise<void>;
  applySmartDraft: () => void;
}

export function SmartGenerateModal(props: SmartGenerateModalProps) {
  return (
    <Show when={props.showSmartGenerate}>
      <div class="fixed inset-0 z-[200] flex items-center justify-center p-4">
        <button
          type="button"
          class="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
          onClick={() => (!props.smartIsGenerating() ? props.setShowSmartGenerate(false) : null)}
        />
        <div class="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
          <div class="px-6 py-4 bg-gradient-to-r from-emerald-50 to-sky-50 border-b flex items-center justify-between">
            <div>
              <div class="text-[10px] font-black text-emerald-700 uppercase tracking-[0.2em]">Smart Generate</div>
              <div class="text-sm font-bold text-gray-800 mt-1">用一句话生成 Agent 名称、Prompt 与工具推荐</div>
            </div>
            <button
              type="button"
              disabled={props.smartIsGenerating()}
              onClick={() => props.setShowSmartGenerate(false)}
              class={`p-2 rounded-lg transition-colors ${
                props.smartIsGenerating() ? 'text-gray-300' : 'text-gray-400 hover:text-gray-600 hover:bg-white/60'
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="p-6 space-y-4">
            <Show
              when={!!props.smartDraft()}
              fallback={
                <>
                  <div>
                    <label class="block text-sm font-semibold text-gray-700 mb-2">一句话描述</label>
                    <textarea
                      class="w-full border rounded-xl px-4 py-3 min-h-[120px] focus:ring-2 focus:ring-emerald-500 outline-none text-sm leading-relaxed"
                      value={props.smartDescription()}
                      onInput={e => props.setSmartDescription(e.currentTarget.value)}
                      placeholder="例如：我想要一个能审阅前端 PR、提出可执行改进建议的代码审查专家"
                      disabled={props.smartIsGenerating()}
                    />
                  </div>

                  <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                    <input
                      type="checkbox"
                      class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                      checked={props.smartUpdateTools()}
                      onChange={e => props.setSmartUpdateTools(e.currentTarget.checked)}
                      disabled={props.smartIsGenerating()}
                    />
                    同时更新工具勾选（会覆盖当前选择）
                  </label>
                </>
              }
            >
              <div class="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="text-[10px] font-black text-emerald-700 uppercase tracking-[0.2em]">Draft Preview</div>
                    <div class="text-sm font-bold text-gray-900 mt-1">{props.smartDraft()?.name || 'Untitled Agent'}</div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] font-bold text-emerald-700 bg-white/80 px-2 py-1 rounded-full border border-emerald-100">Review</span>
                  </div>
                </div>

                <div class="mt-4 grid grid-cols-1 gap-3">
                  <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                    <input
                      type="checkbox"
                      class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                      checked={props.smartApplyName()}
                      onChange={e => props.setSmartApplyName(e.currentTarget.checked)}
                    />
                    Apply name
                  </label>
                  <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                    <input
                      type="checkbox"
                      class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                      checked={props.smartApplyPrompt()}
                      onChange={e => props.setSmartApplyPrompt(e.currentTarget.checked)}
                    />
                    Apply system prompt
                  </label>
                  <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                    <input
                      type="checkbox"
                      class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                      checked={props.smartApplyTools()}
                      onChange={e => props.setSmartApplyTools(e.currentTarget.checked)}
                    />
                    Apply tool selection
                  </label>
                </div>

                <Show when={props.smartPromptLint().length > 0}>
                  <div class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                    <div class="font-bold">Prompt lint warning</div>
                    <div class="mt-1 opacity-90">Missing sections: {props.smartPromptLint().join(', ')}</div>
                  </div>
                </Show>

                <Show when={props.smartApplyTools() && (props.smartRiskSummary().hasWrite || props.smartRiskSummary().hasNetwork)}>
                  <div class="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-900">
                    <div class="font-bold">Tool risk warning</div>
                    <div class="mt-1 opacity-90">
                      {props.smartRiskSummary().hasWrite ? 'Includes WRITE-capable tools.' : ''}
                      {props.smartRiskSummary().hasWrite && props.smartRiskSummary().hasNetwork ? ' ' : ''}
                      {props.smartRiskSummary().hasNetwork ? 'Includes NETWORK tools.' : ''}
                    </div>
                  </div>
                </Show>

                <div class="mt-4">
                  <div class="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">System Prompt</div>
                  <div class="mt-2 bg-white border border-emerald-100 rounded-xl p-3 max-h-56 overflow-auto">
                    <pre class="whitespace-pre-wrap text-xs text-gray-700 leading-relaxed font-mono">
                      {props.smartDraft()?.system_prompt || ''}
                    </pre>
                  </div>
                </div>

                <div class="mt-4">
                  <div class="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">Recommended Tools</div>
                  <div class="mt-2 space-y-2">
                    <For each={(props.smartDraft()?.recommended_tools && props.smartDraft()!.recommended_tools!.length > 0) ? props.smartDraft()!.recommended_tools! : (props.smartDraft()?.enabled_tools || [])}>
                      {(tid) => {
                        const risk = props.smartDraft()?.tool_risks?.[tid] || 'unknown';
                        const reason = props.smartDraft()?.tool_reasons?.[tid];
                        const badge = () => {
                          if (risk === 'write') return 'bg-red-50 text-red-700 border-red-100';
                          if (risk === 'network') return 'bg-amber-50 text-amber-800 border-amber-100';
                          if (risk === 'read') return 'bg-emerald-50 text-emerald-800 border-emerald-100';
                          return 'bg-gray-100 text-gray-600 border-gray-200';
                        };
                        const label = () => {
                          if (risk === 'write') return 'WRITE';
                          if (risk === 'network') return 'NET';
                          if (risk === 'read') return 'READ';
                          return 'UNKNOWN';
                        };
                        return (
                          <div class="bg-white border border-gray-100 rounded-xl px-3 py-2">
                            <div class="flex items-center justify-between gap-3">
                              <div class="min-w-0">
                                <div class="text-xs font-semibold text-gray-900 truncate">{tid}</div>
                                <Show when={!!reason}>
                                  <div class="text-[11px] text-gray-600 mt-0.5">{reason}</div>
                                </Show>
                              </div>
                              <span class={`shrink-0 text-[10px] font-black px-2 py-1 rounded-full border ${badge()}`}>
                                {label()}
                              </span>
                            </div>
                          </div>
                        );
                      }}
                    </For>
                    <Show when={!((props.smartDraft()?.recommended_tools && props.smartDraft()!.recommended_tools!.length > 0) || (props.smartDraft()?.enabled_tools && props.smartDraft()!.enabled_tools!.length > 0))}>
                      <div class="text-sm text-gray-500 bg-white border border-dashed border-gray-200 rounded-xl px-4 py-3">
                        No tools recommended.
                      </div>
                    </Show>
                  </div>
                </div>
              </div>
            </Show>

            <Show when={!!props.smartError()}>
              <div class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                {props.smartError()}
              </div>
            </Show>
          </div>

          <div class="px-6 py-4 border-t bg-gray-50 flex items-center justify-end gap-3">
            <Show
              when={!!props.smartDraft()}
              fallback={
                <>
                  <button
                    type="button"
                    onClick={() => props.setShowSmartGenerate(false)}
                    disabled={props.smartIsGenerating()}
                    class={`px-5 py-2.5 rounded-lg font-medium transition-colors ${
                      props.smartIsGenerating() ? 'text-gray-300 bg-white' : 'text-gray-600 hover:bg-gray-100 bg-white'
                    }`}
                  >
                    取消
                  </button>
                  <button
                    type="button"
                    onClick={props.runSmartGenerate}
                    disabled={props.smartIsGenerating()}
                    class={`px-5 py-2.5 rounded-lg font-semibold shadow-md transition-all active:scale-95 ${
                      props.smartIsGenerating()
                        ? 'bg-emerald-200 text-white cursor-not-allowed'
                        : 'bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-700 hover:to-sky-700 text-white'
                    }`}
                  >
                    <span class="flex items-center gap-2">
                      <Show
                        when={props.smartIsGenerating()}
                        fallback={
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M11.3 1.046a1 1 0 10-2.6 0l-.27 2.68a1 1 0 00.997 1.099h1.146a1 1 0 00.997-1.099l-.27-2.68zM4.222 3.636a1 1 0 00-1.414 1.414l1.895 1.894a1 1 0 001.414-1.414L4.222 3.636zm11.556 0L13.883 5.53a1 1 0 001.414 1.414l1.895-1.894a1 1 0 10-1.414-1.414zM10 5a5 5 0 100 10A5 5 0 0010 5zM1 11.3a1 1 0 100-2.6l2.68-.27a1 1 0 011.099.997v1.146a1 1 0 01-1.099.997L1 11.3zm18 0l-2.68.27a1 1 0 00-1.099-.997H14.075a1 1 0 00-1.099.997L19 11.3z" />
                          </svg>
                        }
                      >
                        <div class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>
                      </Show>
                      {props.smartIsGenerating() ? '生成中…' : '生成草案'}
                    </span>
                  </button>
                </>
              }
            >
              <button
                type="button"
                onClick={() => props.setSmartDraft(null)}
                disabled={props.smartIsGenerating()}
                class={`px-5 py-2.5 rounded-lg font-medium transition-colors ${
                  props.smartIsGenerating() ? 'text-gray-300 bg-white' : 'text-gray-600 hover:bg-gray-100 bg-white'
                }`}
              >
                返回编辑
              </button>
              <button
                type="button"
                onClick={props.runSmartGenerate}
                disabled={props.smartIsGenerating()}
                class={`px-5 py-2.5 rounded-lg font-semibold transition-all active:scale-95 ${
                  props.smartIsGenerating()
                    ? 'bg-emerald-200 text-white cursor-not-allowed'
                    : 'bg-white text-emerald-700 border border-emerald-200 hover:bg-emerald-50'
                }`}
              >
                重新生成
              </button>
              <button
                type="button"
                onClick={props.applySmartDraft}
                disabled={props.smartIsGenerating()}
                class={`px-5 py-2.5 rounded-lg font-semibold shadow-md transition-all active:scale-95 ${
                  props.smartIsGenerating()
                    ? 'bg-emerald-200 text-white cursor-not-allowed'
                    : 'bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-700 hover:to-sky-700 text-white'
                }`}
              >
                应用到表单
              </button>
            </Show>
          </div>
        </div>
      </div>
    </Show>
  );
}
