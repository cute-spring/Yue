import { For, Show, createEffect, createSignal, onCleanup, onMount } from 'solid-js';
import { Agent, Provider, SkillMode, VisibleSkillChip } from '../types';
import LLMSelector from './LLMSelector';
import AgentSelector from './AgentSelector';
import VoiceDraftCard from './chat-input/VoiceDraftCard';
import { useToast } from '../context/ToastContext';
import { modelSupportsVision } from '../hooks/useLLMProviders';

interface ChatInputProps {
  // Agent Selector State
  showAgentSelector: boolean;
  filteredAgents: Agent[];
  selectedIndex: number;
  selectAgent: (agent: Agent) => void;
  
  // Input State
  input: string;
  onInput: (e: any) => void;
  onKeyDown: (e: any) => void;
  onSubmit: (e: Event) => void;
  isTyping: boolean;
  activeAgentName: string;
  textareaRef: (el: HTMLTextAreaElement) => void;
  inputReadOnly?: boolean;
  composerKey: number;
  
  // LLM Selector Props
  showLLMSelector: boolean;
  setShowLLMSelector: (show: boolean) => void;
  selectedModel: string;
  onSelectModel: (provider: string, model: string) => void;
  selectedProvider: string;
  providers: Provider[];
  showAllModels: boolean;
  setShowAllModels: (show: boolean) => void;
  isRefreshingModels: boolean;
  onRefreshModels: () => Promise<void>;

  // Deep Thinking
  isDeepThinking: boolean;
  setIsDeepThinking: (val: boolean) => void;

  // Tools
  imageAttachments: File[];
  setImageAttachments: (files: File[]) => void;
  onImageClick: () => void;
  imageInputRef: (el: HTMLInputElement) => void;

  // Skills
  visibleSkills: VisibleSkillChip[];
  requestedSkill: string | null;
  onSelectSkill: (skillId: string | null) => void;
  skillMode?: SkillMode;

  // Voice Input
  voiceInputEnabled: boolean;
  voiceInputSupported: boolean;
  voiceInputProvider: 'browser' | 'azure';
  voiceInputPreferredProvider: 'browser' | 'azure';
  voiceInputPhase: 'idle' | 'recording' | 'finalizing' | 'ready' | 'error';
  voiceInputIsRecording: boolean;
  voiceInputIsProcessing: boolean;
  voiceInputHasDraft: boolean;
  voiceInputPreviewText: string;
  voiceInputInterimTranscript: string;
  voiceInputError: string | null;
  voiceInputFallbackMessage: string | null;
  onToggleVoiceInput: () => void;
  onCancelVoiceInput: () => void;
  onInsertVoiceInput: () => void;
  onSendVoiceInput: () => void;

  // Advanced Mode
  advancedMode?: boolean;
}

export const canSubmitFromInput = (inputText: string, imageCount: number): boolean => {
  return inputText.trim().length > 0 || imageCount > 0;
};

export const MAX_ATTACHMENT_COUNT = 10;
export const MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024;
const DEFAULT_SUPPORTED_ATTACHMENT_MIME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
  'text/csv',
  'image/png',
  'image/jpeg',
  'image/gif',
  'image/webp',
];
const DEFAULT_SUPPORTED_ATTACHMENT_EXTENSIONS = [
  '.pdf',
  '.xlsx',
  '.xls',
  '.csv',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
];

export type UploadPolicy = {
  maxFiles: number;
  maxFileSizeBytes: number;
  allowedMimeTypes: string[];
  allowedExtensions: string[];
};

type UploadPolicyPayload = {
  max_files?: number;
  max_file_size_bytes?: number;
  allowed_mime_types?: string[];
  allowed_extensions?: string[];
};

export const DEFAULT_UPLOAD_POLICY: UploadPolicy = {
  maxFiles: MAX_ATTACHMENT_COUNT,
  maxFileSizeBytes: MAX_ATTACHMENT_SIZE_BYTES,
  allowedMimeTypes: [...DEFAULT_SUPPORTED_ATTACHMENT_MIME_TYPES],
  allowedExtensions: [...DEFAULT_SUPPORTED_ATTACHMENT_EXTENSIONS],
};

