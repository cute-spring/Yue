import { Accessor, Setter, createEffect, createSignal, onCleanup, onMount } from 'solid-js';
import { deriveSlashAgentSelectorState, getAgentSelectorKeyAction } from '../../../hooks/useAgents';
import { composeVoiceInputText, useVoiceInput } from '../../../hooks/useVoiceInput';

type VoiceInputController = ReturnType<typeof useVoiceInput>;

type UseVoiceComposerIntegrationArgs = {
  voiceInput: VoiceInputController;
  speechPrefs: Accessor<{ voice_input_enabled: boolean }>;
  currentAgentVoiceEnabled: Accessor<boolean>;
  input: Accessor<string>;
  setInput: Setter<string>;
  textareaRef: Accessor<HTMLTextAreaElement | undefined>;
  showAgentSelector: Accessor<boolean>;
  setShowAgentSelector: Setter<boolean>;
  setAgentFilter: Setter<string>;
  selectedIndex: Accessor<number>;
  setSelectedIndex: Setter<number>;
  filteredAgents: Accessor<any[]>;
  selectAgent: (agent: any, inputValue: string, setInput: Setter<string>) => void;
  onSubmit: (event: KeyboardEvent | Event) => void;
  onVoiceSubmit: (next: string) => void;
};

export function useVoiceComposerIntegration(args: UseVoiceComposerIntegrationArgs) {
  const [voiceCommitLockText, setVoiceCommitLockText] = createSignal<string | null>(null);
  const [composerKey, setComposerKey] = createSignal(1);

  let voiceCommitLockTimer: ReturnType<typeof setTimeout> | null = null;
  let voiceCommitReplayTimers: ReturnType<typeof setTimeout>[] = [];

  const focusTextareaToEnd = () => {
    const textarea = args.textareaRef();
    if (!textarea) return;
    textarea.focus();
    const next = textarea.value.length;
    textarea.setSelectionRange(next, next);
  };

  const applyVoiceCommittedText = (next: string) => {
    args.setInput(next);
    const textarea = args.textareaRef();
    if (textarea && textarea.value !== next) {
      textarea.value = next;
    }
  };

  const clearVoiceCommitLock = () => {
    setVoiceCommitLockText(null);
    if (voiceCommitLockTimer) {
      clearTimeout(voiceCommitLockTimer);
      voiceCommitLockTimer = null;
    }
    voiceCommitReplayTimers.forEach(clearTimeout);
    voiceCommitReplayTimers = [];
  };

  const lockVoiceCommittedText = (next: string) => {
    if (voiceCommitLockTimer) clearTimeout(voiceCommitLockTimer);
    voiceCommitReplayTimers.forEach(clearTimeout);
    voiceCommitReplayTimers = [];
    setVoiceCommitLockText(next);
    voiceCommitLockTimer = setTimeout(() => {
      voiceCommitLockTimer = null;
      setVoiceCommitLockText(null);
    }, 5000);

    for (const delay of [0, 30, 80, 160, 320, 640, 1000, 1800, 3000, 4500]) {
      const timer = setTimeout(() => {
        applyVoiceCommittedText(next);
      }, delay);
      voiceCommitReplayTimers.push(timer);
    }
  };

  const handleMentionSelect = (agent: any) => {
    args.selectAgent(agent, args.input(), args.setInput);
  };

  const handleInsertVoiceInput = (options?: { lock?: boolean; focus?: boolean }) => {
    const shouldLock = options?.lock ?? true;
    const shouldFocus = options?.focus ?? true;
    const next = args.voiceInput.consumeDraft();

    if (shouldLock) {
      lockVoiceCommittedText(next);
    } else {
      clearVoiceCommitLock();
    }

    applyVoiceCommittedText(next);
    setComposerKey((key) => key + 1);

    if (shouldFocus) {
      queueMicrotask(() => focusTextareaToEnd());
    }
  };

  const handleInsertAndSubmitVoiceInput = () => {
    const next = args.voiceInput.consumeDraft();
    clearVoiceCommitLock();
    setComposerKey((key) => key + 1);
    args.onVoiceSubmit(next);
  };

  const handleToggleVoiceInput = async () => {
    args.voiceInput.clearError();
    if (args.voiceInput.isRecording() || args.voiceInput.isProcessing()) {
      args.voiceInput.stopRecording();
      return;
    }
    setComposerKey((key) => key + 1);
    await args.voiceInput.startRecording(args.input());
  };

  const handleCancelVoiceInput = () => {
    if (args.voiceInput.isRecording() || args.voiceInput.isProcessing()) {
      args.voiceInput.cancelRecording();
      setComposerKey((key) => key + 1);
      return;
    }
    args.voiceInput.clearDraft();
    setComposerKey((key) => key + 1);
  };

  const handleVoiceDraftShortcut = (event: KeyboardEvent): boolean => {
    if (args.voiceInput.phase() !== 'ready') return false;
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      handleInsertAndSubmitVoiceInput();
      return true;
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleInsertVoiceInput();
      return true;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      handleCancelVoiceInput();
      return true;
    }
    return false;
  };

  const handleInput = (event: InputEvent & { currentTarget: HTMLTextAreaElement }) => {
    const target = event.currentTarget;
    const value = target.value;
    args.voiceInput.clearError();

    const lockedText = voiceCommitLockText();
    if (lockedText !== null && value !== lockedText) {
      target.value = lockedText;
      args.setInput(lockedText);
      return;
    }
    if (lockedText !== null && value === lockedText) {
      clearVoiceCommitLock();
    }

    if (args.voiceInput.phase() !== 'idle') {
      const voiceOnlyPreview = composeVoiceInputText(
        args.voiceInput.baseText(),
        args.voiceInput.transcript(),
        args.voiceInput.interimTranscript(),
        true,
      );
      const voiceCommittedPreview = composeVoiceInputText(
        args.voiceInput.baseText(),
        args.voiceInput.transcript(),
        '',
        false,
      );
      if (value === voiceOnlyPreview || value === voiceCommittedPreview) {
        target.value = args.input();
        return;
      }
    }

    const pos = target.selectionStart || 0;
    const slashState = deriveSlashAgentSelectorState(value, pos);
    if (slashState.show) {
      args.setShowAgentSelector(true);
      args.setAgentFilter(slashState.filter);
      args.setSelectedIndex(0);
    } else {
      args.setShowAgentSelector(false);
    }
    args.setInput(value);
  };

  const handleKeyDown = (event: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => {
    if (voiceCommitLockText() !== null && args.voiceInput.phase() === 'idle') {
      const isModifier = event.metaKey || event.ctrlKey || event.altKey;
      const editableKey =
        event.key.length === 1 ||
        event.key === 'Backspace' ||
        event.key === 'Delete' ||
        event.key === 'Enter' ||
        event.key === 'Tab';
      if (!isModifier && editableKey) {
        clearVoiceCommitLock();
      }
    }

    if (handleVoiceDraftShortcut(event)) return;

    if (args.showAgentSelector()) {
      const list = args.filteredAgents();
      const action = getAgentSelectorKeyAction(
        args.showAgentSelector(),
        list.length,
        event.key,
        event.shiftKey,
      );
      if (action === 'next') {
        event.preventDefault();
        args.setSelectedIndex((args.selectedIndex() + 1) % list.length);
      } else if (action === 'previous') {
        event.preventDefault();
        args.setSelectedIndex((args.selectedIndex() - 1 + list.length) % list.length);
      } else if (action === 'select') {
        event.preventDefault();
        handleMentionSelect(list[args.selectedIndex()]);
      } else if (action === 'close') {
        args.setShowAgentSelector(false);
      } else if (action === 'submit') {
        event.preventDefault();
        args.onSubmit(event);
      }
    } else if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      args.onSubmit(event);
    }
  };

  createEffect(() => {
    if (args.speechPrefs().voice_input_enabled && args.currentAgentVoiceEnabled()) return;
    if (args.voiceInput.isRecording() || args.voiceInput.isProcessing()) {
      args.voiceInput.cancelRecording();
    }
    args.voiceInput.clearDraft();
  });

  createEffect(() => {
    const lockedText = voiceCommitLockText();
    if (lockedText === null) return;
    applyVoiceCommittedText(lockedText);
  });

  createEffect(() => {
    if (args.voiceInput.phase() !== 'ready') return;
    queueMicrotask(() => focusTextareaToEnd());
  });

  onMount(() => {
    const onWindowKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      handleVoiceDraftShortcut(event);
    };

    window.addEventListener('keydown', onWindowKeyDown);
    onCleanup(() => {
      window.removeEventListener('keydown', onWindowKeyDown);
      clearVoiceCommitLock();
    });
  });

  return {
    composerKey,
    handleInput,
    handleKeyDown,
    handleToggleVoiceInput,
    handleCancelVoiceInput,
    handleInsertVoiceInput,
    handleInsertAndSubmitVoiceInput,
  };
}
