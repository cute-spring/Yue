import { For, Show, Switch, Match, createMemo, createSignal } from 'solid-js';
import MermaidViewer from './MermaidViewer';
import { ActionState, Message } from '../types';

const tryFormatStructuredValue = (value: unknown): string => {
  if (value == null) return '';
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return '';
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        return JSON.stringify(JSON.parse(trimmed), null, 2);
      } catch {
        return value;
      }
    }
    return value;
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

export const getActionStateTone = (state: Pick<ActionState, 'lifecycle_status' | 'status'>): string => {
  const key = (state.lifecycle_status || state.status || '').toLowerCase();
  if (key.includes('approval') || key.includes('awaiting')) return 'amber';
  if (key.includes('blocked') || key.includes('failed') || key.includes('rejected')) return 'rose';
  if (key.includes('success') || key.includes('succeeded') || key.includes('ready') || key.includes('approved')) return 'emerald';
  return 'slate';
};

export const getActionStateLabel = (state: Pick<ActionState, 'lifecycle_status' | 'status'>): string => {
  const raw = (state.lifecycle_status || state.status || 'unknown').replace(/_/g, ' ');
  return raw.replace(/\b\w/g, (char) => char.toUpperCase());
};

export const sortActionStates = (states: ActionState[]): ActionState[] => {
  return [...states].sort((a, b) => {
    const sequenceDelta = (b.sequence || 0) - (a.sequence || 0);
    if (sequenceDelta !== 0) return sequenceDelta;
    return String(b.updated_at || b.ts || '').localeCompare(String(a.updated_at || a.ts || ''));
  });
};

export type ActionStateGroup = {
  key: string;
  label: string;
  latest: ActionState;
  states: ActionState[];
};

export type ActionDetailSection = {
  title: string;
  tone: 'slate' | 'rose' | 'emerald';
  content: string;
};

export type ActionTraceIdentity = {
  key: string;
  label: string;
};

export type ActionFilterKey = 'all' | 'awaiting_approval' | 'failed' | 'succeeded';

export type ActionStatusSummary = {
  total: number;
  awaitingApproval: number;
  failed: number;
  succeeded: number;
};

const COLLAPSED_VISIBLE_INVOCATIONS = 1;
const EXPANDED_VISIBLE_INVOCATIONS = 3;

export const getActionStateDisplayId = (state: Pick<ActionState, 'invocation_id' | 'request_id'>): string => {
  const source = state.invocation_id || state.request_id || '';
  if (!source) return 'pending';
  const parts = String(source).split(':');
  return parts[parts.length - 1] || source;
};

export const getActionStateTraceIdentity = (state: ActionState): ActionTraceIdentity => {
  const key = [
    state.skill_name,
    state.action_id,
    state.invocation_id || '',
    state.request_id || '',
    state.lifecycle_status || state.status || '',
    state.updated_at || state.ts || '',
    state.sequence || '',
  ].join('::');
  return {
    key,
    label: `${state.skill_name}.${state.action_id}#${getActionStateDisplayId(state)}`,
  };
};

export const getActionStateTracePayload = (state: ActionState): string =>
  JSON.stringify(state, null, 2);

export const getActionStateTimestampLabel = (state: Pick<ActionState, 'updated_at' | 'ts'>): string => {
  const raw = String(state.updated_at || state.ts || '').trim();
  if (!raw) return '';
  return raw.replace('T', ' ').replace('Z', ' UTC');
};

export const groupActionStates = (states: ActionState[]): ActionStateGroup[] => {
  const grouped = new Map<string, ActionState[]>();
  for (const state of sortActionStates(states)) {
    const key = `${state.skill_name}::${state.action_id}`;
    const existing = grouped.get(key) || [];
    existing.push(state);
    grouped.set(key, existing);
  }

  return [...grouped.entries()].map(([key, groupedStates]) => ({
    key,
    label: `${groupedStates[0].skill_name}.${groupedStates[0].action_id}`,
    latest: groupedStates[0],
    states: groupedStates,
  }));
};

export const summarizeActionGroups = (groups: ActionStateGroup[]): ActionStatusSummary => {
  return groups.reduce<ActionStatusSummary>(
    (summary, group) => {
      const status = (group.latest.lifecycle_status || group.latest.status || '').toLowerCase();
      summary.total += 1;
      if (status === 'awaiting_approval') summary.awaitingApproval += 1;
      if (status === 'failed') summary.failed += 1;
      if (status === 'succeeded') summary.succeeded += 1;
      return summary;
    },
    { total: 0, awaitingApproval: 0, failed: 0, succeeded: 0 },
  );
};

export const filterActionGroups = (
  groups: ActionStateGroup[],
  searchText: string,
  filter: ActionFilterKey,
): ActionStateGroup[] => {
  const normalizedSearch = searchText.trim().toLowerCase();
  return groups.filter((group) => {
    const latestStatus = (group.latest.lifecycle_status || group.latest.status || '').toLowerCase();
    if (filter === 'awaiting_approval' && latestStatus !== 'awaiting_approval') return false;
    if (filter === 'failed' && latestStatus !== 'failed') return false;
    if (filter === 'succeeded' && latestStatus !== 'succeeded') return false;

    if (!normalizedSearch) return true;
    const haystacks = [
      group.label,
      group.latest.invocation_id || '',
      group.latest.request_id || '',
      group.latest.approval_token || '',
      ...group.states.map((state) => `${state.lifecycle_status || ''} ${state.status || ''}`),
    ];
    return haystacks.some((value) => value.toLowerCase().includes(normalizedSearch));
  });
};

export const getVisibleActionGroupStates = (
  group: ActionStateGroup,
  expanded: boolean,
  requestedVisibleCount?: number,
): ActionState[] => {
  if (!expanded) return group.states.slice(0, COLLAPSED_VISIBLE_INVOCATIONS);
  const resolvedCount = Math.max(requestedVisibleCount || EXPANDED_VISIBLE_INVOCATIONS, EXPANDED_VISIBLE_INVOCATIONS);
  return group.states.slice(0, resolvedCount);
};

