import { expect, test, type Page } from '@playwright/test';
import { mockChatBootstrap } from './chat-test-helpers';

const workspace = {
  id: 'ws_1',
  name: 'Client Research',
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-01T00:00:00Z',
};

const makeSseBody = (events: Record<string, unknown>[]) =>
  events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');

const routeWorkspaceBootstrap = async (page: Page, state: {
  notes: Record<string, unknown>[];
  candidates: Record<string, unknown>[];
  memories: Record<string, unknown>[];
}) => {
  await page.route('**/api/workspaces/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([workspace]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(workspace) });
  });
  await page.route('**/api/workspaces/ws_1/sources', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/workspaces/ws_1/artifacts', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/workspaces/ws_1/memory', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.memories) });
  });
  await page.route('**/api/workspaces/ws_1/memory-candidates', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.candidates) });
  });
  await page.route('**/api/notebook/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.notes) });
  });
};

const openWorkspaceDock = async (page: Page) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.locator('button[title="Workspace"]').click();
  await page.getByRole('button', { name: /Client Research/i }).click();
  return page.getByRole('complementary').nth(1);
};

test('workspace capture flow saves a note, creates a memory candidate, and recalls the note later', async ({ page }) => {
  const telemetryEvents: Record<string, unknown>[] = [];
  const streamPayloads: Record<string, unknown>[] = [];
  const state = {
    notes: [] as Record<string, unknown>[],
    candidates: [] as Record<string, unknown>[],
    memories: [] as Record<string, unknown>[],
  };

  await mockChatBootstrap(page, {
    prefs: {
      theme: 'light',
      language: 'en',
      default_agent: null,
      capture_suggestions_enabled: true,
      memory_suggestions_enabled: true,
      note_recall_enabled: true,
    },
    agents: [],
  });
  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini');
  });

  await routeWorkspaceBootstrap(page, state);

  await page.route('**/api/chat/chat-memory-1/meta', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'chat-memory-1',
        title: 'Workspace memory capture',
        summary: null,
        updated_at: '2026-06-04T00:00:00Z',
      }),
    });
  });

  await page.route('**/api/chat/chat-memory-1/capture-events', async (route) => {
    telemetryEvents.push(route.request().postDataJSON() as Record<string, unknown>);
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'success' }) });
  });

  await page.route('**/api/workspaces/ws_1/notes/from-message', async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.chat_id).toBe('chat-memory-1');
    const note = {
      id: 'note_1',
      workspace_id: 'ws_1',
      title: 'Onboarding checklist',
      summary: 'Keep onboarding answers short, structured, and reusable.',
      content: 'Use a concise onboarding checklist with links to setup docs.',
      tags: ['onboarding', 'process'],
      note_type: 'reference',
      capture_type: 'chat_capture',
      status: 'saved',
      source_session_id: 'chat-memory-1',
      source_message_id: 101,
      citation_refs: [],
      source_metadata: {},
      promoted_memory_id: null,
      promotion_hint: {
        eligible: true,
        state: 'ready',
        suggested_action: 'create_new',
        reason_summary: 'This looks like a stable reusable instruction.',
      },
      created_at: '2026-06-04T00:00:00Z',
      updated_at: '2026-06-04T00:00:00Z',
    };
    state.notes = [note];
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(note) });
  });

  await page.route('**/api/workspaces/ws_1/notes/note_1/memory-candidates', async (route) => {
    const candidate = {
      id: 'cand_1',
      workspace_id: 'ws_1',
      memory_type: 'recurring_instruction',
      title: 'Onboarding checklist',
      content: 'Use a concise onboarding checklist with links to setup docs.',
      status: 'pending',
      suggested_action: 'create_new',
      candidate_metadata: { note_id: 'note_1' },
      created_at: '2026-06-04T00:00:00Z',
      updated_at: '2026-06-04T00:00:00Z',
    };
    state.candidates = [candidate];
    state.notes = state.notes.map((note) =>
      note.id === 'note_1'
        ? {
            ...note,
            promotion_hint: {
              eligible: true,
              state: 'candidate_pending',
              candidate_id: 'cand_1',
              candidate_status: 'pending',
              suggested_action: 'create_new',
              reason_summary: 'Waiting for review before becoming durable memory.',
            },
            source_metadata: { ...(note.source_metadata as Record<string, unknown>), last_memory_candidate_id: 'cand_1' },
          }
        : note,
    );
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(candidate) });
  });

  let streamCallCount = 0;
  await page.route('**/api/chat/stream', async (route) => {
    const payload = route.request().postDataJSON() as Record<string, unknown>;
    streamPayloads.push(payload);
    streamCallCount += 1;

    if (streamCallCount === 1) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          { chat_id: 'chat-memory-1' },
          {
            meta: {
              id: 101,
              timestamp: '2026-06-04T00:00:00Z',
              provider: 'openai',
              model: 'gpt-4o-mini',
            },
            run_id: 'run-1',
            assistant_turn_id: 'turn-1',
          },
          { content: 'Here is a reusable onboarding answer with a checklist and links.' },
          {
            workspace_capture_suggestion: {
              workspace_id: 'ws_1',
              show_note_action: true,
              show_memory_action: true,
              reason: 'This answer looks reusable for future onboarding questions.',
              source: 'assistant_reply',
            },
          },
          { finish_reason: 'stop' },
        ]),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: makeSseBody([
        { chat_id: 'chat-memory-1' },
        {
          meta: {
            id: 202,
            timestamp: '2026-06-04T00:05:00Z',
            provider: 'openai',
            model: 'gpt-4o-mini',
          },
          run_id: 'run-2',
          assistant_turn_id: 'turn-2',
        },
        { content: 'I reused the saved onboarding checklist for this follow-up.' },
        {
          workspace_notes: {
            workspace_id: 'ws_1',
            loaded_note_count: 1,
            loaded_note_ids: ['note_1'],
            loaded_notes: [
              {
                id: 'note_1',
                title: 'Onboarding checklist',
                summary: 'Keep onboarding answers short, structured, and reusable.',
                content: 'Use a concise onboarding checklist with links to setup docs.',
                note_type: 'reference',
                tags: ['onboarding', 'process'],
                source_session_id: 'chat-memory-1',
                source_message_id: 101,
              },
            ],
          },
        },
        { finish_reason: 'stop' },
      ]),
    });
  });

  const workspaceDock = await openWorkspaceDock(page);

  await page.locator('textarea').first().fill('How should I answer onboarding questions?');
  await page.getByRole('button', { name: 'Send Message' }).click();

  await expect(page.getByText('Here is a reusable onboarding answer with a checklist and links.')).toBeVisible();
  await expect(page.getByText('Worth keeping')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save as note' })).toBeVisible();

  await page.getByRole('button', { name: 'Save as note' }).click();
  await expect(page.getByText('Saved note: Onboarding checklist')).toBeVisible();

  await expect(workspaceDock.getByText('Onboarding checklist', { exact: true })).toBeVisible();
  await expect(workspaceDock.getByRole('button', { name: 'Review as memory' })).toBeVisible();

  await workspaceDock.getByRole('button', { name: 'Review as memory' }).click();
  await expect(workspaceDock.getByText(/candidate pending/i).first()).toBeVisible();

  await page.locator('textarea').first().fill('Give me the short version again.');
  await page.getByRole('button', { name: 'Send Message' }).click();

  await expect(page.getByText('I reused the saved onboarding checklist for this follow-up.')).toBeVisible();
  await expect(page.getByText('Note recall', { exact: true })).toBeVisible();
  await expect(page.getByText('1 recalled', { exact: true })).toBeVisible();

  await expect.poll(() => telemetryEvents.some((event) => event.event_type === 'suggestion_shown')).toBe(true);
  await expect.poll(() => telemetryEvents.some((event) => event.event_type === 'note_saved')).toBe(true);
  await expect.poll(() => telemetryEvents.some((event) => event.event_type === 'memory_candidate_created')).toBe(true);

  expect(streamPayloads).toHaveLength(2);
  expect(streamPayloads[0]).toMatchObject({
    workspace_id: 'ws_1',
    note_recall_enabled: true,
    capture_suggestions_enabled: true,
    memory_suggestions_enabled: true,
  });
  expect(streamPayloads[1]).toMatchObject({
    workspace_id: 'ws_1',
    chat_id: 'chat-memory-1',
    note_recall_enabled: true,
    capture_suggestions_enabled: true,
    memory_suggestions_enabled: true,
  });
});

