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

  it('renders browser screenshot artifacts with download link and image preview', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'browser-operator',
      action_id: 'capture',
      lifecycle_status: 'succeeded',
      payload: {
        mapped_tool: 'builtin:browser_screenshot',
        metadata: {
          tool_result: JSON.stringify({
            filename: 'browser-shot.png',
            file_path: '/workspace/.yue/data/exports/browser-shot.png',
            download_url: '/exports/browser-shot.png',
            artifact: {
              kind: 'screenshot',
            },
          }),
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual(['Artifact', 'Download', 'Preview', 'Artifact Metadata']);
    expect(sections[1].kind).toBe('link');
    expect(sections[1].href).toBe('/exports/browser-shot.png');
    expect(sections[2].kind).toBe('image');
    expect(sections[2].href).toBe('/exports/browser-shot.png');
  });

  it('renders browser contract sections from runtime metadata and tool args', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'browser-operator',
      action_id: 'click_element',
      lifecycle_status: 'running',
      payload: {
        mapped_tool: 'builtin:browser_click',
        metadata: {
          tool_family: 'agent_browser',
          operation: 'click',
          runtime_metadata_expectations: {
            required: ['operation', 'element_ref'],
            optional: ['session_id', 'tab_id', 'url'],
          },
          runtime_metadata: {
            operation: 'click',
            tool_family: 'agent_browser',
            mapped_tool: 'builtin:browser_click',
            element_ref: 'button:submit',
            session_id: 'session-1',
            tab_id: 'tab-1',
          },
          browser_continuity: {
            contract_mode: 'authoritative_target_mutation',
            current_execution_mode: 'resumable_session_required',
            authoritative_target_required: true,
            resumable_continuity: 'deferred',
          },
          browser_continuity_resolution: {
            resolver_contract_version: 1,
            resolution_mode: 'explicit_request_context',
            continuity_status: 'resolved',
            missing_context: [],
            resolved_context: {
              resolved_context_id: 'browser_ctx:test',
              session_id: 'session-1',
              tab_id: 'tab-1',
              element_ref: 'button:submit',
              resolution_mode: 'explicit_request_context',
              resolution_source: 'explicit_request_context',
              resolved_target_kind: 'authoritative_target',
            },
          },
          browser_continuity_resolver: {
            resolver_id: 'explicit_context',
            status: 'resolved',
            resolved: true,
          },
          tool_args: {
            url: 'https://example.com/checkout',
            element_ref: 'button:submit',
            session_id: 'session-1',
            tab_id: 'tab-1',
          },
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual([
      'Browser Contract',
      'Browser Target',
      'Browser Context',
      'Runtime Metadata Contract',
      'Browser Continuity',
      'Browser Continuity Resolution',
      'Resolved Browser Context',
    ]);
    expect(sections[0].content).toContain('operation: click');
    expect(sections[0].content).toContain('mapped tool: builtin:browser_click');
    expect(sections[1].content).toContain('url: https://example.com/checkout');
    expect(sections[1].content).toContain('element_ref: button:submit');
    expect(sections[2].content).toContain('session_id: session-1');
    expect(sections[3].content).toContain('required: operation, element_ref');
    expect(sections[4].content).toContain('contract mode: authoritative_target_mutation');
    expect(sections[4].content).toContain('resumable continuity: deferred');
    expect(sections[5].content).toContain('resolution mode: explicit_request_context');
    expect(sections[5].content).toContain('resolver: explicit_context');
    expect(sections[6].content).toContain('resolved_context_id: browser_ctx:test');
    expect(sections[6].content).toContain('resolved target kind: authoritative_target');
  });

  it('renders browser snapshot results as readable summary and interactive elements', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'browser-operator',
      action_id: 'snapshot_page',
      lifecycle_status: 'succeeded',
      payload: {
        mapped_tool: 'builtin:browser_snapshot',
        metadata: {
          tool_result: JSON.stringify({
            browser_context: {
              url: 'https://example.com',
              page_title: 'Example Domain',
            },
            snapshot: {
              max_nodes: 50,
              visible_text: 'Example Domain Example text content',
              interactive_elements: [
                {
                  ref: 'snapshot:browser_snapshot#node:1',
                  tag: 'a',
                  text: 'More information',
                  aria_label: '',
                  name: '',
                  id: 'cta-link',
                },
                {
                  ref: 'snapshot:browser_snapshot#node:2',
                  tag: 'button',
                  text: 'Continue',
                  aria_label: 'Continue flow',
                  name: 'continue',
                  id: '',
                },
              ],
              target_binding_context: {
                binding_source: 'snapshot:browser_snapshot',
                binding_session_id: 'session-1',
                binding_tab_id: 'tab-1',
                binding_url: 'https://example.com',
                binding_dom_version: null,
              },
            },
          }),
        },
      },
    });

    expect(sections.map((section) => section.title)).toEqual([
      'Snapshot Summary',
      'Interactive Elements',
      'Visible Text',
      'Snapshot Binding Context',
    ]);
    expect(sections[0].content).toContain('url: https://example.com');
    expect(sections[0].content).toContain('interactive elements: 2');
    expect(sections[1].content).toContain('1. snapshot:browser_snapshot#node:1');
    expect(sections[1].content).toContain('tag=a');
    expect(sections[1].content).toContain('text=More information');
    expect(sections[1].content).toContain('aria=Continue flow');
    expect(sections[2].content).toContain('Example Domain Example text content');
    expect(sections[3].content).toContain('binding_source: snapshot:browser_snapshot');
    expect(sections[3].content).toContain('binding_session_id: session-1');
  });

  it('renders blocked browser continuity resolution without resolved context section', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'browser-operator',
      action_id: 'click_element',
      lifecycle_status: 'preflight_blocked',
      payload: {
        mapped_tool: 'builtin:browser_click',
        metadata: {
          tool_family: 'agent_browser',
          operation: 'click',
          runtime_metadata: {
            operation: 'click',
            tool_family: 'agent_browser',
            mapped_tool: 'builtin:browser_click',
            element_ref: 'snapshot:browser_snapshot#node:1',
          },
          browser_continuity_resolution: {
            resolver_contract_version: 1,
            resolution_mode: 'session_tab_target_lookup',
            continuity_status: 'blocked',
            missing_context: ['tab_id'],
            resolved_context: {},
          },
          browser_continuity_resolver: {
            resolver_id: 'explicit_context',
            status: 'blocked',
            resolved: false,
          },
        },
      },
    });

    expect(sections.map((section) => section.title)).toContain('Browser Continuity Resolution');
    expect(sections.find((section) => section.title === 'Browser Continuity Resolution')?.content).toContain('missing context: tab_id');
    expect(sections.find((section) => section.title === 'Resolved Browser Context')).toBeUndefined();
  });

  it('renders browser key and label targets when present', () => {
    const sections = getActionStateDetailSections({
      skill_name: 'browser-operator',
      action_id: 'press_key',
      lifecycle_status: 'succeeded',
      payload: {
        metadata: {
          tool_family: 'agent_browser',
          operation: 'press',
          runtime_metadata_expectations: {
            required: ['operation', 'key'],
            optional: ['session_id', 'tab_id', 'element_ref'],
          },
          runtime_metadata: {
            operation: 'press',
            tool_family: 'agent_browser',
            mapped_tool: 'builtin:browser_press',
            key: 'Enter',
            label: 'confirm-submit',
          },
        },
      },
    });

    expect(sections[1].title).toBe('Browser Target');
    expect(sections[1].content).toContain('key: Enter');
    expect(sections[1].content).toContain('label: confirm-submit');
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
