import { createSignal, onMount, onCleanup, Show, createEffect, createMemo } from 'solid-js';
import { Message, SkillSpec, VisibleSkillChip } from '../types';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import { useToast } from '../context/ToastContext';
import { getMermaidInitConfig, getMermaidThemePreset } from '../utils/mermaidTheme';
import { parseThoughtAndContent } from '../utils/thoughtParser';
import { 
  handleMermaidClick, 
  handleMermaidWheel, 
  handleMermaidChange, 
  handleMermaidPointerDown, 
  handleMermaidPointerMove, 
  handleMermaidPointerUp,
  closeMermaidExportModal,
  closeMermaidOverlay
} from '../utils/mermaidRenderer';
import ChatSidebar from '../components/ChatSidebar';
import ChatInput from '../components/ChatInput';
import MessageList from '../components/MessageList';
import IntelligencePanel from '../components/IntelligencePanel';
import { ConfirmModal } from '../components/ConfirmModal';
import { modelSupportsVision, useLLMProviders } from '../hooks/useLLMProviders';
import { useAgents } from '../hooks/useAgents';
import { canSubmitChatRequest, getAgentVisibleSkills, useChatState } from '../hooks/useChatState';
import { useMermaid } from '../hooks/useMermaid';
import { SpeechControllerProvider, useSpeechController } from '../context/SpeechControllerContext';
import { DEFAULT_PREFERENCES, Preferences, normalizePreferences } from './settings/types';
import { getSpeechMessageId } from '../utils/speech';
import { composeVoiceInputText, useVoiceInput } from '../hooks/useVoiceInput';