test('workspace memory protections disable unsafe actions and preserve recurring instruction bulk updates', async ({ page }) => {
  const approvalPayloads: Record<string, unknown>[] = [];
  const bulkStatusPayloads: Record<string, unknown>[] = [];
  const state = {
    notes: [] as Record<string, unknown>[],
    candidates: [
      {
        id: 'cand_protected_1',
        workspace_id: 'ws_1',
        memory_type: 'preference',
        scope_type: 'user',
        title: 'Keep responses crisp',
        content: 'Prefer short answers with clear next steps.',
        status: 'pending',
        score: 0.91,
        suggested_action: 'replace_existing',
        conflict_memory_id: 'mem_protected_pref',
        candidate_metadata: { score_reasons: ['High-value durable memory type.'] },
        created_at: '2026-06-04T00:00:00Z',
        updated_at: '2026-06-04T00:00:00Z',
      },
    ] as Record<string, unknown>[],
    memories: [
      {
        id: 'mem_locked_instruction',
        workspace_id: 'ws_1',
        memory_type: 'recurring_instruction',
        scope_type: 'workspace',
        scope_ref: 'ws_1',
        title: 'Locked instruction',
        content: 'Always include a checklist for onboarding.',
        status: 'active',
        editable: false,
        revocable: true,
        created_at: '2026-06-04T00:00:00Z',
        updated_at: '2026-06-04T00:00:00Z',
      },
      {
        id: 'mem_live_instruction',
        workspace_id: 'ws_1',
        memory_type: 'recurring_instruction',
        scope_type: 'workspace',
        scope_ref: 'ws_1',
        title: 'Live instruction',
        content: 'End onboarding replies with the next step.',
        status: 'active',
        editable: true,
        revocable: true,
        created_at: '2026-06-04T00:01:00Z',
        updated_at: '2026-06-04T00:01:00Z',
      },
      {
        id: 'mem_protected_pref',
        workspace_id: 'ws_1',
        memory_type: 'preference',
        scope_type: 'user',
        scope_ref: null,
        title: 'Protected preference',
        content: 'Default to Chinese output.',
        status: 'active',
        editable: true,
        revocable: false,
        created_at: '2026-06-04T00:02:00Z',
        updated_at: '2026-06-04T00:02:00Z',
      },
    ] as Record<string, unknown>[],
  };

  await mockChatBootstrap(page, {
    prefs: {
      theme: 'light',
      language: 'en',
      default_agent: null,
      capture_suggestions_enabled: true,
      memory_suggestions_enabled: true,
      note_recall_enabled: true,
    },
    agents: [],
  });
  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini');
  });

  await routeWorkspaceBootstrap(page, state);

  await page.route('**/api/workspaces/ws_1/memory/bulk-status', async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>;
    bulkStatusPayloads.push(body);
    expect(body).toEqual({ memory_type: 'recurring_instruction', status: 'disabled' });

    state.memories = state.memories.map((memory) =>
      memory.memory_type === 'recurring_instruction' && memory.editable !== false
        ? { ...memory, status: 'disabled', updated_at: '2026-06-04T00:03:00Z' }
        : memory,
    );

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'success', updated_count: 1 }),
    });
  });

  await page.route('**/api/workspaces/ws_1/memory-candidates/cand_protected_1/approve', async (route) => {
    approvalPayloads.push(route.request().postDataJSON() as Record<string, unknown>);
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Workspace memory cannot be deleted or replaced' }),
    });
  });

  const workspaceDock = await openWorkspaceDock(page);
  await workspaceDock.getByRole('button', { name: /Memory 3 total/i }).click();

  await expect(workspaceDock.getByText('Locked instruction', { exact: true })).toBeVisible();
  await workspaceDock.getByText('Locked instruction', { exact: true }).click();
  await expect(workspaceDock.getByRole('button', { name: 'Locked', exact: true })).toBeDisabled();
  await expect(workspaceDock.getByRole('button', { name: 'Disable', exact: true })).toBeDisabled();

  await expect(workspaceDock.getByText('Protected preference', { exact: true })).toBeVisible();
  await workspaceDock.getByText('Protected preference', { exact: true }).click();
  await expect(workspaceDock.getByRole('button', { name: 'Protected', exact: true })).toBeDisabled();

  const disableAllButtons = workspaceDock.getByRole('button', { name: 'Disable all' });
  await disableAllButtons.nth(1).click();

  await expect.poll(() => bulkStatusPayloads.length).toBe(1);
  await workspaceDock.getByText('Live instruction', { exact: true }).click();
  await expect(workspaceDock.getByRole('button', { name: 'Enable', exact: true })).toBeVisible();
  await expect(workspaceDock.getByText('Protected preference', { exact: true })).toBeVisible();

  await expect(workspaceDock.getByText('Keep responses crisp', { exact: true })).toBeVisible();
  await workspaceDock.getByRole('button', { name: 'Replace existing' }).click();
  await expect(workspaceDock.getByText('Workspace memory cannot be deleted or replaced')).toBeVisible();

  expect(approvalPayloads).toEqual([
    {
      approval_mode: 'replace_existing',
      target_memory_id: 'mem_protected_pref',
      memory_type: 'preference',
      scope_type: 'user',
      scope_ref: null,
      title: 'Keep responses crisp',
      content: 'Prefer short answers with clear next steps.',
      confidence: 0.91,
      why_saved: null,
      expires_at: null,
    },
  ]);
});
