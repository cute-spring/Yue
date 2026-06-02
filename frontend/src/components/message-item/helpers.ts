import { Attachment, Message } from '../../types';
import { renderMarkdown } from '../../utils/markdown';

export type EditShortcutAction = 'none' | 'cancel' | 'submit';

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

export const shouldCollapseAssistantMessage = (args: {
  role: Message['role'];
  isTyping: boolean;
  isLatestAssistantMessage: boolean;
}): boolean => {
  if (args.role === 'user') return false;
  if (args.isTyping) return false;
  return !args.isLatestAssistantMessage;
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

export const getAttachmentDisplayName = (attachment: Attachment): string => {
  if (attachment.display_name && attachment.display_name.trim().length > 0) return attachment.display_name;
  if (attachment.url) {
    const path = attachment.url.split('?')[0];
    const tail = path.split('/').pop();
    if (tail && tail.trim().length > 0) return tail;
  }
  return 'attachment';
};

export const getAttachmentMimeType = (attachment: Attachment): string => {
  if (attachment.mime_type && attachment.mime_type.trim().length > 0) return attachment.mime_type;
  return 'application/octet-stream';
};

export const isImageAttachment = (attachment: Attachment): boolean =>
  getAttachmentMimeType(attachment).startsWith('image/');

export const getRenderableUserAttachments = (
  msg: Pick<Message, 'attachments' | 'images'>,
): Attachment[] => {
  const typed = Array.isArray(msg.attachments) ? msg.attachments.filter(Boolean) : [];
  const legacyImageUrls = Array.isArray(msg.images) ? msg.images : [];
  const uploadedImageCount = typed.filter(isImageAttachment).length;
  let consumedUploadedImageSlots = 0;
  const normalizedLegacy = legacyImageUrls
    .filter((url) => !!url)
    .filter((url) => {
      const normalized = typeof url === 'string' ? url.trim() : '';
      const isDataImageUrl = normalized.startsWith('data:image/');
      if (!isDataImageUrl) return true;
      if (consumedUploadedImageSlots < uploadedImageCount) {
        consumedUploadedImageSlots += 1;
        return false;
      }
      return true;
    })
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

export const getLoadingStatus = (waitSecs: number) => {
  if (waitSecs < 3) return { title: 'Initializing', sub: 'Agent is preparing response...' };
  if (waitSecs < 8) return { title: 'Analyzing', sub: 'Searching for the best approach...' };
  if (waitSecs < 15) return { title: 'Deep Thinking', sub: 'Processing complex request details...' };
  return { title: 'Still Thinking', sub: 'Taking longer than usual, thanks for your patience.' };
};

export const isAssistantMessageTruncated = (msg: Message, isTyping: boolean): boolean => {
  if (msg.finish_reason === 'length') return true;
  if (msg.role !== 'assistant' || isTyping) return false;

  const content = msg.content || '';
  const codeBlockCount = (content.match(/```/g) || []).length;
  if (codeBlockCount > 0 && codeBlockCount % 2 !== 0) return true;
  if (content.includes('<html') && !content.includes('</html>')) return true;
  return false;
};

export const formatTime = (value?: string) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit' }).format(date);
};

export const formatTokenCount = (n: number) => `${(n / 1000).toFixed(1)}k`;

export const getResponseStatus = (msg: Message, isTyping: boolean) => {
  if (msg.error || (msg.content && msg.content.startsWith('Error:'))) return 'Failed';
  if (msg.role === 'assistant' && isTyping) return 'Generating';
  return 'Completed';
};

export const getModelLabel = (msg: Message, selectedProvider: string, selectedModel: string) => {
  const provider = msg.provider || selectedProvider;
  const model = msg.model || selectedModel;
  if (provider && model) return `${provider}/${model}`;
  if (model) return model;
  return 'Unknown model';
};

export const renderThought = (thought: string | null, isTyping: boolean) => {
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
    processedThought = processedThought.replace(
      regex,
      `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-current/10 ${color} ${bg} font-bold text-[11px] mr-1"><span>${icon}</span><span>${tag}</span></span>`,
    );
  });

  return renderMarkdown(processedThought, isTyping);
};

export const assistantContentMarkdownClass = `prose prose-slate dark:prose-invert max-w-none
  prose-p:leading-relaxed prose-p:my-3 prose-p:text-[15px]
  prose-headings:text-text-primary prose-headings:font-black prose-headings:tracking-tight
  prose-a:text-primary prose-a:font-bold hover:prose-a:text-primary-hover prose-a:no-underline border-b border-transparent hover:border-primary
  prose-strong:text-text-primary prose-strong:font-bold
  prose-code:text-primary prose-code:bg-primary/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-code:font-bold prose-code:break-words prose-code:break-all
  prose-pre:bg-[#1E1E1E] prose-pre:text-slate-300 prose-pre:p-4 prose-pre:rounded-xl prose-pre:shadow-inner prose-pre:my-6 prose-pre:border prose-pre:border-slate-800
  prose-ol:my-4 prose-ul:my-4 prose-li:my-1
  prose-table:w-full prose-table:border-collapse prose-table:my-6 prose-table:table-fixed
  prose-th:bg-primary/5 prose-th:text-primary prose-th:p-3 prose-th:text-left prose-th:text-xs prose-th:font-black prose-th:uppercase prose-th:tracking-wider prose-th:border prose-th:border-border/60 prose-th:break-words prose-th:break-all
  prose-td:p-3 prose-td:text-sm prose-td:border prose-td:border-border/60 prose-td:text-text-secondary prose-td:break-words prose-td:break-all`;
