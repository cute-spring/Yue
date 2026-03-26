import { createSignal, onMount, onCleanup } from 'solid-js';
import { Agent, McpTool, SkillSpec, SmartDraft, SkillGroup } from '../types';

type BuildAgentPayloadInput = {
  name: string;
  systemPrompt: string;
  provider: string;
  model: string;
  enabledTools: string[];
  voiceInputEnabled: boolean;
  voiceInputProvider: 'browser' | 'azure';
  voiceAzureRegion: string;
  voiceAzureEndpointId: string;
  voiceAzureApiKey: string;
  skillMode: 'off' | 'manual' | 'auto';
  visibleSkills: string[];
  agentKind: 'traditional' | 'universal';
  skillGroups: string[];
  extraVisibleSkills: string[];
  docRoots: string[];
  docFilePatternsText: string;
};

export const buildAgentPayload = (input: BuildAgentPayloadInput) => {
  const parsedPatterns = input.docFilePatternsText
    .split('\n')
    .map(s => s.trim())
    .filter(s => s.length > 0 && !s.startsWith('#'));

  return {
    name: input.name,
    system_prompt: input.systemPrompt,
    provider: input.provider,
    model: input.model,
    enabled_tools: input.enabledTools,
    voice_input_enabled: input.voiceInputEnabled,
    voice_input_provider: input.voiceInputProvider,
    voice_azure_config: input.voiceInputProvider === 'azure'
      ? {
          region: input.voiceAzureRegion.trim(),
          endpoint_id: input.voiceAzureEndpointId.trim(),
          api_key: input.voiceAzureApiKey,
        }
      : null,
    skill_mode: input.skillMode,
    visible_skills: input.visibleSkills,
    agent_kind: input.agentKind,
    skill_groups: input.skillGroups,
    extra_visible_skills: input.extraVisibleSkills,
    doc_roots: input.docRoots,
    doc_file_patterns: parsedPatterns
  };
};

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
  const [isRefreshingTools, setIsRefreshingTools] = createSignal(false);
  const [skills, setSkills] = createSignal<SkillSpec[]>([]);
  const [skillGroups, setSkillGroups] = createSignal<SkillGroup[]>([]);
  
  // Form state
  const [formName, setFormName] = createSignal("");
  const [formPrompt, setFormPrompt] = createSignal("");
  const [formProvider, setFormProvider] = createSignal("openai");
  const [formModel, setFormModel] = createSignal("gpt-4o");
  const [formTools, setFormTools] = createSignal<string[]>([]);
  const [formVoiceInputEnabled, setFormVoiceInputEnabled] = createSignal(true);
  const [formVoiceInputProvider, setFormVoiceInputProvider] = createSignal<'browser' | 'azure'>('browser');
  const [formVoiceAzureRegion, setFormVoiceAzureRegion] = createSignal("");
  const [formVoiceAzureEndpointId, setFormVoiceAzureEndpointId] = createSignal("");
  const [formVoiceAzureApiKey, setFormVoiceAzureApiKey] = createSignal("");
  const [formVoiceAzureApiKeyConfigured, setFormVoiceAzureApiKeyConfigured] = createSignal(false);
  const [isTestingVoiceAzure, setIsTestingVoiceAzure] = createSignal(false);
  const [voiceAzureTestResult, setVoiceAzureTestResult] = createSignal<{ type: 'success' | 'error'; message: string } | null>(null);
  const [formSkillMode, setFormSkillMode] = createSignal<'off' | 'manual' | 'auto'>('off');
  const [formVisibleSkills, setFormVisibleSkills] = createSignal<string[]>([]);
  const [formAgentKind, setFormAgentKind] = createSignal<'traditional' | 'universal'>('traditional');
  const [formSkillGroups, setFormSkillGroups] = createSignal<string[]>([]);
  const [formExtraVisibleSkills, setFormExtraVisibleSkills] = createSignal<string[]>([]);
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
      setIsRefreshingTools(true);
      const res = await fetch('/api/mcp/tools');
      const data = await res.json();
      const tools = Array.isArray(data) ? data : [];
      const hasDocsList = tools.some(t => t && t.id === 'builtin:docs_list');
      const next = hasDocsList
        ? tools
        : [
            ...tools,
            {
              id: 'builtin:docs_list',
              name: 'docs_list',
              description: 'List files and directories under Yue/docs (or root_dir). Returns a tree-like listing with paths relative to the docs root.',
              server: 'builtin'
            }
          ];
      setAvailableTools(next);
    } catch (e) {
      console.error("Failed to load tools", e);
    } finally {
      setIsRefreshingTools(false);
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

  const loadSkills = async (triggerReload = false) => {
    try {
      if (triggerReload) {
        await fetch('/api/skills/reload', { method: 'POST' });
      }
      const res = await fetch('/api/skills');
      const data = await res.json();
      setSkills(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Failed to load skills", e);
      setSkills([]);
    }
  };

  const loadSkillGroups = async () => {
    try {
      const res = await fetch('/api/skill-groups/');
      const data = await res.json();
      setSkillGroups(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Failed to load skill groups", e);
      setSkillGroups([]);
    }
  };

  onMount(async () => {
    loadAgents();
    loadTools();
    loadProviders();
    loadDocAccess();
    loadSkills();
    loadSkillGroups();

    const handleClickOutside = () => {
      if (showLLMSelector()) {
        setShowLLMSelector(false);
      }
    };
    window.addEventListener('click', handleClickOutside);
    onCleanup(() => window.removeEventListener('click', handleClickOutside));
  });

  const openCreate = () => {
    loadTools(); // Auto refresh tools when opening form
    loadSkills();
    loadSkillGroups();
    setFormName("");
    setFormPrompt("");
    setFormProvider("openai");
    setFormModel("gpt-4o");
    setFormTools([]);
    setFormVoiceInputEnabled(true);
    setFormVoiceInputProvider('browser');
    setFormVoiceAzureRegion("");
    setFormVoiceAzureEndpointId("");
    setFormVoiceAzureApiKey("");
    setFormVoiceAzureApiKeyConfigured(false);
    setVoiceAzureTestResult(null);
    setFormSkillMode("off");
    setFormVisibleSkills([]);
    setFormAgentKind("traditional");
    setFormSkillGroups([]);
    setFormExtraVisibleSkills([]);
    setFormDocRoots([]);
    setFormDocRootInput("");
    setFormDocFilePatternsText("");
    setEditingId(null);
    setIsEditing(true);
  };

  const openEdit = (agent: Agent) => {
    loadTools(); // Auto refresh tools when opening form
    loadSkills();
    loadSkillGroups();
    setFormName(agent.name);
    setFormPrompt(agent.system_prompt);
    setFormProvider(agent.provider);
    setFormModel(agent.model);
    setFormTools(agent.enabled_tools);
    setFormVoiceInputEnabled(agent.voice_input_enabled ?? true);
    setFormVoiceInputProvider(agent.voice_input_provider === 'azure' ? 'azure' : 'browser');
    setFormVoiceAzureRegion(agent.voice_azure_config?.region || "");
    setFormVoiceAzureEndpointId(agent.voice_azure_config?.endpoint_id || "");
    setFormVoiceAzureApiKey("");
    setFormVoiceAzureApiKeyConfigured(!!agent.voice_azure_config?.api_key_configured);
    setVoiceAzureTestResult(null);
    setFormSkillMode((agent.skill_mode as 'off' | 'manual' | 'auto') || "off");
    setFormVisibleSkills(agent.visible_skills || []);
    setFormAgentKind((agent.agent_kind as 'traditional' | 'universal') || "traditional");
    setFormSkillGroups(agent.skill_groups || []);
    setFormExtraVisibleSkills(agent.extra_visible_skills || []);
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
    
    const payload = buildAgentPayload({
      name: formName(),
      systemPrompt: formPrompt(),
      provider: formProvider(),
      model: formModel(),
      enabledTools: formTools(),
      voiceInputEnabled: formVoiceInputEnabled(),
      voiceInputProvider: formVoiceInputProvider(),
      voiceAzureRegion: formVoiceAzureRegion(),
      voiceAzureEndpointId: formVoiceAzureEndpointId(),
      voiceAzureApiKey: formVoiceAzureApiKey(),
      skillMode: formSkillMode(),
      visibleSkills: formVisibleSkills(),
      agentKind: formAgentKind(),
      skillGroups: formSkillGroups(),
      extraVisibleSkills: formExtraVisibleSkills(),
      docRoots: formDocRoots(),
      docFilePatternsText: formDocFilePatternsText()
    });

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

  const testVoiceAzureConfig = async () => {
    setVoiceAzureTestResult(null);
    setIsTestingVoiceAzure(true);
    try {
      const apiKey = formVoiceAzureApiKey().trim();
      if (!formVoiceAzureRegion().trim()) {
        throw new Error('Azure region is required.');
      }
      if (!apiKey && !formVoiceAzureApiKeyConfigured()) {
        throw new Error('Azure Speech key is required.');
      }

      const response = await fetch('/api/speech/stt/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'azure',
          region: formVoiceAzureRegion().trim(),
          api_key: apiKey,
          endpoint_id: formVoiceAzureEndpointId().trim(),
        }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `HTTP ${response.status}`);
      }
      setVoiceAzureTestResult({ type: 'success', message: 'Azure Speech STT connection succeeded.' });
    } catch (e: any) {
      setVoiceAzureTestResult({ type: 'error', message: e?.message || 'Azure Speech STT connection failed.' });
    } finally {
      setIsTestingVoiceAzure(false);
    }
  };

  return {
    agents, availableTools, groupedTools, isEditing, editingId, providers,
    skills,
    skillGroups,
    showLLMSelector, isRefreshingModels, isRefreshingTools, showAllModels, showSmartGenerate,
    smartDescription, smartUpdateTools, smartIsGenerating, smartError, smartDraft,
    smartApplyName, smartApplyPrompt, smartApplyTools, formName, formPrompt,
    formProvider, formModel, formTools, formVoiceInputEnabled, formVoiceInputProvider, formVoiceAzureRegion, formVoiceAzureEndpointId, formVoiceAzureApiKey, formVoiceAzureApiKeyConfigured, isTestingVoiceAzure, voiceAzureTestResult, formSkillMode, formVisibleSkills, formAgentKind, formSkillGroups, formExtraVisibleSkills, formDocRoots, formDocRootInput,
    formDocFilePatternsText, expandedGroups, allowDocRoots, denyDocRoots,
    setAgents, setAvailableTools, setIsEditing, setEditingId, setProviders,
    setSkills,
    setSkillGroups,
    setShowLLMSelector, setIsRefreshingModels, setIsRefreshingTools, setShowAllModels, setShowSmartGenerate,
    setSmartDescription, setSmartUpdateTools, setSmartIsGenerating, setSmartError,
    setSmartDraft, setSmartApplyName, setSmartApplyPrompt, setSmartApplyTools,
    setFormName, setFormPrompt, setFormProvider, setFormModel, setFormTools, setFormVoiceInputEnabled, setFormVoiceInputProvider, setFormVoiceAzureRegion, setFormVoiceAzureEndpointId, setFormVoiceAzureApiKey, setFormVoiceAzureApiKeyConfigured, setFormSkillMode, setFormVisibleSkills, setFormAgentKind, setFormSkillGroups, setFormExtraVisibleSkills,
    setFormDocRoots, setFormDocRootInput, setFormDocFilePatternsText,
    setExpandedGroups, setAllowDocRoots, setDenyDocRoots,
    toggleGroupExpand, loadAgents, loadProviders, loadTools, loadDocAccess, loadSkills, loadSkillGroups,
    openCreate, openEdit, openSmartGenerate, applySmartDraft, smartPromptLint,
    smartRiskSummary, runSmartGenerate, handleSubmit, handleDelete, toggleTool, testVoiceAzureConfig,
    supportsDocScope, addDocRoot, addDocRootValue, removeDocRoot
  };
}
