import { describe, expect, it } from 'vitest';

import { canResolveActionState, filterActionGroups, getActionStateArgs, getActionStateDetail, getActionStateDetailSections, getActionStateDisplayId, getActionStateLabel, getActionStateTimestampLabel, getActionStateTone, getActionStateTraceIdentity, getActionStateTracePayload, getHiddenActionGroupCount, getVisibleActionGroupStates, groupActionStates, sortActionStates, summarizeActionGroups } from './IntelligencePanel';

describe('IntelligencePanel action helpers', () => {
  it('maps approval states to amber tone', () => {
    expect(getActionStateTone({ lifecycle_status: 'awaiting_approval', status: 'awaiting_approval' })).toBe('amber');
  });

  it('maps blocked and failed states to rose tone', () => {
    expect(getActionStateTone({ lifecycle_status: 'preflight_blocked', status: 'blocked' })).toBe('rose');
    expect(getActionStateTone({ lifecycle_status: 'failed', status: 'failed' })).toBe('rose');
  });

  it('builds readable labels from lifecycle status', () => {
    expect(getActionStateLabel({ lifecycle_status: 'preflight_approval_required', status: 'approval_required' })).toBe('Preflight Approval Required');
  });

  it('sorts action states by latest sequence first', () => {
    const ordered = sortActionStates([
      {
        skill_name: 'docs',
        action_id: 'read',
        lifecycle_status: 'ready',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
      },
      {
        skill_name: 'docs',
        action_id: 'read',
        lifecycle_status: 'awaiting_approval',
        sequence: 30,
        ts: '2026-03-28T10:00:03Z',
      },
      {
        skill_name: 'notes',
        action_id: 'save',
        lifecycle_status: 'succeeded',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
    ]);
    expect(ordered.map((item) => `${item.skill_name}.${item.action_id}:${item.sequence}`)).toEqual([
      'docs.read:30',
      'notes.save:20',
      'docs.read:10',
    ]);
  });

  it('detects approval-resolvable states', () => {
    expect(canResolveActionState({
      skill_name: 'docs',
      action_id: 'read',
      lifecycle_status: 'awaiting_approval',
      approval_token: 'approval:token',
    })).toBe(true);
    expect(canResolveActionState({
      skill_name: 'docs',
      action_id: 'read',
      lifecycle_status: 'succeeded',
    })).toBe(false);
  });

  it('extracts latest tool result detail from action payload metadata', () => {
    expect(getActionStateDetail({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'succeeded',
      payload: {
        metadata: {
          tool_result: 'pwd\n/workspace',
        },
      },
    })).toContain('/workspace');
  });

  it('prefers validated arguments when present', () => {
    expect(getActionStateArgs({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'running',
      payload: {
        metadata: {
          validated_arguments: {
            command: 'pwd',
            cwd: '/workspace',
          },
          tool_args: {
            command: 'ignored',
          },
        },
      },
    })).toEqual({
      command: 'pwd',
      cwd: '/workspace',
    });
  });

  it('pretty prints structured tool results', () => {
    expect(getActionStateDetail({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'succeeded',
      payload: {
        metadata: {
          tool_result: '{"ok":true,"files":["a.ts","b.ts"]}',
        },
      },
    })).toContain('"files": [');
  });

  it('builds structured detail sections for validation and runtime output', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'failed',
      payload: {
        validation_errors: ['Missing required action argument: options.cwd'],
        missing_requirements: ['tool:builtin:exec'],
        metadata: {
          tool_error: 'permission denied',
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual([
      'Validation Errors',
      'Missing Requirements',
      'Tool Error',
    ]);
    expect(sections[0].content).toContain('options.cwd');
    expect(sections[2].tone).toBe('rose');
  });

  it('uses tool result as a success detail section', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'succeeded',
      payload: {
        metadata: {
          tool_result: '{"ok":true}',
        },
      },
    });

    expect(sections).toHaveLength(1);
    expect(sections[0].title).toBe('Tool Result');
    expect(sections[0].tone).toBe('emerald');
    expect(sections[0].content).toContain('"ok": true');
  });

  it('renders observability detail section for retryability and artifact path', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'excalidraw-diagram-generator',
      action_id: 'generate',
      lifecycle_status: 'failed',
      observability: {
        started_at: '2026-03-28T00:00:00Z',
        finished_at: '2026-03-28T00:00:00.220Z',
        duration_ms: 220,
        error_kind: 'retryable_error',
        retryable: true,
        artifact_path: '/tmp/diagram.excalidraw',
      },
      payload: {
        event: 'skill.action.result',
      },
    });

    expect(sections[0].title).toBe('Observability');
    expect(sections[0].content).toContain('error_kind: retryable_error');
    expect(sections[0].content).toContain('retryable: true');
    expect(sections[0].content).toContain('/tmp/diagram.excalidraw');
  });

  it('renders builtin exec results as stdout, stderr, and exit code sections', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'failed',
      payload: {
        mapped_tool: 'builtin:exec',
        metadata: {
          tool_result: 'file-a\nfile-b\nSTDERR:\nwarning line\nExit code: 2',
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Stdout', 'Stderr', 'Exit Code']);
    expect(sections[0].content).toContain('file-a');
    expect(sections[1].content).toContain('warning line');
    expect(sections[2].content).toBe('2');
  });

  it('renders builtin exec stderr-only errors cleanly', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'exec',
      action_id: 'run',
      lifecycle_status: 'failed',
      payload: {
        mapped_tool: 'builtin:exec',
        metadata: {
          tool_error: 'STDERR:\npermission denied\nExit code: 126',
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Stderr', 'Exit Code']);
    expect(sections[0].content).toContain('permission denied');
    expect(sections[1].content).toBe('126');
  });

  it('renders docs search results as matched paths and excerpts', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'docs',
      action_id: 'search',
      lifecycle_status: 'succeeded',
      payload: {
        mapped_tool: 'builtin:docs_search',
        metadata: {
          tool_result: JSON.stringify([
            {
              path: '/workspace/docs/plan.md',
              snippet: 'roadmap summary',
              score: 0.92,
              start_line: 12,
              end_line: 16,
            },
            {
              path: '/workspace/docs/spec.md',
              snippet: 'contract details',
              score: 0.71,
            },
          ]),
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Result Summary', 'Matched Paths', 'Excerpts']);
    expect(sections[1].content).toContain('/workspace/docs/plan.md');
    expect(sections[1].content).toContain('lines 12-16');
    expect(sections[2].content).toContain('roadmap summary');
  });

  it('renders docs read results as document path, range, and excerpt', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'docs',
      action_id: 'read',
      lifecycle_status: 'succeeded',
      payload: {
        mapped_tool: 'builtin:docs_read',
        metadata: {
          tool_result: '/workspace/docs/plan.md#L20-L40\nImplementation details go here',
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Document Path', 'Line Range', 'Excerpt']);
    expect(sections[0].content).toBe('/workspace/docs/plan.md');
    expect(sections[1].content).toBe('L20-L40');
    expect(sections[2].content).toContain('Implementation details');
  });

  it('renders artifact generation results with download metadata', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'ppt',
      action_id: 'generate',
      lifecycle_status: 'succeeded',
      payload: {
        mapped_tool: 'builtin:generate_pptx',
        metadata: {
          tool_result: JSON.stringify({
            filename: 'deck.pptx',
            file_path: '/workspace/backend/data/exports/deck.pptx',
            download_url: '/exports/deck.pptx',
          }),
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Artifact', 'Download']);
    expect(sections[0].content).toContain('deck.pptx');
    expect(sections[1].content).toBe('/exports/deck.pptx');
  });

  it('builds stable short display ids from invocation ids', () => {
    expect(getActionStateDisplayId({
      invocation_id: 'invoke:exec:1.0.0:run:req-approval',
    })).toBe('req-approval');
  });

  it('builds stable trace identities and export payloads', () => {
    const state = {
      skill_name: 'exec',
      action_id: 'run',
      invocation_id: 'invoke:exec:1.0.0:run:req-approval',
      request_id: 'req-approval',
      lifecycle_status: 'awaiting_approval',
      updated_at: '2026-03-28T10:00:03Z',
      sequence: 30,
      payload: { metadata: { tool_args: { command: 'pwd' } } },
    };

    expect(getActionStateTraceIdentity(state).label).toBe('exec.run#req-approval');
    expect(getActionStateTracePayload(state)).toContain('"command": "pwd"');
  });

  it('formats timestamps for action cards and focused traces', () => {
    expect(getActionStateTimestampLabel({ updated_at: '2026-03-28T10:00:03Z' })).toBe('2026-03-28 10:00:03 UTC');
    expect(getActionStateTimestampLabel({ ts: '2026-03-28T10:00:03Z' })).toBe('2026-03-28 10:00:03 UTC');
  });

  it('groups action states by skill and action while keeping invocation history', () => {
    const groups = groupActionStates([
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-1',
        lifecycle_status: 'skipped',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
      },
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-2',
        lifecycle_status: 'succeeded',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
      {
        skill_name: 'docs',
        action_id: 'read',
        invocation_id: 'invoke:docs:1.0.0:read:req-3',
        lifecycle_status: 'awaiting_approval',
        sequence: 15,
        ts: '2026-03-28T10:00:01Z',
      },
    ]);

    expect(groups).toHaveLength(2);
    expect(groups[0].label).toBe('exec.run');
    expect(groups[0].latest.invocation_id).toBe('invoke:exec:1.0.0:run:req-2');
    expect(groups[0].states).toHaveLength(2);
  });

  it('summarizes latest group statuses', () => {
    const groups = groupActionStates([
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-2',
        lifecycle_status: 'succeeded',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
      {
        skill_name: 'docs',
        action_id: 'read',
        invocation_id: 'invoke:docs:1.0.0:read:req-3',
        lifecycle_status: 'awaiting_approval',
        sequence: 15,
        ts: '2026-03-28T10:00:01Z',
      },
      {
        skill_name: 'shell',
        action_id: 'cleanup',
        invocation_id: 'invoke:shell:1.0.0:cleanup:req-4',
        lifecycle_status: 'failed',
        sequence: 11,
        ts: '2026-03-28T10:00:00Z',
      },
    ]);

    expect(summarizeActionGroups(groups)).toEqual({
      total: 3,
      awaitingApproval: 1,
      failed: 1,
      succeeded: 1,
    });
  });

  it('filters grouped actions by status and search text', () => {
    const groups = groupActionStates([
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-2',
        lifecycle_status: 'succeeded',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
      {
        skill_name: 'docs',
        action_id: 'read',
        invocation_id: 'invoke:docs:1.0.0:read:req-3',
        lifecycle_status: 'awaiting_approval',
        approval_token: 'approval:docs',
        sequence: 15,
        ts: '2026-03-28T10:00:01Z',
      },
    ]);

    expect(filterActionGroups(groups, '', 'awaiting_approval')).toHaveLength(1);
    expect(filterActionGroups(groups, 'approval:docs', 'all')).toHaveLength(1);
    expect(filterActionGroups(groups, 'cleanup', 'all')).toHaveLength(0);
  });

  it('shows only the latest invocation when a group is collapsed', () => {
    const group = groupActionStates([
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-1',
        lifecycle_status: 'skipped',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
      },
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-2',
        lifecycle_status: 'succeeded',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
    ])[0];

    expect(getVisibleActionGroupStates(group, false)).toHaveLength(1);
    expect(getVisibleActionGroupStates(group, false)[0].invocation_id).toBe('invoke:exec:1.0.0:run:req-2');
    expect(getHiddenActionGroupCount(group, false)).toBe(1);
  });

  it('paginates invocation history when a group is expanded', () => {
    const group = groupActionStates([
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-1',
        lifecycle_status: 'skipped',
        sequence: 10,
        ts: '2026-03-28T10:00:01Z',
      },
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-2',
        lifecycle_status: 'failed',
        sequence: 20,
        ts: '2026-03-28T10:00:02Z',
      },
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-3',
        lifecycle_status: 'awaiting_approval',
        sequence: 30,
        ts: '2026-03-28T10:00:03Z',
      },
      {
        skill_name: 'exec',
        action_id: 'run',
        invocation_id: 'invoke:exec:1.0.0:run:req-4',
        lifecycle_status: 'succeeded',
        sequence: 40,
        ts: '2026-03-28T10:00:04Z',
      },
    ])[0];

    expect(getVisibleActionGroupStates(group, true, 3)).toHaveLength(3);
    expect(getHiddenActionGroupCount(group, true, 3)).toBe(1);
    expect(getVisibleActionGroupStates(group, true, 6)).toHaveLength(4);
    expect(getHiddenActionGroupCount(group, true, 6)).toBe(0);
  });
});
