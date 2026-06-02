import { Show } from 'solid-js';

import LLMSelector from '../LLMSelector';
import type { Provider } from '../../types';
import {
  getTooManyFilesWarningMessage,
  getOversizedWarningMessage,
  getUploadButtonClass,
  mergeAttachments,
  type UploadPolicy,
} from './attachmentUtils';

type ChatInputActionBarProps = {
  advancedMode?: boolean;
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
  isDeepThinking: boolean;
  setIsDeepThinking: (val: boolean) => void;
  imageAttachments: File[];
  setImageAttachments: (files: File[]) => void;
  onImageClick: () => void;
  imageInputRef: (el: HTMLInputElement) => void;
  uploadAccept: string;
  uploadPolicy: UploadPolicy;
  maxAttachmentCount: number;
  maxAttachmentSizeBytes: number;
  toast: {
    warning: (message: string, duration?: number) => void;
  };
  voiceInputEnabled: boolean;
  voiceInputSupported: boolean;
  voiceInputProvider: 'browser' | 'azure';
  voiceInputPreferredProvider: 'browser' | 'azure';
  voiceInputPhase: 'idle' | 'recording' | 'finalizing' | 'ready' | 'error';
  voiceInputIsRecording: boolean;
  voiceInputIsProcessing: boolean;
  voiceInputFallbackMessage: string | null;
  onToggleVoiceInput: () => void;
  isTyping: boolean;
  canSubmit: boolean;
  onSubmit: (e: Event) => void;
};

const getVoiceInputProviderLabel = (provider: 'browser' | 'azure'): string => {
  return provider === 'azure' ? 'Azure Speech' : 'Browser dictation';
};

const getVoiceInputButtonClass = (
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

const buildVoiceInputLabel = (props: ChatInputActionBarProps): string => {
  if (!props.voiceInputEnabled) return 'Voice input disabled in settings';
  if (!props.voiceInputSupported) return 'Voice input unavailable in this browser';
  if (props.voiceInputPhase === 'ready') return `Start new voice input (${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)})`;
  if (props.voiceInputIsRecording) return `Stop voice input (${getVoiceInputProviderLabel(props.voiceInputProvider)})`;
  if (props.voiceInputIsProcessing) return `Finishing voice input (${getVoiceInputProviderLabel(props.voiceInputProvider)})`;
  return `Start voice input (${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)})`;
};

const buildVoiceInputTooltip = (props: ChatInputActionBarProps): string => {
  if (!props.voiceInputEnabled) return 'Enable browser dictation in Settings';
  if (!props.voiceInputSupported) return 'Browser voice input unavailable';
  if (props.voiceInputFallbackMessage) return `${getVoiceInputProviderLabel(props.voiceInputProvider)} active`;
  if (props.voiceInputPhase === 'ready') return `Voice draft ready from ${getVoiceInputProviderLabel(props.voiceInputProvider)}`;
  if (props.voiceInputIsRecording) return `Listening with ${getVoiceInputProviderLabel(props.voiceInputProvider)}... pause to finish or tap to stop`;
  if (props.voiceInputIsProcessing) return `Processing speech with ${getVoiceInputProviderLabel(props.voiceInputProvider)}...`;
  return `Voice input via ${getVoiceInputProviderLabel(props.voiceInputPreferredProvider)}`;
};

export default function ChatInputActionBar(props: ChatInputActionBarProps) {
  const voiceInputLabel = () => buildVoiceInputLabel(props);
  const voiceInputTooltip = () => buildVoiceInputTooltip(props);

  return (
    <div class="absolute bottom-3 left-4 right-4 flex items-center justify-between">
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

      <div class="flex items-center gap-3">
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
            <input
              ref={props.imageInputRef}
              type="file"
              accept={props.uploadAccept}
              multiple
              class="hidden"
              onChange={e => {
                const files = Array.from(e.currentTarget.files || []);
                const merged = mergeAttachments(
                  props.imageAttachments,
                  files,
                  props.maxAttachmentCount,
                  props.maxAttachmentSizeBytes,
                  props.uploadPolicy,
                );
                if (merged.overflowCount > 0) {
                  props.toast.warning(getTooManyFilesWarningMessage(props.maxAttachmentCount));
                }
                if (merged.oversizedCount > 0) {
                  props.toast.warning(getOversizedWarningMessage(props.maxAttachmentSizeBytes));
                }
                if (merged.unsupportedCount > 0) {
                  props.toast.warning('部分文件类型不支持，已忽略');
                }
                props.setImageAttachments(merged.files);
                e.currentTarget.value = '';
              }}
            />
            <button
              type="button"
              class={getUploadButtonClass(props.imageAttachments.length)}
              aria-label="Upload files"
              onClick={props.onImageClick}
            >
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
          disabled={!props.isTyping && (!props.canSubmit || !props.selectedModel)}
          class={`
            flex items-center justify-center p-3 rounded-2xl transition-all duration-500 shadow-lg
            ${props.isTyping
              ? 'bg-rose-500 text-white hover:bg-rose-600 hover:shadow-rose-500/30 active:scale-95'
              : (props.canSubmit && props.selectedModel)
                ? 'bg-primary text-white hover:bg-primary-hover hover:shadow-primary/30 hover:scale-[1.02] active:scale-95'
                : 'bg-border/50 text-text-secondary cursor-not-allowed opacity-50'}
          `}
          title={props.isTyping ? "Stop Generation" : "Send Message"}
        >
          <Show
            when={props.isTyping}
            fallback={
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
              </svg>
            }
          >
            <div class="relative flex items-center justify-center">
              <div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <div class="absolute w-2 h-2 bg-white rounded-sm"></div>
            </div>
          </Show>
        </button>
      </div>
    </div>
  );
}
