import { For, Show, Switch, Match } from 'solid-js';
import MermaidViewer from './MermaidViewer';

interface IntelligencePanelProps {
  showKnowledge: boolean;
  setShowKnowledge: (val: boolean) => void;
  isArtifactExpanded: boolean;
  setIsArtifactExpanded: (val: boolean) => void;
  intelligenceTab: 'notes' | 'graph' | 'actions' | 'preview';
  setIntelligenceTab: (val: 'notes' | 'graph' | 'actions' | 'preview') => void;
  previewContent: { lang: string, content: string } | null;
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
          </Switch>
        </div>
      </div>
    </div>
  );
}