function ChatContent(props: { speechPrefs: () => Preferences }) {
  const toast = useToast();
  const speech = useSpeechController();
  const [requestedSkill, setRequestedSkill] = createSignal<string | null>(null);
  const [skills, setSkills] = createSignal<SkillSpec[]>([]);
  const [voiceCommitLockText, setVoiceCommitLockText] = createSignal<string | null>(null);
  const [composerKey, setComposerKey] = createSignal(1);
  const speechStatusText = createMemo(() => {
    if (!speech.supported()) return 'Read aloud is unavailable in this browser.';
    if (speech.isPaused()) return 'Read aloud paused.';
    if (speech.isSpeaking()) return 'Read aloud started.';
    return 'Read aloud stopped.';
  });
  
  // History & Knowledge State
  const [showHistory, setShowHistory] = createSignal(true); // Default to true on desktop
  const [showKnowledge, setShowKnowledge] = createSignal(false);
  const [intelligenceTab, setIntelligenceTab] = createSignal<'notes' | 'graph' | 'actions' | 'preview' | 'stats'>('actions');
  const [previewContent, setPreviewContent] = createSignal<{lang: string, content: string} | null>(null);
  const [isArtifactExpanded, setIsArtifactExpanded] = createSignal(false);
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);
  
  // Refs
  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;
  let messagesEndRef: HTMLDivElement | undefined;
  let imageInputRef: HTMLInputElement | undefined;
  let voiceCommitLockTimer: ReturnType<typeof setTimeout> | null = null;
  let voiceCommitReplayTimers: ReturnType<typeof setTimeout>[] = [];

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
    MODEL_STORAGE_KEY
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
    selectAgent
  } = useAgents(() => textareaRef);
  const currentAgent = () => agents().find(a => a.id === selectedAgent());

  const chatState = useChatState(
    selectedProvider,
    selectedModel,
    selectedAgent,
    requestedSkill,
    setShowLLMSelector
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
    setActiveSkill,
    loadChat,
    startNewChat,
    deleteChat,
    generateSummary,
    toggleThought,
    copyUserMessage,
    quoteUserMessage,
    handleRegenerate,
    lastGenerationOutcome,
    submitText,
    handleSubmit: originalHandleSubmit,
  } = chatState;
  const voiceInput = useVoiceInput(() => ({
    language: props.speechPrefs().voice_input_language,
    appLanguage: props.speechPrefs().language,
    provider: currentAgent()?.voice_input_provider === 'azure' && currentAgent()?.voice_azure_config?.api_key_configured
      ? 'azure'
      : (props.speechPrefs().voice_input_provider === 'azure' && currentAgent()?.voice_azure_config?.api_key_configured
        ? 'azure'
        : 'browser'),
    agentId: currentAgent()?.id || null,
  }));

  const focusTextareaToEnd = () => {
    if (!textareaRef) return;
    textareaRef.focus();
    const next = textareaRef.value.length;
    textareaRef.setSelectionRange(next, next);
  };

  const applyVoiceCommittedText = (next: string) => {
    setInput(next);
    if (textareaRef && textareaRef.value !== next) {
      textareaRef.value = next;
    }
  };

  const lockVoiceCommittedText = (next: string) => {
    if (voiceCommitLockTimer) clearTimeout(voiceCommitLockTimer);
    voiceCommitReplayTimers.forEach(clearTimeout);
    voiceCommitReplayTimers = [];
    setVoiceCommitLockText(next);
    voiceCommitLockTimer = setTimeout(() => {
      voiceCommitLockTimer = null;
      setVoiceCommitLockText(null);
    }, 5000);
    for (const delay of [0, 30, 80, 160, 320, 640, 1000, 1800, 3000, 4500]) {
      const timer = setTimeout(() => {
        applyVoiceCommittedText(next);
      }, delay);
      voiceCommitReplayTimers.push(timer);
    }
  };

  const clearVoiceCommitLock = () => {
    setVoiceCommitLockText(null);
    if (voiceCommitLockTimer) {
      clearTimeout(voiceCommitLockTimer);
      voiceCommitLockTimer = null;
    }
    voiceCommitReplayTimers.forEach(clearTimeout);
    voiceCommitReplayTimers = [];
  };

  createEffect(() => {
    if (props.speechPrefs().voice_input_enabled && currentAgent()?.voice_input_enabled !== false) return;
    if (voiceInput.isRecording() || voiceInput.isProcessing()) {
      voiceInput.cancelRecording();
    }
    voiceInput.clearDraft();
  });

  createEffect(() => {
    const lockedText = voiceCommitLockText();
    if (lockedText === null) return;
    applyVoiceCommittedText(lockedText);
  });
  const [lastAutoSpokenKey, setLastAutoSpokenKey] = createSignal('');

  const loadSkills = async () => {
    try {
      const res = await fetch('/api/skills');
      const data = await res.json();
      setSkills(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Failed to load skills", e);
      setSkills([]);
    }
  };

  createEffect(() => {
    selectedAgent();
    setRequestedSkill(null);
    setActiveSkill(null);
  });

  // Sync textarea height with input content
  createEffect(() => {
    const _value = input(); // Track input
    if (textareaRef) {
      textareaRef.style.height = 'auto';
      if (_value !== '') {
        textareaRef.style.height = `${textareaRef.scrollHeight}px`;
      }
    }
  });

  const handleSubmit = (e: Event) => {
    e.preventDefault();
    speech.stopCurrent();

    if (voiceInput.isRecording() || voiceInput.isProcessing()) {
      voiceInput.stopRecording();
      return;
    }

    if (voiceInput.phase() === 'ready') {
      handleInsertVoiceInput();
      return;
    }

    if (isTyping()) {
      originalHandleSubmit(e);
      return;
    }

    const trimmedInput = input().trim();
    if (!canSubmitChatRequest(trimmedInput, imageAttachments().length)) return;

    // Handle slash commands
    if (trimmedInput === '/help') {
      const helpMsg: Message = {
        role: 'assistant',
        content: 'Commands: /help /note /clear',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, helpMsg]);
      setInput('');
      return;
    }
    
    if (trimmedInput === '/clear') {
      setMessages([]);
      setInput('');
      return;
    }

    if (trimmedInput === '/note') {
      const lastAssistantMsg = [...messages()].reverse().find(m => m.role === 'assistant');
      if (lastAssistantMsg) {
        toast.success('Saved to notes.', 3000);
      } else {
        toast.error('No assistant message to save.', 3000);
      }
      setInput('');
      return;
    }

    // Regular chat message logic...
    if (!selectedModel()) {
      setShowLLMSelector(true);
      return;
    }

    originalHandleSubmit(e);
  };

  const handleContinue = (msg: Message) => {
    void msg;
    speech.stopCurrent();
    setInput("继续");
    setTimeout(() => {
      handleSubmit(new Event('submit'));
    }, 0);
  };

  const handleGenerateSummary = async (chatId: string) => {
    speech.stopCurrent();
    const summary = await generateSummary(chatId, true);
    if (summary) {
      toast.success('Summary updated');
    } else {
      toast.info('No summary generated');
    }
    if (currentChatId() === chatId) {
      await loadChat(chatId, false, setShowHistory, setSelectedAgent);
    }
  };

  const {
    debouncedRender
  } = useMermaid(messages);

  // Responsive State
  const [windowWidth, setWindowWidth] = createSignal(window.innerWidth);
  onMount(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  });
  const isMobile = () => windowWidth() < 1024;

  createEffect(() => {
    if (messages().length > 0 && !userHasScrolledUp()) {
      messagesEndRef?.scrollIntoView({ behavior: 'smooth' });
    }
  });

  // Auto-expand thoughts when streaming starts
  createEffect(() => {
    const msgs = messages();
    if (msgs.length === 0) return;
    const lastIdx = msgs.length - 1;
    const lastMsg = msgs[lastIdx];
    if (lastMsg.role === 'assistant' && isTyping()) {
      const { isThinking } = parseThoughtAndContent(lastMsg.content);
      if (isThinking && !expandedThoughts()[lastIdx]) {
        setExpandedThoughts(prev => ({ ...prev, [lastIdx]: true }));
      }
    }
  });

  createEffect(() => {
    const outcome = lastGenerationOutcome();
    const typing = isTyping();
    const prefs = props.speechPrefs();
    const msgs = messages();
    if (typing || outcome !== 'success' || !prefs.auto_speech_enabled) return;
    const lastIndex = msgs.length - 1;
    if (lastIndex < 0) return;
    const msg = msgs[lastIndex];
    if (msg.role !== 'assistant') return;
    if (!msg.content?.trim() || msg.error || msg.content.startsWith('Error:')) return;
    const messageId = getSpeechMessageId(msg, lastIndex);
    const messageKey = `${messageId}:${msg.content.length}:${msg.total_duration ?? 0}`;
    if (messageKey === lastAutoSpokenKey()) return;
    if (speech.speakMessage(messageId, msg.content)) {
      setLastAutoSpokenKey(messageKey);
    }
  });
  
  // Auto-scroll logic
  const [userHasScrolledUp, setUserHasScrolledUp] = createSignal(false);
  createEffect(() => {
    messages(); // Dependency
    if (chatContainerRef && !userHasScrolledUp()) {
      chatContainerRef.scrollTo({
        top: chatContainerRef.scrollHeight,
        behavior: isTyping() ? 'auto' : 'smooth'
      });
    }
  });

  const handleScroll = (e: Event) => {
    const target = e.currentTarget as HTMLDivElement;
    const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 100;
    setUserHasScrolledUp(!isAtBottom);
  };

  onMount(() => {
    const preset = getMermaidThemePreset();
    (mermaid as any).initialize(getMermaidInitConfig(preset));

    const storedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const storedModel = localStorage.getItem(MODEL_STORAGE_KEY);
    if (storedProvider) setSelectedProvider(storedProvider);
    if (storedModel) setSelectedModel(storedModel);

    loadProviders();
    loadSkills();

    (window as any).openArtifact = (lang: string, encodedContent: string) => {
      try {
        const content = decodeURIComponent(encodedContent);
        setPreviewContent({ lang, content });
        setIntelligenceTab('preview');
        setShowKnowledge(true);
      } catch (e) {
        console.error("Failed to open artifact:", e);
        toast.error("Failed to open artifact preview");
      }
    };

    const handleGlobalClick = () => {
      setShowLLMSelector(false);
      setShowAgentSelector(false);
    };
    window.addEventListener('click', handleGlobalClick);

    const onMermaidClick = (e: MouseEvent) => handleMermaidClick(e, (type, msg) => toast[type](msg));
    document.addEventListener('click', onMermaidClick);
    document.addEventListener('wheel', handleMermaidWheel, { passive: false });
    document.addEventListener('change', handleMermaidChange);
    document.addEventListener('pointerdown', handleMermaidPointerDown);
    document.addEventListener('pointermove', handleMermaidPointerMove, { passive: false } as any);
    document.addEventListener('pointerup', handleMermaidPointerUp);
    
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (e.defaultPrevented) return;
        closeMermaidExportModal();
        closeMermaidOverlay();
      }
    };
    document.addEventListener('keydown', handleGlobalKeyDown);

    return () => {
      window.removeEventListener('click', handleGlobalClick);
      document.removeEventListener('click', onMermaidClick);
      document.removeEventListener('wheel', handleMermaidWheel as any);
      document.removeEventListener('change', handleMermaidChange);
      document.removeEventListener('pointerdown', handleMermaidPointerDown);
      document.removeEventListener('pointermove', handleMermaidPointerMove as any);
      document.removeEventListener('pointerup', handleMermaidPointerUp);
      document.removeEventListener('keydown', handleGlobalKeyDown);
      closeMermaidExportModal();
      closeMermaidOverlay();
    };
  });

  createEffect(() => {
    messages();
    debouncedRender();
  });

  const activeAgentName = () => {
    const agent = agents().find(a => a.id === selectedAgent());
    return agent ? agent.name : 'AI Assistant';
  };

  const versionKey = (value: string) => value.split(/(\d+)/).map(token => (token.match(/^\d+$/) ? Number(token) : token));
  const compareVersion = (a: string, b: string) => {
    const ka = versionKey(a);
    const kb = versionKey(b);
    const len = Math.max(ka.length, kb.length);
    for (let i = 0; i < len; i += 1) {
      const va = ka[i];
      const vb = kb[i];
      if (va === undefined) return -1;
      if (vb === undefined) return 1;
      if (typeof va === 'number' && typeof vb === 'number') {
        if (va !== vb) return va > vb ? 1 : -1;
      } else if (String(va) !== String(vb)) {
        return String(va) > String(vb) ? 1 : -1;
      }
    }
    return 0;
  };

  const resolveSkillSpec = (nameVersion: string) => {
    if (nameVersion.includes(':')) {
      const [name, version] = nameVersion.split(':', 2);
      return skills().find(s => s.name === name && s.version === version);
    }
    const matches = skills().filter(s => s.name === nameVersion);
    if (matches.length === 0) return undefined;
    return [...matches].sort((a, b) => compareVersion(a.version, b.version)).pop();
  };

  const parseSkillReference = (skillId: string) => {
    if (!skillId.includes(':')) return { name: skillId, version: undefined as string | undefined };
    const [name, version] = skillId.split(':', 2);
    return { name, version };
  };

  const visibleSkillOptions = createMemo<VisibleSkillChip[]>(() => {
    const visibleSkillIds = getAgentVisibleSkills(currentAgent());
    return visibleSkillIds.flatMap((skillId) => {
      const spec = resolveSkillSpec(skillId);
      if (spec?.availability === false) return [];
      if (spec) return [{ id: skillId, name: spec.name, version: spec.version }];
      const parsed = parseSkillReference(skillId);
      return [{ id: skillId, name: parsed.name, version: parsed.version }];
    });
  });

  const handleMentionSelect = (agent: any) => {
    selectAgent(agent, input(), setInput);
  };

  const handleModelSelect = (provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
    localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
    localStorage.setItem(MODEL_STORAGE_KEY, model);

    // If switched to a model that doesn't support vision, clear image attachments
    if (imageAttachments().length > 0 && !modelSupportsVision(providers(), provider, model)) {
      setImageAttachments([]);
      toast.info('已自动清空图片，当前模型不支持视觉能力。', 3500);
    }
  };

  const handleRefreshModels = async () => {
    setIsRefreshingModels(true);
    try {
      await loadProviders(true);
    } finally {
      setIsRefreshingModels(false);
    }
  };

  const handleInput = (e: InputEvent & { currentTarget: HTMLTextAreaElement }) => {
    const target = e.currentTarget;
    const value = target.value;
    voiceInput.clearError();

    const lockedText = voiceCommitLockText();
    if (lockedText !== null && value !== lockedText) {
      target.value = lockedText;
      setInput(lockedText);
      return;
    }
    if (lockedText !== null && value === lockedText) {
      clearVoiceCommitLock();
    }

    if (voiceInput.phase() !== 'idle') {
      const voiceOnlyPreview = composeVoiceInputText(
        voiceInput.baseText(),
        voiceInput.transcript(),
        voiceInput.interimTranscript(),
        true,
      );
      const voiceCommittedPreview = composeVoiceInputText(
        voiceInput.baseText(),
        voiceInput.transcript(),
        '',
        false,
      );
      if (value === voiceOnlyPreview || value === voiceCommittedPreview) {
        target.value = input();
        return;
      }
    }
    
    const pos = target.selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');

    if (lastAtPos !== -1 && (lastAtPos === 0 || textBefore[lastAtPos - 1] === ' ')) {
      setShowAgentSelector(true);
      setAgentFilter(textBefore.substring(lastAtPos + 1));
      setSelectedIndex(0);
    } else {
      setShowAgentSelector(false);
    }
    setInput(value);
  };

  const handleToggleVoiceInput = async () => {
    voiceInput.clearError();
    if (voiceInput.isRecording() || voiceInput.isProcessing()) {
      voiceInput.stopRecording();
      return;
    }
    setComposerKey((key) => key + 1);
    await voiceInput.startRecording(input());
  };

  const handleCancelVoiceInput = () => {
    if (voiceInput.isRecording() || voiceInput.isProcessing()) {
      voiceInput.cancelRecording();
      setComposerKey((key) => key + 1);
      return;
    }
    voiceInput.clearDraft();
    setComposerKey((key) => key + 1);
  };

  const handleInsertVoiceInput = (options?: { lock?: boolean; focus?: boolean }) => {
    const shouldLock = options?.lock ?? true;
    const shouldFocus = options?.focus ?? true;
    const next = voiceInput.consumeDraft();
    if (shouldLock) {
      lockVoiceCommittedText(next);
    } else {
      clearVoiceCommitLock();
    }
    applyVoiceCommittedText(next);
    setComposerKey((key) => key + 1);
    if (shouldFocus) {
      queueMicrotask(() => focusTextareaToEnd());
    }
  };

  const handleInsertAndSubmitVoiceInput = () => {
    const next = voiceInput.consumeDraft();
    clearVoiceCommitLock();
    setComposerKey((key) => key + 1);
    speech.stopCurrent();
    void submitText(next);
  };

  const handleVoiceDraftShortcut = (e: KeyboardEvent): boolean => {
    if (voiceInput.phase() !== 'ready') return false;
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleInsertAndSubmitVoiceInput();
      return true;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleInsertVoiceInput();
      return true;
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelVoiceInput();
      return true;
    }
    return false;
  };

  createEffect(() => {
    if (voiceInput.phase() !== 'ready') return;
    queueMicrotask(() => focusTextareaToEnd());
  });

  onMount(() => {
    const onWindowKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      handleVoiceDraftShortcut(event);
    };
    window.addEventListener('keydown', onWindowKeyDown);
    onCleanup(() => {
      window.removeEventListener('keydown', onWindowKeyDown);
    });
  });

  const handleKeyDown = (e: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => {
    if (voiceCommitLockText() !== null && voiceInput.phase() === 'idle') {
      const isModifier = e.metaKey || e.ctrlKey || e.altKey;
      const editableKey =
        e.key.length === 1 ||
        e.key === 'Backspace' ||
        e.key === 'Delete' ||
        e.key === 'Enter' ||
        e.key === 'Tab';
      if (!isModifier && editableKey) {
        clearVoiceCommitLock();
      }
    }
    if (handleVoiceDraftShortcut(e)) return;
    if (showAgentSelector()) {
      const list = filteredAgents();
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() + 1) % list.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() - 1 + list.length) % list.length);
      } else if (e.key === 'Enter' && list.length > 0) {
        e.preventDefault();
        handleMentionSelect(list[selectedIndex()]);
      } else if (e.key === 'Escape') {
        setShowAgentSelector(false);
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div class="flex h-full bg-background overflow-hidden relative">
      <div class="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {speechStatusText()}
      </div>
      <ChatSidebar 
        showHistory={showHistory()} 
        chats={chats()} 
        currentChatId={currentChatId()} 
        onNewChat={() => {
          speech.stopCurrent();
          startNewChat(isMobile(), setShowHistory);
        }} 
        onLoadChat={(id) => {
          speech.stopCurrent();
          loadChat(id, isMobile(), setShowHistory, setSelectedAgent);
        }} 
        onDeleteChat={(id) => setConfirmDeleteId(id)} 
        onGenerateSummary={handleGenerateSummary}
      />

      {/* 2. Main Chat Area (flex) */}
      <div class="flex-1 flex flex-col h-full min-w-0 bg-background relative">
        {/* Chat Header */}
        <div class="h-16 px-6 border-b border-border flex items-center justify-between bg-surface/80 backdrop-blur-md z-10 sticky top-0">
          <div class="flex items-center gap-4 min-w-0">
            <button 
              onClick={() => setShowHistory(!showHistory())} 
              class="p-2 -ml-2 text-text-secondary hover:bg-primary/10 rounded-xl transition-all active:scale-90"
              title={showHistory() ? "Hide History" : "Show History"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            
            <div class="flex items-center gap-3.5 truncate">
              <div class="relative">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary font-bold shrink-0 border border-primary/10 shadow-sm overflow-hidden">
                  <Show when={currentAgent()?.avatar} fallback={activeAgentName().charAt(0)}>
                    <img src={currentAgent()?.avatar} alt={activeAgentName()} class="w-full h-full object-cover" />
                  </Show>
                </div>
                <div class={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-surface ${isTyping() ? 'bg-primary animate-pulse' : 'bg-emerald-500'}`}></div>
              </div>
              <div class="truncate">
                <h3 class="font-bold text-text-primary text-base truncate leading-tight">{activeAgentName()}</h3>
                <p class="text-[11px] text-text-secondary font-medium uppercase tracking-widest opacity-70">
                  {isTyping() ? 'Processing Intelligence...' : 'System Ready'}
                </p>
              </div>
            </div>
            <Show when={currentAgent()?.skill_mode && currentAgent()?.skill_mode !== 'off'}>
              <div class="hidden md:flex items-center gap-2 ml-4">
                <span class="text-[10px] uppercase tracking-wider font-bold text-violet-700 bg-violet-100 border border-violet-200 rounded-full px-2 py-1">
                  {currentAgent()?.skill_mode}
                </span>
                <Show when={activeSkill()}>
                  <span class="text-[10px] font-bold text-emerald-700 bg-emerald-100 border border-emerald-200 rounded-full px-2 py-1">
                    Active: {activeSkill()!.name}@{activeSkill()!.version}
                  </span>
                </Show>
              </div>
            </Show>
          </div>
          
          <div class="flex items-center gap-2">
            <button 
              onClick={() => setShowKnowledge(!showKnowledge())}
              class={`p-2.5 rounded-xl transition-all duration-300 active:scale-90 ${showKnowledge() ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-text-secondary hover:bg-primary/10 hover:text-primary'}`}
              title="Toggle Knowledge Intelligence"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* Messages Container */}
        <MessageList 
          chatContainerRef={el => chatContainerRef = el}
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
          onContinue={handleContinue}
          messagesEndRef={el => messagesEndRef = el}
          setInput={setInput}
          selectedProvider={selectedProvider()}
          selectedModel={selectedModel()}
        />

        {/* 3. Unified Input Center (Phase 1.3) */}
        <ChatInput 
          showAgentSelector={showAgentSelector()}
          filteredAgents={filteredAgents()}
          selectedIndex={selectedIndex()}
          selectAgent={handleMentionSelect}
          input={input()}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          onSubmit={handleSubmit}
          isTyping={isTyping()}
          activeAgentName={activeAgentName()}
          textareaRef={el => textareaRef = el}
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
          imageInputRef={el => imageInputRef = el}
          visibleSkills={visibleSkillOptions()}
          requestedSkill={requestedSkill()}
          onSelectSkill={setRequestedSkill}
          skillMode={currentAgent()?.skill_mode}
          voiceInputEnabled={props.speechPrefs().voice_input_enabled && currentAgent()?.voice_input_enabled !== false}
          voiceInputSupported={voiceInput.supported()}
          voiceInputProvider={voiceInput.provider()}
          voiceInputPreferredProvider={voiceInput.preferredProvider()}
          voiceInputIsRecording={voiceInput.isRecording()}
          voiceInputIsProcessing={voiceInput.isProcessing()}
          voiceInputHasDraft={voiceInput.hasDraft()}
          voiceInputPhase={voiceInput.phase()}
          voiceInputPreviewText={props.speechPrefs().voice_input_show_interim ? voiceInput.previewText() : ''}
          voiceInputInterimTranscript={voiceInput.interimTranscript()}
          voiceInputError={voiceInput.error()}
          voiceInputFallbackMessage={voiceInput.fallbackMessage()}
          onToggleVoiceInput={() => { void handleToggleVoiceInput(); }}
          onCancelVoiceInput={handleCancelVoiceInput}
          onInsertVoiceInput={handleInsertVoiceInput}
          onSendVoiceInput={handleInsertAndSubmitVoiceInput}
        />
      </div>

      {/* 4. Intelligence Hub */}
      <IntelligencePanel 
        showKnowledge={showKnowledge()}
        setShowKnowledge={setShowKnowledge}
        isArtifactExpanded={isArtifactExpanded()}
        setIsArtifactExpanded={setIsArtifactExpanded}
        intelligenceTab={intelligenceTab()}
        setIntelligenceTab={setIntelligenceTab}
        previewContent={previewContent()}
        lastMessage={[...messages()].reverse().find(m => m.role === 'assistant')}
        isMobile={isMobile()}
      />
      
      {/* Mobile Overlays */}
      {(showHistory() || (showKnowledge() && isMobile())) && (
        <div 
          onClick={() => { setShowHistory(false); setShowKnowledge(false); }}
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
    </div>
  );
}

export default function Chat() {
  const [speechPrefs, setSpeechPrefs] = createSignal<Preferences>(DEFAULT_PREFERENCES);

  onMount(async () => {
    try {
      const res = await fetch('/api/config/preferences');
      const raw = await res.json();
      setSpeechPrefs(normalizePreferences(raw));
    } catch (e) {
      console.warn('Failed to load speech preferences', e);
    }
  });

  return (
    <SpeechControllerProvider prefs={speechPrefs}>
      <ChatContent speechPrefs={speechPrefs} />
    </SpeechControllerProvider>
  );
}
