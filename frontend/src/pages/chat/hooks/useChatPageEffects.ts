import { Accessor, Setter, createEffect, createSignal, onMount } from 'solid-js';
import mermaid from 'mermaid';
import { getMermaidInitConfig, getMermaidThemePreset } from '../../../utils/mermaidTheme';
import { parseThoughtAndContent } from '../../../utils/thoughtParser';
import {
  handleMermaidClick,
  handleMermaidWheel,
  handleMermaidChange,
  handleMermaidPointerDown,
  handleMermaidPointerMove,
  handleMermaidPointerUp,
  closeMermaidExportModal,
  closeMermaidOverlay,
} from '../../../utils/mermaidRenderer';
import { copyCodeBlockText } from '../../../utils/markdown';
import { getSpeechMessageId } from '../../../utils/speech';
import { Message } from '../../../types';

type ToastLike = {
  error: (message: string, duration?: number) => void;
  success?: (message: string, duration?: number) => void;
  info?: (message: string, duration?: number) => void;
  warning?: (message: string, duration?: number) => void;
};

type UseChatPageEffectsArgs = {
  input: Accessor<string>;
  textareaRef: Accessor<HTMLTextAreaElement | undefined>;
  chatContainerRef: Accessor<HTMLDivElement | undefined>;
  messagesEndRef: Accessor<HTMLDivElement | undefined>;
  messages: Accessor<Message[]>;
  isTyping: Accessor<boolean>;
  expandedThoughts: Accessor<Record<number, boolean>>;
  setExpandedThoughts: Setter<Record<number, boolean>>;
  lastGenerationOutcome: Accessor<'success' | 'aborted' | 'error' | null>;
  speechPrefs: Accessor<{ auto_speech_enabled: boolean }>;
  speech: {
    speakMessage: (id: string, content: string) => boolean;
  };
  debouncedRender: () => void;
  toast: ToastLike;
  setShowLLMSelector: Setter<boolean>;
  setShowAgentSelector: Setter<boolean>;
  setPreviewContent: Setter<{ lang: string; content: string } | null>;
  setIntelligenceTab: Setter<'actions' | 'preview' | 'stats'>;
  setShowKnowledge: Setter<boolean>;
  setSelectedProvider: Setter<string>;
  setSelectedModel: Setter<string>;
  loadProviders: () => void | Promise<void>;
  loadSkills: () => void | Promise<void>;
  loadWorkspaces: () => void | Promise<void>;
  providerStorageKey: string;
  modelStorageKey: string;
};

