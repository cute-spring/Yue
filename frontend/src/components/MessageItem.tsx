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
  selectedProvider: string;
  selectedModel: string;
}

export default function MessageItem(props: MessageItemProps) {
  const formatTime = (value?: string) => {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat('en-US', { hour: '2-digit', minute: '2-digit' }).format(date);
  };

  const formatTokenCount = (n: number) => {
    return (n / 1000).toFixed(1) + 'k';
  };

  const responseStatus = (msg: Message) => {
    if (msg.error || (msg.content && msg.content.startsWith("Error:"))) return "Failed";
    if (msg.role === "assistant" && props.isTyping && props.index === 0) return "Generating";
    return "Completed";
  };

  const modelLabel = (msg: Message) => {
    const provider = msg.provider || props.selectedProvider;
    const model = msg.model || props.selectedModel;
    if (provider && model) return `${provider}/${model}`;
    if (model) return model;
    return "Unknown model";
  };

  const renderThought = (thought: string | null) => {
    if (!thought) return null;
    
    let processedThought = thought;
    const protocolTags = [
      { tag: '[目标]', icon: '🎯', color: 'text-blue-500', bg: 'bg-blue-500/10' },
      { tag: '[已知条件]', icon: '📋', color: 'text-amber-500', bg: 'bg-amber-500/10' },
      { tag: '[计划]', icon: '🗺️', color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
      { tag: '[反思]', icon: '🔄', color: 'text-rose-500', bg: 'bg-rose-500/10' },
    ];
    
    protocolTags.forEach(({ tag, icon, color, bg }) => {
      const escapedTag = tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(\\*\\*)?${escapedTag}(\\*\\*)?`, 'g');
      processedThought = processedThought.replace(regex, `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-current/10 ${color} ${bg} font-bold text-[11px] mr-1"><span>${icon}</span><span>${tag}</span></span>`);
    });

    return (
      <div 
        class="prose prose-sm dark:prose-invert max-w-none opacity-90 leading-relaxed font-sans"
        innerHTML={renderMarkdown(processedThought)}
      />
    );
  };

  const renderMetaBadges = (msg: Message) => {
    const isUser = msg.role === 'user';
    const [hoveredMetric, setHoveredMetric] = createSignal<string | null>(null);

    const MetricPopover = (p: { title: string; label: string; value: string | number; icon?: any; description?: string }) => {
      const isVisible = () => hoveredMetric() === p.label;

      return (
        <div 
          class="relative flex items-center"
          onMouseEnter={() => setHoveredMetric(p.label)}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface/50 border border-border/40 text-[10px] font-medium text-text-secondary/80 hover:border-primary/30 hover:bg-primary/5 transition-all duration-200 cursor-default">
            {p.icon}
            <span class="opacity-50 font-bold uppercase tracking-tighter text-[9px]">{p.label}</span>
            <span class="font-semibold text-text-primary/90">{p.value}</span>
          </div>
          
          <div 
            class={`absolute top-full left-1/2 -translate-x-1/2 mt-2 w-48 pointer-events-none transition-all duration-300 ease-out z-[100] ${
              isVisible() ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1'
            }`}
          >
            <div class="bg-white/95 backdrop-blur-xl border border-border/50 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-xl p-3 overflow-hidden">
              <div class="flex items-center gap-2 mb-1.5">
                <div class="p-1.5 rounded-lg bg-primary/10 text-primary">
                  {p.icon}
                </div>
                <div class="font-bold text-[11px] text-text-primary tracking-tight">
                  {p.title}
                </div>
              </div>
              <div class="text-[10px] leading-relaxed text-text-secondary/90 font-medium">
                {p.description}
              </div>
              <div class="mt-2 pt-2 border-t border-border/30 flex justify-between items-center">
                <span class="text-[9px] text-text-secondary/50 font-bold uppercase">{p.label}</span>
                <span class="text-[10px] font-bold text-primary">{p.value}</span>
              </div>
            </div>
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-white/95"></div>
          </div>
        </div>
      );
    };

    return (
      <div class={`mt-4 flex flex-wrap items-center gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-text-secondary/5 border border-border/40 text-[10px] font-medium text-text-secondary/70">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-60"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          {formatTime(msg.timestamp)}
        </div>

        <Show when={!isUser}>
          <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-primary/5 border border-primary/10 text-[10px] font-bold text-primary/80 uppercase tracking-tight shadow-sm shadow-primary/5">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            {modelLabel(msg)}
          </div>

          <div class={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-bold uppercase tracking-tight ${
            responseStatus(msg) === 'Failed' 
              ? 'bg-rose-500/5 border-rose-500/20 text-rose-500' 
              : responseStatus(msg) === 'Generating' 
                ? 'bg-amber-500/5 border-amber-500/20 text-amber-500' 
                : 'bg-emerald-500/5 border-emerald-500/20 text-emerald-500 shadow-sm shadow-emerald-500/5'
          }`}>
            <Show when={responseStatus(msg) === 'Generating'}>
              <div class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
            </Show>
            <Show when={responseStatus(msg) === 'Completed'}>
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
            </Show>
            {responseStatus(msg)}
          </div>

          <div class="flex items-center gap-2">
            <Show when={msg.ttft}>
              <MetricPopover 
                title="First Token Latency"
                label="TTFT"
                value={`${(msg.ttft! / 1000).toFixed(2)}s`}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>}
                description="The time taken from sending the request to receiving the very first token from the model."
              />
            </Show>
            <Show when={msg.total_duration}>
              <MetricPopover 
                title="Generation Time"
                label="Total"
                value={`${(msg.total_duration! / 1000).toFixed(2)}s`}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
                description="The total wall-clock time elapsed for the complete response generation process."
              />
            </Show>
            <Show when={msg.tps}>
              <MetricPopover 
                title="Inference Speed"
                label="TPS"
                value={msg.tps!.toFixed(1)}
                icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="m16 18 6-6-6-6"/><path d="M8 6l-6 6 6 6"/></svg>}
                description="Tokens Per Second: The average speed at which the model generated the text content."
              />
            </Show>
          </div>

          <Show when={msg.prompt_tokens || msg.completion_tokens}>
            <MetricPopover 
              title="Token Consumption"
              label="Usage"
              value={`${formatTokenCount(msg.prompt_tokens ?? 0)}i / ${formatTokenCount(msg.completion_tokens ?? 0)}o`}
              icon={<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-70"><path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7"/><path d="M16 5V3"/><path d="M8 5V3"/><path d="M3 9h18"/><path d="M16 19h6"/><path d="M19 16v6"/></svg>}
              description="Detailed breakdown of input (prompt) tokens and output (generated) tokens used."
            />
          </Show>

          <Show when={msg.citations && msg.citations.length > 0}>
            <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-indigo-500/5 border border-indigo-500/20 text-[10px] font-bold text-indigo-500/80 uppercase tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/><path d="M14 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1 0 2.5 0 5-2 7Z"/></svg>
              {msg.citations?.length} Citations
            </div>
          </Show>

          <Show when={msg.tools && msg.tools.length > 0}>
            <div class="flex items-center gap-1.5 px-2 py-1 rounded-md bg-amber-500/5 border border-amber-500/20 text-[10px] font-bold text-amber-500/80 uppercase tracking-tight">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
              {msg.tools?.length} Tools
            </div>
          </Show>
        </Show>
      </div>
    );
  };

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
                        {renderThought(thought)}
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
        
        <Show when={props.msg.finish_reason === 'length'}>
          <div class="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-[13px] flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Response truncated due to output length limit. Try asking for a shorter summary or continuing from where it left off.</span>
          </div>
        </Show>

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
        {renderMetaBadges(props.msg)}
      </div>
    </div>
  );
}
