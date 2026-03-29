import { For, Show } from 'solid-js';
import { ChatSession } from '../types';

interface ChatSidebarProps {
  showHistory: boolean;
  chats: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
  onLoadChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onGenerateSummary: (id: string) => void;
}

export default function ChatSidebar(props: ChatSidebarProps) {
  return (
    <div
      class={`
        relative inset-y-0 left-0 bg-surface/90 backdrop-blur-xl border-r border-border/70 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showHistory ? 'w-[21rem] opacity-100' : 'w-0 opacity-0 overflow-hidden'}
      `}
    >
      <div class="h-full w-[21rem] flex flex-col">
        <div class="px-6 py-5 border-b border-border/70 flex justify-between items-center bg-surface/88 backdrop-blur-md sticky top-0 z-10">
          <h2 class="font-semibold text-text-primary text-sm tracking-[0.02em] flex items-center gap-2.5">
            <div class="w-2 h-2 rounded-full bg-primary/80 shadow-[0_0_8px_rgba(16,185,129,0.22)]"></div>
            Chat History
          </h2>
          <button 
            onClick={props.onNewChat} 
            class="group relative p-2.5 bg-primary/10 hover:bg-primary/14 text-primary rounded-2xl transition-all duration-300 active:scale-90 shadow-sm hover:shadow-primary/10"
            title="New Chat Session"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <div class="overflow-y-auto flex-1 px-3 py-3 pb-20 scrollbar-thin scrollbar-thumb-border">
          <For each={props.chats}>
            {chat => (
              <div 
                class={`my-1.5 rounded-[1.35rem] px-4 py-3.5 cursor-pointer group flex justify-between items-start transition-all ${
                  props.currentChatId === chat.id
                    ? 'bg-primary/10 ring-1 ring-primary/12 shadow-sm shadow-primary/5'
                    : 'hover:bg-background/90'
                }`}
                onClick={() => props.onLoadChat(chat.id)}
              >
                <div class="flex-1 min-w-0">
                  <h3 class="text-[14px] font-semibold truncate text-text-primary leading-5">{chat.title}</h3>
                  <Show when={chat.summary}>
                    <p class="text-[12px] leading-5 text-text-secondary mt-1.5 line-clamp-2">{chat.summary}</p>
                  </Show>
                  <p class="text-[11px] text-text-secondary/85 mt-2">{new Date(chat.updated_at).toLocaleDateString()}</p>
                </div>
                <div class="flex items-start gap-1">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      props.onGenerateSummary(chat.id);
                    }}
                    class="opacity-60 group-hover:opacity-100 text-text-secondary hover:text-primary p-1 transition-all"
                    title="Generate summary"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8M8 14h5M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3V8a2 2 0 012-2z" />
                    </svg>
                  </button>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      props.onDeleteChat(chat.id);
                    }}
                    class="opacity-60 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 transition-all"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            )}
          </For>
          <Show when={props.chats.length === 0}>
             <div class="p-8 text-center text-sm text-text-secondary italic">No recent chats</div>
          </Show>
        </div>
      </div>
    </div>
  );
}
