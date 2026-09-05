import { expect, test } from '@playwright/test';
import { installClipboardCapture, mockBasicChatBootstrap } from './chat-test-helpers';

const chartSpec = {
  version: 1,
  kind: 'chart',
  chartType: 'bar',
  title: 'Revenue by Region',
  data: [
    { region: 'APAC', revenue: 120 },
    { region: 'EMEA', revenue: 90 },
  ],
  encoding: {
    x: { field: 'region', type: 'category' },
    y: { field: 'revenue', type: 'number' },
  },
};

const chartArtifact = {
  artifact_id: 'chart_revenue_region',
  artifact_type: 'chart',
  display_mode: 'inline',
  assistant_turn_id: 'turn_chart_1',
  run_id: 'run_chart_1',
  sequence: 3,
  ts: '2026-07-24T00:00:00Z',
  chart: chartSpec,
};

test('structured chart artifact renders from stream and message history replay', async ({ page }) => {
  await installClipboardCapture(page);
  await page.addInitScript(() => {
    localStorage.setItem('yue_selected_provider', 'openai');
    localStorage.setItem('yue_selected_model', 'gpt-4o-mini');
  });
  await mockBasicChatBootstrap(page);
  await page.route('**/api/config/preferences', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        theme: 'light',
        language: 'en',
        default_agent: null,
        advanced_mode: false,
        voice_input_enabled: false,
      }),
    });
  });
  await page.route('**/api/config/feature_flags', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chat_trace_ui_enabled: false, chat_trace_raw_enabled: false }),
    });
  });
  await page.route('**/api/config/doc_access', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ allow_roots: [], deny_roots: [] }),
    });
  });
  await page.route('**/api/files/policy', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ max_file_count: 5, max_file_size_mb: 20, allowed_extensions: ['.png', '.pdf', '.xlsx', '.csv'] }),
    });
  });

  await page.route('**/api/workspaces/', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/workspaces/**/sources', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/workspaces/**/artifacts', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/chat/stream', async (route) => {
    const event = (payload: unknown) => `data: ${JSON.stringify(payload)}\n\n`;
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        event({ chat_id: 'chat-chart-replay' }),
        event({
          version: 'v2',
          event: 'meta',
          event_id: 'evt_meta_chart',
          run_id: 'run_chart_1',
          assistant_turn_id: 'turn_chart_1',
          sequence: 1,
          ts: '2026-07-24T00:00:00Z',
          payload: {
            meta: {
              provider: 'openai',
              model: 'gpt-4o-mini',
              run_id: 'run_chart_1',
              assistant_turn_id: 'turn_chart_1',
            },
          },
        }),
        event({
          version: 'v2',
          event: 'content.delta',
          event_id: 'evt_content_chart',
          run_id: 'run_chart_1',
          assistant_turn_id: 'turn_chart_1',
          sequence: 2,
          ts: '2026-07-24T00:00:01Z',
          payload: { content: 'Here is the chart.' },
        }),
        event({
          version: 'v2',
          event: 'artifact.chart.created',
          event_id: 'evt_chart_created',
          run_id: 'run_chart_1',
          assistant_turn_id: 'turn_chart_1',
          sequence: 3,
          ts: '2026-07-24T00:00:02Z',
          payload: {
            artifact_id: chartArtifact.artifact_id,
            artifact_type: 'chart',
            display_mode: 'inline',
            chart: chartSpec,
          },
        }),
        event({ total_duration: 0.2 }),
      ].join(''),
    });
  });
  await page.route('**/api/chat/history', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'chat-chart-replay',
          title: 'Chart replay session',
          summary: null,
          updated_at: '2026-07-24T00:00:03Z',
        },
      ]),
    });
  });
  await page.route('**/api/chat/chat-chart-replay', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'chat-chart-replay',
        agent_id: null,
        workspace_id: null,
        messages: [
          { id: 1, role: 'user', content: 'show chart' },
          {
            id: 2,
            role: 'assistant',
            content: 'Here is the chart.',
            assistant_turn_id: 'turn_chart_1',
            run_id: 'run_chart_1',
            chart_artifacts: [{ ...chartArtifact, message_id: 2 }],
          },
        ],
      }),
    });
  });
  await page.route('**/api/chat/chat-chart-replay/events', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/chat/chat-chart-replay/actions/states', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/chat/chat-chart-replay/meta', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'chat-chart-replay',
        title: 'Chart replay session',
        summary: null,
        updated_at: '2026-07-24T00:00:03Z',
      }),
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/You are chatting with/i);
  await input.fill('show chart');
  await input.press('Enter');

  const liveChart = page.locator('[data-chart-artifact-id="chart_revenue_region"] .yue-chart-render-target[data-processed="true"]');
  await expect(liveChart).toBeVisible({ timeout: 15000 });
  await expect.poll(async () => liveChart.getAttribute('data-spec')).toContain('Revenue%20by%20Region');
  const liveWidget = page.locator('[data-chart-artifact-id="chart_revenue_region"]').first();
  await expect(liveWidget.getByTitle('Export chart image')).toBeVisible();
  await expect(liveWidget.getByTitle('Regenerate chart')).toBeVisible();
  await expect(liveWidget.getByTitle('Save chart to workspace')).toBeVisible();
  await liveWidget.getByRole('button', { name: 'Data' }).click();
  await expect(liveWidget.getByText('APAC')).toBeVisible();
  await liveWidget.getByTitle('Copy chart data').click();
  await expect.poll(async () => page.evaluate(() => (window as any).__copiedText || '')).toContain('APAC,120');
  await liveWidget.getByTitle('Switch chart type').selectOption('line');
  await expect(liveChart).toHaveAttribute('data-processed', 'true');

  await page.reload();
  await page.getByText('Chart replay session').click();

  const replayedChart = page.locator('[data-chart-artifact-id="chart_revenue_region"] .yue-chart-render-target[data-processed="true"]');
  await expect(replayedChart).toBeVisible({ timeout: 15000 });
  await expect.poll(async () => replayedChart.getAttribute('data-spec')).toContain('Revenue%20by%20Region');
});
