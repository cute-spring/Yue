import { For, Show, createEffect, createSignal, onCleanup, onMount } from 'solid-js';
import { Agent, Provider, SkillMode, VisibleSkillChip } from '../types';
import AgentSelector from './AgentSelector';
import AttachmentPreviewStrip from './chat-input/AttachmentPreviewStrip';
import ChatInputActionBar from './chat-input/ChatInputActionBar';
import VoiceDraftCard from './chat-input/VoiceDraftCard';
import {
  DEFAULT_UPLOAD_POLICY,
  extractClipboardFiles,
  getAcceptAttributeFromPolicy,
  getAttachmentCompositionHint,
  getOversizedWarningMessage,
  getTooManyFilesWarningMessage,
  getVisionCapabilityHint,
  isImageFile,
  mergeAttachments,
  removeAttachmentAt,
  resolveUploadPolicy,
  type UploadPolicy,
  type UploadPolicyPayload,
} from './chat-input/attachmentUtils';
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

  const canSubmit = () => canSubmitFromInput(props.input, imageAttachmentCount());
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

            <ChatInputActionBar
              advancedMode={props.advancedMode}
              showLLMSelector={props.showLLMSelector}
              setShowLLMSelector={props.setShowLLMSelector}
              selectedModel={props.selectedModel}
              onSelectModel={props.onSelectModel}
              selectedProvider={props.selectedProvider}
              providers={props.providers}
              showAllModels={props.showAllModels}
              setShowAllModels={props.setShowAllModels}
              isRefreshingModels={props.isRefreshingModels}
              onRefreshModels={props.onRefreshModels}
              isDeepThinking={props.isDeepThinking}
              setIsDeepThinking={props.setIsDeepThinking}
              imageAttachments={props.imageAttachments}
              setImageAttachments={props.setImageAttachments}
              onImageClick={props.onImageClick}
              imageInputRef={props.imageInputRef}
              uploadAccept={uploadAccept()}
              uploadPolicy={uploadPolicy()}
              maxAttachmentCount={maxAttachmentCount()}
              maxAttachmentSizeBytes={maxAttachmentSizeBytes()}
              toast={toast}
              voiceInputEnabled={props.voiceInputEnabled}
              voiceInputSupported={props.voiceInputSupported}
              voiceInputProvider={props.voiceInputProvider}
              voiceInputPreferredProvider={props.voiceInputPreferredProvider}
              voiceInputPhase={props.voiceInputPhase}
              voiceInputIsRecording={props.voiceInputIsRecording}
              voiceInputIsProcessing={props.voiceInputIsProcessing}
              voiceInputFallbackMessage={props.voiceInputFallbackMessage}
              onToggleVoiceInput={props.onToggleVoiceInput}
              isTyping={props.isTyping}
              canSubmit={canSubmit()}
              onSubmit={props.onSubmit}
            />
          </div>
        </form>

        <AttachmentPreviewStrip
          files={props.imageAttachments}
          previewUrls={previewUrls}
          attachmentCompositionHint={attachmentCompositionHint}
          visionCapabilityHint={visionCapabilityHint}
          formatSize={formatSize}
          setFiles={props.setImageAttachments}
        />
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
export {
  DEFAULT_UPLOAD_POLICY,
  extractClipboardFiles,
  getAcceptAttributeFromPolicy,
  getAttachmentCompositionHint,
  getOversizedWarningMessage,
  getTooManyFilesWarningMessage,
  getUploadButtonClass,
  getVisionCapabilityHint,
  isImageFile,
  mergeAttachments,
  removeAttachmentAt,
  resolveUploadPolicy,
  splitAttachmentsByType,
} from './chat-input/attachmentUtils';
