import { type Accessor, createEffect, createSignal } from 'solid-js';

import type { WorkspaceUnderstandingSummary } from '../../../types';

type UseWorkspaceUnderstandingArgs = {
  selectedWorkspaceId: Accessor<string | null>;
};

export function useWorkspaceUnderstanding(args: UseWorkspaceUnderstandingArgs) {
  const [summary, setSummary] = createSignal<WorkspaceUnderstandingSummary | null>(null);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);
  let requestVersion = 0;

  const loadWorkspaceUnderstanding = async (
    workspaceId: string | null = args.selectedWorkspaceId(),
  ): Promise<WorkspaceUnderstandingSummary | null> => {
    const version = ++requestVersion;
    if (!workspaceId) {
      setSummary(null);
      setError(null);
      setLoading(false);
      return null;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/workspaces/${encodeURIComponent(workspaceId)}/understanding`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const next = (await res.json()) as WorkspaceUnderstandingSummary;
      if (version === requestVersion) {
        setSummary(next);
      }
      return next;
    } catch (err) {
      if (version === requestVersion) {
        console.error('Failed to load workspace understanding', err);
        setSummary(null);
        setError(err instanceof Error ? err.message : 'Failed to load workspace understanding');
      }
      return null;
    } finally {
      if (version === requestVersion) {
        setLoading(false);
      }
    }
  };

  createEffect(() => {
    void loadWorkspaceUnderstanding(args.selectedWorkspaceId());
  });

  return {
    workspaceUnderstanding: summary,
    workspaceUnderstandingLoading: loading,
    workspaceUnderstandingError: error,
    refreshWorkspaceUnderstanding: loadWorkspaceUnderstanding,
  };
}
