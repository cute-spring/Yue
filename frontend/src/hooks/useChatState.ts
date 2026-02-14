import { createSignal, onMount } from 'solid-js';
import { ChatSession, Message } from '../types';
import { useToast } from '../context/ToastContext';

export function useChatState(
  selectedProvider: () => string,
  selectedModel: () => string,
  selectedAgent: () => string | null,
  setShowLLMSelector: (v: boolean) => void
) {
  const toast = useToast();
  const [chats, setChats] = createSignal<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = createSignal<string | null>(null);
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [elapsedTime, setElapsedTime] = createSignal(0);
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  const [expandedThoughts, setExpandedThoughts] = createSignal<Record<number, boolean>>({});
  const [imageAttachments, setImageAttachments] = createSignal<File[]>([]);
  const [copiedMessageIndex, setCopiedMessageIndex] = createSignal<number | null>(null);
  
  let abortController: AbortController | null = null;
  let timerInterval: any = null;

  const loadHistory = async () => {
    try {
      const res = await fetch('/api/chat/history');
      const data = await res.json();
      setChats(data);
    } catch (e) {
      console.error("Failed to load history", e);
      toast.error("Failed to load chat history");
    }
  };

  const loadChat = async (id: string, isMobile: boolean, setShowHistory: (v: boolean) => void, setSelectedAgent: (v: string | null) => void) => {
    if (isTyping()) stopGeneration();
    try {
      const res = await fetch(`/api/chat/${id}`);
      const data = await res.json();
      setCurrentChatId(data.id);
      setMessages(data.messages);
      setSelectedAgent(data.agent_id);
      if (isMobile) {
        setShowHistory(false);
      }
    } catch (e) {
      console.error("Failed to load chat", e);
      toast.error("Failed to load chat session");
    }
  };

  const startNewChat = (isMobile: boolean, setShowHistory: (v: boolean) => void) => {
    if (isTyping()) stopGeneration();
    setCurrentChatId(null);
    setMessages([]);
    setInput("");
    if (isMobile) {
      setShowHistory(false);
    }
  };

  const deleteChat = async (id: string, e: Event) => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    try {
      await fetch(`/api/chat/${id}`, { method: 'DELETE' });
      loadHistory();
      if (currentChatId() === id) {
        setCurrentChatId(null);
        setMessages([]);
      }
      toast.success("Chat deleted successfully");
    } catch (e) {
      toast.error("Failed to delete chat");
    }
  };

  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
      setIsTyping(false);
      clearInterval(timerInterval);
    }
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  const handleSubmit = async (e?: Event) => {
    e?.preventDefault();
    const text = input().trim();
    if (!text) return;

    if (!selectedModel()) {
      setShowLLMSelector(true);
      const last = messages()[messages().length - 1];
      if (!last || last.role !== 'assistant' || last.content !== 'Please select a model before starting a chat.') {
        setMessages([...messages(), { role: 'assistant', content: 'Please select a model before starting a chat.' }]);
      }
      return;
    }

    if (isTyping()) {
      stopGeneration();
      return;
    }

    const agentId = selectedAgent() || undefined;
    const currentImages = imageAttachments();
    let base64Images: string[] = [];
    if (currentImages.length > 0) {
      try {
        base64Images = await Promise.all(currentImages.map(fileToBase64));
      } catch (e) {
        console.error("Failed to convert images", e);
        toast.error("Failed to process attached images");
      }
    }

    const nowIso = new Date().toISOString();
    const contextId = currentChatId() || undefined;
    setMessages([...messages(), { role: 'user', content: text, images: base64Images, timestamp: nowIso, context_id: contextId }]);
    setInput("");
    setImageAttachments([]);
    setIsTyping(true);
    setElapsedTime(0);
    const startTime = Date.now();
    let firstTokenTime: number | null = null;

    timerInterval = setInterval(() => setElapsedTime(t => t + 0.1), 100);
    setMessages(prev => [...prev, { role: 'assistant', content: "", timestamp: nowIso, provider: selectedProvider(), model: selectedModel(), context_id: contextId, tools: [], citations: [] }]);

    abortController = new AbortController();

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          images: base64Images.length > 0 ? base64Images : undefined,
          agent_id: agentId,
          chat_id: currentChatId(),
          provider: selectedProvider(),
          model: selectedModel(),
        }),
        signal: abortController.signal
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.chat_id) {
                  setCurrentChatId(data.chat_id);
                  setMessages(prev => prev.map(m => m.context_id ? m : { ...m, context_id: data.chat_id }));
                  loadHistory();
                } else if (data.meta) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], ...data.meta };
                    return newMsgs;
                  });
                } else if (data.content || data.thought) {
                  if (!firstTokenTime) {
                    firstTokenTime = Date.now();
                    const ttft = firstTokenTime - startTime;
                    setMessages(prev => {
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      newMsgs[lastIndex] = { ...newMsgs[lastIndex], ttft };
                      return newMsgs;
                    });
                  }
                  if (data.content) {
                    accumulatedResponse += data.content;
                    setMessages(prev => {
                      const newMsgs = [...prev];
                      const lastIndex = newMsgs.length - 1;
                      newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
                      return newMsgs;
                    });
                  }
                } else if (data.thought_duration) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], thought_duration: data.thought_duration };
                    return newMsgs;
                  });
                } else if (data.total_duration) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration: data.total_duration * 1000 };
                    return newMsgs;
                  });
                } else if (data.prompt_tokens !== undefined || data.completion_tokens !== undefined || data.total_tokens !== undefined || data.tps !== undefined || data.finish_reason !== undefined) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], ...data };
                    return newMsgs;
                  });
                } else if (data.citations) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], citations: data.citations };
                    return newMsgs;
                  });
                } else if (data.error) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: `Error: ${data.error}`, error: data.error };
                    return newMsgs;
                  });
                }
              } catch (e) {
                console.warn("Failed to parse stream message", e);
              }
            }
          }
        }
      }
      const total_duration = Date.now() - startTime;
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastIndex = newMsgs.length - 1;
        newMsgs[lastIndex] = { ...newMsgs[lastIndex], total_duration };
        return newMsgs;
      });
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user');
      } else {
        console.error("Chat error:", err);
        toast.error("Connection error: " + (err.message || "Unknown error"));
      }
    } finally {
      setIsTyping(false);
      clearInterval(timerInterval);
      abortController = null;
    }
  };

  const handleRegenerate = async (index: number) => {
    if (isTyping()) return;
    const historyBefore = messages().slice(0, index);
    const lastUserMsgIndex = historyBefore.findLastIndex(m => m.role === 'user');
    if (lastUserMsgIndex === -1) return;
    const lastUserMsg = historyBefore[lastUserMsgIndex];
    if (currentChatId()) {
      try {
        await fetch(`/api/chat/${currentChatId()}/truncate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keep_count: lastUserMsgIndex })
        });
      } catch (e) {
        console.error("Failed to truncate chat history", e);
      }
    }
    setMessages(messages().slice(0, lastUserMsgIndex));
    setInput(lastUserMsg.content);
    handleSubmit();
  };

  onMount(() => {
    loadHistory();
  });

  const toggleThought = (index: number) => {
    setExpandedThoughts(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const handleImageUpload = (e: Event) => {
    const target = e.target as HTMLInputElement;
    if (target.files) {
      setImageAttachments(prev => [...prev, ...Array.from(target.files!)]);
    }
  };

  const removeImage = (index: number) => {
    setImageAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const copyUserMessage = (content: string, index: number) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageIndex(index);
    setTimeout(() => setCopiedMessageIndex(null), 2000);
    toast.success("Copied to clipboard");
  };

  const quoteUserMessage = (content: string) => {
    setInput(`> ${content}\n\n${input()}`);
  };

  return {
    chats,
    setChats,
    currentChatId,
    setCurrentChatId,
    messages,
    setMessages,
    input,
    setInput,
    isTyping,
    setIsTyping,
    elapsedTime,
    setElapsedTime,
    isDeepThinking,
    setIsDeepThinking,
    expandedThoughts,
    setExpandedThoughts,
    imageAttachments,
    setImageAttachments,
    copiedMessageIndex,
    setCopiedMessageIndex,
    loadHistory,
    loadChat,
    startNewChat,
    deleteChat,
    stopGeneration,
    handleSubmit,
    handleRegenerate,
    toggleThought,
    handleImageUpload,
    removeImage,
    copyUserMessage,
    quoteUserMessage
  };
}
