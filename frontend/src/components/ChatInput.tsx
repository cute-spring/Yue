import { For, Show } from 'solid-js';
import { Agent, Provider } from '../types';
import ModelSelector from './ModelSelector';

interface ChatInputProps {
  // Agent Selector State
  showAgentSelector: boolean;
  filteredAgents: Agent[];
  selectedIndex: number;
  selectAgent: (agent: Agent) => void;
  
  // Input State
  input: string;
  onInput: (e: any) => void;
  onKeyDown: (e: any) => void;
  onSubmit: (e: Event) => void;
  isTyping: boolean;
  activeAgentName: string;
  textareaRef: (el: HTMLTextAreaElement) => void;
  
  // Model Selector Props
  showLLMSelector: boolean;
  setShowLLMSelector: (show: boolean) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  selectedProvider: string;
  setSelectedProvider: (provider: string) => void;
  providers: Provider[];
  showAllModels: boolean;
  setShowAllModels: (show: boolean) => void;
  isRefreshingModels: boolean;
  setIsRefreshingModels: (refreshing: boolean) => void;
  loadProviders: (refresh?: boolean) => Promise<void>;
  providerStorageKey: string;
  modelStorageKey: string;

  // Deep Thinking
  isDeepThinking: boolean;
  setIsDeepThinking: (val: boolean) => void;

  // Tools
  imageAttachments: File[];
  setImageAttachments: (files: File[]) => void;
  onImageClick: () => void;
  imageInputRef: (el: HTMLInputElement) => void;
}

