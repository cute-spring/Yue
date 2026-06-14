import type { Accessor, Setter } from 'solid-js';
import type { LlmForm } from '../../types';

type LlmRuntimeSettingsSectionProps = {
  llmForm: Accessor<LlmForm>;
  setLlmForm: Setter<LlmForm>;
  onSave: () => void;
};

export function LlmRuntimeSettingsSection(props: LlmRuntimeSettingsSectionProps) {
  return (
    <section class="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]">
        <div>
          <h4 class="mb-3 flex items-center gap-2 text-lg font-bold text-slate-900">
          <span class="p-1 bg-emerald-100 text-emerald-600 rounded">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1z"
                clip-rule="evenodd"
              />
            </svg>
          </span>
          Global Network & Timeout
          </h4>
          <div class="grid grid-cols-1 gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2 2xl:grid-cols-4">
            <div>
              <div class="mb-1 text-xs font-bold text-slate-600">PROXY_URL</div>
            <input
                class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
              placeholder="http://127.0.0.1:7890"
              value={props.llmForm().proxy_url || ''}
              onInput={(e) => props.setLlmForm({ ...props.llmForm(), proxy_url: e.currentTarget.value })}
            />
              <div class="mt-1 text-[10px] text-slate-400">HTTP/HTTPS proxy for LLM requests</div>
            </div>
            <div>
              <div class="mb-1 text-xs font-bold text-slate-600">NO_PROXY</div>
            <input
                class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
              placeholder="e.g. *.openai.azure.com"
              value={props.llmForm().no_proxy || ''}
              onInput={(e) => props.setLlmForm({ ...props.llmForm(), no_proxy: e.currentTarget.value })}
            />
              <div class="mt-1 text-[10px] text-slate-400">Bypass list (loopback included by default)</div>
            </div>
            <div>
              <div class="mb-1 text-xs font-bold text-slate-600">SSL_CERT_FILE</div>
            <input
                class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
              placeholder="/path/to/cert.pem"
              value={props.llmForm().ssl_cert_file || ''}
              onInput={(e) => props.setLlmForm({ ...props.llmForm(), ssl_cert_file: e.currentTarget.value })}
            />
              <div class="mt-1 text-[10px] text-slate-400">Custom CA certificate bundle path</div>
            </div>
            <div>
              <div class="mb-1 text-xs font-bold text-slate-600">REQUEST_TIMEOUT (s)</div>
            <input
              type="number"
                class="w-full rounded-xl border border-slate-300 bg-white p-2.5"
              placeholder="60"
              value={props.llmForm().llm_request_timeout || ''}
              onInput={(e) => props.setLlmForm({ ...props.llmForm(), llm_request_timeout: e.currentTarget.value })}
            />
              <div class="mt-1 text-[10px] text-slate-400">Timeout in seconds (default: 60)</div>
            </div>
          </div>
        </div>

        <div>
          <h4 class="mb-3 flex items-center gap-2 text-lg font-bold text-slate-900">
          <span class="p-1 bg-blue-100 text-blue-600 rounded">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10 2a1 1 0 00-1 1v1.07A7.002 7.002 0 003 10a7 7 0 0014 0 7.002 7.002 0 00-6-6.93V3a1 1 0 00-1-1z" />
            </svg>
          </span>
          Session Meta Behavior
          </h4>
          <div class="rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <label class="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              checked={Boolean(props.llmForm().meta_use_runtime_model_for_title)}
              onChange={(e) =>
                props.setLlmForm({ ...props.llmForm(), meta_use_runtime_model_for_title: e.currentTarget.checked })
              }
            />
              <div>
                <div class="text-sm font-semibold text-slate-800">meta_use_runtime_model_for_title</div>
                <div class="mt-1 text-xs text-slate-600">
                开启后，标题生成会优先使用当前会话运行时所选模型；关闭后，标题与摘要都优先走 Meta 固定模型配置。
                </div>
              </div>
            </label>
          </div>
        </div>
      </div>

      <div class="pt-5 flex justify-end">
        <button
          onClick={props.onSave}
          class="rounded-xl bg-emerald-600 px-10 py-3 font-bold text-white shadow-lg transition-all hover:bg-emerald-700 hover:shadow-emerald-200"
        >
          Save All LLM Settings
        </button>
      </div>
    </section>
  );
}
