import { For, Show } from 'solid-js';
import { useAgentsState } from '../hooks/useAgentsState';
import { SmartGenerateModal } from '../components/SmartGenerateModal';
import { AgentCard } from '../components/AgentCard';
import { AgentForm } from '../components/AgentForm';

export default function Agents() {
  const state = useAgentsState();

  return (
    <div class="max-w-7xl mx-auto p-4 md:p-8">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
        <div>
          <h2 class="text-3xl font-black text-gray-900 tracking-tight">Agents</h2>
          <p class="text-gray-500 mt-1">Configure specialized AI assistants with specific tools and search scopes</p>
        </div>
        <button 
          onClick={state.openCreate}
          class="bg-black text-white px-6 py-3 rounded-xl font-bold hover:bg-gray-800 transition-all shadow-lg shadow-gray-200 flex items-center justify-center gap-2 transform active:scale-95"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Create Agent
        </button>
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
        <AgentForm {...state} />
      </Show>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        <For each={state.agents()}>
          {agent => (
            <AgentCard
              agent={agent}
              onEdit={state.openEdit}
              onDelete={state.handleDelete}
            />
          )}
        </For>
      </div>
    </div>
  );
}
