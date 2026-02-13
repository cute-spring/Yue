import { createSignal, For, Show } from 'solid-js';
import { Message } from '../types';
import { renderMarkdown } from '../utils/markdown';
import { parseThoughtAndContent } from '../utils/thoughtParser';

interface MessageItemProps {
  msg: Message;
  index: number;
  activeAgentName: string;
  isTyping: boolean;
  expandedThoughts: Record<number, boolean>;
  toggleThought: (index: number) => void;
  elapsedTime: number;
  copiedMessageIndex: number | null;
  copyUserMessage: (content: string, index: number) => void;
  quoteUserMessage: (content: string) => void;
  handleRegenerate: (index: number) => void;
  renderThought: (thought: string | null) => any;
  renderMetaBadges: (msg: Message, index: number) => any;
}

export default function MessageItem(props: MessageItemProps) {
  return (
    <div class={`flex flex-col gap-2 ${props.msg.role === 'user' ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
      <div class="flex items-center gap-2 px-1">
        <div class={`w-5 h-5 rounded-full flex items-center justify-center border ${props.msg.role === 'user' ? 'border-text-secondary/20 bg-text-secondary/10 text-text-secondary/60' : 'border-primary/30 bg-primary/10 text-primary/70'}`}>
          <Show when={props.msg.role === 'user'}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.761 0 5-2.239 5-5s-2.239-5-5-5-5 2.239-5 5 2.239 5 5 5zm0 2c-3.333 0-10 1.667-10 5v3h20v-3c0-3.333-6.667-5-10-5z"/>
            </svg>
          </Show>
          <Show when={props.msg.role !== 'user'}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a8 8 0 00-8 8v2a8 8 0 0016 0v-2a8 8 0 00-8-8zm0 3a3 3 0 110 6 3 3 0 010-6zm-6 9.2a6 6 0 0112 0A6.98 6.98 0 0112 20a6.98 6.98 0 01-6-5.8z"/>
            </svg>
          </Show>
        </div>
        <span class={`text-[10px] font-black uppercase tracking-[0.24em] ${props.msg.role === 'user' ? 'text-text-secondary/50' : 'text-primary/70'}`}>
          {props.msg.role === 'user' ? 'You' : props.activeAgentName}
        </span>
      </div>
      <div class={`group relative max-w-[85%] lg:max-w-[75%] ${
        props.msg.role === 'user' 
          ? 'bg-surface text-text-primary px-6 py-4 shadow-sm border border-primary/20 rounded-[26px] rounded-br-none overflow-hidden' 
          : 'bg-surface text-text-primary border border-border/50 px-6 py-5 shadow-sm rounded-[24px] rounded-bl-none'
      }`}>
        {props.msg.role === 'user' ? (
           <>
             <div class="absolute inset-0 pointer-events-none overflow-hidden">
               <div class="absolute -top-24 -left-24 w-72 h-72 rounded-full bg-primary/10 blur-3xl"></div>
               <div class="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-primary/5 blur-3xl"></div>
               <div class="absolute inset-0 bg-[linear-gradient(135deg,rgba(16,185,129,0.10),transparent_55%,rgba(16,185,129,0.06))]"></div>
             </div>
             <Show when={props.msg.images && props.msg.images.length > 0}>
               <div class="flex flex-wrap gap-2 mb-2 relative z-10">
                 <For each={props.msg.images}>
                   {(img) => (
                     <img src={img} class="max-w-full h-auto max-h-64 rounded-lg border border-white/10" alt="User upload" />
                   )}
                 </For>
               </div>
             </Show>
             <div class="relative whitespace-pre-wrap leading-relaxed font-medium text-[15px] select-text">{props.msg.content}</div>
             <div class="mt-3 flex justify-end">
               <div class="flex items-center gap-1 p-1 rounded-2xl bg-surface/70 backdrop-blur-md ring-1 ring-border/70 shadow-sm transition-opacity opacity-100 lg:opacity-0 lg:group-hover:opacity-100">
                 <button
                   class={`p-1.5 rounded-xl transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                     props.copiedMessageIndex === props.index
                       ? 'text-emerald-500 bg-emerald-500/10'
                       : 'text-text-secondary/70 hover:text-primary hover:bg-primary/10'
                   }`}
                   title={props.copiedMessageIndex === props.index ? "Copied" : "Copy"}
                   aria-label="Copy message"
                   onClick={() => props.copyUserMessage(props.msg.content, props.index)}
                 >
                   <Show
                     when={props.copiedMessageIndex === props.index}
                     fallback={
                       <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                       </svg>
                     }
                   >
                     <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                       <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                     </svg>
                   </Show>
                 </button>
                 <button
                   class="p-1.5 rounded-xl text-text-secondary/70 hover:text-primary hover:bg-primary/10 transition-all active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                   title="Quote"
                   aria-label="Quote message"
                   onClick={() => props.quoteUserMessage(props.msg.content)}
                 >
                   <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                     <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l5 5m-5-5l5-5" />
                   </svg>
                 </button>
               </div>
             </div>
           </>
        ) : (
          (() => {
            const { thought, content, isThinking } = parseThoughtAndContent(props.msg.content);
            return (
              <>
                <Show when={thought}>
                  <div class="mb-4 rounded-2xl border border-border/40 bg-background/40 overflow-hidden group/thought transition-all duration-300 hover:border-primary/20 hover:shadow-sm">
                    <button 
                      onClick={() => props.toggleThought(props.index)}
                      class="w-full flex items-center justify-between px-5 py-3.5 hover:bg-primary/5 transition-all group/btn"
                    >
                      <div class="flex items-center gap-3">
                        <div class="relative flex items-center justify-center w-5 h-5">
                          <Show when={isThinking}>
                            <div class="absolute inset-0 bg-primary/10 rounded-full animate-ping"></div>
                            <div class="absolute inset-0.5 border border-primary/20 rounded-full animate-[spin_3s_linear_infinite]"></div>
                          </Show>
                          <div class={`relative w-2 h-2 rounded-full transition-all duration-700 ${isThinking ? 'bg-primary shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-text-secondary/30'}`}></div>
                        </div>
                        <div class="flex items-center gap-2">
                          <span class="text-[13px] font-medium text-text-secondary">
                            {isThinking ? 'Thinking Process' : 'Reasoning Chain'}
                          </span>
                          <span class="text-[11px] font-mono text-text-secondary/40">
                            {props.msg.thought_duration 
                              ? `${props.msg.thought_duration < 60 ? props.msg.thought_duration.toFixed(1) + 's' : Math.floor(props.msg.thought_duration / 60) + 'm ' + (props.msg.thought_duration % 60).toFixed(0) + 's'}`
                              : (isThinking ? `${props.elapsedTime.toFixed(1)}s` : '')}
                          </span>
                        </div>
                      </div>
                      <div class={`p-1 rounded-md transition-all duration-300 ${props.expandedThoughts[props.index] ? 'bg-black/5 text-text-primary' : 'text-text-secondary/40'}`}>
                        <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 transition-transform duration-300 ${props.expandedThoughts[props.index] ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                          <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                      </div>
                    </button>
                    <div 
                      class={`transition-all duration-300 ease-in-out overflow-hidden ${
                        props.expandedThoughts[props.index] ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <div class="px-6 py-4 text-[13px] text-text-secondary/80 leading-relaxed overflow-y-auto max-h-[500px] border-t border-border/5 bg-black/5 dark:bg-black/10">
                        {props.renderThought(thought)}
                      </div>
                    </div>
                  </div>
                </Show>
                
                <Show when={content || (props.isTyping && !thought)}>
                  <div 
                    innerHTML={renderMarkdown(content)} 
                    class="prose prose-slate dark:prose-invert max-w-none 
                      prose-p:leading-relaxed prose-p:my-3 prose-p:text-[15px]
                      prose-headings:text-text-primary prose-headings:font-black prose-headings:tracking-tight
                      prose-a:text-primary prose-a:font-bold hover:prose-a:text-primary-hover prose-a:no-underline border-b border-transparent hover:border-primary
                      prose-strong:text-text-primary prose-strong:font-bold
                      prose-code:text-primary prose-code:bg-primary/5 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none prose-code:font-bold
                      prose-pre:p-0 prose-pre:bg-transparent
                      prose-ol:my-4 prose-ul:my-4 prose-li:my-1
                      prose-table:w-full prose-table:border-collapse prose-table:my-6
                      prose-th:bg-primary/5 prose-th:text-primary prose-th:p-3 prose-th:text-left prose-th:text-xs prose-th:font-black prose-th:uppercase prose-th:tracking-wider prose-th:border prose-th:border-border/60
                      prose-td:p-3 prose-td:text-sm prose-td:border prose-td:border-border/60 prose-td:text-text-secondary" 
                  />
                </Show>

                <Show when={(props.msg.citations?.length ?? 0) > 0}>
                  <details class="mt-5 -mx-2 rounded-2xl border border-border/50 bg-black/5 dark:bg-white/5 px-4 py-3">
                    <summary class="cursor-pointer text-xs font-black uppercase tracking-[0.2em] text-text-secondary/70">
                      Sources ({props.msg.citations?.length ?? 0})
                    </summary>
                    <div class="mt-3 space-y-2">
                      <For each={props.msg.citations || []}>
                        {(c) => (
                          <div class="rounded-xl border border-border/40 bg-surface/60 px-3 py-2">
                            <div class="text-xs font-mono text-text-secondary">
                              {(() => {
                                const path = typeof c?.path === 'string' ? c.path : '';
                                const startLine = typeof c?.start_line === 'number' ? c.start_line : null;
                                const endLine = typeof c?.end_line === 'number' ? c.end_line : null;
                                const startPage = typeof c?.start_page === 'number' ? c.start_page : null;
                                const endPage = typeof c?.end_page === 'number' ? c.end_page : null;
                                if (path && startLine !== null && endLine !== null) return `${path}#L${startLine}-L${endLine}`;
                                if (path && startPage !== null && endPage !== null) return `${path}#P${startPage}-P${endPage}`;
                                return path || 'Unknown source';
                              })()}
                            </div>
                            <Show when={typeof c?.snippet === 'string' && c.snippet.trim().length > 0}>
                              <pre class="mt-2 text-[12px] leading-relaxed whitespace-pre-wrap font-mono text-text-secondary/80 max-h-56 overflow-auto">{c.snippet}</pre>
                            </Show>
                          </div>
                        )}
                      </For>
                    </div>
                  </details>
                </Show>
              </>
            );
          })()
        )}
        
        <Show when={props.isTyping && props.index === 0}>
          <span class="inline-block w-2.5 h-5 ml-1 bg-primary/30 animate-pulse align-middle rounded-sm shadow-[0_0_8px_rgba(16,185,129,0.3)]"></span>
        </Show>

        <Show when={props.msg.role === 'assistant' && (!props.isTyping || props.index !== 0)}>
          <div class="flex items-center gap-1 mt-3 -ml-2">
            <button 
              class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
              title="Copy" 
              onClick={() => navigator.clipboard.writeText(props.msg.content)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
            </button>
            <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Read Aloud">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
               </svg>
            </button>
             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Download">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
               </svg>
            </button>
             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="Share">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
               </svg>
            </button>
             <button class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" title="More">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
               </svg>
            </button>
            
            <div class="h-4 w-[1px] bg-border/50 mx-1"></div>
            
            <button 
              class="p-1.5 text-text-secondary/40 hover:text-primary hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition-all" 
              title="Regenerate" 
              onClick={() => props.handleRegenerate(props.index)}
            >
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
               </svg>
            </button>
          </div>
        </Show>
        {props.renderMetaBadges(props.msg, props.index)}
      </div>
    </div>
  );
}
