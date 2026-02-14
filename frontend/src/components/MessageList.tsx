import { For, Show } from 'solid-js';
import { Message } from '../types';
import MessageItem from './MessageItem';

interface MessageListProps {
  messages: Message[];
  activeAgentName: string;
  isTyping: boolean;
  expandedThoughts: Record<number, boolean>;
  toggleThought: (index: number) => void;
  elapsedTime: number;
  copiedMessageIndex: number | null;
  copyUserMessage: (content: string, index: number) => void;
  quoteUserMessage: (content: string) => void;
  handleRegenerate: (index: number) => void;
  messagesEndRef: (el: HTMLDivElement) => void;
  chatContainerRef: (el: HTMLDivElement) => void;
  handleScroll: (e: Event) => void;
  setInput: (val: string) => void;
  selectedProvider: string;
  selectedModel: string;
}

export default function MessageList(props: MessageListProps) {
  return (
    <div 
      ref={props.chatContainerRef}
      onScroll={props.handleScroll}
      class="flex-1 overflow-y-auto px-4 py-8 lg:px-12 space-y-8 scroll-smooth scrollbar-thin scrollbar-thumb-border/50"
    >
      <Show when={props.messages.length === 0}>
        <div class="h-full flex flex-col items-center justify-center text-center px-4 max-w-2xl mx-auto">
          <div class="w-24 h-24 mb-8 rounded-[2rem] bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center shadow-xl shadow-primary/5 border border-primary/10 animate-in zoom-in-90 duration-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h2 class="text-3xl font-extrabold text-text-primary tracking-tight mb-4">Empowering your workflow with Yue</h2>
          <p class="text-lg text-text-secondary leading-relaxed mb-8 max-w-lg mx-auto">
            Select an expert agent or start a new conversation to explore documents, research topics, or generate insights.
          </p>
          
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
            <button onClick={() => props.setInput("Generate a responsive landing page for a coffee shop using HTML and Tailwind CSS.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
              <div class="flex items-center gap-2 mb-2">
                <span class="p-1.5 rounded-lg bg-orange-500/10 text-orange-500 group-hover:bg-orange-500/20 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                </span>
                <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">HTML Preview</span>
              </div>
              <p class="text-sm text-text-primary line-clamp-2">Generate a responsive landing page for a coffee shop</p>
            </button>
            
            <button onClick={() => props.setInput("Create a complex SVG illustration of a futuristic city skyline.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
              <div class="flex items-center gap-2 mb-2">
                <span class="p-1.5 rounded-lg bg-pink-500/10 text-pink-500 group-hover:bg-pink-500/20 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </span>
                <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">SVG Artifact</span>
              </div>
              <p class="text-sm text-text-primary line-clamp-2">Create a complex SVG illustration of a city skyline</p>
            </button>

            <button onClick={() => props.setInput("Write a Python script to solve the Tower of Hanoi problem with a recursive function.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
              <div class="flex items-center gap-2 mb-2">
                <span class="p-1.5 rounded-lg bg-blue-500/10 text-blue-500 group-hover:bg-blue-500/20 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </span>
                <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">Code & Logic</span>
              </div>
              <p class="text-sm text-text-primary line-clamp-2">Solve Tower of Hanoi with recursive Python code</p>
            </button>

            <button onClick={() => props.setInput("Explain the Schrödinger equation with mathematical formulas.")} class="p-4 bg-surface border border-border rounded-2xl text-left hover:border-primary/50 hover:shadow-md transition-all group">
              <div class="flex items-center gap-2 mb-2">
                <span class="p-1.5 rounded-lg bg-green-500/10 text-green-500 group-hover:bg-green-500/20 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                </span>
                <span class="text-xs font-bold text-text-secondary group-hover:text-primary transition-colors uppercase tracking-wider">Math & Latex</span>
              </div>
              <p class="text-sm text-text-primary line-clamp-2">Explain Schrödinger equation with math formulas</p>
            </button>
          </div>
        </div>
      </Show>

      <For each={props.messages}>
        {(msg, index) => (
          <MessageItem 
            msg={msg}
            index={index()}
            activeAgentName={props.activeAgentName}
            isTyping={props.isTyping && index() === props.messages.length - 1}
            expandedThoughts={props.expandedThoughts}
            toggleThought={props.toggleThought}
            elapsedTime={props.elapsedTime}
            copiedMessageIndex={props.copiedMessageIndex}
            copyUserMessage={props.copyUserMessage}
            quoteUserMessage={props.quoteUserMessage}
            handleRegenerate={props.handleRegenerate}
            selectedProvider={props.selectedProvider}
            selectedModel={props.selectedModel}
          />
        )}
      </For>
      
      <Show when={props.isTyping && props.messages.length > 0 && props.messages[props.messages.length-1].content === ""}>
        <div class="flex justify-start animate-in fade-in duration-300">
          <div class="bg-surface px-5 py-4 rounded-2xl rounded-bl-none border border-border shadow-sm flex items-center gap-1.5">
            <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style="animation-delay: 300ms"></div>
          </div>
        </div>
      </Show>
      <div ref={props.messagesEndRef} />
    </div>
  );
}