export const getHiddenActionGroupCount = (
  group: ActionStateGroup,
  expanded: boolean,
  requestedVisibleCount?: number,
): number => {
  return Math.max(group.states.length - getVisibleActionGroupStates(group, expanded, requestedVisibleCount).length, 0);
};

export const canResolveActionState = (state: ActionState): boolean => {
  const key = (state.lifecycle_status || state.status || '').toLowerCase();
  return key === 'awaiting_approval' && !!state.approval_token;
};

export const getActionStateArgs = (state: ActionState): Record<string, any> | null => {
  const metadata = state.payload?.metadata;
  if (!metadata || typeof metadata !== 'object') return null;

  const candidates = [metadata.validated_arguments, metadata.tool_args];
  for (const candidate of candidates) {
    if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
      return candidate as Record<string, any>;
    }
  }
  return null;
};

export const getActionStateDetail = (state: ActionState): string => {
  const metadata = state.payload?.metadata;
  if (!metadata || typeof metadata !== 'object') return '';
  const toolError = tryFormatStructuredValue(metadata.tool_error);
  if (toolError) return toolError;
  const toolResult = tryFormatStructuredValue(metadata.tool_result);
  if (toolResult) return toolResult;
  return '';
};

const getStringList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
};

const tryParseStructuredPayload = (value: unknown): unknown => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return value;
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        return JSON.parse(trimmed);
      } catch {
        return value;
      }
    }
  }
  return value;
};

const formatPathRange = (item: Record<string, unknown>): string => {
  const ranges: string[] = [];
  if (typeof item.start_line === 'number' || typeof item.end_line === 'number') {
    const start = item.start_line ?? '?';
    const end = item.end_line ?? start;
    ranges.push(`lines ${start}-${end}`);
  }
  if (typeof item.start_page === 'number' || typeof item.end_page === 'number') {
    const start = item.start_page ?? '?';
    const end = item.end_page ?? start;
    ranges.push(`pages ${start}-${end}`);
  }
  return ranges.join(', ');
};

const buildDocsSearchDetailSections = (
  rawValue: unknown,
  tone: 'emerald' | 'rose',
): ActionDetailSection[] => {
  const parsed = tryParseStructuredPayload(rawValue);
  if (!Array.isArray(parsed)) return [];
  const items = parsed.filter((item): item is Record<string, unknown> => !!item && typeof item === 'object');
  if (items.length === 0) return [];

  const matchedPaths = items
    .map((item, index) => {
      const path = typeof item.path === 'string' ? item.path : `result-${index + 1}`;
      const score = typeof item.score === 'number' ? `score ${item.score.toFixed(2)}` : '';
      const range = formatPathRange(item);
      return [path, score, range].filter(Boolean).join(' | ');
    })
    .join('\n');

  const excerpts = items
    .map((item, index) => {
      const path = typeof item.path === 'string' ? item.path : `result-${index + 1}`;
      const snippet = tryFormatStructuredValue(item.snippet);
      return snippet ? `${path}\n${snippet}` : '';
    })
    .filter(Boolean)
    .join('\n\n---\n\n');

  const sections: ActionDetailSection[] = [
    {
      title: 'Result Summary',
      tone,
      content: `${items.length} matched document result(s)`,
    },
    {
      title: 'Matched Paths',
      tone: 'slate',
      content: matchedPaths,
    },
  ];
  if (excerpts) {
    sections.push({
      title: 'Excerpts',
      tone,
      content: excerpts,
    });
  }
  return sections;
};

const buildDocsReadDetailSections = (
  rawValue: unknown,
  tone: 'emerald' | 'rose',
): ActionDetailSection[] => {
  if (typeof rawValue !== 'string') return [];
  const formatted = tryFormatStructuredValue(rawValue);
  if (!formatted) return [];
  const [referenceLine, ...rest] = formatted.split('\n');
  if (!referenceLine.includes('#L') && !referenceLine.includes('#P')) return [];
  const content = rest.join('\n').trim();
  const [path, anchor] = referenceLine.split('#');
  const sections: ActionDetailSection[] = [
    {
      title: 'Document Path',
      tone: 'slate',
      content: path,
    },
    {
      title: anchor?.startsWith('P') ? 'Page Range' : 'Line Range',
      tone: 'slate',
      content: anchor || '',
    },
  ];
  if (content) {
    sections.push({
      title: 'Excerpt',
      tone,
      content,
    });
  }
  return sections;
};

const buildArtifactDetailSections = (
  rawValue: unknown,
  tone: 'emerald' | 'rose',
): ActionDetailSection[] => {
  const parsed = tryParseStructuredPayload(rawValue);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return [];
  const payload = parsed as Record<string, unknown>;
  const filename = typeof payload.filename === 'string' ? payload.filename : '';
  const filePath = typeof payload.file_path === 'string' ? payload.file_path : '';
  const downloadUrl = typeof payload.download_url === 'string' ? payload.download_url : '';
  if (!filename && !filePath && !downloadUrl) return [];

  const sections: ActionDetailSection[] = [];
  if (filename || filePath) {
    sections.push({
      title: 'Artifact',
      tone,
      content: [filename, filePath].filter(Boolean).join('\n'),
    });
  }
  if (downloadUrl) {
    sections.push({
      title: 'Download',
      tone: 'slate',
      content: downloadUrl,
    });
  }
  const remainingEntries = Object.entries(payload).filter(([key]) => !['filename', 'file_path', 'download_url', 'download_markdown'].includes(key));
  if (remainingEntries.length > 0) {
    sections.push({
      title: 'Artifact Metadata',
      tone: 'slate',
      content: JSON.stringify(Object.fromEntries(remainingEntries), null, 2),
    });
  }
  return sections;
};

