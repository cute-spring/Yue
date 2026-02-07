import { createSignal, For, onMount, Show, onCleanup } from 'solid-js';

type Agent = {
  id: string;
  name: string;
  system_prompt: string;
  provider: string;
  model: string;
  enabled_tools: string[];
  doc_roots?: string[];
};

type McpTool = {
  id: string;
  name: string;
  description: string;
  server: string;
};

type SmartDraft = {
  name?: string;
  system_prompt?: string;
  enabled_tools?: string[];
  recommended_tools?: string[];
  tool_reasons?: Record<string, string>;
  tool_risks?: Record<string, string>;
};

export default function Agents() {
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [availableTools, setAvailableTools] = createSignal<McpTool[]>([]);

  // Grouped tools derived from availableTools
  const groupedTools = () => {
    const tools = availableTools();
    const groups: Record<string, McpTool[]> = {};
    tools.forEach(tool => {
      const server = tool.server || 'Unknown';
      if (!groups[server]) groups[server] = [];
      groups[server].push(tool);
    });
    return groups;
  };
  
  // UI State
  const [isEditing, setIsEditing] = createSignal(false);
  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [providers, setProviders] = createSignal<any[]>([]);
  const [showLLMSelector, setShowLLMSelector] = createSignal(false);
  const [isRefreshingModels, setIsRefreshingModels] = createSignal(false);
  const [showSmartGenerate, setShowSmartGenerate] = createSignal(false);
  const [smartDescription, setSmartDescription] = createSignal("");
  const [smartUpdateTools, setSmartUpdateTools] = createSignal(true);
  const [smartIsGenerating, setSmartIsGenerating] = createSignal(false);
  const [smartError, setSmartError] = createSignal<string | null>(null);
  const [smartDraft, setSmartDraft] = createSignal<SmartDraft | null>(null);
  const [smartApplyName, setSmartApplyName] = createSignal(true);
  const [smartApplyPrompt, setSmartApplyPrompt] = createSignal(true);
  const [smartApplyTools, setSmartApplyTools] = createSignal(true);
  
  // Form state
  const [formName, setFormName] = createSignal("");
  const [formPrompt, setFormPrompt] = createSignal("");
  const [formProvider, setFormProvider] = createSignal("openai");
  const [formModel, setFormModel] = createSignal("gpt-4o");
  const [formTools, setFormTools] = createSignal<string[]>([]);
  const [formDocRoots, setFormDocRoots] = createSignal<string[]>([]);
  const [formDocRootInput, setFormDocRootInput] = createSignal("");
  const [expandedGroups, setExpandedGroups] = createSignal<Record<string, boolean>>({});
  const [allowDocRoots, setAllowDocRoots] = createSignal<string[]>([]);
  const [denyDocRoots, setDenyDocRoots] = createSignal<string[]>([]);

  const toggleGroupExpand = (server: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [server]: !prev[server]
    }));
  };

  const loadAgents = async () => {
    const res = await fetch('/api/agents/');
    setAgents(await res.json());
  };

  const loadProviders = async (refresh = false) => {
    try {
      const res = await fetch(`/api/models/providers${refresh ? '?refresh=1' : ''}`);
      const data = await res.json();
      setProviders(data);
    } catch (e) {
      console.error("Failed to load providers", e);
    }
  };

  const loadTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      setAvailableTools(await res.json());
    } catch (e) {
      console.error("Failed to load tools", e);
    }
  };

  const loadDocAccess = async () => {
    try {
      const res = await fetch('/api/config/doc_access');
      const data = await res.json();
      setAllowDocRoots(Array.isArray(data?.allow_roots) ? data.allow_roots : []);
      setDenyDocRoots(Array.isArray(data?.deny_roots) ? data.deny_roots : []);
    } catch (e) {
      console.error("Failed to load doc access config", e);
    }
  };

  onMount(async () => {
    loadAgents();
    loadTools();
    loadProviders();
    loadDocAccess();

    const handleClickOutside = () => {
      if (showLLMSelector()) {
        setShowLLMSelector(false);
      }
    };
    window.addEventListener('click', handleClickOutside);
    onCleanup(() => window.removeEventListener('click', handleClickOutside));
  });

  const openCreate = () => {
    setFormName("");
    setFormPrompt("");
    setFormProvider("openai");
    setFormModel("gpt-4o");
    setFormTools([]);
    setFormDocRoots([]);
    setFormDocRootInput("");
    setEditingId(null);
    setIsEditing(true);
  };

  const openEdit = (agent: Agent) => {
    setFormName(agent.name);
    setFormPrompt(agent.system_prompt);
    setFormProvider(agent.provider);
    setFormModel(agent.model);
    setFormTools(agent.enabled_tools);
    setFormDocRoots(agent.doc_roots || []);
    setFormDocRootInput("");
    setEditingId(agent.id);
    setIsEditing(true);
  };

  const openSmartGenerate = () => {
    setSmartError(null);
    setSmartIsGenerating(false);
    setSmartUpdateTools(true);
    setSmartDescription("");
    setSmartDraft(null);
    setSmartApplyName(true);
    setSmartApplyPrompt(true);
    setSmartApplyTools(true);
    setShowSmartGenerate(true);
  };

  const applySmartDraft = () => {
    const draft = smartDraft();
    if (!draft) return;
    if (smartApplyName() && draft.name) setFormName(draft.name);
    if (smartApplyPrompt() && draft.system_prompt) setFormPrompt(draft.system_prompt);
    if (smartApplyTools()) {
      const tools = Array.isArray(draft.recommended_tools) && draft.recommended_tools.length > 0
        ? draft.recommended_tools
        : (Array.isArray(draft.enabled_tools) ? draft.enabled_tools : []);
      if (tools.length > 0) setFormTools(tools);
    }
    setShowSmartGenerate(false);
    setSmartDraft(null);
  };

  const smartPromptLint = () => {
    const prompt = (smartDraft()?.system_prompt || '').toLowerCase();
    const missing: string[] = [];
    const hasRole = prompt.includes('role') || prompt.includes('你是') || prompt.includes('角色');
    const hasBoundary = prompt.includes('boundary') || prompt.includes('scope') || prompt.includes('边界') || prompt.includes('范围');
    const hasWorkflow = prompt.includes('workflow') || prompt.includes('step') || prompt.includes('流程') || prompt.includes('步骤');
    const hasOutput = prompt.includes('output') || prompt.includes('format') || prompt.includes('输出') || prompt.includes('格式');
    const hasProhibit = prompt.includes('prohibit') || prompt.includes('forbid') || prompt.includes('禁忌') || prompt.includes('不要') || prompt.includes('禁止');
    if (!hasRole) missing.push('Role');
    if (!hasBoundary) missing.push('Scope');
    if (!hasWorkflow) missing.push('Workflow');
    if (!hasOutput) missing.push('Output format');
    if (!hasProhibit) missing.push('Prohibitions');
    return missing;
  };

  const smartRiskSummary = () => {
    const draft = smartDraft();
    const tools = (draft?.recommended_tools && draft.recommended_tools.length > 0)
      ? draft.recommended_tools
      : (draft?.enabled_tools || []);
    const risks = draft?.tool_risks || {};
    const hasWrite = tools.some(t => risks[t] === 'write');
    const hasNetwork = tools.some(t => risks[t] === 'network');
    return { hasWrite, hasNetwork };
  };

  const runSmartGenerate = async () => {
    const desc = smartDescription().trim();
    if (!desc) {
      setSmartError("请先输入一句话描述");
      return;
    }
    setSmartError(null);
    setSmartIsGenerating(true);
    try {
      const res = await fetch('/api/agents/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: desc,
          provider: formProvider(),
          model: formModel(),
          existing_tools: formTools(),
          update_tools: smartUpdateTools()
        })
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data?.detail || 'Smart Generate failed';
        throw new Error(detail);
      }
      setSmartDraft(data);
      setSmartApplyTools(smartUpdateTools());
    } catch (e: any) {
      setSmartError(e?.message || String(e));
    } finally {
      setSmartIsGenerating(false);
    }
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    
    const payload = {
      name: formName(),
      system_prompt: formPrompt(),
      provider: formProvider(),
      model: formModel(),
      enabled_tools: formTools(),
      doc_roots: formDocRoots()
    };

    if (editingId()) {
      await fetch(`/api/agents/${editingId()}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      await fetch('/api/agents/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }
    
    setIsEditing(false);
    loadAgents();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete agent?")) return;
    await fetch(`/api/agents/${id}`, { method: 'DELETE' });
    loadAgents();
  };

  const toggleTool = (toolId: string) => {
    const current = formTools();
    const legacyName = toolId.includes(":") ? toolId.split(":").slice(1).join(":") : toolId;
    const hasId = current.includes(toolId);
    const hasLegacy = current.includes(legacyName);
    if (hasId || hasLegacy) {
      setFormTools(current.filter(t => t !== toolId && t !== legacyName));
    } else {
      setFormTools([...current, toolId]);
    }
  };

  const supportsDocScope = () => {
    return formTools().some(t => t.includes("docs_search_markdown_dir") || t.includes("docs_read_markdown_dir"));
  };

  const addDocRoot = () => {
    addDocRootValue(formDocRootInput());
    setFormDocRootInput("");
  };

  const addDocRootValue = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    if (formDocRoots().includes(trimmed)) {
      return;
    }
    setFormDocRoots([...formDocRoots(), trimmed]);
  };

  const removeDocRoot = (root: string) => {
    setFormDocRoots(formDocRoots().filter(r => r !== root));
  };

  return (
    <div class="p-6 h-full overflow-y-auto bg-gray-50">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-800">Agents</h2>
          <p class="text-gray-500 text-sm">Manage your AI assistants and their capabilities</p>
        </div>
        <button 
          onClick={openCreate}
          class="bg-emerald-600 text-white px-4 py-2 rounded-xl font-medium hover:bg-emerald-700 transition-colors shadow-sm flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Create Agent
        </button>
      </div>

      <Show when={isEditing()}>
        <>
          <Show when={showSmartGenerate()}>
            <div class="fixed inset-0 z-[200] flex items-center justify-center p-4">
              <button
                type="button"
                class="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
                onClick={() => (!smartIsGenerating() ? setShowSmartGenerate(false) : null)}
              />
              <div class="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
                <div class="px-6 py-4 bg-gradient-to-r from-emerald-50 to-sky-50 border-b flex items-center justify-between">
                  <div>
                    <div class="text-[10px] font-black text-emerald-700 uppercase tracking-[0.2em]">Smart Generate</div>
                    <div class="text-sm font-bold text-gray-800 mt-1">用一句话生成 Agent 名称、Prompt 与工具推荐</div>
                  </div>
                  <button
                    type="button"
                    disabled={smartIsGenerating()}
                    onClick={() => setShowSmartGenerate(false)}
                    class={`p-2 rounded-lg transition-colors ${
                      smartIsGenerating() ? 'text-gray-300' : 'text-gray-400 hover:text-gray-600 hover:bg-white/60'
                    }`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <div class="p-6 space-y-4">
                  <Show
                    when={!!smartDraft()}
                    fallback={
                      <>
                        <div>
                          <label class="block text-sm font-semibold text-gray-700 mb-2">一句话描述</label>
                          <textarea
                            class="w-full border rounded-xl px-4 py-3 min-h-[120px] focus:ring-2 focus:ring-emerald-500 outline-none text-sm leading-relaxed"
                            value={smartDescription()}
                            onInput={e => setSmartDescription(e.currentTarget.value)}
                            placeholder="例如：我想要一个能审阅前端 PR、提出可执行改进建议的代码审查专家"
                            disabled={smartIsGenerating()}
                          />
                        </div>

                        <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                          <input
                            type="checkbox"
                            class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                            checked={smartUpdateTools()}
                            onChange={e => setSmartUpdateTools(e.currentTarget.checked)}
                            disabled={smartIsGenerating()}
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
                          <div class="text-sm font-bold text-gray-900 mt-1">{smartDraft()?.name || 'Untitled Agent'}</div>
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
                            checked={smartApplyName()}
                            onChange={e => setSmartApplyName(e.currentTarget.checked)}
                          />
                          Apply name
                        </label>
                        <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                          <input
                            type="checkbox"
                            class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                            checked={smartApplyPrompt()}
                            onChange={e => setSmartApplyPrompt(e.currentTarget.checked)}
                          />
                          Apply system prompt
                        </label>
                        <label class="flex items-center gap-2 text-sm text-gray-700 select-none">
                          <input
                            type="checkbox"
                            class="text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                            checked={smartApplyTools()}
                            onChange={e => setSmartApplyTools(e.currentTarget.checked)}
                          />
                          Apply tool selection
                        </label>
                      </div>

                      <Show when={smartPromptLint().length > 0}>
                        <div class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                          <div class="font-bold">Prompt lint warning</div>
                          <div class="mt-1 opacity-90">Missing sections: {smartPromptLint().join(', ')}</div>
                        </div>
                      </Show>

                      <Show when={smartApplyTools() && (smartRiskSummary().hasWrite || smartRiskSummary().hasNetwork)}>
                        <div class="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-900">
                          <div class="font-bold">Tool risk warning</div>
                          <div class="mt-1 opacity-90">
                            {smartRiskSummary().hasWrite ? 'Includes WRITE-capable tools.' : ''}
                            {smartRiskSummary().hasWrite && smartRiskSummary().hasNetwork ? ' ' : ''}
                            {smartRiskSummary().hasNetwork ? 'Includes NETWORK tools.' : ''}
                          </div>
                        </div>
                      </Show>

                      <div class="mt-4">
                        <div class="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">System Prompt</div>
                        <div class="mt-2 bg-white border border-emerald-100 rounded-xl p-3 max-h-56 overflow-auto">
                          <pre class="whitespace-pre-wrap text-xs text-gray-700 leading-relaxed font-mono">
                            {smartDraft()?.system_prompt || ''}
                          </pre>
                        </div>
                      </div>

                      <div class="mt-4">
                        <div class="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em]">Recommended Tools</div>
                        <div class="mt-2 space-y-2">
                          <For each={(smartDraft()?.recommended_tools && smartDraft()!.recommended_tools!.length > 0) ? smartDraft()!.recommended_tools! : (smartDraft()?.enabled_tools || [])}>
                            {(tid) => {
                              const risk = smartDraft()?.tool_risks?.[tid] || 'unknown';
                              const reason = smartDraft()?.tool_reasons?.[tid];
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
                          <Show when={!((smartDraft()?.recommended_tools && smartDraft()!.recommended_tools!.length > 0) || (smartDraft()?.enabled_tools && smartDraft()!.enabled_tools!.length > 0))}>
                            <div class="text-sm text-gray-500 bg-white border border-dashed border-gray-200 rounded-xl px-4 py-3">
                              No tools recommended.
                            </div>
                          </Show>
                        </div>
                      </div>
                    </div>
                  </Show>

                  <Show when={!!smartError()}>
                    <div class="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                      {smartError()}
                    </div>
                  </Show>
                </div>

                <div class="px-6 py-4 border-t bg-gray-50 flex items-center justify-end gap-3">
                  <Show
                    when={!!smartDraft()}
                    fallback={
                      <>
                        <button
                          type="button"
                          onClick={() => setShowSmartGenerate(false)}
                          disabled={smartIsGenerating()}
                          class={`px-5 py-2.5 rounded-lg font-medium transition-colors ${
                            smartIsGenerating() ? 'text-gray-300 bg-white' : 'text-gray-600 hover:bg-gray-100 bg-white'
                          }`}
                        >
                          取消
                        </button>
                        <button
                          type="button"
                          onClick={runSmartGenerate}
                          disabled={smartIsGenerating()}
                          class={`px-5 py-2.5 rounded-lg font-semibold shadow-md transition-all active:scale-95 ${
                            smartIsGenerating()
                              ? 'bg-emerald-200 text-white cursor-not-allowed'
                              : 'bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-700 hover:to-sky-700 text-white'
                          }`}
                        >
                          <span class="flex items-center gap-2">
                            <Show
                              when={smartIsGenerating()}
                              fallback={
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path d="M11.3 1.046a1 1 0 10-2.6 0l-.27 2.68a1 1 0 00.997 1.099h1.146a1 1 0 00.997-1.099l-.27-2.68zM4.222 3.636a1 1 0 00-1.414 1.414l1.895 1.894a1 1 0 001.414-1.414L4.222 3.636zm11.556 0L13.883 5.53a1 1 0 001.414 1.414l1.895-1.894a1 1 0 10-1.414-1.414zM10 5a5 5 0 100 10A5 5 0 0010 5zM1 11.3a1 1 0 100-2.6l2.68-.27a1 1 0 011.099.997v1.146a1 1 0 01-1.099.997L1 11.3zm18 0l-2.68.27a1 1 0 00-1.099-.997H14.075a1 1 0 00-1.099.997L19 11.3z" />
                                </svg>
                              }
                            >
                              <div class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></div>
                            </Show>
                            {smartIsGenerating() ? '生成中…' : '生成草案'}
                          </span>
                        </button>
                      </>
                    }
                  >
                    <button
                      type="button"
                      onClick={() => setSmartDraft(null)}
                      disabled={smartIsGenerating()}
                      class={`px-5 py-2.5 rounded-lg font-medium transition-colors ${
                        smartIsGenerating() ? 'text-gray-300 bg-white' : 'text-gray-600 hover:bg-gray-100 bg-white'
                      }`}
                    >
                      返回编辑
                    </button>
                    <button
                      type="button"
                      onClick={runSmartGenerate}
                      disabled={smartIsGenerating()}
                      class={`px-5 py-2.5 rounded-lg font-semibold transition-all active:scale-95 ${
                        smartIsGenerating()
                          ? 'bg-emerald-200 text-white cursor-not-allowed'
                          : 'bg-white text-emerald-700 border border-emerald-200 hover:bg-emerald-50'
                      }`}
                    >
                      重新生成
                    </button>
                    <button
                      type="button"
                      onClick={applySmartDraft}
                      disabled={smartIsGenerating()}
                      class={`px-5 py-2.5 rounded-lg font-semibold shadow-md transition-all active:scale-95 ${
                        smartIsGenerating()
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

          <div class="mb-8 bg-white border rounded-2xl shadow-lg overflow-hidden max-w-4xl mx-auto">
            <div class="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
              <div class="flex items-center gap-3">
                <h3 class="font-bold text-lg text-gray-800">{editingId() ? 'Edit Agent' : 'New Agent'}</h3>
                <button
                  type="button"
                  onClick={openSmartGenerate}
                  class="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-700 hover:to-sky-700 shadow-sm transition-all active:scale-95"
                >
                  Smart Generate
                </button>
              </div>
              <button onClick={() => setIsEditing(false)} class="text-gray-400 hover:text-gray-600">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <form onSubmit={handleSubmit} class="p-6 space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Name</label>
                <input 
                  class="w-full border rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                  value={formName()}
                  onInput={e => setFormName(e.currentTarget.value)}
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
                    setShowLLMSelector(!showLLMSelector());
                    setIsRefreshingModels(true);
                    loadProviders(true).finally(() => setIsRefreshingModels(false));
                  }}
                  class="w-full flex items-center justify-between px-4 py-2.5 bg-white border border-gray-200 hover:border-emerald-500 rounded-lg transition-all active:scale-[0.98] shadow-sm group"
                >
                  <div class="flex items-center gap-2.5 overflow-hidden">
                    <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></div>
                    <div class="flex flex-col items-start overflow-hidden">
                      <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider leading-none mb-0.5">{formProvider() || "Select Provider"}</span>
                      <span class="text-sm font-bold text-gray-800 truncate">{formModel() || "Select Model"}</span>
                    </div>
                  </div>
                  <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 text-gray-400 transition-transform duration-300 ${showLLMSelector() ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <Show when={showLLMSelector()}>
                  <div class="absolute top-full left-0 mt-2 w-full min-w-[280px] bg-white border border-gray-100 rounded-xl shadow-2xl z-[100] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                    <div class="p-3 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                      <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Quick Switch</span>
                      <Show when={isRefreshingModels()}>
                        <div class="w-3 h-3 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
                      </Show>
                    </div>
                    <div class="p-2 max-h-72 overflow-y-auto space-y-1 scrollbar-thin">
                      <For each={providers().filter(p => p.available_models && p.available_models.length > 0)}>
                        {provider => (
                          <div class="space-y-1">
                            <div class="px-3 py-1.5 text-[9px] font-black text-emerald-600 uppercase bg-emerald-50 rounded-md tracking-widest">{provider.name}</div>
                            <For each={provider.available_models || []}>
                              {model => (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setFormProvider(provider.name);
                                    setFormModel(model);
                                    setShowLLMSelector(false);
                                  }}
                                  class={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all flex items-center justify-between group ${
                                    formModel() === model
                                      ? 'bg-emerald-600 text-white font-bold shadow-md shadow-emerald-200'
                                      : 'hover:bg-gray-50 text-gray-600 hover:text-gray-900'
                                  }`}
                                >
                                  <span class="truncate">{model}</span>
                                  <Show when={formModel() === model}>
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
                value={formPrompt()}
                onInput={e => setFormPrompt(e.currentTarget.value)}
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
                    onClick={() => setFormTools(availableTools().map(t => t.id))}
                    class="text-[10px] uppercase tracking-wider font-bold text-emerald-600 hover:text-emerald-700 bg-emerald-50 px-2 py-1 rounded"
                  >
                    Select All
                  </button>
                  <button 
                    type="button"
                    onClick={() => setFormTools([])}
                    class="text-[10px] uppercase tracking-wider font-bold text-gray-500 hover:text-gray-600 bg-gray-100 px-2 py-1 rounded"
                  >
                    Clear All
                  </button>
                </div>
              </div>
              <div class="space-y-6">
                <For each={Object.entries(groupedTools())}>
                  {([server, tools]) => {
                    const isExpanded = () => !!expandedGroups()[server];
                    const selectedCountInGroup = () => tools.filter(t => formTools().includes(t.id)).length;
                    
                    return (
                      <div class="border rounded-xl overflow-hidden bg-white shadow-sm transition-all duration-200">
                        {/* Group Header */}
                        <div 
                          class="flex items-center justify-between px-4 py-3 bg-gray-50/80 cursor-pointer hover:bg-gray-100 transition-colors"
                          onClick={() => toggleGroupExpand(server)}
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
                                const current = formTools();
                                const allSelected = toolIds.every(id => current.includes(id));
                                if (allSelected) {
                                  setFormTools(current.filter(id => !toolIds.includes(id)));
                                } else {
                                  const next = new Set([...current, ...toolIds]);
                                  setFormTools(Array.from(next));
                                }
                              }}
                              class="text-[10px] font-bold text-emerald-600 hover:bg-emerald-100 px-2 py-1 rounded transition-colors"
                            >
                              {tools.every(t => formTools().includes(t.id)) ? 'Deselect All' : 'Select All'}
                            </button>
                          </div>
                        </div>

                        {/* Group Content */}
                        <Show when={isExpanded()}>
                          <div class="p-4 bg-white border-t border-gray-100 animate-in fade-in slide-in-from-top-2 duration-200">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                              <For each={tools}>
                                {tool => (
                                  <label class={`flex items-start p-3 border rounded-lg cursor-pointer transition-all ${
                                    (formTools().includes(tool.id) || formTools().includes(tool.name)) 
                                    ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500' 
                                    : 'hover:bg-gray-50 border-gray-200'
                                  }`}>
                                    <input 
                                      type="checkbox" 
                                      class="mt-1 mr-3 text-emerald-600 focus:ring-emerald-500 rounded border-gray-300"
                                      checked={formTools().includes(tool.id) || formTools().includes(tool.name)}
                                      onChange={() => toggleTool(tool.id)}
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
                <Show when={availableTools().length === 0}>
                  <div class="col-span-full text-center py-8 text-gray-500 text-sm bg-gray-50 rounded-xl border border-dashed border-gray-300">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 011 1V4z" />
                    </svg>
                    No MCP tools found. Configure MCP servers in Settings.
                  </div>
                </Show>
              </div>
            </div>

            <Show when={supportsDocScope()}>
              <div class="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4 space-y-3">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <div class="text-[10px] font-black text-emerald-700 uppercase tracking-[0.2em]">Search Scope</div>
                    <div class="text-xs text-emerald-700/80 mt-1">Applies to docs_search_markdown_dir / docs_read_markdown_dir</div>
                  </div>
                  <div class="text-[10px] font-bold text-emerald-700 bg-white/80 px-2 py-1 rounded-full border border-emerald-100">Optional</div>
                </div>
                <div class="flex flex-col md:flex-row gap-2">
                  <input
                    class="flex-1 border rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-emerald-500 outline-none text-sm"
                    value={formDocRootInput()}
                    onInput={e => setFormDocRootInput(e.currentTarget.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addDocRoot();
                      }
                    }}
                    placeholder="Absolute or project-relative path, e.g. docs or /Users/.../docs"
                  />
                  <button
                    type="button"
                    onClick={addDocRoot}
                    class="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:bg-emerald-700 transition-colors"
                  >
                    Add
                  </button>
                </div>
                <Show
                  when={formDocRoots().length > 0}
                  fallback={
                    <div class="text-xs text-emerald-700/70 bg-white/70 border border-emerald-100 rounded-lg px-3 py-2">
                      Add one or more directories to narrow retrieval. Invalid paths will be rejected by the server.
                    </div>
                  }
                >
                  <div class="flex flex-wrap gap-2">
                    <For each={formDocRoots()}>
                      {root => (
                        <div class="flex items-center gap-2 bg-white border border-emerald-100 text-emerald-800 text-xs px-3 py-1.5 rounded-full">
                          <span class="max-w-[240px] truncate">{root}</span>
                          <button
                            type="button"
                            class="text-emerald-500 hover:text-emerald-700"
                            onClick={() => removeDocRoot(root)}
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
                <Show when={allowDocRoots().length > 0}>
                  <div class="space-y-2">
                    <div class="text-[10px] font-bold text-emerald-700 uppercase tracking-[0.2em]">Allowed Roots</div>
                    <div class="flex flex-wrap gap-2">
                      <For each={allowDocRoots()}>
                        {root => {
                          const selected = () => formDocRoots().includes(root);
                          return (
                            <button
                              type="button"
                              onClick={() => addDocRootValue(root)}
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
                <Show when={denyDocRoots().length > 0}>
                  <div class="space-y-2">
                    <div class="text-[10px] font-bold text-red-600 uppercase tracking-[0.2em]">Denied Roots</div>
                    <div class="flex flex-wrap gap-2">
                      <For each={denyDocRoots()}>
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

            <div class="flex justify-end gap-3 pt-4 border-t">
              <button 
                type="button" 
                onClick={() => setIsEditing(false)} 
                class="px-5 py-2.5 rounded-lg text-gray-600 hover:bg-gray-100 font-medium transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                class="bg-emerald-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-emerald-700 shadow-md transition-all transform active:scale-95"
              >
                {editingId() ? 'Update Agent' : 'Create Agent'}
              </button>
            </div>
          </form>
        </div>
        </>
      </Show>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <For each={agents()}>
          {agent => (
            <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
              <div class="flex justify-between items-start mb-4">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-100 to-emerald-200 flex items-center justify-center text-emerald-700 font-bold text-lg shadow-inner">
                    {agent.name.charAt(0)}
                  </div>
                  <div>
                    <h3 class="font-bold text-gray-800">{agent.name}</h3>
                    <div class="flex items-center gap-1.5 text-xs text-gray-500">
                      <span class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600 font-medium">{agent.provider}</span>
                      <span>•</span>
                      <span>{agent.model}</span>
                    </div>
                  </div>
                </div>
                <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={() => openEdit(agent)}
                    class="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="Edit"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button 
                    onClick={() => handleDelete(agent.id)}
                    class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
              
              <div class="bg-gray-50 p-3 rounded-xl mb-4 border border-gray-100">
                <p class="text-xs text-gray-600 font-mono line-clamp-3 leading-relaxed">
                  {agent.system_prompt}
                </p>
              </div>
              
              <div class="flex items-center gap-2 overflow-hidden">
                <span class="text-xs font-semibold text-gray-400 shrink-0">TOOLS</span>
                <div class="flex flex-wrap gap-1">
                  <For each={agent.enabled_tools.slice(0, 3)}>
                    {tool => (
                      <span class="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded border border-blue-100">
                        {tool}
                      </span>
                    )}
                  </For>
                  <Show when={agent.enabled_tools.length > 3}>
                    <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                      +{agent.enabled_tools.length - 3}
                    </span>
                  </Show>
                  <Show when={agent.enabled_tools.length === 0}>
                    <span class="text-[10px] text-gray-400 italic">No tools enabled</span>
                  </Show>
                </div>
              </div>
              <Show when={agent.doc_roots && agent.doc_roots.length > 0}>
                <div class="flex items-center gap-2 mt-2 overflow-hidden">
                  <span class="text-xs font-semibold text-gray-400 shrink-0">SCOPE</span>
                  <div class="flex flex-wrap gap-1">
                    <For each={agent.doc_roots?.slice(0, 2) || []}>
                      {root => (
                        <span class="text-[10px] bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-100">
                          {root}
                        </span>
                      )}
                    </For>
                    <Show when={(agent.doc_roots?.length || 0) > 2}>
                      <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                        +{(agent.doc_roots?.length || 0) - 2}
                      </span>
                    </Show>
                  </div>
                </div>
              </Show>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
