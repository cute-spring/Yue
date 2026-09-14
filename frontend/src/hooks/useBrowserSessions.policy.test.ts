import { afterEach, describe, expect, it, vi } from 'vitest';
import { useBrowserSessions } from './useBrowserSessions';

const response = (body: unknown, ok = true) => ({ ok, json: async () => body }) as Response;

afterEach(() => vi.unstubAllGlobals());

describe('browser origin policy controls', () => {
  it('reviews, approves, and refreshes an exact origin', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ id: 'request-1', origin: 'https://erp.example.com', purpose: 'business', status: 'awaiting_approval' }))
      .mockResolvedValueOnce(response({ id: 'request-1', status: 'approved' }))
      .mockResolvedValueOnce(response([{ origin: 'https://erp.example.com', purpose: 'business', approved_at: 'now' }]));
    vi.stubGlobal('fetch', fetchMock);
    const browser = useBrowserSessions();

    const request = await browser.requestPolicyOrigin('https://erp.example.com', 'business');
    await browser.decidePolicyOrigin(request.id, true);

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/browser/policy/origin-requests', expect.objectContaining({ method: 'POST' }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/browser/policy/origin-requests/request-1/decision', expect.objectContaining({ method: 'POST' }));
    expect(browser.policyOrigins()).toEqual([{ origin: 'https://erp.example.com', purpose: 'business', approved_at: 'now' }]);
  });

  it('revokes an approved origin and refreshes the displayed policy', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(null))
      .mockResolvedValueOnce(response([]));
    vi.stubGlobal('fetch', fetchMock);
    const browser = useBrowserSessions();

    await browser.revokePolicyOrigin('https://erp.example.com');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/browser/policy/origins/https%3A%2F%2Ferp.example.com', { method: 'DELETE' });
    expect(browser.policyOrigins()).toEqual([]);
  });

  it('reconciles an uncertain browser command and refreshes its visible state', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ status: 'cancelled' }))
      .mockResolvedValueOnce(response([]));
    vi.stubGlobal('fetch', fetchMock);
    const browser = useBrowserSessions();
    browser.setSelectedBrowserSessionId('session-1');

    await browser.reconcileBrowserAction('command-1', 'not_applied');

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/browser/sessions/session-1/actions/command-1/reconciliation',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
