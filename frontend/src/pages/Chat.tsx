import { createSignal, For, onMount, Show, createEffect, Switch, Match } from 'solid-js';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import ModelSwitcher, { type ProviderInfo } from '../components/ModelSwitcher';

// Configure marked to use highlight.js via a custom renderer
const renderer = new marked.Renderer();

// Custom math rendering helper
const renderMath = (text: string) => {
  // 1. Protect code blocks and inline code to prevent false positives
  const codeBlocks: string[] = [];
  
  // Replace code blocks (```...```)
  text = text.replace(/```[\s\S]*?```/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // Replace inline code (`...`)
  text = text.replace(/`[^`\n]+`/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 2. Render Math
  // Block math: $$ ... $$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      return `<div class="math-block my-4 overflow-x-auto">` + 
             katex.renderToString(math, { displayMode: true, throwOnError: false }) + 
             `</div>`;
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Block math: \[ ... \]
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, math) => {
    try {
      return `<div class="math-block my-4 overflow-x-auto">` + 
             katex.renderToString(math, { displayMode: true, throwOnError: false }) + 
             `</div>`;
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Inline math: \( ... \)
  text = text.replace(/\\\(([\s\S]+?)\\\)/g, (_, math) => {
    try {
      return katex.renderToString(math, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Inline math: $ ... $ (avoiding common false positives like $100)
  // This regex matches $...$ where the content doesn't start or end with a space
  text = text.replace(/\$([^\s$](?:[^$]*[^\s$])?)\$/g, (_, math) => {
    try {
      return katex.renderToString(math, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // 3. Restore code blocks
  text = text.replace(/__CODE_BLOCK_(\d+)__/g, (_, index) => {
    return codeBlocks[parseInt(index)];
  });

  return text;
};
renderer.code = ({ text, lang }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
  const highlighted = hljs.highlight(text, { language }).value;
  
  const isPreviewable = ['html', 'svg', 'xml'].includes(language);
  // Encode content and escape single quotes to prevent breaking the onclick attribute
  const encodedContent = isPreviewable ? encodeURIComponent(text).replace(/'/g, '%27') : '';

  return `
    <div class="code-block-container relative group my-6 rounded-xl overflow-hidden border border-border/50 bg-[#0d1117] shadow-xl transition-all duration-300 hover:border-primary/30">
      <div class="flex items-center justify-between px-4 py-2.5 bg-[#161b22]/80 backdrop-blur-sm border-b border-border/10">
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-1.5 mr-2">
            <div class="w-3 h-3 rounded-full bg-[#ff5f56] shadow-inner"></div>
            <div class="w-3 h-3 rounded-full bg-[#ffbd2e] shadow-inner"></div>
            <div class="w-3 h-3 rounded-full bg-[#27c93f] shadow-inner"></div>
          </div>
          <div class="h-4 w-[1px] bg-border/10 mx-1"></div>
          <span class="text-[10px] font-black font-mono text-text-secondary/60 uppercase tracking-[0.2em] ml-1">${language}</span>
        </div>
        <div class="flex items-center gap-2">
          ${isPreviewable ? `
            <button 
              onclick="window.openArtifact('${language}', '${encodedContent}')"
              class="px-2 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-all flex items-center gap-1.5 border border-primary/20"
              title="Open Preview"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span class="text-[9px] font-bold uppercase tracking-wider">Preview</span>
            </button>
          ` : ''}
          <button 
            onclick="window.copyToClipboard(this)" 
            class="p-1.5 rounded-lg hover:bg-white/5 text-text-secondary/60 hover:text-primary transition-all flex items-center gap-1.5 group/copy"
            title="Copy code"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform group-hover/copy:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
            <span class="text-[9px] font-black uppercase tracking-wider">Copy</span>
          </button>
        </div>
      </div>
      <pre class="p-5 overflow-x-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent selection:bg-primary/20"><code class="hljs language-${language} text-[14px] leading-relaxed font-mono block">${highlighted}</code></pre>
    </div>
  `;
};

marked.setOptions({
  renderer
});

// Global helper for copying code
(window as any).copyToClipboard = (btn: HTMLButtonElement) => {
  const container = btn.closest('.code-block-container');
  const code = container?.querySelector('code')?.innerText;
  if (code) {
    navigator.clipboard.writeText(code).then(() => {
      const span = btn.querySelector('span');
      if (span) {
        const originalText = span.innerText;
        span.innerText = 'Copied!';
        btn.classList.add('text-emerald-400');
        setTimeout(() => {
          span.innerText = originalText;
          btn.classList.remove('text-emerald-400');
        }, 2000);
      }
    });
  }
};

type Agent = {
  id: string;
  name: string;
};

type ChatSession = {
  id: string;
  title: string;
  updated_at: string;
};

type Message = {
  role: string;
  content: string;
  thought_duration?: number;
};

export default function Chat() {
  const MODEL_STORAGE_KEY = "chat.selected_model";
  const PROVIDER_STORAGE_KEY = "chat.selected_provider";

  // Core State
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [elapsedTime, setElapsedTime] = createSignal(0);
  let timerInterval: any;
  
  // Reasoning Chain State
  const [expandedThoughts, setExpandedThoughts] = createSignal<Record<number, boolean>>({});
  const toggleThought = (index: number) => {
    setExpandedThoughts(prev => ({ ...prev, [index]: !prev[index] }));
  };

  // Refs
  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;

  // Agent & Model State
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string>("");
  const [showAgentSelector, setShowAgentSelector] = createSignal(false);
  const [agentFilter, setAgentFilter] = createSignal("");
  const [selectedIndex, setSelectedIndex] = createSignal(0);
  
  const [providers, setProviders] = createSignal<ProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = createSignal("");
  const [selectedModel, setSelectedModel] = createSignal("");
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  // keep selected images in memory for future send
  const [imageAttachments, setImageAttachments] = createSignal<File[]>([]);
  let imageInputRef: HTMLInputElement | undefined;
  
  // History & Knowledge State
  const [chats, setChats] = createSignal<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = createSignal<string | null>(null);
  const [showHistory, setShowHistory] = createSignal(true); // Default to true on desktop
  const [showKnowledge, setShowKnowledge] = createSignal(false);
  const [intelligenceTab, setIntelligenceTab] = createSignal<'notes' | 'graph' | 'actions' | 'preview'>('actions');
  const [previewContent, setPreviewContent] = createSignal<{lang: string, content: string} | null>(null);
  const [isArtifactExpanded, setIsArtifactExpanded] = createSignal(false);
  
  // Responsive State
  const [windowWidth, setWindowWidth] = createSignal(window.innerWidth);
  onMount(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  });
  const isMobile = () => windowWidth() < 1024;
  
  let messagesEndRef: HTMLDivElement | undefined;

  createEffect(() => {
    if (messages().length > 0 && !userHasScrolledUp()) {
      messagesEndRef?.scrollIntoView({ behavior: 'smooth' });
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

   // Helper to split thought and content
  const parseThoughtAndContent = (text: string) => {
    const thoughtMatch = text.match(/<(?:thought|think)>([\s\S]*?)(?:<\/(?:thought|think)>|$)/);
    if (thoughtMatch) {
      const thought = thoughtMatch[1];
      const rest = text.replace(/<(?:thought|think)>[\s\S]*?(?:<\/(?:thought|think)>|$)/, "").trim();
      return { thought, content: rest };
    }
    return { thought: null, content: text };
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
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch('/api/chat/history');
      setChats(await res.json());
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

  const loadProviders = async (refresh = false) => {
    try {
      const res = await fetch(`/api/models/providers${refresh ? '?refresh=1' : ''}`);
      const data = await res.json();
      setProviders(data);

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
    }
  };

  const loadChat = async (id: string) => {
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
    }
  };

  const startNewChat = () => {
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
    } catch (e) {}
  };
  
  onMount(() => {
    const storedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const storedModel = localStorage.getItem(MODEL_STORAGE_KEY);
    if (storedProvider) setSelectedProvider(storedProvider);
    if (storedModel) setSelectedModel(storedModel);

    loadAgents();
    loadHistory();
    loadProviders();

    // Register global artifact opener
    (window as any).openArtifact = (lang: string, encodedContent: string) => {
      try {
        const content = decodeURIComponent(encodedContent);
        setPreviewContent({ lang, content });
        setIntelligenceTab('preview');
        setShowKnowledge(true);
      } catch (e) {
        console.error("Failed to open artifact:", e);
      }
    };

    // Global click listener to close dropdowns
    const handleGlobalClick = () => {
      setShowAgentSelector(false);
    };
    window.addEventListener('click', handleGlobalClick);
    return () => window.removeEventListener('click', handleGlobalClick);
  });

  const handleRegenerate = async (index: number) => {
    if (isTyping()) return;
    
    // Find the last user message before this assistant message
    const historyBefore = messages().slice(0, index);
    const lastUserMsgIndex = historyBefore.findLastIndex(m => m.role === 'user');
    
    if (lastUserMsgIndex === -1) return;
    
    const lastUserMsg = historyBefore[lastUserMsgIndex];
    // Keep everything up to the user message, then re-send it
    setMessages(messages().slice(0, lastUserMsgIndex + 1));
    setInput(lastUserMsg.content);
    // Trigger submit (but we need to handle the event or call a modified handleSubmit)
    // Actually, let's just call handleSubmit with a simulated event or refactor handleSubmit
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
      const last = messages()[messages().length - 1];
      if (!last || last.role !== 'assistant' || last.content !== '请先选择一个模型再开始对话。') {
        setMessages([...messages(), { role: 'assistant', content: '请先选择一个模型再开始对话。' }]);
      }
      return;
    }

    if (isTyping()) {
      stopGeneration();
      return;
    }
    
    const agentId = selectedAgent() || undefined;

    setMessages([...messages(), { role: 'user', content: text }]);
    setInput("");
    if (textareaRef) {
      textareaRef.style.height = 'auto';
    }
    setIsTyping(true);
    setElapsedTime(0);
    timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);

    setMessages(prev => [...prev, { role: 'assistant', content: "" }]);

    abortController = new AbortController();

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
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
                  loadHistory(); // Refresh history list to show new title
                } else if (data.content) {
                  accumulatedResponse += data.content;
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
                    return newMsgs;
                  });
                } else if (data.thought_duration) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], thought_duration: data.thought_duration };
                    return newMsgs;
                  });
                } else if (data.error) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: `Error: ${data.error}` };
                    return newMsgs;
                  });
                }
              } catch (e) {}
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user');
      } else {
        console.error("Chat error:", err);
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

  return (
    <div class="flex h-full bg-background overflow-hidden relative">
      {/* 1. History Sidebar (250px) */}
      <div 
        class={`
          fixed lg:relative inset-y-0 left-0 bg-surface border-r border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
          ${showHistory() ? 'translate-x-0 w-sidebar opacity-100' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
        `}
      >
        <div class="w-sidebar h-full flex flex-col">
          <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
            <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
              <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
              Chat History
            </h2>
            <button 
              onClick={startNewChat} 
              class="group relative p-2 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-xl transition-all duration-300 active:scale-90 shadow-sm hover:shadow-primary/20"
              title="New Chat Session"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>
          <div class="overflow-y-auto flex-1 pb-20 scrollbar-thin scrollbar-thumb-border">
            <For each={chats()}>
              {chat => (
                <div 
                  class={`p-3 border-b border-border cursor-pointer hover:bg-primary/5 group flex justify-between items-start transition-colors ${
                    currentChatId() === chat.id ? 'bg-primary/10 border-l-4 border-l-primary' : 'border-l-4 border-l-transparent'
                  }`}
                  onClick={() => loadChat(chat.id)}
                >
                  <div class="flex-1 min-w-0">
                    <h3 class={`text-sm font-medium truncate ${currentChatId() === chat.id ? 'text-primary' : 'text-text-primary'}`}>{chat.title}</h3>
                    <p class="text-[10px] text-text-secondary mt-1">{new Date(chat.updated_at).toLocaleDateString()}</p>
                  </div>
                  <button 
                    onClick={(e) => deleteChat(chat.id, e)}
                    class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 transition-all"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              )}
            </For>
            <Show when={chats().length === 0}>
               <div class="p-8 text-center text-sm text-text-secondary italic">No recent chats</div>
            </Show>
          </div>
        </div>
      </div>

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
        <div 
          ref={chatContainerRef}
          onScroll={handleScroll}
          class="flex-1 overflow-y-auto px-4 py-8 lg:px-12 space-y-8 scroll-smooth scrollbar-thin scrollbar-thumb-border/50"
        >
          <Show when={messages().length === 0}>
            <div class="h-full flex flex-col items-center justify-center text-center px-4 max-w-2xl mx-auto">
              <div class="w-24 h-24 mb-8 rounded-[2rem] bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center shadow-xl shadow-primary/5 border border-primary/10 animate-in zoom-in-90 duration-500">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h2 class="text-3xl font-extrabold text-text-primary tracking-tight mb-4">Empowering your workflow with Yue</h2>
              <p class="text-lg text-text-secondary leading-relaxed mb-8 max-w-lg mx-auto">
                Select an expert agent or start a new conversation to explore documents, research topics, or generate insights.
              </p>
              
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
                <button onClick={() => setInput("Generate a responsive landing page for a coffee shop using HTML and Tailwind CSS.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="p-1.5 rounded-lg bg-orange-500/10 text-orange-500 group-hover:bg-orange-500/20 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                    </span>
                    <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">HTML Preview</span>
                  </div>
                  <p class="text-sm text-text-primary line-clamp-2">Generate a responsive landing page for a coffee shop</p>
                </button>
                
                <button onClick={() => setInput("Create a complex SVG illustration of a futuristic city skyline.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="p-1.5 rounded-lg bg-pink-500/10 text-pink-500 group-hover:bg-pink-500/20 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                    </span>
                    <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">SVG Artifact</span>
                  </div>
                  <p class="text-sm text-text-primary line-clamp-2">Create a complex SVG illustration of a city skyline</p>
                </button>

                <button onClick={() => setInput("Write a Python script to solve the Tower of Hanoi problem with a recursive function.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="p-1.5 rounded-lg bg-blue-500/10 text-blue-500 group-hover:bg-blue-500/20 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                    </span>
                    <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">Code & Logic</span>
                  </div>
                  <p class="text-sm text-text-primary line-clamp-2">Solve Tower of Hanoi with recursive Python code</p>
                </button>

                <button onClick={() => setInput("Explain the Schrödinger equation with mathematical formulas.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
                  <div class="flex items-center gap-2 mb-2">
                    <span class="p-1.5 rounded-lg bg-green-500/10 text-green-500 group-hover:bg-green-500/20 transition-colors">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                    </span>
                    <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">Math & Latex</span>
                  </div>
                  <p class="text-sm text-text-primary line-clamp-2">Explain Schrödinger equation with math formulas</p>
                </button>
              </div>
            </div>
          </Show>

          <For each={messages()}>
            {(msg, index) => (
              <div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
                <div class={`group relative max-w-[85%] lg:max-w-[75%] ${
                  msg.role === 'user' 
                    ? 'bg-primary text-white px-6 py-4 shadow-xl shadow-primary/10 rounded-[24px] rounded-br-none' 
                    : 'bg-surface text-text-primary border border-border/50 px-6 py-5 shadow-sm rounded-[24px] rounded-bl-none'
                }`}>
                  {msg.role === 'user' ? (
                     <div class="whitespace-pre-wrap leading-relaxed font-medium text-[15px]">{msg.content}</div>
                  ) : (
                     <div class="relative space-y-5">
                        {(() => {
                          const { thought, content } = parseThoughtAndContent(msg.content);
                          return (
                            <>
                              <Show when={thought}>
                                <div class="bg-black/5 dark:bg-black/20 -mx-6 -mt-5 rounded-t-[24px] border-b border-border/10 overflow-hidden group/thought mb-5">
                                  <button 
                                    onClick={() => toggleThought(index())}
                                    class="w-full flex items-center justify-between px-6 py-3 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                                  >
                                    <div class="flex items-center gap-3">
                                      <div class="relative flex items-center justify-center w-5 h-5">
                                        <Show when={isTyping() && !content}>
                                          <div class="absolute inset-0 bg-primary/10 rounded-full animate-ping"></div>
                                          <div class="absolute inset-0.5 border border-primary/20 rounded-full animate-[spin_3s_linear_infinite]"></div>
                                        </Show>
                                        <div class={`relative w-2 h-2 rounded-full transition-all duration-700 ${isTyping() && !content ? 'bg-primary shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-text-secondary/30'}`}></div>
                                      </div>
                                      <div class="flex items-center gap-2">
                                        <span class="text-[13px] font-medium text-text-secondary">
                                          {isTyping() && !content ? 'Thinking Process' : 'Reasoning Chain'}
                                        </span>
                                        <span class="text-[11px] font-mono text-text-secondary/40">
                                          {msg.thought_duration 
                                            ? `${msg.thought_duration < 60 ? msg.thought_duration.toFixed(1) + 's' : Math.floor(msg.thought_duration / 60) + 'm ' + (msg.thought_duration % 60).toFixed(0) + 's'}`
                                            : (isTyping() && !content ? `${elapsedTime().toFixed(1)}s` : '')}
                                        </span>
                                      </div>
                                    </div>
                                    <div class={`p-1 rounded-md transition-all duration-300 ${expandedThoughts()[index()] ? 'bg-black/5 text-text-primary' : 'text-text-secondary/40'}`}>
                                      <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 transition-transform duration-300 ${expandedThoughts()[index()] ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                                        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                                      </svg>
                                    </div>
                                  </button>
                                  <div 
                                    class={`transition-all duration-300 ease-in-out overflow-hidden ${
                                      expandedThoughts()[index()] ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                                    }`}
                                  >
                                    <div class="px-6 py-4 text-[13px] font-mono text-text-secondary/80 leading-relaxed overflow-y-auto max-h-[500px] border-t border-border/5 bg-black/5 dark:bg-black/10">
                                      {thought}
                                    </div>
                                  </div>
                                </div>
                              </Show>
                              
                              <Show when={content || (isTyping() && !thought)}>
                                <div 
                                  innerHTML={marked.parse(renderMath(content)) as string} 
                                  class="prose prose-slate dark:prose-invert max-w-none 
                                    prose-p:leading-relaxed prose-p:my-3 prose-p:text-[15px]
                                    prose-headings:text-text-primary prose-headings:font-black prose-headings:tracking-tight
                                    prose-a:text-primary prose-a:font-bold hover:prose-a:text-primary-hover prose-a:no-underline border-b border-transparent hover:border-primary
                                    prose-strong:text-text-primary prose-strong:font-bold
                                    prose-code:text-primary prose-code:bg-primary/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-code:font-bold
                                    prose-pre:p-0 prose-pre:bg-transparent
                                    prose-ol:my-4 prose-ul:my-4 prose-li:my-1
                                    prose-table:w-full prose-table:border-collapse prose-table:my-6
                                    prose-th:bg-primary/5 prose-th:text-primary prose-th:p-3 prose-th:text-left prose-th:text-xs prose-th:font-black prose-th:uppercase prose-th:tracking-wider prose-th:border prose-th:border-border/60
                                    prose-td:p-3 prose-td:text-sm prose-td:border prose-td:border-border/60 prose-td:text-text-secondary" 
                                />
                              </Show>
                            </>
                          );
                        })()}
                        
                        <Show when={isTyping() && index() === messages().length - 1}>
                          <span class="inline-block w-2.5 h-5 ml-1 bg-primary/30 animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(16,185,129,0.3)]"></span>
                        </Show>

                        {/* Message Actions */}
                        <Show when={msg.role === 'user'}>
                          <div class="absolute top-0 right-full mr-3 flex flex-col gap-1.5">
                            <button 
                              onClick={() => {
                                navigator.clipboard.writeText(msg.content);
                              }}
                              class="p-2 text-text-secondary hover:text-primary hover:bg-surface border border-transparent hover:border-border shadow-sm rounded-xl transition-all active:scale-90" 
                              title="Copy Message"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                              </svg>
                            </button>
                          </div>
                        </Show>

                        <Show when={msg.role === 'assistant' && (!isTyping() || index() !== messages().length - 1)}>
                          <div class="flex items-center gap-1 mt-3 -ml-2">
                            <button 
                              class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
                              title="Copy" 
                              onClick={() => navigator.clipboard.writeText(msg.content)}
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                              </svg>
                            </button>
                            <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Read Aloud">
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                               </svg>
                            </button>
                             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Download">
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                               </svg>
                            </button>
                             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Share">
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                               </svg>
                            </button>
                             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="More">
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
                               </svg>
                            </button>
                            
                            <div class="h-4 w-[1px] bg-border/50 mx-1"></div>
                            
                            <button 
                              class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
                              title="Regenerate" 
                              onClick={() => handleRegenerate(index())}
                            >
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                               </svg>
                            </button>
                          </div>
                        </Show>
                     </div>
                  )}
                </div>
              </div>
            )}
          </For>
          
          <Show when={isTyping() && messages().length > 0 && messages()[messages().length-1].content === ""}>
            <div class="flex justify-start animate-in fade-in duration-300">
              <div class="bg-surface px-5 py-4 rounded-2xl rounded-bl-none border border-border shadow-sm flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 300ms"></div>
              </div>
            </div>
          </Show>
          <div ref={messagesEndRef} />
        </div>

        {/* 3. Unified Input Center (Phase 1.3) */}
        <div class="px-4 pb-6 lg:px-8 bg-transparent">
          <div class="max-w-5xl mx-auto relative">
            <Show when={showAgentSelector()}>
              <div class="absolute bottom-full left-0 mb-4 w-80 bg-surface border border-border rounded-[24px] shadow-2xl overflow-hidden z-50 animate-in slide-in-from-bottom-4 duration-300 backdrop-blur-xl">
                <div class="bg-primary/5 px-5 py-3 border-b border-border flex items-center justify-between">
                  <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Mention Intelligence Agent</span>
                  <span class="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">@</span>
                </div>
                <div class="max-h-72 overflow-y-auto p-2 scrollbar-thin">
                  <For each={filteredAgents()}>
                    {(agent, index) => (
                      <button
                        onClick={() => selectAgent(agent)}
                        class={`w-full text-left px-4 py-3 flex items-center justify-between rounded-xl transition-all duration-200 ${
                          selectedIndex() === index() ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[1.02]' : 'hover:bg-primary/5 text-text-primary'
                        }`}
                      >
                        <div class="flex items-center gap-3">
                          <div class={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${selectedIndex() === index() ? 'bg-white/20' : 'bg-primary/10 text-primary'}`}>
                            {agent.name.charAt(0)}
                          </div>
                          <div>
                            <span class="font-bold text-sm block">{agent.name}</span>
                            <span class={`text-[10px] block opacity-70 ${selectedIndex() === index() ? 'text-white' : 'text-text-secondary'}`}>Specialized Intelligence</span>
                          </div>
                        </div>
                        <Show when={selectedIndex() === index()}>
                          <div class="flex items-center gap-1">
                            <span class="text-[9px] font-black tracking-tighter border border-white/30 px-1 rounded">ENTER</span>
                          </div>
                        </Show>
                      </button>
                    )}
                  </For>
                  <Show when={filteredAgents().length === 0}>
                    <div class="px-4 py-10 text-center">
                      <div class="text-text-secondary opacity-30 mb-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </div>
                      <p class="text-sm text-text-secondary italic">No matching agents</p>
                    </div>
                  </Show>
                </div>
              </div>
            </Show>

            <form onSubmit={handleSubmit} class="relative">
              <div class={`
                relative bg-surface/80 backdrop-blur-xl border-2 rounded-[28px] transition-all duration-500 p-2 shadow-2xl
                ${isTyping() ? 'border-primary/40 ring-8 ring-primary/5 shadow-primary/10' : 'border-border focus-within:border-primary/40 focus-within:ring-8 focus-within:ring-primary/5'}
              `}>
                <textarea
                  ref={textareaRef}
                  value={input()}
                  onInput={handleInput}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask Yue anything... (Type @ to mention agents)"
                  class="w-full bg-transparent px-6 pt-5 pb-20 focus:outline-none resize-none min-h-[96px] max-h-[400px] overflow-y-auto text-text-primary leading-relaxed text-lg font-medium placeholder:text-text-secondary/30"
                  rows={1}
                />
                
                {/* Unified Action Bar */}
                <div class="absolute bottom-4 left-5 right-5 flex items-center justify-between">
                  {/* Left Side: Configuration */}
                  <div class="flex items-center gap-3">
                    {/* Model Selector */}
                    <div class="relative">
                      <ModelSwitcher
                        providers={providers()}
                        selectedModel={selectedModel()}
                        theme="dark"
                        placement="top"
                        onRefresh={() => loadProviders(true)}
                        onSelect={(provider, model) => {
                          setSelectedProvider(provider);
                          setSelectedModel(model);
                          localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
                          localStorage.setItem(MODEL_STORAGE_KEY, model);
                        }}
                      />
                    </div>

                    {/* Deep Thinking Toggle */}
                    <button
                      type="button"
                      onClick={() => setIsDeepThinking(!isDeepThinking())}
                      class={`flex items-center gap-2.5 px-4 py-2.5 rounded-2xl transition-all active:scale-95 border shadow-sm ${
                        isDeepThinking() 
                          ? 'bg-primary/10 border-primary/30 text-primary' 
                          : 'bg-background border-border text-text-secondary hover:text-primary hover:bg-primary/5'
                      }`}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                      <span class="text-xs font-bold uppercase tracking-wider">Deep Thinking</span>
                    </button>
                  </div>

                  {/* Right Side: Tools + Action */}
                  <div class="flex items-center gap-4">
                    {/* Tools Group */}
                    <div class="flex items-center gap-2">
                      <div class="relative group/tooltip">
                        <button type="button" class="p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Attach files">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                          </svg>
                        </button>
                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                          <span class="font-bold text-white/90">快速理解总结文件</span>
                          <span class="block text-[11px] text-white/50 mt-1">PDF, Word, Excel, PPT, Code</span>
                          <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                        </div>
                      </div>
                      <div class="relative group/tooltip">
                        <input ref={el => imageInputRef = el} type="file" accept="image/*" multiple class="hidden" 
                          onChange={e => {
                            const files = Array.from(e.currentTarget.files || []);
                            const maxCount = 10;
                            const maxSize = 10 * 1024 * 1024;
                            const valid = files.filter(f => f.size <= maxSize);
                            if (files.length > maxCount) {
                              alert(`最多选择 ${maxCount} 张图片`);
                            }
                            if (valid.length !== files.length) {
                              alert('部分文件超过 10MB 大小限制，已忽略');
                            }
                            setImageAttachments(valid.slice(0, maxCount));
                            e.currentTarget.value = '';
                          }} />
                        <button type="button" class="relative p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Upload images"
                          onClick={() => imageInputRef?.click()}>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke-width="2" />
                            <circle cx="8.5" cy="8.5" r="1.5" stroke-width="2" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 15l-5-5L5 21" />
                          </svg>
                          <Show when={imageAttachments().length > 0}>
                            <span class="absolute -top-1 -right-1 text-[10px] bg-primary text-white rounded-full px-1.5 py-0.5 border border-background shadow-sm">{imageAttachments().length}</span>
                          </Show>
                        </button>
                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                          <span class="font-bold text-white/90">上传图片</span>
                          <span class="block text-[11px] text-white/50 mt-1">JPG, PNG (Max 10)</span>
                          <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                        </div>
                      </div>
                      <div class="relative group/tooltip">
                        <button type="button" class="p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Voice input">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                          </svg>
                        </button>
                        <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[200px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                          <span class="font-bold text-white/90">语音输入 (Beta)</span>
                          <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                        </div>
                      </div>
                    </div>

                    <button 
                      type="submit"
                      disabled={!isTyping() && (!input().trim() || !selectedModel())}
                      class={`
                        flex items-center justify-center p-4 rounded-2xl transition-all duration-500 shadow-lg
                        ${(input().trim() && selectedModel()) || isTyping() 
                          ? 'bg-primary text-white hover:bg-primary-hover hover:shadow-primary/30 hover:scale-[1.02] active:scale-95' 
                          : 'bg-border/50 text-text-secondary cursor-not-allowed opacity-50'}
                      `}
                    >
                      <Show when={isTyping()} fallback={
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                        </svg>
                      }>
                        <div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      </Show>
                    </button>
                  </div>
                </div>
              </div>
            </form>

            <Show when={!selectedModel()}>
              <div class="mt-3 flex items-center justify-center">
                <div class="px-3 py-1.5 rounded-full bg-surface border border-border text-[11px] text-text-secondary font-semibold">
                  请选择模型后开始提问
                </div>
              </div>
            </Show>

            {/* (Removed) Full Model Selector Popover to avoid duplicate menus; quick switch near button remains */}
          </div>
        </div>
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
