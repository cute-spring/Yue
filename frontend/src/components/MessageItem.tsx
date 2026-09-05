import { createSignal, Show, onCleanup, createEffect, createMemo } from 'solid-js';
import { Message, StructuredChartArtifact, WorkspaceMemoryCandidate, WorkspaceNote } from '../types';
import { getAdaptedThought } from "../utils/thoughtParser";
import MessageExportMenu from './MessageExportMenu';
import SpeechControl from './SpeechControl';
import MessageAssistantBody from './message-item/MessageAssistantBody';
import MessageAssistantFooter from './message-item/MessageAssistantFooter';
import MessageUserContent from './message-item/MessageUserContent';
import { getSpeechMessageId } from '../utils/speech';
import { useMaybeSpeechController } from '../context/SpeechControllerContext';
export {
  getEditShortcutAction,
  getNormalizedEditedQuestion,
  getRenderableUserAttachments,
  getVisionBadge,
  getVisionFeedbackText,
  shouldCollapseAssistantMessage,
} from './message-item/helpers';
export {
  formatCitationSourceLabel,
  getWorkspaceCitationWarning,
  getWorkspaceGroundingModeLabel,
  getWorkspaceGroundingSummary,
  getWorkspaceSourceModeLabel,
  getWorkspaceToolingWarning,
} from './message-item/evidence';
import {
  formatTime,
  getEditShortcutAction,
  getLoadingStatus,
  getModelLabel,
  getNormalizedEditedQuestion,
  getRenderableUserAttachments,
  getVisionBadge,
  getVisionFeedbackText,
  getWorkspaceCaptureSuggestion,
  isAssistantMessageTruncated,
  shouldCollapseAssistantMessage,
} from './message-item/helpers';

