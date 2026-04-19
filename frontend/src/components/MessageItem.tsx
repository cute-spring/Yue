import { createSignal, For, Show, onCleanup, createEffect, createMemo } from 'solid-js';
import { Attachment, Message } from '../types';
import { renderMarkdown } from '../utils/markdown';
import { getAdaptedThought } from "../utils/thoughtParser";
import ToolCallItem from './ToolCallItem';
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
  handleEditQuestion: (index: number, newContent: string) => Promise<void>;
  onContinue: (msg: Message) => void;
  selectedProvider: string;
  selectedModel: string;
}

type EditShortcutAction = 'none' | 'cancel' | 'submit';

export const getNormalizedEditedQuestion = (value: string): string => value.trim();

export const getEditShortcutAction = (event: {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  shiftKey: boolean;
}): EditShortcutAction => {
  if (event.key === 'Escape') return 'cancel';
  if (event.key === 'Enter' && !event.shiftKey && (event.metaKey || event.ctrlKey)) return 'submit';
  return 'none';
};

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

const getAttachmentDisplayName = (attachment: Attachment): string => {
  if (attachment.display_name && attachment.display_name.trim().length > 0) return attachment.display_name;
  if (attachment.url) {
    const path = attachment.url.split('?')[0];
    const tail = path.split('/').pop();
    if (tail && tail.trim().length > 0) return tail;
  }
  return 'attachment';
};

const getAttachmentMimeType = (attachment: Attachment): string => {
  if (attachment.mime_type && attachment.mime_type.trim().length > 0) return attachment.mime_type;
  return 'application/octet-stream';
};

const isImageAttachment = (attachment: Attachment): boolean => getAttachmentMimeType(attachment).startsWith('image/');

export const getRenderableUserAttachments = (
  msg: Pick<Message, 'attachments' | 'images'>,
): Attachment[] => {
  const typed = Array.isArray(msg.attachments) ? msg.attachments.filter(Boolean) : [];
  const legacyImageUrls = Array.isArray(msg.images) ? msg.images : [];
  const normalizedLegacy = legacyImageUrls
    .filter((url) => !!url)
    .map((url) => ({
      kind: 'file',
      display_name: url.split('?')[0].split('/').pop() || 'legacy-image',
      url,
      mime_type: 'image/*',
      source: 'legacy_images',
      status: 'ready',
    } satisfies Attachment));

  const dedup = new Set<string>();
  const getAttachmentKeys = (attachment: Attachment): string[] => {
    const keys: string[] = [];
    const id = typeof attachment.id === 'string' ? attachment.id.trim() : '';
    if (id.length > 0) keys.push(`id:${id}`);
    const url = typeof attachment.url === 'string' ? attachment.url.trim() : '';
    if (url.length > 0) keys.push(`url:${url}`);
    return keys;
  };

  const renderable: Attachment[] = [];
  [...typed, ...normalizedLegacy].forEach((attachment) => {
    const keys = getAttachmentKeys(attachment);
    if (keys.some((key) => dedup.has(key))) return;
    keys.forEach((key) => dedup.add(key));
    renderable.push(attachment);
  });
  return renderable;
};

