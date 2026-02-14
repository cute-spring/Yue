import { createSignal, onMount, Show, createEffect } from 'solid-js';
import { Message } from '../types';
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
import { useLLMProviders } from '../hooks/useLLMProviders';
import { useAgents } from '../hooks/useAgents';
import { useChatState } from '../hooks/useChatState';
import { useMermaid } from '../hooks/useMermaid';

export default function Chat() {
  const toast = useToast();
  
  // History & Knowledge State
  const [showHistory, setShowHistory] = createSignal(true); // Default to true on desktop
  const [showKnowledge, setShowKnowledge] = createSignal(false);
  const [intelligenceTab, setIntelligenceTab] = createSignal<'notes' | 'graph' | 'actions' | 'preview'>('actions');
  const [previewContent, setPreviewContent] = createSignal<{lang: string, content: string} | null>(null);
  const [isArtifactExpanded, setIsArtifactExpanded] = createSignal(false);
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);
  
  // Refs
  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;
  let messagesEndRef: HTMLDivElement | undefined;
  let imageInputRef: HTMLInputElement | undefined;

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

  const chatState = useChatState(
    selectedProvider,
    selectedModel,
    selectedAgent,
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
    loadChat,
    startNewChat,
    deleteChat,
    toggleThought,
    copyUserMessage,
    quoteUserMessage,
    handleRegenerate,
    handleSubmit: originalHandleSubmit,
  } = chatState;

  const handleSubmit = (e: Event) => {
    e.preventDefault();
    const trimmedInput = input().trim();
    if (!trimmedInput || isTyping()) return;

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
        setInlineToast({ message: 'Saved to notes.', type: 'success' });
        setTimeout(() => setInlineToast(null), 3000);
      } else {
        setInlineToast({ message: 'No assistant message to save.', type: 'error' });
        setTimeout(() => setInlineToast(null), 3000);
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

  // Additional UI State
  const [inlineToast, setInlineToast] = createSignal<{ type: 'success' | 'error' | 'info', message: string } | null>(null);

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

  const currentAgent = () => agents().find(a => a.id === selectedAgent());

  const handleMentionSelect = (agent: any) => {
    selectAgent(agent, input(), setInput);
  };

  const handleModelSelect = (provider: string, model: string) => {
    setSelectedProvider(provider);
    setSelectedModel(model);
    localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
    localStorage.setItem(MODEL_STORAGE_KEY, model);
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
    
    // Auto-expand height
    target.style.height = 'auto';
    target.style.height = `${target.scrollHeight}px`;

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

  const handleKeyDown = (e: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => {
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
      <ChatSidebar 
        showHistory={showHistory()} 
        chats={chats()} 
        currentChatId={currentChatId()} 
        onNewChat={() => startNewChat(isMobile(), setShowHistory)} 
        onLoadChat={(id) => loadChat(id, isMobile(), setShowHistory, setSelectedAgent)} 
        onDeleteChat={(id) => setConfirmDeleteId(id)} 
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
          </div>
          
          <div class="flex items-center gap-2">
            <button 
              onClick={() => setShowKnowledge(!showKnowledge())}
              class={`p-2.5 rounded-xl transition-all duration-300 active:scale-90 ${showKnowledge() ? 'bg-primary text-white shadow-lg shadow-primary/20' : 'text-text-secondary hover:bg-primary/10 hover:text-primary'}`}
              title="Toggle Knowledge Intelligence"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5.5 w-5.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
        isMobile={isMobile()}
      />
      
      <Show when={inlineToast()}>
        <div class="fixed bottom-6 right-6 z-[2000]">
          <div
            class={`px-4 py-3 rounded-2xl border shadow-2xl backdrop-blur-md flex items-center gap-3 min-w-[240px] ${
              inlineToast()!.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200'
                : inlineToast()!.type === 'error'
                  ? 'bg-rose-500/10 border-rose-500/20 text-rose-200'
                  : 'bg-slate-500/10 border-slate-500/20 text-slate-200'
            }`}
          >
            <div class={`w-2 h-2 rounded-full ${inlineToast()!.type === 'success' ? 'bg-emerald-400' : inlineToast()!.type === 'error' ? 'bg-rose-400' : 'bg-slate-300'}`} />
            <div class="text-sm font-bold">{inlineToast()!.message}</div>
            <button
              type="button"
              onClick={() => setInlineToast(null)}
              class="ml-auto p-1.5 rounded-xl hover:bg-white/10 text-white/70 hover:text-white transition-colors"
              aria-label="Close"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </Show>

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
            deleteChat(id);
            setConfirmDeleteId(null);
          }
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
