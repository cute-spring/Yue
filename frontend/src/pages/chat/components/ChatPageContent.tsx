import { createSignal, Show, createEffect, onCleanup, onMount } from 'solid-js';
import { SkillSpec, WorkspaceArtifact } from '../../../types';
import { useToast } from '../../../context/ToastContext';
import ChatSidebar from '../../../components/ChatSidebar';
import { ChatWorkspaceDock } from '../../../components/chat-sidebar/ChatWorkspaceDock';
import ChatInput from '../../../components/ChatInput';
import MessageList from '../../../components/MessageList';
import IntelligencePanel from '../../../components/IntelligencePanel';
import ChatTraceShell from '../../../components/ChatTraceShell';
import { ConfirmModal } from '../../../components/ConfirmModal';
import { useLLMProviders } from '../../../hooks/useLLMProviders';
import { useAgents } from '../../../hooks/useAgents';
import { useChatState } from '../../../hooks/useChatState';
import { useMermaid } from '../../../hooks/useMermaid';
import { useCharts } from '../../../hooks/useCharts';
import { useSpeechController } from '../../../context/SpeechControllerContext';
import type { Preferences } from '../../settings/types';
import { useVoiceInput } from '../../../hooks/useVoiceInput';
import { useChatWorkspace } from '../hooks/useChatWorkspace';
import { useWorkspaceUnderstanding } from '../hooks/useWorkspaceUnderstanding';
import { useVoiceComposerIntegration } from '../hooks/useVoiceComposerIntegration';
import { useChatPageEffects } from '../hooks/useChatPageEffects';
import ChatHeader from './ChatHeader';
import { useChatContentActions } from '../hooks/useChatContentActions';
import { buildDiscoveryQuestionnaireArtifact } from '../utils/chatCommands';
import { useBrowserSessions } from '../../../hooks/useBrowserSessions';

