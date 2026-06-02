import { publishFeatureFlagsUpdate, publishPreferencesUpdate } from '../../utils/preferencesSync';
import { normalizeFeatureFlags, normalizePreferences } from './types';
import type { DocAccess, FeatureFlags, Preferences } from './types';
import { splitRootsText } from './settingsUtils';

type Accessor<T> = () => T;
type Setter<T> = (value: T | ((prev: T) => T)) => unknown;

type ToastFn = (
  type: 'success' | 'error',
  message: string,
  actionLabel?: string,
  action?: () => void,
) => void;

type UseSettingsGeneralOptions = {
  prefs: Accessor<Preferences>;
  setPrefs: Setter<Preferences>;
  featureFlags: Accessor<FeatureFlags>;
  setFeatureFlags: Setter<FeatureFlags>;
  docAllowText: Accessor<string>;
  setDocAllowText: Setter<string>;
  docDenyText: Accessor<string>;
  setDocDenyText: Setter<string>;
  setDocAccess: Setter<DocAccess>;
  setIsSavingDocAccess: Setter<boolean>;
  showToast: ToastFn;
};

export function useSettingsGeneral(options: UseSettingsGeneralOptions) {
  const savePrefs = async (nextPrefs?: Preferences) => {
    const payload = normalizePreferences(nextPrefs ?? options.prefs());
    options.setPrefs(payload);
    await fetch('/api/config/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    publishPreferencesUpdate(payload);
    options.showToast('success', 'Preferences saved');
  };

  const saveDocAccess = async () => {
    options.setIsSavingDocAccess(true);
    try {
      const allow = splitRootsText(options.docAllowText());
      const deny = splitRootsText(options.docDenyText());
      const res = await fetch('/api/config/doc_access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allow_roots: allow, deny_roots: deny }),
      });
      if (!res.ok) {
        options.showToast('error', 'Failed to save document access');
        return;
      }
      const docAccess = (await res.json()) as DocAccess;
      options.setDocAccess(docAccess);
      options.setDocAllowText((docAccess.allow_roots || []).join('\n'));
      options.setDocDenyText((docAccess.deny_roots || []).join('\n'));
      options.showToast('success', 'Document access saved');
    } finally {
      options.setIsSavingDocAccess(false);
    }
  };

  const saveFeatureFlags = async (nextFlags?: FeatureFlags) => {
    const payload = nextFlags ?? options.featureFlags();
    options.setFeatureFlags(payload);
    const res = await fetch('/api/config/feature_flags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      options.showToast('error', 'Failed to save feature flags');
      return;
    }
    const saved = await res.json();
    const normalized = normalizeFeatureFlags(saved);
    options.setFeatureFlags(normalized);
    publishFeatureFlagsUpdate(normalized);
    options.showToast('success', 'Feature flags saved');
  };

  return {
    savePrefs,
    saveDocAccess,
    saveFeatureFlags,
  };
}