const getActionMappedTool = (state: ActionState): string => {
  const payloadTool = state.payload?.mapped_tool;
  if (typeof payloadTool === 'string' && payloadTool.trim()) return payloadTool;
  const metadataTool = state.payload?.metadata?.mapped_tool;
  if (typeof metadataTool === 'string' && metadataTool.trim()) return metadataTool;
  return '';
};

const buildExecDetailSections = (
  rawValue: unknown,
  tone: 'emerald' | 'rose',
): ActionDetailSection[] => {
  const formatted = tryFormatStructuredValue(rawValue);
  if (!formatted) return [];

  const exitCodeMatch = formatted.match(/\n?Exit code:\s*(-?\d+)\s*$/);
  const exitCode = exitCodeMatch ? exitCodeMatch[1] : '';
  const withoutExitCode = exitCodeMatch ? formatted.slice(0, exitCodeMatch.index).trimEnd() : formatted;

  const stderrMarker = '\nSTDERR:\n';
  const stderrIndex = withoutExitCode.indexOf(stderrMarker);
  let stdoutText = withoutExitCode;
  let stderrText = '';
  if (stderrIndex >= 0) {
    stdoutText = withoutExitCode.slice(0, stderrIndex).trimEnd();
    stderrText = withoutExitCode.slice(stderrIndex + stderrMarker.length).trim();
  } else if (withoutExitCode.startsWith('STDERR:\n')) {
    stdoutText = '';
    stderrText = withoutExitCode.slice('STDERR:\n'.length).trim();
  }

  const sections: ActionDetailSection[] = [];
  if (stdoutText.trim()) {
    sections.push({
      title: 'Stdout',
      tone,
      content: stdoutText.trim(),
    });
  }
  if (stderrText) {
    sections.push({
      title: 'Stderr',
      tone: 'rose',
      content: stderrText,
    });
  }
  if (exitCode) {
    sections.push({
      title: 'Exit Code',
      tone: exitCode === '0' ? 'emerald' : 'rose',
      content: exitCode,
    });
  }
  return sections;
};

export const getActionStateDetailSections = (state: ActionState): ActionDetailSection[] => {
  const sections: ActionDetailSection[] = [];
  const validationErrors = getStringList(state.payload?.validation_errors);
  const missingRequirements = getStringList(state.payload?.missing_requirements);
  const metadata = state.payload?.metadata;
  const mappedTool = getActionMappedTool(state);

  if (validationErrors.length > 0) {
    sections.push({
      title: 'Validation Errors',
      tone: 'rose',
      content: validationErrors.join('\n'),
    });
  }
  if (missingRequirements.length > 0) {
    sections.push({
      title: 'Missing Requirements',
      tone: 'rose',
      content: missingRequirements.join('\n'),
    });
  }

  const toolError = tryFormatStructuredValue(metadata?.tool_error);
  if (toolError) {
    const rendererSections =
      mappedTool === 'builtin:exec'
        ? buildExecDetailSections(metadata?.tool_error, 'rose')
        : mappedTool === 'builtin:docs_search' || mappedTool === 'builtin:docs_search_pdf'
          ? buildDocsSearchDetailSections(metadata?.tool_error, 'rose')
          : mappedTool === 'builtin:docs_read' || mappedTool === 'builtin:docs_read_pdf'
            ? buildDocsReadDetailSections(metadata?.tool_error, 'rose')
            : mappedTool === 'builtin:generate_pptx'
              ? buildArtifactDetailSections(metadata?.tool_error, 'rose')
              : [];
    if (rendererSections.length > 0) {
      sections.push(...rendererSections);
    } else {
      sections.push({
        title: 'Tool Error',
        tone: 'rose',
        content: toolError,
      });
    }
  }

  const toolResult = tryFormatStructuredValue(metadata?.tool_result);
  if (toolResult) {
    const rendererSections =
      mappedTool === 'builtin:exec'
        ? buildExecDetailSections(metadata?.tool_result, 'emerald')
        : mappedTool === 'builtin:docs_search' || mappedTool === 'builtin:docs_search_pdf'
          ? buildDocsSearchDetailSections(metadata?.tool_result, 'emerald')
          : mappedTool === 'builtin:docs_read' || mappedTool === 'builtin:docs_read_pdf'
            ? buildDocsReadDetailSections(metadata?.tool_result, 'emerald')
            : mappedTool === 'builtin:generate_pptx'
              ? buildArtifactDetailSections(metadata?.tool_result, 'emerald')
              : [];
    if (rendererSections.length > 0) {
      sections.push(...rendererSections);
    } else {
      sections.push({
        title: 'Tool Result',
        tone: 'emerald',
        content: toolResult,
      });
    }
  }

  if (sections.length === 0) {
    const fallback = getActionStateDetail(state);
    if (fallback) {
      sections.push({
        title: 'Details',
        tone: 'slate',
        content: fallback,
      });
    }
  }

  return sections;
};

const getActionToneClasses = (tone: string): string => {
  if (tone === 'amber') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (tone === 'rose') return 'border-rose-200 bg-rose-50 text-rose-700';
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return 'border-slate-200 bg-slate-50 text-slate-700';
};

const getActionDetailClasses = (tone: ActionDetailSection['tone']): string => {
  if (tone === 'rose') return 'border-rose-200 bg-rose-50/70';
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50/70';
  return 'border-border bg-background/80';
};

interface IntelligencePanelProps {
  showKnowledge: boolean;
  setShowKnowledge: (val: boolean) => void;
  isArtifactExpanded: boolean;
  setIsArtifactExpanded: (val: boolean) => void;
  intelligenceTab: 'notes' | 'graph' | 'actions' | 'preview' | 'stats';
  setIntelligenceTab: (val: 'notes' | 'graph' | 'actions' | 'preview' | 'stats') => void;
  previewContent: { lang: string, content: string } | null;
  lastMessage: Message | undefined;
  isMobile: boolean;
  actionStates: ActionState[];
  isTyping: boolean;
  onResolveAction: (state: ActionState, approved: boolean) => void;
}