export default function MessageItem(props: MessageItemProps) {
  const speechController = useMaybeSpeechController();
  const [waitSecs, setWaitSecs] = createSignal(0);
  const [isEditing, setIsEditing] = createSignal(false);
  const [editContent, setEditContent] = createSignal('');
  const [isSavingEdit, setIsSavingEdit] = createSignal(false);
  const [editError, setEditError] = createSignal<string | null>(null);
  let timer: any;

  const [exportMenuPos, setExportMenuPos] = createSignal<{x: number, y: number} | null>(null);

  const handleExportClick = (e: MouseEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    setExportMenuPos({ x: rect.left, y: rect.bottom + 8 });
  };

  const closeEdit = () => {
    setIsEditing(false);
    setIsSavingEdit(false);
    setEditError(null);
  };

  const onSubmitEditedQuestion = async () => {
    const normalized = getNormalizedEditedQuestion(editContent());
    if (!normalized) {
      setEditError('Question cannot be empty');
      return;
    }

    setIsSavingEdit(true);
    setEditError(null);
    try {
      await props.handleEditQuestion(props.index, normalized);
      closeEdit();
    } catch (error) {
      setEditError(error instanceof Error ? error.message : 'Failed to update question');
    } finally {
      setIsSavingEdit(false);
    }
  };

  const onEditKeyDown = async (event: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => {
    const action = getEditShortcutAction(event);
    if (action === 'cancel') {
      event.preventDefault();
      closeEdit();
      return;
    }
    if (action === 'submit') {
      event.preventDefault();
      await onSubmitEditedQuestion();
    }
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
  const userAttachments = createMemo(() => getRenderableUserAttachments(props.msg));
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
        class="prose prose-sm dark:prose-invert max-w-none opacity-90 leading-relaxed font-sans"
        innerHTML={renderMarkdown(processedThought, props.isTyping)}
      />
    );
  };

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
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface/50 border border-border/40 text-[10px] font-medium text-text-secondary/80 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 cursor-default">
            {p.icon}
            <span class="opacity-50 font-bold uppercase tracking-tighter text-[9px]">{p.label}</span>
            <span class="font-semibold text-text-primary/90">{p.value}</span>
          </div>
          
          <div 
            class={`absolute top-full left-1/2 -translate-x-1/2 mt-2 w-48 pointer-events-none transition-all duration-300 ease-out z-[100] ${
              isVisible() ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
            }`}
          >
            <div class="bg-white/95 backdrop-blur-xl border border-border/50 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-xl p-3 overflow-hidden">
              <div class="flex items-center gap-2 mb-1.5">
                <div class="p-1.5 rounded-lg bg-primary/10 text-primary">
                  {p.icon}
                </div>
                <div class="font-bold text-[11px] text-text-primary tracking-tight">
                  {p.title}
                </div>
              </div>
              <div class="text-[10px] leading-relaxed text-text-secondary/90 font-medium">
                {p.description}
              </div>
              <div class="mt-2 pt-2 border-t border-border/30 flex justify-between items-center">
                <span class="text-[9px] text-text-secondary/50 font-bold uppercase">{p.label}</span>
                <span class="text-[10px] font-bold text-primary">{p.value}</span>
              </div>
            </div>
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-white/95"></div>
          </div>
        </div>
      );
    };

    return (
      <div class={`export-exclude mt-4 flex flex-wrap items-center gap-3 ${isUser ? 'justify-between' : 'justify-start'}`}>
        <Show when={isUser}>
          <div class="flex items-center gap-1.5 -ml-2">
            <button
              class={`p-1.5 rounded-lg transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                props.copiedMessageIndex === props.index
                  ? 'text-emerald-500 bg-emerald-500/10'
                  : 'text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5'
              }`}
              title={props.copiedMessageIndex === props.index ? "Copied" : "Copy"}
              aria-label="Copy message"
              onClick={() => props.copyUserMessage(props.msg.content, props.index)}
            >
              <Show
                when={props.copiedMessageIndex === props.index}
                fallback={
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                }
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
              </Show>
            </button>
            <button
              class="p-1.5 rounded-lg text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              title="Quote"
              aria-label="Quote message"
              onClick={() => props.quoteUserMessage(props.msg.content)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l5 5m-5-5l5-5" />
              </svg>
            </button>
            <button
              class="p-1.5 rounded-lg text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
              title="Edit"
              aria-label="Edit message"
              onClick={() => {
                setEditContent(props.msg.content);
                setEditError(null);
                setIsEditing(true);
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5h2m-7 14h12a2 2 0 002-2V7a2 2 0 00-2-2h-3m-4 0H8a2 2 0 00-2 2v3m0 4v3a2 2 0 002 2m8-7l-6 6-4 1 1-4 6-6m3-3l2 2" />
              </svg>
            </button>
          </div>
        </Show>
        <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-text-secondary/5 border border-border/40 text-[10px] font-medium text-text-secondary/70">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {formatTime(msg.timestamp)}
        </div>

        <Show when={!isUser}>
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/5 border border-primary/10 text-[10px] font-bold text-primary/80 uppercase tracking-tight shadow-sm shadow-primary/5">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            {modelLabel(msg)}
          </div>

          <div class={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold uppercase tracking-tight ${
            responseStatus(msg) === 'Failed' 
              ? 'bg-rose-500/5 border-rose-500/20 text-rose-500' 
              : responseStatus(msg) === 'Generating' 
                ? 'bg-amber-500/5 border-amber-500/20 text-amber-500' 
                : 'bg-primary/5 border-primary/20 text-primary shadow-sm shadow-primary/5'
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
            <div class={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold uppercase tracking-tight ${visionBadge()?.className}`}>
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
        <span class={`text-[10px] font-black uppercase tracking-[0.24em] ${props.msg.role === 'user' ? 'text-text-secondary/50' : 'text-primary/70'}`}>
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
          ? 'bg-surface text-text-primary px-6 py-4 shadow-sm border border-border/40 rounded-[26px] rounded-br-none max-w-[85%] lg:max-w-[75%]' 
          : 'bg-surface text-text-primary border border-border/50 px-6 py-5 shadow-sm rounded-[24px] rounded-bl-none max-w-[85%] lg:max-w-[75%]'
      }`}
      >
        {props.msg.role === 'user' ? (
           <>
             <Show when={!isEditing()}>
               <Show when={userAttachments().length > 0}>
                 <div class="flex flex-wrap gap-2 mb-2 relative z-10">
                   <For each={userAttachments()}>
                     {(attachment) => (
                       <Show
                         when={isImageAttachment(attachment) && !!attachment.url}
                         fallback={
                           <a
                             href={attachment.url || '#'}
                             target="_blank"
                             rel="noreferrer"
                             class="flex min-w-[220px] max-w-[320px] items-center gap-3 rounded-lg border border-white/10 bg-black/5 px-3 py-2 text-left hover:border-primary/30"
                           >
                             <div class="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary text-[11px] font-bold uppercase">
                               {getAttachmentDisplayName(attachment).split('.').pop() || 'file'}
                             </div>
                             <div class="min-w-0">
                               <div class="truncate text-[13px] font-semibold text-text-primary">{getAttachmentDisplayName(attachment)}</div>
                               <div class="truncate text-[11px] text-text-secondary/70">{getAttachmentMimeType(attachment)}</div>
                             </div>
                           </a>
                         }
                       >
                         <img src={attachment.url!} class="max-w-full h-auto max-h-64 rounded-lg border border-white/10 shadow-sm" alt="User upload" />
                       </Show>
                     )}
                   </For>
                 </div>
               </Show>
               <div class="relative whitespace-pre-wrap leading-relaxed font-medium text-[15px] select-text">{props.msg.content}</div>
               <div class="mt-4 flex justify-between items-center border-t border-primary/10 pt-3">
                 <div class="export-exclude flex items-center gap-1.5 -ml-2">
                   <button
                     class={`p-1.5 rounded-lg transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                       props.copiedMessageIndex === props.index
                         ? 'text-emerald-500 bg-emerald-500/10'
                         : 'text-text-secondary/50 hover:text-primary hover:bg-primary/10'
                     }`}
                     title={props.copiedMessageIndex === props.index ? "Copied" : "Copy"}
                     aria-label="Copy message"
                     onClick={() => props.copyUserMessage(props.msg.content, props.index)}
                   >
                     <Show
                       when={props.copiedMessageIndex === props.index}
                       fallback={
                         <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                         </svg>
                       }
                     >
                       <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                       </svg>
                     </Show>
                   </button>
                   <button
                     class="p-1.5 rounded-lg text-text-secondary/50 hover:text-primary hover:bg-primary/10 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                     title="Quote"
                     aria-label="Quote message"
                     onClick={() => props.quoteUserMessage(props.msg.content)}
                   >
                     <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l5 5m-5-5l5-5" />
                     </svg>
                   </button>
                   <button
                     class="p-1.5 rounded-lg text-text-secondary/50 hover:text-primary hover:bg-primary/10 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                     title="Edit"
                     aria-label="Edit message"
                     onClick={() => {
                       setEditContent(props.msg.content);
                       setEditError(null);
                       setIsEditing(true);
                     }}
                   >
                     <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5h2m-7 14h12a2 2 0 002-2V7a2 2 0 00-2-2h-3m-4 0H8a2 2 0 00-2 2v3m0 4v3a2 2 0 002 2m8-7l-6 6-4 1 1-4 6-6m3-3l2 2" />
                     </svg>
                   </button>
                 </div>
                 <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/5 border border-primary/10 text-[10px] font-bold text-text-secondary/60 uppercase tracking-tight">
                   <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                   {formatTime(props.msg.timestamp)}
                 </div>
               </div>
             </Show>
             <Show when={isEditing()}>
               <div class="flex flex-col gap-2 mt-2 w-full min-w-[250px] relative z-20">
                 <textarea
                   class="w-full bg-background/80 backdrop-blur-md border border-primary/30 rounded-xl p-3 text-[15px] text-text-primary focus:outline-none focus:border-primary/60 resize-y min-h-[100px]"
                   value={editContent()}
                   disabled={isSavingEdit()}
                   onInput={(e) => setEditContent(e.currentTarget.value)}
                   onKeyDown={(e) => {
                     void onEditKeyDown(e);
                   }}
                 />
                 <Show when={editError()}>
                   <div class="text-xs text-rose-500">{editError()}</div>
                 </Show>
                 <div class="flex justify-end gap-2 mt-1">
                   <button
                     disabled={isSavingEdit()}
                     onClick={closeEdit}
                     class="px-3 py-1.5 rounded-lg text-xs font-medium text-text-secondary hover:bg-text-secondary/10 transition-colors disabled:opacity-60"
                   >
                     Cancel
                   </button>
                   <button
                     disabled={isSavingEdit()}
                     onClick={() => {
                       void onSubmitEditedQuestion();
                     }}
                     class="px-3 py-1.5 rounded-lg text-xs font-bold bg-primary text-white hover:bg-primary-hover transition-colors shadow-sm disabled:opacity-60"
                   >
                     Save & Submit
                   </button>
                 </div>
               </div>
             </Show>
           </>
        ) : (
          (() => {
            const res = adapted();
            const thought = res.thought;
            const content = res.content;
            const isActuallyThinking = res.isThinking;
            const thoughtSource = res.source;
            const reasoningEnabled = props.msg.reasoning_enabled === true;
            const isThinking = reasoningEnabled && (isActuallyThinking || (props.isTyping && !content));
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
                      <span class="text-[11px] font-black uppercase tracking-[0.2em] text-primary/70 animate-pulse">
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
                          <span class="text-[9px] font-bold uppercase tracking-wider text-text-secondary/30">Capabilities Ready</span>
                        </div>
                        <div class="flex flex-wrap gap-1.5 pl-2">
                          <For each={props.msg.tools?.slice(0, 5)}>
                            {(tool) => (
                              <div class="px-1.5 py-0.5 rounded bg-primary/5 border border-primary/10 text-[8px] font-medium text-primary/60 flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                                {tool.replace('mcp__', '').replace('builtin:', '').split('__').pop()}
                              </div>
                            )}
                          </For>
                          <Show when={(props.msg.tools?.length || 0) > 5}>
                            <div class="px-1.5 py-0.5 rounded bg-text-secondary/5 border border-border/20 text-[8px] font-medium text-text-secondary/40">
                              +{(props.msg.tools?.length || 0) - 5} more
                            </div>
                          </Show>
                        </div>
                      </div>
                    </Show>

                    <Show when={waitSecs() > 20}>
                      <div class="mt-1 px-3 py-1.5 rounded-lg bg-amber-500/5 border border-amber-500/10 text-[9px] text-amber-600/70 font-bold animate-in fade-in slide-in-from-top-1">
                        ⚠️ The model is taking longer than expected. This can happen with complex reasoning or high server load.
                      </div>
                    </Show>
                  </div>
                </Show>

                <Show when={reasoningEnabled && (thought || (props.isTyping && !content))}>
                  <div class="mb-4 rounded-xl border border-border/40 bg-background/40 overflow-hidden group/thought transition-all duration-500 hover:border-primary/30">
                    <button 
                      onClick={() => props.toggleThought(props.index)}
                      class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-primary/[0.03] transition-all group/btn relative overflow-hidden"
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
                              ? 'bg-gradient-to-tr from-primary to-primary shadow-[0_0_15px_rgba(16,185,129,0.8)] scale-110' 
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
                              <div class="px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20" title="Structured reasoning from model API">
                                <span class="text-[8px] font-black uppercase tracking-wider text-primary">Structured</span>
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

                <Show when={content || (props.isTyping && !thought)}>
                  <Show when={visionFeedbackText()}>
                    <div class="mb-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-700 text-[13px]">
                      {visionFeedbackText()}
                    </div>
                  </Show>
                  <div 
                    innerHTML={renderMarkdown(content, props.isTyping)} 
                    class="prose prose-slate dark:prose-invert max-w-none 
                      prose-p:leading-relaxed prose-p:my-3 prose-p:text-[15px]
                      prose-headings:text-text-primary prose-headings:font-black prose-headings:tracking-tight
                      prose-a:text-primary prose-a:font-bold hover:prose-a:text-primary-hover prose-a:no-underline border-b border-transparent hover:border-primary
                      prose-strong:text-text-primary prose-strong:font-bold
                      prose-code:text-primary prose-code:bg-primary/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-code:font-bold prose-code:break-words prose-code:break-all
                      prose-pre:bg-[#1E1E1E] prose-pre:text-slate-300 prose-pre:p-4 prose-pre:rounded-xl prose-pre:shadow-inner prose-pre:my-6 prose-pre:border prose-pre:border-slate-800
                      prose-ol:my-4 prose-ul:my-4 prose-li:my-1
                      prose-table:w-full prose-table:border-collapse prose-table:my-6 prose-table:table-fixed
                      prose-th:bg-primary/5 prose-th:text-primary prose-th:p-3 prose-th:text-left prose-th:text-xs prose-th:font-black prose-th:uppercase prose-th:tracking-wider prose-th:border prose-th:border-border/60 prose-th:break-words prose-th:break-all
                      prose-td:p-3 prose-td:text-sm prose-td:border prose-td:border-border/60 prose-td:text-text-secondary prose-td:break-words prose-td:break-all" 
                  />
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
          <div class="export-exclude flex flex-wrap items-center justify-between gap-3 mt-4 pt-3 border-t border-border/10">
            <div class="flex items-center gap-1.5 -ml-1.5">
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
                  {speechState() === 'speaking' ? 'Speaking' : 'Paused'}
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
            
            <div class="flex items-center gap-2">
              {renderMetaBadges(props.msg)}
            </div>
          </div>
        </Show>
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
