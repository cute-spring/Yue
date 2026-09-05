type YueChartWidgetOptions = {
  complete?: boolean;
  showLoading?: boolean;
};

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

export const renderYueChartWidgetHtml = (rawSpec: unknown, options: YueChartWidgetOptions = {}): string => {
  const text = typeof rawSpec === 'string' ? rawSpec : (JSON.stringify(rawSpec, null, 2) ?? 'null');
  const isComplete = options.complete ?? true;
  const encodedContent = encodeURIComponent(text).replace(/'/g, '%27');
  const escaped = escapeHtml(text);

  return `
    <div class="yue-chart-widget my-4" data-complete="${isComplete}" data-chart-type-override="">
      <div class="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-xl shadow-sm dark:bg-[#0d1117] dark:border-gray-800">
        <div class="flex items-center gap-2">
          <button type="button" data-yue-chart-action="tab-chart" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${isComplete ? 'bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100' : 'text-gray-400 cursor-not-allowed'}" ${!isComplete ? 'disabled' : ''}>Chart</button>
          <button type="button" data-yue-chart-action="tab-json" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors text-gray-500 hover:text-gray-800 hover:bg-gray-50 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800">JSON</button>
          <button type="button" data-yue-chart-action="tab-data" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors text-gray-500 hover:text-gray-800 hover:bg-gray-50 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800" ${!isComplete ? 'disabled' : ''}>Data</button>
        </div>
        <div class="flex items-center gap-2">
          <select data-yue-chart-type-select="1" class="max-w-[9rem] rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-xs font-semibold text-gray-700 outline-none hover:border-gray-300 focus:ring-2 focus:ring-emerald-500/20 dark:border-gray-800 dark:bg-[#0d1117] dark:text-gray-200" title="Switch chart type" ${!isComplete ? 'disabled' : ''}>
            <option value="">Original</option>
            <option value="bar">Bar</option>
            <option value="line">Line</option>
            <option value="area">Area</option>
            <option value="scatter">Scatter</option>
            <option value="pie">Pie</option>
            <option value="stacked-bar">Stacked bar</option>
            <option value="multi-line">Multi-line</option>
          </select>
          <button type="button" data-yue-chart-action="copy-data" class="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100" title="Copy chart data" ${!isComplete ? 'disabled' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          </button>
          <button type="button" data-yue-chart-action="download-png" class="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-50 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100" title="Export chart image" ${!isComplete ? 'disabled' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
          </button>
          <span class="text-[10px] font-black font-mono uppercase tracking-[0.2em] text-text-secondary/50">YueChartSpec</span>
        </div>
      </div>
      <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden dark:bg-[#0d1117] dark:border-gray-800">
        <div class="yue-chart-canvas-panel">
          <div class="yue-chart-render-target" data-spec="${encodedContent}" data-processed="false">
            ${isComplete ? `
              <div class="yue-chart-canvas h-[360px] min-h-[320px] w-full"></div>
            ` : `
              <div class="flex min-h-[320px] flex-col items-center justify-center text-gray-400">
                <div class="w-8 h-8 border-2 border-gray-200 border-t-emerald-400 rounded-full animate-spin mb-4"></div>
                <div class="text-xs font-medium animate-pulse">Generating chart...</div>
              </div>
            `}
          </div>
        </div>
        <div class="yue-chart-json-panel hidden">
          <pre class="max-h-[28rem] overflow-auto bg-gray-50 p-6 text-xs font-mono leading-relaxed text-gray-700 whitespace-pre-wrap dark:bg-gray-900 dark:text-gray-300"><code>${escaped}</code></pre>
        </div>
        <div class="yue-chart-data-panel hidden">
          <div class="max-h-[28rem] overflow-auto bg-gray-50 p-4 dark:bg-gray-900">
            <div class="yue-chart-data-table text-xs text-gray-700 dark:text-gray-300"></div>
          </div>
        </div>
      </div>
    </div>
  `;
};

export const renderStructuredChartArtifactHtml = (rawSpec: unknown): string =>
  renderYueChartWidgetHtml(rawSpec, { complete: true });
