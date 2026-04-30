import { describe, expect, it, vi } from 'vitest';

// @ts-ignore -- IDE diagnostics intermittently fail to resolve sibling .tsx module in this workspace layout.
import {
  copyFixCommandsToClipboard,
  getExcalidrawHealthSummary,
  filterPreflightRecords,
  formatMountErrorMessage,
  groupPreflightRecordsByAvailability,
  getMountActionState,
  getRecordStatusMessage,
  getVisibilityStateLabel,
  mountSkillToAgent,
  rescanSkillPreflight,
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
