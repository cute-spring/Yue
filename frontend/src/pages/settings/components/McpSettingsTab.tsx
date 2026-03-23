import type { Accessor, Setter } from 'solid-js';
import { For, Show } from 'solid-js';
import type { McpStatus, McpTool } from '../types';
import { McpManualModal } from './modals/McpManualModal';
import { McpMarketplaceModal } from './modals/McpMarketplaceModal';
import { McpRawConfigModal } from './modals/McpRawConfigModal';

type McpSettingsTabProps = {
  mcpStatus: Accessor<McpStatus[]>;
  mcpTools: Accessor<McpTool[]>;
  expanded: Accessor<Record<string, boolean>>;
  setExpanded: Setter<Record<string, boolean>>;
  hoveredServer: Accessor<string | null>;
  setHoveredServer: Setter<string | null>;
  showAddMenu: Accessor<boolean>;
  setShowAddMenu: Setter<boolean>;
  showManual: Accessor<boolean>;
  setShowManual: Setter<boolean>;
  manualText: Accessor<string>;
  setManualText: Setter<string>;
  showRaw: Accessor<boolean>;
  setShowRaw: Setter<boolean>;
  showMarketplace: Accessor<boolean>;
  setShowMarketplace: Setter<boolean>;
  mcpConfig: Accessor<string>;
  setMcpConfig: Setter<string>;
  reloadMcp: () => void;
  toggleMcpEnabled: (serverName: string, enabled: boolean) => void;
  deleteMcpServer: (serverName: string) => void;
  confirmManual: () => void;
  saveMcp: () => Promise<void>;
};

export function McpSettingsTab(props: McpSettingsTabProps) {
  return (
    <div class="h-full flex flex-col space-y-4">
      <div class="flex justify-between items-center">
        <div class="flex items-center gap-2">
          <h3 class="text-xl font-semibold">MCP</h3>
        </div>
        <div class="flex items-center gap-2">
          <button onClick={props.reloadMcp} class="p-2 rounded-md border bg-white hover:bg-gray-50">
            ↻
          </button>
          <div class="relative">
            <button
              data-testid="mcp-add-menu-button"
              onClick={(e) => {
                e.stopPropagation();
                props.setShowAddMenu((v) => !v);
              }}
              class="px-3 py-1.5 rounded-md bg-blue-700 text-white flex items-center gap-2"
            >
              <span>+ Add</span>
              <span>▾</span>
            </button>
            <Show when={props.showAddMenu()}>
              <div class="absolute right-0 mt-2 w-56 bg-white border rounded-lg shadow-xl z-50">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    props.setShowAddMenu(false);
                    props.setShowMarketplace(true);
                  }}
                  class="block w-full text-left px-3 py-2 hover:bg-gray-50"
                >
                  Add from Marketplace
                </button>
                <button
                  data-testid="mcp-add-manual-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    props.setShowAddMenu(false);
                    props.setShowManual(true);
                  }}
                  class="block w-full text-left px-3 py-2 hover:bg-gray-50"
                >
                  Add Manually
                </button>
              </div>
            </Show>
          </div>
        </div>
      </div>
      <div class="border rounded-xl bg-white">
        <For each={props.mcpStatus()}>
          {(s) => (
            <div class="border-b last:border-b-0">
              <div class="px-4 py-3 flex items-center justify-between relative">
                <div class="flex items-center gap-3">
                  <button
                    onClick={() =>
                      props.setExpanded((prev) => ({ ...prev, [s.name]: !prev[s.name] }))
                    }
                    class="text-gray-500"
                  >
                    ▸
                  </button>
                  <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center font-bold text-emerald-700">
                    {s.name.charAt(0).toUpperCase()}
                  </div>
                  <div class="flex items-center gap-2">
                    <span
                      class="font-semibold underline cursor-pointer"
                      onMouseEnter={() => props.setHoveredServer(s.name)}
                      onMouseLeave={() => props.setHoveredServer(null)}
                    >
                      {s.name}
                    </span>
                    <Show when={s.connected}>
                      <span class="text-emerald-600">✓</span>
                    </Show>
                    <Show when={!s.connected}>
                      <span class="text-red-600">Failed to start</span>
                      <button onClick={props.reloadMcp} class="text-blue-600 underline">
                        Retry
                      </button>
                    </Show>
                  </div>
                  <Show when={props.hoveredServer() === s.name}>
                    <div class="absolute left-20 top-full mt-2 bg-white border rounded-xl shadow-xl w-[420px] z-50">
                      <div class="px-4 py-3 border-b">
                        <div class="font-semibold">{s.name} • From TRAE</div>
                        <div class="text-xs text-gray-500">
                          Update on {new Date().toISOString().slice(0, 10)}
                        </div>
                        <div class="text-xs text-gray-600 mt-1">
                          MCP Server — Tools for this integration
                        </div>
                      </div>
                      <div class="py-2">
                        <For each={props.mcpTools().filter((t) => t.server === s.name).slice(0, 2)}>
                          {(t) => (
                            <div class="px-4 py-2">
                              <div class="text-sm font-medium">{t.name}</div>
                              <div class="text-xs text-gray-500">
                                {t.description?.length ? t.description : 'Tool provided by this server.'}
                              </div>
                            </div>
                          )}
                        </For>
                        <Show when={props.mcpTools().filter((t) => t.server === s.name).length === 0}>
                          <div class="px-4 py-3 text-xs text-gray-500">No tools</div>
                        </Show>
                      </div>
                    </div>
                  </Show>
                </div>
                <div class="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={s.enabled}
                    onChange={(e) => props.toggleMcpEnabled(s.name, e.currentTarget.checked)}
                    class="w-4 h-4 text-emerald-600 rounded border-gray-300 focus:ring-emerald-500"
                  />
                  <button
                    onClick={() => props.deleteMcpServer(s.name)}
                    class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete MCP Server"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
              <Show when={props.expanded()[s.name]}>
                <div class="px-12 pb-4">
                  <div class="text-xs text-gray-500 mb-2">Tools</div>
                  <div class="grid md:grid-cols-2 gap-2">
                    <For each={props.mcpTools().filter((t) => t.server === s.name)}>
                      {(t) => (
                        <div class="p-2 border rounded-lg">
                          <div class="text-sm font-medium">{t.name}</div>
                          <div class="text-xs text-gray-500">{t.description}</div>
                        </div>
                      )}
                    </For>
                    <Show when={props.mcpTools().filter((t) => t.server === s.name).length === 0}>
                      <div class="text-xs text-gray-500">No tools</div>
                    </Show>
                  </div>
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>
      <Show when={props.showManual()}>
        <McpManualModal
          manualText={props.manualText()}
          setManualText={(value) => props.setManualText(value)}
          onClose={() => props.setShowManual(false)}
          onConfirm={props.confirmManual}
        />
      </Show>
      <Show when={props.showMarketplace()}>
        <McpMarketplaceModal onClose={() => props.setShowMarketplace(false)} />
      </Show>
      <Show when={props.showRaw()}>
        <McpRawConfigModal
          mcpConfig={props.mcpConfig()}
          setMcpConfig={(value) => props.setMcpConfig(value)}
          onClose={() => props.setShowRaw(false)}
          onConfirm={async () => {
            await props.saveMcp();
            props.setShowRaw(false);
          }}
        />
      </Show>
    </div>
  );
}
