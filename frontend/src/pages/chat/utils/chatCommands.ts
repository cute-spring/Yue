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
  saveLastAssistantAsWorkspaceNote: () => Promise<WorkspaceNote | null>;
  saveLastAssistantAsResearchArtifact: () => Promise<void>;
  toast: ToastLike;
};

export const handleChatCommand = ({
  trimmedInput,
  setMessages,
  setInput,
  saveLastAssistantAsWorkspaceNote,
  saveLastAssistantAsResearchArtifact,
  toast,
}: HandleChatCommandArgs): boolean => {
  if (trimmedInput === '/help') {
    const helpMsg: Message = {
      role: 'assistant',
      content: 'Commands: /help /note /research /clear',
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
