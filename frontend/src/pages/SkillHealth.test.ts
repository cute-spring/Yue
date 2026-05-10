import { describe, expect, it, vi } from 'vitest';

// @ts-ignore -- IDE diagnostics intermittently fail to resolve sibling .tsx module in this workspace layout.
import {
  canInstallCandidateDirectly,
  copyFixCommandsToClipboard,
  getExcalidrawHealthSummary,
  filterPreflightRecords,
  formatImportErrorMessage,
  formatImportSuccessMessage,
  formatInstallCandidateSelectionMessage,
  formatSetupErrorMessage,
  formatMountErrorMessage,
  getSkillInstallCandidates,
  getSkillPreflightRecordAnchorId,
  getSkillRecordCardClass,
  getSkillStatusBadge,
  SKILL_RECORD_HIGHLIGHT_DURATION_MS,
  getSetupLastFailureMessage,
  groupPreflightRecordsByAvailability,
  getMountActionState,
  getRecordStatusMessage,
  getSetupActionState,
  getSetupStatusMessage,
  getSetupSupportMessage,
  getTrustStatusMessage,
  getVisibilityStateLabel,
  importSkillFromPath,
  mountSkillToAgent,
  rescanSkillPreflight,
  trustAndSetupSkill,
  type SkillPreflightRecord,
} from './SkillHealth';

const sampleRecords: SkillPreflightRecord[] = [
  {
    skill_name: 'ok-skill',
    skill_version: '1.0.0',
    skill_ref: 'ok-skill:1.0.0',
    source_path: '/tmp/ok-skill',
    source_layer: 'workspace',
    status: 'available',
    issues: [],
    warnings: [],
    suggestions: [],
    status_message: 'Ready to mount.',
    next_action: 'Mount this skill to the default agent.',
    visible_in_default_agent: false,
    setup_capable: false,
    setup_required: false,
    trust_status: 'untrusted',
    setup_status: 'not_needed',
    setup_supported_runtimes: [],
    checked_at: '2026-04-25T00:00:00Z',
  },
  {
    skill_name: 'fix-skill',
    skill_version: '1.0.0',
    skill_ref: 'fix-skill:1.0.0',
    source_path: '/tmp/fix-skill',
    source_layer: 'user',
    status: 'needs_fix',
    issues: ['missing binary'],
    warnings: [],
    suggestions: [],
    status_message: 'missing binary',
    next_action: 'Resolve listed issues, then rerun preflight.',
    visible_in_default_agent: false,
    setup_capable: true,
    setup_required: true,
    trust_status: 'untrusted',
    setup_status: 'available',
    setup_supported_runtimes: ['python'],
    setup_status_message: 'Setup requires explicit trust.',
    setup_next_action: 'Trust this skill, then run setup.',
    checked_at: '2026-04-25T00:00:00Z',
  },
];

