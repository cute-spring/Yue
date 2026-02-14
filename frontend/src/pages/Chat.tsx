import { createSignal, For, onMount, Show, createEffect, Switch, Match } from 'solid-js';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import MermaidViewer from '../components/MermaidViewer';
import { useToast } from '../context/ToastContext';
import { getMermaidInitConfig, getMermaidThemePreset } from '../utils/mermaidTheme';
import { parseThoughtAndContent } from '../utils/thoughtParser';
import { renderMarkdown } from '../utils/markdown';
import { Agent, ChatSession, Message, Provider } from '../types';
import { 
  renderMermaidChart, 
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

const PROVIDER_STORAGE_KEY = 'yue_selected_provider';
const MODEL_STORAGE_KEY = 'yue_selected_model';

export default function Chat() {
  const toast = useToast();
  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    toast[type](message);
  };
  
  // History & Knowledge State
  const [chats, setChats] = createSignal<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = createSignal<string | null>(null);
  const [showHistory, setShowHistory] = createSignal(true); // Default to true on desktop
  const [showKnowledge, setShowKnowledge] = createSignal(false);
  const [intelligenceTab, setIntelligenceTab] = createSignal<'notes' | 'graph' | 'actions' | 'preview'>('actions');
  const [previewContent, setPreviewContent] = createSignal<{lang: string, content: string} | null>(null);
  const [isArtifactExpanded, setIsArtifactExpanded] = createSignal(false);
  
  // Chat State
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string | null>(null);
  const [providers, setProviders] = createSignal<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = createSignal<string>("");
  const [selectedModel, setSelectedModel] = createSignal<string>("");
  const [showLLMSelector, setShowLLMSelector] = createSignal(false);
  const [showAgentSelector, setShowAgentSelector] = createSignal(false);
  const [agentFilter, setAgentFilter] = createSignal("");
  const [selectedIndex, setSelectedIndex] = createSignal(0);
  const [copiedMessageIndex, setCopiedMessageIndex] = createSignal<number | null>(null);
  const [expandedThoughts, setExpandedThoughts] = createSignal<Record<number, boolean>>({});
  
  // Refs
  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;
  let messagesEndRef: HTMLDivElement | undefined;
  
  // Responsive State
  const [windowWidth, setWindowWidth] = createSignal(window.innerWidth);
  onMount(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  });
  const isMobile = () => windowWidth() < 1024;

  // Additional UI State
  const [imageAttachments, setImageAttachments] = createSignal<File[]>([]);
  const [elapsedTime, setElapsedTime] = createSignal(0);
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  const [showAllModels, setShowAllModels] = createSignal(false);
  const [isRefreshingModels, setIsRefreshingModels] = createSignal(false);
  const [inlineToast, setInlineToast] = createSignal<{ type: 'success' | 'error' | 'info', message: string } | null>(null);
  let timerInterval: any = null;
  let imageInputRef: HTMLInputElement | undefined;

  const toggleThought = (index: number) => {
    setExpandedThoughts(prev => ({ ...prev, [index]: !prev[index] }));
  };

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
  
  let abortController: AbortController | null = null;

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

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const filteredAgents = () => {
    const filter = agentFilter().toLowerCase();
    return agents().filter(a => a.name.toLowerCase().includes(filter));
  };

  const adjustHeight = () => {
    if (textareaRef) {
      textareaRef.style.height = 'auto';
      textareaRef.style.height = Math.min(textareaRef.scrollHeight, 200) + 'px';
    }
  };

  const copyUserMessage = async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageIndex(index);
      setTimeout(() => setCopiedMessageIndex(curr => (curr === index ? null : curr)), 1600);
    } catch (e) {
      toast.error("Failed to copy message");
    }
  };

  const quoteUserMessage = (content: string) => {
    const quoted = content.split('\n').map(line => `> ${line}`).join('\n');
    const base = input().trim().length ? `${input()}\n\n${quoted}\n\n` : `${quoted}\n\n`;
    setInput(base);
    setTimeout(() => {
      adjustHeight();
      textareaRef?.focus();
      textareaRef?.setSelectionRange(base.length, base.length);
    }, 0);
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
    adjustHeight();
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
        selectAgent(list[selectedIndex()]);
      } else if (e.key === 'Escape') {
        setShowAgentSelector(false);
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const selectAgent = (agent: Agent) => {
    const value = input();
    const pos = textareaRef?.selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');
    
    const newValue = value.substring(0, lastAtPos) + value.substring(pos);
    setInput(newValue);
    setSelectedAgent(agent.id);
    setShowAgentSelector(false);
  };

  const loadAgents = async () => {
    try {
      const res = await fetch('/api/agents/');
      const data = await res.json();
      setAgents(data);
    } catch (e) {
      console.error("Failed to load agents", e);
      toast.error("Failed to load agents");
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch('/api/chat/history');
      setChats(await res.json());
    } catch (e) {
      console.error("Failed to load history", e);
      toast.error("Failed to load chat history");
    }
  };

  const loadProviders = async (refresh = false) => {
    try {
      const res = await fetch(`/api/models/providers${refresh ? '?refresh=1' : ''}`);
      const data = await res.json();
      setProviders(data);
      if (refresh) {
        toast.success("Models refreshed");
      }

      let currentProvider = data.find((p: any) => p.name === selectedProvider());

      if (!currentProvider && selectedModel()) {
        const providerByModel = data.find((p: any) => (p.available_models || []).includes(selectedModel()));
        if (providerByModel) {
          currentProvider = providerByModel;
          setSelectedProvider(providerByModel.name);
        }
      }

      if (selectedProvider() && (!currentProvider || !currentProvider.configured)) {
        setSelectedProvider("");
        setSelectedModel("");
        localStorage.removeItem(PROVIDER_STORAGE_KEY);
        localStorage.removeItem(MODEL_STORAGE_KEY);
        return;
      }

      if (currentProvider) {
        const availableModels = currentProvider.available_models || [];
        if (selectedModel() && !availableModels.includes(selectedModel())) {
          setSelectedModel("");
          localStorage.removeItem(MODEL_STORAGE_KEY);
        }
      }
    } catch (e) {
      console.error("Failed to load providers", e);
      toast.error("Failed to load AI providers");
    }
  };

  const loadChat = async (id: string) => {
    if (isTyping()) stopGeneration();
    try {
      const res = await fetch(`/api/chat/${id}`);
      const data = await res.json();
      setCurrentChatId(data.id);
      setMessages(data.messages);
      setSelectedAgent(data.agent_id);
      if (isMobile()) {
        setShowHistory(false); // On mobile, close sidebar after selection
      }
    } catch (e) {
      console.error("Failed to load chat", e);
      toast.error("Failed to load chat session");
    }
  };

  const startNewChat = () => {
    if (isTyping()) stopGeneration();
    setCurrentChatId(null);
    setMessages([]);
    setInput("");
    if (textareaRef) {
      textareaRef.style.height = 'auto';
    }
    // Only close sidebar on mobile to avoid jumping on desktop
    if (isMobile()) {
      setShowHistory(false);
    }
  };

  const deleteChat = async (id: string, e: Event) => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    try {
      await fetch(`/api/chat/${id}`, { method: 'DELETE' });
      loadHistory();
      if (currentChatId() === id) startNewChat();
      toast.success("Chat deleted successfully");
    } catch (e) {
      toast.error("Failed to delete chat");
    }
  };
  
  onMount(() => {
    const preset = getMermaidThemePreset();
    (mermaid as any).initialize(getMermaidInitConfig(preset));

    const storedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const storedModel = localStorage.getItem(MODEL_STORAGE_KEY);
    if (storedProvider) setSelectedProvider(storedProvider);
    if (storedModel) setSelectedModel(storedModel);

    loadAgents();
    loadHistory();
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

    const onMermaidClick = (e: MouseEvent) => handleMermaidClick(e, showToast);
    document.addEventListener('click', onMermaidClick);
    document.addEventListener('wheel', handleMermaidWheel, { passive: false });
    document.addEventListener('change', handleMermaidChange);
    document.addEventListener('pointerdown', handleMermaidPointerDown);
    document.addEventListener('pointermove', handleMermaidPointerMove, { passive: false } as any);
    document.addEventListener('pointerup', handleMermaidPointerUp);
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (e.defaultPrevented) return;
        closeMermaidExportModal();
        closeMermaidOverlay();
      }
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('click', handleGlobalClick);
      document.removeEventListener('click', onMermaidClick);
      document.removeEventListener('wheel', handleMermaidWheel as any);
      document.removeEventListener('change', handleMermaidChange);
      document.removeEventListener('pointerdown', handleMermaidPointerDown);
      document.removeEventListener('pointermove', handleMermaidPointerMove as any);
      document.removeEventListener('pointerup', handleMermaidPointerUp);
      document.removeEventListener('keydown', handleKeyDown);
      closeMermaidExportModal();
      closeMermaidOverlay();
    };
  });

  // Debounced mermaid renderer to avoid flickering during streaming
  let renderTimeout: any;
  const debouncedRender = () => {
    if (renderTimeout) clearTimeout(renderTimeout);
    renderTimeout = setTimeout(() => {
      requestAnimationFrame(() => {
        const charts = document.querySelectorAll('.mermaid-chart:not([data-processed="true"])');
        charts.forEach(async (container) => {
          const widget = container.closest('.mermaid-widget');
          if (widget?.getAttribute('data-complete') === 'true') {
            await renderMermaidChart(container);
          }
        });
      });
    }, 100);
  };

  createEffect(() => {
    messages();
    debouncedRender();
  });

  const handleRegenerate = async (index: number) => {
    if (isTyping()) return;
    
    // Find the last user message before this assistant message
    const historyBefore = messages().slice(0, index);
    const lastUserMsgIndex = historyBefore.findLastIndex(m => m.role === 'user');
    
    if (lastUserMsgIndex === -1) return;
    
    const lastUserMsg = historyBefore[lastUserMsgIndex];
    
    // Truncate backend history if we have a chat ID
    if (currentChatId()) {
      try {
        await fetch(`/api/chat/${currentChatId()}/truncate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keep_count: lastUserMsgIndex })
        });
      } catch (e) {
        console.error("Failed to truncate chat history", e);
      }
    }

    // Keep messages BEFORE the user message (effectively removing the user message and everything after)
    // The user message will be re-added by handleSubmit
    setMessages(messages().slice(0, lastUserMsgIndex));
    setInput(lastUserMsg.content);
    
    // Trigger submit
    handleSubmit(new Event('submit') as any);
  };
  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
      setIsTyping(false);
      clearInterval(timerInterval);
    }
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    const text = input().trim();
    if (!text) return;
    
    if (text.startsWith('/')) {
      const cmd = text.split(/\s+/)[0].toLowerCase();
      if (cmd === '/help') {
        setMessages([...messages(), { role: 'assistant', content: 'Commands: /help /note /clear' }]);
        setInput('');
        return;
      }
      if (cmd === '/clear') {
        startNewChat();
        return;
      }
      if (cmd === '/note') {
        const last = [...messages()].reverse().find(m => m.role === 'assistant' && m.content && m.content.trim().length > 0);
        if (last) {
          const title = last.content.slice(0, 50);
          try {
            await fetch('/api/notebook/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ title: title || 'Saved from chat', content: last.content })
            });
            setMessages([...messages(), { role: 'assistant', content: 'Saved to notes.' }]);
          } catch (e) {
            setMessages([...messages(), { role: 'assistant', content: 'Save failed.' }]);
          }
        } else {
          setMessages([...messages(), { role: 'assistant', content: 'No assistant message to save.' }]);
        }
        setInput('');
        return;
      }
    }
    
    if (!selectedModel()) {
      setShowLLMSelector(true);
      const last = messages()[messages().length - 1];
      if (!last || last.role !== 'assistant' || last.content !== 'Please select a model before starting a chat.') {
        setMessages([...messages(), { role: 'assistant', content: 'Please select a model before starting a chat.' }]);
      }
      return;
    }

    if (isTyping()) {
      stopGeneration();
      return;
    }
    
    const agentId = selectedAgent() || undefined;

    // Convert images to base64
    const currentImages = imageAttachments();
    let base64Images: string[] = [];
    if (currentImages.length > 0) {
      try {
        base64Images = await Promise.all(currentImages.map(fileToBase64));
      } catch (e) {
        console.error("Failed to convert images", e);
        toast.error("Failed to process attached images");
      }
    }

    const nowIso = new Date().toISOString();
    const contextId = currentChatId() || undefined;
    setMessages([...messages(), { role: 'user', content: text, images: base64Images, timestamp: nowIso, context_id: contextId }]);
    setInput("");
    setImageAttachments([]); // Clear attachments
    if (textareaRef) {
      textareaRef.style.height = 'auto';
    }
    setIsTyping(true);
    setElapsedTime(0);
    const startTime = Date.now();
    let firstTokenTime: number | null = null;

    timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);

    setMessages(prev => [...prev, { role: 'assistant', content: "", timestamp: nowIso, provider: selectedProvider(), model: selectedModel(), context_id: contextId, tools: [], citations: [] }]);

    abortController = new AbortController();

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          images: base64Images.length > 0 ? base64Images : undefined,
          agent_id: agentId,
          chat_id: currentChatId(),
          provider: selectedProvider(),
          model: selectedModel(),
        }),
        signal: abortController.signal
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.chat_id) {
                  setCurrentChatId(data.chat_id);
                  setMessages(prev => prev.map(m => m.context_id ? m : { ...m, context_id: data.chat_id }));
                  loadHistory();
                } else if (data.meta) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = {
                      ...newMsgs[lastIndex],
                      provider: data.meta.provider ?? newMsgs[lastIndex].provider,
                      model: data.meta.model ?? newMsgs[lastIndex].model,
                      tools: data.meta.tools ?? newMsgs[lastIndex].tools,
                      context_id: data.meta.context_id ?? newMsgs[lastIndex].context_id
                    };
                    return newMsgs;
                  });
                } else if (data.content || data.thought) {
                  if (!firstTokenTime) {
                    firstTokenTime = Date.now();
                    const ttft = firstTokenTime - startTime;
                    setMessages(prev => {
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      newMsgs[lastIndex] = { ...newMsgs[lastIndex], ttft };
                      return newMsgs;
                    });
                  }
                  
                  if (data.content) {
                    accumulatedResponse += data.content;
                    setMessages(prev => {
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
                      return newMsgs;
                    });
                  }
                } else if (data.thought_duration) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], thought_duration: data.thought_duration };
                    return newMsgs;
                  });
                } else if (data.total_duration) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration: data.total_duration * 1000 };
                    return newMsgs;
                  });
                } else if (data.prompt_tokens !== undefined || data.completion_tokens !== undefined || data.total_tokens !== undefined || data.tps !== undefined || data.finish_reason !== undefined) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { 
                      ...newMsgs[lastIndex], 
                      prompt_tokens: data.prompt_tokens,
                      completion_tokens: data.completion_tokens,
                      total_tokens: data.total_tokens,
                      tps: data.tps,
                      finish_reason: data.finish_reason
                    };
                    return newMsgs;
                  });
                } else if (data.citations) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], citations: data.citations };
                    return newMsgs;
                  });
                } else if (data.error) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: `Error: ${data.error}`, error: data.error };
                    return newMsgs;
                  });
                }
              } catch (e) {
                console.warn("Failed to parse stream message", e);
              }
            }
          }
        }
      }

      // Record total duration after stream finishes
      const total_duration = Date.now() - startTime;
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIndex = newMsgs.length - 1;
        newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration };
        return newMsgs;
      });
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user');
      } else {
        console.error("Chat error:", err);
        toast.error("Connection error: " + (err.message || "Unknown error"));
      }
    } finally {
      setIsTyping(false);
      clearInterval(timerInterval);
      abortController = null;
    }
  };

  const activeAgentName = () => {
    const agent = agents().find(a => a.id === selectedAgent());
    return agent ? agent.name : 'AI Assistant';
  };

  const formatTime = (value?: string) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit' }).format(date);
  };

  const formatTokenCount = (n: number) => {
    return (n / 1000).toFixed(1) + 'k';
  };

  const readStatus = (index: number) => {
    const later = messages().slice(index + 1);
    const hasAssistant = later.some(m => m.role === 'assistant' && m.content && m.content.trim().length > 0);
    return hasAssistant ? "Read" : "Sent";
  };

  const responseStatus = (msg: Message, index: number) => {
    if (msg.error || (msg.content && msg.content.startsWith("Error:"))) return "Failed";
    if (msg.role === "assistant" && isTyping() && index === messages().length - 1) return "Generating";
    return "Completed";
  };

  const renderThought = (thought: string | null) => {
    if (!thought) return null;
    
    let processedThought = thought;
    const protocolTags = [
      { tag: '[目标]', icon: '🎯', color: 'text-blue-500', bg: 'bg-blue-500/10' },
      { tag: '[已知条件]', icon: '📋', color: 'text-amber-500', bg: 'bg-amber-500/10' },
      { tag: '[计划]', icon: '🗺️', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
      { tag: '[反思]', icon: '🔄', color: 'text-rose-500', bg: 'bg-rose-500/10' },
    ];
    
    protocolTags.forEach(({ tag, icon, color, bg }) => {
      const escapedTag = tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(\\*\\*)?${escapedTag}(\\*\\*)?`, 'g');
      processedThought = processedThought.replace(regex, `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-current/10 ${color} ${bg} font-bold text-[11px] mr-1"><span>${icon}</span><span>${tag}</span></span>`);
    });

    return (
      <div 
        class="prose prose-sm dark:prose-invert max-w-none opacity-90 leading-relaxed font-sans"
        innerHTML={renderMarkdown(processedThought)}
      />
    );
  };

  const modelLabel = (msg: Message) => {
    const provider = msg.provider || selectedProvider();
    const model = msg.model || selectedModel();
    if (provider && model) return `${provider}/${model}`;
    if (model) return model;
    return "Unknown model";
  };

  const renderMetaBadges = (msg: Message, index: number) => {
    const isUser = msg.role === 'user';
    const [hoveredMetric, setHoveredMetric] = createSignal<string | null>(null);

    // Unified High-End Metric Popover Component
    const MetricPopover = (props: { title: string; label: string; value: string | number; icon?: any; description?: string }) => {
      const isVisible = () => hoveredMetric() === props.label;

      return (
        <div 
          class="relative flex items-center"
          onMouseEnter={() => setHoveredMetric(props.label)}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface/50 border border-border/40 text-[10px] font-medium text-text-secondary/80 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 cursor-default">
            {props.icon}
            <span class="opacity-50 font-bold uppercase tracking-tighter text-[9px]">{props.label}</span>
            <span class="font-semibold text-text-primary/90">{props.value}</span>
          </div>
          
          {/* Advanced Popover Card */}
          <div 
            class={`absolute top-full left-1/2 -translate-x-1/2 mt-2 w-48 pointer-events-none transition-all duration-300 ease-out z-[100] ${
              isVisible() ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
            }`}
          >
            <div class="bg-white/95 backdrop-blur-xl border border-border/50 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-xl p-3 overflow-hidden">
              <div class="flex items-center gap-2 mb-1.5">
                <div class="p-1.5 rounded-lg bg-primary/10 text-primary">
                  {props.icon}
                </div>
                <div class="font-bold text-[11px] text-text-primary tracking-tight">
                  {props.title}
                </div>
              </div>
              <div class="text-[10px] leading-relaxed text-text-secondary/90 font-medium">
                {props.description}
              </div>
              <div class="mt-2 pt-2 border-t border-border/30 flex justify-between items-center">
                <span class="text-[9px] text-text-secondary/50 font-bold uppercase">{props.label}</span>
                <span class="text-[10px] font-bold text-primary">{props.value}</span>
              </div>
            </div>
            {/* Elegant Arrow */}
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-white/95"></div>
          </div>
        </div>
      );
    };

    return (
      <div class={`mt-4 flex flex-wrap items-center gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
        {/* Time */}
        <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-text-secondary/5 border border-border/40 text-[10px] font-medium text-text-secondary/70">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {formatTime(msg.timestamp)}
        </div>

        <Show when={isUser}>
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-text-secondary/5 border border-border/40 text-[10px] font-medium text-text-secondary/70">
             <Show when={readStatus(index) === 'Read'} fallback={<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><path d="m5 12 5 5L20 7"/></svg>}>
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-primary"><path d="M2 17L12 22L22 17"/><path d="M2 12L12 17L22 12"/><path d="M12 2L2 7L12 12L22 7L12 2Z"/></svg>
             </Show>
            {readStatus(index)}
          </div>
        </Show>

        <Show when={!isUser}>
          {/* Model Info */}
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/5 border border-primary/10 text-[10px] font-bold text-primary/80 uppercase tracking-tight shadow-sm shadow-primary/5">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            {modelLabel(msg)}
          </div>

          {/* Status */}
          <div class={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold uppercase tracking-tight ${
            responseStatus(msg, index) === 'Failed' 
              ? 'bg-rose-500/5 border-rose-500/20 text-rose-500' 
              : responseStatus(msg, index) === 'Generating' 
                ? 'bg-amber-500/5 border-amber-500/20 text-amber-500' 
                : 'bg-emerald-500/5 border-emerald-500/20 text-emerald-500 shadow-sm shadow-emerald-500/5'
          }`}>
            <Show when={responseStatus(msg, index) === 'Generating'}>
              <div class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
            </Show>
            <Show when={responseStatus(msg, index) === 'Completed'}>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </Show>
            {responseStatus(msg, index)}
          </div>

          {/* Performance Metrics Group */}
          <div class="flex items-center gap-2">
            <Show when={msg.ttft}>
              <MetricPopover 
                title="First Token Latency"
                label="TTFT"
                value={`${(msg.ttft! / 1000).toFixed(2)}s`}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>}
                description="The time taken from sending the request to receiving the very first token from the model."
              />
            </Show>
            <Show when={msg.total_duration}>
              <MetricPopover 
                title="Generation Time"
                label="Total"
                value={`${(msg.total_duration! / 1000).toFixed(2)}s`}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
                description="The total wall-clock time elapsed for the complete response generation process."
              />
            </Show>
            <Show when={msg.tps}>
              <MetricPopover 
                title="Inference Speed"
                label="TPS"
                value={msg.tps!.toFixed(1)}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="m16 18 6-6-6-6"/><path d="M8 6l-6 6 6 6"/></svg>}
                description="Tokens Per Second: The average speed at which the model generated the text content."
              />
            </Show>
          </div>

          {/* Usage Metrics */}
          <Show when={msg.prompt_tokens || msg.completion_tokens}>
            <MetricPopover 
              title="Token Consumption"
              label="Usage"
              value={`${formatTokenCount(msg.prompt_tokens ?? 0)}i / ${formatTokenCount(msg.completion_tokens ?? 0)}o`}
              icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7"/><path d="M16 5V3"/><path d="M8 5V3"/><path d="M3 9h18"/><path d="M16 19h6"/><path d="M19 16v6"/></svg>}
              description="Detailed breakdown of input (prompt) tokens and output (generated) tokens used."
            />
          </Show>

          {/* Extras */}
          <Show when={msg.citations && msg.citations.length > 0}>
            <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-indigo-500/5 border border-indigo-500/20 text-[10px] font-bold text-indigo-500/80 uppercase tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/><path d="M14 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/></svg>
              {msg.citations?.length} Citations
            </div>
          </Show>

          <Show when={msg.tools && msg.tools.length > 0}>
            <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-500/5 border border-amber-500/20 text-[10px] font-bold text-amber-500/80 uppercase tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
              {msg.tools?.length} Tools
            </div>
          </Show>
        </Show>
      </div>
    );
  };

  return (
    <div class="flex h-full bg-background overflow-hidden relative">
      <ChatSidebar 
        showHistory={showHistory()} 
        chats={chats()} 
        currentChatId={currentChatId()} 
        onNewChat={startNewChat} 
        onLoadChat={loadChat} 
        onDeleteChat={deleteChat} 
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
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary font-bold shrink-0 border border-primary/10 shadow-sm">
                  {activeAgentName().charAt(0)}
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
          renderThought={renderThought}
          renderMetaBadges={renderMetaBadges}
          messagesEndRef={el => messagesEndRef = el}
          setInput={setInput}
        />

        {/* 3. Unified Input Center (Phase 1.3) */}
        <ChatInput 
          showAgentSelector={showAgentSelector()}
          filteredAgents={filteredAgents()}
          selectedIndex={selectedIndex()}
          selectAgent={selectAgent}
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
          setSelectedModel={setSelectedModel}
          selectedProvider={selectedProvider()}
          setSelectedProvider={setSelectedProvider}
          providers={providers()}
          showAllModels={showAllModels()}
          setShowAllModels={setShowAllModels}
          isRefreshingModels={isRefreshingModels()}
          setIsRefreshingModels={setIsRefreshingModels}
          loadProviders={loadProviders}
          providerStorageKey={PROVIDER_STORAGE_KEY}
          modelStorageKey={MODEL_STORAGE_KEY}
          isDeepThinking={isDeepThinking()}
          setIsDeepThinking={setIsDeepThinking}
          imageAttachments={imageAttachments()}
          setImageAttachments={setImageAttachments}
          onImageClick={() => imageInputRef?.click()}
          imageInputRef={el => imageInputRef = el}
        />
      </div>

      {/* 4. Intelligence Hub (300px) */}
      <div 
        class={`
          fixed lg:relative inset-y-0 right-0 bg-surface border-l border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
          ${showKnowledge() ? (isArtifactExpanded() ? 'translate-x-0 w-[55vw] opacity-100' : 'translate-x-0 w-[420px] opacity-100') : 'translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
        `}
      >
        <div class={`${isArtifactExpanded() ? 'w-[55vw]' : 'w-[420px]'} h-full flex flex-col transition-all duration-300`}>
          <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
            <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
              <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
              Intelligence Hub
            </h2>
            <div class="flex items-center gap-1">
              <button 
                onClick={() => setIsArtifactExpanded(!isArtifactExpanded())} 
                class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90"
                title={isArtifactExpanded() ? "Collapse view" : "Expand view"}
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {isArtifactExpanded() 
                    ? <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    : <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                  }
                </svg>
              </button>
              <button onClick={() => setShowKnowledge(false)} class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Intelligence Tabs */}
          <div class="flex border-b border-border bg-background/50 p-1">
            <button 
              onClick={() => setIntelligenceTab('actions')}
              class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${intelligenceTab() === 'actions' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
            >
              Actions
            </button>
            <button 
              onClick={() => setIntelligenceTab('notes')}
              class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${intelligenceTab() === 'notes' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
            >
              Notes
            </button>
            <button 
              onClick={() => setIntelligenceTab('graph')}
              class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${intelligenceTab() === 'graph' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
            >
              Graph
            </button>
            <Show when={previewContent()}>
              <button 
                onClick={() => setIntelligenceTab('preview')}
                class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${intelligenceTab() === 'preview' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
              >
                Preview
              </button>
            </Show>
          </div>

          <div class="p-6 space-y-8 overflow-y-auto flex-1 scrollbar-thin">
            <Switch>
              <Match when={intelligenceTab() === 'preview'}>
                <div class="h-full flex flex-col animate-in fade-in slide-in-from-right-4 duration-300">
                  <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xs font-black text-text-primary uppercase tracking-[0.2em]">Artifact Preview</h3>
                    <div class="flex gap-2">
                       <span class="text-[10px] font-mono bg-primary/10 text-primary px-2 py-1 rounded">{previewContent()?.lang}</span>
                    </div>
                  </div>
                  <div class="flex-1 bg-white rounded-xl overflow-hidden border border-border shadow-sm relative">
                    <Show when={previewContent()?.lang === 'html' || previewContent()?.lang === 'xml'}>
                      <iframe 
                        srcdoc={previewContent()?.content} 
                        class="w-full h-full border-0" 
                        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                      />
                    </Show>
                    <Show when={previewContent()?.lang === 'svg'}>
                      <div class="w-full h-full flex items-center justify-center p-4 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjgiPgo8cmVjdCB3aWR0aD0iOCIgaGVpZ2h0PSI4IiBmaWxsPSIjZmZmIi8+CjxwYXRoIGQ9Ik0wIDBMOCA4Wk04IDBMMCA4WiIgc3Ryb2tlPSIjZWVlIiBzdHJva2Utd2lkdGg9IjEiLz4KPC9zdmc+')]">
                        <div innerHTML={previewContent()?.content} />
                      </div>
                    </Show>
                    <Show when={previewContent()?.lang === 'mermaid'}>
                      <div class="w-full h-full p-4 bg-white overflow-hidden">
                        <MermaidViewer code={previewContent()?.content || ''} />
                      </div>
                    </Show>
                  </div>
                </div>
              </Match>
              <Match when={intelligenceTab() === 'actions'}>
                <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div class="relative group">
                    <div class="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-primary/5 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                    <div class="relative bg-surface border border-primary/10 rounded-2xl p-5 shadow-sm">
                      <h4 class="text-[10px] font-black text-primary uppercase tracking-[0.2em] mb-3">Contextual Analysis</h4>
                      <p class="text-[13px] text-text-secondary leading-relaxed font-medium">
                        Monitoring your conversation to extract key entities and research data in real-time.
                      </p>
                    </div>
                  </div>
                  
                  <div class="space-y-5">
                    <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em] flex items-center gap-2">
                      <span class="w-1 h-1 bg-text-secondary/40 rounded-full"></span>
                      Suggested Actions
                    </h4>
                    <div class="grid grid-cols-1 gap-3">
                      <For each={[
                        { title: 'Research deep dive', icon: 'M9 5l7 7-7 7' },
                        { title: 'Save to intelligence', icon: 'M5 5h5M5 8h2m6 11H9a2 2 0 01-2-2v-3a2 2 0 012-2h3m5 4V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
                        { title: 'Extract key findings', icon: 'M13 10V3L4 14h7v7l9-11h-7z' }
                      ]}>
                        {(action) => (
                          <button class="text-left px-5 py-4 bg-background border border-border/60 rounded-2xl text-[13px] font-bold text-text-primary hover:border-primary/50 hover:bg-primary/5 transition-all flex items-center justify-between group">
                            <span>{action.title}</span>
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-text-secondary group-hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={action.icon} />
                            </svg>
                          </button>
                        )}
                      </For>
                    </div>
                  </div>

                  <div class="pt-4 border-t border-border/40">
                    <div class="flex items-center justify-between mb-4">
                      <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Connected Nodes</h4>
                      <span class="text-[9px] font-bold bg-primary/10 text-primary px-2 py-0.5 rounded-full tracking-tighter">0 ACTIVE</span>
                    </div>
                    <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                      <p class="text-xs text-text-secondary/60 font-medium italic">No entities detected yet</p>
                    </div>
                  </div>
                </div>
              </Match>

              <Match when={intelligenceTab() === 'notes'}>
                <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div class="flex items-center justify-between">
                    <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Related Notes</h4>
                    <button class="text-[10px] font-bold text-primary hover:underline">View All</button>
                  </div>
                  <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                    <p class="text-xs text-text-secondary/60 font-medium italic">No related notes found</p>
                  </div>
                </div>
              </Match>

              <Match when={intelligenceTab() === 'graph'}>
                <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Knowledge Graph</h4>
                  <div class="aspect-square bg-background/50 border border-border rounded-2xl flex items-center justify-center p-8 text-center">
                    <div>
                      <div class="w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <p class="text-xs text-text-secondary/60 font-medium">Graph visualization will appear here as entities are discovered.</p>
                    </div>
                  </div>
                </div>
              </Match>
            </Switch>
          </div>
        </div>
      </div>
      
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
    </div>
  );
}
