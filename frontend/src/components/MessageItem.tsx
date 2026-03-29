import { createSignal, For, Show, onCleanup, createEffect, createMemo } from 'solid-js';
import { Message } from '../types';
import { renderMarkdown } from '../utils/markdown';
import { getAdaptedThought } from "../utils/thoughtParser";
import ToolCallItem, { getDownloadArtifact, getScreenshotPreview, isBrowserSnapshotTool, parseToolCallResultPayload } from './ToolCallItem';
import MessageExportMenu from './MessageExportMenu';
import SpeechControl from './SpeechControl';
import { getSpeechMessageId } from '../utils/speech';
import { useMaybeSpeechController } from '../context/SpeechControllerContext';

interface MessageItemProps {
  msg: Message;
  index: number;
  activeAgentName: string;
  isTyping: boolean;
  expandedThoughts: Record<number, boolean>;
  toggleThought: (index: number) => void;
  elapsedTime: number;
  copiedMessageIndex: number | null;
  copyUserMessage: (content: string, index: number) => void;
  quoteUserMessage: (content: string) => void;
  handleRegenerate: (index: number) => void;
  onContinue: (msg: Message) => void;
  selectedProvider: string;
  selectedModel: string;
}

export const getVisionBadge = (msg: Pick<Message, 'supports_vision' | 'vision_enabled' | 'vision_fallback_mode' | 'image_count'>) => {
  const imageCount = typeof msg.image_count === 'number' ? msg.image_count : 0;
  if (msg.vision_fallback_mode === 'text_only' && imageCount > 0) {
    return {
      label: 'Vision Fallback',
      className: 'bg-amber-500/5 border-amber-500/20 text-amber-500',
    };
  }
  if (msg.supports_vision === true && msg.vision_enabled === true) {
    return {
      label: 'Vision On',
      className: 'bg-emerald-500/5 border-emerald-500/20 text-emerald-500',
    };
  }
  if (msg.supports_vision === true) {
    return {
      label: 'Vision Ready',
      className: 'bg-sky-500/5 border-sky-500/20 text-sky-500',
    };
  }
  if (msg.supports_vision === false) {
    return {
      label: 'Vision Off',
      className: 'bg-rose-500/5 border-rose-500/20 text-rose-500',
    };
  }
  return null;
};

export const getVisionFeedbackText = (
  msg: Pick<Message, 'error_code' | 'vision_fallback_mode' | 'image_count'>,
): string => {
  if (msg.error_code === 'MODEL_VISION_UNSUPPORTED') {
    return '该模型不支持视觉能力，请切换到带 Vision 标识的模型后重试。';
  }
  const imageCount = typeof msg.image_count === 'number' ? msg.image_count : 0;
  if (msg.vision_fallback_mode === 'text_only' && imageCount > 0) {
    return '已自动降级为纯文本模式，本次回复不会分析图片内容。';
  }
  return '';
};

const _SYSTEM_MESSAGE_PREFIXES = [
  '[Action Preflight]',
  '[Action Flow]',
  '[Action Approval]',
  '[Tool Result]',
];

const _looksLikeStructuredPayloadLine = (value: string): boolean => {
  const trimmed = value.trim();
  if (!trimmed) return false;
  return (
    trimmed.startsWith('{') ||
    trimmed.startsWith('}') ||
    trimmed.startsWith('[') ||
    trimmed.startsWith(']') ||
    trimmed.startsWith('"') ||
    trimmed.startsWith(',') ||
    trimmed.startsWith(':') ||
    trimmed in { 'true': true, 'false': true, 'null': true } ||
    trimmed.includes('download_url') ||
    trimmed.includes('download_markdown') ||
    trimmed.includes('artifact') ||
    trimmed.includes('file_path') ||
    trimmed.includes('filename')
  );
};