describe('SkillHealth helpers', () => {
  it('filters records by status and keyword', () => {
    const filtered = filterPreflightRecords(sampleRecords, {
      status: 'needs_fix',
      sourceLayer: 'all',
      query: 'fix',
    });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].skill_ref).toBe('fix-skill:1.0.0');
  });

  it('returns disabled mount action when skill is not available', () => {
    expect(getMountActionState('needs_fix')).toEqual({
      label: 'Needs Fix',
      disabled: true,
    });
    expect(getMountActionState('unavailable')).toEqual({
      label: 'Unavailable',
      disabled: true,
    });
  });

  it('mounts skill successfully', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ mount_status: 'mounted' }),
    }));
    const result = await mountSkillToAgent('ok-skill:1.0.0', 'builtin-action-lab', fetchMock as any);
    expect(fetchMock).toHaveBeenCalledWith('/api/skill-preflight/ok-skill:1.0.0/mount', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: 'builtin-action-lab' }),
    });
    expect(result).toEqual({ ok: true, mountStatus: 'mounted', error: null });
  });

  it('returns normalized error when mount request fails', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      json: async () => ({ detail: 'skill_preflight_not_mountable' }),
    }));
    const result = await mountSkillToAgent('fix-skill:1.0.0', 'builtin-action-lab', fetchMock as any);
    expect(result).toEqual({
      ok: false,
      mountStatus: null,
      error: 'skill_preflight_not_mountable',
    });
  });

  it('extracts error code from structured backend detail payload', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      json: async () => ({
        detail: {
          code: 'agent_not_found',
          message: 'Target agent was not found.',
          next_action: 'Use an existing agent id.',
        },
      }),
    }));
    const result = await mountSkillToAgent('ok-skill:1.0.0', 'missing-agent', fetchMock as any);
    expect(result).toEqual({
      ok: false,
      mountStatus: null,
      error: 'agent_not_found',
    });
  });

  it('maps mount error code to actionable text', () => {
    expect(formatMountErrorMessage('skill_preflight_not_mountable')).toContain('Fix preflight issues');
    expect(formatMountErrorMessage('agent_not_found')).toContain('Target agent');
  });

  it('derives trust-and-setup action state from backend contract', () => {
    expect(getSetupActionState(sampleRecords[0])).toEqual({
      visible: false,
      label: 'Setup Unsupported',
      disabled: true,
    });
    expect(getSetupActionState(sampleRecords[1])).toEqual({
      visible: true,
      label: 'Trust & Setup',
      disabled: false,
    });
    expect(
      getSetupActionState({
        ...sampleRecords[1],
        trust_status: 'trusted',
        setup_status: 'failed',
      }),
    ).toEqual({
      visible: true,
      label: 'Retry Setup',
      disabled: false,
    });
    expect(
      getSetupActionState({
        ...sampleRecords[1],
        trust_status: 'trusted',
        setup_status: 'succeeded',
      }),
    ).toEqual({
      visible: false,
      label: 'Setup Complete',
      disabled: true,
    });
  });

  it('describes trusted setup support, trust state, and last failure separately', () => {
    expect(getSetupSupportMessage(sampleRecords[0])).toBe('Trusted setup support: Not supported.');
    expect(getTrustStatusMessage(sampleRecords[0])).toBe('Trusted: No');
    expect(getSetupLastFailureMessage(sampleRecords[0])).toBeNull();

    expect(getSetupSupportMessage(sampleRecords[1])).toBe('Trusted setup support: Supported (python).');
    expect(getTrustStatusMessage(sampleRecords[1])).toBe('Trusted: No');
    expect(getSetupLastFailureMessage(sampleRecords[1])).toBeNull();

    expect(
      getSetupLastFailureMessage({
        ...sampleRecords[1],
        setup_status: 'failed',
        setup_last_error: 'pip install failed',
      }),
    ).toBe('pip install failed');
  });

  it('prefers backend setup status message when present', () => {
    expect(getSetupStatusMessage(sampleRecords[1])).toBe('Setup requires explicit trust.');
    expect(
      getSetupStatusMessage({
        ...sampleRecords[1],
        setup_status_message: '',
        setup_last_error: 'pip install failed',
      }),
    ).toBe('pip install failed');
  });

  it('maps setup error code to actionable text', () => {
    expect(formatSetupErrorMessage('skill_setup_requires_trust')).toContain('Trust');
    expect(formatSetupErrorMessage('skill_setup_not_supported')).toContain('manifest');
  });

  it('imports skill successfully and exposes auto-mount details', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        import: { skill_name: 'fireworks-tech-graph', skill_version: '1.0.0' },
        report: {
          default_agent_mount_status: 'mounted',
          default_agent_mount_target_agent_id: 'builtin-action-lab',
          default_agent_mount_message: 'Skill was auto-mounted to Skill Playground (builtin-action-lab).',
        },
        default_agent_mount: {
          status: 'mounted',
          target_agent_id: 'builtin-action-lab',
          message: 'Skill was auto-mounted to Skill Playground (builtin-action-lab).',
        },
      }),
    }));

    const result = await importSkillFromPath('/tmp/fireworks-tech-graph', fetchMock as any);

    expect(fetchMock).toHaveBeenCalledWith('/api/skill-imports', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: 'directory', source_path: '/tmp/fireworks-tech-graph' }),
    });
    expect(result.ok).toBe(true);
    expect(result.payload?.default_agent_mount?.status).toBe('mounted');
    expect(formatImportSuccessMessage(result.payload!)).toContain('auto-mounted to Skill Playground');
  });

  it('returns normalized import error when request fails', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: false,
      json: async () => ({ detail: 'import_source_not_found' }),
    }));
    const result = await importSkillFromPath('/tmp/missing-skill', fetchMock as any);
    expect(result).toEqual({
      ok: false,
      payload: { detail: 'import_source_not_found' },
      error: 'import_source_not_found',
    });
    expect(formatImportErrorMessage(result.error)).toContain('not found');
  });

  it('builds install candidates from workspace skills, deduped by path', () => {
    const candidates = getSkillInstallCandidates([
      ...sampleRecords,
      {
        ...sampleRecords[1],
        skill_name: 'fix-skill-shadow',
        skill_ref: 'fix-skill-shadow:1.0.0',
        source_layer: 'workspace',
        source_path: '/tmp/ok-skill',
      },
      {
        ...sampleRecords[0],
        skill_name: 'alpha-skill',
        skill_ref: 'alpha-skill:1.0.0',
        source_path: '/tmp/alpha-skill',
      },
    ]);

    expect(candidates).toEqual([
      {
        skillRef: 'alpha-skill:1.0.0',
        skillName: 'alpha-skill',
        sourcePath: '/tmp/alpha-skill',
        status: 'available',
        statusMessage: 'Ready to mount.',
      },
      {
        skillRef: 'ok-skill:1.0.0',
        skillName: 'ok-skill',
        sourcePath: '/tmp/ok-skill',
        status: 'available',
        statusMessage: 'Ready to mount.',
      },
    ]);
  });

  it('maps skill status to suggestion badge styling', () => {
    expect(getSkillStatusBadge('available')).toEqual({
      label: 'Available',
      className: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    });
    expect(getSkillStatusBadge('needs_fix')).toEqual({
      label: 'Needs Fix',
      className: 'bg-amber-100 text-amber-700 border-amber-200',
    });
    expect(getSkillStatusBadge('unavailable')).toEqual({
      label: 'Unavailable',
      className: 'bg-rose-100 text-rose-700 border-rose-200',
    });
  });

  it('warns when selecting a non-ready install candidate', () => {
    expect(
      formatInstallCandidateSelectionMessage({
        skillRef: 'fix-skill:1.0.0',
        skillName: 'fix-skill',
        sourcePath: '/tmp/fix-skill',
        status: 'needs_fix',
        statusMessage: 'missing binary',
      }),
    ).toContain('Current issue: missing binary');
    expect(
      formatInstallCandidateSelectionMessage({
        skillRef: 'bad-skill:1.0.0',
        skillName: 'bad-skill',
        sourcePath: '/tmp/bad-skill',
        status: 'unavailable',
        statusMessage: 'parse failed',
      }),
    ).toContain('Current issue: parse failed');
    expect(
      formatInstallCandidateSelectionMessage({
        skillRef: 'ok-skill:1.0.0',
        skillName: 'ok-skill',
        sourcePath: '/tmp/ok-skill',
        status: 'available',
        statusMessage: 'Ready to mount.',
      }),
    ).toBeNull();
  });

  it('allows one-click install only for available suggestions', () => {
    expect(
      canInstallCandidateDirectly({
        skillRef: 'ok-skill:1.0.0',
        skillName: 'ok-skill',
        sourcePath: '/tmp/ok-skill',
        status: 'available',
        statusMessage: 'Ready to mount.',
      }),
    ).toBe(true);
    expect(
      canInstallCandidateDirectly({
        skillRef: 'fix-skill:1.0.0',
        skillName: 'fix-skill',
        sourcePath: '/tmp/fix-skill',
        status: 'needs_fix',
        statusMessage: 'missing binary',
      }),
    ).toBe(false);
  });

  it('builds a stable anchor id for each preflight record', () => {
    expect(getSkillPreflightRecordAnchorId('fix-skill:1.0.0')).toBe('skill-record-fix-skill%3A1.0.0');
  });

  it('returns highlighted card styling for focused records', () => {
    expect(getSkillRecordCardClass(true)).toContain('ring-2');
    expect(getSkillRecordCardClass(true)).toContain('bg-amber-50');
    expect(getSkillRecordCardClass(false)).not.toContain('ring-2');
    expect(SKILL_RECORD_HIGHLIGHT_DURATION_MS).toBe(2200);
  });

  it('separates visibility label from availability status', () => {
    expect(getVisibilityStateLabel(false)).toBe('Hidden in default agent');
    expect(getVisibilityStateLabel(true)).toBe('Visible in default agent');
  });

  it('prefers backend actionable status message when present', () => {
    expect(getRecordStatusMessage(sampleRecords[1])).toBe('missing binary');
  });

  it('rescans preflight records and returns summary and items', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        summary: { total: 2, available: 1, needs_fix: 1, unavailable: 0 },
        items: sampleRecords,
      }),
    }));
    const result = await rescanSkillPreflight(fetchMock as any);
    expect(fetchMock).toHaveBeenCalledWith('/api/skill-preflight/rescan', { method: 'POST' });
    expect(result.ok).toBe(true);
    expect(result.summary?.total).toBe(2);
    expect(result.items).toHaveLength(2);
  });

  it('trusts then runs setup for a skill', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ item: { ...sampleRecords[1], trust_status: 'trusted' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ item: { ...sampleRecords[1], trust_status: 'trusted', setup_status: 'succeeded' } }),
      });

    const result = await trustAndSetupSkill('fix-skill:1.0.0', fetchMock as any);

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/skill-preflight/fix-skill:1.0.0/trust', {
      method: 'POST',
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/skill-preflight/fix-skill:1.0.0/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    expect(result.ok).toBe(true);
    expect(result.item?.trust_status).toBe('trusted');
    expect(result.item?.setup_status).toBe('succeeded');
  });

  it('groups records by available vs non-available', () => {
    const groups = groupPreflightRecordsByAvailability([
      ...sampleRecords,
      {
        skill_name: 'bad-skill',
        skill_version: '1.0.0',
        skill_ref: 'bad-skill:1.0.0',
        source_path: '/tmp/bad-skill',
        source_layer: 'workspace',
        status: 'unavailable',
        issues: ['parse failed'],
        warnings: [],
        suggestions: [],
        status_message: 'parse failed',
        next_action: 'Fix and retry.',
      },
    ]);
    expect(groups.available.map((item: SkillPreflightRecord) => item.skill_ref)).toEqual(['ok-skill:1.0.0']);
    expect(groups.nonAvailable.map((item: SkillPreflightRecord) => item.skill_ref)).toEqual([
      'fix-skill:1.0.0',
      'bad-skill:1.0.0',
    ]);
  });

  it('summarizes excalidraw health level and blockers for UI', () => {
    const summary = getExcalidrawHealthSummary({
      ...sampleRecords[0],
      skill_name: 'excalidraw-diagram-generator',
      skill_ref: 'excalidraw-diagram-generator:1.0.0',
      excalidraw_health: {
        effective_level: 'L2',
        levels: ['L1', 'L2', 'L3'],
        blockers: [
          {
            code: 'script_dependency_missing',
            title: 'Script dependency missing',
            fix_command: 'python scripts/install-deps.py',
            fix_path: '/tmp/excalidraw/scripts',
          },
        ],
      },
    } as SkillPreflightRecord);
    expect(summary).toEqual({
      visible: true,
      effectiveLevel: 'L2',
      blockers: ['Script dependency missing'],
      repairCommands: ['python scripts/install-deps.py'],
    });
  });

  it('copies fix commands to clipboard as newline-delimited text', async () => {
    const writeText = vi.fn(async () => undefined);
    const ok = await copyFixCommandsToClipboard(['python scripts/a.py', 'python scripts/b.py'], {
      writeText,
    } as unknown as Clipboard);
    expect(ok).toBe(true);
    expect(writeText).toHaveBeenCalledWith('python scripts/a.py\npython scripts/b.py');
  });

  it('returns false when clipboard is unavailable or commands are empty', async () => {
    expect(await copyFixCommandsToClipboard([], null)).toBe(false);
    expect(await copyFixCommandsToClipboard(['   '], null)).toBe(false);
  });
});