const getFileExtension = (name: string): string => {
  const dot = name.lastIndexOf('.');
  if (dot < 0) return '';
  return name.slice(dot).toLowerCase();
};

export const isImageFile = (file: Pick<File, 'type'>): boolean => file.type.startsWith('image/');

const normalizeAllowedList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === 'string')
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
};

const uniqueOrdered = (items: string[]): string[] => {
  const dedup = new Set<string>();
  items.forEach((item) => dedup.add(item));
  return Array.from(dedup.values());
};

export const resolveUploadPolicy = (payload?: UploadPolicyPayload | null): UploadPolicy => {
  const maxFiles = typeof payload?.max_files === 'number' && payload.max_files > 0
    ? payload.max_files
    : DEFAULT_UPLOAD_POLICY.maxFiles;
  const maxFileSizeBytes = typeof payload?.max_file_size_bytes === 'number' && payload.max_file_size_bytes > 0
    ? payload.max_file_size_bytes
    : DEFAULT_UPLOAD_POLICY.maxFileSizeBytes;
  const allowedMimeTypes = normalizeAllowedList(payload?.allowed_mime_types);
  const allowedExtensions = normalizeAllowedList(payload?.allowed_extensions);
  return {
    maxFiles,
    maxFileSizeBytes,
    allowedMimeTypes: allowedMimeTypes.length > 0 ? uniqueOrdered(allowedMimeTypes) : [...DEFAULT_UPLOAD_POLICY.allowedMimeTypes],
    allowedExtensions: allowedExtensions.length > 0 ? uniqueOrdered(allowedExtensions) : [...DEFAULT_UPLOAD_POLICY.allowedExtensions],
  };
};

const createSupportSets = (policy: UploadPolicy): { mimeTypes: Set<string>; extensions: Set<string> } => ({
  mimeTypes: new Set(policy.allowedMimeTypes.map((item) => item.toLowerCase())),
  extensions: new Set(policy.allowedExtensions.map((item) => item.toLowerCase())),
});

const formatLimitMb = (bytes: number): string => {
  const value = bytes / 1024 / 1024;
  return Number.isInteger(value) ? `${value}MB` : `${value.toFixed(2)}MB`;
};

export const getTooManyFilesWarningMessage = (maxFiles: number): string => `最多选择 ${maxFiles} 个附件`;
export const getOversizedWarningMessage = (maxFileSizeBytes: number): string =>
  `部分文件超过 ${formatLimitMb(maxFileSizeBytes)} 大小限制，已忽略`;

export const getAcceptAttributeFromPolicy = (policy: UploadPolicy): string => {
  const extensions = policy.allowedExtensions.map((item) => item.toLowerCase());
  const mimeTypes = policy.allowedMimeTypes.map((item) => item.toLowerCase());
  return [...extensions, ...mimeTypes].join(',');
};

export const isSupportedAttachment = (
  file: Pick<File, 'name' | 'type'>,
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): boolean => {
  const sets = createSupportSets(policy);
  const mime = (file.type || '').toLowerCase();
  const extension = getFileExtension(file.name || '');
  if (mime.startsWith('image/')) return true;
  return sets.mimeTypes.has(mime) || sets.extensions.has(extension);
};

export const filterSupportedAttachments = (
  files: File[],
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): { accepted: File[]; rejectedCount: number } => {
  const accepted = files.filter((file) => isSupportedAttachment(file, policy));
  return { accepted, rejectedCount: files.length - accepted.length };
};

export const mergeAttachments = (
  existing: File[],
  incoming: File[],
  maxCount: number,
  maxSizeBytes: number,
  policy: UploadPolicy = DEFAULT_UPLOAD_POLICY,
): { files: File[]; oversizedCount: number; overflowCount: number; unsupportedCount: number } => {
  const { accepted, rejectedCount } = filterSupportedAttachments(incoming, policy);
  const validIncoming = accepted.filter((file) => file.size <= maxSizeBytes);
  const oversizedCount = accepted.length - validIncoming.length;
  const merged = [...existing, ...validIncoming];
  const files = merged.slice(0, maxCount);
  const overflowCount = Math.max(0, merged.length - maxCount);
  return { files, oversizedCount, overflowCount, unsupportedCount: rejectedCount };
};

