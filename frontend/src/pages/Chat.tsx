import { createSignal, For, onMount, Show, createEffect } from 'solid-js';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import katex from 'katex';
import 'katex/dist/katex.min.css';

// Configure marked to use highlight.js via a custom renderer
const renderer = new marked.Renderer();

// Custom math rendering helper
const renderMath = (text: string) => {
  // Block math: $$ ... $$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
    try {
      return `<div class="math-block my-4 overflow-x-auto">` + 
             katex.renderToString(math, { displayMode: true, throwOnError: false }) + 
             `</div>`;
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Inline math: $ ... $ (avoiding common false positives like $100)
  // This regex matches $...$ where the content doesn't start or end with a space
  text = text.replace(/\$([^\s$](?:[^$]*[^\s$])?)\$/g, (_, math) => {
    try {
      return katex.renderToString(math, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  return text;
};
renderer.code = ({ text, lang }) => {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
  const highlighted = hljs.highlight(text, { language }).value;
  
  return `
    <div class="code-block-container relative group my-4 rounded-lg overflow-hidden border border-gray-700 bg-[#0d1117]">
      <div class="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-gray-700">
        <div class="flex items-center gap-1.5">
          <div class="w-2.5 h-2.5 rounded-full bg-[#ff5f56]"></div>
          <div class="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]"></div>
          <div class="w-2.5 h-2.5 rounded-full bg-[#27c93f]"></div>
          <span class="ml-2 text-xs font-mono text-gray-400 uppercase tracking-wider">${language}</span>
        </div>
        <button 
          onclick="window.copyToClipboard(this)" 
          class="p-1.5 rounded hover:bg-gray-700 text-gray-400 transition-colors flex items-center gap-1"
          title="Copy code"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          <span class="text-[10px] font-medium">Copy</span>
        </button>
      </div>
      <pre class="p-4 overflow-x-auto scrollbar-thin scrollbar-thumb-gray-700"><code class="hljs language-${language}">${highlighted}</code></pre>
    </div>
  `;
};

marked.setOptions({
  renderer
});

// Global helper for copying code
(window as any).copyToClipboard = (btn: HTMLButtonElement) => {
  const container = btn.closest('.code-block-container');
  const code = container?.querySelector('code')?.innerText;
  if (code) {
    navigator.clipboard.writeText(code).then(() => {
      const span = btn.querySelector('span');
      if (span) {
        const originalText = span.innerText;
        span.innerText = 'Copied!';
        btn.classList.add('text-emerald-400');
        setTimeout(() => {
          span.innerText = originalText;
          btn.classList.remove('text-emerald-400');
        }, 2000);
      }
    });
  }
};

type Agent = {
  id: string;
  name: string;
};

type ChatSession = {
  id: string;
  title: string;
  updated_at: string;
};

type Message = {
  role: string;
  content: string;
};

export default function Chat() {
  const [messages, setMessages] = createSignal<Message[]>([]);
  const [input, setInput] = createSignal("");
  const [isTyping, setIsTyping] = createSignal(false);
  const [agents, setAgents] = createSignal<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = createSignal<string>("");
  const [showAgentSelector, setShowAgentSelector] = createSignal(false);
  const [agentFilter, setAgentFilter] = createSignal("");
  const [selectedIndex, setSelectedIndex] = createSignal(0);
  
  // Feature States (Mock)
  const [isDeepThinking, setIsDeepThinking] = createSignal(false);
  
  // History State
  const [chats, setChats] = createSignal<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = createSignal<string | null>(null);
  const [showHistory, setShowHistory] = createSignal(false);

  // LLM State
  const [providers, setProviders] = createSignal<any[]>([]);
  const [selectedProvider, setSelectedProvider] = createSignal("openai");
  const [selectedModel, setSelectedModel] = createSignal("gpt-4o");
  
  let textareaRef: HTMLTextAreaElement | undefined;
  let chatContainerRef: HTMLDivElement | undefined;
  let abortController: AbortController | null = null;

  // Auto-scroll logic
  createEffect(() => {
    messages(); // Dependency
    if (chatContainerRef && !userHasScrolledUp()) {
      chatContainerRef.scrollTo({
        top: chatContainerRef.scrollHeight,
        behavior: isTyping() ? 'auto' : 'smooth'
      });
    }
  });

  const [userHasScrolledUp, setUserHasScrolledUp] = createSignal(false);
   const handleScroll = (e: Event) => {
     const target = e.currentTarget as HTMLDivElement;
     const isAtBottom = target.scrollHeight - target.scrollTop <= target.clientHeight + 50;
     setUserHasScrolledUp(!isAtBottom);
   };

   // Helper to split thought and content
   const parseThoughtAndContent = (text: string) => {
     const thoughtMatch = text.match(/<thought>([\s\S]*?)(?:<\/thought>|$)/);
     if (thoughtMatch) {
       const thought = thoughtMatch[1];
       const rest = text.replace(/<thought>[\s\S]*?(?:<\/thought>|$)/, "").trim();
       return { thought, content: rest };
     }
     return { thought: null, content: text };
   };

   const [expandedThoughts, setExpandedThoughts] = createSignal<Record<number, boolean>>({});
   const toggleThought = (index: number) => {
     setExpandedThoughts(prev => ({ ...prev, [index]: !prev[index] }));
   };

  const filteredAgents = () => {
    const filter = agentFilter().toLowerCase();
    return agents().filter(a => a.name.toLowerCase().includes(filter));
  };

  const adjustHeight = () => {
    if (textareaRef) {
      textareaRef.style.height = 'auto';
      textareaRef.style.height = Math.min(textareaRef.scrollHeight, 200) + 'px';
    }
  };

  const handleInput = (e: InputEvent & { currentTarget: HTMLTextAreaElement }) => {
    const value = e.currentTarget.value;
    const pos = e.currentTarget.selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');

    if (lastAtPos !== -1 && (lastAtPos === 0 || textBefore[lastAtPos - 1] === ' ')) {
      setShowAgentSelector(true);
      setAgentFilter(textBefore.substring(lastAtPos + 1));
      setSelectedIndex(0);
    } else {
      setShowAgentSelector(false);
    }
    setInput(value);
    adjustHeight();
  };

  const handleKeyDown = (e: KeyboardEvent & { currentTarget: HTMLTextAreaElement }) => {
    if (showAgentSelector()) {
      const list = filteredAgents();
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() + 1) % list.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((selectedIndex() - 1 + list.length) % list.length);
      } else if (e.key === 'Enter' && list.length > 0) {
        e.preventDefault();
        selectAgent(list[selectedIndex()]);
      } else if (e.key === 'Escape') {
        setShowAgentSelector(false);
      }
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const selectAgent = (agent: Agent) => {
    const value = input();
    const pos = textareaRef?.selectionStart || 0;
    const textBefore = value.substring(0, pos);
    const lastAtPos = textBefore.lastIndexOf('@');
    
    const newValue = value.substring(0, lastAtPos) + value.substring(pos);
    setInput(newValue);
    setSelectedAgent(agent.id);
    setShowAgentSelector(false);
  };

  const loadAgents = async () => {
    try {
      const res = await fetch('/api/agents/');
      const data = await res.json();
      setAgents(data);
    } catch (e) {
      console.error("Failed to load agents", e);
    }
  };

  const loadHistory = async () => {
    try {
      const res = await fetch('/api/chat/history');
      setChats(await res.json());
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

  const loadProviders = async () => {
    try {
      const res = await fetch('/api/models/providers');
      const data = await res.json();
      setProviders(data);
      // Initialize with first configured provider if not set
      if (data.length > 0 && !selectedProvider()) {
        const first = data.find((p: any) => p.configured) || data[0];
        setSelectedProvider(first.name);
        setSelectedModel(first.current_model || 'default');
      }
    } catch (e) {
      console.error("Failed to load providers", e);
    }
  };

  const loadChat = async (id: string) => {
    try {
      const res = await fetch(`/api/chat/${id}`);
      const data = await res.json();
      setCurrentChatId(data.id);
      setMessages(data.messages);
      setSelectedAgent(data.agent_id);
      setShowHistory(false); // On mobile, close sidebar
    } catch (e) {
      console.error("Failed to load chat", e);
    }
  };

  const startNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
    setInput("");
    if (textareaRef) textareaRef.style.height = 'auto';
    setShowHistory(false);
  };

  const deleteChat = async (id: string, e: Event) => {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    try {
      await fetch(`/api/chat/${id}`, { method: 'DELETE' });
      loadHistory();
      if (currentChatId() === id) startNewChat();
    } catch (e) {}
  };

  onMount(() => {
    loadAgents();
    loadHistory();
    loadProviders();
  });

  const stopGeneration = () => {
    if (abortController) {
      abortController.abort();
      abortController = null;
      setIsTyping(false);
    }
  };

  const handleSubmit = async (e: Event) => {
    e.preventDefault();
    const text = input().trim();
    if (!text) return;
    
    if (isTyping()) {
      stopGeneration();
      return;
    }
    
    const agentId = selectedAgent() || undefined;

    setMessages([...messages(), { role: 'user', content: text }]);
    setInput("");
    if (textareaRef) {
      textareaRef.style.height = 'auto';
    }
    setIsTyping(true);
    setMessages(prev => [...prev, { role: 'assistant', content: "" }]);

    abortController = new AbortController();

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
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
                  loadHistory(); // Refresh history list to show new title
                } else if (data.content) {
                  accumulatedResponse += data.content;
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: accumulatedResponse };
                    return newMsgs;
                  });
                } else if (data.error) {
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    const lastIndex = newMsgs.length - 1;
                    newMsgs[lastIndex] = { ...newMsgs[lastIndex], content: `Error: ${data.error}` };
                    return newMsgs;
                  });
                }
              } catch (e) {}
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user');
      } else {
        console.error("Chat error:", err);
      }
    } finally {
      setIsTyping(false);
      abortController = null;
    }
  };

  const activeAgentName = () => {
    const agent = agents().find(a => a.id === selectedAgent());
    return agent ? agent.name : 'AI Assistant';
  };

  return (
    <div class="flex h-full bg-gray-50 overflow-hidden">
      {/* History Sidebar */}
      <div class={`
        fixed md:relative inset-y-0 left-0 w-64 bg-white border-r transform transition-transform z-20
        ${showHistory() ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div class="p-4 border-b flex justify-between items-center bg-gray-50">
          <h2 class="font-bold text-gray-800">History</h2>
          <button onClick={startNewChat} class="text-emerald-600 hover:text-emerald-700 p-1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <div class="overflow-y-auto h-full pb-20">
          <For each={chats()}>
            {chat => (
              <div 
                class={`p-3 border-b cursor-pointer hover:bg-gray-50 group flex justify-between items-start ${
                  currentChatId() === chat.id ? 'bg-emerald-50 border-l-4 border-l-emerald-500' : 'border-l-4 border-l-transparent'
                }`}
                onClick={() => loadChat(chat.id)}
              >
                <div class="flex-1 min-w-0">
                  <h3 class="text-sm font-medium text-gray-800 truncate">{chat.title}</h3>
                  <p class="text-xs text-gray-500">{new Date(chat.updated_at).toLocaleDateString()}</p>
                </div>
                <button 
                  onClick={(e) => deleteChat(chat.id, e)}
                  class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 p-1 transition-opacity"
                >
                  ×
                </button>
              </div>
            )}
          </For>
          <Show when={chats().length === 0}>
             <div class="p-4 text-center text-sm text-gray-400">No recent chats</div>
          </Show>
        </div>
      </div>

      {/* Main Chat Area */}
      <div class="flex-1 flex flex-col h-full min-w-0">
        {/* Mobile Header Toggle */}
        <div class="md:hidden p-2 bg-white border-b flex items-center">
          <button onClick={() => setShowHistory(!showHistory())} class="p-2 text-gray-600">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span class="font-bold ml-2">Chat</span>
        </div>

        <div class="p-4 border-b flex items-center justify-between bg-white shadow-sm z-10">
          <div class="flex items-center gap-3">
            <div class="relative group">
              <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 font-bold text-xl shrink-0 cursor-pointer hover:bg-emerald-200 transition-colors">
                <Show when={selectedAgent()} fallback={
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                }>
                  {activeAgentName().charAt(0)}
                </Show>
              </div>
              {/* Agent Selector Dropdown (Absolute positioned below avatar) */}
              <div class="absolute left-0 top-full mt-2 w-48 bg-white border rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-30">
                <div class="p-2 border-b bg-gray-50 rounded-t-xl">
                  <span class="text-[10px] font-bold text-gray-400 uppercase">Switch Persona</span>
                </div>
                <div class="max-h-60 overflow-y-auto p-1">
                  <button 
                    onClick={() => setSelectedAgent("")}
                    class={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                      selectedAgent() === "" ? 'bg-emerald-50 text-emerald-700 font-bold' : 'hover:bg-gray-50 text-gray-600'
                    }`}
                  >
                    No Persona (Generic)
                  </button>
                  <div class="h-[1px] bg-gray-100 my-1"></div>
                  <For each={agents()}>
                    {agent => (
                      <button 
                        onClick={() => setSelectedAgent(agent.id)}
                        class={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          selectedAgent() === agent.id ? 'bg-emerald-50 text-emerald-700 font-bold' : 'hover:bg-gray-50 text-gray-600'
                        }`}
                      >
                        {agent.name}
                      </button>
                    )}
                  </For>
                </div>
              </div>
            </div>
            <div>
              <h3 class="font-bold text-gray-800 text-sm truncate max-w-[150px]">{activeAgentName()}</h3>
              <div class="flex items-center gap-1.5">
                <span class={`w-1.5 h-1.5 rounded-full ${isTyping() ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'}`}></span>
                <p class="text-[10px] text-gray-500 uppercase tracking-wider">{isTyping() ? 'Thinking' : 'Ready'}</p>
              </div>
            </div>
          </div>
          
          <div class="flex items-center gap-4">
            <Show when={selectedProvider()}>
              <div class="flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full border border-gray-200">
                <span class="text-[10px] font-bold text-gray-500">{selectedProvider().toUpperCase()}</span>
                <span class="text-[10px] text-emerald-600 font-mono">{selectedModel()}</span>
              </div>
            </Show>
          </div>
        </div>
        
        <div 
          ref={chatContainerRef}
          onScroll={handleScroll}
          class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
        >
          <Show when={messages().length === 0}>
            <div class="h-full flex flex-col items-center justify-center text-gray-400 opacity-50">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p class="text-lg font-medium">Start a conversation with {activeAgentName()}</p>
            </div>
          </Show>

          <For each={messages()}>
            {(msg, index) => (
              <div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div class={`max-w-[85%] px-5 py-3 rounded-2xl shadow-sm ${
                  msg.role === 'user' 
                    ? 'bg-emerald-600 text-white rounded-br-none' 
                    : 'bg-white text-gray-800 border rounded-bl-none'
                }`}>
                  {msg.role === 'user' ? (
                     <div class="whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                     <div class="relative space-y-3">
                        {(() => {
                          const { thought, content } = parseThoughtAndContent(msg.content);
                          return (
                            <>
                              <Show when={thought}>
                                <div class="thought-container bg-gray-50 border-l-2 border-gray-300 rounded-r-lg overflow-hidden transition-all duration-300">
                                  <button 
                                    onClick={() => toggleThought(index())}
                                    class="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-gray-500 hover:bg-gray-100 transition-colors"
                                  >
                                    <div class="flex items-center gap-2">
                                      <svg xmlns="http://www.w3.org/2000/svg" class={`h-3.5 w-3.5 transition-transform ${expandedThoughts()[index()] ? 'rotate-90' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                                        <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                                      </svg>
                                      <span>{isTyping() && !content ? 'Thinking...' : 'Thought Process'}</span>
                                    </div>
                                    <Show when={!expandedThoughts()[index()]}>
                                      <span class="text-[10px] opacity-50 truncate max-w-[200px]">{thought?.slice(0, 50)}...</span>
                                    </Show>
                                  </button>
                                  <Show when={expandedThoughts()[index()]}>
                                    <div class="px-3 pb-3 text-xs text-gray-600 italic leading-relaxed border-t border-gray-100 mt-1 pt-2 animate-in fade-in slide-in-from-top-1">
                                      {thought}
                                    </div>
                                  </Show>
                                </div>
                              </Show>
                              
                              <Show when={content || (isTyping() && !thought)}>
                                <div 
                                  innerHTML={marked.parse(renderMath(content)) as string} 
                                  class="prose prose-sm max-w-none prose-p:my-1 prose-headings:mb-2 prose-headings:mt-4 prose-code:text-emerald-600 prose-code:bg-emerald-50 prose-code:px-1 prose-code:rounded prose-pre:p-0 prose-pre:bg-transparent" 
                                />
                              </Show>
                            </>
                          );
                        })()}
                        
                        <Show when={isTyping() && index() === messages().length - 1}>
                          <span class="inline-block w-1.5 h-4 ml-1 bg-emerald-500 animate-pulse align-middle"></span>
                        </Show>
                     </div>
                  )}
                </div>
              </div>
            )}
          </For>
          
          {/* Typing Indicator moved inside the loop for smoother flow, 
              but we keep this for initial "thinking" phase if needed */}
          <Show when={isTyping() && messages().length > 0 && messages()[messages().length-1].content === ""}>
            <div class="flex justify-start">
              <div class="bg-white px-4 py-3 rounded-2xl rounded-bl-none border shadow-sm flex items-center gap-1">
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
              </div>
            </div>
          </Show>
        </div>

        <div class="p-6 bg-white border-t relative">
          <Show when={showAgentSelector()}>
            <div class="absolute bottom-full left-6 mb-2 w-64 bg-white border rounded-xl shadow-xl overflow-hidden z-10">
              <div class="bg-gray-50 px-4 py-2 border-b">
                <span class="text-xs font-bold text-gray-500 uppercase">Select Agent</span>
              </div>
              <div class="max-h-60 overflow-y-auto">
                <For each={filteredAgents()}>
                  {(agent, index) => (
                    <button
                      onClick={() => selectAgent(agent)}
                      class={`w-full text-left px-4 py-3 flex items-center justify-between transition-colors ${
                        selectedIndex() === index() ? 'bg-emerald-50 text-emerald-700' : 'hover:bg-gray-50'
                      }`}
                    >
                      <span class="font-medium">{agent.name}</span>
                      <Show when={selectedIndex() === index()}>
                        <span class="text-xs bg-emerald-100 px-2 py-0.5 rounded text-emerald-600">Enter</span>
                      </Show>
                    </button>
                  )}
                </For>
                <Show when={filteredAgents().length === 0}>
                  <div class="px-4 py-3 text-sm text-gray-500 italic">No agents found</div>
                </Show>
              </div>
            </div>
          </Show>

          <form onSubmit={handleSubmit} class="max-w-4xl mx-auto">
            <div class="relative bg-gray-50 border-2 border-blue-100 rounded-[24px] focus-within:border-blue-400 focus-within:bg-white transition-all p-3 shadow-sm">
              <textarea
                ref={textareaRef}
                value={input()}
                onInput={handleInput}
                onKeyDown={handleKeyDown}
                placeholder="询问 AI 任何问题"
                class="w-full bg-transparent px-4 py-2 focus:outline-none resize-none max-h-48 overflow-y-auto text-gray-700 leading-relaxed"
                rows={1}
              />
              
              <div class="flex items-center justify-between mt-2 px-1">
                <div class="flex items-center gap-2">
                  {/* Deep Thinking Toggle */}
                  <button 
                    type="button"
                    onClick={() => setIsDeepThinking(!isDeepThinking())}
                    class={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition-colors ${
                      isDeepThinking() 
                        ? 'bg-blue-50 border-blue-200 text-blue-600' 
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    深度思考
                  </button>

                  {/* LLM Switcher (Integrated) */}
                  <div class="relative group/llm">
                    <button 
                      type="button"
                      class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-50 border border-blue-100 text-blue-600 text-xs font-bold hover:bg-blue-100 transition-colors"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 11-2 0 1 1 0 012 0zM8 16v-1a1 1 0 10-2 0v1a1 1 0 102 0zM13.657 15.657a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM16 10a1 1 0 11-2 0 1 1 0 012 0z" />
                      </svg>
                      {selectedModel().toUpperCase()}
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h8M8 12h8m-8 5h8" />
                      </svg>
                    </button>
                    
                    {/* LLM Dropdown */}
                    <div class="absolute bottom-full left-0 mb-2 w-64 bg-white border rounded-xl shadow-xl opacity-0 invisible group-hover/llm:opacity-100 group-hover/llm:visible transition-all z-30 overflow-hidden">
                      <div class="p-2 border-b bg-gray-50 flex justify-between items-center">
                        <span class="text-[10px] font-bold text-gray-400 uppercase">Select Model</span>
                        <span class="text-[10px] text-blue-500 font-medium">Auto-detected</span>
                      </div>
                      <div class="max-h-80 overflow-y-auto p-1">
                        <For each={providers()}>
                          {p => (
                            <div class="mb-2 last:mb-0">
                              <div class={`px-2 py-1 text-[10px] font-bold uppercase flex items-center justify-between ${p.configured ? 'text-gray-400' : 'text-gray-300'}`}>
                                <span>{p.name}</span>
                                <Show when={!p.configured}>
                                  <span class="text-[8px] border border-gray-200 px-1 rounded">Offline</span>
                                </Show>
                              </div>
                              <div class="space-y-0.5">
                                <For each={p.available_models}>
                                  {model => (
                                    <button 
                                      onClick={() => {
                                        setSelectedProvider(p.name);
                                        setSelectedModel(model);
                                      }}
                                      class={`w-full text-left px-3 py-1.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                                        selectedProvider() === p.name && selectedModel() === model 
                                          ? 'bg-blue-50 text-blue-700 font-bold' 
                                          : 'hover:bg-gray-50 text-gray-600'
                                      }`}
                                    >
                                      <span class="truncate">{model}</span>
                                      <Show when={selectedProvider() === p.name && selectedModel() === model}>
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                                          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                        </svg>
                                      </Show>
                                    </button>
                                  )}
                                </For>
                                <Show when={p.available_models.length === 0 && p.name === 'ollama'}>
                                  <div class="px-3 py-2 text-[10px] text-gray-400 italic bg-gray-50 rounded">
                                    Ollama not found or no models pulled.
                                  </div>
                                </Show>
                              </div>
                            </div>
                          )}
                        </For>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="flex items-center gap-3 text-gray-400">
                  {/* Mock Buttons: Voice, Attachment, Image */}
                  <button type="button" class="hover:text-gray-600 transition-colors" title="语音输入">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  </button>
                  <button type="button" class="hover:text-gray-600 transition-colors" title="上传文档">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                  </button>
                  <button type="button" class="hover:text-gray-600 transition-colors" title="上传图片">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </button>

                  {/* Send Button */}
                  <button 
                    type="submit"
                    disabled={isTyping()}
                    class={`p-2 rounded-full transition-all ${
                      isTyping() 
                        ? 'bg-gray-100 text-gray-300 cursor-not-allowed' 
                        : 'bg-blue-100 text-blue-600 hover:bg-blue-600 hover:text-white shadow-sm'
                    }`}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </form>
          <div class="text-center mt-3">
             <p class="text-[10px] text-gray-400">内容由 AI 生成，仅供参考。请核实重要信息。</p>
          </div>
        </div>
      </div>
    </div>
  );
}
