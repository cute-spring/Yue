import { For, Show, Switch, Match } from 'solid-js';
import MermaidViewer from './MermaidViewer';
import { Message } from '../types';

interface IntelligencePanelProps {
  showKnowledge: boolean;
  setShowKnowledge: (val: boolean) => void;
  isArtifactExpanded: boolean;
  setIsArtifactExpanded: (val: boolean) => void;
  intelligenceTab: 'notes' | 'graph' | 'actions' | 'preview' | 'stats';
  setIntelligenceTab: (val: 'notes' | 'graph' | 'actions' | 'preview' | 'stats') => void;
  previewContent: { lang: string, content: string } | null;
  lastMessage: Message | undefined;
  isMobile: boolean;
}

export default function IntelligencePanel(props: IntelligencePanelProps) {
  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 right-0 bg-surface border-l border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showKnowledge ? (props.isArtifactExpanded ? 'translate-x-0 w-[55vw] opacity-100' : 'translate-x-0 w-[420px] opacity-100') : 'translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
      `}
    >
      <div class={`${props.isArtifactExpanded ? 'w-[55vw]' : 'w-[420px]'} h-full flex flex-col transition-all duration-300`}>
        <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
          <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
            <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            Intelligence Hub
          </h2>
          <div class="flex items-center gap-1">
            <button 
              onClick={() => props.setIsArtifactExpanded(!props.isArtifactExpanded)} 
              class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90"
              title={props.isArtifactExpanded ? "Collapse view" : "Expand view"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {props.isArtifactExpanded 
                  ? <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  : <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                }
              </svg>
            </button>
            <button onClick={() => props.setShowKnowledge(false)} class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Intelligence Tabs */}
        <div class="flex border-b border-border bg-background/50 p-1">
          <button 
            onClick={() => props.setIntelligenceTab('actions')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'actions' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Actions
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('notes')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'notes' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Notes
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('graph')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'graph' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Graph
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('stats')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'stats' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Stats
          </button>
          <Show when={props.previewContent}>
            <button 
              onClick={() => props.setIntelligenceTab('preview')}
              class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'preview' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
            >
              Preview
            </button>
          </Show>
        </div>

        <div class="p-6 space-y-8 overflow-y-auto flex-1 scrollbar-thin">
          <Switch>
            <Match when={props.intelligenceTab === 'preview'}>
              <div class="h-full flex flex-col animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-xs font-black text-text-primary uppercase tracking-[0.2em]">Artifact Preview</h3>
                  <div class="flex gap-2">
                     <span class="text-[10px] font-mono bg-primary/10 text-primary px-2 py-1 rounded">{props.previewContent?.lang}</span>
                  </div>
                </div>
                <div class="flex-1 bg-white rounded-xl overflow-hidden border border-border shadow-sm relative">
                  <Show when={props.previewContent?.lang === 'html' || props.previewContent?.lang === 'xml'}>
                    <iframe 
                      srcdoc={props.previewContent?.content} 
                      class="w-full h-full border-0" 
                      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                    />
                  </Show>
                  <Show when={props.previewContent?.lang === 'svg'}>
                    <div class="w-full h-full flex items-center justify-center p-4 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjgiPgo8cmVjdCB3aWR0aD0iOCIgaGVpZ2h0PSI4IiBmaWxsPSIjZmZmIi8+CjxwYXRoIGQ9Ik0wIDBMOCA4Wk04IDBMMCA4WiIgc3Ryb2tlPSIjZWVlIiBzdHJva2Utd2lkdGg9IjEiLz4KPC9zdmc+')]">
                      <div innerHTML={props.previewContent?.content} />
                    </div>
                  </Show>
                  <Show when={props.previewContent?.lang === 'mermaid'}>
                    <div class="w-full h-full p-4 bg-white overflow-hidden">
                      <MermaidViewer code={props.previewContent?.content || ''} />
                    </div>
                  </Show>
                </div>
              </div>
            </Match>
            <Match when={props.intelligenceTab === 'actions'}>
              <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="relative group">
                  <div class="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-primary/5 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                  <div class="relative bg-surface border border-primary/10 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-[10px] font-black text-primary uppercase tracking-[0.2em] mb-3">Contextual Analysis</h4>
                    <p class="text-[13px] text-text-secondary leading-relaxed font-medium">
                      Monitoring your conversation to extract key entities and research data in real-time.
                    </p>
                  </div>
                </div>
                
                <div class="space-y-5">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em] flex items-center gap-2">
                    <span class="w-1 h-1 bg-text-secondary/40 rounded-full"></span>
                    Suggested Actions
                  </h4>
                  <div class="grid grid-cols-1 gap-3">
                    <For each={[
                      { title: 'Research deep dive', icon: 'M9 5l7 7-7 7' },
                      { title: 'Save to intelligence', icon: 'M5 5h5M5 8h2m6 11H9a2 2 0 01-2-2v-3a2 2 0 012-2h3m5 4V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
                      { title: 'Extract key findings', icon: 'M13 10V3L4 14h7v7l9-11h-7z' }
                    ]}>
                      {(action) => (
                        <button class="text-left px-5 py-4 bg-background border border-border/60 rounded-2xl text-[13px] font-bold text-text-primary hover:border-primary/50 hover:bg-primary/5 transition-all flex items-center justify-between group">
                          <span>{action.title}</span>
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-text-secondary group-hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={action.icon} />
                          </svg>
                        </button>
                      )}
                    </For>
                  </div>
                </div>

                <div class="pt-4 border-t border-border/40">
                  <div class="flex items-center justify-between mb-4">
                    <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Connected Nodes</h4>
                    <span class="text-[9px] font-bold bg-primary/10 text-primary px-2 py-0.5 rounded-full tracking-tighter">0 ACTIVE</span>
                  </div>
                  <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                    <p class="text-xs text-text-secondary/60 font-medium italic">No entities detected yet</p>
                  </div>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'notes'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Related Notes</h4>
                  <button class="text-[10px] font-bold text-primary hover:underline">View All</button>
                </div>
                <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                  <p class="text-xs text-text-secondary/60 font-medium italic">No related notes found</p>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'graph'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Knowledge Graph</h4>
                <div class="aspect-square bg-background/50 border border-border rounded-2xl flex items-center justify-center p-8 text-center">
                  <div>
                    <div class="w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <p class="text-xs text-text-secondary/60 font-medium">Graph visualization will appear here as entities are discovered.</p>
                  </div>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'stats'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Performance Statistics</h4>
                  <Show when={props.lastMessage?.model}>
                    <span class="text-[9px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-full">{props.lastMessage?.model}</span>
                  </Show>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-surface border border-border rounded-2xl p-4 shadow-sm relative overflow-hidden group">
                    <div class="absolute inset-0 bg-primary/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                    <div class="relative">
                      <div class="text-[10px] font-black text-text-secondary uppercase tracking-wider mb-1">Tokens/Sec</div>
                      <div class="text-2xl font-black text-primary leading-none flex items-baseline gap-1">
                        {props.lastMessage?.tps?.toFixed(1) || '0.0'}
                        <span class="text-[10px] text-primary/60 font-bold">TPS</span>
                      </div>
                      {/* Simple visual indicator for TPS */}
                      <div class="mt-2 flex gap-0.5 h-1 items-end">
                        <For each={Array(10).fill(0)}>
                          {(_, i) => (
                            <div 
                              class={`flex-1 rounded-full transition-all duration-500 ${
                                (props.lastMessage?.tps || 0) / 10 > i() ? 'bg-primary' : 'bg-primary/10'
                              }`}
                              style={{ height: `${20 + i() * 8}%` }}
                            ></div>
                          )}
                        </For>
                      </div>
                    </div>
                  </div>
                  <div class="bg-surface border border-border rounded-2xl p-4 shadow-sm relative overflow-hidden group">
                    <div class="absolute inset-0 bg-text-primary/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                    <div class="relative">
                      <div class="text-[10px] font-black text-text-secondary uppercase tracking-wider mb-1">Total Tokens</div>
                      <div class="text-2xl font-black text-text-primary leading-none flex items-baseline gap-1">
                        {props.lastMessage?.total_tokens || '0'}
                        <span class="text-[10px] text-text-secondary/60 font-bold">SUM</span>
                      </div>
                      {/* Mini bar chart placeholder for total */}
                      <div class="mt-2 flex gap-0.5 h-1 items-end">
                         <div class="w-full h-1 bg-text-primary/10 rounded-full overflow-hidden">
                           <div class="h-full bg-text-primary/30 rounded-full" style={{ width: '60%' }}></div>
                         </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="space-y-4 bg-surface border border-border rounded-2xl p-5 shadow-sm relative overflow-hidden group">
                  <div class="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 blur-2xl group-hover:bg-primary/10 transition-colors duration-700"></div>
                  
                  <div class="flex items-center gap-6 relative">
                    {/* Donut Chart for Token Distribution */}
                    <div class="relative w-20 h-20 shrink-0">
                      <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                        <circle cx="18" cy="18" r="16" fill="none" class="stroke-background" stroke-width="3.5"></circle>
                        <circle 
                          cx="18" cy="18" r="16" fill="none" 
                          class="stroke-primary/30" stroke-width="3.5"
                          stroke-dasharray={`${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100} 100`}
                        ></circle>
                        <circle 
                          cx="18" cy="18" r="16" fill="none" 
                          class="stroke-primary" stroke-width="3.5"
                          stroke-dasharray={`${(props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100} 100`}
                          stroke-dashoffset={`-${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}`}
                        ></circle>
                      </svg>
                      <div class="absolute inset-0 flex flex-col items-center justify-center">
                        <span class="text-[10px] font-black text-text-primary leading-none">
                          {Math.round(((props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1)) * 100)}%
                        </span>
                        <span class="text-[7px] font-bold text-text-secondary uppercase tracking-tighter">Out</span>
                      </div>
                    </div>

                    <div class="flex-1 space-y-3">
                      <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px]">
                          <div class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-primary/40"></div>
                            <span class="font-bold text-text-secondary uppercase tracking-wider">Prompt</span>
                          </div>
                          <span class="font-mono text-text-primary">{props.lastMessage?.prompt_tokens || 0}</span>
                        </div>
                        <div class="w-full h-1 bg-background rounded-full overflow-hidden">
                          <div 
                            class="h-full bg-primary/40 rounded-full transition-all duration-1000" 
                            style={{ width: `${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}%` }}
                          />
                        </div>
                      </div>
                      
                      <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px]">
                          <div class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
                            <span class="font-bold text-text-secondary uppercase tracking-wider">Completion</span>
                          </div>
                          <span class="font-mono text-text-primary">{props.lastMessage?.completion_tokens || 0}</span>
                        </div>
                        <div class="w-full h-1 bg-background rounded-full overflow-hidden">
                          <div 
                            class="h-full bg-primary rounded-full transition-all duration-1000" 
                            style={{ width: `${(props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <Show when={props.lastMessage?.finish_reason}>
                  <div class="bg-background/50 border border-border rounded-2xl p-4 flex items-center justify-between">
                    <span class="text-[10px] font-black text-text-secondary uppercase tracking-wider">Finish Reason</span>
                    <span class="text-[10px] font-mono font-bold text-primary uppercase">{props.lastMessage?.finish_reason}</span>
                  </div>
                </Show>

                <Show when={props.lastMessage?.thought_duration}>
                   <div class="bg-background/50 border border-border rounded-2xl p-4 flex items-center justify-between">
                     <span class="text-[10px] font-black text-text-secondary uppercase tracking-wider">Thinking Time</span>
                     <span class="text-[10px] font-mono font-bold text-text-primary">{(props.lastMessage?.thought_duration || 0) / 1000}s</span>
                   </div>
                 </Show>
              </div>
            </Match>
          </Switch>
        </div>
      </div>
    </div>
  );
}
