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
    <div class="h-full flex flex-col space-y-6 max-w-5xl">
      <div class="flex justify-between items-center">
        <div>
          <h3 class="text-xl font-bold text-gray-800">Model Context Protocol (MCP)</h3>
          <p class="text-sm text-gray-500 mt-1">Extend Yue's capabilities with external tools and data sources.</p>
        </div>
        <div class="flex items-center gap-2">
          <button 
            onClick={props.reloadMcp} 
            class="p-2 rounded-xl border border-gray-100 bg-white hover:bg-gray-50 shadow-sm transition-all active:scale-95"
            title="Reload all servers"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <div class="relative">
            <button
              data-testid="mcp-add-menu-button"
              onClick={(e) => {
                e.stopPropagation();
                props.setShowAddMenu((v) => !v);
              }}
              class="px-4 py-2 rounded-xl bg-emerald-600 text-white font-bold flex items-center gap-2 shadow-lg shadow-emerald-100 hover:bg-emerald-700 transition-all active:scale-95"
            >
              <span>+ Add Server</span>
              <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 transition-transform ${props.showAddMenu() ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
            <Show when={props.showAddMenu()}>
              <div class="absolute right-0 mt-2 w-64 bg-white border border-gray-100 rounded-2xl shadow-2xl z-50 p-2 animate-in fade-in zoom-in-95 duration-200">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    props.setShowAddMenu(false);
                    props.setShowMarketplace(true);
                  }}
                  class="flex items-center gap-3 w-full text-left px-4 py-3 hover:bg-emerald-50 rounded-xl transition-all group"
                >
                  <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center group-hover:bg-emerald-200">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                    </svg>
                  </div>
                  <div>
                    <div class="text-sm font-bold text-gray-800">Marketplace</div>
                    <div class="text-[10px] text-gray-500">Discover pre-built servers</div>
                  </div>
                </button>
                <button
                  data-testid="mcp-add-manual-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    props.setShowAddMenu(false);
                    props.setShowManual(true);
                  }}
                  class="flex items-center gap-3 w-full text-left px-4 py-3 hover:bg-blue-50 rounded-xl transition-all group"
                >
                  <div class="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center group-hover:bg-blue-200">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                  </div>
                  <div>
                    <div class="text-sm font-bold text-gray-800">Manual Config</div>
                    <div class="text-[10px] text-gray-500">Add custom server JSON</div>
                  </div>
                </button>
              </div>
            </Show>
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <For each={props.mcpStatus()}>
          {(s) => (
            <div class={`bg-white rounded-2xl border transition-all ${props.expanded()[s.name] ? 'border-emerald-200 ring-4 ring-emerald-50' : 'border-gray-100 shadow-sm hover:shadow-md'}`}>
              <div class="px-6 py-4 flex items-center justify-between relative">
                <div class="flex items-center gap-4">
                  <button
                    onClick={() =>
                      props.setExpanded((prev) => ({ ...prev, [s.name]: !prev[s.name] }))
                    }
                    class={`p-1 rounded-lg hover:bg-gray-100 transition-transform ${props.expanded()[s.name] ? 'rotate-90 text-emerald-600' : 'text-gray-400'}`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <div class={`w-10 h-10 rounded-xl flex items-center justify-center font-bold transition-colors ${s.connected ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                    {s.name.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span
                        class="font-bold text-gray-800 cursor-pointer hover:text-emerald-600 transition-colors"
                        onMouseEnter={() => props.setHoveredServer(s.name)}
                        onMouseLeave={() => props.setHoveredServer(null)}
                      >
                        {s.name}
                      </span>
                      <Show when={s.connected}>
                        <span class="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                          Online
                        </span>
                      </Show>
                      <Show when={!s.connected}>
                        <span class="flex items-center gap-1 text-[10px] font-black uppercase tracking-widest text-rose-600 bg-rose-50 px-2 py-0.5 rounded-md">
                          <span class="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse"></span>
                          Offline
                        </span>
                        <button onClick={props.reloadMcp} class="text-[10px] font-bold text-blue-600 hover:underline">
                          Retry
                        </button>
                      </Show>
                    </div>
                    <div class="text-[10px] text-gray-400 mt-0.5 font-medium">
                      {props.mcpTools().filter((t) => t.server === s.name).length} tools available
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-4">
                  <label class="flex items-center gap-2 cursor-pointer group">
                    <span class={`text-[10px] font-bold uppercase tracking-widest transition-colors ${s.enabled ? 'text-emerald-600' : 'text-gray-400'}`}>
                      {s.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <div class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                         class:bg-emerald-600={s.enabled}
                         class:bg-gray-200={!s.enabled}
                    >
                      <input
                        type="checkbox"
                        class="sr-only"
                        checked={s.enabled}
                        onChange={(e) => props.toggleMcpEnabled(s.name, e.currentTarget.checked)}
                      />
                      <span class={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${s.enabled ? 'translate-x-6' : 'translate-x-1'}`} />
                    </div>
                  </label>
                  <button
                    onClick={() => props.deleteMcpServer(s.name)}
                    class="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                    title="Delete MCP Server"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <Show when={props.expanded()[s.name]}>
                <div class="px-16 pb-6 pt-2 animate-in slide-in-from-top-2 duration-200">
                  <div class="flex items-center gap-2 mb-4">
                    <span class="text-xs font-black uppercase tracking-widest text-gray-400">Available Tools</span>
                    <div class="h-px bg-gray-100 flex-1"></div>
                  </div>
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    <For each={props.mcpTools().filter((t) => t.server === s.name)}>
                      {(t) => (
                        <div class="p-3 bg-gray-50/50 rounded-xl border border-gray-100 hover:border-emerald-200 hover:bg-white transition-all group">
                          <div class="text-sm font-bold text-gray-800 group-hover:text-emerald-700 transition-colors">{t.name}</div>
                          <div class="text-[10px] text-gray-500 mt-1 line-clamp-2 leading-relaxed">{t.description}</div>
                        </div>
                      )}
                    </For>
                    <Show when={props.mcpTools().filter((t) => t.server === s.name).length === 0}>
                      <div class="col-span-full py-8 text-center bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                        <div class="text-sm font-medium text-gray-400">No tools discovered for this server.</div>
                      </div>
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
