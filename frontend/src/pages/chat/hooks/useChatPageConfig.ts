import { createSignal, onCleanup, onMount } from 'solid-js';
import { FeatureFlags } from '../../../types';
import { DEFAULT_PREFERENCES, Preferences, normalizeFeatureFlags, normalizePreferences } from '../../settings/types';
import {
  readCachedFeatureFlags,
  readCachedPreferences,
  subscribeToFeatureFlagsUpdates,
  subscribeToPreferencesUpdates,
} from '../../../utils/preferencesSync';

export function useChatPageConfig() {
  const [speechPrefs, setSpeechPrefs] = createSignal<Preferences>(DEFAULT_PREFERENCES);
  const [featureFlags, setFeatureFlags] = createSignal<FeatureFlags>(normalizeFeatureFlags({}));

  onMount(() => {
    const cachedPrefs = readCachedPreferences();
    if (cachedPrefs) {
      setSpeechPrefs(normalizePreferences(cachedPrefs));
    }
    const unsubscribe = subscribeToPreferencesUpdates((prefs) => {
      setSpeechPrefs(normalizePreferences(prefs));
    });
    onCleanup(unsubscribe);
  });

  onMount(() => {
    const cachedFlags = readCachedFeatureFlags();
    if (cachedFlags) {
      setFeatureFlags(normalizeFeatureFlags(cachedFlags));
    }
    const unsubscribe = subscribeToFeatureFlagsUpdates((flags) => {
      setFeatureFlags(normalizeFeatureFlags(flags));
    });
    onCleanup(unsubscribe);
  });

  onMount(async () => {
    try {
      const [preferencesRes, featureFlagsRes] = await Promise.all([
        fetch('/api/config/preferences'),
        fetch('/api/config/feature_flags'),
      ]);
      const raw = await preferencesRes.json();
      setSpeechPrefs(normalizePreferences(raw));

      if (featureFlagsRes.ok) {
        const flags = (await featureFlagsRes.json()) as FeatureFlags;
        setFeatureFlags(normalizeFeatureFlags(flags));
      }
    } catch (e) {
      console.warn('Failed to load chat configuration', e);
    }
  });

  return {
    speechPrefs,
    featureFlags,
  };
}
