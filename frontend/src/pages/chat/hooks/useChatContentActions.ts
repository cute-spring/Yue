import { Accessor, Setter, createMemo } from 'solid-js';
import { Message, SkillSpec, WorkspaceNote } from '../../../types';
import { canSubmitChatRequest } from '../../../hooks/useChatState';
import { buildContinuationRequestOverrides } from '../../../utils/continuation';
import { buildVisibleSkillOptions } from '../utils/skillResolution';
import { handleChatCommand } from '../utils/chatCommands';
import { modelSupportsVision } from '../../../hooks/useLLMProviders';

type ToastLike = {
  success: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
};

type UseChatContentActionsArgs = {
  toast: ToastLike;
  speech: { stopCurrent: () => void };
  currentAgent: Accessor<any>;
  voiceInput: {
    isRecording: () => boolean;
    isProcessing: () => boolean;
    phase: () => string;
    stopRecording: () => void;
  };
  handleInsertVoiceInput: () => void;
  agents: Accessor<any[]>;
  selectedAgent: Accessor<string | null>;
  skills: Accessor<SkillSpec[]>;
  input: Accessor<string>;
  setInput: Setter<string>;
  messages: Accessor<Message[]>;
  setMessages: Setter<Message[]>;
  imageAttachments: Accessor<File[]>;
  isTyping: Accessor<boolean>;
  selectedModel: Accessor<string>;
  setShowLLMSelector: Setter<boolean>;
  submitText: (value: string, overrides?: Record<string, unknown>) => Promise<void> | void;
  originalHandleSubmit: (event: Event) => void;
  saveLastAssistantAsWorkspaceNote: () => Promise<WorkspaceNote | null>;
  saveLastAssistantAsResearchArtifact: () => Promise<void>;
  buildWorkspaceRequestOverrides: () => Record<string, unknown>;
  generateSummary: (chatId: string, force?: boolean) => Promise<string | null | undefined>;
  currentChatId: Accessor<string | null>;
  loadChat: (
    id: string,
    isMobile: boolean,
    setShowHistory: (value: boolean) => void,
    setSelectedAgent: (value: string | null) => void,
    setSelectedWorkspaceId?: (value: string | null) => void,
  ) => Promise<void>;
  setShowHistory: (value: boolean) => void;
  setSelectedAgent: (value: string | null) => void;
  selectedProvider: Accessor<string>;
  setSelectedProvider: Setter<string>;
  providers: Accessor<any[]>;
  setSelectedModel: Setter<string>;
  setImageAttachments: Setter<File[]>;
  providerStorageKey: string;
  modelStorageKey: string;
  loadProviders: (force?: boolean) => Promise<void>;
  setIsRefreshingModels: Setter<boolean>;
  isMobile: Accessor<boolean>;
};

export function useChatContentActions(args: UseChatContentActionsArgs) {
  const activeAgentName = () => {
    const agent = args.agents().find((entry) => entry.id === args.selectedAgent());
    return agent ? agent.name : 'AI Assistant';
  };

  const visibleSkillOptions = createMemo(() =>
    buildVisibleSkillOptions(args.skills(), args.currentAgent()),
  );

  const handleSubmit = (event: Event) => {
    event.preventDefault();
    args.speech.stopCurrent();

    if (args.voiceInput.isRecording() || args.voiceInput.isProcessing()) {
      args.voiceInput.stopRecording();
      return;
    }

    if (args.voiceInput.phase() === 'ready') {
      args.handleInsertVoiceInput();
      return;
    }

    if (args.isTyping()) {
      args.originalHandleSubmit(event);
      return;
    }

    const trimmedInput = args.input().trim();
    if (!canSubmitChatRequest(trimmedInput, args.imageAttachments().length)) return;

    if (
      handleChatCommand({
        trimmedInput,
        setMessages: args.setMessages,
        setInput: args.setInput,
        saveLastAssistantAsWorkspaceNote: args.saveLastAssistantAsWorkspaceNote,
        saveLastAssistantAsResearchArtifact: args.saveLastAssistantAsResearchArtifact,
        toast: args.toast,
      })
    ) {
      return;
    }

    if (!args.selectedModel()) {
      args.setShowLLMSelector(true);
      return;
    }

    void args.submitText(args.input(), args.buildWorkspaceRequestOverrides());
  };

  const handleContinue = (msg: Message) => {
    args.speech.stopCurrent();
    void args.submitText('继续', buildContinuationRequestOverrides(args.messages(), msg));
  };

  const handleGenerateSummary = async (chatId: string) => {
    args.speech.stopCurrent();
    const summary = await args.generateSummary(chatId, true);
    if (summary) {
      args.toast.success('Summary updated');
    } else {
      args.toast.info('No summary generated');
    }
    if (args.currentChatId() === chatId) {
      await args.loadChat(
        chatId,
        args.isMobile(),
        args.setShowHistory,
        args.setSelectedAgent,
      );
    }
  };

  const handleModelSelect = (provider: string, model: string) => {
    args.setSelectedProvider(provider);
    args.setSelectedModel(model);
    localStorage.setItem(args.providerStorageKey, provider);
    localStorage.setItem(args.modelStorageKey, model);

    const supportsVision = modelSupportsVision(args.providers(), provider, model);
    if (args.imageAttachments().length > 0 && !supportsVision) {
      const kept = args.imageAttachments().filter((file) => !file.type.startsWith('image/'));
      if (kept.length !== args.imageAttachments().length) {
        args.setImageAttachments(kept);
        args.toast.info('已自动移除图片附件，当前模型不支持视觉能力。', 3500);
      }
    }
  };

  const handleRefreshModels = async () => {
    args.setIsRefreshingModels(true);
    try {
      await args.loadProviders(true);
    } finally {
      args.setIsRefreshingModels(false);
    }
  };

  return {
    activeAgentName,
    visibleSkillOptions,
    handleSubmit,
    handleContinue,
    handleGenerateSummary,
    handleModelSelect,
    handleRefreshModels,
  };
}