export default function ChatInput(props: ChatInputProps) {
  return (
    <div class="px-4 pb-6 lg:px-8 bg-transparent">
      <div class="max-w-5xl mx-auto relative">
        <Show when={props.showAgentSelector}>
          <div class="absolute bottom-full left-0 mb-4 w-80 bg-surface border border-border rounded-[24px] shadow-2xl overflow-hidden z-50 animate-in slide-in-from-bottom-4 duration-300 backdrop-blur-xl">
            <div class="bg-primary/5 px-5 py-3 border-b border-border flex items-center justify-between">
              <span class="text-[10px] font-bold text-primary uppercase tracking-[0.2em]">Mention Intelligence Agent</span>
              <span class="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">@</span>
            </div>
            <div class="max-h-72 overflow-y-auto p-2 scrollbar-thin">
              <For each={props.filteredAgents}>
                {(agent, index) => (
                  <button
                    onClick={() => props.selectAgent(agent)}
                    class={`w-full text-left px-4 py-3 flex items-center justify-between rounded-xl transition-all duration-200 ${
                      props.selectedIndex === index() ? 'bg-primary text-white shadow-lg shadow-primary/20 scale-[1.02]' : 'hover:bg-primary/5 text-text-primary'
                    }`}
                  >
                    <div class="flex items-center gap-3">
                      <div class={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${props.selectedIndex === index() ? 'bg-white/20' : 'bg-primary/10 text-primary'}`}>
                        {agent.name.charAt(0)}
                      </div>
                      <div>
                        <span class="font-bold text-sm block">{agent.name}</span>
                        <span class={`text-[10px] block opacity-70 ${props.selectedIndex === index() ? 'text-white' : 'text-text-secondary'}`}>Specialized Intelligence</span>
                      </div>
                    </div>
                    <Show when={props.selectedIndex === index()}>
                      <div class="flex items-center gap-1">
                        <span class="text-[9px] font-black tracking-tighter border border-white/30 px-1 rounded">ENTER</span>
                      </div>
                    </Show>
                  </button>
                )}
              </For>
              <Show when={props.filteredAgents.length === 0}>
                <div class="px-4 py-10 text-center">
                  <div class="text-text-secondary opacity-30 mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <p class="text-sm text-text-secondary italic">No matching agents</p>
                </div>
              </Show>
            </div>
          </div>
        </Show>

        <form onSubmit={props.onSubmit} class="relative">
          <div class={`
            relative bg-surface/80 backdrop-blur-xl border-2 rounded-[28px] transition-all duration-500 p-2 shadow-2xl
            ${props.isTyping ? 'border-primary/40 ring-8 ring-primary/5 shadow-primary/10' : 'border-border focus-within:border-primary/40 focus-within:ring-8 focus-within:ring-primary/5'}
          `}>
            <textarea
              ref={props.textareaRef}
              value={props.input}
              onInput={props.onInput}
              onKeyDown={props.onKeyDown}
              placeholder={`You are chatting with ${props.activeAgentName} now`}
              class="w-full bg-transparent px-6 pt-5 pb-20 focus:outline-none resize-none min-h-[96px] max-h-[400px] overflow-y-auto text-text-primary leading-relaxed text-lg font-medium placeholder:text-text-secondary/30"
              rows={1}
            />
            
            {/* Unified Action Bar */}
            <div class="absolute bottom-4 left-5 right-5 flex items-center justify-between">
              {/* Left Side: Configuration */}
              <div class="flex items-center gap-3">
                <ModelSelector 
                  showLLMSelector={props.showLLMSelector}
                  setShowLLMSelector={props.setShowLLMSelector}
                  selectedModel={props.selectedModel}
                  setSelectedModel={props.setSelectedModel}
                  selectedProvider={props.selectedProvider}
                  setSelectedProvider={props.setSelectedProvider}
                  providers={props.providers}
                  showAllModels={props.showAllModels}
                  setShowAllModels={props.setShowAllModels}
                  isRefreshingModels={props.isRefreshingModels}
                  setIsRefreshingModels={props.setIsRefreshingModels}
                  loadProviders={props.loadProviders}
                  providerStorageKey={props.providerStorageKey}
                  modelStorageKey={props.modelStorageKey}
                />

                {/* Deep Thinking Toggle */}
                <button
                  type="button"
                  onClick={() => props.setIsDeepThinking(!props.isDeepThinking)}
                  class={`flex items-center gap-2.5 px-4 py-2.5 rounded-2xl transition-all active:scale-95 border shadow-sm ${
                    props.isDeepThinking 
                      ? 'bg-primary/10 border-primary/30 text-primary' 
                      : 'bg-background border-border text-text-secondary hover:text-primary hover:bg-primary/5'
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <span class="text-xs font-bold uppercase tracking-wider">Deep Thinking</span>
                </button>
              </div>

              {/* Right Side: Tools + Action */}
              <div class="flex items-center gap-4">
                {/* Tools Group */}
                <div class="flex items-center gap-2">
                  <div class="relative group/tooltip">
                    <button type="button" class="p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Attach files">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                      </svg>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">快速理解总结文件</span>
                      <span class="block text-[11px] text-white/50 mt-1">PDF, Word, Excel, PPT, Code</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                  <div class="relative group/tooltip">
                    <input ref={props.imageInputRef} type="file" accept="image/*" multiple class="hidden" 
                      onChange={e => {
                        const files = Array.from(e.currentTarget.files || []);
                        const maxCount = 10;
                        const maxSize = 10 * 1024 * 1024;
                        const valid = files.filter(f => f.size <= maxSize);
                        if (files.length > maxCount) {
                          alert(`最多选择 ${maxCount} 张图片`);
                        }
                        if (valid.length !== files.length) {
                          alert('部分文件超过 10MB 大小限制，已忽略');
                        }
                        props.setImageAttachments(valid.slice(0, maxCount));
                        e.currentTarget.value = '';
                      }} />
                    <button type="button" class="relative p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Upload images"
                      onClick={props.onImageClick}>
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke-width="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" stroke-width="2" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 15l-5-5L5 21" />
                      </svg>
                      <Show when={props.imageAttachments.length > 0}>
                        <span class="absolute -top-1 -right-1 text-[10px] bg-primary text-white rounded-full px-1.5 py-0.5 border border-background shadow-sm">{props.imageAttachments.length}</span>
                      </Show>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[280px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">上传图片</span>
                      <span class="block text-[11px] text-white/50 mt-1">JPG, PNG (Max 10)</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                  <div class="relative group/tooltip">
                    <button type="button" class="p-3 text-text-secondary hover:text-primary hover:bg-primary/10 rounded-2xl transition-all active:scale-90" aria-label="Voice input">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </button>
                    <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-max max-w-[200px] bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl px-5 py-3 text-xs font-medium text-white whitespace-normal text-center pointer-events-none opacity-0 translate-y-2 group-hover/tooltip:opacity-100 group-hover/tooltip:translate-y-0 transition-all duration-200 z-50">
                      <span class="font-bold text-white/90">Voice Input (Beta)</span>
                      <div class="absolute top-full left-1/2 -translate-x-1/2 -mt-1.5 w-3 h-3 bg-slate-900/95 border-r border-b border-white/10 rotate-45"></div>
                    </div>
                  </div>
                </div>

                <button 
                  type="submit"
                  disabled={!props.isTyping && (!props.input.trim() || !props.selectedModel)}
                  class={`
                    flex items-center justify-center p-4 rounded-2xl transition-all duration-500 shadow-lg
                    ${(props.input.trim() && props.selectedModel) || props.isTyping 
                      ? 'bg-primary text-white hover:bg-primary-hover hover:shadow-primary/30 hover:scale-[1.02] active:scale-95' 
                      : 'bg-border/50 text-text-secondary cursor-not-allowed opacity-50'}
                  `}
                >
                  <Show when={props.isTyping} fallback={
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                    </svg>
                  }>
                    <div class="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  </Show>
                </button>
              </div>
            </div>
          </div>
        </form>

        <Show when={!props.selectedModel}>
          <div class="mt-3 flex items-center justify-center">
            <div class="px-3 py-1.5 rounded-full bg-surface border border-border text-[11px] text-text-secondary font-semibold">
              Select a model to start
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}
