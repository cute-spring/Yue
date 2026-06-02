import { expect, test, type Page } from '@playwright/test';
import { mockBasicChatBootstrap } from './chat-test-helpers';

const workspace = {
  id: 'ws_1',
  name: 'Client Research',
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-01T00:00:00Z',
};

const createSource = ({
  id,
  displayName,
  status,
  sourceRef,
  sourceType = 'upload',
  citationCapable = false,
  availableTools = [],
}: {
  id: string;
  displayName: string;
  status: string;
  sourceRef: string;
  sourceType?: string;
  citationCapable?: boolean;
  availableTools?: string[];
}) => ({
  id,
  workspace_id: workspace.id,
  source_type: sourceType,
  source_ref: sourceRef,
  display_name: displayName,
  status,
  source_metadata: {
    citation_capable: citationCapable,
    available_tools: availableTools,
  },
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-01T00:00:00Z',
});

const singleReadyPdfSources = [
  createSource({
    id: 'src_policy',
    displayName: 'Policy.pdf',
    status: 'ready',
    sourceRef: 'uploads/chat/policy.pdf',
    citationCapable: true,
    availableTools: ['docs_read_pdf'],
  }),
];

const mixedReadinessSources = [
  createSource({
    id: 'src_ready',
    displayName: 'Report.pdf',
    status: 'ready',
    sourceRef: 'uploads/chat/report.pdf',
    citationCapable: true,
    availableTools: ['docs_read_pdf'],
  }),
  createSource({
    id: 'src_unsupported',
    displayName: 'Clip.mov',
    status: 'unsupported_type',
    sourceRef: 'uploads/chat/clip.mov',
  }),
  createSource({
    id: 'src_missing',
    displayName: 'Missing.pdf',
    status: 'missing',
    sourceRef: 'uploads/chat/missing.pdf',
  }),
];

const dualReadySources = [
  createSource({
    id: 'src_selected',
    displayName: 'Selected.pdf',
    status: 'ready',
    sourceRef: 'uploads/chat/selected.pdf',
    citationCapable: true,
    availableTools: ['docs_read_pdf'],
  }),
  createSource({
    id: 'src_excluded',
    displayName: 'Excluded.pdf',
    status: 'ready',
    sourceRef: 'uploads/chat/excluded.pdf',
    citationCapable: true,
    availableTools: ['docs_read_pdf'],
  }),
];

const artifacts = [
  {
    id: 'artifact_1',
    workspace_id: 'ws_1',
    artifact_type: 'research_report',
    title: 'Workspace synthesis',
    artifact_metadata: {
      question: 'What changed?',
      summary: 'Changes are grounded in the PDF source.',
      source_ids: ['src_ready'],
      mode: 'require_sources',
    },
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
  },
];

const makeSseBody = (events: Record<string, unknown>[]) =>
  events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join('');

const prepareChatPage = async (page: Page) => {
  await mockBasicChatBootstrap(page);
  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini');
  });
};

const routeWorkspaceData = async (
  page: Page,
  {
    sources,
    workspaceArtifacts = [],
  }: {
    sources: Record<string, unknown>[];
    workspaceArtifacts?: Record<string, unknown>[];
  },
) => {
  await page.route('**/api/workspaces/', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([workspace]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(workspace) });
  });
  await page.route('**/api/workspaces/ws_1/sources', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sources) });
  });
  await page.route('**/api/workspaces/ws_1/artifacts', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(workspaceArtifacts) });
  });
};

const expectSelectedWorkspace = async (page: Page) => {
  await page.goto('/', { waitUntil: 'networkidle' });
  await page.locator('select').first().selectOption('ws_1');
};

const sendPrompt = async (page: Page, prompt: string) => {
  await page.locator('textarea').first().fill(prompt);
  await expect(page.getByRole('button', { name: 'Send Message' })).toBeEnabled();
  await page.getByRole('button', { name: 'Send Message' }).click();
};

