import type { FeatureFlags, Preferences } from '../pages/settings/types';

const PREFERENCES_CACHE_KEY = 'yue_cached_preferences';
const PREFERENCES_UPDATED_EVENT = 'yue:preferences-updated';
const FEATURE_FLAGS_CACHE_KEY = 'yue_cached_feature_flags';
const FEATURE_FLAGS_UPDATED_EVENT = 'yue:feature-flags-updated';

export const readCachedPreferences = (): Preferences | null => {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(PREFERENCES_CACHE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Preferences;
  } catch {
    return null;
  }
};

export const publishPreferencesUpdate = (prefs: Preferences): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(PREFERENCES_CACHE_KEY, JSON.stringify(prefs));
  window.dispatchEvent(new CustomEvent<Preferences>(PREFERENCES_UPDATED_EVENT, { detail: prefs }));
};

export const subscribeToPreferencesUpdates = (
  handler: (prefs: Preferences) => void,
): (() => void) => {
  if (typeof window === 'undefined') return () => {};
  const listener = (event: Event) => {
    const customEvent = event as CustomEvent<Preferences>;
    if (customEvent.detail) {
      handler(customEvent.detail);
    }
  };
  window.addEventListener(PREFERENCES_UPDATED_EVENT, listener as EventListener);
  return () => {
    window.removeEventListener(PREFERENCES_UPDATED_EVENT, listener as EventListener);
  };
};

export const readCachedFeatureFlags = (): FeatureFlags | null => {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(FEATURE_FLAGS_CACHE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as FeatureFlags;
  } catch {
    return null;
  }
};

export const publishFeatureFlagsUpdate = (flags: FeatureFlags): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(FEATURE_FLAGS_CACHE_KEY, JSON.stringify(flags));
  window.dispatchEvent(new CustomEvent<FeatureFlags>(FEATURE_FLAGS_UPDATED_EVENT, { detail: flags }));
};

export const subscribeToFeatureFlagsUpdates = (
  handler: (flags: FeatureFlags) => void,
): (() => void) => {
  if (typeof window === 'undefined') return () => {};
  const listener = (event: Event) => {
    const customEvent = event as CustomEvent<FeatureFlags>;
    if (customEvent.detail) {
      handler(customEvent.detail);
    }
  };
  window.addEventListener(FEATURE_FLAGS_UPDATED_EVENT, listener as EventListener);
  return () => {
    window.removeEventListener(FEATURE_FLAGS_UPDATED_EVENT, listener as EventListener);
  };
};
