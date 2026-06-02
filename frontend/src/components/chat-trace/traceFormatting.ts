import type { ToolTraceRecord, TraceFieldPolicy } from '../../types';

export const formatJson = (value: unknown): string => {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

export const formatTimestamp = (value?: string | null): string => {
  if (!value) return '';
  return value.replace('T', ' ').replace('Z', ' UTC');
};

export const formatBytes = (value?: number | null): string => {
  if (value == null || Number.isNaN(value)) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
};

export const policyTone = (exposure: TraceFieldPolicy['exposure']): string => {
  if (exposure === 'raw_only') return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-emerald-100 text-emerald-700 border-emerald-200';
};

export const normalizeTraceError = (status: number, detail?: string): string => {
  if (status === 404) return 'No saved trace summary is available for this chat yet.';
  if (status === 403) return detail || 'Trace access is currently restricted.';
  return detail || `HTTP ${status}`;
};

export const statusTone = (status: ToolTraceRecord['status']): string => {
  if (status === 'success') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  if (status === 'error') return 'bg-rose-100 text-rose-700 border-rose-200';
  if (status === 'cancelled') return 'bg-amber-100 text-amber-700 border-amber-200';
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

export const buildTraceTree = (traces: ToolTraceRecord[]): Map<string | null, ToolTraceRecord[]> => {
  const tree = new Map<string | null, ToolTraceRecord[]>();
  for (const trace of traces) {
    const key = trace.parent_trace_id || null;
    const bucket = tree.get(key) || [];
    bucket.push(trace);
    tree.set(key, bucket);
  }
  for (const [, bucket] of tree) {
    bucket.sort((a, b) => a.call_index - b.call_index);
  }
  return tree;
};
