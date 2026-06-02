import { ChatSidebarChatList } from './chat-sidebar/ChatSidebarChatList';
import { DEFAULT_WIDTH } from './chat-sidebar/sidebarFilters';
import { useChatSidebarState } from './chat-sidebar/useChatSidebarState';
import type { ChatSidebarProps } from './chat-sidebar/types';

export default function ChatSidebar(props: ChatSidebarProps) {
  const state = useChatSidebarState(props);

  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 left-0 bg-white transform transition-all ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showHistory ? 'translate-x-0 opacity-100 shadow-2xl lg:shadow-none border-r border-slate-200' : '-translate-x-full lg:translate-x-0'}
      `}
      style={{ 
        width: props.showHistory ? `${DEFAULT_WIDTH}px` : '0px',
        "transition-duration": '300ms'
      }}
      >
        <div 
          class="h-full flex flex-col bg-white overflow-hidden transition-opacity duration-300"
        style={{ 
          width: `${DEFAULT_WIDTH}px`,
          opacity: props.showHistory ? 1 : 0,
          "pointer-events": props.showHistory ? 'auto' : 'none'
        }}
      >
        <ChatSidebarChatList
          chats={props.chats}
          selectedWorkspaceId={props.selectedWorkspaceId}
          currentChatId={props.currentChatId}
          searchQuery={state.searchQuery()}
          setSearchQuery={state.setSearchQuery}
          groupedChats={state.groupedChats()}
          filteredChatCount={state.filteredChats().length}
          activeFilterCount={state.activeFilterCount()}
          datePreset={state.datePreset()}
          setDatePreset={state.setDatePreset}
          isGroupCollapsed={state.isGroupCollapsed}
          toggleGroup={state.toggleGroup}
          clearFilters={state.clearFilters}
          onLoadChat={props.onLoadChat}
          onGenerateSummary={props.onGenerateSummary}
          onDeleteChat={props.onDeleteChat}
        />
      </div>
      
      {/* Toggle Handle - Fixed width mode, no resize */}
      <div
        class={`absolute top-0 -right-2 w-4 h-full z-50 group hidden lg:block select-none`}
      >
        {/* The interactive handle strip */}
        <div 
          class={`absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 w-1.5 h-24 rounded-full transition-all duration-300 flex items-center justify-center
            bg-slate-200/50 group-hover:bg-primary/40 group-hover:h-32 group-hover:w-2`}
        >
          {/* Action Button (Click to toggle) */}
          <div 
            onClick={(e) => {
              e.stopPropagation();
              props.setShowHistory(!props.showHistory);
            }}
            class="absolute inset-0 cursor-pointer flex items-center justify-center"
            title={props.showHistory ? "Collapse" : "Expand"}
          >
            <div class={`w-5 h-10 bg-white border border-slate-200 rounded-full shadow-md flex items-center justify-center transition-all duration-300 transform 
              ${props.showHistory ? 'opacity-0 group-hover:opacity-100 rotate-0' : 'opacity-100 rotate-180 translate-x-1.5'}`}>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-primary font-bold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" d="M15 19l-7-7 7-7" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