export const getUploadButtonClass = (attachmentCount: number): string => {
  if (attachmentCount > 0) {
    return 'relative p-2.5 bg-primary/20 text-primary border border-primary/30 rounded-2xl transition-all active:scale-90 shadow-sm';
  }
  return 'relative p-2.5 text-slate-500 hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90';
};

export const removeAttachmentAt = (files: File[], index: number): File[] => {
  return files.filter((_, i) => i !== index);
};

type ClipboardFileLike = {
  kind: string;
  type: string;
  getAsFile: () => File | null;
};

type ClipboardDataLike = {
  files?: ArrayLike<File>;
  items?: ArrayLike<ClipboardFileLike>;
};

export const extractClipboardFiles = (clipboardData: ClipboardDataLike | null | undefined): File[] => {
  if (!clipboardData) return [];

  const fromFiles = Array.from(clipboardData.files || []).filter((file) => isSupportedAttachment(file));
  const fromItems = Array.from(clipboardData.items || [])
    .filter((item) => item.kind === 'file')
    .map((item) => item.getAsFile())
    .filter((file): file is File => file instanceof File)
    .filter((file) => isSupportedAttachment(file));
  const dedup = new Map<string, File>();
  [...fromFiles, ...fromItems].forEach((file) => {
    const key = `${file.name}::${file.type}::${file.size}`;
    dedup.set(key, file);
  });
  return Array.from(dedup.values());
};

export const splitAttachmentsByType = (files: File[]): { imageFiles: File[]; nonImageFiles: File[] } => {
  const imageFiles = files.filter(isImageFile);
  const nonImageFiles = files.filter((file) => !isImageFile(file));
  return { imageFiles, nonImageFiles };
};

export const getVisionCapabilityHint = (
  hasSelectedModel: boolean,
  supportsVision: boolean,
  imageCount: number,
): string => {
  if (!hasSelectedModel || imageCount === 0 || supportsVision) return '';
  return '当前模型不支持图片理解能力，本次图片不会被分析；PDF/表格附件不受这条提示直接约束。';
};

export const getAttachmentCompositionHint = (imageCount: number, documentCount: number): string => {
  const totalCount = imageCount + documentCount;
  if (totalCount === 0) return '';

  const parts: string[] = [];
  if (imageCount > 0) {
    parts.push(`${imageCount} 张图片`);
  }
  if (documentCount > 0) {
    parts.push(`${documentCount} 个文档`);
  }
  return `已选择 ${totalCount} 个附件：${parts.join('，')}`;
};

export const getModelCapabilityBadge = (hasSelectedModel: boolean, supportsVision: boolean): string => {
  if (!hasSelectedModel) return '';
  return supportsVision ? 'Vision' : 'Text Only';
};

export const getVoiceInputButtonClass = (
  enabled: boolean,
  supported: boolean,
  isRecording: boolean,
  isProcessing: boolean,
): string => {
  if (!enabled || !supported) {
    return 'p-2.5 text-slate-300 bg-slate-100 rounded-2xl cursor-not-allowed';
  }
  if (isRecording) {
    return 'p-2.5 text-white bg-rose-500 hover:bg-rose-600 rounded-2xl transition-all active:scale-90 animate-pulse shadow-sm shadow-rose-500/30';
  }
  if (isProcessing) {
    return 'p-2.5 text-white bg-sky-500 hover:bg-sky-600 rounded-2xl transition-all active:scale-90 animate-pulse shadow-sm shadow-sky-500/30';
  }
  return 'p-2.5 text-slate-500 hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90';
};

export const getVoiceInputProviderLabel = (provider: 'browser' | 'azure'): string => {
  return provider === 'azure' ? 'Azure Speech' : 'Browser dictation';
};

