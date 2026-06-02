import { For, Show } from 'solid-js';
import type { ChatSession } from '../../types';
import { formatChatTime } from './sidebarFilters';
import type { ChatSidebarGroup } from './types';

type ChatSidebarChatListProps = {
  chats: ChatSession[];
  selectedWorkspaceId: string | null;
  currentChatId: string | null;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  groupedChats: ChatSidebarGroup[];
  filteredChatCount: number;
  activeFilterCount: number;
  datePreset: 'all' | 'today' | '7d' | '30d';
  setDatePreset: (value: 'all' | 'today' | '7d' | '30d') => void;
  isGroupCollapsed: (group: ChatSidebarGroup) => boolean;
  toggleGroup: (key: string) => void;
  clearFilters: () => void;
  onLoadChat: (id: string) => void;
  onGenerateSummary: (id: string) => void;
  onDeleteChat: (id: string) => void;
};

export function ChatSidebarChatList(props: ChatSidebarChatListProps) {
  return (
    <>
      <div class="border-b border-slate-200 bg-white">
        <div class="px-4 py-3 border-b border-slate-100">
          <div class="relative">
            <input
              type="text"
              value={props.searchQuery}
              onInput={(e) => props.setSearchQuery(e.currentTarget.value)}
              placeholder="Search chats..."
              class="w-full rounded-lg border border-slate-200 bg-white px-8 py-2 text-xs shadow-sm outline-none transition-all focus:ring-2 focus:ring-primary/20"
            />
            <svg xmlns="http://www.w3.org/2000/svg" class="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <Show when={props.searchQuery}>
              <button
                onClick={() => props.setSearchQuery('')}
                class="absolute right-2.5 top-2.5 text-slate-400 transition-colors hover:text-slate-600"
                title="Clear search"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </Show>
          </div>
        </div>
        <div class="px-4 py-3 bg-white flex gap-2 overflow-x-auto no-scrollbar">
          <button onClick={() => props.setDatePreset('all')} class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${props.datePreset === 'all' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>ALL</button>
          <button onClick={() => props.setDatePreset('today')} class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${props.datePreset === 'today' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>TODAY</button>
          <button onClick={() => props.setDatePreset('7d')} class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${props.datePreset === '7d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>7D</button>
          <button onClick={() => props.setDatePreset('30d')} class={`px-2 py-1 text-[10px] font-bold rounded transition-all whitespace-nowrap shadow-sm ${props.datePreset === '30d' ? 'bg-primary text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>30D</button>
        </div>
      </div>

      <div class="overflow-y-auto flex-1 no-scrollbar bg-white relative">
        <Show when={props.chats.length > 0 && props.activeFilterCount > 0}>
          <div class="px-4 py-2 text-[10px] border-b border-slate-100 bg-slate-50/50 text-slate-500 flex items-center justify-between font-medium">
            <span>{props.filteredChatCount} sessions · {props.activeFilterCount} active</span>
          </div>
        </Show>
        <For each={props.groupedChats}>
          {(group) => (
            <section>
              <button
                onClick={() => props.toggleGroup(group.key)}
                class={`w-full sticky top-0 z-10 px-4 py-2 text-[10px] font-black uppercase tracking-widest border-y flex justify-between items-center ${group.type === 'today' ? 'text-primary border-primary/10 bg-surface/95 backdrop-blur-sm' : 'text-slate-500 border-slate-100 bg-slate-50/90 backdrop-blur-sm'}`}
                aria-expanded={!props.isGroupCollapsed(group)}
                aria-label={`Toggle date group ${group.label}`}
              >
                <span class="flex items-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" class={`w-3 h-3 transition-transform duration-200 ${props.isGroupCollapsed(group) ? 'rotate-90' : 'rotate-0'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7" />
                  </svg>
                  {group.label}
                </span>
                <span class={`px-1.5 py-0.5 rounded text-[9px] ${group.type === 'today' ? 'bg-primary/10 text-primary' : 'bg-slate-200 text-slate-600'}`}>
                  {group.chats.length} {group.chats.length === 1 ? 'chat' : 'chats'}
                </span>
              </button>
              <Show when={!props.isGroupCollapsed(group)}>
                <div class="divide-y divide-slate-50">
                  <For each={group.chats}>
                    {(chat) => (
                      <div
                        class={`px-4 py-3 cursor-pointer group flex justify-between items-start transition-colors relative border-l-4 ${props.currentChatId === chat.id ? 'bg-primary/5 border-l-primary' : 'bg-white border-l-transparent hover:bg-slate-50'}`}
                        onClick={() => props.onLoadChat(chat.id)}
                      >
                        <div class="flex-1 min-w-0">
                          <div class="flex justify-between items-start mb-1">
                            <h3 class={`text-sm truncate pr-2 transition-colors ${props.currentChatId === chat.id ? 'font-bold text-slate-800' : 'font-semibold text-slate-700 group-hover:text-primary'}`}>
                              {chat.title}
                            </h3>
                            <span class="text-[9px] text-slate-400 font-medium whitespace-nowrap shrink-0 pt-0.5">
                              {formatChatTime(chat.updated_at, group.type)}
                            </span>
                          </div>
                          <Show when={chat.summary}>
                            <div class="text-[11px] text-slate-500 line-clamp-1 mb-2">{chat.summary}</div>
                          </Show>
                          <div class="flex flex-wrap gap-1 items-center">
                            <Show when={chat.workspace_id && !props.selectedWorkspaceId}>
                              <span class="px-1.5 py-0.5 text-[9px] font-semibold rounded uppercase tracking-tighter bg-amber-50 text-amber-700 border border-amber-200/70">
                                workspace
                              </span>
                            </Show>
                            <Show when={chat.tags && chat.tags.length > 0}>
                              <For each={(chat.tags || []).slice(0, 3)}>
                                {(tag) => (
                                  <span class="px-1.5 py-0.5 text-[9px] font-semibold rounded uppercase tracking-tighter bg-slate-100 text-slate-500 border border-slate-200/60">
                                    {tag}
                                  </span>
                                )}
                              </For>
                            </Show>
                            <Show when={chat.tags && chat.tags.length > 3}>
                              <span class="px-1.5 py-0.5 bg-slate-100 text-slate-400 border border-slate-200/60 text-[9px] font-semibold rounded">
                                +{chat.tags!.length - 3}
                              </span>
                            </Show>
                          </div>
                        </div>
                        <div class="absolute right-2 bottom-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onGenerateSummary(chat.id);
                            }}
                            class="p-1.5 bg-white text-slate-400 hover:text-primary rounded shadow-sm border border-slate-200"
                            title="Generate summary"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h8M8 14h5M5 6h14a2 2 0 012 2v8a2 2 0 01-2 2H9l-4 3V8a2 2 0 012-2z" />
                            </svg>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              props.onDeleteChat(chat.id);
                            }}
                            class="p-1.5 bg-white text-slate-400 hover:text-rose-500 rounded shadow-sm border border-slate-200"
                            title="Delete session"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    )}
                  </For>
                </div>
              </Show>
            </section>
          )}
        </For>
        <Show when={props.chats.length > 0 && props.filteredChatCount === 0}>
          <div class="p-8 text-center">
            <p class="text-sm text-slate-400 italic mb-3">No chats match your current filters</p>
            <button onClick={props.clearFilters} class="text-xs text-primary font-bold hover:underline active:scale-95 transition-transform inline-block">
              Clear all filters
            </button>
          </div>
        </Show>
        <Show when={props.chats.length === 0}>
          <div class="p-8 text-center text-sm text-slate-400 italic">No recent chats</div>
        </Show>
      </div>
      <div class="p-3 bg-slate-50 border-t border-slate-200 text-center">
        <span class="text-[10px] text-slate-400 font-medium italic">Showing {props.filteredChatCount} sessions</span>
      </div>
    </>
  );
}
