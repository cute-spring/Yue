import { For, Show } from 'solid-js';
import { ChatSession } from '../types';

interface ChatSidebarProps {
  showHistory: boolean;
  chats: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
  onLoadChat: (id: string) => void;
  onDeleteChat: (id: string, e: Event) => void;
}

export default function ChatSidebar(props: ChatSidebarProps) {
  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 left-0 bg-surface border-r border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showHistory ? 'translate-x-0 w-sidebar opacity-100' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
      `}
    >
      <div class="w-sidebar h-full flex flex-col">
        <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
          <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
            <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            Chat History
          </h2>
          <button 
            onClick={props.onNewChat} 
            class="group relative p-2 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-xl transition-all duration-300 active:scale-90 shadow-sm hover:shadow-primary/20"
            title="New Chat Session"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 transform group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
        <div class="overflow-y-auto flex-1 pb-20 scrollbar-thin scrollbar-thumb-border">
          <For each={props.chats}>
            {chat => (
              <div 
                class={`p-3 border-b border-border cursor-pointer hover:bg-primary/5 group flex justify-between items-start transition-colors ${
                  props.currentChatId === chat.id ? 'bg-primary/10 border-l-4 border-l-primary' : 'border-l-4 border-l-transparent'
                }`}
                onClick={() => props.onLoadChat(chat.id)}
              >
                <div class="flex-1 min-w-0">
                  <h3 class={`text-sm font-medium truncate ${props.currentChatId === chat.id ? 'text-primary' : 'text-text-primary'}`}>{chat.title}</h3>
                  <p class="text-[10px] text-text-secondary mt-1">{new Date(chat.updated_at).toLocaleDateString()}</p>
                </div>
                <button 
                  onClick={(e) => props.onDeleteChat(chat.id, e)}
                  class="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500 p-1 transition-all"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
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
