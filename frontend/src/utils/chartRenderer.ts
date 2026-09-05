import * as echarts from 'echarts/core';
import type { ECharts } from 'echarts/core';
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts';
import {
  DatasetComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  TransformComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { compileYueChartOption, type YueChartThemeMode } from './chartCompiler';
import { parseYueChartSpec, validateYueChartSpec, type YueChartSpec } from './chartSpec';

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  DatasetComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  TransformComponent,
  CanvasRenderer,
]);

type ChartInstanceState = {
  chart: ECharts;
  resizeObserver?: ResizeObserver;
};

const chartInstances = new WeakMap<Element, ChartInstanceState>();

const decodeSpec = (container: Element): string => {
  const encoded = container.getAttribute('data-spec') || '';
  return decodeURIComponent(encoded);
};

const isDarkMode = (): boolean =>
  typeof document !== 'undefined' && document.documentElement.classList.contains('dark');

const themeMode = (): YueChartThemeMode => (isDarkMode() ? 'dark' : 'light');

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const setError = (container: Element, title: string, detail: string, raw?: string) => {
  container.setAttribute('data-processed', 'true');
  container.innerHTML = `
    <div class="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
      <div class="font-semibold">Chart Error</div>
      <div class="mt-1 opacity-90">${escapeHtml(title)}</div>
      <div class="mt-1 text-xs opacity-75">${escapeHtml(detail)}</div>
      ${raw ? `
        <details class="mt-3">
          <summary class="cursor-pointer text-xs font-semibold opacity-80">Show chart JSON</summary>
          <pre class="mt-2 max-h-64 overflow-auto rounded-lg border border-red-200 bg-red-100 p-3 text-xs whitespace-pre-wrap dark:border-red-800/50 dark:bg-red-900/40"></pre>
        </details>
      ` : ''}
    </div>
  `;
  const pre = container.querySelector('pre');
  if (pre && raw) pre.textContent = raw;
};

const specForContainer = (container: Element): { raw: string; spec?: YueChartSpec; error?: string } => {
  const raw = decodeSpec(container);
  const parsed = parseYueChartSpec(raw);
  if (!parsed.ok) return { raw, error: parsed.error.message };
  const widget = container.closest('.yue-chart-widget') as HTMLElement | null;
  const override = widget?.getAttribute('data-chart-type-override') || '';
  if (!override) return { raw, spec: parsed.spec };
  const overridden = validateYueChartSpec({ ...parsed.spec, chartType: override });
  if (!overridden.ok) return { raw, error: overridden.error.message };
  return { raw, spec: overridden.spec };
};

const csvEscape = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

const chartDataToCsv = (spec: YueChartSpec): string => {
  const fields = Array.from(spec.data.reduce<Set<string>>((acc, row) => {
    Object.keys(row).forEach((field) => acc.add(field));
    return acc;
  }, new Set()));
  return [
    fields.map(csvEscape).join(','),
    ...spec.data.map((row) => fields.map((field) => csvEscape(row[field])).join(',')),
  ].join('\n');
};

