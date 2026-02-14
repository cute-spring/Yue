import { For, Show } from 'solid-js';
import { McpTool } from '../types';

interface AgentFormProps {
  editingId: () => string | null;
  formName: () => string;
  setFormName: (name: string) => void;
  formProvider: () => string;
  setFormProvider: (provider: string) => void;
  formModel: () => string;
  setFormModel: (model: string) => void;
  formPrompt: () => string;
  setFormPrompt: (prompt: string) => void;
  formTools: () => string[];
  setFormTools: (tools: string[]) => void;
  availableTools: () => McpTool[];
  groupedTools: () => Record<string, McpTool[]>;
  expandedGroups: () => Record<string, boolean>;
  toggleGroupExpand: (server: string) => void;
  toggleTool: (toolId: string) => void;
  showLLMSelector: () => boolean;
  setShowLLMSelector: (show: boolean) => void;
  showAllModels: () => boolean;
  setShowAllModels: (show: boolean) => void;
  providers: () => any[];
  isRefreshingModels: () => boolean;
  setIsRefreshingModels: (refreshing: boolean) => void;
  loadProviders: (refresh?: boolean) => Promise<void>;
  supportsDocScope: () => boolean;
  formDocRootInput: () => string;
  setFormDocRootInput: (input: string) => void;
  addDocRoot: () => void;
  addDocRootValue: (value: string) => void;
  formDocRoots: () => string[];
  removeDocRoot: (root: string) => void;
  allowDocRoots: () => string[];
  denyDocRoots: () => string[];
  formDocFilePatternsText: () => string;
  setFormDocFilePatternsText: (text: string) => void;
  handleSubmit: (e: Event) => Promise<void>;
  setIsEditing: (editing: boolean) => void;
  openSmartGenerate: () => void;
}

