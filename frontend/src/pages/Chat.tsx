import { createSignal, For, onMount, Show, createEffect, Switch, Match } from 'solid-js';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import MermaidViewer from '../components/MermaidViewer';
import { useToast } from '../context/ToastContext';
import { getMermaidInitConfig, getMermaidThemePreset, MERMAID_THEME_PRESETS, setMermaidThemePreset, type MermaidThemePreset } from '../utils/mermaidTheme';
import { buildExportSvgString, canCopyPng, copyPngBlobToClipboard, copyTextToClipboard, downloadBlob, getMermaidExportPrefs, getMermaidExportTimestamp, sanitizeFilenameBase, setMermaidExportPrefs, svgStringToPngBlob } from '../utils/mermaidExport';
import { parseThoughtAndContent } from '../utils/thoughtParser';
import { renderMarkdown, normalizeMermaidCode, getMermaidThemeOptionsHtml } from '../utils/markdown';

const renderMermaidChart = async (container: Element) => {
  if (container.getAttribute('data-processed') === 'true') return;
  
  const widget = container.closest('.mermaid-widget');
  const isComplete = widget?.getAttribute('data-complete') === 'true';
  
  // If the block is not complete (streaming), don't render yet
  if (!isComplete) return;

  const code = normalizeMermaidCode(decodeURIComponent(container.getAttribute('data-code') || ''));
  if (!code) return;

  try {
    const preset = getMermaidThemePreset();
    (mermaid as any).initialize(getMermaidInitConfig(preset));
    const id = `mermaid-${Math.random().toString(36).slice(2, 11)}`;
    
    // Silent error handling: check if code is valid before rendering
    try {
      await mermaid.parse(code);
    } catch (parseErr) {
      // If parsing fails even when "complete", it's a real syntax error.
      // We still want to handle it gracefully.
      throw parseErr;
    }

    const { svg } = await mermaid.render(id, code);
    container.classList.add('opacity-0', 'transition-opacity', 'duration-500');
    container.innerHTML = svg;
    requestAnimationFrame(() => {
      container.classList.remove('opacity-0');
      container.classList.add('opacity-100');
    });
    container.setAttribute('data-processed', 'true');
  } catch (err) {
    console.warn('Mermaid render error (silent):', err);
    // Keep showing the code or a friendly error if it's truly broken
    container.innerHTML = `
      <div class="text-amber-600 text-xs p-3 border border-amber-200 rounded-xl bg-amber-50/50 font-mono">
        <div class="flex items-center gap-2 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <span class="font-bold">Mermaid Diagram Note</span>
        </div>
        <div class="opacity-80">${err instanceof Error ? err.message.split('\n')[0] : 'Syntax error in diagram'}</div>
        <button type="button" data-mermaid-action="tab-code" class="mt-2 text-amber-700 hover:underline font-bold uppercase tracking-wider text-[9px]">View Code</button>
      </div>
    `;
    container.setAttribute('data-processed', 'true');
  }
};

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
  images?: string[];
  thought_duration?: number;
  ttft?: number;
  total_duration?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  tps?: number;
  timestamp?: string;
  provider?: string;
  model?: string;
  tools?: string[];
  citations?: any[];
  context_id?: string;
  error?: string;
};