export const sanitizeAssistantDisplayContent = (content?: string | null): string => {
  if (!content) return '';

  const normalized = content.replace(/\r\n/g, '\n');
  const lines = normalized.split('\n');
  const kept: string[] = [];
  let skippingToolPayload = false;
  let skippingArtifactFollowup = false;

  for (const line of lines) {
    const trimmed = line.trim();

    if (_SYSTEM_MESSAGE_PREFIXES.some((prefix) => trimmed.startsWith(prefix))) {
      skippingToolPayload = trimmed.startsWith('[Tool Result]');
      skippingArtifactFollowup = false;
      continue;
    }

    if (trimmed === 'Screenshot ready:' || trimmed === 'Artifact ready:') {
      skippingArtifactFollowup = true;
      skippingToolPayload = false;
      continue;
    }

    if (skippingToolPayload) {
      if (!trimmed || _looksLikeStructuredPayloadLine(trimmed)) {
        continue;
      }
      skippingToolPayload = false;
    }

    if (skippingArtifactFollowup) {
      if (
        !trimmed ||
        trimmed.startsWith('![') ||
        /^\[.+\]\(.+\)$/.test(trimmed) ||
        trimmed.includes('/exports/')
      ) {
        continue;
      }
      skippingArtifactFollowup = false;
    }

    kept.push(line);
  }

  return kept
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

export const stripDuplicateArtifactReferences = (
  content: string,
  artifactUrls: string[],
): string => {
  if (!content) return '';
  const normalizedUrls = artifactUrls
    .map((url) => url.trim())
    .filter(Boolean);
  if (normalizedUrls.length === 0) return content;

  const lines = content.split('\n');
  const kept = lines.filter((line) => {
    const trimmed = line.trim();
    if (!trimmed) return true;

    return !normalizedUrls.some((url) => {
      if (!trimmed.includes(url)) return false;
      return (
        trimmed.startsWith('![') ||
        /^\[.+\]\(.+\)$/.test(trimmed) ||
        trimmed === url
      );
    });
  });

  return kept.join('\n').replace(/\n{3,}/g, '\n\n').trim();
};

export const formatSnapshotVisibleText = (
  value?: string | null,
  pageTitle?: string | null,
): string => {
  const structured = structureSnapshotVisibleText(value, pageTitle);
  if (structured.resultItems.length > 0) {
    return [
      ...structured.headerLines,
      structured.scopeLine,
      structured.sortLine,
      ...structured.resultItems,
      ...structured.paragraphs,
    ]
      .filter(Boolean)
      .join('\n\n');
  }

  if (!value) return '';
  let normalized = value.replace(/\r\n/g, '\n').trim();
  if (!normalized) return '';

  const trimmedTitle = typeof pageTitle === 'string' ? pageTitle.trim() : '';
  if (trimmedTitle && normalized.startsWith(trimmedTitle)) {
    normalized = normalized.slice(trimmedTitle.length).trim();
  }

  if (!normalized.includes('\n')) {
    normalized = normalized
      .replace(/(Models Docs Pricing Sign in Download)\s+/g, '$1\n\n')
      .replace(/(Cloud Embedding Vision Tools Thinking)\s+/g, '$1\n\n')
      .replace(/(Popular Newest)\s+/g, '$1\n\n')
      .replace(/\s+(Updated\s+\d+\s+\w+\s+ago)\s+/g, ' $1\n\n');
  }

  return normalized
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

type StructuredSnapshotText = {
  headerLines: string[];
  scopeLine: string;
  sortLine: string;
  resultItems: string[];
  paragraphs: string[];
};

const SNAPSHOT_HEADER_PATTERNS = [
  /^Models Docs Pricing Sign in Download\b/i,
  /^Cloud Embedding Vision Tools Thinking\b/i,
];

const SNAPSHOT_SORT_PATTERN = /^(Popular Newest|Popular|Newest)\b/i;
const SNAPSHOT_RESULT_SPLIT_PATTERN = /(?<=Updated\s+\d+\s+\w+\s+ago)\s+(?=[a-z0-9][\w.-]{1,40}(?:\s|$))/i;

export const structureSnapshotVisibleText = (
  value?: string | null,
  pageTitle?: string | null,
): StructuredSnapshotText => {
  if (!value) {
    return {
      headerLines: [],
      scopeLine: '',
      sortLine: '',
      resultItems: [],
      paragraphs: [],
    };
  }

  let normalized = value.replace(/\r\n/g, '\n').trim();
  const trimmedTitle = typeof pageTitle === 'string' ? pageTitle.trim() : '';
  if (trimmedTitle && normalized.startsWith(trimmedTitle)) {
    normalized = normalized.slice(trimmedTitle.length).trim();
  }

  if (!normalized) {
    return {
      headerLines: [],
      scopeLine: '',
      sortLine: '',
      resultItems: [],
      paragraphs: [],
    };
  }

  if (normalized.includes('\n')) {
    return {
      headerLines: [],
      scopeLine: '',
      sortLine: '',
      resultItems: [],
      paragraphs: normalized
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .split(/\n{2,}/)
        .map((item) => item.trim())
        .filter(Boolean),
    };
  }

  let working = normalized.replace(/\s+/g, ' ').trim();
  const headerLines: string[] = [];

  for (const pattern of SNAPSHOT_HEADER_PATTERNS) {
    const match = working.match(pattern);
    if (!match || match.index !== 0) continue;
    headerLines.push(match[0].trim());
    working = working.slice(match[0].length).trim();
  }

  let scopeLine = '';
  const scopeMatch = working.match(/^(Cloud|Embedding|Vision|Tools|Thinking)(?:\s+\S+){0,12}/i);
  if (!headerLines.some((line) => /Cloud Embedding Vision Tools Thinking/i.test(line)) && scopeMatch && scopeMatch.index === 0) {
    scopeLine = scopeMatch[0].trim();
    working = working.slice(scopeMatch[0].length).trim();
  }

  let sortLine = '';
  const sortMatch = working.match(SNAPSHOT_SORT_PATTERN);
  if (sortMatch && sortMatch.index === 0) {
    sortLine = sortMatch[1].trim();
    working = working.slice(sortMatch[0].length).trim();
  }

  const resultItems = working
    ? working
        .split(SNAPSHOT_RESULT_SPLIT_PATTERN)
        .map((item) => item.trim())
        .filter(Boolean)
    : [];

  if (resultItems.length <= 1) {
    return {
      headerLines,
      scopeLine,
      sortLine,
      resultItems: [],
      paragraphs: [
        [scopeLine, sortLine, working].filter(Boolean).join(' ').trim(),
      ].filter(Boolean),
    };
  }

  return {
    headerLines,
    scopeLine,
    sortLine,
    resultItems,
    paragraphs: [],
  };
};

const getSnapshotItemTitle = (value: string): string => {
  const match = value.trim().match(/^([^\s]+)\s+(.+)$/);
  return match ? match[1].trim() : value.trim();
};

const getSnapshotItemBody = (value: string): string => {
  const match = value.trim().match(/^([^\s]+)\s+(.+)$/);
  return match ? match[2].trim() : '';
};

type BrowserScreenshotArtifact = {
  kind: 'screenshot';
  url: string;
  alt: string;
  toolName: string;
  sourceUrl: string;
};

type DownloadArtifact = {
  kind: 'download';
  url: string;
  filename: string;
  kindLabel: string;
  toolName: string;
  sourceUrl: string;
  isImage: boolean;
};

type MessageArtifact = BrowserScreenshotArtifact | DownloadArtifact;

type BrowserSnapshotArtifact = {
  kind: 'snapshot';
  toolName: string;
  sourceUrl: string;
  pageTitle: string;
  visibleText: string;
  interactiveCount: number;
  bindingSource: string;
  bindingUrl: string;
};

type UnifiedArtifact = MessageArtifact | BrowserSnapshotArtifact;

export default function MessageItem(props: MessageItemProps) {
  const speechController = useMaybeSpeechController();
  const [waitSecs, setWaitSecs] = createSignal(0);
  let timer: any;

  const [exportMenuPos, setExportMenuPos] = createSignal<{x: number, y: number} | null>(null);

  const handleExportClick = (e: MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setExportMenuPos({ x: rect.left, y: rect.bottom + 8 });
  };

  // Memoize parsing to avoid redundant work and logic issues during non-typing states
  const adapted = createMemo(() => getAdaptedThought(props.msg, props.isTyping));

  createEffect(() => {
    const { content } = adapted();
    // 只要还在打字，且没有最终内容，就继续计时
    if (props.isTyping && !content) {
      if (!timer) {
        setWaitSecs(0);
        timer = setInterval(() => {
          setWaitSecs(prev => prev + 1);
        }, 1000);
      }
    } else {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }
  });

  onCleanup(() => {
    if (timer) clearInterval(timer);
  });

  const getLoadingStatus = () => {
    const s = waitSecs();
    if (s < 3) return { title: "Initializing", sub: "Agent is preparing response..." };
    if (s < 8) return { title: "Analyzing", sub: "Searching for the best approach..." };
    if (s < 15) return { title: "Deep Thinking", sub: "Processing complex request details..." };
    return { title: "Still Thinking", sub: "Taking longer than usual, thanks for your patience." };
  };

  const isTruncated = () => {
    if (props.msg.finish_reason === 'length') return true;
    if (props.msg.role !== 'assistant' || props.isTyping) return false;
    
    const content = props.msg.content || "";
    // Check for unclosed code blocks
    const codeBlockCount = (content.match(/```/g) || []).length;
    if (codeBlockCount > 0 && codeBlockCount % 2 !== 0) return true;
    
    // Check for unclosed HTML tags if it looks like HTML (basic check)
    if (content.includes('<html') && !content.includes('</html>')) return true;
    
    return false;
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

  const responseStatus = (msg: Message) => {
    if (msg.error || (msg.content && msg.content.startsWith("Error:"))) return "Failed";
    if (msg.role === "assistant" && props.isTyping) return "Generating";
    return "Completed";
  };

  const modelLabel = (msg: Message) => {
    const provider = msg.provider || props.selectedProvider;
    const model = msg.model || props.selectedModel;
    if (provider && model) return `${provider}/${model}`;
    if (model) return model;
    return "Unknown model";
  };
  const visionBadge = () => getVisionBadge(props.msg);
  const visionFeedbackText = () => getVisionFeedbackText(props.msg);
  const getToolSourceUrl = (args: unknown) => {
    if (!args || typeof args !== 'object' || Array.isArray(args)) return '';
    const sourceUrl = (args as Record<string, unknown>).url;
    return typeof sourceUrl === 'string' ? sourceUrl : '';
  };
  const artifactItems = (): MessageArtifact[] =>
    (props.msg.tool_calls || [])
      .map((toolCall) => {
        const screenshot = getScreenshotPreview(toolCall.tool_name, toolCall.result);
        const sourceUrl = getToolSourceUrl(toolCall.args);
        if (screenshot) {
          return { kind: 'screenshot', ...screenshot, toolName: toolCall.tool_name, sourceUrl } as MessageArtifact;
        }

        const artifact = getDownloadArtifact(toolCall.tool_name, toolCall.result);
        if (!artifact) return null;
        return {
          kind: 'download',
          ...artifact,
          toolName: toolCall.tool_name,
          sourceUrl,
          isImage: /\.(png|jpe?g|gif|webp|svg)$/i.test(artifact.url || artifact.filename),
        } as MessageArtifact;
      })
      .filter((item): item is MessageArtifact => item !== null);
  const browserSnapshotItems = (): BrowserSnapshotArtifact[] =>
    (props.msg.tool_calls || [])
      .map((toolCall) => {
        if (!isBrowserSnapshotTool(toolCall.tool_name)) return null;
        const payload = parseToolCallResultPayload(toolCall.result);
        const snapshot = payload && typeof payload === 'object' && !Array.isArray(payload)
          ? (payload as Record<string, any>).snapshot
          : null;
        const browserContext = payload && typeof payload === 'object' && !Array.isArray(payload)
          ? (payload as Record<string, any>).browser_context
          : null;
        const snapshotRecord = snapshot && typeof snapshot === 'object' && !Array.isArray(snapshot)
          ? snapshot as Record<string, any>
          : null;
        const browserContextRecord = browserContext && typeof browserContext === 'object' && !Array.isArray(browserContext)
          ? browserContext as Record<string, any>
          : null;
        if (!payload || !snapshotRecord) return null;

        const sourceUrl = typeof browserContextRecord?.url === 'string'
          ? browserContextRecord.url
          : getToolSourceUrl(toolCall.args);
        const pageTitle = typeof browserContextRecord?.page_title === 'string' ? browserContextRecord.page_title : '';
        const visibleText = typeof snapshotRecord.visible_text === 'string' ? snapshotRecord.visible_text.trim() : '';
        const interactiveElements = Array.isArray(snapshotRecord.interactive_elements)
          ? snapshotRecord.interactive_elements.filter((item) => item && typeof item === 'object').length
          : 0;
        const bindingContext = snapshotRecord.target_binding_context && typeof snapshotRecord.target_binding_context === 'object' && !Array.isArray(snapshotRecord.target_binding_context)
          ? snapshotRecord.target_binding_context as Record<string, any>
          : null;

        return {
          kind: 'snapshot',
          toolName: toolCall.tool_name,
          sourceUrl,
          pageTitle,
          visibleText,
          interactiveCount: interactiveElements,
          bindingSource: typeof bindingContext?.binding_source === 'string' ? bindingContext.binding_source : '',
          bindingUrl: typeof bindingContext?.binding_url === 'string' ? bindingContext.binding_url : '',
        };
      })
      .filter((item): item is BrowserSnapshotArtifact => item !== null);
  const unifiedArtifacts = (): UnifiedArtifact[] => {
    const items: UnifiedArtifact[] = [...browserSnapshotItems(), ...artifactItems()];
    const rank = (artifact: UnifiedArtifact) =>
      artifact.kind === 'snapshot' ? 0 : artifact.kind === 'screenshot' ? 1 : 2;
    return items.sort((a, b) => rank(a) - rank(b));
  };
  const speechMessageId = () => getSpeechMessageId(props.msg, props.index);
  const speechState = () => speechController?.getMessageState(speechMessageId()) || 'idle';
  const handleSpeechShortcut = (e: KeyboardEvent) => {
    if (props.msg.role !== 'assistant') return;
    if (!speechController?.supported()) return;
    if (e.defaultPrevented) return;
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key.toLowerCase() !== 'r') return;
    const target = e.target as HTMLElement | null;
    if (target?.closest('button, input, textarea, select, [contenteditable="true"]')) return;
    e.preventDefault();
    speechController.toggleMessage(speechMessageId(), props.msg.content);
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
        class="prose prose-sm max-w-none text-text-primary leading-relaxed font-sans"
        innerHTML={renderMarkdown(processedThought, props.isTyping)}
      />
    );
  };

  const artifactShellClass =
    'overflow-hidden rounded-[1rem] border border-slate-200/55 bg-white/70 shadow-[0_8px_24px_rgba(15,23,42,0.04)]';
  const artifactHeaderClass =
    'flex items-start justify-between gap-3 px-4 pt-4 pb-2';
  const artifactMetaLabelClass =
    'text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500/80';
  const artifactMetaValueClass =
    'mt-1 block break-all text-[12px] font-medium text-text-primary hover:text-primary hover:underline';

  const renderMetaBadges = (msg: Message) => {
    const isUser = msg.role === 'user';
    const [hoveredMetric, setHoveredMetric] = createSignal<string | null>(null);

    const MetricPopover = (p: { title: string; label: string; value: string | number; icon?: any; description?: string }) => {
      const isVisible = () => hoveredMetric() === p.label;

      return (
        <div 
          class="relative flex items-center"
          onMouseEnter={() => setHoveredMetric(p.label)}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-background/85 border border-border/70 text-[11px] font-medium text-text-secondary hover:border-primary/20 hover:bg-primary/5 transition-all duration-200 cursor-default">
            {p.icon}
            <span class="opacity-60 font-semibold text-[10px]">{p.label}</span>
            <span class="font-semibold text-text-primary/90">{p.value}</span>
          </div>
          
          <div 
            class={`absolute top-full left-1/2 -translate-x-1/2 mt-2 w-48 pointer-events-none transition-all duration-300 ease-out z-[100] ${
              isVisible() ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
            }`}
          >
            <div class="bg-surface/98 backdrop-blur-xl border border-border shadow-[0_10px_30px_rgb(20,35,30,0.12)] rounded-2xl p-3 overflow-hidden">
              <div class="flex items-center gap-2 mb-1.5">
                <div class="p-1.5 rounded-lg bg-primary/10 text-primary">
                  {p.icon}
                </div>
                <div class="font-semibold text-[11px] text-text-primary tracking-tight">
                  {p.title}
                </div>
              </div>
              <div class="text-[10px] leading-relaxed text-text-secondary/90 font-medium">
                {p.description}
              </div>
              <div class="mt-2 pt-2 border-t border-border/30 flex justify-between items-center">
                <span class="text-[9px] text-text-secondary/60 font-semibold">{p.label}</span>
                <span class="text-[10px] font-bold text-primary">{p.value}</span>
              </div>
            </div>
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-[color:rgba(255,255,255,0.98)]"></div>
          </div>
        </div>
      );
    };

    return (
      <div class={`export-exclude mt-4 flex flex-wrap items-center gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-background/85 border border-border/70 text-[11px] font-medium text-text-secondary">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {formatTime(msg.timestamp)}
        </div>

        <Show when={!isUser}>
          <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-primary/6 border border-primary/12 text-[11px] font-semibold text-primary tracking-tight shadow-sm shadow-primary/5">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            {modelLabel(msg)}
          </div>

          <div class={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-semibold tracking-tight ${
            responseStatus(msg) === 'Failed' 
              ? 'bg-rose-50 border-rose-200 text-rose-700' 
              : responseStatus(msg) === 'Generating' 
                ? 'bg-amber-50 border-amber-200 text-amber-700' 
                : 'bg-emerald-50 border-emerald-200 text-emerald-700 shadow-sm shadow-emerald-500/5'
          }`}>
            <Show when={responseStatus(msg) === 'Generating'}>
              <div class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
            </Show>
            <Show when={responseStatus(msg) === 'Completed'}>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </Show>
            {responseStatus(msg)}
          </div>
          <Show when={visionBadge()}>
            <div class={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-semibold tracking-tight ${visionBadge()?.className}`}>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/></svg>
              {visionBadge()?.label}
            </div>
          </Show>

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
                value={`${msg.tps!.toFixed(1)} t/s`}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="m16 18 6-6-6-6"/><path d="M8 6l-6 6 6 6"/></svg>}
                description="Tokens Per Second: The average speed at which the model generated the text content."
              />
            </Show>

            <Show when={msg.finish_reason}>
              <MetricPopover 
                title="Finish Reason"
                label="Exit"
                value={msg.finish_reason!}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>}
                description="The reason why the model stopped generating (e.g., 'stop', 'length', 'tool_calls')."
              />
            </Show>
          </div>

          <Show when={msg.prompt_tokens || msg.completion_tokens}>
            <MetricPopover 
              title="Token Consumption"
              label="Usage"
              value={`${formatTokenCount(msg.prompt_tokens ?? 0)}i / ${formatTokenCount(msg.completion_tokens ?? 0)}o`}
              icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7"/><path d="M16 5V3"/><path d="M8 5V3"/><path d="M3 9h18"/><path d="M16 19h6"/><path d="M19 16v6"/></svg>}
              description="Detailed breakdown of input (prompt) tokens and output (generated) tokens used."
            />
          </Show>

          <Show when={msg.citations && msg.citations.length > 0}>
            <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-background/90 border border-border/80 text-[11px] font-semibold text-text-secondary tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/><path d="M14 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/></svg>
              {msg.citations?.length} Citations
            </div>
          </Show>

          <Show when={msg.tools && msg.tools.length > 0}>
            <div class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-background/90 border border-border/80 text-[11px] font-semibold text-text-secondary tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
              {msg.tools?.length} Tools
            </div>
          </Show>
        </Show>
      </div>
    );
  };

  return (
    <div class={`flex flex-col gap-2 ${props.msg.role === 'user' ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
      <div class="flex items-center gap-2 px-1">
        <div class={`w-5 h-5 rounded-full flex items-center justify-center border ${props.msg.role === 'user' ? 'border-text-secondary/20 bg-text-secondary/10 text-text-secondary/60' : 'border-primary/30 bg-primary/10 text-primary/70'}`}>
          <Show when={props.msg.role === 'user'}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5zm0 2c-3.333 0-10 1.667-10 5v3h20v-3c0-3.333-6.667-5-10-5z"/>
            </svg>
          </Show>
          <Show when={props.msg.role !== 'user'}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a8 8 0 00-8 8v2a8 8 0 0016 0v-2a8 8 0 00-8-8zm0 3a3 3 0 110 6 3 3 0 010-6zm-6 9.2a6 6 0 0112 0A6.98 6.98 0 0112 20a6.98 6.98 0 01-6-5.8z"/>
            </svg>
          </Show>
        </div>
        <span class={`text-[11px] font-semibold tracking-[0.02em] ${props.msg.role === 'user' ? 'text-text-secondary/80' : 'text-primary/85'}`}>
          {props.msg.role === 'user' ? 'You' : props.activeAgentName}
        </span>
      </div>
      <div
        id={`message-container-${props.index}`}
        tabIndex={props.msg.role === 'assistant' ? 0 : -1}
        onKeyDown={handleSpeechShortcut}
        aria-label={props.msg.role === 'assistant' ? 'Assistant message. Press R to read aloud or stop.' : undefined}
        class={`group relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
        props.msg.role === 'user' 
          ? 'max-w-[44rem] bg-surface text-text-primary px-5 py-4 border border-primary/14 rounded-[18px] rounded-br-[6px] overflow-hidden' 
          : 'w-full max-w-none bg-transparent text-text-primary border-0 px-0 py-2 shadow-none rounded-none'
      }`}
      >
        {props.msg.role === 'user' ? (
           <>
             <div class="absolute inset-0 pointer-events-none overflow-hidden">
               <div class="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-primary/10 blur-3xl"></div>
               <div class="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-primary/5 blur-3xl"></div>
               <div class="absolute inset-0 bg-[linear-gradient(135deg,rgba(16,185,129,0.10),transparent_55%,rgba(16,185,129,0.06))]"></div>
             </div>
             <Show when={props.msg.images && props.msg.images.length > 0}>
               <div class="flex flex-wrap gap-2 mb-2 relative z-10">
                 <For each={props.msg.images}>
                   {(img) => (
                     <img src={img} class="max-w-full h-auto max-h-64 rounded-lg border border-white/10" alt="User upload" />
                   )}
                 </For>
               </div>
             </Show>
             <div class="relative whitespace-pre-wrap leading-relaxed font-medium text-[15px] select-text">{props.msg.content}</div>
             <div class="mt-3 flex justify-end">
               <div class="flex items-center gap-1 p-1 rounded-2xl bg-surface/70 backdrop-blur-md ring-1 ring-border/70 shadow-sm transition-opacity opacity-100 lg:opacity-0 lg:group-hover:opacity-100">
                 <button
                   class={`p-1.5 rounded-xl transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                     props.copiedMessageIndex === props.index
                       ? 'text-emerald-500 bg-emerald-500/10'
                       : 'text-text-secondary/70 hover:text-primary hover:bg-primary/10'
                   }`}
                   title={props.copiedMessageIndex === props.index ? "Copied" : "Copy"}
                   aria-label="Copy message"
                   onClick={() => props.copyUserMessage(props.msg.content, props.index)}
                 >
                   <Show
                     when={props.copiedMessageIndex === props.index}
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
                   onClick={() => props.quoteUserMessage(props.msg.content)}
                 >
                   <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l5 5m-5-5l5-5" />
                   </svg>
                 </button>
               </div>
             </div>
           </>
        ) : (
          (() => {
            const res = adapted();
            const thought = res.thought;
            const content = res.content;
            const artifactUrls = unifiedArtifacts()
              .filter((artifact): artifact is BrowserScreenshotArtifact | DownloadArtifact => artifact.kind !== 'snapshot')
              .map((artifact) => artifact.url);
            const displayContent = stripDuplicateArtifactReferences(
              sanitizeAssistantDisplayContent(content),
              artifactUrls,
            );
            const isActuallyThinking = res.isThinking;
            const thoughtSource = res.source;
            const reasoningEnabled = props.msg.reasoning_enabled === true;
            const isThinking = reasoningEnabled && (isActuallyThinking || (props.isTyping && !displayContent));
            const showInitializing = () => props.isTyping && !thought && !content && !reasoningEnabled;

            return (
              <>
                <Show when={showInitializing()}>
                  <div class="flex flex-col gap-3 py-1">
                    <div class="flex items-center gap-3">
                      <div class="relative flex items-center justify-center w-5 h-5">
                        <div class="absolute inset-0 bg-primary/20 rounded-full animate-ping"></div>
                        <div class="absolute inset-0 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                        <div class="relative w-1.5 h-1.5 bg-primary rounded-full shadow-[0_0_8px_rgba(var(--primary-rgb),0.6)]"></div>
                      </div>
                      <span class="text-[11px] font-semibold tracking-[0.04em] text-primary/80 animate-pulse">
                        {getLoadingStatus().title}
                      </span>
                    </div>
                    <div class="flex items-center gap-1.5 pl-1">
                      <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-duration:1s]" style="animation-delay: 0ms"></div>
                      <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-duration:1s]" style="animation-delay: 200ms"></div>
                      <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-duration:1s]" style="animation-delay: 400ms"></div>
                    </div>
                    <div class={`text-[10px] font-medium italic transition-colors duration-500 ${waitSecs() > 15 ? 'text-amber-500/80' : 'text-text-secondary/40'}`}>
                      {getLoadingStatus().sub}
                    </div>

                    <Show when={props.msg.tools && props.msg.tools.length > 0}>
                      <div class="mt-2 flex flex-col gap-1.5 animate-in fade-in slide-in-from-bottom-1 duration-700 delay-300">
                        <div class="flex items-center gap-1.5">
                          <div class="w-1 h-1 rounded-full bg-primary/40"></div>
                          <span class="text-[10px] font-medium text-text-secondary/70">Capabilities Ready</span>
                        </div>
                        <div class="flex flex-wrap gap-1.5 pl-2">
                          <For each={props.msg.tools?.slice(0, 5)}>
                            {(tool) => (
                              <div class="px-2 py-0.5 rounded-full bg-primary/6 border border-primary/12 text-[10px] font-medium text-primary/80 flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                                {tool.replace('mcp__', '').replace('builtin:', '').split('__').pop()}
                              </div>
                            )}
                          </For>
                          <Show when={(props.msg.tools?.length || 0) > 5}>
                            <div class="px-2 py-0.5 rounded-full bg-background border border-border/70 text-[10px] font-medium text-text-secondary/70">
                              +{(props.msg.tools?.length || 0) - 5} more
                            </div>
                          </Show>
                        </div>
                      </div>
                    </Show>

                    <Show when={waitSecs() > 20}>
                      <div class="mt-1 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-[10px] text-amber-800 font-medium animate-in fade-in slide-in-from-top-1">
                        ⚠️ The model is taking longer than expected. This can happen with complex reasoning or high server load.
                      </div>
                    </Show>
                  </div>
                </Show>

                <Show when={reasoningEnabled && (thought || (props.isTyping && !displayContent))}>
                  <section class="mb-4 space-y-2">
                    <div class="flex items-center gap-2 px-1">
                      <div class="w-1 h-3 rounded-full bg-primary/40"></div>
                      <span class="text-[10px] font-bold uppercase tracking-wider text-text-secondary/40">LLM Thinking</span>
                    </div>
                  <div class="rounded-2xl border border-border/40 bg-background/40 overflow-hidden group/thought transition-all duration-500 hover:border-primary/30 hover:shadow-[0_0_20px_rgba(var(--primary-rgb),0.05)]">
                    <button 
                      onClick={() => props.toggleThought(props.index)}
                      class="w-full flex items-center justify-between px-5 py-4 hover:bg-primary/[0.03] transition-all group/btn relative overflow-hidden"
                    >
                      <Show when={isThinking}>
                        <div class="absolute inset-0 bg-gradient-to-r from-transparent via-primary/[0.05] to-transparent -translate-x-full animate-[shimmer_3s_infinite] pointer-events-none"></div>
                      </Show>
                      <Show when={props.isTyping}>
                        <div class="absolute bottom-0 left-0 h-[2px] bg-primary/20 w-full overflow-hidden">
                          <div class="h-full bg-primary/40 animate-[loading_2s_infinite_ease-in-out]"></div>
                        </div>
                      </Show>
                      
                      <div class="flex items-center gap-4 relative z-10">
                        <div class="relative flex items-center justify-center w-6 h-6">
                          <Show when={isThinking}>
                            <div class="absolute inset-[-4px] bg-primary/20 rounded-full animate-ping [animation-duration:2.5s]"></div>
                            <div class="absolute inset-[-2px] bg-primary/10 rounded-full animate-pulse [animation-duration:1.8s]"></div>
                            <div class="absolute inset-0 border-2 border-primary/20 rounded-full animate-spin-slow"></div>
                            <div class="absolute inset-1 border-2 border-t-primary border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin [animation-duration:0.8s]"></div>
                          </Show>
                          <div class={`relative w-2.5 h-2.5 rounded-full transition-all duration-1000 ${
                            isThinking 
                              ? 'bg-gradient-to-tr from-primary to-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.8)] scale-110' 
                              : 'bg-text-secondary/20'
                          }`}></div>
                        </div>
                        <div class="flex flex-col items-start -space-y-0.5">
                          <div class="flex items-center gap-1.5">
                            <span class={`text-[13px] font-black tracking-wide transition-colors duration-500 ${isThinking ? 'text-primary' : 'text-text-secondary'}`}>
                              {isThinking 
                                ? (isActuallyThinking ? 'Thinking & Analyzing' : getLoadingStatus().title) 
                                : 'Reasoning Chain'}
                            </span>
                            <Show when={thoughtSource === 'structured'}>
                              <div class="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20" title="Structured reasoning from model API">
                                <span class="text-[8px] font-black uppercase tracking-wider text-emerald-500/80">Structured</span>
                              </div>
                            </Show>
                          </div>
                          <Show when={isThinking}>
                            <span class="text-[9px] font-bold text-primary/40 tabular-nums">
                              Elapsed: {waitSecs()}s
                            </span>
                          </Show>
                          <Show when={!isThinking && props.msg.thought_duration !== undefined}>
                            <span class="text-[9px] font-bold text-text-secondary/40 tabular-nums">
                              Took: {props.msg.thought_duration?.toFixed(1)}s
                            </span>
                          </Show>
                        </div>
                      </div>
                      <div class="flex items-center gap-3 relative z-10">
                        <Show when={isThinking}>
                           <div class="px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20">
                             <span class="text-[9px] font-black uppercase tracking-[0.15em] text-primary animate-pulse-fast">Live Processing</span>
                           </div>
                        </Show>
                        <div class={`p-1.5 rounded-lg transition-all duration-300 ${props.expandedThoughts[props.index] ? 'bg-primary/10 text-primary' : 'bg-black/5 text-text-secondary/40'}`}>
                          <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 transition-transform duration-500 ${props.expandedThoughts[props.index] ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                          </svg>
                        </div>
                      </div>
                    </button>
                    
                    {/* 新增：在思考块内部显示详细状态描述 */}
                    <Show when={isThinking && !isActuallyThinking}>
                      <div class="px-5 pb-4 -mt-1 animate-in fade-in slide-in-from-top-1 duration-500">
                        <div class="flex flex-col gap-2 p-3 rounded-xl bg-primary/[0.02] border border-primary/5">
                          <div class="flex items-center gap-2">
                            <div class="flex gap-1">
                              <div class="w-1 h-1 bg-primary rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                              <div class="w-1 h-1 bg-primary rounded-full animate-bounce" style="animation-delay: 200ms"></div>
                              <div class="w-1 h-1 bg-primary rounded-full animate-bounce" style="animation-delay: 400ms"></div>
                            </div>
                            <span class="text-[10px] font-medium text-text-secondary/60 italic">
                              {getLoadingStatus().sub}
                            </span>
                          </div>
                          
                          <Show when={props.msg.tools && props.msg.tools.length > 0}>
                            <div class="flex flex-wrap gap-1.5 pt-1 border-t border-primary/5">
                              <For each={props.msg.tools?.slice(0, 3)}>
                                {(tool) => (
                                  <div class="px-1.5 py-0.5 rounded bg-primary/5 text-[8px] font-medium text-primary/40">
                                    {tool.replace('mcp__', '').replace('builtin:', '').split('__').pop()}
                                  </div>
                                )}
                              </For>
                            </div>
                          </Show>
                        </div>
                      </div>
                    </Show>

                    <div 
                      class={`transition-all duration-500 ease-in-out overflow-hidden ${
                        props.expandedThoughts[props.index] ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <div class="px-8 py-6 text-[13.5px] text-text-secondary/90 leading-relaxed overflow-y-auto max-h-[500px] border-t border-border/5 bg-gradient-to-b from-black/[0.02] to-transparent dark:from-white/[0.02]">
                        <div class="prose prose-sm dark:prose-invert max-w-none opacity-80">
                          {renderThought(thought)}
                        </div>
                        <Show when={isThinking}>
                          <div class="flex items-center gap-3 mt-6 p-3 rounded-xl bg-primary/[0.03] border border-primary/5 text-primary/70 italic text-xs animate-pulse">
                            <div class="relative flex w-4 h-4">
                              <div class="absolute inset-0 bg-primary/20 rounded-full animate-ping"></div>
                              <div class="absolute inset-1 bg-primary/40 rounded-full animate-pulse"></div>
                            </div>
                            Exploring knowledge base and synthesizing optimal response...
                          </div>
                        </Show>
                      </div>
                    </div>
                  </div>
                  </section>
                </Show>

                <Show when={props.msg.tool_calls && props.msg.tool_calls.length > 0}>
                  <div class="mb-4 space-y-2">
                    <div class="flex items-center gap-2 px-1 mb-1">
                      <div class="w-1 h-3 bg-primary/40 rounded-full"></div>
                      <span class="text-[10px] font-bold uppercase tracking-wider text-text-secondary/40">Tools Execution</span>
                    </div>
                    <For each={props.msg.tool_calls}>
                      {(toolCall) => <ToolCallItem toolCall={toolCall} />}
                    </For>
                  </div>
                </Show>

                <Show when={displayContent || unifiedArtifacts().length > 0 || (props.isTyping && !thought)}>
                  <Show when={visionFeedbackText()}>
                    <div class="mb-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 text-[13px]">
                      {visionFeedbackText()}
                    </div>
                  </Show>
                  <Show when={displayContent}>
                    <div 
                      innerHTML={renderMarkdown(displayContent, props.isTyping)} 
                      class="prose prose-slate max-w-none text-text-primary
                        prose-p:leading-relaxed prose-p:my-3 prose-p:text-[15px] prose-p:text-text-primary
                        prose-li:text-text-primary prose-ol:text-text-primary prose-ul:text-text-primary
                        prose-headings:text-text-primary prose-headings:font-black prose-headings:tracking-tight
                        prose-a:text-primary prose-a:font-bold hover:prose-a:text-primary-hover prose-a:no-underline border-b border-transparent hover:border-primary
                        prose-strong:text-text-primary prose-strong:font-bold
                        prose-code:text-primary prose-code:bg-primary/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-code:font-bold prose-code:break-words prose-code:break-all
                        prose-pre:p-0 prose-pre:bg-transparent
                        prose-ol:my-4 prose-ul:my-4 prose-li:my-1
                        prose-table:w-full prose-table:border-collapse prose-table:my-6 prose-table:table-fixed
                        prose-th:bg-primary/5 prose-th:text-primary prose-th:p-3 prose-th:text-left prose-th:text-xs prose-th:font-black prose-th:uppercase prose-th:tracking-wider prose-th:border prose-th:border-border/60 prose-th:break-words prose-th:break-all
                        prose-td:p-3 prose-td:text-sm prose-td:border prose-td:border-border/60 prose-td:text-text-secondary prose-td:break-words prose-td:break-all" 
                    />
                  </Show>
                  <Show when={unifiedArtifacts().length > 0}>
                    <div class={`${displayContent ? 'mt-4' : 'mt-0'} grid gap-3`}>
                      <For each={unifiedArtifacts()}>
                        {(artifact) => (
                          <figure class={artifactShellClass}>
                            <div class={artifactHeaderClass}>
                              <div class="min-w-0">
                                <div class={artifactMetaLabelClass}>
                                  {artifact.kind === 'screenshot'
                                    ? 'Browser Capture'
                                    : artifact.kind === 'snapshot'
                                      ? 'Browser Snapshot'
                                      : 'File Export'}
                                </div>
                                <Show when={artifact.kind === 'screenshot'}>
                                  <div class="mt-1 truncate text-[13px] font-semibold text-text-primary">
                                    {(artifact as BrowserScreenshotArtifact).alt}
                                  </div>
                                </Show>
                                <Show when={artifact.kind === 'download'}>
                                  <div class="mt-1 truncate text-[13px] font-semibold text-text-primary">
                                    {(artifact as DownloadArtifact).filename}
                                  </div>
                                </Show>
                                <Show when={artifact.kind === 'snapshot'}>
                                  <div class="mt-1 truncate text-[13px] font-semibold text-text-primary">
                                    {(artifact as BrowserSnapshotArtifact).pageTitle || 'Captured page summary'}
                                  </div>
                                </Show>
                              </div>
                              <Show when={artifact.kind === 'download'}>
                                <span class="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                                  {(artifact as DownloadArtifact).kindLabel}
                                </span>
                              </Show>
                            </div>

                            <Show when={artifact.sourceUrl}>
                              <div class="px-4 pb-3">
                                <div class={artifactMetaLabelClass}>
                                  {artifact.kind === 'screenshot' ? 'Captured From' : 'Source'}
                                </div>
                                <a
                                  href={artifact.sourceUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class={artifactMetaValueClass}
                                >
                                  {artifact.sourceUrl}
                                </a>
                              </div>
                            </Show>

                            <Show when={artifact.kind === 'screenshot'}>
                              <img
                                src={(artifact as BrowserScreenshotArtifact).url}
                                alt={(artifact as BrowserScreenshotArtifact).alt}
                                class="block w-full object-contain border-y border-slate-200/50 bg-[linear-gradient(180deg,rgba(248,250,252,0.95),rgba(241,245,249,0.95))]"
                                loading="lazy"
                              />
                            </Show>

                            <Show when={artifact.kind === 'download'}>
                              <Show
                                when={(artifact as DownloadArtifact).isImage}
                                fallback={
                                  <div class="flex items-start gap-3 px-4 pb-4">
                                    <div class="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-primary">
                                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M7 21h10a2 2 0 0 0 2-2V9.414a1 1 0 0 0-.293-.707l-5.414-5.414A1 1 0 0 0 12.586 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2z" />
                                      </svg>
                                    </div>
                                    <div class="min-w-0 flex-1">
                                      <div class="truncate text-[14px] font-semibold text-text-primary">{(artifact as DownloadArtifact).filename}</div>
                                      <div class="mt-1 text-[11px] font-medium uppercase tracking-[0.16em] text-text-secondary/60">
                                        {(artifact as DownloadArtifact).kindLabel}
                                      </div>
                                    </div>
                                  </div>
                                }
                              >
                                <img
                                  src={(artifact as DownloadArtifact).url}
                                  alt={(artifact as DownloadArtifact).filename}
                                  class="block w-full object-contain border-y border-slate-200/50 bg-[linear-gradient(180deg,rgba(248,250,252,0.95),rgba(241,245,249,0.95))]"
                                  loading="lazy"
                                />
                              </Show>
                            </Show>

                            <Show when={artifact.kind === 'snapshot'}>
                              <div class="space-y-3 px-4 pb-4">
                                {(() => {
                                  const snapshotArtifact = artifact as BrowserSnapshotArtifact;
                                  const structuredText = structureSnapshotVisibleText(
                                    snapshotArtifact.visibleText,
                                    snapshotArtifact.pageTitle,
                                  );
                                  const paragraphs = structuredText.paragraphs;

                                  return (
                                    <div class="space-y-3">
                                      <Show when={structuredText.headerLines.length > 0 || structuredText.scopeLine || structuredText.sortLine}>
                                        <div class="space-y-2">
                                          <div class={artifactMetaLabelClass}>Page Structure</div>
                                          <div class="flex flex-wrap gap-2">
                                            <For each={structuredText.headerLines}>
                                              {(line) => (
                                                <div class="rounded-full border border-slate-200 bg-white/80 px-3 py-1.5 text-[12px] font-medium text-text-primary">
                                                  {line}
                                                </div>
                                              )}
                                            </For>
                                            <Show when={structuredText.scopeLine}>
                                              <div class="rounded-full border border-primary/10 bg-primary/[0.04] px-3 py-1.5 text-[12px] font-medium text-primary">
                                                {structuredText.scopeLine}
                                              </div>
                                            </Show>
                                            <Show when={structuredText.sortLine}>
                                              <div class="rounded-full border border-slate-200 bg-slate-50/80 px-3 py-1.5 text-[12px] font-medium text-text-secondary">
                                                Sort: {structuredText.sortLine}
                                              </div>
                                            </Show>
                                          </div>
                                        </div>
                                      </Show>

                                      <Show when={structuredText.resultItems.length > 0}>
                                        <div class="space-y-2">
                                          <div class={artifactMetaLabelClass}>Visible Results</div>
                                          <div class="space-y-2">
                                            <For each={structuredText.resultItems}>
                                              {(item, index) => (
                                                <div class={`${index() === 0 ? 'bg-slate-50/80 border-slate-200/80' : 'bg-white/75 border-slate-200/65'} rounded-2xl border px-3 py-3`}>
                                                  <div class="flex items-start gap-3">
                                                    <div class="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/[0.08] text-[11px] font-semibold text-primary">
                                                      {index() + 1}
                                                    </div>
                                                    <div class="min-w-0">
                                                      <div class="text-[13px] font-semibold text-text-primary">
                                                        {getSnapshotItemTitle(item)}
                                                      </div>
                                                      <Show when={getSnapshotItemBody(item)}>
                                                        <div class="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-text-secondary">
                                                          {getSnapshotItemBody(item)}
                                                        </div>
                                                      </Show>
                                                    </div>
                                                  </div>
                                                </div>
                                              )}
                                            </For>
                                          </div>
                                        </div>
                                      </Show>

                                      <Show when={paragraphs.length > 0}>
                                        <div class="space-y-2">
                                          <div class={artifactMetaLabelClass}>Page Summary</div>
                                          <div class="space-y-2">
                                            <For each={paragraphs}>
                                              {(paragraph, index) => (
                                                <div class={`${index() === 0 ? 'bg-slate-50/75' : 'bg-white/65'} rounded-2xl px-3 py-3`}>
                                                  <div class="whitespace-pre-wrap text-[13px] leading-relaxed text-text-primary">
                                                    {paragraph}
                                                  </div>
                                                </div>
                                              )}
                                            </For>
                                          </div>
                                        </div>
                                      </Show>

                                      <Show when={!structuredText.resultItems.length && !paragraphs.length}>
                                        <div class="space-y-2">
                                          <div class={artifactMetaLabelClass}>Page Summary</div>
                                          <div class="rounded-2xl bg-slate-50/75 px-3 py-3 text-[13px] leading-relaxed text-text-secondary">
                                            No readable page summary was captured.
                                          </div>
                                        </div>
                                      </Show>
                                    </div>
                                  );
                                })()}
                                <div class="grid gap-2 lg:grid-cols-2">
                                  <Show when={(artifact as BrowserSnapshotArtifact).bindingSource}>
                                    <div class="rounded-2xl bg-slate-50/75 px-3 py-2">
                                      <div class={artifactMetaLabelClass}>Binding Source</div>
                                      <div class="mt-1 break-all text-[12px] text-text-primary">{(artifact as BrowserSnapshotArtifact).bindingSource}</div>
                                    </div>
                                  </Show>
                                  <Show when={(artifact as BrowserSnapshotArtifact).bindingUrl}>
                                    <div class="rounded-2xl bg-slate-50/75 px-3 py-2">
                                      <div class={artifactMetaLabelClass}>Binding URL</div>
                                      <div class="mt-1 break-all text-[12px] text-text-primary">{(artifact as BrowserSnapshotArtifact).bindingUrl}</div>
                                    </div>
                                  </Show>
                                </div>
                                <div class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50/75 px-3 py-2">
                                  <div class="text-[12px] text-text-secondary">Interactive elements</div>
                                  <div class="text-[12px] font-semibold text-text-primary">
                                    {(artifact as BrowserSnapshotArtifact).interactiveCount}
                                  </div>
                                </div>
                              </div>
                            </Show>

                            <figcaption class="flex items-center justify-between gap-3 px-4 py-3">
                              <span class="truncate text-[11px] font-medium text-slate-800">
                                {artifact.kind === 'screenshot'
                                  ? (artifact as BrowserScreenshotArtifact).alt
                                  : artifact.kind === 'download'
                                    ? (artifact as DownloadArtifact).filename
                                    : ((artifact as BrowserSnapshotArtifact).pageTitle || 'Snapshot details')}
                              </span>
                              <Show when={artifact.kind !== 'snapshot'}>
                                <a
                                  href={artifact.kind === 'screenshot' ? (artifact as BrowserScreenshotArtifact).url : (artifact as DownloadArtifact).url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="text-[11px] font-semibold text-slate-700 hover:text-slate-800 hover:underline"
                                >
                                  {artifact.kind === 'screenshot' ? 'Open image' : 'Open file'}
                                </a>
                              </Show>
                            </figcaption>
                          </figure>
                        )}
                      </For>
                    </div>
                  </Show>
                </Show>

                <Show when={isTruncated()}>
                  <div class="mt-4 flex justify-start">
                    <button
                      onClick={() => props.onContinue(props.msg)}
                      class="group flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white font-bold text-sm shadow-lg shadow-primary/20 hover:bg-primary/90 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-300"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                      </svg>
                      继续生成
                    </button>
                  </div>
                </Show>

                <Show when={(props.msg.citations?.length ?? 0) > 0}>
                  <details class="mt-5 -mx-2 rounded-2xl border border-border/50 bg-black/5 dark:bg-white/5 px-4 py-3">
                    <summary class="cursor-pointer text-xs font-black uppercase tracking-[0.2em] text-text-secondary/70">
                      Sources ({props.msg.citations?.length ?? 0})
                    </summary>
                    <div class="mt-3 space-y-2">
                      <For each={props.msg.citations || []}>
                        {(c) => (
                          <div class="rounded-xl border border-border/40 bg-surface/60 px-3 py-2">
                            <div class="text-xs font-mono text-text-secondary">
                              {(() => {
                                const path = typeof c?.path === 'string' ? c.path : '';
                                const startLine = typeof c?.start_line === 'number' ? c.start_line : null;
                                const endLine = typeof c?.end_line === 'number' ? c.end_line : null;
                                const startPage = typeof c?.start_page === 'number' ? c.start_page : null;
                                const endPage = typeof c?.end_page === 'number' ? c.end_page : null;
                                if (path && startLine !== null && endLine !== null) return `${path}#L${startLine}-L${endLine}`;
                                if (path && startPage !== null && endPage !== null) return `${path}#P${startPage}-P${endPage}`;
                                return path || 'Unknown source';
                              })()}
                            </div>
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
          })()
        )}
        
        <Show when={props.msg.finish_reason === 'length'}>
          <div class="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-[13px] flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Response truncated due to output length limit. Try asking for a shorter summary or continuing from where it left off.</span>
          </div>
        </Show>

        <Show when={props.isTyping}>
          <span class="inline-block w-2.5 h-5 ml-1 bg-primary/30 animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(16,185,129,0.3)]"></span>
        </Show>

        <Show when={props.msg.role === 'assistant' && !props.isTyping}>
          <div class="export-exclude flex items-center gap-1.5 mt-3 -ml-2">
            <button 
              class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
              title="Copy" 
              onClick={() => navigator.clipboard.writeText(props.msg.content)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
            </button>
            <SpeechControl messageId={speechMessageId()} content={props.msg.content} />
            <Show when={speechState() === 'speaking' || speechState() === 'paused'}>
              <div class="px-2 py-1 rounded-md border border-primary/20 bg-primary/5 text-[10px] font-semibold text-primary flex items-center gap-1.5">
                <span class={`w-1.5 h-1.5 rounded-full ${speechState() === 'speaking' ? 'bg-primary animate-pulse' : 'bg-primary/60'}`}></span>
                {speechState() === 'speaking' ? 'Speaking now' : 'Paused'}
              </div>
            </Show>
             <button 
               class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
               title="Download/Export"
               onClick={handleExportClick}
             >
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
              onClick={() => props.handleRegenerate(props.index)}
            >
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
               </svg>
            </button>
          </div>
        </Show>
        {renderMetaBadges(props.msg)}
      </div>
      <Show when={exportMenuPos()}>
        <MessageExportMenu 
          content={props.msg.content}
          messageId={`message-container-${props.index}`}
          position={exportMenuPos()!}
          onClose={() => setExportMenuPos(null)}
        />
      </Show>
    </div>
  );
}
