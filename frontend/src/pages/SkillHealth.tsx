import { For, Show, createMemo, createSignal, onMount } from 'solid-js';
import type { SkillPreflightRecord, SkillPreflightStatus } from '../types';

export type { SkillPreflightRecord, SkillPreflightStatus } from '../types';

export type SkillPreflightFilter = {
  status: SkillPreflightStatus | 'all';
  sourceLayer: string | 'all';
  query: string;
};

export type MountResult = {
  ok: boolean;
  mountStatus: string | null;
  error: string | null;
};

export type PreflightSummary = {
  total: number;
  available: number;
  needs_fix: number;
  unavailable: number;
};

export type RescanResult = {
  ok: boolean;
  items: SkillPreflightRecord[];
  summary: PreflightSummary | null;
  error: string | null;
};

export const getExcalidrawHealthSummary = (
  record: SkillPreflightRecord,
): { visible: boolean; effectiveLevel: string; blockers: string[]; repairCommands: string[] } => {
  if (record.skill_name !== 'excalidraw-diagram-generator' || !record.excalidraw_health) {
    return { visible: false, effectiveLevel: 'N/A', blockers: [], repairCommands: [] };
  }
  const blockers = Array.isArray(record.excalidraw_health.blockers) ? record.excalidraw_health.blockers : [];
  return {
    visible: true,
    effectiveLevel: record.excalidraw_health.effective_level || 'L0',
    blockers: blockers.map((item) => item.title).filter(Boolean),
    repairCommands: blockers.map((item) => item.fix_command || '').filter(Boolean),
  };
};

export const copyFixCommandsToClipboard = async (
  commands: string[],
  clipboard: Pick<Clipboard, 'writeText'> | null =
    typeof navigator !== 'undefined' ? navigator.clipboard : null,
): Promise<boolean> => {
  const text = commands.join('\n').trim();
  if (!text || !clipboard) return false;
  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};

export const filterPreflightRecords = (
  records: SkillPreflightRecord[],
  filter: SkillPreflightFilter,
): SkillPreflightRecord[] => {
  const keyword = filter.query.trim().toLowerCase();
  return records.filter((item) => {
    if (filter.status !== 'all' && item.status !== filter.status) return false;
    if (filter.sourceLayer !== 'all' && item.source_layer !== filter.sourceLayer) return false;
    if (!keyword) return true;
    const searchable = [
      item.skill_name,
      item.skill_ref,
      item.source_layer,
      item.issues.join(' '),
      item.warnings.join(' '),
      item.suggestions.join(' '),
    ]
      .join(' ')
      .toLowerCase();
    return searchable.includes(keyword);
  });
};

export const getMountActionState = (status: SkillPreflightStatus): { label: string; disabled: boolean } => {
  if (status === 'available') return { label: 'Mount', disabled: false };
  if (status === 'needs_fix') return { label: 'Needs Fix', disabled: true };
  return { label: 'Unavailable', disabled: true };
};

export const getVisibilityStateLabel = (isVisibleInDefaultAgent: boolean): string =>
  isVisibleInDefaultAgent ? 'Visible in default agent' : 'Hidden in default agent';

export const getRecordStatusMessage = (record: SkillPreflightRecord): string => {
  if (record.status_message?.trim()) return record.status_message.trim();
  if (record.issues.length > 0) return record.issues[0];
  if (record.status === 'available') return 'Ready to mount.';
  if (record.status === 'needs_fix') return 'Preflight checks found issues.';
  return 'Skill is unavailable.';
};

export const formatMountErrorMessage = (errorCode: string | null): string => {
  if (errorCode === 'skill_preflight_not_mountable') {
    return 'Fix preflight issues first, then retry mount.';
  }
  if (errorCode === 'agent_not_found') {
    return 'Target agent was not found.';
  }
  if (errorCode === 'agent_store_unavailable') {
    return 'Agent store is unavailable. Retry later.';
  }
  if (errorCode === 'network_error') {
    return 'Network error. Check backend connectivity and retry.';
  }
  return 'Mount failed. Please retry.';
};

export const groupPreflightRecordsByAvailability = (
  records: SkillPreflightRecord[],
): { available: SkillPreflightRecord[]; nonAvailable: SkillPreflightRecord[] } => ({
  available: records.filter((item) => item.status === 'available'),
  nonAvailable: records.filter((item) => item.status !== 'available'),
});

