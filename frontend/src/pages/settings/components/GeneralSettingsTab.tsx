import { For, type Accessor, type Setter } from 'solid-js';
import type { Agent, DocAccess, Preferences } from '../types';

type GeneralSettingsTabProps = {
  prefs: Accessor<Preferences>;
  setPrefs: Setter<Preferences>;
  agents: Accessor<Agent[]>;
  savePrefs: (prefs?: Preferences) => void;
  docAccess: Accessor<DocAccess>;
  docAllowText: Accessor<string>;
  setDocAllowText: Setter<string>;
  docDenyText: Accessor<string>;
  setDocDenyText: Setter<string>;
  isSavingDocAccess: Accessor<boolean>;
  saveDocAccess: () => void;
};

export function GeneralSettingsTab(props: GeneralSettingsTabProps) {
  const savePreferences = (event: SubmitEvent) => {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const formData = new FormData(form);
    const next: Preferences = {
      theme: String(formData.get('theme') || props.prefs().theme),
      language: String(formData.get('language') || props.prefs().language),
      default_agent: String(formData.get('default_agent') || props.prefs().default_agent),
    };

    props.setPrefs(next);
    props.savePrefs(next);
  };

  return (
    <div class="max-w-2xl space-y-6">
      <form class="grid gap-4" onSubmit={savePreferences}>
        <h3 class="text-xl font-semibold border-b pb-2">User Preferences</h3>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Theme</label>
          <select
            data-testid="settings-theme-select"
            name="theme"
            class="w-full border rounded-lg p-2 bg-gray-50"
          >
            <option value="light" selected={props.prefs().theme === 'light'}>
              Light
            </option>
            <option value="dark" selected={props.prefs().theme === 'dark'}>
              Dark
            </option>
            <option value="system" selected={props.prefs().theme === 'system'}>
              System
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Language</label>
          <select
            data-testid="settings-language-select"
            name="language"
            class="w-full border rounded-lg p-2 bg-gray-50"
          >
            <option value="en" selected={props.prefs().language === 'en'}>
              English
            </option>
            <option value="zh" selected={props.prefs().language === 'zh'}>
              Chinese
            </option>
          </select>
        </div>
        <div>
          <div class="flex items-center justify-between gap-3 mb-1">
            <label class="block text-sm font-medium text-gray-700">Default Agent</label>
            <a href="/agents" class="text-emerald-600 hover:underline text-sm font-medium">
              Manage agents →
            </a>
          </div>
          <select
            data-testid="settings-default-agent-select"
            name="default_agent"
            class="w-full border rounded-lg p-2 bg-gray-50"
          >
            <For each={props.agents()}>
              {(a) => (
                <option value={a.id} selected={props.prefs().default_agent === a.id}>
                  {a.name}
                </option>
              )}
            </For>
          </select>
        </div>
        <div>
          <button
            data-testid="settings-save-preferences"
            type="submit"
            class="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-md"
          >
            Save Preferences
          </button>
        </div>
      </form>

      <div class="pt-6 border-t">
        <h3 class="text-xl font-semibold border-b pb-2">Document Access</h3>
        <p class="text-sm text-gray-500 mt-2">
          Configure allow/deny roots for local document read/search tools.
        </p>
        <div class="grid gap-4 mt-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Allow Roots (one per line)</label>
            <textarea
              data-testid="settings-doc-allow-textarea"
              class="w-full border rounded-lg p-3 bg-gray-50 font-mono text-xs h-32"
              value={props.docAllowText()}
              onInput={(e) => props.setDocAllowText(e.currentTarget.value)}
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Deny Roots (one per line)</label>
            <textarea
              data-testid="settings-doc-deny-textarea"
              class="w-full border rounded-lg p-3 bg-gray-50 font-mono text-xs h-24"
              value={props.docDenyText()}
              onInput={(e) => props.setDocDenyText(e.currentTarget.value)}
            />
          </div>
        </div>
        <div class="mt-4 flex items-center justify-between gap-3">
          <div class="text-xs text-gray-500">
            Active allow roots: {props.docAccess().allow_roots.length} • deny roots:{' '}
            {props.docAccess().deny_roots.length}
          </div>
          <button
            data-testid="settings-save-doc-access"
            onClick={props.saveDocAccess}
            disabled={props.isSavingDocAccess()}
            class={`px-6 py-2 rounded-lg transition-colors shadow-md ${
              props.isSavingDocAccess()
                ? 'bg-gray-300 text-gray-600'
                : 'bg-emerald-600 text-white hover:bg-emerald-700'
            }`}
          >
            {props.isSavingDocAccess() ? 'Saving...' : 'Save Document Access'}
          </button>
        </div>
      </div>
    </div>
  );
}
