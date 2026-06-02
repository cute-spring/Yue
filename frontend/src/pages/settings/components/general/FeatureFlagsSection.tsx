import type { Accessor, Setter } from 'solid-js';
import type { FeatureFlags } from '../../types';

type FeatureFlagsSectionProps = {
  featureFlags: Accessor<FeatureFlags>;
  setFeatureFlags: Setter<FeatureFlags>;
  onSave: () => void | Promise<void>;
};

export function FeatureFlagsSection(props: FeatureFlagsSectionProps) {
  return (
    <div class="pt-6 border-t">
      <h3 class="text-xl font-semibold border-b pb-2">Feature Flags</h3>
      <p class="text-sm text-gray-500 mt-2">
        Toggle internal feature controls without editing config files manually.
      </p>
      <div class="rounded-lg border border-gray-200 bg-gray-50/80 p-4 space-y-4 mt-4">
        <label class="flex items-start justify-between gap-4">
          <span class="space-y-1">
            <span class="block text-sm font-medium text-gray-700">Smart Paste AI 解析</span>
            <span class="block text-xs text-gray-500">
              开启后，粘贴自然语言描述或半结构化文本时，自动调用 AI 兜底解析 MCP 配置。
            </span>
          </span>
          <input
            type="checkbox"
            data-testid="settings-feature-flag-mcp-smart-paste"
            class="mt-1 h-4 w-4 accent-emerald-600"
            checked={props.featureFlags().mcp_smart_paste_enabled}
            onChange={(e) =>
              props.setFeatureFlags((current) => ({
                ...current,
                mcp_smart_paste_enabled: e.currentTarget.checked,
              }))
            }
          />
        </label>
        <label class="flex items-start justify-between gap-4">
          <span class="space-y-1">
            <span class="block text-sm font-medium text-gray-700">Trace Inspector UI</span>
            <span class="block text-xs text-gray-500">
              Shows the read-only trace drawer in chat so you can inspect historical request and tool call data.
            </span>
          </span>
          <input
            type="checkbox"
            data-testid="settings-feature-flag-chat-trace-ui"
            class="mt-1 h-4 w-4 accent-emerald-600"
            checked={props.featureFlags().chat_trace_ui_enabled}
            onChange={(e) =>
              props.setFeatureFlags((current) => ({
                ...current,
                chat_trace_ui_enabled: e.currentTarget.checked,
              }))
            }
          />
        </label>
        <label class="flex items-start justify-between gap-4">
          <span class="space-y-1">
            <span class="block text-sm font-medium text-gray-700">Raw Trace Access</span>
            <span class="block text-xs text-gray-500">
              Allows the trace drawer to switch into raw payload mode for deeper debugging.
            </span>
          </span>
          <input
            type="checkbox"
            data-testid="settings-feature-flag-chat-trace-raw"
            class="mt-1 h-4 w-4 accent-emerald-600"
            checked={props.featureFlags().chat_trace_raw_enabled}
            onChange={(e) =>
              props.setFeatureFlags((current) => ({
                ...current,
                chat_trace_raw_enabled: e.currentTarget.checked,
              }))
            }
          />
        </label>
        <div class="flex items-center justify-between gap-3">
          <div class="text-xs text-gray-500">
            Smart Paste: {props.featureFlags().mcp_smart_paste_enabled ? 'On' : 'Off'} • Trace UI: {props.featureFlags().chat_trace_ui_enabled ? 'On' : 'Off'} • Raw: {props.featureFlags().chat_trace_raw_enabled ? 'On' : 'Off'}
          </div>
          <button
            type="button"
            data-testid="settings-save-feature-flags"
            onClick={() => { void props.onSave(); }}
            class="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-md"
          >
            Save Feature Flags
          </button>
        </div>
      </div>
    </div>
  );
}