test.describe('workspace grounded answer smoke', () => {
  test('shows first-time workspace guidance when a selected workspace has no sources or artifacts yet', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, { sources: [] });

    await expectSelectedWorkspace(page);

    await expect(page.getByText('No sources yet · No saved artifacts yet')).toBeVisible();
    await expect(page.getByRole('button', { name: /^Resources/i })).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByText('Start by asking a question in this workspace or upload a file in chat to give it context.')).toBeVisible();
    await expect(page.getByText('No sources yet. Upload a file in chat or attach a local document to give this workspace evidence.')).toBeVisible();
    await expect(page.getByText('No saved artifacts yet').first()).toBeVisible();
  });

  test('scenario A keeps the single-ready-PDF evidence contract stable across grounding modes', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, { sources: singleReadyPdfSources });
    const requestPayloads: Record<string, unknown>[] = [];

    await page.route('**/api/chat/stream', async (route) => {
      const payload = route.request().postDataJSON() as Record<string, unknown>;
      requestPayloads.push(payload);
      const groundingMode = String(payload.grounding_mode || 'normal');
      const citationEvents =
        groundingMode === 'normal'
          ? []
          : [{ citations: [{ path: 'Policy.pdf', snippet: `Evidence for ${groundingMode}` }] }];

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          {
            workspace_grounding: {
              workspace_id: 'ws_1',
              workspace_source_mode: 'all_ready',
              grounding_mode: groundingMode,
              eligible_sources: [{ id: 'src_policy', display_name: 'Policy.pdf' }],
              unavailable_sources: [],
            },
          },
          { content: `Scenario A ${groundingMode} response.` },
          ...citationEvents,
        ]),
      });
    });

    await expectSelectedWorkspace(page);
    await expect(page.getByText('1 ready source · No saved artifacts yet')).toBeVisible();

    const modeCases = [
      {
        mode: 'normal',
        summary: 'All ready sources; Sources optional; 1 eligible source; No citations attached',
      },
      {
        mode: 'prefer_sources',
        summary: 'All ready sources; Citations preferred; 1 eligible source; 1 citations attached',
      },
      {
        mode: 'require_sources',
        summary: 'All ready sources; Citations required; 1 eligible source; 1 citations attached',
      },
    ] as const;

    for (const { mode, summary } of modeCases) {
      await page.locator('select').nth(2).selectOption(mode);
      await sendPrompt(page, `Scenario A prompt for ${mode}`);
      await expect(page.getByText(`Scenario A ${mode} response.`)).toBeVisible();
      await expect(page.getByText(summary).last()).toBeVisible();
    }

    expect(requestPayloads).toHaveLength(3);
    expect(requestPayloads.map((payload) => payload.grounding_mode)).toEqual(['normal', 'prefer_sources', 'require_sources']);
    expect(requestPayloads.every((payload) => payload.workspace_source_mode === 'all_ready')).toBe(true);
  });

  test('scenario C keeps only the ready source eligible in a mixed-readiness require-sources turn', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, { sources: mixedReadinessSources, workspaceArtifacts: artifacts });
    let requestPayload: Record<string, unknown> | null = null;

    await page.route('**/api/chat/stream', async (route) => {
      requestPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          {
            workspace_grounding: {
              workspace_id: 'ws_1',
              workspace_source_mode: 'all_ready',
              grounding_mode: 'require_sources',
              eligible_sources: [{ id: 'src_ready', display_name: 'Report.pdf' }],
              unavailable_sources: [
                { id: 'src_unsupported', display_name: 'Clip.mov' },
                { id: 'src_missing', display_name: 'Missing.pdf' },
              ],
            },
          },
          { content: 'Mixed readiness answer grounded only in Report.pdf.' },
          { citations: [{ path: 'Report.pdf', snippet: 'Grounded evidence snippet' }] },
        ]),
      });
    });

    await expectSelectedWorkspace(page);
    await expect(page.getByText('1 ready source · 2 sources needing attention · 1 saved artifact')).toBeVisible();
    await page.locator('select').nth(2).selectOption('require_sources');
    await sendPrompt(page, 'What changed in the ready report?');

    await expect(page.getByText('Mixed readiness answer grounded only in Report.pdf.')).toBeVisible();
    await expect(page.getByText(/All ready sources; Citations required; 1 eligible source, 2 unavailable; 1 citations attached/)).toBeVisible();
    await expect(page.getByText('Unavailable in this turn')).toBeVisible();
    await expect(page.getByText('Clip.mov').last()).toBeVisible();
    await expect(page.getByText('Missing.pdf').last()).toBeVisible();
    await expect(page.getByText('Sources (1)')).toBeVisible();

    expect(requestPayload?.workspace_source_mode).toBe('all_ready');
    expect(requestPayload?.grounding_mode).toBe('require_sources');
  });

  test('scenario D keeps selected-source turns scoped to the chosen source when evidence is insufficient', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, { sources: dualReadySources });
    let requestPayload: Record<string, unknown> | null = null;

    await page.route('**/api/chat/stream', async (route) => {
      requestPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          {
            workspace_grounding: {
              workspace_id: 'ws_1',
              workspace_source_mode: 'selected',
              grounding_mode: 'require_sources',
              selected_source_ids: ['src_selected'],
              eligible_sources: [{ id: 'src_selected', display_name: 'Selected.pdf' }],
              unavailable_sources: [],
            },
          },
          { content: 'Evidence is insufficient from the selected source to answer that question.' },
        ]),
      });
    });

    await expectSelectedWorkspace(page);
    await page.locator('select').nth(1).selectOption('selected');
    await page.locator('select').nth(2).selectOption('require_sources');
    await page.locator('input[type="checkbox"]').first().check();
    await sendPrompt(page, 'Answer a question that only the excluded source could answer.');

    await expect(page.getByText('Evidence is insufficient from the selected source to answer that question.')).toBeVisible();
    await expect(page.getByText('Selected sources; Citations required; 1 eligible source; No citations attached')).toBeVisible();
    await expect(page.getByText('Citation-required mode was active. If this answer makes source-specific claims without citations, treat it as needing follow-up verification.')).toBeVisible();
    await expect(page.getByText('Selected.pdf').last()).toBeVisible();
    await expect(page.getByText('Sources (1)')).toHaveCount(0);

    expect(requestPayload?.workspace_source_mode).toBe('selected');
    expect(requestPayload?.grounding_mode).toBe('require_sources');
    expect(requestPayload?.selected_workspace_source_ids).toEqual(['src_selected']);
  });

  test('scenario E makes require-sources failure explicit when workspace sources are disabled', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, { sources: singleReadyPdfSources });
    let requestPayload: Record<string, unknown> | null = null;

    await page.route('**/api/chat/stream', async (route) => {
      requestPayload = route.request().postDataJSON() as Record<string, unknown>;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          {
            workspace_grounding: {
              workspace_id: 'ws_1',
              workspace_source_mode: 'none',
              grounding_mode: 'require_sources',
              eligible_sources: [],
              unavailable_sources: [{ id: 'src_policy', display_name: 'Policy.pdf' }],
            },
          },
          { content: 'Citation-required mode cannot proceed because workspace sources are disabled for this turn.' },
        ]),
      });
    });

    await expectSelectedWorkspace(page);
    await page.locator('select').nth(1).selectOption('none');
    await page.locator('select').nth(2).selectOption('require_sources');
    await sendPrompt(page, 'Use workspace evidence even though sources are disabled.');

    await expect(page.getByText('Citation-required mode cannot proceed because workspace sources are disabled for this turn.')).toBeVisible();
    await expect(page.getByText('No workspace sources; Citations required')).toBeVisible();
    await expect(page.getByText('Citation-required mode was active, but no eligible workspace sources were available for this turn.')).toBeVisible();
    await expect(page.getByText('Unavailable in this turn')).toBeVisible();
    await expect(page.getByText('Policy.pdf').last()).toBeVisible();

    expect(requestPayload?.workspace_source_mode).toBe('none');
    expect(requestPayload?.grounding_mode).toBe('require_sources');
    expect(requestPayload?.selected_workspace_source_ids).toBeUndefined();
  });

  test('shows citation-required warning and tooling warning when citations are missing', async ({ page }) => {
    await prepareChatPage(page);
    await routeWorkspaceData(page, {
      sources: [
        createSource({
          id: 'src_ready',
          displayName: 'Report.pdf',
          status: 'ready',
          sourceRef: 'uploads/chat/report.pdf',
          citationCapable: true,
          availableTools: ['docs_read_pdf'],
        }),
        createSource({
          id: 'src_missing',
          displayName: 'Missing.pdf',
          status: 'missing',
          sourceRef: 'uploads/chat/missing.pdf',
        }),
      ],
    });

    await page.route('**/api/chat/stream', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: makeSseBody([
          {
            workspace_grounding: {
              workspace_id: 'ws_1',
              workspace_source_mode: 'all_ready',
              grounding_mode: 'require_sources',
              eligible_sources: [{ id: 'src_ready', display_name: 'Report.pdf' }],
              unavailable_sources: [{ id: 'src_missing', display_name: 'Missing.pdf' }],
              tooling_warning: 'Citation-required mode is active, but no compatible retrieval tools were enabled for this turn.',
            },
          },
          { content: 'This answer needs follow-up verification.' },
        ]),
      });
    });

    await expectSelectedWorkspace(page);
    await expect(page.getByRole('button', { name: /^Resources/i })).toHaveAttribute('aria-expanded', 'true');
    await expect(page.getByRole('button', { name: /^Sources/i })).toHaveAttribute('aria-expanded', 'true');
    await page.locator('select').nth(2).selectOption('require_sources');
    await sendPrompt(page, 'Summarize the missing evidence state.');

    await expect(page.getByText('This answer needs follow-up verification.')).toBeVisible();
    await expect(page.getByText('Citation-required mode was active. If this answer makes source-specific claims without citations, treat it as needing follow-up verification.')).toBeVisible();
    await expect(page.getByText('Citation-required mode is active, but no compatible retrieval tools were enabled for this turn.')).toBeVisible();
  });
});