export default function IntelligencePanel(props: IntelligencePanelProps) {
  const [actionSearchText, setActionSearchText] = createSignal('');
  const [actionFilter, setActionFilter] = createSignal<ActionFilterKey>('all');
  const [expandedActionGroups, setExpandedActionGroups] = createSignal<Record<string, boolean>>({});
  const [visibleInvocationCounts, setVisibleInvocationCounts] = createSignal<Record<string, number>>({});
  const [focusedActionKey, setFocusedActionKey] = createSignal<string | null>(null);
  const [copiedTraceKey, setCopiedTraceKey] = createSignal<string | null>(null);
  const groupedActionStates = createMemo(() => groupActionStates(props.actionStates));
  const actionStatusSummary = createMemo(() => summarizeActionGroups(groupedActionStates()));
  const visibleActionGroups = createMemo(() =>
    filterActionGroups(groupedActionStates(), actionSearchText(), actionFilter()),
  );
  const focusedActionState = createMemo(() => {
    const targetKey = focusedActionKey();
    if (!targetKey) return null;
    for (const group of groupedActionStates()) {
      for (const state of group.states) {
        if (getActionStateTraceIdentity(state).key === targetKey) {
          return state;
        }
      }
    }
    return null;
  });

  const isGroupExpanded = (groupKey: string) => !!expandedActionGroups()[groupKey];
  const getVisibleInvocationCount = (groupKey: string) =>
    visibleInvocationCounts()[groupKey] || EXPANDED_VISIBLE_INVOCATIONS;
  const toggleGroupExpanded = (groupKey: string) => {
    const nextExpanded = !isGroupExpanded(groupKey);
    setExpandedActionGroups((current) => ({ ...current, [groupKey]: nextExpanded }));
    if (nextExpanded) {
      setVisibleInvocationCounts((current) => ({
        ...current,
        [groupKey]: Math.max(current[groupKey] || 0, EXPANDED_VISIBLE_INVOCATIONS),
      }));
    }
  };
  const showMoreInvocations = (groupKey: string) => {
    setVisibleInvocationCounts((current) => ({
      ...current,
      [groupKey]: (current[groupKey] || EXPANDED_VISIBLE_INVOCATIONS) + EXPANDED_VISIBLE_INVOCATIONS,
    }));
  };
  const copyFocusedTrace = async () => {
    const focused = focusedActionState();
    if (!focused || typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return;
    const identity = getActionStateTraceIdentity(focused);
    await navigator.clipboard.writeText(getActionStateTracePayload(focused));
    setCopiedTraceKey(identity.key);
    window.setTimeout(() => {
      setCopiedTraceKey((current) => (current === identity.key ? null : current));
    }, 1800);
  };

  return (
    <div 
      class={`
        fixed lg:relative inset-y-0 right-0 bg-surface border-l border-border transform transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] z-30
        ${props.showKnowledge ? (props.isArtifactExpanded ? 'translate-x-0 w-[55vw] opacity-100' : 'translate-x-0 w-[420px] opacity-100') : 'translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0 overflow-hidden'}
      `}
    >
      <div class={`${props.isArtifactExpanded ? 'w-[55vw]' : 'w-[420px]'} h-full flex flex-col transition-all duration-300`}>
        <div class="p-5 border-b border-border flex justify-between items-center bg-surface/50 backdrop-blur-md sticky top-0 z-10">
          <h2 class="font-black text-text-primary text-xs uppercase tracking-[0.2em] flex items-center gap-2.5">
            <div class="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
            Intelligence Hub
          </h2>
          <div class="flex items-center gap-1">
            <button 
              onClick={() => props.setIsArtifactExpanded(!props.isArtifactExpanded)} 
              class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90"
              title={props.isArtifactExpanded ? "Collapse view" : "Expand view"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {props.isArtifactExpanded 
                  ? <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  : <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                }
              </svg>
            </button>
            <button onClick={() => props.setShowKnowledge(false)} class="text-text-secondary hover:text-primary p-2 hover:bg-primary/10 rounded-xl transition-all active:scale-90">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Intelligence Tabs */}
        <div class="flex border-b border-border bg-background/50 p-1">
          <button 
            onClick={() => props.setIntelligenceTab('actions')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'actions' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Actions
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('notes')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'notes' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Notes
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('graph')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'graph' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Graph
          </button>
          <button 
            onClick={() => props.setIntelligenceTab('stats')}
            class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'stats' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
          >
            Stats
          </button>
          <Show when={props.previewContent}>
            <button 
              onClick={() => props.setIntelligenceTab('preview')}
              class={`flex-1 py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${props.intelligenceTab === 'preview' ? 'bg-surface text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'}`}
            >
              Preview
            </button>
          </Show>
        </div>

        <div class="p-6 space-y-8 overflow-y-auto flex-1 scrollbar-thin">
          <Switch>
            <Match when={props.intelligenceTab === 'preview'}>
              <div class="h-full flex flex-col animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-xs font-black text-text-primary uppercase tracking-[0.2em]">Artifact Preview</h3>
                  <div class="flex gap-2">
                     <span class="text-[10px] font-mono bg-primary/10 text-primary px-2 py-1 rounded">{props.previewContent?.lang}</span>
                  </div>
                </div>
                <div class="flex-1 bg-white rounded-xl overflow-hidden border border-border shadow-sm relative">
                  <Show when={props.previewContent?.lang === 'html' || props.previewContent?.lang === 'xml'}>
                    <iframe 
                      srcdoc={props.previewContent?.content} 
                      class="w-full h-full border-0" 
                      sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                    />
                  </Show>
                  <Show when={props.previewContent?.lang === 'svg'}>
                    <div class="w-full h-full flex items-center justify-center p-4 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4IiBoZWlnaHQ9IjgiPgo8cmVjdCB3aWR0aD0iOCIgaGVpZ2h0PSI4IiBmaWxsPSIjZmZmIi8+CjxwYXRoIGQ9Ik0wIDBMOCA4Wk04IDBMMCA4WiIgc3Ryb2tlPSIjZWVlIiBzdHJva2Utd2lkdGg9IjEiLz4KPC9zdmc+')]">
                      <div innerHTML={props.previewContent?.content} />
                    </div>
                  </Show>
                  <Show when={props.previewContent?.lang === 'mermaid'}>
                    <div class="w-full h-full p-4 bg-white overflow-hidden">
                      <MermaidViewer code={props.previewContent?.content || ''} />
                    </div>
                  </Show>
                </div>
              </div>
            </Match>
            <Match when={props.intelligenceTab === 'actions'}>
              <div class="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="relative group">
                  <div class="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-primary/5 rounded-2xl blur opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                  <div class="relative bg-surface border border-primary/10 rounded-2xl p-5 shadow-sm">
                    <h4 class="text-[10px] font-black text-primary uppercase tracking-[0.2em] mb-3">Contextual Analysis</h4>
                    <p class="text-[13px] text-text-secondary leading-relaxed font-medium">
                      Monitoring your conversation to extract key entities and research data in real-time.
                    </p>
                  </div>
                </div>
                
                <div class="space-y-5">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em] flex items-center gap-2">
                    <span class="w-1 h-1 bg-text-secondary/40 rounded-full"></span>
                    Action States
                  </h4>
                  <Show
                    when={groupedActionStates().length > 0}
                    fallback={
                      <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                        <p class="text-xs text-text-secondary/60 font-medium italic">No tool-backed skill actions observed yet</p>
                      </div>
                    }
                  >
                    <div class="space-y-4">
                      <div class="grid grid-cols-2 gap-2">
                        <div class="rounded-2xl border border-border bg-surface/70 p-3">
                          <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">Tracked</div>
                          <div class="mt-1 text-lg font-black text-text-primary">{actionStatusSummary().total}</div>
                        </div>
                        <div class="rounded-2xl border border-amber-200 bg-amber-50/70 p-3">
                          <div class="text-[10px] font-black uppercase tracking-[0.16em] text-amber-700">Awaiting Approval</div>
                          <div class="mt-1 text-lg font-black text-amber-800">{actionStatusSummary().awaitingApproval}</div>
                        </div>
                        <div class="rounded-2xl border border-rose-200 bg-rose-50/70 p-3">
                          <div class="text-[10px] font-black uppercase tracking-[0.16em] text-rose-700">Failed</div>
                          <div class="mt-1 text-lg font-black text-rose-800">{actionStatusSummary().failed}</div>
                        </div>
                        <div class="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-3">
                          <div class="text-[10px] font-black uppercase tracking-[0.16em] text-emerald-700">Succeeded</div>
                          <div class="mt-1 text-lg font-black text-emerald-800">{actionStatusSummary().succeeded}</div>
                        </div>
                      </div>
                      <div class="space-y-3 rounded-2xl border border-border bg-surface/60 p-4">
                        <input
                          value={actionSearchText()}
                          onInput={(event) => setActionSearchText(event.currentTarget.value)}
                          placeholder="Search by action, invocation, token, or status"
                          class="w-full rounded-xl border border-border bg-background px-3 py-2 text-[12px] text-text-primary outline-none transition-all placeholder:text-text-secondary/60 focus:border-primary/50"
                        />
                        <div class="flex flex-wrap gap-2">
                          <For each={[
                            { key: 'all' as const, label: 'All' },
                            { key: 'awaiting_approval' as const, label: 'Awaiting Approval' },
                            { key: 'failed' as const, label: 'Failed' },
                            { key: 'succeeded' as const, label: 'Succeeded' },
                          ]}>
                            {(option) => (
                              <button
                                class={`rounded-full border px-3 py-1.5 text-[10px] font-black uppercase tracking-wide transition-all ${
                                  actionFilter() === option.key
                                    ? 'border-primary bg-primary/10 text-primary'
                                    : 'border-border bg-background text-text-secondary hover:text-text-primary'
                                }`}
                                onClick={() => setActionFilter(option.key)}
                              >
                                {option.label}
                              </button>
                            )}
                          </For>
                        </div>
                      </div>
                      <Show
                        when={visibleActionGroups().length > 0}
                        fallback={
                          <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                            <p class="text-xs text-text-secondary/60 font-medium italic">No action groups match the current filters</p>
                          </div>
                        }
                      >
                        <div class="space-y-3">
                      <Show when={focusedActionState()}>
                        {(focusedAction) => {
                          const focused = focusedAction();
                          const focusedTone = getActionStateTone(focused);
                          const focusedArgs = getActionStateArgs(focused);
                          const focusedSections = getActionStateDetailSections(focused);
                          const focusedIdentity = getActionStateTraceIdentity(focused);
                          return (
                            <div class="rounded-[1.6rem] border border-primary/20 bg-gradient-to-br from-primary/5 via-surface to-surface p-5 shadow-sm">
                              <div class="flex items-start justify-between gap-3">
                                <div class="min-w-0">
                                  <div class="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Focused Trace</div>
                                  <div class="mt-2 text-[14px] font-black text-text-primary break-all">
                                    {focused.skill_name}.{focused.action_id}
                                  </div>
                                  <div class="mt-1 font-mono text-[11px] text-text-secondary">
                                    {focusedIdentity.label}
                                  </div>
                                </div>
                                <div class="flex flex-wrap justify-end gap-2">
                                  <span class={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${getActionToneClasses(focusedTone)}`}>
                                    {getActionStateLabel(focused)}
                                  </span>
                                  <button
                                    class="rounded-full border border-border bg-surface px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-text-secondary transition-all hover:text-text-primary"
                                    onClick={() => void copyFocusedTrace()}
                                  >
                                    {copiedTraceKey() === focusedIdentity.key ? 'Trace Copied' : 'Copy Trace'}
                                  </button>
                                  <button
                                    class="rounded-full border border-border bg-surface px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-text-secondary transition-all hover:text-text-primary"
                                    onClick={() => setFocusedActionKey(null)}
                                  >
                                    Clear Focus
                                  </button>
                                </div>
                              </div>
                              <div class="mt-3 flex flex-wrap gap-2 text-[10px] font-medium text-text-secondary">
                                <Show when={focused.skill_version}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">v{focused.skill_version}</span>
                                </Show>
                                <Show when={focused.lifecycle_phase}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">phase: {focused.lifecycle_phase}</span>
                                </Show>
                                <Show when={focused.sequence != null}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">seq: {focused.sequence}</span>
                                </Show>
                                <Show when={getActionStateTimestampLabel(focused)}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">
                                    updated: {getActionStateTimestampLabel(focused)}
                                  </span>
                                </Show>
                                <Show when={focused.request_id}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">request: {focused.request_id}</span>
                                </Show>
                                <Show when={focused.approval_token}>
                                  <span class="rounded-full border border-border bg-background px-2 py-1">approval token attached</span>
                                </Show>
                              </div>
                              <Show when={focusedArgs}>
                                <div class="mt-4 rounded-xl border border-border bg-background/80 p-3">
                                  <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">Tool Arguments</div>
                                  <pre class="mt-2 whitespace-pre-wrap break-words text-[11px] leading-relaxed text-text-primary">{JSON.stringify(focusedArgs, null, 2)}</pre>
                                </div>
                              </Show>
                              <Show when={focusedSections.length > 0}>
                                <div class="mt-4 space-y-3">
                                  <For each={focusedSections}>
                                    {(section) => (
                                      <div class={`rounded-xl border p-3 ${getActionDetailClasses(section.tone)}`}>
                                        <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">{section.title}</div>
                                        <pre class="mt-2 whitespace-pre-wrap break-words text-[11px] leading-relaxed text-text-primary">{section.content}</pre>
                                      </div>
                                    )}
                                  </For>
                                </div>
                              </Show>
                              <div class="mt-4 rounded-xl border border-border bg-background/80 p-3">
                                <div class="flex items-center justify-between gap-3">
                                  <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">Raw Trace Payload</div>
                                  <span class="text-[10px] text-text-secondary">exportable for debugging and handoff</span>
                                </div>
                                <pre class="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words text-[11px] leading-relaxed text-text-primary">{getActionStateTracePayload(focused)}</pre>
                              </div>
                              <Show when={canResolveActionState(focused)}>
                                <div class="mt-4 flex gap-2">
                                  <button
                                    class="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] font-black uppercase tracking-wide text-emerald-700 transition-all hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                                    disabled={props.isTyping}
                                    onClick={() => props.onResolveAction(focused, true)}
                                  >
                                    Approve
                                  </button>
                                  <button
                                    class="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] font-black uppercase tracking-wide text-rose-700 transition-all hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                                    disabled={props.isTyping}
                                    onClick={() => props.onResolveAction(focused, false)}
                                  >
                                    Reject
                                  </button>
                                </div>
                              </Show>
                            </div>
                          );
                        }}
                      </Show>
                      <For each={visibleActionGroups()}>
                        {(group) => {
                          const latestTone = getActionStateTone(group.latest);
                          const expanded = isGroupExpanded(group.key);
                          const visibleStates = getVisibleActionGroupStates(group, expanded, getVisibleInvocationCount(group.key));
                          const hiddenCount = getHiddenActionGroupCount(group, expanded, getVisibleInvocationCount(group.key));
                          return (
                            <div class="px-5 py-4 bg-background border border-border/60 rounded-2xl transition-all">
                              <div class="flex items-start justify-between gap-3">
                                <div class="min-w-0">
                                  <div class="text-[13px] font-bold text-text-primary break-all">
                                    {group.label}
                                  </div>
                                  <div class="mt-1 text-[11px] text-text-secondary">
                                    {group.states.length > 1
                                      ? `${group.states.length} invocations tracked for this tool-backed action.`
                                      : 'Single invocation tracked for this tool-backed action.'}
                                  </div>
                                </div>
                                <span class={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${getActionToneClasses(latestTone)}`}>
                                  Latest: {getActionStateLabel(group.latest)}
                                </span>
                              </div>
                              <div class="mt-3 flex items-center justify-between gap-3">
                                <div class="text-[11px] text-text-secondary">
                                  {expanded
                                    ? `Showing ${visibleStates.length} of ${group.states.length} invocations`
                                    : `Showing latest invocation of ${group.states.length}`}
                                </div>
                                <Show when={group.states.length > 1}>
                                  <button
                                    class="rounded-full border border-border bg-surface px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-text-secondary transition-all hover:text-text-primary"
                                    onClick={() => toggleGroupExpanded(group.key)}
                                  >
                                    {expanded ? 'Collapse History' : 'Expand History'}
                                  </button>
                                </Show>
                              </div>
                              <div class="mt-4 space-y-3">
                                <For each={visibleStates}>
                                  {(action, index) => {
                                    const tone = getActionStateTone(action);
                                    const actionArgs = getActionStateArgs(action);
                                    const actionDetailSections = getActionStateDetailSections(action);
                                    const actionTraceIdentity = getActionStateTraceIdentity(action);
                                    return (
                                      <div class="rounded-2xl border border-border bg-surface/60 p-4">
                                        <div class="flex items-start justify-between gap-3">
                                          <div class="min-w-0">
                                            <div class="text-[11px] font-black uppercase tracking-[0.16em] text-text-secondary">
                                              Invocation {group.states.length - index()}
                                            </div>
                                            <div class="mt-1 font-mono text-[11px] text-text-primary">
                                              {getActionStateDisplayId(action)}
                                            </div>
                                          </div>
                                          <span class={`shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${getActionToneClasses(tone)}`}>
                                            {getActionStateLabel(action)}
                                          </span>
                                        </div>
                                        <div class="mt-3 flex flex-wrap gap-2 text-[10px] font-medium text-text-secondary">
                                          <Show when={action.skill_version}>
                                            <span class="rounded-full bg-background px-2 py-1 border border-border">v{action.skill_version}</span>
                                          </Show>
                                          <Show when={action.lifecycle_phase}>
                                            <span class="rounded-full bg-background px-2 py-1 border border-border">
                                              phase: {action.lifecycle_phase}
                                            </span>
                                          </Show>
                                          <Show when={action.sequence != null}>
                                            <span class="rounded-full bg-background px-2 py-1 border border-border">
                                              seq: {action.sequence}
                                            </span>
                                          </Show>
                                          <Show when={action.approval_token}>
                                            <span class="rounded-full bg-background px-2 py-1 border border-border">
                                              approval token attached
                                            </span>
                                          </Show>
                                          <Show when={getActionStateTimestampLabel(action)}>
                                            <span class="rounded-full bg-background px-2 py-1 border border-border">
                                              updated: {getActionStateTimestampLabel(action)}
                                            </span>
                                          </Show>
                                        </div>
                                        <Show when={actionArgs}>
                                          <div class="mt-3 rounded-xl border border-border bg-background/80 p-3">
                                            <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">Tool Arguments</div>
                                            <pre class="mt-2 whitespace-pre-wrap break-words text-[11px] leading-relaxed text-text-primary">{JSON.stringify(actionArgs, null, 2)}</pre>
                                          </div>
                                        </Show>
                                        <Show when={actionDetailSections.length > 0}>
                                          <div class="mt-3 space-y-3">
                                            <For each={actionDetailSections}>
                                              {(section) => (
                                                <div class={`rounded-xl border p-3 ${getActionDetailClasses(section.tone)}`}>
                                                  <div class="text-[10px] font-black uppercase tracking-[0.16em] text-text-secondary">{section.title}</div>
                                                  <pre class="mt-2 whitespace-pre-wrap break-words text-[11px] leading-relaxed text-text-primary">{section.content}</pre>
                                                </div>
                                              )}
                                            </For>
                                          </div>
                                        </Show>
                                        <Show when={canResolveActionState(action)}>
                                          <div class="mt-3 flex gap-2">
                                            <button
                                              class="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] font-black uppercase tracking-wide text-emerald-700 transition-all hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-50"
                                              disabled={props.isTyping}
                                              onClick={() => props.onResolveAction(action, true)}
                                            >
                                              Approve
                                            </button>
                                            <button
                                              class="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] font-black uppercase tracking-wide text-rose-700 transition-all hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                                              disabled={props.isTyping}
                                              onClick={() => props.onResolveAction(action, false)}
                                            >
                                              Reject
                                            </button>
                                          </div>
                                        </Show>
                                        <div class="mt-3 flex justify-end">
                                          <button
                                            class={`rounded-full border px-3 py-1.5 text-[10px] font-black uppercase tracking-wide transition-all ${
                                              focusedActionKey() === actionTraceIdentity.key
                                                ? 'border-primary bg-primary/10 text-primary'
                                                : 'border-border bg-surface text-text-secondary hover:text-text-primary'
                                            }`}
                                            onClick={() => setFocusedActionKey(actionTraceIdentity.key)}
                                          >
                                            {focusedActionKey() === actionTraceIdentity.key ? 'Focused Trace' : 'Inspect Trace'}
                                          </button>
                                        </div>
                                      </div>
                                    );
                                  }}
                                </For>
                              </div>
                              <Show when={expanded && hiddenCount > 0}>
                                <div class="mt-3 flex justify-center">
                                  <button
                                    class="rounded-full border border-border bg-surface px-3 py-1.5 text-[10px] font-black uppercase tracking-wide text-text-secondary transition-all hover:text-text-primary"
                                    onClick={() => showMoreInvocations(group.key)}
                                  >
                                    Show {Math.min(EXPANDED_VISIBLE_INVOCATIONS, hiddenCount)} More
                                  </button>
                                </div>
                              </Show>
                            </div>
                          );
                        }}
                      </For>
                        </div>
                      </Show>
                    </div>
                  </Show>
                </div>

                <div class="pt-4 border-t border-border/40">
                  <div class="flex items-center justify-between mb-4">
                    <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Connected Nodes</h4>
                    <span class="text-[9px] font-bold bg-primary/10 text-primary px-2 py-0.5 rounded-full tracking-tighter">{groupedActionStates().length} TRACKED</span>
                  </div>
                  <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                    <p class="text-xs text-text-secondary/60 font-medium italic">
                      Current action panel reflects only existing tool/MCP-backed skill states.
                    </p>
                  </div>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'notes'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Related Notes</h4>
                  <button class="text-[10px] font-bold text-primary hover:underline">View All</button>
                </div>
                <div class="bg-background/50 border border-dashed border-border rounded-2xl p-8 text-center">
                  <p class="text-xs text-text-secondary/60 font-medium italic">No related notes found</p>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'graph'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Knowledge Graph</h4>
                <div class="aspect-square bg-background/50 border border-border rounded-2xl flex items-center justify-center p-8 text-center">
                  <div>
                    <div class="w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                    <p class="text-xs text-text-secondary/60 font-medium">Graph visualization will appear here as entities are discovered.</p>
                  </div>
                </div>
              </div>
            </Match>

            <Match when={props.intelligenceTab === 'stats'}>
              <div class="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
                <div class="flex items-center justify-between">
                  <h4 class="text-[10px] font-black text-text-secondary uppercase tracking-[0.2em]">Performance Statistics</h4>
                  <Show when={props.lastMessage?.model}>
                    <span class="text-[9px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded-full">{props.lastMessage?.model}</span>
                  </Show>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div class="bg-surface border border-border rounded-2xl p-4 shadow-sm relative overflow-hidden group">
                    <div class="absolute inset-0 bg-primary/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                    <div class="relative">
                      <div class="text-[10px] font-black text-text-secondary uppercase tracking-wider mb-1">Tokens/Sec</div>
                      <div class="text-2xl font-black text-primary leading-none flex items-baseline gap-1">
                        {props.lastMessage?.tps?.toFixed(1) || '0.0'}
                        <span class="text-[10px] text-primary/60 font-bold">TPS</span>
                      </div>
                      {/* Simple visual indicator for TPS */}
                      <div class="mt-2 flex gap-0.5 h-1 items-end">
                        <For each={Array(10).fill(0)}>
                          {(_, i) => (
                            <div 
                              class={`flex-1 rounded-full transition-all duration-500 ${
                                (props.lastMessage?.tps || 0) / 10 > i() ? 'bg-primary' : 'bg-primary/10'
                              }`}
                              style={{ height: `${20 + i() * 8}%` }}
                            ></div>
                          )}
                        </For>
                      </div>
                    </div>
                  </div>
                  <div class="bg-surface border border-border rounded-2xl p-4 shadow-sm relative overflow-hidden group">
                    <div class="absolute inset-0 bg-text-primary/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500"></div>
                    <div class="relative">
                      <div class="text-[10px] font-black text-text-secondary uppercase tracking-wider mb-1">Total Tokens</div>
                      <div class="text-2xl font-black text-text-primary leading-none flex items-baseline gap-1">
                        {props.lastMessage?.total_tokens || '0'}
                        <span class="text-[10px] text-text-secondary/60 font-bold">SUM</span>
                      </div>
                      {/* Mini bar chart placeholder for total */}
                      <div class="mt-2 flex gap-0.5 h-1 items-end">
                         <div class="w-full h-1 bg-text-primary/10 rounded-full overflow-hidden">
                           <div class="h-full bg-text-primary/30 rounded-full" style={{ width: '60%' }}></div>
                         </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="space-y-4 bg-surface border border-border rounded-2xl p-5 shadow-sm relative overflow-hidden group">
                  <div class="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full -mr-16 -mt-16 blur-2xl group-hover:bg-primary/10 transition-colors duration-700"></div>
                  
                  <div class="flex items-center gap-6 relative">
                    {/* Donut Chart for Token Distribution */}
                    <div class="relative w-20 h-20 shrink-0">
                      <svg class="w-full h-full -rotate-90" viewBox="0 0 36 36">
                        <circle cx="18" cy="18" r="16" fill="none" class="stroke-background" stroke-width="3.5"></circle>
                        <circle 
                          cx="18" cy="18" r="16" fill="none" 
                          class="stroke-primary/30" stroke-width="3.5"
                          stroke-dasharray={`${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100} 100`}
                        ></circle>
                        <circle 
                          cx="18" cy="18" r="16" fill="none" 
                          class="stroke-primary" stroke-width="3.5"
                          stroke-dasharray={`${(props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100} 100`}
                          stroke-dashoffset={`-${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}`}
                        ></circle>
                      </svg>
                      <div class="absolute inset-0 flex flex-col items-center justify-center">
                        <span class="text-[10px] font-black text-text-primary leading-none">
                          {Math.round(((props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1)) * 100)}%
                        </span>
                        <span class="text-[7px] font-bold text-text-secondary uppercase tracking-tighter">Out</span>
                      </div>
                    </div>

                    <div class="flex-1 space-y-3">
                      <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px]">
                          <div class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-primary/40"></div>
                            <span class="font-bold text-text-secondary uppercase tracking-wider">Prompt</span>
                          </div>
                          <span class="font-mono text-text-primary">{props.lastMessage?.prompt_tokens || 0}</span>
                        </div>
                        <div class="w-full h-1 bg-background rounded-full overflow-hidden">
                          <div 
                            class="h-full bg-primary/40 rounded-full transition-all duration-1000" 
                            style={{ width: `${(props.lastMessage?.prompt_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}%` }}
                          />
                        </div>
                      </div>
                      
                      <div class="space-y-1">
                        <div class="flex items-center justify-between text-[11px]">
                          <div class="flex items-center gap-1.5">
                            <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
                            <span class="font-bold text-text-secondary uppercase tracking-wider">Completion</span>
                          </div>
                          <span class="font-mono text-text-primary">{props.lastMessage?.completion_tokens || 0}</span>
                        </div>
                        <div class="w-full h-1 bg-background rounded-full overflow-hidden">
                          <div 
                            class="h-full bg-primary rounded-full transition-all duration-1000" 
                            style={{ width: `${(props.lastMessage?.completion_tokens || 0) / (props.lastMessage?.total_tokens || 1) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <Show when={props.lastMessage?.finish_reason}>
                  <div class="bg-background/50 border border-border rounded-2xl p-4 flex items-center justify-between">
                    <span class="text-[10px] font-black text-text-secondary uppercase tracking-wider">Finish Reason</span>
                    <span class="text-[10px] font-mono font-bold text-primary uppercase">{props.lastMessage?.finish_reason}</span>
                  </div>
                </Show>

                <Show when={props.lastMessage?.thought_duration}>
                   <div class="bg-background/50 border border-border rounded-2xl p-4 flex items-center justify-between">
                     <span class="text-[10px] font-black text-text-secondary uppercase tracking-wider">Thinking Time</span>
                     <span class="text-[10px] font-mono font-bold text-text-primary">{(props.lastMessage?.thought_duration || 0) / 1000}s</span>
                   </div>
                 </Show>
              </div>
            </Match>
          </Switch>
        </div>
      </div>
    </div>
  );
}
