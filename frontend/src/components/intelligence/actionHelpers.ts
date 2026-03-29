import { ActionState } from '../../types';

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
  kind?: 'text' | 'link' | 'image';
  href?: string;
  alt?: string;
};

type StructuredRecord = Record<string, unknown>;

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

export const COLLAPSED_VISIBLE_INVOCATIONS = 1;
export const EXPANDED_VISIBLE_INVOCATIONS = 3;

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
  const isImageArtifact = /\.(png|jpe?g|gif|webp|svg)$/i.test(downloadUrl || filename || filePath);

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
      kind: 'link',
      href: downloadUrl,
    });
  }
  if (downloadUrl && isImageArtifact) {
    sections.push({
      title: 'Preview',
      tone,
      content: downloadUrl,
      kind: 'image',
      href: downloadUrl,
      alt: filename || 'artifact preview',
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

const buildBrowserSnapshotDetailSections = (
  rawValue: unknown,
  tone: 'emerald' | 'rose',
): ActionDetailSection[] => {
  const parsed = tryParseStructuredPayload(rawValue);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return [];
  const payload = parsed as Record<string, unknown>;
  const snapshot = asStructuredRecord(payload.snapshot);
  if (!snapshot) return [];

  const sections: ActionDetailSection[] = [];
  const browserContext = asStructuredRecord(payload.browser_context);
  const bindingContext = asStructuredRecord(snapshot.target_binding_context);
  const interactiveElements = Array.isArray(snapshot.interactive_elements)
    ? snapshot.interactive_elements.filter((item): item is StructuredRecord => !!item && typeof item === 'object')
    : [];
  const visibleText = getStringValue(snapshot.visible_text);

  const snapshotLines = [
    getStringValue(browserContext?.url) ? `url: ${getStringValue(browserContext?.url)}` : '',
    getStringValue(browserContext?.page_title) ? `page title: ${getStringValue(browserContext?.page_title)}` : '',
    typeof snapshot.max_nodes === 'number' ? `max nodes: ${String(snapshot.max_nodes)}` : '',
    `interactive elements: ${interactiveElements.length}`,
  ].filter(Boolean);
  if (snapshotLines.length > 0) {
    sections.push({
      title: 'Snapshot Summary',
      tone,
      content: snapshotLines.join('\n'),
    });
  }

  if (interactiveElements.length > 0) {
    const interactiveLines = interactiveElements.slice(0, 12).map((item, index) => {
      const ref = getStringValue(item.ref) || `node-${index + 1}`;
      const tag = getStringValue(item.tag);
      const text = getStringValue(item.text);
      const aria = getStringValue(item.aria_label);
      const name = getStringValue(item.name);
      const id = getStringValue(item.id);
      const parts = [
        `${index + 1}. ${ref}`,
        tag ? `tag=${tag}` : '',
        text ? `text=${text}` : '',
        aria ? `aria=${aria}` : '',
        name ? `name=${name}` : '',
        id ? `id=${id}` : '',
      ].filter(Boolean);
      return parts.join(' | ');
    });
    if (interactiveElements.length > 12) {
      interactiveLines.push(`... ${interactiveElements.length - 12} more elements`);
    }
    sections.push({
      title: 'Interactive Elements',
      tone,
      content: interactiveLines.join('\n'),
    });
  }

  if (visibleText) {
    sections.push({
      title: 'Visible Text',
      tone: 'slate',
      content: visibleText,
    });
  }

  const bindingLines = [
    getStringValue(bindingContext?.binding_source) ? `binding_source: ${getStringValue(bindingContext?.binding_source)}` : '',
    getStringValue(bindingContext?.binding_session_id)
      ? `binding_session_id: ${getStringValue(bindingContext?.binding_session_id)}`
      : '',
    getStringValue(bindingContext?.binding_tab_id) ? `binding_tab_id: ${getStringValue(bindingContext?.binding_tab_id)}` : '',
    getStringValue(bindingContext?.binding_url) ? `binding_url: ${getStringValue(bindingContext?.binding_url)}` : '',
    getStringValue(bindingContext?.binding_dom_version)
      ? `binding_dom_version: ${getStringValue(bindingContext?.binding_dom_version)}`
      : '',
  ].filter(Boolean);
  if (bindingLines.length > 0) {
    sections.push({
      title: 'Snapshot Binding Context',
      tone: 'slate',
      content: bindingLines.join('\n'),
    });
  }

  return sections;
};

const asStructuredRecord = (value: unknown): StructuredRecord | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as StructuredRecord;
};

const getBrowserMetadata = (state: ActionState): StructuredRecord | null => {
  const metadata = asStructuredRecord(state.payload?.metadata);
  if (!metadata) return null;
  if (typeof metadata.tool_family === 'string' && metadata.tool_family === 'agent_browser') {
    return metadata;
  }
  const runtimeMetadata = asStructuredRecord(metadata.runtime_metadata);
  if (runtimeMetadata) return metadata;
  return null;
};

const getBrowserArgs = (state: ActionState): StructuredRecord => {
  return (getActionStateArgs(state) || {}) as StructuredRecord;
};

const getStringValue = (value: unknown): string => (typeof value === 'string' && value.trim() ? value : '');

const buildBrowserContractSections = (state: ActionState): ActionDetailSection[] => {
  const metadata = getBrowserMetadata(state);
  if (!metadata) return [];

  const runtimeMetadata = asStructuredRecord(metadata.runtime_metadata) || {};
  const expectations = asStructuredRecord(metadata.runtime_metadata_expectations) || {};
  const continuity = asStructuredRecord(metadata.browser_continuity) || {};
  const continuityResolution = asStructuredRecord(metadata.browser_continuity_resolution) || {};
  const continuityResolver = asStructuredRecord(metadata.browser_continuity_resolver) || {};
  const resolvedContext = asStructuredRecord(continuityResolution.resolved_context) || {};
  const args = getBrowserArgs(state);

  const operation = getStringValue(metadata.operation) || getStringValue(runtimeMetadata.operation);
  const toolFamily = getStringValue(metadata.tool_family) || getStringValue(runtimeMetadata.tool_family);
  const mappedTool = getActionMappedTool(state) || getStringValue(runtimeMetadata.mapped_tool);
  const summaryLines = [
    operation ? `operation: ${operation}` : '',
    toolFamily ? `tool family: ${toolFamily}` : '',
    mappedTool ? `mapped tool: ${mappedTool}` : '',
  ].filter(Boolean);

  const url = getStringValue(runtimeMetadata.url) || getStringValue(args.url);
  const elementRef = getStringValue(runtimeMetadata.element_ref) || getStringValue(args.element_ref);
  const key = getStringValue(runtimeMetadata.key) || getStringValue(args.key);
  const text = getStringValue(runtimeMetadata.text) || getStringValue(args.text);
  const sessionId = getStringValue(runtimeMetadata.session_id) || getStringValue(args.session_id);
  const tabId = getStringValue(runtimeMetadata.tab_id) || getStringValue(args.tab_id);
  const label = getStringValue(runtimeMetadata.label) || getStringValue(args.label);

  const targetLines = [
    url ? `url: ${url}` : '',
    elementRef ? `element_ref: ${elementRef}` : '',
    key ? `key: ${key}` : '',
    text ? `text: ${text}` : '',
    label ? `label: ${label}` : '',
  ].filter(Boolean);

  const contextLines = [
    sessionId ? `session_id: ${sessionId}` : '',
    tabId ? `tab_id: ${tabId}` : '',
  ].filter(Boolean);

  const expectationLines = [
    Array.isArray(expectations.required) && expectations.required.length > 0
      ? `required: ${expectations.required.join(', ')}`
      : '',
    Array.isArray(expectations.optional) && expectations.optional.length > 0
      ? `optional: ${expectations.optional.join(', ')}`
      : '',
  ].filter(Boolean);

  const continuityLines = [
    getStringValue(continuity.contract_mode) ? `contract mode: ${getStringValue(continuity.contract_mode)}` : '',
    getStringValue(continuity.current_execution_mode)
      ? `current execution mode: ${getStringValue(continuity.current_execution_mode)}`
      : '',
    typeof continuity.authoritative_target_required === 'boolean'
      ? `authoritative target required: ${String(continuity.authoritative_target_required)}`
      : '',
    getStringValue(continuity.resumable_continuity)
      ? `resumable continuity: ${getStringValue(continuity.resumable_continuity)}`
      : '',
  ].filter(Boolean);

  const continuityResolutionLines = [
    getStringValue(continuityResolution.resolution_mode)
      ? `resolution mode: ${getStringValue(continuityResolution.resolution_mode)}`
      : '',
    getStringValue(continuityResolution.continuity_status)
      ? `continuity status: ${getStringValue(continuityResolution.continuity_status)}`
      : '',
    getStringValue(continuityResolver.resolver_id)
      ? `resolver: ${getStringValue(continuityResolver.resolver_id)}`
      : '',
    getStringValue(continuityResolver.status)
      ? `resolver status: ${getStringValue(continuityResolver.status)}`
      : '',
    typeof continuityResolver.resolved === 'boolean'
      ? `resolver resolved: ${String(continuityResolver.resolved)}`
      : '',
    Array.isArray(continuityResolution.missing_context) && continuityResolution.missing_context.length > 0
      ? `missing context: ${continuityResolution.missing_context.join(', ')}`
      : '',
  ].filter(Boolean);

  const resolvedContextLines = [
    getStringValue(resolvedContext.resolved_context_id)
      ? `resolved_context_id: ${getStringValue(resolvedContext.resolved_context_id)}`
      : '',
    getStringValue(resolvedContext.session_id) ? `session_id: ${getStringValue(resolvedContext.session_id)}` : '',
    getStringValue(resolvedContext.tab_id) ? `tab_id: ${getStringValue(resolvedContext.tab_id)}` : '',
    getStringValue(resolvedContext.element_ref) ? `element_ref: ${getStringValue(resolvedContext.element_ref)}` : '',
    getStringValue(resolvedContext.resolution_mode)
      ? `resolution mode: ${getStringValue(resolvedContext.resolution_mode)}`
      : '',
    getStringValue(resolvedContext.resolution_source)
      ? `resolution source: ${getStringValue(resolvedContext.resolution_source)}`
      : '',
    getStringValue(resolvedContext.resolved_target_kind)
      ? `resolved target kind: ${getStringValue(resolvedContext.resolved_target_kind)}`
      : '',
  ].filter(Boolean);

  const sections: ActionDetailSection[] = [];
  if (summaryLines.length > 0) {
    sections.push({
      title: 'Browser Contract',
      tone: 'slate',
      content: summaryLines.join('\n'),
    });
  }
  if (targetLines.length > 0) {
    sections.push({
      title: 'Browser Target',
      tone: 'slate',
      content: targetLines.join('\n'),
    });
  }
  if (contextLines.length > 0) {
    sections.push({
      title: 'Browser Context',
      tone: 'slate',
      content: contextLines.join('\n'),
    });
  }
  if (expectationLines.length > 0) {
    sections.push({
      title: 'Runtime Metadata Contract',
      tone: 'slate',
      content: expectationLines.join('\n'),
    });
  }
  if (continuityLines.length > 0) {
    sections.push({
      title: 'Browser Continuity',
      tone: 'slate',
      content: continuityLines.join('\n'),
    });
  }
  if (continuityResolutionLines.length > 0) {
    sections.push({
      title: 'Browser Continuity Resolution',
      tone: 'slate',
      content: continuityResolutionLines.join('\n'),
    });
  }
  if (resolvedContextLines.length > 0) {
    sections.push({
      title: 'Resolved Browser Context',
      tone: 'slate',
      content: resolvedContextLines.join('\n'),
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
  const browserContractSections = buildBrowserContractSections(state);

  if (browserContractSections.length > 0) {
    sections.push(...browserContractSections);
  }

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
            : mappedTool === 'builtin:browser_snapshot'
              ? buildBrowserSnapshotDetailSections(metadata?.tool_error, 'rose')
            : mappedTool === 'builtin:generate_pptx' || mappedTool === 'builtin:browser_screenshot'
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
            : mappedTool === 'builtin:browser_snapshot'
              ? buildBrowserSnapshotDetailSections(metadata?.tool_result, 'emerald')
            : mappedTool === 'builtin:generate_pptx' || mappedTool === 'builtin:browser_screenshot'
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

export const getActionToneClasses = (tone: string): string => {
  if (tone === 'amber') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (tone === 'rose') return 'border-rose-200 bg-rose-50 text-rose-700';
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return 'border-slate-200 bg-slate-50 text-slate-700';
};

export const getActionDetailClasses = (tone: ActionDetailSection['tone']): string => {
  if (tone === 'rose') return 'border-rose-200 bg-rose-50/70';
  if (tone === 'emerald') return 'border-emerald-200 bg-emerald-50/70';
  return 'border-border bg-background/80';
};
