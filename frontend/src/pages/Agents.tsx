import { createMemo, createSignal, For, Show, onMount, onCleanup } from 'solid-js';
import { useAgentsState } from '../hooks/useAgentsState';
import { SmartGenerateModal } from '../components/SmartGenerateModal';
import { ConfirmModal } from '../components/ConfirmModal';
import { AgentCard } from '../components/AgentCard';
import { AgentForm } from '../components/AgentForm';

export default function Agents() {
  const state = useAgentsState();
  const [confirmDeleteId, setConfirmDeleteId] = createSignal<string | null>(null);
  const [searchQuery, setSearchQuery] = createSignal("");
  const [showScrollTop, setShowScrollTop] = createSignal(false);
  let mainContentEl: HTMLElement | null = null;

  const filteredAgents = createMemo(() => {
    const query = searchQuery().toLowerCase().trim();
    if (!query) return state.agents();
    return state.agents().filter(agent => {
      const haystack = [
        agent.name,
        agent.system_prompt,
        agent.provider,
        agent.model,
        ...(agent.enabled_tools || [])
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  });

  const handleScroll = () => {
    const target = mainContentEl;
    if (!target) return;
    setShowScrollTop(target.scrollTop > 300);
  };

  const scrollToTop = () => {
    if (mainContentEl) {
      mainContentEl.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  onMount(() => {
    mainContentEl = document.getElementById('main-content');
    if (mainContentEl) {
      mainContentEl.addEventListener('scroll', handleScroll, { passive: true });
      setShowScrollTop(mainContentEl.scrollTop > 300);
    }
  });

  onCleanup(() => {
    if (mainContentEl) {
      mainContentEl.removeEventListener('scroll', handleScroll);
    }
  });

  return (
    <div class="max-w-7xl mx-auto p-4 md:p-8 relative">
      <div class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
        <div class="space-y-1">
          <h2 class="text-4xl font-black text-gray-900 tracking-tight">Agents</h2>
          <p class="text-gray-500 text-lg">Configure specialized AI assistants with specific tools and search scopes</p>
        </div>
        
        <div class="flex flex-wrap items-center gap-3">
          <div class="relative group">
            <input 
              type="text" 
              placeholder="Search agents..." 
              aria-label="Search agents"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
              class="pl-10 pr-9 py-2.5 bg-gray-100 border-transparent focus:bg-white focus:border-black focus:ring-0 rounded-xl transition-all w-full md:w-64 text-sm font-medium"
            />
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-black transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <Show when={searchQuery().trim().length > 0}>
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => setSearchQuery("")}
                class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-200/70 transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </Show>
          </div>

          <button 
            onClick={state.openCreate}
            class="bg-black text-white px-6 py-2.5 rounded-xl font-bold hover:bg-gray-800 transition-all shadow-lg shadow-gray-200 flex items-center justify-center gap-2 transform active:scale-95 whitespace-nowrap"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Create Agent
          </button>
        </div>
      </div>

      <SmartGenerateModal
        showSmartGenerate={state.showSmartGenerate()}
        setShowSmartGenerate={state.setShowSmartGenerate}
        smartDraft={state.smartDraft}
        setSmartDraft={state.setSmartDraft}
        smartDescription={state.smartDescription}
        setSmartDescription={state.setSmartDescription}
        smartUpdateTools={state.smartUpdateTools}
        setSmartUpdateTools={state.setSmartUpdateTools}
        smartIsGenerating={state.smartIsGenerating}
        smartError={state.smartError}
        smartApplyName={state.smartApplyName}
        setSmartApplyName={state.setSmartApplyName}
        smartApplyPrompt={state.smartApplyPrompt}
        setSmartApplyPrompt={state.setSmartApplyPrompt}
        smartApplyTools={state.smartApplyTools}
        setSmartApplyTools={state.setSmartApplyTools}
        smartPromptLint={state.smartPromptLint}
        smartRiskSummary={state.smartRiskSummary}
        runSmartGenerate={state.runSmartGenerate}
        applySmartDraft={state.applySmartDraft}
      />

      <Show when={state.isEditing()}>
        <div
          class="fixed inset-0 z-[1100] bg-black/45 backdrop-blur-sm p-4 md:p-8 overflow-y-auto"
          onClick={() => state.setIsEditing(false)}
        >
          <div class="min-h-full flex items-start md:items-center justify-center">
            <div class="w-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
              <AgentForm {...state} />
            </div>
          </div>
        </div>
      </Show>

      <div class="flex items-center justify-between text-xs text-gray-500 mb-4">
        <span>{filteredAgents().length} agents</span>
        <Show when={searchQuery().trim().length > 0}>
          <span>Filtered by "{searchQuery().trim()}"</span>
        </Show>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-12">
        <For each={filteredAgents()} fallback={
          <div class="col-span-full py-20 text-center animate-in fade-in duration-500">
            <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 class="text-xl font-bold text-gray-900">No agents found</h3>
            <p class="text-gray-500 mt-2">Try adjusting your search query or create a new agent.</p>
          </div>
        }>
          {agent => (
            <div class="animate-in fade-in slide-in-from-bottom-4 duration-300">
              <AgentCard
                agent={agent}
                onEdit={state.openEdit}
                onDelete={(id) => setConfirmDeleteId(id)}
              />
            </div>
          )}
        </For>
      </div>

      <Show when={showScrollTop() && !state.isEditing()}>
        <button 
          onClick={scrollToTop}
          class="fixed bottom-8 right-8 p-3 bg-black text-white rounded-full shadow-2xl hover:bg-gray-800 transition-all transform hover:-translate-y-1 active:scale-95 z-50 group"
          title="Scroll to Top"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 group-hover:animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      </Show>

      <ConfirmModal
        show={!!confirmDeleteId()}
        title="Delete Agent"
        message="Are you sure you want to delete this agent? This action cannot be undone."
        confirmText="Delete Agent"
        cancelText="Keep Agent"
        type="danger"
        onConfirm={() => {
          const id = confirmDeleteId();
          if (id) {
            state.handleDelete(id);
            setConfirmDeleteId(null);
          }
        }}
        onCancel={() => setConfirmDeleteId(null)}
      />
    </div>
  );
}