export const rescanSkillPreflight = async (fetchImpl: typeof fetch = fetch): Promise<RescanResult> => {
  try {
    const response = await fetchImpl('/api/skill-preflight/rescan', { method: 'POST' });
    const payload = await response.json();
    if (!response.ok) {
      return { ok: false, items: [], summary: null, error: 'skill_preflight_rescan_failed' };
    }
    const summary = payload?.summary;
    const normalizedSummary =
      summary &&
      typeof summary.total === 'number' &&
      typeof summary.available === 'number' &&
      typeof summary.needs_fix === 'number' &&
      typeof summary.unavailable === 'number'
        ? summary
        : null;
    return {
      ok: true,
      items: Array.isArray(payload?.items) ? payload.items : [],
      summary: normalizedSummary,
      error: null,
    };
  } catch {
    return { ok: false, items: [], summary: null, error: 'network_error' };
  }
};

export const mountSkillToAgent = async (
  skillRef: string,
  agentId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<MountResult> => {
  try {
    const response = await fetchImpl(`/api/skill-preflight/${skillRef}/mount`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload?.detail;
      const errorCode =
        typeof detail === 'string'
          ? detail
          : typeof detail?.code === 'string'
            ? detail.code
            : 'skill_mount_failed';
      return { ok: false, mountStatus: null, error: errorCode };
    }
    return { ok: true, mountStatus: payload?.mount_status || null, error: null };
  } catch {
    return { ok: false, mountStatus: null, error: 'network_error' };
  }
};

export default function SkillHealth() {
  const [records, setRecords] = createSignal<SkillPreflightRecord[]>([]);
  const [statusFilter, setStatusFilter] = createSignal<SkillPreflightStatus | 'all'>('all');
  const [layerFilter, setLayerFilter] = createSignal<string | 'all'>('all');
  const [query, setQuery] = createSignal('');
  const [busyRef, setBusyRef] = createSignal<string | null>(null);
  const [rescanBusy, setRescanBusy] = createSignal(false);
  const [mountedRefs, setMountedRefs] = createSignal<Set<string>>(new Set());
  const [notice, setNotice] = createSignal<{ type: 'success' | 'error'; message: string } | null>(null);

  const filtered = createMemo(() =>
    filterPreflightRecords(records(), {
      status: statusFilter(),
      sourceLayer: layerFilter(),
      query: query(),
    }),
  );

  const layers = createMemo(() => {
    const unique = new Set(records().map((item) => item.source_layer).filter(Boolean));
    return Array.from(unique).sort();
  });

  const grouped = createMemo(() => groupPreflightRecordsByAvailability(filtered()));

  const load = async () => {
    try {
      const response = await fetch('/api/skill-preflight');
      const payload = await response.json();
      setRecords(Array.isArray(payload?.items) ? payload.items : []);
    } catch {
      setRecords([]);
      setNotice({ type: 'error', message: 'Failed to load skill preflight records.' });
    }
  };

  const handleMount = async (skillRef: string) => {
    setBusyRef(skillRef);
    setNotice(null);
    const result = await mountSkillToAgent(skillRef, 'builtin-action-lab');
    setBusyRef(null);
    if (!result.ok) {
      setNotice({ type: 'error', message: formatMountErrorMessage(result.error) });
      return;
    }
    setMountedRefs((prev) => new Set(prev).add(skillRef));
    const status = result.mountStatus || 'mounted';
    setNotice({ type: 'success', message: `Mount result: ${status}` });
  };

  const handleRescan = async () => {
    setRescanBusy(true);
    setNotice(null);
    const result = await rescanSkillPreflight();
    setRescanBusy(false);
    if (!result.ok) {
      setNotice({ type: 'error', message: 'Rescan failed. Please retry.' });
      return;
    }
    setRecords(result.items);
    const summary = result.summary;
    if (!summary) {
      setNotice({ type: 'success', message: `Rescan complete: ${result.items.length} records.` });
      return;
    }
    setNotice({
      type: 'success',
      message: `Rescan complete: ${summary.available} available, ${summary.needs_fix} needs_fix, ${summary.unavailable} unavailable.`,
    });
  };

  const handleCopyFixCommands = async (commands: string[]) => {
    const ok = await copyFixCommandsToClipboard(commands);
    setNotice({
      type: ok ? 'success' : 'error',
      message: ok ? 'Fix commands copied to clipboard.' : 'Unable to copy fix commands.',
    });
  };

  onMount(load);

  return (
    <div class="max-w-7xl mx-auto p-4 md:p-8">
      <div class="mb-8 space-y-1">
        <h2 class="text-4xl font-black text-gray-900 tracking-tight">Skill Health</h2>
        <p class="text-gray-500 text-lg">Inspect preflight status and mount available skills.</p>
      </div>

      <Show when={notice()}>
        {(item) => (
          <div
            class={`mb-4 px-4 py-3 rounded-xl border text-sm font-semibold ${
              item().type === 'success'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
          >
            {item().message}
          </div>
        )}
      </Show>

      <div class="bg-white border border-gray-100 rounded-2xl shadow-sm p-4 mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          value={query()}
          onInput={(e) => setQuery(e.currentTarget.value)}
          placeholder="Search by skill, issue, suggestion"
          class="min-w-[220px] flex-1 border border-gray-200 rounded-lg px-3 py-2.5 focus:ring-2 focus:ring-violet-500 outline-none"
        />
        <select
          value={statusFilter()}
          onChange={(e) => setStatusFilter(e.currentTarget.value as SkillPreflightStatus | 'all')}
          class="border border-gray-200 rounded-lg px-3 py-2.5"
        >
          <option value="all">All Status</option>
          <option value="available">Available</option>
          <option value="needs_fix">Needs Fix</option>
          <option value="unavailable">Unavailable</option>
        </select>
        <select
          value={layerFilter()}
          onChange={(e) => setLayerFilter(e.currentTarget.value)}
          class="border border-gray-200 rounded-lg px-3 py-2.5"
        >
          <option value="all">All Layers</option>
          <For each={layers()}>{(layer) => <option value={layer}>{layer}</option>}</For>
        </select>
        <button
          type="button"
          onClick={load}
          class="px-4 py-2.5 rounded-lg border border-violet-200 text-violet-700 text-xs font-bold uppercase tracking-wider hover:bg-violet-50"
        >
          Refresh
        </button>
        <button
          type="button"
          onClick={handleRescan}
          disabled={rescanBusy()}
          class="px-4 py-2.5 rounded-lg border border-indigo-200 text-indigo-700 text-xs font-bold uppercase tracking-wider hover:bg-indigo-50 disabled:opacity-50"
        >
          {rescanBusy() ? 'Rescanning...' : 'Rescan'}
        </button>
      </div>

      <div class="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 class="text-lg font-black text-gray-800">Preflight Records</h3>
          <span class="text-xs text-gray-500 font-bold uppercase tracking-wider">{filtered().length} visible</span>
        </div>
        <div class="divide-y divide-gray-100">
          <div class="p-5 border-b border-gray-100 bg-emerald-50/30">
            <h4 class="text-sm font-black text-emerald-700 uppercase tracking-wider">
              可用 ({grouped().available.length})
            </h4>
          </div>
          <For each={grouped().available}>
            {(item) => {
              const action = () => getMountActionState(item.status);
              const health = () => getExcalidrawHealthSummary(item);
              return (
                <div class="p-5 space-y-3">
                  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                      <div class="font-bold text-gray-900">{item.skill_ref}</div>
                      <div class="text-xs text-gray-500 mt-1">
                        Layer: {item.source_layer} | Path: {item.source_path}
                      </div>
                      <div class="text-xs text-gray-500 mt-1">
                        Availability: {item.status} | Visibility:{' '}
                        {getVisibilityStateLabel(Boolean(item.visible_in_default_agent) || mountedRefs().has(item.skill_ref))}
                      </div>
                      <div class="text-xs text-gray-500 mt-1">Action: {item.next_action || 'Review diagnostics.'}</div>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="text-[10px] px-2 py-1 rounded-full bg-gray-100 text-gray-700 font-bold uppercase tracking-wider">
                        {item.status}
                      </span>
                      <button
                        type="button"
                        disabled={action().disabled || busyRef() === item.skill_ref}
                        onClick={() => handleMount(item.skill_ref)}
                        class="px-3 py-1.5 rounded-lg border border-violet-200 text-violet-700 text-xs font-bold uppercase tracking-wider hover:bg-violet-50 disabled:opacity-50"
                      >
                        {busyRef() === item.skill_ref ? 'Mounting...' : action().label}
                      </button>
                    </div>
                  </div>
                  <Show when={item.issues.length > 0}>
                    <div class="text-sm text-rose-700 bg-rose-50 border border-rose-100 rounded-lg p-3">
                      Issues: {item.issues.join('; ')}
                    </div>
                  </Show>
                  <Show when={getRecordStatusMessage(item)}>
                    <div class="text-sm text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-3">
                      Status: {getRecordStatusMessage(item)}
                    </div>
                  </Show>
                  <Show when={health().visible}>
                    <div class="text-sm text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-lg p-3">
                      Excalidraw Level: {health().effectiveLevel} (L1/L2/L3)
                      <Show when={health().blockers.length > 0}>
                        <div class="mt-2">Blockers: {health().blockers.join('; ')}</div>
                      </Show>
                      <Show when={health().repairCommands.length > 0}>
                        <div class="mt-2">Fix Commands: {health().repairCommands.join(' | ')}</div>
                        <button
                          type="button"
                          onClick={() => handleCopyFixCommands(health().repairCommands)}
                          class="mt-2 px-3 py-1.5 rounded-lg border border-indigo-200 text-indigo-700 text-xs font-bold uppercase tracking-wider hover:bg-indigo-100"
                        >
                          Copy Fix Commands
                        </button>
                      </Show>
                    </div>
                  </Show>
                  <Show when={item.warnings.length > 0}>
                    <div class="text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                      Warnings: {item.warnings.join('; ')}
                    </div>
                  </Show>
                  <Show when={item.suggestions.length > 0}>
                    <div class="text-sm text-violet-700 bg-violet-50 border border-violet-100 rounded-lg p-3">
                      Suggestions: {item.suggestions.join('; ')}
                    </div>
                  </Show>
                </div>
              );
            }}
          </For>
          <div class="p-5 border-y border-gray-100 bg-rose-50/30">
            <h4 class="text-sm font-black text-rose-700 uppercase tracking-wider">
              不可用（含原因） ({grouped().nonAvailable.length})
            </h4>
          </div>
          <For each={grouped().nonAvailable}>
            {(item) => {
              const action = () => getMountActionState(item.status);
              const health = () => getExcalidrawHealthSummary(item);
              return (
                <div class="p-5 space-y-3">
                  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                    <div>
                      <div class="font-bold text-gray-900">{item.skill_ref}</div>
                      <div class="text-xs text-gray-500 mt-1">
                        Layer: {item.source_layer} | Path: {item.source_path}
                      </div>
                      <div class="text-xs text-gray-500 mt-1">
                        Availability: {item.status} | Visibility:{' '}
                        {getVisibilityStateLabel(Boolean(item.visible_in_default_agent) || mountedRefs().has(item.skill_ref))}
                      </div>
                      <div class="text-xs text-gray-500 mt-1">Action: {item.next_action || 'Review diagnostics.'}</div>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="text-[10px] px-2 py-1 rounded-full bg-gray-100 text-gray-700 font-bold uppercase tracking-wider">
                        {item.status}
                      </span>
                      <button
                        type="button"
                        disabled={action().disabled || busyRef() === item.skill_ref}
                        onClick={() => handleMount(item.skill_ref)}
                        class="px-3 py-1.5 rounded-lg border border-violet-200 text-violet-700 text-xs font-bold uppercase tracking-wider hover:bg-violet-50 disabled:opacity-50"
                      >
                        {busyRef() === item.skill_ref ? 'Mounting...' : action().label}
                      </button>
                    </div>
                  </div>
                  <Show when={item.issues.length > 0}>
                    <div class="text-sm text-rose-700 bg-rose-50 border border-rose-100 rounded-lg p-3">
                      Issues: {item.issues.join('; ')}
                    </div>
                  </Show>
                  <Show when={getRecordStatusMessage(item)}>
                    <div class="text-sm text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-3">
                      Status: {getRecordStatusMessage(item)}
                    </div>
                  </Show>
                  <Show when={health().visible}>
                    <div class="text-sm text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-lg p-3">
                      Excalidraw Level: {health().effectiveLevel} (L1/L2/L3)
                      <Show when={health().blockers.length > 0}>
                        <div class="mt-2">Blockers: {health().blockers.join('; ')}</div>
                      </Show>
                      <Show when={health().repairCommands.length > 0}>
                        <div class="mt-2">Fix Commands: {health().repairCommands.join(' | ')}</div>
                        <button
                          type="button"
                          onClick={() => handleCopyFixCommands(health().repairCommands)}
                          class="mt-2 px-3 py-1.5 rounded-lg border border-indigo-200 text-indigo-700 text-xs font-bold uppercase tracking-wider hover:bg-indigo-100"
                        >
                          Copy Fix Commands
                        </button>
                      </Show>
                    </div>
                  </Show>
                  <Show when={item.warnings.length > 0}>
                    <div class="text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg p-3">
                      Warnings: {item.warnings.join('; ')}
                    </div>
                  </Show>
                  <Show when={item.suggestions.length > 0}>
                    <div class="text-sm text-violet-700 bg-violet-50 border border-violet-100 rounded-lg p-3">
                      Suggestions: {item.suggestions.join('; ')}
                    </div>
                  </Show>
                </div>
              );
            }}
          </For>
          <Show when={filtered().length === 0}>
            <div class="p-6 text-sm text-gray-500">No records match current filters.</div>
          </Show>
        </div>
      </div>
    </div>
  );
}