export default function Chat() {
  const toast = useToast();
  const MODEL_STORAGE_KEY = "chat.selected_model";
  const PROVIDER_STORAGE_KEY = "chat.selected_provider";

  // Core State
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [elapsedTime, setElapsedTime] = createSignal(0);
  const [copiedMessageIndex, setCopiedMessageIndex] = createSignal<number | null>(null);
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
  
  const [providers, setProviders] = createSignal<any[]>([]);
  const [showLLMSelector, setShowLLMSelector] = createSignal(false);
  const [selectedProvider, setSelectedProvider] = createSignal("");
  const [selectedModel, setSelectedModel] = createSignal("");
  const [isRefreshingModels, setIsRefreshingModels] = createSignal(false);
  const [showAllModels, setShowAllModels] = createSignal(false);
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  // keep selected images in memory for future send
  const [imageAttachments, setImageAttachments] = createSignal<File[]>([]);
  let imageInputRef: HTMLInputElement | undefined;

  const [inlineToast, setInlineToast] = createSignal<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  let toastTimer: number | undefined;
  const showToast = (type: 'success' | 'error' | 'info', message: string) => {
    if (toastTimer) window.clearTimeout(toastTimer);
    setInlineToast({ type, message });
    toastTimer = window.setTimeout(() => setInlineToast(null), 2200);
  };
  
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

  const editUserMessage = (content: string) => {
    setInput(content);
    setTimeout(() => {
      adjustHeight();
      textareaRef?.focus();
      textareaRef?.setSelectionRange(content.length, content.length);
    }, 0);
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

    let mermaidOverlayEl: HTMLElement | null = null;
    let mermaidExportEl: HTMLElement | null = null;
    const previousOverflow = document.body.style.overflow;

    const closeMermaidOverlay = () => {
      if (mermaidOverlayEl) {
        mermaidOverlayEl.remove();
        mermaidOverlayEl = null;
        document.body.style.overflow = mermaidExportEl ? 'hidden' : previousOverflow;
      }
    };

    const closeMermaidExportModal = () => {
      const nodes = Array.from(document.querySelectorAll<HTMLElement>('#mermaid-export-modal'));
      nodes.forEach((n) => n.remove());
      mermaidExportEl = null;
      document.body.style.overflow = mermaidOverlayEl ? 'hidden' : previousOverflow;
    };

    const getWidgetMermaidSvg = (widget: HTMLElement) => widget.querySelector('.mermaid-chart svg') as SVGSVGElement | null;

    const exportMermaidFromWidget = async (
      widget: HTMLElement,
      opts: { format: 'png' | 'svg' | 'mmd'; background: 'transparent' | 'light' | 'dark' | 'custom'; backgroundColor: string; scale: number; padding: number; filename: string },
    ) => {
      const encoded = widget.getAttribute('data-code') || '';
      const raw = decodeURIComponent(encoded);
      const normalized = normalizeMermaidCode(raw);
      const ts = getMermaidExportTimestamp();
      const base = sanitizeFilenameBase(opts.filename);

      if (opts.format === 'mmd') {
        const blob = new Blob([normalized], { type: 'text/plain;charset=utf-8' });
        downloadBlob(blob, `${base}-${ts}.mmd`);
        return;
      }

      const chart = widget.querySelector('.mermaid-chart');
      const existingSvg = getWidgetMermaidSvg(widget);
      if (!existingSvg && chart) {
        chart.setAttribute('data-processed', 'false');
        await renderMermaidChart(chart);
      }

      const svgEl = getWidgetMermaidSvg(widget);
      if (!svgEl) return;

      const svgString = buildExportSvgString(svgEl, { padding: opts.padding, background: opts.background, backgroundColor: opts.backgroundColor });

      if (opts.format === 'svg') {
        downloadBlob(new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' }), `${base}-${ts}.svg`);
        return;
      }

      const pngBlob = await svgStringToPngBlob(svgString, opts.scale);
      if (pngBlob) downloadBlob(pngBlob, `${base}-${ts}.png`);
    };

    const copyMermaidFromWidget = async (
      widget: HTMLElement,
      opts: { format: 'png' | 'svg' | 'mmd'; background: 'transparent' | 'light' | 'dark' | 'custom'; backgroundColor: string; scale: number; padding: number },
    ) => {
      const encoded = widget.getAttribute('data-code') || '';
      const raw = decodeURIComponent(encoded);
      const normalized = normalizeMermaidCode(raw);

      if (opts.format === 'mmd') {
        await copyTextToClipboard(normalized);
        return;
      }

      const chart = widget.querySelector('.mermaid-chart');
      const existingSvg = getWidgetMermaidSvg(widget);
      if (!existingSvg && chart) {
        chart.setAttribute('data-processed', 'false');
        await renderMermaidChart(chart);
      }
      const svgEl = getWidgetMermaidSvg(widget);
      if (!svgEl) return;

      const svgString = buildExportSvgString(svgEl, { padding: opts.padding, background: opts.background, backgroundColor: opts.backgroundColor });

      if (opts.format === 'svg') {
        await copyTextToClipboard(svgString);
        return;
      }
      const pngBlob = await svgStringToPngBlob(svgString, opts.scale);
      if (!pngBlob) return;
      await copyPngBlobToClipboard(pngBlob);
    };

    const openMermaidExportModal = async (widget: HTMLElement) => {
      closeMermaidExportModal();
      document.body.style.overflow = 'hidden';

      const encoded = widget.getAttribute('data-code') || '';
      const raw = decodeURIComponent(encoded);
      const normalized = normalizeMermaidCode(raw);

      const prefs = getMermaidExportPrefs();
      const format: 'png' | 'svg' | 'mmd' = prefs.format;
      const background: 'transparent' | 'light' | 'dark' | 'custom' = prefs.background;
      const backgroundColor = prefs.backgroundColor;
      const scale = prefs.scale;
      const padding = prefs.padding;
      const filename = prefs.filename;

      const modal = document.createElement('div');
      modal.id = 'mermaid-export-modal';
      modal.className = 'fixed inset-0 z-[1300]';
      modal.dataset.format = format;
      modal.dataset.background = background;
      modal.dataset.backgroundColor = backgroundColor;
      modal.dataset.scale = String(scale);
      modal.dataset.padding = String(padding);
      modal.dataset.filename = filename;
      modal.dataset.busy = '0';

      const previewChecker = 'background-image: linear-gradient(45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(-45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, rgba(148,163,184,.18) 75%), linear-gradient(-45deg, transparent 75%, rgba(148,163,184,.18) 75%); background-size: 18px 18px; background-position: 0 0, 0 9px, 9px -9px, -9px 0px;';

      modal.innerHTML = `
        <div class="absolute inset-0 bg-slate-900/25 backdrop-blur-md" data-mermaid-export-close="1"></div>
        <div class="absolute inset-0 flex items-start justify-center px-3 pb-3 pt-3 sm:px-6 sm:pb-6 sm:pt-6">
          <div class="w-[min(1120px,98vw)] h-[min(740px,94vh)] bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col" role="dialog" aria-modal="true" aria-labelledby="mermaid-export-title" aria-describedby="mermaid-export-desc" tabindex="-1" data-mermaid-export-dialog="1">
            <div class="h-16 px-6 border-b border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M3 3a1 1 0 011-1h4a1 1 0 010 2H5v12h10V4h-3a1 1 0 110-2h4a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3z" />
                    <path d="M9 9a1 1 0 011-1h0a1 1 0 011 1v4.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 111.414-1.414L9 13.586V9z" />
                  </svg>
                </div>
                <div>
                  <div id="mermaid-export-title" class="text-sm font-extrabold text-text-primary">Export diagram</div>
                  <div id="mermaid-export-desc" class="text-xs text-text-secondary/70">PNG / SVG / MMD • Background • Advanced</div>
                </div>
              </div>
              <button type="button" class="p-2 rounded-xl hover:bg-surface-elevated text-text-secondary/70 hover:text-text-primary transition-colors" data-mermaid-export-close="1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>

            <div class="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-5">
              <div class="md:col-span-2 p-5 border-b md:border-b-0 md:border-r border-border overflow-auto">
                <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Export format</div>
                <div class="mt-3 grid grid-cols-3 gap-2">
                  <button type="button" data-mermaid-export-format="png" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface-elevated/40 hover:bg-surface-elevated transition-colors text-left">
                    <div class="text-sm font-extrabold text-text-primary">PNG</div>
                    <div class="text-[11px] text-text-secondary/70 mt-0.5">Raster image</div>
                  </button>
                  <button type="button" data-mermaid-export-format="svg" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                    <div class="text-sm font-extrabold text-text-primary">SVG</div>
                    <div class="text-[11px] text-text-secondary/70 mt-0.5">Vector</div>
                  </button>
                  <button type="button" data-mermaid-export-format="mmd" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                    <div class="text-sm font-extrabold text-text-primary">MMD</div>
                    <div class="text-[11px] text-text-secondary/70 mt-0.5">Mermaid source</div>
                  </button>
                </div>

                <div data-mermaid-export-section="background">
                  <div class="mt-6 text-xs font-black uppercase tracking-wider text-text-secondary/60">Background</div>
                  <div class="mt-3 grid grid-cols-2 gap-2">
                    <button type="button" data-mermaid-export-bg="transparent" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface-elevated/40 hover:bg-surface-elevated transition-colors text-left">
                      <div class="text-sm font-extrabold text-text-primary">Transparent</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Checker preview</div>
                    </button>
                    <button type="button" data-mermaid-export-bg="light" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                      <div class="text-sm font-extrabold text-text-primary">Light</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">White</div>
                    </button>
                    <button type="button" data-mermaid-export-bg="dark" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                      <div class="text-sm font-extrabold text-text-primary">Dark</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Deep navy</div>
                    </button>
                    <button type="button" data-mermaid-export-bg="custom" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                      <div class="flex items-center justify-between">
                        <div>
                          <div class="text-sm font-extrabold text-text-primary">Custom</div>
                          <div class="text-[11px] text-text-secondary/70 mt-0.5">Pick a color</div>
                        </div>
                        <input data-mermaid-export-bgcolor="1" type="color" value="${backgroundColor}" class="w-9 h-9 rounded-xl border border-border bg-transparent p-1 cursor-pointer" />
                      </div>
                    </button>
                  </div>
                </div>

                <details class="mt-6 group">
                  <summary class="cursor-pointer select-none text-xs font-black uppercase tracking-wider text-text-secondary/60 flex items-center justify-between">
                    <span>Advanced</span>
                    <span class="text-[11px] text-text-secondary/40 group-open:hidden">Show</span>
                    <span class="text-[11px] text-text-secondary/40 hidden group-open:inline">Hide</span>
                  </summary>
                  <div class="mt-3 space-y-4">
                    <div data-mermaid-export-only="png">
                      <div class="flex items-center justify-between">
                        <div class="text-sm font-bold text-text-primary">PNG scale</div>
                        <div class="text-xs font-mono text-text-secondary/70"><span data-mermaid-export-scale-label="1">${scale}x</span></div>
                      </div>
                      <input data-mermaid-export-scale="1" type="range" min="1" max="4" step="1" value="${scale}" class="w-full mt-2" />
                      <div class="mt-1 text-[11px] text-text-secondary/60">Only affects PNG export.</div>
                    </div>
                    <div data-mermaid-export-only="svgpng">
                      <div class="flex items-center justify-between">
                        <div class="text-sm font-bold text-text-primary">Padding</div>
                        <div class="text-xs font-mono text-text-secondary/70"><span data-mermaid-export-padding-label="1">${padding}px</span></div>
                      </div>
                      <input data-mermaid-export-padding="1" type="range" min="0" max="96" step="4" value="${padding}" class="w-full mt-2" />
                      <div class="mt-1 text-[11px] text-text-secondary/60">Adds margin around the diagram.</div>
                    </div>
                    <div>
                      <div class="text-sm font-bold text-text-primary">File name</div>
                      <input data-mermaid-export-filename="1" type="text" value="${filename}" class="mt-2 w-full px-3 py-2 rounded-xl border border-border bg-surface text-sm font-semibold text-text-primary placeholder:text-text-secondary/40 focus:outline-none focus:ring-2 focus:ring-primary/20" placeholder="diagram" />
                      <div class="mt-1 text-[11px] text-text-secondary/60">Extension is added automatically.</div>
                    </div>
                  </div>
                </details>
              </div>

              <div class="md:col-span-3 p-5 min-h-0 flex flex-col">
                <div class="flex items-center justify-between">
                  <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Preview</div>
                  <div class="flex items-center gap-2">
                    <button type="button" data-mermaid-export-copy="1" class="px-3 py-2 rounded-xl border border-border bg-surface hover:bg-surface-elevated/70 transition-colors text-sm font-bold text-text-primary">Copy</button>
                    <button type="button" data-mermaid-export-download="1" class="px-3 py-2 rounded-xl bg-primary text-white hover:brightness-110 transition-colors text-sm font-black">Export</button>
                  </div>
                </div>
                <div class="mt-4 flex-1 min-h-0 rounded-2xl border border-border overflow-hidden">
                  <div data-mermaid-export-preview="1" class="w-full h-full overflow-auto px-5 pb-5 pt-3" style="${previewChecker}"></div>
                </div>
              </div>
            </div>

            <div class="h-16 px-6 border-t border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
              <div class="text-[11px] text-text-secondary/60 font-mono truncate">mermaid</div>
              <div class="flex items-center gap-2">
                <button type="button" data-mermaid-export-close="1" class="px-4 py-2 rounded-xl border border-border bg-surface hover:bg-surface-elevated/70 transition-colors text-sm font-bold text-text-primary">Cancel</button>
                <button type="button" data-mermaid-export-download="1" class="px-4 py-2 rounded-xl bg-primary text-white hover:brightness-110 transition-colors text-sm font-black">Export</button>
              </div>
            </div>
          </div>
        </div>
      `;

      const updateButtons = () => {
        const fmt = (modal.dataset.format || 'png') as any;
        const busy = modal.dataset.busy === '1';
        modal.querySelectorAll('.mermaid-export-format').forEach((el) => {
          const btn = el as HTMLButtonElement;
          const id = btn.getAttribute('data-mermaid-export-format');
          const active = id === fmt;
          btn.className = `mermaid-export-format px-3 py-3 rounded-xl border transition-colors text-left ${active ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`;
          btn.disabled = busy;
        });
        const bg = modal.dataset.background || 'transparent';
        modal.querySelectorAll('.mermaid-export-bg').forEach((el) => {
          const btn = el as HTMLButtonElement;
          const id = btn.getAttribute('data-mermaid-export-bg');
          const active = id === bg;
          btn.className = `mermaid-export-bg px-3 py-3 rounded-xl border transition-colors text-left ${active ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`;
          btn.disabled = busy;
        });

        modal.querySelectorAll('[data-mermaid-export-section="background"]').forEach((el) => {
          (el as HTMLElement).classList.toggle('hidden', fmt === 'mmd');
        });
        modal.querySelectorAll('[data-mermaid-export-only="png"]').forEach((el) => {
          (el as HTMLElement).classList.toggle('hidden', fmt !== 'png');
        });
        modal.querySelectorAll('[data-mermaid-export-only="svgpng"]').forEach((el) => {
          (el as HTMLElement).classList.toggle('hidden', fmt === 'mmd');
        });

        const filenameInput = modal.querySelector('[data-mermaid-export-filename="1"]') as HTMLInputElement | null;
        if (filenameInput) filenameInput.disabled = busy;
        const scaleInput = modal.querySelector('[data-mermaid-export-scale="1"]') as HTMLInputElement | null;
        if (scaleInput) scaleInput.disabled = busy;
        const paddingInput = modal.querySelector('[data-mermaid-export-padding="1"]') as HTMLInputElement | null;
        if (paddingInput) paddingInput.disabled = busy;
        const colorInput = modal.querySelector('[data-mermaid-export-bgcolor="1"]') as HTMLInputElement | null;
        if (colorInput) colorInput.disabled = busy;

        const copyBtn = modal.querySelector('[data-mermaid-export-copy="1"]') as HTMLButtonElement | null;
        if (copyBtn) {
          const isPng = fmt === 'png';
          copyBtn.disabled = busy || (isPng && !canCopyPng());
          copyBtn.className = `px-3 py-2 rounded-xl border border-border transition-colors text-sm font-bold ${copyBtn.disabled ? 'bg-surface text-text-secondary/40 cursor-not-allowed' : 'bg-surface hover:bg-surface-elevated/70 text-text-primary'}`;
          copyBtn.textContent = fmt === 'mmd' ? 'Copy MMD' : fmt === 'svg' ? 'Copy SVG' : 'Copy PNG';
          copyBtn.title = copyBtn.disabled && isPng && !canCopyPng() ? 'Your browser does not support copying PNG to clipboard.' : '';
        }

        modal.querySelectorAll('[data-mermaid-export-download="1"]').forEach((el) => {
          const btn = el as HTMLButtonElement;
          btn.disabled = busy;
          btn.textContent = busy ? 'Exporting…' : 'Export';
        });
      };

      const renderPreview = async () => {
        const preview = modal.querySelector('[data-mermaid-export-preview="1"]') as HTMLElement | null;
        if (!preview) return;
        const fmt = (modal.dataset.format || 'png') as 'png' | 'svg' | 'mmd';
        const bg = (modal.dataset.background || 'transparent') as 'transparent' | 'light' | 'dark' | 'custom';
        const bgColor = modal.dataset.backgroundColor || '#ffffff';
        const pad = parseInt(modal.dataset.padding || '0', 10) || 0;

        preview.innerHTML = '';
        const setPreviewBackground = () => {
          if (bg === 'transparent') {
            preview.setAttribute('style', previewChecker);
            return;
          }
          const fill = bg === 'custom' ? bgColor : bg === 'dark' ? '#0b1220' : '#ffffff';
          preview.setAttribute('style', `background: ${fill};`);
        };
        setPreviewBackground();

        if (fmt === 'mmd') {
          const pre = document.createElement('pre');
          pre.className = 'text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-2xl p-4 overflow-auto whitespace-pre-wrap';
          pre.textContent = normalized;
          preview.appendChild(pre);
          return;
        }

        const chart = widget.querySelector('.mermaid-chart');
        const existingSvg = getWidgetMermaidSvg(widget);
        if (!existingSvg && chart) {
          chart.setAttribute('data-processed', 'false');
          await renderMermaidChart(chart);
        }
        const svgEl = getWidgetMermaidSvg(widget);
        if (!svgEl) return;
        const svgString = buildExportSvgString(svgEl, { padding: pad, background: bg, backgroundColor: bgColor });
        const holder = document.createElement('div');
        holder.className = 'w-full flex justify-center items-start';
        holder.innerHTML = svgString;
        preview.appendChild(holder);
        preview.scrollTop = 0;
      };

      const setBusy = (next: boolean) => {
        modal.dataset.busy = next ? '1' : '0';
        updateButtons();
      };

      const getCurrentOpts = () => {
        return {
          format: (modal.dataset.format || 'png') as 'png' | 'svg' | 'mmd',
          background: (modal.dataset.background || 'transparent') as 'transparent' | 'light' | 'dark' | 'custom',
          backgroundColor: modal.dataset.backgroundColor || '#ffffff',
          scale: parseInt(modal.dataset.scale || '2', 10) || 2,
          padding: parseInt(modal.dataset.padding || '0', 10) || 0,
          filename: modal.dataset.filename || 'diagram',
        };
      };

      const onClick = async (e: MouseEvent) => {
        const t = e.target as HTMLElement | null;
        if (!t) return;
        const closeBtn = t.closest('[data-mermaid-export-close="1"]') as HTMLElement | null;
        if (closeBtn) {
          e.preventDefault();
          e.stopPropagation();
          closeMermaidExportModal();
          return;
        }

        const formatBtn = t.closest('[data-mermaid-export-format]') as HTMLElement | null;
        if (formatBtn) {
          e.preventDefault();
          e.stopPropagation();
          const nextFmt = (formatBtn.getAttribute('data-mermaid-export-format') || 'png') as any;
          modal.dataset.format = nextFmt;
          setMermaidExportPrefs({ format: nextFmt });
          updateButtons();
          await renderPreview();
          return;
        }

        const bgBtn = t.closest('[data-mermaid-export-bg]') as HTMLElement | null;
        if (bgBtn) {
          e.preventDefault();
          e.stopPropagation();
          const nextBg = (bgBtn.getAttribute('data-mermaid-export-bg') || 'transparent') as any;
          modal.dataset.background = nextBg;
          setMermaidExportPrefs({ background: nextBg });
          updateButtons();
          await renderPreview();
          return;
        }

        const copyBtn = t.closest('[data-mermaid-export-copy="1"]') as HTMLElement | null;
        if (copyBtn) {
          e.preventDefault();
          e.stopPropagation();
          if (modal.dataset.busy === '1') return;
          setBusy(true);
          try {
            const opts = getCurrentOpts();
            await copyMermaidFromWidget(widget, opts);
            showToast('success', opts.format === 'mmd' ? 'Copied MMD' : opts.format === 'svg' ? 'Copied SVG' : 'Copied PNG');
          } catch (err) {
            showToast('error', 'Copy failed');
          } finally {
            setBusy(false);
          }
          return;
        }

        const dlBtn = t.closest('[data-mermaid-export-download="1"]') as HTMLElement | null;
        if (dlBtn) {
          e.preventDefault();
          e.stopPropagation();
          if (modal.dataset.busy === '1') return;
          setBusy(true);
          try {
            const opts = getCurrentOpts();
            await exportMermaidFromWidget(widget, opts);
            showToast('success', opts.format === 'mmd' ? 'Exported MMD' : opts.format === 'svg' ? 'Exported SVG' : 'Exported PNG');
          } catch (err) {
            showToast('error', 'Export failed');
          } finally {
            setBusy(false);
          }
          return;
        }
      };

      const onInput = async (e: Event) => {
        const t = e.target as HTMLElement | null;
        if (!t) return;
        if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-bgcolor') === '1') {
          modal.dataset.backgroundColor = t.value || '#ffffff';
          modal.dataset.background = 'custom';
          setMermaidExportPrefs({ backgroundColor: modal.dataset.backgroundColor, background: 'custom' });
          updateButtons();
          await renderPreview();
          return;
        }
        if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-scale') === '1') {
          modal.dataset.scale = t.value;
          const label = modal.querySelector('[data-mermaid-export-scale-label="1"]') as HTMLElement | null;
          if (label) label.textContent = `${t.value}x`;
          setMermaidExportPrefs({ scale: parseInt(t.value, 10) || 2 });
          return;
        }
        if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-padding') === '1') {
          modal.dataset.padding = t.value;
          const label = modal.querySelector('[data-mermaid-export-padding-label="1"]') as HTMLElement | null;
          if (label) label.textContent = `${t.value}px`;
          setMermaidExportPrefs({ padding: parseInt(t.value, 10) || 0 });
          await renderPreview();
          return;
        }
        if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-filename') === '1') {
          modal.dataset.filename = t.value || '';
          setMermaidExportPrefs({ filename: modal.dataset.filename });
          return;
        }
      };

      const onKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          e.preventDefault();
          e.stopPropagation();
          closeMermaidExportModal();
          return;
        }
        if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
          const active = document.activeElement as HTMLElement | null;
          if (active && active.tagName === 'TEXTAREA') return;
          const btn = modal.querySelector('[data-mermaid-export-download="1"]') as HTMLButtonElement | null;
          if (btn && !btn.disabled) {
            e.preventDefault();
            btn.click();
          }
          return;
        }
        if (e.key !== 'Tab') return;
        const dialog = modal.querySelector('[data-mermaid-export-dialog="1"]') as HTMLElement | null;
        if (!dialog) return;
        const focusable = Array.from(
          dialog.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
        ).filter((el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && el.offsetParent !== null);
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const current = document.activeElement as HTMLElement | null;
        if (e.shiftKey) {
          if (!current || current === first || !dialog.contains(current)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (!current || current === last || !dialog.contains(current)) {
            e.preventDefault();
            first.focus();
          }
        }
      };

      document.body.appendChild(modal);
      mermaidExportEl = modal;
      updateButtons();
      await renderPreview();
      modal.addEventListener('click', onClick);
      modal.addEventListener('input', onInput);
      modal.addEventListener('keydown', onKeyDown);
      const primary = modal.querySelector('[data-mermaid-export-download="1"]') as HTMLButtonElement | null;
      const dialog = modal.querySelector('[data-mermaid-export-dialog="1"]') as HTMLElement | null;
      (primary || dialog)?.focus?.();
    };

    const openMermaidOverlay = async (encoded: string) => {
      closeMermaidOverlay();
      document.body.style.overflow = 'hidden';
      const preset = getMermaidThemePreset();

      const overlay = document.createElement('div');
      overlay.id = 'mermaid-overlay';
      overlay.className = 'fixed inset-0 z-[1200]';
      overlay.innerHTML = `
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" data-mermaid-overlay-close="1"></div>
        <div class="absolute inset-0 p-2 sm:p-4 md:p-6 flex items-center justify-center">
          <div class="w-[98vw] h-[94vh] max-w-none bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col">
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div class="text-sm font-bold text-gray-800">Mermaid</div>
              <button type="button" class="p-2 rounded-lg hover:bg-gray-50 text-gray-500 hover:text-gray-800" data-mermaid-overlay-close="1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
            <div class="p-3 sm:p-4 flex-1 min-h-0">
              <div class="mermaid-widget my-0" data-code="${encoded}" data-complete="true" data-scale="1" data-tx="0" data-ty="0" data-tab="diagram">
                <div class="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-xl shadow-sm">
                  <div class="flex items-center gap-2">
                    <button type="button" data-mermaid-action="tab-diagram" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors bg-gray-100 text-gray-900">Diagram</button>
                    <button type="button" data-mermaid-action="tab-code" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors text-gray-500 hover:text-gray-800 hover:bg-gray-50">Code</button>
                  </div>
                  <div class="flex items-center gap-1.5 text-gray-500">
                    <button type="button" data-mermaid-action="zoom-out" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom out">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="7" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        <line x1="8" y1="11" x2="14" y2="11" />
                      </svg>
                    </button>
                    <button type="button" data-mermaid-action="zoom-in" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom in">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="7" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        <line x1="11" y1="8" x2="11" y2="14" />
                        <line x1="8" y1="11" x2="14" y2="11" />
                      </svg>
                    </button>
                    <div class="w-px h-5 bg-gray-200 mx-1"></div>
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-semibold text-gray-500">Theme</span>
                      <select data-mermaid-theme-select="1" class="text-sm font-semibold text-gray-800 bg-white border border-gray-200 rounded-lg px-2 py-1.5 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20">
                        ${getMermaidThemeOptionsHtml(preset)}
                      </select>
                    </div>
                    <button type="button" data-mermaid-action="fit" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fit">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M8 3H3v5" />
                        <path d="M16 3h5v5" />
                        <path d="M21 16v5h-5" />
                        <path d="M3 16v5h5" />
                      </svg>
                      <span class="text-sm font-semibold">Fit</span>
                    </button>
                    <button type="button" data-mermaid-action="download" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Export">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                      </svg>
                      <span class="text-sm font-semibold">Export</span>
                    </button>
                    <button type="button" data-mermaid-action="reset" class="px-2 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Reset zoom">
                      <span class="mermaid-widget-zoom-label text-sm font-semibold">100%</span>
                    </button>
                  </div>
                </div>
                <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden">
                  <div class="mermaid-widget-diagram-panel">
                    <div class="mermaid-widget-viewport w-full h-[calc(94vh-220px)] overflow-auto">
                      <div class="mermaid-widget-zoom-area min-h-[360px] flex justify-center items-center p-4 sm:p-6 transition-all duration-300" style="transform: translate(0px, 0px) scale(1); transform-origin: top center;">
                        <div class="mermaid-chart w-full flex justify-center" data-code="${encoded}">
                          <div class="flex flex-col items-center justify-center">
                            <div class="loading-spinner w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="mermaid-widget-code-panel hidden p-4">
                    <pre class="mermaid-widget-code-pre text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-xl p-4 overflow-auto whitespace-pre-wrap"><code class="hljs language-plaintext mermaid-widget-code-code"></code></pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
      mermaidOverlayEl = overlay;

      requestAnimationFrame(async () => {
        const chartEl = overlay.querySelector('.mermaid-chart');
        if (chartEl) {
          chartEl.setAttribute('data-processed', 'false');
          await renderMermaidChart(chartEl);
        }
      });
    };

    const applyWidgetTransform = (widget: HTMLElement, nextScale: number, nextTx: number, nextTy: number) => {
      const clamped = Math.min(4, Math.max(0.25, nextScale));
      widget.setAttribute('data-scale', String(clamped));
      widget.setAttribute('data-tx', String(nextTx));
      widget.setAttribute('data-ty', String(nextTy));
      const zoomArea = widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
      if (zoomArea) {
        zoomArea.style.transform = `translate(${nextTx}px, ${nextTy}px) scale(${clamped})`;
        zoomArea.style.transformOrigin = 'top center';
        if (!zoomArea.style.cursor) zoomArea.style.cursor = 'grab';
      }
      const label = widget.querySelector('.mermaid-widget-zoom-label') as HTMLElement | null;
      if (label) label.textContent = `${Math.round(clamped * 100)}%`;
    };

    const getWidgetScale = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-scale') || '1') || 1;
    const getWidgetTx = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-tx') || '0') || 0;
    const getWidgetTy = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-ty') || '0') || 0;

    const applyWidgetScale = (widget: HTMLElement, nextScale: number) => {
      applyWidgetTransform(widget, nextScale, getWidgetTx(widget), getWidgetTy(widget));
    };

    const fitWidget = (widget: HTMLElement) => {
      const viewport = widget.querySelector('.mermaid-widget-viewport') as HTMLElement | null;
      const svg = widget.querySelector('svg') as SVGSVGElement | null;
      if (!viewport || !svg) return;
      const availW = viewport.clientWidth;
      const availH = viewport.clientHeight;
      if (!availW || !availH) return;

      let baseW = 0;
      let baseH = 0;
      const vb = (svg as any).viewBox?.baseVal;
      if (vb && vb.width > 0 && vb.height > 0) {
        baseW = vb.width;
        baseH = vb.height;
      } else {
        const wAttr = svg.getAttribute('width') || '';
        const hAttr = svg.getAttribute('height') || '';
        baseW = parseFloat(wAttr.replace('px', '')) || 0;
        baseH = parseFloat(hAttr.replace('px', '')) || 0;
      }

      if (!baseW || !baseH) {
        const current = getWidgetScale(widget);
        const rect = svg.getBoundingClientRect();
        baseW = rect.width / current;
        baseH = rect.height / current;
      }
      if (!baseW || !baseH) return;

      const padding = 56;
      const rawScale = Math.min((availW - padding) / baseW, (availH - padding) / baseH);
      const nextScale = Math.min(rawScale * 0.95, 1.2);
      if (!Number.isFinite(nextScale) || nextScale <= 0) return;
      applyWidgetTransform(widget, nextScale, 0, 0);
      try {
        viewport.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      } catch (e) {
        viewport.scrollTop = 0;
        viewport.scrollLeft = 0;
      }
    };

    let activePan: { widget: HTMLElement; startX: number; startY: number; startTx: number; startTy: number } | null = null;

    const setWidgetTab = (widget: HTMLElement, next: 'diagram' | 'code') => {
      widget.setAttribute('data-tab', next);
      const diagramBtn = widget.querySelector('[data-mermaid-action="tab-diagram"]') as HTMLElement | null;
      const codeBtn = widget.querySelector('[data-mermaid-action="tab-code"]') as HTMLElement | null;
      if (diagramBtn) diagramBtn.className = `px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${next === 'diagram' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`;
      if (codeBtn) codeBtn.className = `px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${next === 'code' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`;
      const diagramPanel = widget.querySelector('.mermaid-widget-diagram-panel') as HTMLElement | null;
      const codePanel = widget.querySelector('.mermaid-widget-code-panel') as HTMLElement | null;
      if (diagramPanel) diagramPanel.classList.toggle('hidden', next !== 'diagram');
      if (codePanel) codePanel.classList.toggle('hidden', next !== 'code');
      if (next === 'code') {
        const codeEl = widget.querySelector('.mermaid-widget-code-code') as HTMLElement | null;
        if (codeEl && !codeEl.innerHTML) {
          const encoded = widget.getAttribute('data-code') || '';
          const raw = decodeURIComponent(encoded);
          const normalized = normalizeMermaidCode(raw);
          codeEl.innerHTML = hljs.highlight(normalized, { language: 'plaintext' }).value;
        }
      }
    };

    const handleMermaidClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const overlayClose = target.closest('[data-mermaid-overlay-close="1"]') as HTMLElement | null;
      if (overlayClose) {
        e.preventDefault();
        e.stopPropagation();
        closeMermaidOverlay();
        return;
      }
      const btn = target.closest('[data-mermaid-action]') as HTMLElement | null;
      if (!btn) return;
      const widget = btn.closest('.mermaid-widget') as HTMLElement | null;
      if (!widget) return;
      const action = btn.getAttribute('data-mermaid-action') || '';

      if (action === 'tab-diagram' || action === 'tab-code' || action === 'zoom-in' || action === 'zoom-out' || action === 'reset' || action === 'fit' || action === 'download' || action === 'fullscreen') {
        e.preventDefault();
        e.stopPropagation();
      } else {
        return;
      }

      const currentScale = getWidgetScale(widget);
      if (action === 'tab-diagram') setWidgetTab(widget, 'diagram');
      if (action === 'tab-code') setWidgetTab(widget, 'code');
      if (action === 'zoom-in') applyWidgetScale(widget, currentScale * 1.2);
      if (action === 'zoom-out') applyWidgetScale(widget, currentScale / 1.2);
      if (action === 'reset') applyWidgetScale(widget, 1);
      if (action === 'fit') fitWidget(widget);
      if (action === 'fullscreen') {
        const encoded = widget.getAttribute('data-code') || '';
        openMermaidOverlay(encoded);
      }
      if (action === 'download') void openMermaidExportModal(widget);
    };

    const handleMermaidWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const widget = target.closest('.mermaid-widget') as HTMLElement | null;
      if (!widget) return;
      e.preventDefault();
      const currentScale = getWidgetScale(widget);
      const next = e.deltaY > 0 ? currentScale * 0.9 : currentScale * 1.1;
      applyWidgetTransform(widget, next, getWidgetTx(widget), getWidgetTy(widget));
    };

    const handleMermaidPointerDown = (e: PointerEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const viewport = target.closest('.mermaid-widget-viewport') as HTMLElement | null;
      if (!viewport) return;
      const widget = viewport.closest('.mermaid-widget') as HTMLElement | null;
      if (!widget) return;
      if ((widget.getAttribute('data-tab') || 'diagram') !== 'diagram') return;
      if (e.button !== 0) return;
      const zoomArea = widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
      if (zoomArea) zoomArea.style.cursor = 'grabbing';
      activePan = { widget, startX: e.clientX, startY: e.clientY, startTx: getWidgetTx(widget), startTy: getWidgetTy(widget) };
      e.preventDefault();
    };

    const handleMermaidPointerMove = (e: PointerEvent) => {
      if (!activePan) return;
      e.preventDefault();
      const { widget, startX, startY, startTx, startTy } = activePan;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      applyWidgetTransform(widget, getWidgetScale(widget), startTx + dx, startTy + dy);
    };

    const handleMermaidPointerUp = () => {
      if (!activePan) return;
      const zoomArea = activePan.widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
      if (zoomArea) zoomArea.style.cursor = 'grab';
      activePan = null;
    };

    const handleMermaidChange = (e: Event) => {
      const target = e.target as HTMLElement | null;
      if (!(target instanceof HTMLSelectElement)) return;
      if (target.getAttribute('data-mermaid-theme-select') !== '1') return;

      const next = target.value as MermaidThemePreset;
      setMermaidThemePreset(next);

      document.querySelectorAll('select[data-mermaid-theme-select="1"]').forEach((el) => {
        if (el instanceof HTMLSelectElement) el.value = next;
      });

      document.querySelectorAll('.mermaid-chart').forEach((container) => {
        container.setAttribute('data-processed', 'false');
        renderMermaidChart(container);
      });
    };

    document.addEventListener('click', handleMermaidClick);
    document.addEventListener('wheel', handleMermaidWheel, { passive: false });
    document.addEventListener('change', handleMermaidChange);
    document.addEventListener('pointerdown', handleMermaidPointerDown);
    document.addEventListener('pointermove', handleMermaidPointerMove, { passive: false } as any);
    document.addEventListener('pointerup', handleMermaidPointerUp);
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (e.defaultPrevented) return;
        if (mermaidExportEl) closeMermaidExportModal();
        else closeMermaidOverlay();
      }
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('click', handleGlobalClick);
      document.removeEventListener('click', handleMermaidClick);
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

  createEffect(() => {
    messages();
    requestAnimationFrame(() => {
      const charts = document.querySelectorAll('.mermaid-chart');
      charts.forEach(async (container) => {
        await renderMermaidChart(container);
      });
    });
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
                } else if (data.prompt_tokens !== undefined || data.completion_tokens !== undefined || data.total_tokens !== undefined || data.tps !== undefined) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { 
                      ...newMsgs[lastIndex], 
                      prompt_tokens: data.prompt_tokens,
                      completion_tokens: data.completion_tokens,
                      total_tokens: data.total_tokens,
                      tps: data.tps
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

  const formatCitation = (c: any) => {
    const path = typeof c?.path === 'string' ? c.path : '';
    const startLine = typeof c?.start_line === 'number' ? c.start_line : null;
    const endLine = typeof c?.end_line === 'number' ? c.end_line : null;
    const startPage = typeof c?.start_page === 'number' ? c.start_page : null;
    const endPage = typeof c?.end_page === 'number' ? c.end_page : null;
    if (path && startLine !== null && endLine !== null) return `${path}#L${startLine}-L${endLine}`;
    if (path && startPage !== null && endPage !== null) return `${path}#P${startPage}-P${endPage}`;
    return path || 'Unknown source';
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
              <div class={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
                <div class="flex items-center gap-2 px-1">
                  <div class={`w-5 h-5 rounded-full flex items-center justify-center border ${msg.role === 'user' ? 'border-text-secondary/20 bg-text-secondary/10 text-text-secondary/60' : 'border-primary/30 bg-primary/10 text-primary/70'}`}>
                    <Show when={msg.role === 'user'}>
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5zm0 2c-3.333 0-10 1.667-10 5v3h20v-3c0-3.333-6.667-5-10-5z"/>
                      </svg>
                    </Show>
                    <Show when={msg.role !== 'user'}>
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2a8 8 0 00-8 8v2a8 8 0 0016 0v-2a8 8 0 00-8-8zm0 3a3 3 0 110 6 3 3 0 010-6zm-6 9.2a6 6 0 0112 0A6.98 6.98 0 0112 20a6.98 6.98 0 01-6-5.8z"/>
                      </svg>
                    </Show>
                  </div>
                  <span class={`text-[10px] font-black uppercase tracking-[0.24em] ${msg.role === 'user' ? 'text-text-secondary/50' : 'text-primary/70'}`}>
                    {msg.role === 'user' ? 'You' : activeAgentName()}
                  </span>
                </div>
                <div class={`group relative max-w-[85%] lg:max-w-[75%] ${
                  msg.role === 'user' 
                    ? 'bg-surface text-text-primary px-6 py-4 shadow-sm border border-primary/20 rounded-[26px] rounded-br-none overflow-hidden' 
                    : 'bg-surface text-text-primary border border-border/50 px-6 py-5 shadow-sm rounded-[24px] rounded-bl-none'
                }`}>
                  {msg.role === 'user' ? (
                     <>
                       <div class="absolute inset-0 pointer-events-none overflow-hidden">
                         <div class="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-primary/10 blur-3xl"></div>
                         <div class="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-primary/5 blur-3xl"></div>
                         <div class="absolute inset-0 bg-[linear-gradient(135deg,rgba(16,185,129,0.10),transparent_55%,rgba(16,185,129,0.06))]"></div>
                       </div>
                       <Show when={msg.images && msg.images.length > 0}>
                         <div class="flex flex-wrap gap-2 mb-2 relative z-10">
                           <For each={msg.images}>
                             {(img) => (
                               <img src={img} class="max-w-full h-auto max-h-64 rounded-lg border border-white/10" alt="User upload" />
                             )}
                           </For>
                         </div>
                       </Show>
                       <div class="relative whitespace-pre-wrap leading-relaxed font-medium text-[15px] select-text">{msg.content}</div>
                       <div class="mt-3 flex justify-end">
                         <div class="flex items-center gap-1 p-1 rounded-2xl bg-surface/70 backdrop-blur-md ring-1 ring-border/70 shadow-sm transition-opacity opacity-100 lg:opacity-0 lg:group-hover:opacity-100">
                           <button
                             class={`p-1.5 rounded-xl transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                               copiedMessageIndex() === index()
                                 ? 'text-emerald-500 bg-emerald-500/10'
                                 : 'text-text-secondary/70 hover:text-primary hover:bg-primary/10'
                             }`}
                             title={copiedMessageIndex() === index() ? "Copied" : "Copy"}
                             aria-label="Copy message"
                             onClick={() => copyUserMessage(msg.content, index())}
                           >
                             <Show
                               when={copiedMessageIndex() === index()}
                               fallback={
                                 <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                                 </svg>
                               }
                             >
                               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                               </svg>
                             </Show>
                           </button>
                           <button
                             class="p-1.5 rounded-xl text-text-secondary/70 hover:text-primary hover:bg-primary/10 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                             title="Quote"
                             aria-label="Quote message"
                             onClick={() => quoteUserMessage(msg.content)}
                           >
                             <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h7M7 16h10" />
                             </svg>
                           </button>
                           <button
                             class="p-1.5 rounded-xl text-text-secondary/70 hover:text-primary hover:bg-primary/10 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                             title="Edit"
                             aria-label="Edit message"
                             onClick={() => editUserMessage(msg.content)}
                           >
                             <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 20h9" />
                               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
                             </svg>
                           </button>
                         </div>
                       </div>
                       {renderMetaBadges(msg, index())}
                     </>
                  ) : (
                     <div class="relative space-y-5">
                        {(() => {
                          const { thought, content, isThinking } = parseThoughtAndContent(msg.content);
                          return (
                            <>
                              <Show when={thought || isThinking}>
                                <div class="bg-black/5 dark:bg-black/20 -mx-6 -mt-5 rounded-t-[24px] border-b border-border/10 overflow-hidden group/thought mb-5">
                                  <button 
                                    onClick={() => toggleThought(index())}
                                    class="w-full flex items-center justify-between px-6 py-3 cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
                                  >
                                    <div class="flex items-center gap-3">
                                      <div class="relative flex items-center justify-center w-5 h-5">
                                        <Show when={isThinking}>
                                          <div class="absolute inset-0 bg-primary/10 rounded-full animate-ping"></div>
                                          <div class="absolute inset-0.5 border border-primary/20 rounded-full animate-[spin_3s_linear_infinite]"></div>
                                        </Show>
                                        <div class={`relative w-2 h-2 rounded-full transition-all duration-700 ${isThinking ? 'bg-primary shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-text-secondary/30'}`}></div>
                                      </div>
                                      <div class="flex items-center gap-2">
                                        <span class="text-[13px] font-medium text-text-secondary">
                                          {isThinking ? 'Thinking Process' : 'Reasoning Chain'}
                                        </span>
                                        <span class="text-[11px] font-mono text-text-secondary/40">
                                          {msg.thought_duration 
                                            ? `${msg.thought_duration < 60 ? msg.thought_duration.toFixed(1) + 's' : Math.floor(msg.thought_duration / 60) + 'm ' + (msg.thought_duration % 60).toFixed(0) + 's'}`
                                            : (isThinking ? `${elapsedTime().toFixed(1)}s` : '')}
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
                                    <div class="px-6 py-4 text-[13px] text-text-secondary/80 leading-relaxed overflow-y-auto max-h-[500px] border-t border-border/5 bg-black/5 dark:bg-black/10">
                                      {renderThought(thought)}
                                    </div>
                                  </div>
                                </div>
                              </Show>
                              
                              <Show when={content || (isTyping() && !thought)}>
                                <div 
                                  innerHTML={renderMarkdown(content)} 
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

                              <Show when={(msg.citations?.length ?? 0) > 0}>
                                <details class="mt-5 -mx-2 rounded-2xl border border-border/50 bg-black/5 dark:bg-white/5 px-4 py-3">
                                  <summary class="cursor-pointer text-xs font-black uppercase tracking-[0.2em] text-text-secondary/70">
                                    Sources ({msg.citations?.length ?? 0})
                                  </summary>
                                  <div class="mt-3 space-y-2">
                                    <For each={msg.citations || []}>
                                      {(c) => (
                                        <div class="rounded-xl border border-border/40 bg-surface/60 px-3 py-2">
                                          <div class="text-xs font-mono text-text-secondary">{formatCitation(c)}</div>
                                          <Show when={typeof c?.snippet === 'string' && c.snippet.trim().length > 0}>
                                            <pre class="mt-2 text-[12px] leading-relaxed whitespace-pre-wrap font-mono text-text-secondary/80 max-h-56 overflow-auto">{c.snippet}</pre>
                                          </Show>
                                        </div>
                                      )}
                                    </For>
                                  </div>
                                </details>
                              </Show>
                            </>
                          );
                        })()}
                        
                        <Show when={isTyping() && index() === messages().length - 1}>
                          <span class="inline-block w-2.5 h-5 ml-1 bg-primary/30 animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(16,185,129,0.3)]"></span>
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
                        {renderMetaBadges(msg, index())}
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
                  placeholder={`You are chatting with ${activeAgentName()} now`}
                  class="w-full bg-transparent px-6 pt-5 pb-20 focus:outline-none resize-none min-h-[96px] max-h-[400px] overflow-y-auto text-text-primary leading-relaxed text-lg font-medium placeholder:text-text-secondary/30"
                  rows={1}
                />
                
                {/* Unified Action Bar */}
                <div class="absolute bottom-4 left-5 right-5 flex items-center justify-between">
                  {/* Left Side: Configuration */}
                  <div class="flex items-center gap-3">
                    {/* Model Selector */}
                    <div class="relative">
                      <button 
                        type="button"
                        onClick={(e) => { 
                          e.stopPropagation();
                          setShowLLMSelector(!showLLMSelector());
                        }}
                        class="flex items-center gap-2.5 px-4 py-2.5 bg-background border border-border hover:border-primary/30 hover:bg-primary/5 rounded-2xl transition-all active:scale-95 shadow-sm"
                      >
                        <div class="w-2 h-2 rounded-full bg-primary animate-pulse"></div>
                        <span class="text-xs font-bold text-text-primary uppercase tracking-wider">{selectedModel() || "Select Model"}</span>
                        <svg xmlns="http://www.w3.org/2000/svg" class={`h-3.5 w-3.5 text-text-secondary transition-transform duration-300 ${showLLMSelector() ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      <Show when={showLLMSelector()}>
                        <div class="absolute bottom-full left-0 mb-3 w-72 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200">
                          <div class="p-4 border-b border-white/10 flex items-center justify-between bg-white/5">
                            <span class="text-xs font-bold text-white/70 uppercase tracking-widest">{showAllModels() ? 'All Models' : 'Enabled Models'}</span>
                            <div class="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowAllModels(!showAllModels());
                                }}
                                class="text-[10px] px-2 py-1 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-white/80 font-bold uppercase tracking-wider"
                              >
                                {showAllModels() ? 'Enabled' : 'All'}
                              </button>
                              <Show when={isRefreshingModels()}>
                                <div class="w-4 h-4 border-2 border-white/20 border-t-primary rounded-full animate-spin"></div>
                              </Show>
                            </div>
                          </div>
                          <div class="p-2 max-h-80 overflow-y-auto space-y-1 scrollbar-thin scrollbar-thumb-white/10">
                            <For each={providers().filter(p => {
                              const list = showAllModels() ? (p.models || []) : (p.available_models || []);
                              return Array.isArray(list) && list.length > 0;
                            })}>
                              {provider => (
                                <div>
                                  <div class="flex items-center justify-between gap-2 px-3 py-2 text-[10px] font-bold text-primary uppercase bg-primary/10 rounded-lg mb-1 tracking-wider">
                                    <span>{provider.name}</span>
                                    <button
                                      type="button"
                                      disabled={!provider.supports_model_refresh || isRefreshingModels()}
                                      title={provider.supports_model_refresh ? 'Refresh models for this provider' : 'This provider does not support model refresh'}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        if (!provider.supports_model_refresh) return;
                                        setIsRefreshingModels(true);
                                        loadProviders(true).finally(() => setIsRefreshingModels(false));
                                      }}
                                      class={`text-[10px] px-2 py-1 rounded-lg border font-bold uppercase tracking-wider ${
                                        provider.supports_model_refresh && !isRefreshingModels()
                                          ? 'border-white/10 bg-white/5 hover:bg-white/10 text-white/80'
                                          : 'border-white/10 bg-white/5 text-white/30 cursor-not-allowed'
                                      }`}
                                    >
                                      Refresh
                                    </button>
                                  </div>
                                  <For each={(showAllModels() ? provider.models : provider.available_models) || []}>
                                    {model => (
                                      <button
                                        onClick={() => {
                                          setSelectedProvider(provider.name);
                                          setSelectedModel(model);
                                          localStorage.setItem(PROVIDER_STORAGE_KEY, provider.name);
                                          localStorage.setItem(MODEL_STORAGE_KEY, model);
                                          setShowLLMSelector(false);
                                        }}
                                        class={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-between group ${
                                          selectedModel() === model
                                            ? 'bg-primary text-white font-bold shadow-lg shadow-primary/20'
                                            : 'hover:bg-white/5 text-gray-300 hover:text-white'
                                        }`}
                                      >
                                        <span>{model}</span>
                                        <Show when={selectedModel() === model}>
                                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
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
                          <span class="font-bold text-white/90">Voice Input (Beta)</span>
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
                  Select a model to start
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