interface MessageItemProps {
  msg: Message;
  displayContent?: string;
  index: number;
  isLatestAssistantMessage: boolean;
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
  onSaveChartArtifact?: (msg: Message, artifact: StructuredChartArtifact) => Promise<void> | void;
  selectedProvider: string;
  selectedModel: string;
  hasSelectedWorkspace?: boolean;
  alreadySavedAsWorkspaceNote?: boolean;
  hasPendingWorkspaceMemoryCandidate?: boolean;
  captureSuggestionsEnabled?: boolean;
  memorySuggestionsEnabled?: boolean;
  onSaveWorkspaceNote?: () => Promise<WorkspaceNote | null>;
  onSuggestWorkspaceMemoryCandidate?: () => Promise<WorkspaceMemoryCandidate | null>;
  onTrackWorkspaceCaptureTelemetry?: (payload: {
    event_type: string;
    source?: string;
    workspace_id?: string | null;
    assistant_message_id?: number | string | null;
    assistant_turn_id?: string | null;
    run_id?: string | null;
    note_id?: string | null;
    candidate_id?: string | null;
    accepted?: boolean | null;
    metadata?: Record<string, any>;
  }) => Promise<void> | void;
}

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
  const displayedMsg = createMemo(() => ({
    ...props.msg,
    content: props.displayContent ?? props.msg.content,
  }));
  const adapted = createMemo(() => getAdaptedThought(displayedMsg(), props.isTyping));

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

  const visionBadge = () => getVisionBadge(props.msg);
  const visionFeedbackText = () => getVisionFeedbackText(props.msg);
  const userAttachments = createMemo(() => getRenderableUserAttachments(props.msg));
  const loadingStatus = () => getLoadingStatus(waitSecs());
  const modelLabel = () => getModelLabel(props.msg, props.selectedProvider, props.selectedModel);
  const isTruncated = () => isAssistantMessageTruncated(props.msg, props.isTyping);
  const speechMessageId = () => getSpeechMessageId(props.msg, props.index);
  const speechState = () => speechController?.getMessageState(speechMessageId()) || 'idle';
  const workspaceCaptureSuggestion = createMemo(() => {
    const streamed = props.msg.workspace_capture_suggestion;
    const baseSuggestion =
      streamed ||
      getWorkspaceCaptureSuggestion(props.msg, {
        hasSelectedWorkspace: props.hasSelectedWorkspace === true,
        isLatestAssistantMessage: props.isLatestAssistantMessage,
        isTyping: props.isTyping,
        alreadySavedAsNote: props.alreadySavedAsWorkspaceNote === true,
        hasPendingMemoryCandidate: props.hasPendingWorkspaceMemoryCandidate === true,
      });
    if (!baseSuggestion) return null;
    const adjusted = {
      ...baseSuggestion,
      show_note_action:
        baseSuggestion.show_note_action &&
        props.captureSuggestionsEnabled !== false &&
        props.hasSelectedWorkspace === true &&
        props.alreadySavedAsWorkspaceNote !== true,
      show_memory_action:
        baseSuggestion.show_memory_action &&
        props.memorySuggestionsEnabled !== false &&
        props.hasSelectedWorkspace === true &&
        props.hasPendingWorkspaceMemoryCandidate !== true,
    };
    if (!adjusted.show_note_action && !adjusted.show_memory_action) return null;
    return adjusted;
  });
  const userMessageContainerClass = () =>
    [
      'bg-surface text-text-primary px-6 py-4 shadow-sm border border-border/40 rounded-[26px] rounded-br-none',
      isEditing() ? 'w-full max-w-[92%] lg:max-w-[64rem]' : 'max-w-[90%] lg:max-w-[85%]',
    ].join(' ');

  const [isManuallyExpanded, setIsManuallyExpanded] = createSignal(false);
  const [isManuallyCollapsed, setIsManuallyCollapsed] = createSignal(false);

  const isCollapsed = createMemo(() => {
    if (props.msg.role === 'user') return false;

    // User manual overrides
    if (isManuallyExpanded()) return false;
    if (isManuallyCollapsed()) return true;

    // Keep the newest assistant response open by default so the latest answer is visible.
    return shouldCollapseAssistantMessage({
      role: props.msg.role,
      isTyping: props.isTyping,
      isLatestAssistantMessage: props.isLatestAssistantMessage,
    });
  });

  const toggleCollapse = () => {
    if (isCollapsed()) {
      setIsManuallyExpanded(true);
      setIsManuallyCollapsed(false);
    } else {
      setIsManuallyCollapsed(true);
      setIsManuallyExpanded(false);
    }
  };

  const handleSpeechShortcut = (e: KeyboardEvent) => {
    if (props.msg.role !== 'assistant') return;
    if (!speechController?.supported()) return;
    if (e.defaultPrevented) return;
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key.toLowerCase() !== 'r') return;
    const target = e.target as HTMLElement | null;
    if (target?.closest('button, input, textarea, select, [contenteditable="true"]')) return;
    e.preventDefault();
    speechController.toggleMessage(speechMessageId(), displayedMsg().content);
  };
  const assistantState = createMemo(() => {
    const res = adapted();
    const content = res.content;
    const reasoningEnabled = props.msg.reasoning_enabled === true;
    const isThinking = reasoningEnabled && (res.isThinking || (props.isTyping && !content));
    return {
      thought: res.thought,
      content,
      isActuallyThinking: res.isThinking,
      thoughtSource: res.source,
      reasoningEnabled,
      isThinking,
    };
  });

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
          ? userMessageContainerClass()
          : 'bg-surface text-text-primary border border-border/50 px-6 py-5 shadow-sm rounded-[24px] rounded-bl-none max-w-[90%] lg:max-w-[85%]'
      }`}
      >
        {props.msg.role === 'user' ? (
          <MessageUserContent
            msg={props.msg}
            attachments={userAttachments()}
            isEditing={isEditing()}
            editContent={editContent()}
            isSavingEdit={isSavingEdit()}
            editError={editError()}
            copiedMessageIndex={props.copiedMessageIndex}
            index={props.index}
            formattedTime={formatTime(props.msg.timestamp)}
            onEditInput={setEditContent}
            onEditKeyDown={onEditKeyDown}
            onStartEdit={() => {
              setEditContent(props.msg.content);
              setEditError(null);
              setIsEditing(true);
            }}
            onCancelEdit={closeEdit}
            onSubmitEdit={() => {
              void onSubmitEditedQuestion();
            }}
            copyUserMessage={props.copyUserMessage}
            quoteUserMessage={props.quoteUserMessage}
          />
        ) : (
          <MessageAssistantBody
            msg={props.msg}
            content={assistantState().content}
            thought={assistantState().thought}
            isActuallyThinking={assistantState().isActuallyThinking}
            thoughtSource={assistantState().thoughtSource}
            reasoningEnabled={assistantState().reasoningEnabled}
            isThinking={assistantState().isThinking}
            isTyping={props.isTyping}
            waitSecs={waitSecs()}
            loadingStatus={loadingStatus()}
            isCollapsed={isCollapsed()}
            expandedThought={!!props.expandedThoughts[props.index]}
            visionFeedbackText={visionFeedbackText()}
            isTruncated={isTruncated()}
            toggleCollapse={toggleCollapse}
            toggleThought={() => props.toggleThought(props.index)}
            onContinue={props.onContinue}
            onRegenerateChartArtifact={() => props.handleRegenerate(props.index)}
            onSaveChartArtifact={props.onSaveChartArtifact}
          />
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
          <MessageAssistantFooter
            content={displayedMsg().content}
            speechState={speechState()}
            modelLabel={modelLabel()}
            visionBadge={visionBadge()}
            msg={props.msg}
            isTyping={props.isTyping}
            speechControl={<SpeechControl messageId={speechMessageId()} content={displayedMsg().content} />}
            onExport={handleExportClick}
            onCollapse={toggleCollapse}
            onRegenerate={() => props.handleRegenerate(props.index)}
            workspaceCaptureSuggestion={workspaceCaptureSuggestion()}
            onSaveWorkspaceNote={props.onSaveWorkspaceNote}
            onSuggestWorkspaceMemoryCandidate={props.onSuggestWorkspaceMemoryCandidate}
            onTrackWorkspaceCaptureTelemetry={props.onTrackWorkspaceCaptureTelemetry}
          />
        </Show>
      </div>
      <Show when={exportMenuPos()}>
        <MessageExportMenu 
          content={displayedMsg().content}
          messageId={`message-container-${props.index}`}
          position={exportMenuPos()!}
          onClose={() => setExportMenuPos(null)}
        />
      </Show>
    </div>
  );
}
