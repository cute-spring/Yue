import type { Accessor, Setter } from 'solid-js';
import type { DocAccess } from '../../types';

type DocumentAccessSectionProps = {
  docAccess: Accessor<DocAccess>;
  docAllowText: Accessor<string>;
  setDocAllowText: Setter<string>;
  docDenyText: Accessor<string>;
  setDocDenyText: Setter<string>;
  isSavingDocAccess: Accessor<boolean>;
  onSave: () => void;
};

export function DocumentAccessSection(props: DocumentAccessSectionProps) {
  return (
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
          onClick={props.onSave}
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
  );
}