export default function ChatPageContent(props: {
  speechPrefs: () => Preferences;
  traceUiEnabled: boolean;
  traceRawEnabled: boolean;
}) {
  const toast = useToast();
  const speech = useSpeechController();
  const [requestedSkill, setRequestedSkill] = createSignal<string | null>(null);
  const [skills, setSkills] = createSignal<SkillSpec[]>([]);
  const speechStatusText = () => {
    if (!speech.supported()) return 'Read aloud is unavailable in this browser.';
    if (speech.isPaused()) return 'Read aloud paused.';
    if (speech.isSpeaking()) return 'Read aloud started.';
    return 'Read aloud stopped.';
  };

  const [showHistory, setShowHistory] = createSignal(true);
  const [showKnowledge, setShowKnowledge] = createSignal(false);
  const [intelligenceTab, setIntelligenceTab] = createSignal<'actions' | 'preview' | 'stats'>('actions');
  const [previewContent, setPreviewContent] = createSignal<{ lang: string; content: string } | null>(null);
  const [isArtifactExpanded, setIsArtifactExpanded] = createSignal(false);
  const [isArtifactFullscreen, setIsArtifactFullscreen] = createSignal(false);
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);
  const [showTraceShell, setShowTraceShell] = createSignal(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = createSignal<string | null>(null);
  const [historyWorkspaceFilterId, setHistoryWorkspaceFilterId] = createSignal<string | null>(null);
  const browserSessions = useBrowserSessions();

  createEffect(() => {
    void browserSessions.refreshBrowserSessions();
  });
  createEffect(() => {
    browserSessions.selectedBrowserSessionId();
    void browserSessions.refreshBrowserActions();
  });
  onMount(() => {
    const browserActionTimer = window.setInterval(() => void browserSessions.refreshBrowserActions(), 1000);
    onCleanup(() => window.clearInterval(browserActionTimer));
  });

  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;
  let messagesEndRef: HTMLDivElement | undefined;
  let imageInputRef: HTMLInputElement | undefined;
  const isMobileViewport = () => window.innerWidth < 1024;

  const {
    providers,
    selectedProvider,
    setSelectedProvider,
    selectedModel,
    setSelectedModel,
    showLLMSelector,
    setShowLLMSelector,
    showAllModels,
    setShowAllModels,
    isRefreshingModels,
    setIsRefreshingModels,
    loadProviders,
    PROVIDER_STORAGE_KEY,
    MODEL_STORAGE_KEY,
  } = useLLMProviders();

  const {
    agents,
    selectedAgent,
    setSelectedAgent,
    showAgentSelector,
    setShowAgentSelector,
    setAgentFilter,
    selectedIndex,
    setSelectedIndex,
    filteredAgents,
    selectAgent,
  } = useAgents(() => textareaRef);
  const currentAgent = () => agents().find((a) => a.id === selectedAgent());

  const chatState = useChatState(
    selectedProvider,
    selectedModel,
    selectedAgent,
    requestedSkill,
    setShowLLMSelector,
    selectedWorkspaceId,
  );

  const {
    chats,
    currentChatId,
    messages,
    setMessages,
    input,
    setInput,
    isTyping,
    elapsedTime,
    isDeepThinking,
    setIsDeepThinking,
    expandedThoughts,
    setExpandedThoughts,
    imageAttachments,
    setImageAttachments,
    copiedMessageIndex,
    activeSkill,
    actionStates,
    setActiveSkill,
    loadChat,
    startNewChat,
    deleteChat,
    generateSummary,
    toggleThought,
    copyUserMessage,
    quoteUserMessage,
    handleRegenerate,
    handleEditQuestion,
    lastGenerationOutcome,
    submitText,
    submitActionDecision,
    handleSubmit: originalHandleSubmit,
  } = chatState;

  const {
    workspaces,
    workspaceSources,
    workspaceArtifacts,
    workspaceNotes,
    workspaceMemories,
    workspaceMemoryCandidates,
    workspaceSourceMode,
    setWorkspaceSourceMode,
    selectedWorkspaceSourceIds,
    groundingMode,
    setGroundingMode,
    workspaceLoading,
    sourcesLoading,
    artifactsLoading,
    notesLoading,
    memoriesLoading,
    loadWorkspaces,
    checkWorkspaceSources,
    checkWorkspaceSource,
    handleSelectWorkspace,
    toggleWorkspaceSource,
    buildWorkspaceRequestOverrides,
    saveLastAssistantAsWorkspaceNote,
    saveLastAssistantAsResearchArtifact,
    saveSessionHandoffArtifact,
    saveDiscoveryQuestionnaireArtifact,
    suggestWorkspaceMemoryFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromUserMessage,
    suggestWorkspaceMemoryCandidateFromNote,
    createWorkspaceMemory,
    updateWorkspaceMemory,
    bulkUpdateWorkspaceMemoryStatusByType,
    deleteWorkspaceMemory,
    approveWorkspaceMemoryCandidate,
    rejectWorkspaceMemoryCandidate,
    saveChartArtifactToWorkspace,
    handleCreateWorkspace,
    trackWorkspaceCaptureTelemetry,
  } = useChatWorkspace({
    toast,
    selectedWorkspaceId,
    setSelectedWorkspaceId,
    startNewChat,
    isMobile: isMobileViewport,
    setShowHistory,
    currentChatId,
    messages,
  });

  const {
    workspaceUnderstanding,
    workspaceUnderstandingLoading,
    workspaceUnderstandingError,
    refreshWorkspaceUnderstanding,
  } = useWorkspaceUnderstanding({ selectedWorkspaceId });

  const createWorkspaceMemoryAndRefresh = async (payload: Parameters<typeof createWorkspaceMemory>[0]) => {
    await createWorkspaceMemory(payload);
    await refreshWorkspaceUnderstanding();
  };

  const updateWorkspaceMemoryAndRefresh = async (
    memoryId: string,
    payload: Parameters<typeof updateWorkspaceMemory>[1],
  ) => {
    await updateWorkspaceMemory(memoryId, payload);
    await refreshWorkspaceUnderstanding();
  };

  const bulkUpdateWorkspaceMemoryStatusByTypeAndRefresh = async (memoryType: string, status: string) => {
    await bulkUpdateWorkspaceMemoryStatusByType(memoryType, status);
    await refreshWorkspaceUnderstanding();
  };

  const deleteWorkspaceMemoryAndRefresh = async (memoryId: string) => {
    await deleteWorkspaceMemory(memoryId);
    await refreshWorkspaceUnderstanding();
  };

  const approveWorkspaceMemoryCandidateAndRefresh = async (
    candidateId: string,
    payload: Parameters<typeof approveWorkspaceMemoryCandidate>[1],
  ) => {
    await approveWorkspaceMemoryCandidate(candidateId, payload);
    await refreshWorkspaceUnderstanding();
  };

  const rejectWorkspaceMemoryCandidateAndRefresh = async (candidateId: string, reason?: string | null) => {
    await rejectWorkspaceMemoryCandidate(candidateId, reason);
    await refreshWorkspaceUnderstanding();
  };

  createEffect(() => {
    setHistoryWorkspaceFilterId(selectedWorkspaceId());
  });

  const handleManualSelectWorkspace = (workspaceId: string | null) => {
    setHistoryWorkspaceFilterId(workspaceId);
    handleSelectWorkspace(workspaceId);
  };

  const voiceInput = useVoiceInput(() => ({
    language: props.speechPrefs().voice_input_language,
    appLanguage: props.speechPrefs().language,
    provider:
      currentAgent()?.voice_input_provider === 'azure' &&
      currentAgent()?.voice_azure_config?.api_key_configured
        ? 'azure'
        : props.speechPrefs().voice_input_provider === 'azure' &&
            currentAgent()?.voice_azure_config?.api_key_configured
          ? 'azure'
          : 'browser',
    agentId: currentAgent()?.id || null,
  }));

  const loadSkills = async () => {
    try {
      const res = await fetch('/api/skills');
      const data = await res.json();
      setSkills(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load skills', e);
      setSkills([]);
    }
  };

  createEffect(() => {
    selectedAgent();
    setRequestedSkill(null);
    setActiveSkill(null);
  });

  const { debouncedRender: debouncedRenderMermaid } = useMermaid(() => undefined);
  const { debouncedRenderCharts } = useCharts();
  const debouncedRender = () => {
    debouncedRenderMermaid();
    debouncedRenderCharts();
  };
  function forwardSubmit(event: Event) {
    handleSubmit(event);
  }

  const {
    composerKey,
    handleInput,
    handleKeyDown,
    handleToggleVoiceInput,
    handleCancelVoiceInput,
    handleInsertVoiceInput,
    handleInsertAndSubmitVoiceInput,
  } = useVoiceComposerIntegration({
    voiceInput,
    speechPrefs: () => ({ voice_input_enabled: props.speechPrefs().voice_input_enabled }),
    currentAgentVoiceEnabled: () => currentAgent()?.voice_input_enabled !== false,
    input,
    setInput,
    textareaRef: () => textareaRef,
    showAgentSelector,
    setShowAgentSelector,
    setAgentFilter,
    selectedIndex,
    setSelectedIndex,
    filteredAgents,
    selectAgent,
    onSubmit: forwardSubmit,
    onVoiceSubmit: (next) => {
      speech.stopCurrent();
      void submitText(next);
    },
  });

  const {
    isMobile,
    handleScroll,
  } = useChatPageEffects({
    input,
    textareaRef: () => textareaRef,
    chatContainerRef: () => chatContainerRef,
    messagesEndRef: () => messagesEndRef,
    messages,
    isTyping,
    expandedThoughts,
    setExpandedThoughts,
    lastGenerationOutcome,
    speechPrefs: () => ({ auto_speech_enabled: props.speechPrefs().auto_speech_enabled }),
    speech,
    debouncedRender,
    toast,
    setShowLLMSelector,
    setShowAgentSelector,
    setPreviewContent,
    setIntelligenceTab,
    setShowKnowledge,
    setSelectedProvider,
    setSelectedModel,
    loadProviders,
    loadSkills,
    loadWorkspaces,
    providerStorageKey: PROVIDER_STORAGE_KEY,
    modelStorageKey: MODEL_STORAGE_KEY,
  });

  const {
    activeAgentName,
    visibleSkillOptions,
    handleSubmit,
    handleContinue,
    handleGenerateSummary,
    handleModelSelect,
    handleRefreshModels,
  } = useChatContentActions({
    toast,
    speech,
    currentAgent,
    voiceInput,
    handleInsertVoiceInput: () => handleInsertVoiceInput(),
    agents,
    selectedAgent,
    skills,
    input,
    setInput,
    messages,
    setMessages,
    workspaceArtifacts,
    workspaceSources,
    workspaceSourceMode,
    selectedWorkspaceSourceIds,
    groundingMode,
    imageAttachments,
    isTyping,
    selectedModel,
    setShowLLMSelector,
    submitText,
    originalHandleSubmit,
    saveLastAssistantAsWorkspaceNote,
    saveLastAssistantAsResearchArtifact,
    saveSessionHandoffArtifact,
    saveDiscoveryQuestionnaireArtifact,
    buildWorkspaceRequestOverrides: () => ({
      ...buildWorkspaceRequestOverrides(),
      browser_session_id: browserSessions.selectedBrowserSessionId() || undefined,
      note_recall_enabled: props.speechPrefs().note_recall_enabled,
      capture_suggestions_enabled: props.speechPrefs().capture_suggestions_enabled,
      memory_suggestions_enabled: props.speechPrefs().memory_suggestions_enabled,
    }),
    generateSummary,
    currentChatId,
    loadChat,
    setShowHistory,
    setSelectedAgent,
    selectedProvider,
    setSelectedProvider,
    providers,
    setSelectedModel,
    setImageAttachments,
    providerStorageKey: PROVIDER_STORAGE_KEY,
    modelStorageKey: MODEL_STORAGE_KEY,
    loadProviders,
    setIsRefreshingModels,
    isMobile: isMobileViewport,
  });

  const handleCreateQuestionnaireFromResearchGap = async (
    artifact: WorkspaceArtifact,
    gap: string,
  ) => {
    const questionnaire = buildDiscoveryQuestionnaireArtifact(
      `Research gap from "${artifact.title}": ${gap}`,
      messages(),
      [artifact, ...workspaceArtifacts().filter((entry) => entry.id !== artifact.id)],
    );
    await saveDiscoveryQuestionnaireArtifact(questionnaire);
    toast.success('Saved discovery questionnaire from research gap.', 3000);
  };

  const handleClarifyResearchDecision = (artifact: WorkspaceArtifact, question: string) => {
    setInput(`/clarify Research decision from "${artifact.title}": ${question}`);
    toast.success('Clarify prompt staged in the composer.', 3000);
  };

  return (
    <div class="flex h-full bg-background overflow-hidden relative">
      <div class="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {speechStatusText()}
      </div>
      <ChatSidebar
        showHistory={showHistory()}
        setShowHistory={setShowHistory}
        chats={chats()}
        workspaces={workspaces()}
        selectedWorkspaceId={historyWorkspaceFilterId()}
        workspaceSources={workspaceSources()}
        workspaceArtifacts={workspaceArtifacts()}
        workspaceNotes={workspaceNotes()}
        workspaceMemories={workspaceMemories()}
        workspaceMemoryCandidates={workspaceMemoryCandidates()}
        workspaceSourceMode={workspaceSourceMode()}
        selectedWorkspaceSourceIds={selectedWorkspaceSourceIds()}
        groundingMode={groundingMode()}
        workspaceLoading={workspaceLoading()}
        sourcesLoading={sourcesLoading()}
        artifactsLoading={artifactsLoading()}
        notesLoading={notesLoading()}
        memoriesLoading={memoriesLoading()}
        workspaceUnderstanding={workspaceUnderstanding()}
        workspaceUnderstandingLoading={workspaceUnderstandingLoading()}
        workspaceUnderstandingError={workspaceUnderstandingError()}
        currentChatId={currentChatId()}
        onNewChat={() => {
          speech.stopCurrent();
          startNewChat(isMobile(), setShowHistory);
        }}
        onSelectWorkspace={handleManualSelectWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        onWorkspaceSourceModeChange={setWorkspaceSourceMode}
        onToggleWorkspaceSource={toggleWorkspaceSource}
        onGroundingModeChange={setGroundingMode}
        onCheckWorkspaceSources={checkWorkspaceSources}
        onCheckWorkspaceSource={checkWorkspaceSource}
        onLoadChat={(id) => {
          speech.stopCurrent();
          loadChat(id, isMobile(), setShowHistory, setSelectedAgent);
        }}
        onSaveLastAssistantAsWorkspaceNote={saveLastAssistantAsWorkspaceNote}
        onSuggestWorkspaceMemoryFromLastAssistantMessage={suggestWorkspaceMemoryFromLastAssistantMessage}
        onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage={suggestWorkspaceMemoryCandidateFromLastAssistantMessage}
        onSuggestWorkspaceMemoryCandidateFromNote={suggestWorkspaceMemoryCandidateFromNote}
        onCreateWorkspaceMemory={createWorkspaceMemoryAndRefresh}
        onUpdateWorkspaceMemory={updateWorkspaceMemoryAndRefresh}
        onBulkUpdateWorkspaceMemoryStatusByType={bulkUpdateWorkspaceMemoryStatusByTypeAndRefresh}
        onDeleteWorkspaceMemory={deleteWorkspaceMemoryAndRefresh}
        onApproveWorkspaceMemoryCandidate={approveWorkspaceMemoryCandidateAndRefresh}
        onRejectWorkspaceMemoryCandidate={rejectWorkspaceMemoryCandidateAndRefresh}
        onRefreshWorkspaceUnderstanding={refreshWorkspaceUnderstanding}
        onDeleteChat={(id) => setConfirmDeleteId(id)}
        onGenerateSummary={handleGenerateSummary}
      />

      <ChatWorkspaceDock
        workspaces={workspaces()}
        selectedWorkspaceId={selectedWorkspaceId()}
        workspaceSources={workspaceSources()}
        workspaceArtifacts={workspaceArtifacts()}
        workspaceNotes={workspaceNotes()}
        workspaceMemories={workspaceMemories()}
        workspaceMemoryCandidates={workspaceMemoryCandidates()}
        workspaceSourceMode={workspaceSourceMode()}
        selectedWorkspaceSourceIds={selectedWorkspaceSourceIds()}
        groundingMode={groundingMode()}
        workspaceLoading={workspaceLoading()}
        sourcesLoading={sourcesLoading()}
        artifactsLoading={artifactsLoading()}
        notesLoading={notesLoading()}
        memoriesLoading={memoriesLoading()}
        workspaceUnderstanding={workspaceUnderstanding()}
        workspaceUnderstandingLoading={workspaceUnderstandingLoading()}
        workspaceUnderstandingError={workspaceUnderstandingError()}
        onNewChat={() => {
          speech.stopCurrent();
          startNewChat(isMobile(), setShowHistory);
        }}
        onSelectWorkspace={handleManualSelectWorkspace}
        onCreateWorkspace={handleCreateWorkspace}
        onWorkspaceSourceModeChange={setWorkspaceSourceMode}
        onToggleWorkspaceSource={toggleWorkspaceSource}
        onGroundingModeChange={setGroundingMode}
        onCheckWorkspaceSources={checkWorkspaceSources}
        onCheckWorkspaceSource={checkWorkspaceSource}
        onLoadChat={(id) => {
          speech.stopCurrent();
          loadChat(id, isMobile(), setShowHistory, setSelectedAgent);
        }}
        onSaveLastAssistantAsWorkspaceNote={saveLastAssistantAsWorkspaceNote}
        onSuggestWorkspaceMemoryFromLastAssistantMessage={suggestWorkspaceMemoryFromLastAssistantMessage}
        onSuggestWorkspaceMemoryCandidateFromLastAssistantMessage={suggestWorkspaceMemoryCandidateFromLastAssistantMessage}
        onSuggestWorkspaceMemoryCandidateFromNote={suggestWorkspaceMemoryCandidateFromNote}
        onCreateWorkspaceMemory={createWorkspaceMemoryAndRefresh}
        onUpdateWorkspaceMemory={updateWorkspaceMemoryAndRefresh}
        onBulkUpdateWorkspaceMemoryStatusByType={bulkUpdateWorkspaceMemoryStatusByTypeAndRefresh}
        onDeleteWorkspaceMemory={deleteWorkspaceMemoryAndRefresh}
        onApproveWorkspaceMemoryCandidate={approveWorkspaceMemoryCandidateAndRefresh}
        onRejectWorkspaceMemoryCandidate={rejectWorkspaceMemoryCandidateAndRefresh}
        onRefreshWorkspaceUnderstanding={refreshWorkspaceUnderstanding}
        onCreateQuestionnaireFromResearchGap={handleCreateQuestionnaireFromResearchGap}
        onClarifyResearchDecision={handleClarifyResearchDecision}
        memorySuggestionsEnabled={props.speechPrefs().memory_suggestions_enabled}
      />

      <div class="flex-1 flex flex-col h-full min-w-0 bg-background relative">
        <ChatHeader
          showHistory={showHistory()}
          onToggleHistory={() => setShowHistory(!showHistory())}
          currentAgent={currentAgent() || null}
          activeAgentName={activeAgentName()}
          isTyping={isTyping()}
          activeSkill={activeSkill()}
          traceUiEnabled={props.traceUiEnabled}
          onOpenTrace={() => setShowTraceShell(true)}
          showKnowledge={showKnowledge()}
          onToggleKnowledge={() => setShowKnowledge(!showKnowledge())}
        />

        <MessageList
          chatContainerRef={(el) => (chatContainerRef = el)}
          handleScroll={handleScroll}
          messages={messages()}
          activeAgentName={activeAgentName()}
          isTyping={isTyping()}
          expandedThoughts={expandedThoughts()}
          toggleThought={toggleThought}
          elapsedTime={elapsedTime()}
          copiedMessageIndex={copiedMessageIndex()}
          copyUserMessage={copyUserMessage}
          quoteUserMessage={quoteUserMessage}
          handleRegenerate={handleRegenerate}
          handleEditQuestion={handleEditQuestion}
          onContinue={handleContinue}
          onSaveChartArtifact={saveChartArtifactToWorkspace}
          messagesEndRef={(el) => (messagesEndRef = el)}
          setInput={setInput}
          selectedProvider={selectedProvider()}
          selectedModel={selectedModel()}
          selectedWorkspaceId={selectedWorkspaceId()}
          currentChatId={currentChatId()}
          workspaceNotes={workspaceNotes()}
          workspaceMemoryCandidates={workspaceMemoryCandidates()}
          captureSuggestionsEnabled={props.speechPrefs().capture_suggestions_enabled}
          memorySuggestionsEnabled={props.speechPrefs().memory_suggestions_enabled}
          onSaveWorkspaceNote={saveLastAssistantAsWorkspaceNote}
          onSuggestWorkspaceMemoryCandidate={suggestWorkspaceMemoryCandidateFromLastAssistantMessage}
          onSuggestHighSignalUserMemoryCandidate={suggestWorkspaceMemoryCandidateFromUserMessage}
          onApproveWorkspaceMemoryCandidate={approveWorkspaceMemoryCandidateAndRefresh}
          onRejectWorkspaceMemoryCandidate={rejectWorkspaceMemoryCandidateAndRefresh}
          onTrackWorkspaceCaptureTelemetry={trackWorkspaceCaptureTelemetry}
        />

        <div class="mx-auto w-full max-w-4xl px-4 pb-2">
          <div class="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-950 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-100">
            <span class="font-semibold">Browser</span>
            <select
              class="min-w-0 flex-1 rounded border border-emerald-200 bg-white px-2 py-1 text-xs dark:border-emerald-800 dark:bg-slate-900"
              value={browserSessions.selectedBrowserSessionId() || ''}
              onChange={(event) => {
                browserSessions.setSelectedBrowserSessionId(event.currentTarget.value || null);
                void browserSessions.refreshBrowserActions();
              }}
              aria-label="Authorized browser tab"
            >
              <option value="">No tab attached</option>
              {browserSessions.sessions().map((session) => (
                <option value={session.id}>
                  {session.title} — {session.origin} ({session.authorization_mode})
                </option>
              ))}
            </select>
            <button
              type="button"
              class="rounded px-2 py-1 font-medium hover:bg-emerald-100 dark:hover:bg-emerald-900"
              onClick={() => void browserSessions.refreshBrowserSessions()}
            >
              Refresh
            </button>
          </div>
          <Show when={browserSessions.browserActions().find((action) => action.status === 'awaiting_approval')}>
            {(action) => (
              <div class="mt-2 flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100">
                <span class="flex-1">
                  Yue requests approval to {action().action}{action().target ? `: ${action().target}` : ''}.
                </span>
                <button
                  type="button"
                  class="rounded bg-emerald-700 px-2 py-1 font-semibold text-white"
                  onClick={() => void browserSessions.decideBrowserAction(action().id, true)}
                >
                  Approve
                </button>
                <button
                  type="button"
                  class="rounded border border-amber-500 px-2 py-1 font-semibold"
                  onClick={() => void browserSessions.decideBrowserAction(action().id, false)}
                >
                  Reject
                </button>
              </div>
            )}
          </Show>
          <Show when={browserSessions.browserActions().find((action) => action.status === 'needs_reconciliation')}>
            {(action) => (
              <div class="mt-2 flex items-center gap-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-950 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-100">
                <span class="flex-1">
                  Yue could not verify {action().action}{action().target ? `: ${action().target}` : ''}. Check the page, then confirm the outcome.
                </span>
                <button
                  type="button"
                  class="rounded bg-emerald-700 px-2 py-1 font-semibold text-white"
                  onClick={() => void browserSessions.reconcileBrowserAction(action().id, 'completed')}
                >
                  Applied
                </button>
                <button
                  type="button"
                  class="rounded border border-rose-500 px-2 py-1 font-semibold"
                  onClick={() => void browserSessions.reconcileBrowserAction(action().id, 'not_applied')}
                >
                  Not Applied
                </button>
              </div>
            )}
          </Show>
        </div>

        <ChatInput
          showAgentSelector={showAgentSelector()}
          filteredAgents={filteredAgents()}
          selectedIndex={selectedIndex()}
          selectAgent={(agent) => selectAgent(agent, input(), setInput)}
          input={input()}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          onSubmit={handleSubmit}
          isTyping={isTyping()}
          activeAgentName={activeAgentName()}
          textareaRef={(el) => (textareaRef = el)}
          inputReadOnly={voiceInput.phase() !== 'idle'}
          composerKey={composerKey()}
          showLLMSelector={showLLMSelector()}
          setShowLLMSelector={setShowLLMSelector}
          selectedModel={selectedModel()}
          onSelectModel={handleModelSelect}
          selectedProvider={selectedProvider()}
          providers={providers()}
          showAllModels={showAllModels()}
          setShowAllModels={setShowAllModels}
          isRefreshingModels={isRefreshingModels()}
          onRefreshModels={handleRefreshModels}
          isDeepThinking={isDeepThinking()}
          setIsDeepThinking={setIsDeepThinking}
          imageAttachments={imageAttachments()}
          setImageAttachments={setImageAttachments}
          onImageClick={() => imageInputRef?.click()}
          imageInputRef={(el) => (imageInputRef = el)}
          visibleSkills={visibleSkillOptions()}
          requestedSkill={requestedSkill()}
          onSelectSkill={setRequestedSkill}
          skillMode={currentAgent()?.skill_mode}
          voiceInputEnabled={
            props.speechPrefs().voice_input_enabled && currentAgent()?.voice_input_enabled !== false
          }
          voiceInputSupported={voiceInput.supported()}
          voiceInputProvider={voiceInput.provider()}
          voiceInputPreferredProvider={voiceInput.preferredProvider()}
          voiceInputIsRecording={voiceInput.isRecording()}
          voiceInputIsProcessing={voiceInput.isProcessing()}
          voiceInputHasDraft={voiceInput.hasDraft()}
          voiceInputPhase={voiceInput.phase()}
          voiceInputPreviewText={
            props.speechPrefs().voice_input_show_interim ? voiceInput.previewText() : ''
          }
          voiceInputInterimTranscript={voiceInput.interimTranscript()}
          voiceInputError={voiceInput.error()}
          advancedMode={props.speechPrefs().advanced_mode}
          voiceInputFallbackMessage={voiceInput.fallbackMessage()}
          onToggleVoiceInput={() => {
            void handleToggleVoiceInput();
          }}
          onCancelVoiceInput={handleCancelVoiceInput}
          onInsertVoiceInput={handleInsertVoiceInput}
          onSendVoiceInput={handleInsertAndSubmitVoiceInput}
        />
      </div>

      <IntelligencePanel
        showKnowledge={showKnowledge()}
        setShowKnowledge={setShowKnowledge}
        isArtifactExpanded={isArtifactExpanded()}
        setIsArtifactExpanded={setIsArtifactExpanded}
        isArtifactFullscreen={isArtifactFullscreen()}
        setIsArtifactFullscreen={setIsArtifactFullscreen}
        intelligenceTab={intelligenceTab()}
        setIntelligenceTab={setIntelligenceTab}
        previewContent={previewContent()}
        lastMessage={[...messages()].reverse().find((m) => m.role === 'assistant')}
        isMobile={isMobile()}
        actionStates={actionStates()}
        isTyping={isTyping()}
        onResolveAction={(state, approved) => {
          void submitActionDecision(state, approved);
        }}
      />

      {(showHistory() || (showKnowledge() && isMobile())) && (
        <div
          onClick={() => {
            setShowHistory(false);
            setShowKnowledge(false);
          }}
          class="fixed inset-0 bg-black/40 backdrop-blur-sm z-20 lg:hidden"
        />
      )}

      <ConfirmModal
        show={!!confirmDeleteId()}
        title="Delete Chat"
        message="Are you sure you want to delete this chat? This action cannot be undone."
        confirmText="Delete Chat"
        cancelText="Keep Chat"
        type="danger"
        onConfirm={() => {
          const id = confirmDeleteId();
          if (id) {
            speech.stopCurrent();
            deleteChat(id);
            setConfirmDeleteId(null);
          }
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />

      <Show when={props.traceUiEnabled}>
        <ChatTraceShell
          open={showTraceShell()}
          chatId={currentChatId()}
          rawEnabled={props.traceRawEnabled}
          onClose={() => setShowTraceShell(false)}
        />
      </Show>
    </div>
  );
}
