import { createSignal, For, onMount, Show } from 'solid-js';
import { useBrowserSessions } from '../../../../hooks/useBrowserSessions';

export function BrowserOriginPolicySection() {
  const browser = useBrowserSessions();
  const [origin, setOrigin] = createSignal('');
  const [purpose, setPurpose] = createSignal<'business' | 'sso_handoff'>('business');
  const [pendingRequest, setPendingRequest] = createSignal<{ id: string; origin: string; purpose: 'business' | 'sso_handoff' } | null>(null);
  const [error, setError] = createSignal<string | null>(null);

  onMount(() => void browser.refreshPolicyOrigins().catch((reason) => setError(reason.message)));

  return (
    <section class="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5 dark:border-emerald-900 dark:bg-emerald-950/20">
      <h3 class="font-semibold text-gray-900 dark:text-gray-100">Browser origin policy</h3>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Approve exact HTTPS origins before sharing a browser tab. SSO handoff origins are never read or automated.</p>
      <div class="mt-4 flex flex-wrap gap-2">
        <input class="min-w-64 flex-1 rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" placeholder="https://erp.example.com" value={origin()} onInput={(event) => setOrigin(event.currentTarget.value)} aria-label="Exact HTTPS origin" />
        <select class="rounded border border-gray-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" value={purpose()} onChange={(event) => setPurpose(event.currentTarget.value as 'business' | 'sso_handoff')}>
          <option value="business">Business site</option>
          <option value="sso_handoff">SSO handoff only</option>
        </select>
        <button type="button" class="rounded bg-emerald-700 px-3 py-2 text-sm font-semibold text-white" onClick={() => void browser.requestPolicyOrigin(origin(), purpose()).then(setPendingRequest).catch((reason) => setError(reason.message))}>Review add</button>
      </div>
      <Show when={pendingRequest()}>
        {(request) => <div class="mt-3 flex items-center gap-2 rounded border border-amber-300 bg-amber-50 p-3 text-sm dark:bg-amber-950/30"><span class="flex-1">Allow {request().origin} as {request().purpose === 'business' ? 'a business site' : 'SSO handoff only'}?</span><button type="button" class="rounded bg-emerald-700 px-2 py-1 font-semibold text-white" onClick={() => void browser.decidePolicyOrigin(request().id, true).then(() => { setPendingRequest(null); setOrigin(''); }).catch((reason) => setError(reason.message))}>Approve</button><button type="button" class="rounded border border-amber-500 px-2 py-1" onClick={() => void browser.decidePolicyOrigin(request().id, false).then(() => setPendingRequest(null)).catch((reason) => setError(reason.message))}>Reject</button></div>}
      </Show>
      <Show when={error()}>{(message) => <p class="mt-3 text-sm text-rose-700 dark:text-rose-300">{message()}</p>}</Show>
      <ul class="mt-4 space-y-2 text-sm">
        <For each={browser.policyOrigins()}>{(record) => <li class="flex items-center gap-2"><span class="flex-1">{record.origin} — {record.purpose === 'business' ? 'business' : 'SSO handoff only'}</span><button type="button" class="rounded border border-gray-300 px-2 py-1 dark:border-slate-700" onClick={() => void browser.revokePolicyOrigin(record.origin).catch((reason) => setError(reason.message))}>Revoke</button></li>}</For>
      </ul>
    </section>
  );
}