export function AgentForm(props: AgentFormProps) {
  return (
    <div class="mb-8 bg-white border rounded-2xl shadow-lg overflow-hidden max-w-4xl mx-auto">
      <div class="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <h3 class="font-bold text-lg text-gray-800">{props.editingId() ? 'Edit Agent' : 'New Agent'}</h3>
          <button
            type="button"
            onClick={props.openSmartGenerate}
            class="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-700 hover:to-sky-700 shadow-sm transition-all active:scale-95"
          >
            Smart Generate
          </button>
        </div>
        <button onClick={() => props.setIsEditing(false)} class="text-gray-400 hover:text-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <form onSubmit={props.handleSubmit} class="p-6 space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-2">Name</label>
            <input 
              class="w-full border rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
              value={props.formName()}
              onInput={e => props.setFormName(e.currentTarget.value)}
              placeholder="e.g. Coding Assistant"
              required
            />
          </div>
          <div class="relative">
            <label class="block text-sm font-semibold text-gray-700 mb-2">Intelligence Model</label>
            <button 
              type="button"
              onClick={(e) => { 
                e.stopPropagation();
                props.setShowLLMSelector(!props.showLLMSelector());
              }}
              class="w-full flex items-center justify-between px-4 py-2.5 bg-white border border-gray-200 hover:border-emerald-500 rounded-lg transition-all active:scale-[0.98] shadow-sm group"
            >
              <div class="flex items-center gap-2.5 overflow-hidden">
                <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></div>
                <div class="flex flex-col items-start overflow-hidden">
                  <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider leading-none mb-0.5">{props.formProvider() || "Select Provider"}</span>
                  <span class="text-sm font-bold text-gray-800 truncate">{props.formModel() || "Select Model"}</span>
                </div>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 text-gray-400 transition-transform duration-300 ${props.showLLMSelector() ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            <Show when={props.showLLMSelector()}>
              <div class="absolute top-full left-0 mt-2 w-full min-w-[280px] bg-white border border-gray-100 rounded-xl shadow-2xl z-[100] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                <div class="p-3 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                  <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">{props.showAllModels() ? 'All Models' : 'Enabled Models'}</span>
                  <div class="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        props.setShowAllModels(!props.showAllModels());
                      }}
                      class="text-[10px] px-2 py-1 rounded-md border bg-white hover:bg-gray-50 text-gray-700 font-bold uppercase tracking-wider"
                    >
                      {props.showAllModels() ? 'Enabled' : 'All'}
                    </button>
                    <Show when={props.isRefreshingModels()}>
                      <div class="w-3 h-3 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
                    </Show>
                  </div>
                </div>
                <div class="p-2 max-h-72 overflow-y-auto space-y-1 scrollbar-thin">
                  <For each={props.providers().filter(p => {
                    const list = props.showAllModels() ? (p.models || []) : (p.available_models || []);
                    return Array.isArray(list) && list.length > 0;
                  })}>
                    {provider => (
                      <div class="space-y-1">
                        <div class="flex items-center justify-between gap-2 px-3 py-1.5 text-[9px] font-black text-emerald-600 uppercase bg-emerald-50 rounded-md tracking-widest">
                          <span>{provider.name}</span>
                          <button
                            type="button"
                            disabled={!provider.supports_model_refresh || props.isRefreshingModels()}
                            title={provider.supports_model_refresh ? 'Refresh models for this provider' : 'This provider does not support model refresh'}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (!provider.supports_model_refresh) return;
                              props.setIsRefreshingModels(true);
                              props.loadProviders(true).finally(() => props.setIsRefreshingModels(false));
                            }}
                            class={`text-[9px] px-2 py-1 rounded-md border font-black tracking-widest ${
                              provider.supports_model_refresh && !props.isRefreshingModels()
                                ? 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200'
                                : 'bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed'
                            }`}
                          >
                            Refresh
                          </button>
                        </div>
                        <For each={(props.showAllModels() ? provider.models : provider.available_models) || []}>
                          {model => (
                            <button
                              type="button"
                              onClick={() => {
                                props.setFormProvider(provider.name);
                                props.setFormModel(model);
                                props.setShowLLMSelector(false);
                              }}
                              class={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all flex items-center justify-between group ${
                                props.formModel() === model
                                  ? 'bg-emerald-600 text-white font-bold shadow-md shadow-emerald-200'
                                  : 'hover:bg-gray-50 text-gray-600 hover:text-gray-900'
                              }`}
                            >
                              <span class="truncate">{model}</span>
                              <Show when={props.formModel() === model}>
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                </svg>
                              </Show>
                            </button>
                          )}
                        </For>
                      </div>
                    )}
                  </For>
                </div>
              </div>
            </Show>
          </div>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-2">System Prompt</label>
          <textarea 
            class="w-full border rounded-lg px-3 py-2 h-32 focus:ring-2 focus:ring-emerald-500 outline-none font-mono text-sm"
            value={props.formPrompt()}
            onInput={e => props.setFormPrompt(e.currentTarget.value)}
            placeholder="You are a helpful assistant..."
            required
          />
        </div>

        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="block text-sm font-semibold text-gray-700">Enabled Tools (MCP)</label>
            <div class="flex gap-2">
              <button 
                type="button"
                onClick={() => props.setFormTools(props.availableTools().map(t => t.id))}
                class="text-[10px] uppercase tracking-wider font-bold text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-2 py-1 rounded"
              >
                Select All
              </button>
              <button 
                type="button"
                onClick={() => props.setFormTools([])}
                class="text-[10px] uppercase tracking-wider font-bold text-gray-500 hover:text-gray-600 bg-gray-100 px-2 py-1 rounded"
              >
                Clear All
              </button>
            </div>
          </div>
          <div class="space-y-6">
            <For each={Object.entries(props.groupedTools())}>
              {([server, tools]) => {
                const isExpanded = () => !!props.expandedGroups()[server];
                const selectedCountInGroup = () => tools.filter(t => props.formTools().includes(t.id)).length;
                
                return (
                  <div class="border rounded-xl overflow-hidden bg-white shadow-sm transition-all duration-200">
                    <div 
                      class="flex items-center justify-between px-4 py-3 bg-gray-50/80 cursor-pointer hover:bg-gray-100 transition-colors"
                      onClick={() => props.toggleGroupExpand(server)}
                    >
                      <div class="flex items-center gap-3">
                        <div class={`transition-transform duration-200 ${isExpanded() ? 'rotate-90' : ''}`}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                        <span class="text-xs font-bold text-gray-700 uppercase tracking-wider">{server}</span>
                        <Show when={selectedCountInGroup() > 0}>
                          <span class="bg-emerald-100 text-emerald-700 text-[10px] px-2 py-0.5 rounded-full font-bold">
                            {selectedCountInGroup()} / {tools.length}
                          </span>
                        </Show>
                      </div>
                      
                      <div class="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                        <button 
                          type="button"
                          onClick={() => {
                            const toolIds = tools.map(t => t.id);
                            const current = props.formTools();
                            const allSelected = toolIds.every(id => current.includes(id));
                            if (allSelected) {
                              props.setFormTools(current.filter(id => !toolIds.includes(id)));
                            } else {
                              const next = new Set([...current, ...toolIds]);
                              props.setFormTools(Array.from(next));
                            }
                          }}
                          class="text-[10px] font-bold text-emerald-600 hover:bg-emerald-100 px-2 py-1 rounded transition-colors"
                        >
                          {tools.every(t => props.formTools().includes(t.id)) ? 'Deselect All' : 'Select All'}
                        </button>
                      </div>
                    </div>

                    <Show when={isExpanded()}>
                      <div class="p-4 bg-white border-t border-gray-100 animate-in fade-in slide-in-from-top-2 duration-200">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <For each={tools}>
                            {tool => (
                              <label class={`flex items-start p-3 border rounded-lg cursor-pointer transition-all ${
                                (props.formTools().includes(tool.id) || props.formTools().includes(tool.name)) 
                                ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500' 
                                : 'hover:bg-gray-50 border-gray-200'
                              }`}>
                                <input 
                                  type="checkbox" 
                                  class="mt-1 mr-3 text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                                  checked={props.formTools().includes(tool.id) || props.formTools().includes(tool.name)}
                                  onChange={() => props.toggleTool(tool.id)}
                                />
                                <div class="min-w-0">
                                  <div class="font-medium text-sm text-gray-900 truncate">{tool.name}</div>
                                  <div class="text-xs text-gray-500 mt-0.5 line-clamp-1 leading-relaxed">{tool.description}</div>
                                </div>
                              </label>
                            )}
                          </For>
                        </div>
                      </div>
                    </Show>
                  </div>
                );
              }}
            </For>
            <Show when={props.availableTools().length === 0}>
              <div class="col-span-full text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-xl border border-dashed border-gray-300">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 011 1V4z" />
                </svg>
                No MCP tools found. Configure MCP servers in Settings.
              </div>
            </Show>
          </div>
        </div>

        <Show when={props.supportsDocScope()}>
          <div class="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4 space-y-3">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-[10px] font-black text-emerald-700 uppercase tracking-[0.2em]">Search Scope</div>
                <div class="text-xs text-emerald-700/80 mt-1">Applies to docs_search / docs_read via root_dir</div>
              </div>
              <div class="text-[10px] font-bold text-emerald-700 bg-white/80 px-2 py-1 rounded-full border border-emerald-100">Optional</div>
            </div>
            <div class="flex flex-col md:flex-row gap-2">
              <input
                class="flex-1 border rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-emerald-500 outline-none text-sm"
                value={props.formDocRootInput()}
                onInput={e => props.setFormDocRootInput(e.currentTarget.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    props.addDocRoot();
                  }
                }}
                placeholder="Absolute or project-relative path, e.g. docs or /Users/.../docs"
              />
              <button
                type="button"
                onClick={props.addDocRoot}
                class="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition-colors"
              >
                Add
              </button>
            </div>
            <Show
              when={props.formDocRoots().length > 0}
              fallback={
                <div class="text-xs text-emerald-700/70 bg-white/70 border border-emerald-100 rounded-lg px-3 py-2">
                  Add one or more directories to narrow retrieval. Invalid paths will be rejected by the server.
                </div>
              }
            >
              <div class="flex flex-wrap gap-2">
                <For each={props.formDocRoots()}>
                  {root => (
                    <div class="flex items-center gap-2 bg-white border border-emerald-100 text-emerald-800 text-xs px-3 py-1.5 rounded-full">
                      <span class="max-w-[240px] truncate">{root}</span>
                      <button
                        type="button"
                        class="text-emerald-500 hover:text-emerald-700"
                        onClick={() => props.removeDocRoot(root)}
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M10 8.586l3.536-3.535a1 1 0 111.414 1.414L11.414 10l3.536 3.535a1 1 0 01-1.414 1.414L10 11.414l-3.536 3.535a1 1 0 01-1.414-1.414L8.586 10 5.05 6.465A1 1 0 016.465 5.05L10 8.586z" clip-rule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  )}
                </For>
              </div>
            </Show>
            <Show when={props.allowDocRoots().length > 0}>
              <div class="space-y-2">
                <div class="text-[10px] font-bold text-emerald-700 uppercase tracking-[0.2em]">Allowed Roots</div>
                <div class="flex flex-wrap gap-2">
                  <For each={props.allowDocRoots()}>
                    {root => {
                      const selected = () => props.formDocRoots().includes(root);
                      return (
                        <button
                          type="button"
                          onClick={() => props.addDocRootValue(root)}
                          class={`text-[10px] px-2 py-1 rounded-full border transition-colors ${
                            selected()
                              ? 'bg-emerald-600 text-white border-emerald-600'
                              : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                          }`}
                        >
                          {root}
                        </button>
                      );
                    }}
                  </For>
                </div>
              </div>
            </Show>
            <Show when={props.denyDocRoots().length > 0}>
              <div class="space-y-2">
                <div class="text-[10px] font-bold text-red-600 uppercase tracking-[0.2em]">Denied Roots</div>
                <div class="flex flex-wrap gap-2">
                  <For each={props.denyDocRoots()}>
                    {root => (
                      <span class="text-[10px] px-2 py-1 rounded-full border bg-white text-red-600 border-red-200">
                        {root}
                      </span>
                    )}
                  </For>
                </div>
              </div>
            </Show>
          </div>
        </Show>

        <Show when={props.supportsDocScope()}>
          <div class="rounded-2xl border border-sky-100 bg-sky-50/60 p-4 space-y-3">
            <div class="flex items-center justify-between gap-3">
              <div>
                <div class="text-[10px] font-black text-sky-700 uppercase tracking-[0.2em]">File Type Allowlist</div>
                <div class="text-xs text-sky-700/80 mt-1">Include patterns like *.ts, src/**/*.py</div>
              </div>
              <div class="text-[10px] font-bold text-sky-700 bg-white/80 px-2 py-1 rounded-full border border-sky-100">Optional</div>
            </div>
            <textarea
              class="w-full border rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-sky-500 outline-none font-mono text-sm h-24"
              value={props.formDocFilePatternsText()}
              onInput={e => props.setFormDocFilePatternsText(e.currentTarget.value)}
              placeholder="*.py&#10;src/**/*.ts&#10;# One pattern per line"
            />
          </div>
        </Show>

        <div class="flex justify-end gap-3 pt-4">
          <button 
            type="button"
            onClick={() => props.setIsEditing(false)}
            class="px-6 py-2.5 rounded-xl font-medium text-gray-600 hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button 
            type="submit"
            class="px-8 py-2.5 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-md shadow-emerald-100 transition-all active:scale-95"
          >
            {props.editingId() ? 'Save Changes' : 'Create Agent'}
          </button>
        </div>
      </form>
    </div>
  );
}
