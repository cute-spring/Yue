import { createSignal, Show, createEffect } from 'solid-js';
import { SkillSpec } from '../../../types';
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
import { useSpeechController } from '../../../context/SpeechControllerContext';
import type { Preferences } from '../../settings/types';
import { useVoiceInput } from '../../../hooks/useVoiceInput';
import { useChatWorkspace } from '../hooks/useChatWorkspace';
import { useVoiceComposerIntegration } from '../hooks/useVoiceComposerIntegration';
import { useChatPageEffects } from '../hooks/useChatPageEffects';
import ChatHeader from './ChatHeader';
import { useChatContentActions } from '../hooks/useChatContentActions';

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
    suggestWorkspaceMemoryFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromLastAssistantMessage,
    suggestWorkspaceMemoryCandidateFromNote,
    createWorkspaceMemory,
    updateWorkspaceMemory,
    bulkUpdateWorkspaceMemoryStatusByType,
    deleteWorkspaceMemory,
    approveWorkspaceMemoryCandidate,
    rejectWorkspaceMemoryCandidate,
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

  const { debouncedRender } = useMermaid(messages);
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
    imageAttachments,
    isTyping,
    selectedModel,
    setShowLLMSelector,
    submitText,
    originalHandleSubmit,
    saveLastAssistantAsWorkspaceNote,
    saveLastAssistantAsResearchArtifact,
    buildWorkspaceRequestOverrides: () => ({
      ...buildWorkspaceRequestOverrides(),
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
        onCreateWorkspaceMemory={createWorkspaceMemory}
        onUpdateWorkspaceMemory={updateWorkspaceMemory}
        onBulkUpdateWorkspaceMemoryStatusByType={bulkUpdateWorkspaceMemoryStatusByType}
        onDeleteWorkspaceMemory={deleteWorkspaceMemory}
        onApproveWorkspaceMemoryCandidate={approveWorkspaceMemoryCandidate}
        onRejectWorkspaceMemoryCandidate={rejectWorkspaceMemoryCandidate}
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
        onCreateWorkspaceMemory={createWorkspaceMemory}
        onUpdateWorkspaceMemory={updateWorkspaceMemory}
        onBulkUpdateWorkspaceMemoryStatusByType={bulkUpdateWorkspaceMemoryStatusByType}
        onDeleteWorkspaceMemory={deleteWorkspaceMemory}
        onApproveWorkspaceMemoryCandidate={approveWorkspaceMemoryCandidate}
        onRejectWorkspaceMemoryCandidate={rejectWorkspaceMemoryCandidate}
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
          onTrackWorkspaceCaptureTelemetry={trackWorkspaceCaptureTelemetry}
        />

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
