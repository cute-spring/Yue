import { createSignal, onMount, onCleanup } from 'solid-js';
import { Agent, McpTool, SmartDraft } from '../types';

export function useAgentsState() {
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
  const [showAllModels, setShowAllModels] = createSignal(false);
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
  const [formDocFilePatternsText, setFormDocFilePatternsText] = createSignal("");
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
    setFormDocFilePatternsText("");
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
    setFormDocFilePatternsText((agent.doc_file_patterns || []).join("\n"));
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
    
    const parsedPatterns = formDocFilePatternsText()
      .split("\n")
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith("#"));

    const payload = {
      name: formName(),
      system_prompt: formPrompt(),
      provider: formProvider(),
      model: formModel(),
      enabled_tools: formTools(),
      doc_roots: formDocRoots(),
      doc_file_patterns: parsedPatterns
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
    return formTools().some(t => (
      t.includes("builtin:docs_") ||
      t.includes("docs_search") ||
      t.includes("docs_read") ||
      t.includes("docs_search_pdf") ||
      t.includes("docs_read_pdf")
    ));
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

  return {
    agents, availableTools, groupedTools, isEditing, editingId, providers,
    showLLMSelector, isRefreshingModels, showAllModels, showSmartGenerate,
    smartDescription, smartUpdateTools, smartIsGenerating, smartError, smartDraft,
    smartApplyName, smartApplyPrompt, smartApplyTools, formName, formPrompt,
    formProvider, formModel, formTools, formDocRoots, formDocRootInput,
    formDocFilePatternsText, expandedGroups, allowDocRoots, denyDocRoots,
    setAgents, setAvailableTools, setIsEditing, setEditingId, setProviders,
    setShowLLMSelector, setIsRefreshingModels, setShowAllModels, setShowSmartGenerate,
    setSmartDescription, setSmartUpdateTools, setSmartIsGenerating, setSmartError,
    setSmartDraft, setSmartApplyName, setSmartApplyPrompt, setSmartApplyTools,
    setFormName, setFormPrompt, setFormProvider, setFormModel, setFormTools,
    setFormDocRoots, setFormDocRootInput, setFormDocFilePatternsText,
    setExpandedGroups, setAllowDocRoots, setDenyDocRoots,
    toggleGroupExpand, loadAgents, loadProviders, loadTools, loadDocAccess,
    openCreate, openEdit, openSmartGenerate, applySmartDraft, smartPromptLint,
    smartRiskSummary, runSmartGenerate, handleSubmit, handleDelete, toggleTool,
    supportsDocScope, addDocRoot, addDocRootValue, removeDocRoot
  };
}