export function useChatPageEffects(args: UseChatPageEffectsArgs) {
  const [windowWidth, setWindowWidth] = createSignal(window.innerWidth);
  const [userHasScrolledUp, setUserHasScrolledUp] = createSignal(false);
  const [lastAutoSpokenKey, setLastAutoSpokenKey] = createSignal('');

  const isMobile = () => windowWidth() < 1024;

  const handleScroll = (event: Event) => {
    const target = event.currentTarget as HTMLDivElement;
    const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 100;
    setUserHasScrolledUp(!isAtBottom);
  };

  createEffect(() => {
    const value = args.input();
    const textarea = args.textareaRef();
    if (!textarea) return;
    textarea.style.height = 'auto';
    if (value !== '') {
      textarea.style.height = `${textarea.scrollHeight}px`;
    }
  });

  createEffect(() => {
    if (args.messages().length > 0 && !userHasScrolledUp()) {
      args.messagesEndRef()?.scrollIntoView({ behavior: 'smooth' });
    }
  });

  createEffect(() => {
    const msgs = args.messages();
    if (msgs.length === 0) return;
    const lastIdx = msgs.length - 1;
    const lastMsg = msgs[lastIdx];
    if (lastMsg.role === 'assistant' && args.isTyping()) {
      const { isThinking } = parseThoughtAndContent(lastMsg.content);
      if (isThinking && !args.expandedThoughts()[lastIdx]) {
        args.setExpandedThoughts((prev) => ({ ...prev, [lastIdx]: true }));
      }
    }
  });

  createEffect(() => {
    const outcome = args.lastGenerationOutcome();
    const typing = args.isTyping();
    const prefs = args.speechPrefs();
    const msgs = args.messages();
    if (typing || outcome !== 'success' || !prefs.auto_speech_enabled) return;
    const lastIndex = msgs.length - 1;
    if (lastIndex < 0) return;
    const msg = msgs[lastIndex];
    if (msg.role !== 'assistant') return;
    if (!msg.content?.trim() || msg.error || msg.content.startsWith('Error:')) return;
    const messageId = getSpeechMessageId(msg, lastIndex);
    const messageKey = `${messageId}:${msg.content.length}:${msg.total_duration ?? 0}`;
    if (messageKey === lastAutoSpokenKey()) return;
    if (args.speech.speakMessage(messageId, msg.content)) {
      setLastAutoSpokenKey(messageKey);
    }
  });

  createEffect(() => {
    args.messages();
    args.debouncedRender();
  });

  createEffect(() => {
    args.messages();
    const chatContainer = args.chatContainerRef();
    if (chatContainer && !userHasScrolledUp()) {
      chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: args.isTyping() ? 'auto' : 'smooth',
      });
    }
  });

  onMount(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);

    const preset = getMermaidThemePreset();
    (mermaid as any).initialize(getMermaidInitConfig(preset));

    const storedProvider = localStorage.getItem(args.providerStorageKey);
    const storedModel = localStorage.getItem(args.modelStorageKey);
    if (storedProvider) args.setSelectedProvider(storedProvider);
    if (storedModel) args.setSelectedModel(storedModel);

    void args.loadProviders();
    void args.loadSkills();
    void args.loadWorkspaces();

    (window as any).openArtifact = (lang: string, encodedContent: string) => {
      try {
        const content = decodeURIComponent(encodedContent);
        args.setPreviewContent({ lang, content });
        args.setIntelligenceTab('preview');
        args.setShowKnowledge(true);
      } catch (e) {
        console.error('Failed to open artifact:', e);
        args.toast.error('Failed to open artifact preview');
      }
    };
    (window as any).copyToClipboard = copyCodeBlockText;

    const handleGlobalClick = () => {
      args.setShowLLMSelector(false);
      args.setShowAgentSelector(false);
    };
    window.addEventListener('click', handleGlobalClick);

    const onMermaidClick = (event: MouseEvent) =>
      handleMermaidClick(event, (type, msg) => {
        const sink = args.toast[type as keyof ToastLike] || args.toast.error;
        sink(msg);
      });
    document.addEventListener('click', onMermaidClick);
    document.addEventListener('wheel', handleMermaidWheel, { passive: false });
    document.addEventListener('change', handleMermaidChange);
    document.addEventListener('pointerdown', handleMermaidPointerDown);
    document.addEventListener('pointermove', handleMermaidPointerMove, { passive: false } as any);
    document.addEventListener('pointerup', handleMermaidPointerUp);

    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (event.defaultPrevented) return;
        closeMermaidExportModal();
        closeMermaidOverlay();
      }
    };
    document.addEventListener('keydown', handleGlobalKeyDown);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('click', handleGlobalClick);
      document.removeEventListener('click', onMermaidClick);
      document.removeEventListener('wheel', handleMermaidWheel as any);
      document.removeEventListener('change', handleMermaidChange);
      document.removeEventListener('pointerdown', handleMermaidPointerDown);
      document.removeEventListener('pointermove', handleMermaidPointerMove as any);
      document.removeEventListener('pointerup', handleMermaidPointerUp);
      document.removeEventListener('keydown', handleGlobalKeyDown);
      if ((window as any).copyToClipboard === copyCodeBlockText) {
        delete (window as any).copyToClipboard;
      }
      closeMermaidExportModal();
      closeMermaidOverlay();
    };
  });

  return {
    isMobile,
    handleScroll,
  };
}
