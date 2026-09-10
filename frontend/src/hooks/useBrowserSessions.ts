import { createSignal } from 'solid-js';

export type BrowserSession = {
  id: string;
  title: string;
  origin: string;
  status: 'active' | 'paused' | 'disconnected';
  authorization_mode: 'step_confirm' | 'session_auto' | 'site_auto';
  has_snapshot: boolean;
};

export type BrowserAction = {
  id: string;
  action: string;
  target?: string | null;
  status: 'awaiting_approval' | 'queued' | 'dispatched' | 'succeeded' | 'failed' | 'rejected';
};

export type BrowserPolicyOrigin = {
  origin: string;
  purpose: 'business' | 'sso_handoff';
  approved_at: string;
};

export type BrowserOriginRequest = {
  id: string;
  origin: string;
  purpose: 'business' | 'sso_handoff';
  status: 'awaiting_approval' | 'approved' | 'rejected';
};

export function useBrowserSessions() {
  const [sessions, setSessions] = createSignal<BrowserSession[]>([]);
  const [selectedBrowserSessionId, setSelectedBrowserSessionId] = createSignal<string | null>(null);
  const [browserActions, setBrowserActions] = createSignal<BrowserAction[]>([]);
  const [policyOrigins, setPolicyOrigins] = createSignal<BrowserPolicyOrigin[]>([]);

  const refreshBrowserSessions = async () => {
    try {
      const response = await fetch('/api/browser/sessions');
      if (!response.ok) throw new Error('Browser sessions are unavailable.');
      const next = await response.json();
      const active = Array.isArray(next) ? next.filter((item): item is BrowserSession => item?.status === 'active') : [];
      setSessions(active);
      if (selectedBrowserSessionId() && !active.some((item) => item.id === selectedBrowserSessionId())) {
        setSelectedBrowserSessionId(null);
        setBrowserActions([]);
      }
    } catch {
      setSessions([]);
      setSelectedBrowserSessionId(null);
      setBrowserActions([]);
    }
  };

  const refreshBrowserActions = async () => {
    const sessionId = selectedBrowserSessionId();
    if (!sessionId) {
      setBrowserActions([]);
      return;
    }
    try {
      const response = await fetch(`/api/browser/sessions/${sessionId}/actions`);
      if (!response.ok) throw new Error('Browser actions are unavailable.');
      const next = await response.json();
      setBrowserActions(Array.isArray(next) ? next : []);
    } catch {
      setBrowserActions([]);
    }
  };

  const decideBrowserAction = async (actionId: string, approved: boolean) => {
    const sessionId = selectedBrowserSessionId();
    if (!sessionId) return;
    const response = await fetch(`/api/browser/sessions/${sessionId}/actions/${actionId}/decision`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ approved }),
    });
    if (!response.ok) throw new Error('Could not update browser action approval.');
    await refreshBrowserActions();
  };

  const refreshPolicyOrigins = async () => {
    const response = await fetch('/api/browser/policy/origins');
    if (!response.ok) throw new Error('Browser origin policy is unavailable.');
    const next = await response.json();
    setPolicyOrigins(Array.isArray(next) ? next : []);
  };

  const requestPolicyOrigin = async (origin: string, purpose: BrowserOriginRequest['purpose']) => {
    const response = await fetch('/api/browser/policy/origin-requests', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ origin, purpose }),
    });
    if (!response.ok) throw new Error('Could not prepare browser origin approval.');
    return response.json() as Promise<BrowserOriginRequest>;
  };

  const decidePolicyOrigin = async (requestId: string, approved: boolean) => {
    const response = await fetch(`/api/browser/policy/origin-requests/${requestId}/decision`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ approved }),
    });
    if (!response.ok) throw new Error('Could not update browser origin policy.');
    if (approved) await refreshPolicyOrigins();
    return response.json() as Promise<BrowserOriginRequest>;
  };

  const revokePolicyOrigin = async (origin: string) => {
    const response = await fetch(`/api/browser/policy/origins/${encodeURIComponent(origin)}`, { method: 'DELETE' });
    if (!response.ok) throw new Error('Could not revoke browser origin.');
    await refreshPolicyOrigins();
  };

  return {
    sessions,
    selectedBrowserSessionId,
    setSelectedBrowserSessionId,
    browserActions,
    policyOrigins,
    refreshBrowserSessions,
    refreshBrowserActions,
    decideBrowserAction,
    refreshPolicyOrigins,
    requestPolicyOrigin,
    decidePolicyOrigin,
    revokePolicyOrigin,
  };
}