export default function ChatInput(props: ChatInputProps) {
  const toast = useToast();
  const canSubmit = () => canSubmitFromInput(props.input, props.imageAttachments.length);
  const inputLocked = () => !!props.inputReadOnly;
  const formatSize = (size: number) => `${(size / 1024 / 1024).toFixed(2)}MB`;
  const [uploadPolicy, setUploadPolicy] = createSignal<UploadPolicy>(DEFAULT_UPLOAD_POLICY);
  const uploadAccept = () => getAcceptAttributeFromPolicy(uploadPolicy());
  const maxAttachmentCount = () => uploadPolicy().maxFiles;
  const maxAttachmentSizeBytes = () => uploadPolicy().maxFileSizeBytes;
  const supportsVision = () => modelSupportsVision(props.providers, props.selectedProvider, props.selectedModel);
  const [previewUrls, setPreviewUrls] = createSignal<string[]>([]);
  let trackedPreviewUrls: string[] = [];
  createEffect(() => {
    props.imageAttachments.length;
    const previous = trackedPreviewUrls;
    const next = props.imageAttachments.map(file => URL.createObjectURL(file));
    trackedPreviewUrls = next;
    setPreviewUrls(next);
    previous.forEach(url => URL.revokeObjectURL(url));
  });
  onCleanup(() => {
    trackedPreviewUrls.forEach(url => URL.revokeObjectURL(url));
  });
  const imageAttachmentCount = () => props.imageAttachments.filter(isImageFile).length;
  const documentAttachmentCount = () => props.imageAttachments.length - imageAttachmentCount();
  const visionCapabilityHint = () => getVisionCapabilityHint(!!props.selectedModel, supportsVision(), imageAttachmentCount());
  const attachmentCompositionHint = () => getAttachmentCompositionHint(imageAttachmentCount(), documentAttachmentCount());
  const modelCapabilityBadge = () => getModelCapabilityBadge(!!props.selectedModel, supportsVision());
  const voiceInputLabel = () => {
    if (!props.voiceInputEnabled) return 'Voice input disabled in settings';
    if (!props.voiceInputSupported) return 'Voice input unavailable in this browser';
    if (props.voiceInputPhase === 'ready') return `Start new voice input (${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)})`;
    if (props.voiceInputIsRecording) return `Stop voice input (${getVoiceInputProviderLabel(props.voiceInputProvider)})`;
    if (props.voiceInputIsProcessing) return `Finishing voice input (${getVoiceInputProviderLabel(props.voiceInputProvider)})`;
    return `Start voice input (${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)})`;
  };
  const voiceInputTooltip = () => {
    if (!props.voiceInputEnabled) return 'Enable browser dictation in Settings';
    if (!props.voiceInputSupported) return 'Browser voice input unavailable';
    if (props.voiceInputFallbackMessage) return `${getVoiceInputProviderLabel(props.voiceInputProvider)} active`;
    if (props.voiceInputPhase === 'ready') return `Voice draft ready from ${getVoiceInputProviderLabel(props.voiceInputProvider)}`;
    if (props.voiceInputIsRecording) return `Listening with ${getVoiceInputProviderLabel(props.voiceInputProvider)}... pause to finish or tap to stop`;
    if (props.voiceInputIsProcessing) return `Processing speech with ${getVoiceInputProviderLabel(props.voiceInputProvider)}...`;
    return `Voice input via ${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)}`;
  };
  const handlePaste = (e: ClipboardEvent & { currentTarget: HTMLTextAreaElement }) => {
    if (inputLocked()) return;
    const pastedFiles = extractClipboardFiles(e.clipboardData);
    if (pastedFiles.length === 0) return;

    e.preventDefault();
    const policy = uploadPolicy();
    const merged = mergeAttachments(
      props.imageAttachments,
      pastedFiles,
      maxAttachmentCount(),
      maxAttachmentSizeBytes(),
      policy,
    );
    if (merged.overflowCount > 0) {
      toast.warning(getTooManyFilesWarningMessage(maxAttachmentCount()));
    }
    if (merged.oversizedCount > 0) {
      toast.warning(getOversizedWarningMessage(maxAttachmentSizeBytes()));
    }
    if (merged.unsupportedCount > 0) {
      toast.warning('部分文件类型不支持，已忽略');
    }
    props.setImageAttachments(merged.files);
    toast.success('已粘贴附件，可直接发送');
  };

  onMount(() => {
    void (async () => {
      try {
        const response = await fetch('/api/files/policy');
        if (!response.ok) return;
        const payload = (await response.json()) as UploadPolicyPayload;
        setUploadPolicy(resolveUploadPolicy(payload));
      } catch {
        setUploadPolicy(DEFAULT_UPLOAD_POLICY);
      }
    })();
  });

  return (
    <div class="px-4 pb-6 lg:px-8 bg-transparent">
      <div class="max-w-6xl mx-auto relative">
        <AgentSelector 
          show={props.showAgentSelector}
          agents={props.filteredAgents}
          selectedIndex={props.selectedIndex}
          onSelect={props.selectAgent}
        />

        <Show when={props.skillMode === 'manual' && props.visibleSkills.length > 0}>
          <div
            class="flex items-center gap-2 mb-3 overflow-x-auto pb-2 scrollbar-hide no-scrollbar"
            data-testid="skill-chip-list"
            role="group"
            aria-label="Manual skill selection"
          >
            <For each={props.visibleSkills}>
              {(skill) => (
                <button
                  data-testid="skill-chip"
                  data-skill-id={skill.id}
                  type="button"
                  aria-pressed={props.requestedSkill === skill.id}
                  aria-label={skill.version ? `Select skill ${skill.name} ${skill.version}` : `Select skill ${skill.name}`}
                  title={skill.version ? `${skill.name}:${skill.version}` : skill.name}
                  onClick={() => {
                    if (props.requestedSkill === skill.id) {
                      props.onSelectSkill(null);
                    } else {
                      props.onSelectSkill(skill.id);
                    }
                  }}
                  class={`
                    px-3 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap border
                    ${props.requestedSkill === skill.id
                      ? 'bg-violet-600 border-violet-600 text-white shadow-md shadow-violet-500/20 scale-105'
                      : 'bg-surface border-border text-text-secondary hover:border-violet-400/50 hover:text-violet-600 hover:bg-violet-50'}
                  `}
                >
                  {skill.name}{skill.version ? `:${skill.version}` : ''}
                </button>
              )}
            </For>
          </div>
        </Show>

        <form onSubmit={props.onSubmit} class="relative">
          <div class={`
            relative bg-surface/80 backdrop-blur-xl border-2 rounded-[28px] transition-all duration-500 p-1.5 shadow-2xl
            ${props.isTyping ? 'border-primary/40 ring-8 ring-primary/5 shadow-primary/10' : 'border-border focus-within:border-primary/40 focus-within:ring-8 focus-within:ring-primary/5'}
          `}>
            <Show when={props.composerKey} keyed>
              {(composerKey) => (
                <textarea
                  data-composer-key={composerKey}
                  ref={props.textareaRef}
                  value={props.input}
                  onInput={props.onInput}
                  onPaste={handlePaste}
                  onKeyDown={props.onKeyDown}
                  readOnly={inputLocked()}
                  placeholder={`You are chatting with ${props.activeAgentName} now`}
                  class={`w-full bg-transparent px-6 pt-3.5 pb-14 focus:outline-none resize-none min-h-[72px] max-h-[400px] overflow-y-auto text-text-primary leading-relaxed text-lg font-medium placeholder:text-text-secondary/30 ${inputLocked() ? 'cursor-default opacity-90' : ''}`}
                  rows={1}
                />
              )}
            </Show>
            
            {/* Unified Action Bar */}
            <div class="absolute bottom-3 left-4 right-4 flex items-center justify-between">
              {/* Left Side: Configuration */}
              <div class="flex items-center gap-2">
                <Show when={props.advancedMode}>
                  <LLMSelector 
                    show={props.showLLMSelector}
                    setShow={props.setShowLLMSelector}
                    selectedModel={props.selectedModel}
                    onSelectModel={props.onSelectModel}
                    selectedProvider={props.selectedProvider}
                    providers={props.providers}
                    showAllModels={props.showAllModels}
                    setShowAllModels={props.setShowAllModels}
                    isRefreshingModels={props.isRefreshingModels}
                    onRefreshModels={props.onRefreshModels}
                  />
                </Show>

                {/* Deep Thinking Toggle */}
                <button
                  type="button"
                  onClick={() => props.setIsDeepThinking(!props.isDeepThinking)}
                  class={`flex items-center gap-2 px-3 py-2 rounded-2xl transition-all active:scale-95 border shadow-sm ${
                    props.isDeepThinking 
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
              <div class="flex items-center gap-3">
                {/* Tools Group */}
                  <div class="flex items-center gap-1.5">
                    <div class="relative group/tooltip">
                    <button
                      type="button"
                      class="p-2.5 text-slate-500 hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90"
                      aria-label="Attach or paste files"
                      onClick={props.onImageClick}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                      </svg>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">上传附件或直接粘贴</span>
                      <span class="block text-[11px] text-white/50 mt-1">支持图片、PDF、Excel、CSV，`Ctrl+V` 即可</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                  <div class="relative group/tooltip">
                    <input ref={props.imageInputRef} type="file" accept={uploadAccept()} multiple class="hidden" 
                      onChange={e => {
                        const files = Array.from(e.currentTarget.files || []);
                        const policy = uploadPolicy();
                        const merged = mergeAttachments(
                          props.imageAttachments,
                          files,
                          maxAttachmentCount(),
                          maxAttachmentSizeBytes(),
                          policy,
                        );
                        if (merged.overflowCount > 0) {
                          toast.warning(getTooManyFilesWarningMessage(maxAttachmentCount()));
                        }
                        if (merged.oversizedCount > 0) {
                          toast.warning(getOversizedWarningMessage(maxAttachmentSizeBytes()));
                        }
                        if (merged.unsupportedCount > 0) {
                          toast.warning('部分文件类型不支持，已忽略');
                        }
                        props.setImageAttachments(merged.files);
                        e.currentTarget.value = '';
                      }} />
                    <button type="button" class={getUploadButtonClass(props.imageAttachments.length)} aria-label="Upload files"
                      onClick={props.onImageClick}>
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke-width="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" stroke-width="2" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 15l-5-5L5 21" />
                      </svg>
                      <Show when={props.imageAttachments.length > 0}>
                        <span class="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] text-[10px] font-bold bg-primary text-white rounded-full px-1 border-2 border-surface shadow-sm">{props.imageAttachments.length}</span>
                      </Show>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">上传附件</span>
                      <span class="block text-[11px] text-white/50 mt-1">图片、PDF、Excel、CSV，支持 `Ctrl+V` 粘贴</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                  <div class="relative group/tooltip">
                    <button
                      type="button"
                      class={getVoiceInputButtonClass(
                        props.voiceInputEnabled,
                        props.voiceInputSupported,
                        props.voiceInputIsRecording,
                        props.voiceInputIsProcessing,
                      )}
                      aria-label={voiceInputLabel()}
                      aria-pressed={props.voiceInputIsRecording || props.voiceInputIsProcessing}
                      disabled={!props.voiceInputEnabled || !props.voiceInputSupported}
                      onClick={() => props.onToggleVoiceInput()}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[200px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">{voiceInputTooltip()}</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                </div>

                <button 
                  type="submit"
                  onClick={(e) => {
                    if (props.isTyping) {
                      e.preventDefault();
                      props.onSubmit(e);
                    }
                  }}
                  disabled={!props.isTyping && (!canSubmit() || !props.selectedModel)}
                  class={`
                    flex items-center justify-center p-3 rounded-2xl transition-all duration-500 shadow-lg
                    ${props.isTyping 
                      ? 'bg-rose-500 text-white hover:bg-rose-600 hover:shadow-rose-500/30 active:scale-95' 
                      : (canSubmit() && props.selectedModel)
                        ? 'bg-primary text-white hover:bg-primary-hover hover:shadow-primary/30 hover:scale-[1.02] active:scale-95' 
                        : 'bg-border/50 text-text-secondary cursor-not-allowed opacity-50'}
                  `}
                  title={props.isTyping ? "Stop Generation" : "Send Message"}
                >
                  <Show when={props.isTyping} fallback={
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                    </svg>
                  }>
                    <div class="relative flex items-center justify-center">
                      <div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <div class="absolute w-2 h-2 bg-white rounded-sm"></div>
                    </div>
                  </Show>
                </button>
              </div>
            </div>
          </div>
        </form>

        <Show when={props.imageAttachments.length > 0}>
          <div class="mt-2 px-2">
            <Show when={attachmentCompositionHint()}>
              <div class="mb-2 px-1 text-[12px] font-medium text-text-secondary">
                {attachmentCompositionHint()}
              </div>
            </Show>
            <div class="flex items-center gap-2 overflow-x-auto">
            <For each={props.imageAttachments}>
              {(file: File, index: () => number) => (
                <div class="flex items-center gap-2 px-2 py-1.5 rounded-xl border border-border bg-surface text-xs min-w-[200px]">
                  <Show
                    when={isImageFile(file)}
                    fallback={
                      <div class="w-10 h-10 rounded-lg border border-border/60 bg-background/50 shrink-0 flex items-center justify-center text-[10px] font-bold text-text-secondary uppercase">
                        {getFileExtension(file.name).replace('.', '') || 'file'}
                      </div>
                    }
                  >
                    <img src={previewUrls()[index()]} alt={file.name} class="w-10 h-10 rounded-lg object-cover border border-border/60 bg-background/50 shrink-0" />
                  </Show>
                  <div class="min-w-0 flex-1">
                    <div class="max-w-[150px] truncate font-semibold text-text-primary">{file.name}</div>
                    <div class="text-text-secondary">{formatSize(file.size)}</div>
                  </div>
                  <button
                    type="button"
                    class="text-text-secondary hover:text-rose-500"
                    onClick={() => props.setImageAttachments(removeAttachmentAt(props.imageAttachments, index()))}
                  >
                    ×
                  </button>
                </div>
              )}
            </For>
            <button
              type="button"
              class="px-3 py-1.5 rounded-xl border border-border text-xs text-text-secondary hover:text-rose-500"
              onClick={() => props.setImageAttachments([])}
            >
              Clear
            </button>
            </div>
          </div>
        </Show>
        <Show when={modelCapabilityBadge()}>
          <div class="mt-2 px-2">
            <div class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
              supportsVision()
                ? 'border-emerald-300/50 bg-emerald-500/10 text-emerald-700'
                : 'border-slate-300/70 bg-slate-100/90 text-slate-600'
            }`}>
              {modelCapabilityBadge()}
            </div>
          </div>
        </Show>
        <Show when={visionCapabilityHint()}>
          <div class="mt-2 px-3 py-2 rounded-xl border border-amber-400/30 bg-amber-500/10 text-[12px] text-amber-700">
            {visionCapabilityHint()}
          </div>
        </Show>
        <VoiceDraftCard
          visible={props.voiceInputPhase !== 'idle' || !!props.voiceInputFallbackMessage}
          providerLabel={getVoiceInputProviderLabel(props.voiceInputProvider)}
          phase={props.voiceInputPhase}
          isRecording={props.voiceInputIsRecording}
          isProcessing={props.voiceInputIsProcessing}
          error={props.voiceInputError}
          fallbackMessage={props.voiceInputFallbackMessage}
          previewText={props.voiceInputPreviewText}
          onInsert={props.onInsertVoiceInput}
          onSend={props.onSendVoiceInput}
          onCancel={props.onCancelVoiceInput}
        />

        <Show when={!props.selectedModel}>
          <div class="mt-3 flex items-center justify-center">
            <div class="px-3 py-1.5 rounded-full bg-surface border border-border text-[11px] text-text-secondary font-semibold">
              Select a model to start
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}

export const mergeImageAttachments = mergeAttachments;
export const removeImageAttachmentAt = removeAttachmentAt;
export const extractClipboardImageFiles = extractClipboardFiles;
