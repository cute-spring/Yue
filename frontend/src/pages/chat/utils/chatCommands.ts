import { Setter } from 'solid-js';
import { Message, WorkspaceNote } from '../../../types';

type ToastLike = {
  error: (message: string, duration?: number) => void;
  success: (message: string, duration?: number) => void;
};

type HandleChatCommandArgs = {
  trimmedInput: string;
  setMessages: Setter<Message[]>;
  setInput: (value: string) => void;
  submitText: (value: string, overrides?: Record<string, unknown>) => Promise<void> | void;
  saveLastAssistantAsWorkspaceNote: () => Promise<WorkspaceNote | null>;
  saveLastAssistantAsResearchArtifact: () => Promise<void>;
  toast: ToastLike;
};

const CLARIFY_COMMAND = '/clarify';

export const parseClarifyModeTask = (trimmedInput: string): string | null => {
  if (trimmedInput === CLARIFY_COMMAND) return '';
  if (trimmedInput.startsWith(`${CLARIFY_COMMAND} `)) {
    return trimmedInput.slice(CLARIFY_COMMAND.length).trim();
  }

  const naturalTriggers = [
    'clarify this:',
    'clarify this request:',
    'help me shape this:',
  ];
  const lower = trimmedInput.toLowerCase();
  for (const trigger of naturalTriggers) {
    if (lower.startsWith(trigger)) {
      return trimmedInput.slice(trigger.length).trim();
    }
  }

  return null;
};

export const buildClarifyModePrompt = (task: string): string => {
  const normalizedTask = task.trim();
  return [
    'Clarify Mode',
    '',
    'User request to clarify:',
    normalizedTask,
    '',
    'Ask one round of only the highest-impact questions before doing any implementation, research, writing, or external action.',
    '',
    'For each question, include:',
    '- Why this decision changes the outcome',
    '- Recommended answer',
    '- User-approved decision: pending',
    '',
    'Use this exact response format:',
    '',
    '## Clarifying Questions',
    '',
    '1. Question:',
    '   Why it matters:',
    '   Recommended answer:',
    '   User-approved decision: pending',
    '',
    '## Decision Brief',
    '',
    'Confirmed facts:',
    'Recommended defaults:',
    'Assumptions:',
    'Open questions:',
    'Next workbench mode:',
    'Follow-up handoff text:',
    '',
    'Do not execute the task yet. Do not treat recommended answers as user-approved decisions.',
  ].join('\n');
};

const buildClarifyUsageMessage = (): Message => ({
  role: 'assistant',
  content: 'Use `/clarify <task>` to ask Yue for one focused decision round and a decision brief before it acts.',
  timestamp: new Date().toISOString(),
});

export const handleChatCommand = ({
  trimmedInput,
  setMessages,
  setInput,
  submitText,
  saveLastAssistantAsWorkspaceNote,
  saveLastAssistantAsResearchArtifact,
  toast,
}: HandleChatCommandArgs): boolean => {
  if (trimmedInput === '/help') {
    const helpMsg: Message = {
      role: 'assistant',
      content: 'Commands: /help /clarify /note /research /clear',
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, helpMsg]);
    setInput('');
    return true;
  }

  if (trimmedInput === '/clear') {
    setMessages([]);
    setInput('');
    return true;
  }

  const clarifyTask = parseClarifyModeTask(trimmedInput);
  if (clarifyTask !== null) {
    const task = clarifyTask.trim();
    if (!task) {
      setMessages((prev) => [...prev, buildClarifyUsageMessage()]);
      setInput('');
      return true;
    }

    void submitText(buildClarifyModePrompt(task));
    setInput('');
    return true;
  }

  if (trimmedInput === '/note') {
    saveLastAssistantAsWorkspaceNote()
      .then((note) =>
        toast.success(note?.title ? `Saved note: ${note.title}` : 'Saved to workspace notes.', 3000),
      )
      .catch((err) => {
        console.error('Failed to save workspace note', err);
        toast.error('Failed to save workspace note.', 3000);
      });
    setInput('');
    return true;
  }

  if (trimmedInput === '/research') {
    saveLastAssistantAsResearchArtifact()
      .then(() => toast.success('Saved as research artifact.', 3000))
      .catch((err) => {
        console.error('Failed to save research artifact', err);
        toast.error('Failed to save research artifact.', 3000);
      });
    setInput('');
    return true;
  }

  return false;
};
