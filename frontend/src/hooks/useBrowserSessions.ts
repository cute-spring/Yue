import { createSignal } from 'solid-js';

export type BrowserSession = {
  id: string;
  title: string;
  origin: string;
  status: 'active' | 'paused' | 'disconnected';
  authorization_mode: 'step_confirm' | 'session_auto' | 'site_auto';
  has_snapshot: boolean;
};

export function useBrowserSessions() {
  const [sessions, setSessions] = createSignal<BrowserSession[]>([]);
  const [selectedBrowserSessionId, setSelectedBrowserSessionId] = createSignal<string | null>(null);

  const refreshBrowserSessions = async () => {
    try {
      const response = await fetch('/api/browser/sessions');
      if (!response.ok) throw new Error('Browser sessions are unavailable.');
      const next = await response.json();
      const active = Array.isArray(next) ? next.filter((item): item is BrowserSession => item?.status === 'active') : [];
      setSessions(active);
      if (selectedBrowserSessionId() && !active.some((item) => item.id === selectedBrowserSessionId())) {
        setSelectedBrowserSessionId(null);
      }
    } catch {
      setSessions([]);
      setSelectedBrowserSessionId(null);
    }
  };

  return { sessions, selectedBrowserSessionId, setSelectedBrowserSessionId, refreshBrowserSessions };
}