const renderDataTable = (widget: Element, spec: YueChartSpec) => {
  const target = widget.querySelector<HTMLElement>('.yue-chart-data-table');
  if (!target) return;
  const fields = Array.from(spec.data.reduce<Set<string>>((acc, row) => {
    Object.keys(row).forEach((field) => acc.add(field));
    return acc;
  }, new Set()));
  if (fields.length === 0) {
    target.textContent = 'No data';
    return;
  }
  target.innerHTML = `
    <table class="w-full border-collapse text-left">
      <thead>
        <tr>
          ${fields.map((field) => `<th class="border border-gray-200 bg-white px-3 py-2 font-bold text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-200">${escapeHtml(field)}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${spec.data.map((row) => `
          <tr>
            ${fields.map((field) => `<td class="border border-gray-200 px-3 py-2 text-gray-600 dark:border-gray-800 dark:text-gray-300">${escapeHtml(String(row[field] ?? ''))}</td>`).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
};

const downloadDataUrl = (dataUrl: string, filename: string) => {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
};

export const renderYueChart = (container: Element): boolean => {
  const parsed = specForContainer(container);
  if (!parsed.spec) {
    setError(container, parsed.error || 'Chart spec is invalid.', 'invalid_chart_spec', parsed.raw);
    return false;
  }

  const chartHost = container.querySelector<HTMLElement>('.yue-chart-canvas');
  if (!chartHost) {
    setError(container, 'Chart container is missing.', 'missing_canvas', parsed.raw);
    return false;
  }

  const existing = chartInstances.get(container);
  if (existing) {
    existing.chart.dispose();
    existing.resizeObserver?.disconnect();
    chartInstances.delete(container);
  }

  const chart = echarts.init(chartHost, undefined, { renderer: 'canvas' });
  chart.setOption(compileYueChartOption(parsed.spec, themeMode()));
  const resizeObserver = typeof ResizeObserver !== 'undefined'
    ? new ResizeObserver(() => chart.resize())
    : undefined;
  resizeObserver?.observe(chartHost);
  chartInstances.set(container, { chart, resizeObserver });

  const jsonPanel = container.querySelector<HTMLElement>('.yue-chart-json-panel');
  const jsonPre = jsonPanel?.querySelector('pre');
  if (jsonPre) jsonPre.textContent = JSON.stringify(parsed.spec, null, 2);
  const widget = container.closest('.yue-chart-widget');
  if (widget) renderDataTable(widget, parsed.spec);

  container.setAttribute('data-processed', 'true');
  return true;
};

export const renderPendingYueCharts = () => {
  document.querySelectorAll('.yue-chart-render-target:not([data-processed="true"])').forEach((container) => {
    const widget = container.closest('.yue-chart-widget');
    if (widget?.getAttribute('data-complete') !== 'true') return;
    renderYueChart(container);
  });
};

export const handleYueChartClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null;
  const button = target?.closest('[data-yue-chart-action]') as HTMLElement | null;
  if (!button) return;
  const widget = button.closest('.yue-chart-widget') as HTMLElement | null;
  if (!widget) return;
  const action = button.getAttribute('data-yue-chart-action');
  if (action === 'tab-chart' || action === 'tab-json' || action === 'tab-data') {
    const showJson = action === 'tab-json';
    const showData = action === 'tab-data';
    widget.querySelector('[data-yue-chart-action="tab-chart"]')?.classList.toggle('bg-gray-100', !showJson && !showData);
    widget.querySelector('[data-yue-chart-action="tab-chart"]')?.classList.toggle('text-gray-900', !showJson && !showData);
    widget.querySelector('[data-yue-chart-action="tab-json"]')?.classList.toggle('bg-gray-100', showJson);
    widget.querySelector('[data-yue-chart-action="tab-json"]')?.classList.toggle('text-gray-900', showJson);
    widget.querySelector('[data-yue-chart-action="tab-data"]')?.classList.toggle('bg-gray-100', showData);
    widget.querySelector('[data-yue-chart-action="tab-data"]')?.classList.toggle('text-gray-900', showData);
    widget.querySelector('.yue-chart-canvas-panel')?.classList.toggle('hidden', showJson || showData);
    widget.querySelector('.yue-chart-json-panel')?.classList.toggle('hidden', !showJson);
    widget.querySelector('.yue-chart-data-panel')?.classList.toggle('hidden', !showData);
    return;
  }

  const container = widget.querySelector('.yue-chart-render-target') as HTMLElement | null;
  if (!container) return;
  const state = chartInstances.get(container);
  const parsed = specForContainer(container);
  if (!parsed.spec) return;
  if (action === 'copy-data') {
    void navigator.clipboard?.writeText(chartDataToCsv(parsed.spec));
    return;
  }
  if (action === 'download-png' && state?.chart) {
    downloadDataUrl(state.chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' }), `${parsed.spec.title || 'yue-chart'}.png`);
  }
};

export const handleYueChartChange = (event: Event) => {
  const target = event.target as HTMLSelectElement | null;
  if (!target?.matches('[data-yue-chart-type-select]')) return;
  const widget = target.closest('.yue-chart-widget') as HTMLElement | null;
  const container = widget?.querySelector('.yue-chart-render-target') as HTMLElement | null;
  if (!widget || !container) return;
  const previous = widget.getAttribute('data-chart-type-override') || '';
  const nextType = target.value;
  widget.setAttribute('data-chart-type-override', nextType);
  const parsed = specForContainer(container);
  if (!parsed.spec) {
    widget.setAttribute('data-chart-type-override', previous);
    target.value = previous;
    return;
  }
  container.setAttribute('data-processed', 'false');
  const canvasPanel = widget.querySelector<HTMLElement>('.yue-chart-canvas-panel');
  const chartTarget = container.querySelector<HTMLElement>('.yue-chart-canvas') || document.createElement('div');
  if (!chartTarget.classList.contains('yue-chart-canvas')) {
    chartTarget.className = 'yue-chart-canvas h-[360px] min-h-[320px] w-full';
    container.innerHTML = '';
    container.appendChild(chartTarget);
  }
  canvasPanel?.classList.remove('hidden');
  widget.querySelector('.yue-chart-json-panel')?.classList.add('hidden');
  widget.querySelector('.yue-chart-data-panel')?.classList.add('hidden');
  renderYueChart(container);
};

export const disposeYueCharts = () => {
  document.querySelectorAll('.yue-chart-render-target[data-processed="true"]').forEach((container) => {
    const existing = chartInstances.get(container);
    existing?.chart.dispose();
    existing?.resizeObserver?.disconnect();
    chartInstances.delete(container);
  });
};
