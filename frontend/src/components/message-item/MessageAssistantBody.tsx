import { For, Show } from 'solid-js';
import { Message } from '../../types';
import { renderMarkdown } from '../../utils/markdown';
import ToolCallItem from '../ToolCallItem';
import MessageEvidencePanel from './MessageEvidencePanel';
import { assistantContentMarkdownClass, renderThought } from './helpers';

interface MessageAssistantBodyProps {
  msg: Message;
  content: string;
  thought: string | null;
  isActuallyThinking: boolean;
  thoughtSource?: string | null;
  reasoningEnabled: boolean;
  isThinking: boolean;
  isTyping: boolean;
  waitSecs: number;
  loadingStatus: { title: string; sub: string };
  isCollapsed: boolean;
  expandedThought: boolean;
  visionFeedbackText: string;
  isTruncated: boolean;
  toggleCollapse: () => void;
  toggleThought: () => void;
  onContinue: (msg: Message) => void;
}

export default function MessageAssistantBody(props: MessageAssistantBodyProps) {
  const showInitializing = () => props.isTyping && !props.thought && !props.content && !props.reasoningEnabled;

  return (
    <div class="relative w-full">
      <Show when={props.isCollapsed}>
        <div class="group flex cursor-pointer items-center justify-between py-1" onClick={props.toggleCollapse}>
          <div class="max-w-[85%] truncate text-[14px] font-medium text-text-secondary/70">
            {props.content ? `${props.content.replace(/\n/g, ' ').substring(0, 100)}...` : 'AI Response...'}
          </div>
          <button class="rounded-lg bg-text-secondary/5 p-1.5 text-text-secondary/60 transition-all duration-300 group-hover:bg-primary/10 group-hover:text-primary" title="Expand response">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
        </div>
      </Show>

      <Show when={!props.isCollapsed}>
        <div class="flex w-full flex-col animate-in fade-in duration-300">
          <Show when={showInitializing()}>
            <div class="flex flex-col gap-3 py-1">
              <div class="flex items-center gap-3">
                <div class="relative flex h-5 w-5 items-center justify-center">
                  <div class="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                  <div class="absolute inset-0 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
                  <div class="relative h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary-rgb),0.6)]" />
                </div>
                <span class="animate-pulse text-[11px] font-black uppercase tracking-[0.2em] text-primary/70">
                  {props.loadingStatus.title}
                </span>
              </div>
              <div class="flex items-center gap-1.5 pl-1">
                <div class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-duration:1s]" style="animation-delay: 0ms" />
                <div class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-duration:1s]" style="animation-delay: 200ms" />
                <div class="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-duration:1s]" style="animation-delay: 400ms" />
              </div>
              <div class={`text-[10px] font-medium italic transition-colors duration-500 ${props.waitSecs > 15 ? 'text-amber-500/80' : 'text-text-secondary/40'}`}>
                {props.loadingStatus.sub}
              </div>

              <Show when={props.msg.tools && props.msg.tools.length > 0}>
                <div class="mt-2 flex flex-col gap-1.5 animate-in fade-in slide-in-from-bottom-1 delay-300 duration-700">
                  <div class="flex items-center gap-1.5">
                    <div class="h-1 w-1 rounded-full bg-primary/40" />
                    <span class="text-[9px] font-bold uppercase tracking-wider text-text-secondary/30">Capabilities Ready</span>
                  </div>
                  <div class="flex flex-wrap gap-1.5 pl-2">
                    <For each={props.msg.tools?.slice(0, 5)}>
                      {(tool) => (
                        <div class="flex items-center gap-1 rounded border border-primary/10 bg-primary/5 px-1.5 py-0.5 text-[8px] font-medium text-primary/60">
                          <svg xmlns="http://www.w3.org/2000/svg" width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                          {tool.replace('mcp__', '').replace('builtin:', '').split('__').pop()}
                        </div>
                      )}
                    </For>
                    <Show when={(props.msg.tools?.length || 0) > 5}>
                      <div class="rounded border border-border/20 bg-text-secondary/5 px-1.5 py-0.5 text-[8px] font-medium text-text-secondary/40">
                        +{(props.msg.tools?.length || 0) - 5} more
                      </div>
                    </Show>
                  </div>
                </div>
              </Show>

              <Show when={props.waitSecs > 20}>
                <div class="mt-1 rounded-lg border border-amber-500/10 bg-amber-500/5 px-3 py-1.5 text-[9px] font-bold text-amber-600/70 animate-in fade-in slide-in-from-top-1">
                  ⚠️ The model is taking longer than expected. This can happen with complex reasoning or high server load.
                </div>
              </Show>
            </div>
          </Show>

          <Show when={props.reasoningEnabled && (props.thought || (props.isTyping && !props.content))}>
            <div class="group/thought mb-4 overflow-hidden rounded-xl border border-border/40 bg-background/40 transition-all duration-500 hover:border-primary/30">
              <button
                onClick={props.toggleThought}
                class="group/btn relative flex w-full items-center justify-between overflow-hidden px-4 py-2.5 transition-all hover:bg-primary/[0.03]"
              >
                <Show when={props.isThinking}>
                  <div class="pointer-events-none absolute inset-0 -translate-x-full animate-[shimmer_3s_infinite] bg-gradient-to-r from-transparent via-primary/[0.05] to-transparent" />
                </Show>
                <Show when={props.isTyping}>
                  <div class="absolute bottom-0 left-0 h-[2px] w-full overflow-hidden bg-primary/20">
                    <div class="h-full bg-primary/40 animate-[loading_2s_infinite_ease-in-out]" />
                  </div>
                </Show>

                <div class="relative z-10 flex items-center gap-4">
                  <div class="relative flex h-6 w-6 items-center justify-center">
                    <Show when={props.isThinking}>
                      <div class="absolute inset-[-4px] rounded-full bg-primary/20 animate-ping [animation-duration:2.5s]" />
                      <div class="absolute inset-[-2px] rounded-full bg-primary/10 animate-pulse [animation-duration:1.8s]" />
                      <div class="absolute inset-0 rounded-full border-2 border-primary/20 animate-spin-slow" />
                      <div class="absolute inset-1 rounded-full border-2 border-b-transparent border-l-transparent border-r-transparent border-t-primary animate-spin [animation-duration:0.8s]" />
                    </Show>
                    <div class={`relative h-2.5 w-2.5 rounded-full transition-all duration-1000 ${
                      props.isThinking
                        ? 'scale-110 bg-gradient-to-tr from-primary to-primary shadow-[0_0_15px_rgba(16,185,129,0.8)]'
                        : 'bg-text-secondary/20'
                    }`} />
                  </div>
                  <div class="flex flex-col items-start -space-y-0.5">
                    <div class="flex items-center gap-1.5">
                      <span class={`text-[13px] font-black tracking-wide transition-colors duration-500 ${props.isThinking ? 'text-primary' : 'text-text-secondary'}`}>
                        {props.isThinking
                          ? (props.isActuallyThinking ? 'Thinking & Analyzing' : props.loadingStatus.title)
                          : 'Reasoning Chain'}
                      </span>
                      <Show when={props.thoughtSource === 'structured'}>
                        <div class="rounded border border-primary/20 bg-primary/10 px-1.5 py-0.5" title="Structured reasoning from model API">
                          <span class="text-[8px] font-black uppercase tracking-wider text-primary">Structured</span>
                        </div>
                      </Show>
                    </div>
                    <Show when={props.isThinking}>
                      <span class="tabular-nums text-[9px] font-bold text-primary/40">Elapsed: {props.waitSecs}s</span>
                    </Show>
                    <Show when={!props.isThinking && props.msg.thought_duration !== undefined}>
                      <span class="tabular-nums text-[9px] font-bold text-text-secondary/40">
                        Took: {props.msg.thought_duration?.toFixed(1)}s
                      </span>
                    </Show>
                  </div>
                </div>
                <div class="relative z-10 flex items-center gap-3">
                  <Show when={props.isThinking}>
                    <div class="rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5">
                      <span class="animate-pulse-fast text-[9px] font-black uppercase tracking-[0.15em] text-primary">Live Processing</span>
                    </div>
                  </Show>
                  <div class={`rounded-lg p-1.5 transition-all duration-300 ${props.expandedThought ? 'bg-primary/10 text-primary' : 'bg-black/5 text-text-secondary/40'}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" class={`h-4 w-4 transition-transform duration-500 ${props.expandedThought ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                  </div>
                </div>
              </button>

              <Show when={props.isThinking && !props.isActuallyThinking}>
                <div class="animate-in fade-in slide-in-from-top-1 px-5 pb-4 -mt-1 duration-500">
                  <div class="flex flex-col gap-2 rounded-xl border border-primary/5 bg-primary/[0.02] p-3">
                    <div class="flex items-center gap-2">
                      <div class="flex gap-1">
                        <div class="h-1 w-1 rounded-full bg-primary animate-bounce" style="animation-delay: 0ms" />
                        <div class="h-1 w-1 rounded-full bg-primary animate-bounce" style="animation-delay: 200ms" />
                        <div class="h-1 w-1 rounded-full bg-primary animate-bounce" style="animation-delay: 400ms" />
                      </div>
                      <span class="text-[10px] font-medium italic text-text-secondary/60">{props.loadingStatus.sub}</span>
                    </div>

                    <Show when={props.msg.tools && props.msg.tools.length > 0}>
                      <div class="flex flex-wrap gap-1.5 border-t border-primary/5 pt-1">
                        <For each={props.msg.tools?.slice(0, 3)}>
                          {(tool) => (
                            <div class="rounded bg-primary/5 px-1.5 py-0.5 text-[8px] font-medium text-primary/40">
                              {tool.replace('mcp__', '').replace('builtin:', '').split('__').pop()}
                            </div>
                          )}
                        </For>
                      </div>
                    </Show>
                  </div>
                </div>
              </Show>

              <div class={`overflow-hidden transition-all duration-500 ease-in-out ${props.expandedThought ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'}`}>
                <div class="max-h-[500px] overflow-y-auto border-t border-border/5 bg-gradient-to-b from-black/[0.02] to-transparent px-8 py-6 text-[13.5px] leading-relaxed text-text-secondary/90 dark:from-white/[0.02]">
                  <div class="prose prose-sm max-w-none opacity-80 dark:prose-invert">
                    <div
                      class="prose prose-sm max-w-none opacity-90 leading-relaxed font-sans dark:prose-invert"
                      innerHTML={renderThought(props.thought, props.isTyping) || ''}
                    />
                  </div>
                  <Show when={props.isThinking}>
                    <div class="mt-6 flex items-center gap-3 rounded-xl border border-primary/5 bg-primary/[0.03] p-3 text-xs italic text-primary/70 animate-pulse">
                      <div class="relative flex h-4 w-4">
                        <div class="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                        <div class="absolute inset-1 rounded-full bg-primary/40 animate-pulse" />
                      </div>
                      Exploring knowledge base and synthesizing optimal response...
                    </div>
                  </Show>
                </div>
              </div>
            </div>
          </Show>

          <Show when={props.msg.tool_calls && props.msg.tool_calls.length > 0}>
            <div class="mb-4 space-y-2">
              <div class="mb-1 flex items-center gap-2 px-1">
                <div class="h-3 w-1 rounded-full bg-primary/40" />
                <span class="text-[10px] font-bold uppercase tracking-wider text-text-secondary/40">Tools Execution</span>
              </div>
              <For each={props.msg.tool_calls}>
                {(toolCall) => <ToolCallItem toolCall={toolCall} />}
              </For>
            </div>
          </Show>

          <Show when={props.content || (props.isTyping && !props.thought)}>
            <Show when={props.visionFeedbackText}>
              <div class="mb-3 rounded-xl border border-amber-500/20 bg-amber-500/10 p-3 text-[13px] text-amber-700">
                {props.visionFeedbackText}
              </div>
            </Show>
            <div
              innerHTML={renderMarkdown(props.content, props.isTyping)}
              class={assistantContentMarkdownClass}
            />
          </Show>

          <Show when={props.isTruncated}>
            <div class="mt-4 flex justify-start">
              <button
                onClick={() => props.onContinue(props.msg)}
                class="group flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white shadow-lg shadow-primary/20 transition-all duration-300 hover:-translate-y-0.5 hover:bg-primary/90 active:translate-y-0"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
                继续生成
              </button>
            </div>
          </Show>

          <MessageEvidencePanel msg={props.msg} />
        </div>
      </Show>
    </div>
  );
}
