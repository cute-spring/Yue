import { createEffect, createMemo, createSignal, onMount, Show } from 'solid-js';
import hljs from 'highlight.js';
import mermaid from 'mermaid';
import { getMermaidInitConfig, getMermaidThemePreset, MERMAID_THEME_PRESETS, setMermaidThemePreset, type MermaidThemePreset } from '../utils/mermaidTheme';
import { buildExportSvgString, canCopyPng, copyPngBlobToClipboard, copyTextToClipboard, downloadBlob, getMermaidExportPrefs, getMermaidExportTimestamp, sanitizeFilenameBase, setMermaidExportPrefs, svgStringToPngBlob } from '../utils/mermaidExport';

interface MermaidViewerProps {
  code: string;
  className?: string;
  initialTab?: 'diagram' | 'code';
}

export default function MermaidViewer(props: MermaidViewerProps) {
  const [tab, setTab] = createSignal<'diagram' | 'code'>(props.initialTab || 'diagram');
  const [error, setError] = createSignal<string | null>(null);
  const [scale, setScale] = createSignal(1);
  const [tx, setTx] = createSignal(0);
  const [ty, setTy] = createSignal(0);
  const [isPanning, setIsPanning] = createSignal(false);
  const [isFullscreen, setIsFullscreen] = createSignal(false);
  const [dimensions, setDimensions] = createSignal({ width: 0, height: 0 });
  const [themePreset, setThemePreset] = createSignal(getMermaidThemePreset());
  const [isExportOpen, setIsExportOpen] = createSignal(false);
  const exportPrefs = getMermaidExportPrefs();
  const [exportFormat, setExportFormat] = createSignal<'png' | 'svg' | 'mmd'>(exportPrefs.format);
  const [exportBackground, setExportBackground] = createSignal<'transparent' | 'light' | 'dark' | 'custom'>(exportPrefs.background);
  const [exportBackgroundColor, setExportBackgroundColor] = createSignal(exportPrefs.backgroundColor);
  const [exportScale, setExportScale] = createSignal(exportPrefs.scale);
  const [exportPadding, setExportPadding] = createSignal(exportPrefs.padding);
  const [exportFilename, setExportFilename] = createSignal(exportPrefs.filename);
  const [exportBusy, setExportBusy] = createSignal(false);
  const [exportStatus, setExportStatus] = createSignal<string | null>(null);
  const [exportContainerId, setExportContainerId] = createSignal<string | null>(null);
  const baseId = `mermaid-viewer-${Math.random().toString(36).slice(2, 11)}`;
  let exportDialogRef: HTMLDivElement | undefined;
  let exportPrimaryBtnRef: HTMLButtonElement | undefined;
  let exportLastFocus: HTMLElement | null = null;
  let exportPrevOverflow = '';

  const normalize = (code: string) => {
    let normalized = code.replace(/^\uFEFF/, '').trim();
    const lines = normalized.split('\n');
    if (lines.length >= 2) {
      const first = lines[0].trim();
      const last = lines[lines.length - 1].trim();
      if (/^```/.test(first)) lines.shift();
      if (/^```/.test(last)) lines.pop();
    }
    normalized = lines.join('\n').trim();
    normalized = normalized.replace(/^```mermaid\s*/i, '').trim();
    normalized = normalized.replace(/ - -?> /g, ' --> ');
    normalized = normalized.replace(/ = =?> /g, ' ==> ');
    normalized = normalized.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    return normalized;
  };

  const zoomTo = (next: number) => setScale(Math.min(4, Math.max(0.25, next)));
  const zoomIn = () => zoomTo(scale() * 1.2);
  const zoomOut = () => zoomTo(scale() / 1.2);
  const resetZoom = () => {
    zoomTo(1);
    setTx(0);
    setTy(0);
  };

  let panStart: { x: number; y: number; tx: number; ty: number } | null = null;
  const startPan = (e: PointerEvent) => {
    if (tab() !== 'diagram') return;
    if (e.button !== 0) return;
    panStart = { x: e.clientX, y: e.clientY, tx: tx(), ty: ty() };
    setIsPanning(true);
    (e.currentTarget as HTMLElement | null)?.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  };
  const movePan = (e: PointerEvent) => {
    if (!panStart) return;
    e.preventDefault();
    setTx(panStart.tx + (e.clientX - panStart.x));
    setTy(panStart.ty + (e.clientY - panStart.y));
  };
  const endPan = () => {
    panStart = null;
    setIsPanning(false);
  };

  const fitTo = (containerId: string) => {
    const container = document.getElementById(containerId);
    const svg = container?.querySelector('svg') as SVGSVGElement | null;
    const viewport = container?.closest('.mermaid-viewer-viewport') as HTMLElement | null;
    if (!svg || !viewport) return;
    const availW = viewport.clientWidth;
    const availH = viewport.clientHeight;
    if (!availW || !availH) return;

    let baseW = 0;
    let baseH = 0;
    const vb = (svg as any).viewBox?.baseVal;
    if (vb && vb.width > 0 && vb.height > 0) {
      baseW = vb.width;
      baseH = vb.height;
    } else {
      const wAttr = svg.getAttribute('width') || '';
      const hAttr = svg.getAttribute('height') || '';
      baseW = parseFloat(wAttr.replace('px', '')) || 0;
      baseH = parseFloat(hAttr.replace('px', '')) || 0;
    }
    if (!baseW || !baseH) {
      const rect = svg.getBoundingClientRect();
      baseW = rect.width / scale();
      baseH = rect.height / scale();
    }
    if (!baseW || !baseH) return;

    const padding = 56;
    const rawScale = Math.min((availW - padding) / baseW, (availH - padding) / baseH);
    const nextScale = Math.min(rawScale * 0.95, 1.2);
    if (!Number.isFinite(nextScale) || nextScale <= 0) return;
    zoomTo(nextScale);
    setTx(0);
    setTy(0);
    try {
      viewport.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    } catch (e) {
      viewport.scrollTop = 0;
      viewport.scrollLeft = 0;
    }
  };

  const exportFromContainer = async (mode: 'copy' | 'download') => {
    if (exportBusy()) return;
    setExportBusy(true);
    setExportStatus(null);
    const containerId = exportContainerId() || `${baseId}-diagram`;
    const svg = (document.getElementById(containerId)?.querySelector('svg') as SVGSVGElement | null) || null;
    const normalized = normalizedCode();
    const ts = getMermaidExportTimestamp();
    const base = sanitizeFilenameBase(exportFilename());

    if (exportFormat() === 'mmd') {
      try {
        if (mode === 'copy') await copyTextToClipboard(normalized);
        else downloadBlob(new Blob([normalized], { type: 'text/plain;charset=utf-8' }), `${base}-${ts}.mmd`);
        if (isExportOpen()) setExportStatus(mode === 'copy' ? 'Copied MMD' : 'Exported MMD');
      } finally {
        setExportBusy(false);
      }
      return;
    }
    if (!svg) {
      setExportBusy(false);
      return;
    }
    const svgString = buildExportSvgString(svg, { padding: exportPadding(), background: exportBackground(), backgroundColor: exportBackgroundColor() });

    if (exportFormat() === 'svg') {
      try {
        if (mode === 'copy') await copyTextToClipboard(svgString);
        else downloadBlob(new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' }), `${base}-${ts}.svg`);
        if (isExportOpen()) setExportStatus(mode === 'copy' ? 'Copied SVG' : 'Exported SVG');
      } finally {
        setExportBusy(false);
      }
      return;
    }
    try {
      const pngBlob = await svgStringToPngBlob(svgString, exportScale());
      if (!pngBlob) return;
      if (mode === 'download') {
        downloadBlob(pngBlob, `${base}-${ts}.png`);
        if (isExportOpen()) setExportStatus('Exported PNG');
        return;
      }
      if (!canCopyPng()) return;
      await copyPngBlobToClipboard(pngBlob);
      if (isExportOpen()) setExportStatus('Copied PNG');
    } finally {
      setExportBusy(false);
    }
  };

  const handleExportKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      setIsExportOpen(false);
      return;
    }
    if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
      const active = document.activeElement as HTMLElement | null;
      if (active && active.tagName === 'TEXTAREA') return;
      if (active && active.tagName === 'BUTTON') return;
      if (exportBusy()) return;
      e.preventDefault();
      exportFromContainer('download');
      return;
    }
    if (e.key !== 'Tab') return;
    const dialog = exportDialogRef;
    if (!dialog) return;
    const focusable = Array.from(
      dialog.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
    ).filter((el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && el.offsetParent !== null);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const current = document.activeElement as HTMLElement | null;
    if (e.shiftKey) {
      if (!current || current === first || !dialog.contains(current)) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (!current || current === last || !dialog.contains(current)) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  const exportPreviewStyle = createMemo(() => {
    if (exportBackground() === 'transparent') {
      return {
        'background-image':
          'linear-gradient(45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(-45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, rgba(148,163,184,.18) 75%), linear-gradient(-45deg, transparent 75%, rgba(148,163,184,.18) 75%)',
        'background-size': '18px 18px',
        'background-position': '0 0, 0 9px, 9px -9px, -9px 0px',
      } as any;
    }
    const fill = exportBackground() === 'custom' ? exportBackgroundColor() : exportBackground() === 'dark' ? '#0b1220' : '#ffffff';
    return { background: fill } as any;
  });

  const exportPreviewSvg = createMemo(() => {
    if (!isExportOpen()) return '';
    if (exportFormat() === 'mmd') return '';
    const id = exportContainerId() || `${baseId}-diagram`;
    const svg = document.getElementById(id)?.querySelector('svg') as SVGSVGElement | null;
    if (!svg) return '';
    return buildExportSvgString(svg, { padding: exportPadding(), background: exportBackground(), backgroundColor: exportBackgroundColor() });
  });

  createEffect(() => {
    if (isExportOpen()) {
      exportLastFocus = document.activeElement as HTMLElement | null;
      exportPrevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      requestAnimationFrame(() => (exportPrimaryBtnRef || exportDialogRef)?.focus?.());
    } else {
      exportLastFocus?.focus?.();
      exportLastFocus = null;
      document.body.style.overflow = exportPrevOverflow;
      setExportBusy(false);
      setExportStatus(null);
    }
  });

  const renderInto = async (containerId: string, code: string) => {
    const chart = normalize(code);
    if (!chart) return;
    try {
      setError(null);
      const renderId = `${baseId}-${containerId}-${Date.now()}`;
      await mermaid.parse(chart);
      const { svg } = await mermaid.render(renderId, chart);
      const el = document.getElementById(containerId);
      if (!el) return;
      el.innerHTML = svg;
      const parser = new DOMParser();
      const svgDoc = parser.parseFromString(svg, 'image/svg+xml');
      const svgEl = svgDoc.documentElement;
      const width = parseInt(svgEl.getAttribute('width') || '0');
      const height = parseInt(svgEl.getAttribute('height') || '0');
      setDimensions({ width, height });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to render diagram');
    }
  };

  const normalizedCode = createMemo(() => normalize(props.code));
  const highlightedCode = createMemo(() => hljs.highlight(normalizedCode(), { language: 'plaintext' }).value);

  onMount(() => {
    (mermaid as any).initialize(getMermaidInitConfig(themePreset()));
  });

  createEffect(() => {
    props.code;
    themePreset();
    (mermaid as any).initialize(getMermaidInitConfig(themePreset()));
    requestAnimationFrame(() => renderInto(`${baseId}-diagram`, props.code));
    if (isFullscreen()) requestAnimationFrame(() => renderInto(`${baseId}-diagram-full`, props.code));
  });

  const Toolbar = (containerId: string) => (
    <div class="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-xl shadow-sm">
      <div class="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setTab('diagram')}
          class={`px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${tab() === 'diagram' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}
        >
          Diagram
        </button>
        <button
          type="button"
          onClick={() => setTab('code')}
          class={`px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${tab() === 'code' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}
        >
          Code
        </button>
      </div>
      <div class="flex items-center gap-1.5 text-gray-500">
        <button type="button" onClick={zoomOut} class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom out">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
        </button>
        <button type="button" onClick={zoomIn} class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom in">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
        </button>
        <div class="w-px h-5 bg-gray-200 mx-1" />
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold text-gray-500">Theme</span>
          <select
            value={themePreset()}
            onChange={(e) => {
              const next = (e.currentTarget.value || 'default') as MermaidThemePreset;
              setMermaidThemePreset(next);
              setThemePreset(next);
            }}
            class="text-sm font-semibold text-gray-800 bg-white border border-gray-200 rounded-lg px-2 py-1.5 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
            title="Theme"
          >
            {MERMAID_THEME_PRESETS.map((p) => (
              <option value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>
        <button type="button" onClick={() => fitTo(containerId)} class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fit">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 3H3v5" />
            <path d="M16 3h5v5" />
            <path d="M21 16v5h-5" />
            <path d="M3 16v5h5" />
          </svg>
          <span class="text-sm font-semibold">Fit</span>
        </button>
        <button
          type="button"
          onClick={() => {
            setExportContainerId(containerId);
            setExportStatus(null);
            setExportBusy(false);
            setIsExportOpen(true);
          }}
          class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2"
          title="Export"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-semibold">Export</span>
        </button>
        <button type="button" onClick={() => setIsFullscreen(true)} class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fullscreen">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h5a1 1 0 110 2H6v3a1 1 0 11-2 0V4zm14 0a1 1 0 00-1-1h-5a1 1 0 100 2h3v3a1 1 0 102 0V4zM3 16a1 1 0 001 1h5a1 1 0 100-2H6v-3a1 1 0 10-2 0v4zm14 0a1 1 0 01-1 1h-5a1 1 0 110-2h3v-3a1 1 0 112 0v4z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-semibold">Fullscreen</span>
        </button>
        <button type="button" onClick={resetZoom} class="px-2 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Reset zoom">
          <span class="text-sm font-semibold">{Math.round(scale() * 100)}%</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      <div class={props.className || ''}>
        {Toolbar(`${baseId}-diagram`)}
        <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden">
          <Show when={!error()} fallback={<div class="p-4 text-sm text-red-700 bg-red-50">{error()}</div>}>
            <Show when={tab() === 'diagram'}>
              <div
                class="mermaid-viewer-viewport w-full overflow-auto"
                onWheel={(e) => { if (e.ctrlKey) { e.preventDefault(); zoomTo(scale() * (e.deltaY > 0 ? 0.9 : 1.1)); } }}
                onPointerMove={movePan as any}
                onPointerUp={endPan}
                onPointerCancel={endPan}
                onPointerDown={startPan as any}
              >
                <div class="min-h-[240px] flex justify-center items-start p-6" style={{ transform: `translate(${tx()}px, ${ty()}px) scale(${scale()})`, 'transform-origin': 'top center', cursor: isPanning() ? 'grabbing' : 'grab' }}>
                  <div id={`${baseId}-diagram`} class="w-full flex justify-center" />
                </div>
              </div>
            </Show>
            <Show when={tab() === 'code'}>
              <div class="p-4">
              <pre class="text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-xl p-4 overflow-auto whitespace-pre-wrap"><code class="hljs language-plaintext" innerHTML={highlightedCode()} /></pre>
              </div>
            </Show>
          </Show>
        </div>
        <Show when={dimensions().width > 0}>
          <div class="mt-2 text-[10px] text-gray-400 font-mono">{dimensions().width}×{dimensions().height}px</div>
        </Show>
      </div>

      <Show when={isFullscreen()}>
        <div class="fixed inset-0 z-[999] bg-black/50 backdrop-blur-sm" onClick={() => setIsFullscreen(false)} />
        <div class="fixed inset-0 z-[1000] p-6 flex items-center justify-center">
          <div class="w-full max-w-6xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
            <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <div class="text-sm font-bold text-gray-800">Mermaid</div>
              <button type="button" onClick={() => setIsFullscreen(false)} class="p-2 rounded-lg hover:bg-gray-50 text-gray-500 hover:text-gray-800">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
            <div class="p-4">
              {Toolbar(`${baseId}-diagram-full`)}
              <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden">
                <Show when={!error()} fallback={<div class="p-4 text-sm text-red-700 bg-red-50">{error()}</div>}>
                  <Show when={tab() === 'diagram'}>
                    <div
                      class="mermaid-viewer-viewport w-full max-h-[70vh] overflow-auto"
                      onWheel={(e) => { if (e.ctrlKey) { e.preventDefault(); zoomTo(scale() * (e.deltaY > 0 ? 0.9 : 1.1)); } }}
                      onPointerMove={movePan as any}
                      onPointerUp={endPan}
                      onPointerCancel={endPan}
                      onPointerDown={startPan as any}
                    >
                      <div class="min-h-[360px] flex justify-center items-start p-8" style={{ transform: `translate(${tx()}px, ${ty()}px) scale(${scale()})`, 'transform-origin': 'top center', cursor: isPanning() ? 'grabbing' : 'grab' }}>
                        <div id={`${baseId}-diagram-full`} class="w-full flex justify-center" />
                      </div>
                    </div>
                  </Show>
                  <Show when={tab() === 'code'}>
                    <div class="p-4">
                      <pre class="text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-xl p-4 overflow-auto whitespace-pre-wrap"><code class="hljs language-plaintext" innerHTML={highlightedCode()} /></pre>
                    </div>
                  </Show>
                </Show>
              </div>
            </div>
          </div>
        </div>
      </Show>

      <Show when={isExportOpen()}>
        <div class="fixed inset-0 z-[1300]">
          <div class="absolute inset-0 bg-slate-900/25 backdrop-blur-md" onClick={() => setIsExportOpen(false)} />
          <div class="absolute inset-0 flex items-start justify-center px-3 pb-3 pt-3 sm:px-6 sm:pb-6 sm:pt-6">
            <div
              ref={(el) => (exportDialogRef = el)}
              class="w-[min(1120px,98vw)] h-[min(740px,94vh)] bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col"
              role="dialog"
              aria-modal="true"
              aria-labelledby={`${baseId}-export-title`}
              aria-describedby={`${baseId}-export-desc`}
              tabIndex={-1}
              onKeyDown={handleExportKeyDown}
            >
              <div class="h-16 px-6 border-b border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M3 3a1 1 0 011-1h4a1 1 0 010 2H5v12h10V4h-3a1 1 0 110-2h4a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3z" />
                      <path d="M9 9a1 1 0 011-1h0a1 1 0 011 1v4.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 111.414-1.414L9 13.586V9z" />
                    </svg>
                  </div>
                  <div>
                    <div id={`${baseId}-export-title`} class="text-sm font-extrabold text-text-primary">
                      Export diagram
                    </div>
                    <div id={`${baseId}-export-desc`} class="text-xs text-text-secondary/70">
                      PNG / SVG / MMD • Background • Advanced
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  class="p-2 rounded-xl hover:bg-surface-elevated text-text-secondary/70 hover:text-text-primary transition-colors"
                  onClick={() => setIsExportOpen(false)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>

              <div class="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-5">
                <div class="md:col-span-2 p-5 border-b md:border-b-0 md:border-r border-border overflow-auto">
                  <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Export format</div>
                  <div class="mt-3 grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      disabled={exportBusy()}
                      onClick={() => {
                        setExportFormat('png');
                        setMermaidExportPrefs({ format: 'png' });
                      }}
                      class={`px-3 py-3 rounded-xl border transition-colors text-left ${exportFormat() === 'png' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`}
                    >
                      <div class="text-sm font-extrabold text-text-primary">PNG</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Raster image</div>
                    </button>
                    <button
                      type="button"
                      disabled={exportBusy()}
                      onClick={() => {
                        setExportFormat('svg');
                        setMermaidExportPrefs({ format: 'svg' });
                      }}
                      class={`px-3 py-3 rounded-xl border transition-colors text-left ${exportFormat() === 'svg' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`}
                    >
                      <div class="text-sm font-extrabold text-text-primary">SVG</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Vector</div>
                    </button>
                    <button
                      type="button"
                      disabled={exportBusy()}
                      onClick={() => {
                        setExportFormat('mmd');
                        setMermaidExportPrefs({ format: 'mmd' });
                      }}
                      class={`px-3 py-3 rounded-xl border transition-colors text-left ${exportFormat() === 'mmd' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`}
                    >
                      <div class="text-sm font-extrabold text-text-primary">MMD</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Mermaid source</div>
                    </button>
                  </div>

                  <Show when={exportFormat() !== 'mmd'}>
                    <div class="mt-6 text-xs font-black uppercase tracking-wider text-text-secondary/60">Background</div>
                    <div class="mt-3 grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        disabled={exportBusy()}
                        onClick={() => {
                          setExportBackground('transparent');
                          setMermaidExportPrefs({ background: 'transparent' });
                        }}
                        class={`px-3 py-3 rounded-xl border transition-colors text-left ${
                          exportBackground() === 'transparent' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'
                        }`}
                      >
                        <div class="text-sm font-extrabold text-text-primary">Transparent</div>
                        <div class="text-[11px] text-text-secondary/70 mt-0.5">Checker preview</div>
                      </button>
                      <button
                        type="button"
                        disabled={exportBusy()}
                        onClick={() => {
                          setExportBackground('light');
                          setMermaidExportPrefs({ background: 'light' });
                        }}
                        class={`px-3 py-3 rounded-xl border transition-colors text-left ${
                          exportBackground() === 'light' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'
                        }`}
                      >
                        <div class="text-sm font-extrabold text-text-primary">Light</div>
                        <div class="text-[11px] text-text-secondary/70 mt-0.5">White</div>
                      </button>
                      <button
                        type="button"
                        disabled={exportBusy()}
                        onClick={() => {
                          setExportBackground('dark');
                          setMermaidExportPrefs({ background: 'dark' });
                        }}
                        class={`px-3 py-3 rounded-xl border transition-colors text-left ${
                          exportBackground() === 'dark' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'
                        }`}
                      >
                        <div class="text-sm font-extrabold text-text-primary">Dark</div>
                        <div class="text-[11px] text-text-secondary/70 mt-0.5">Deep navy</div>
                      </button>
                      <button
                        type="button"
                        disabled={exportBusy()}
                        onClick={() => {
                          setExportBackground('custom');
                          setMermaidExportPrefs({ background: 'custom' });
                        }}
                        class={`px-3 py-3 rounded-xl border transition-colors text-left ${
                          exportBackground() === 'custom' ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'
                        }`}
                      >
                        <div class="flex items-center justify-between">
                          <div>
                            <div class="text-sm font-extrabold text-text-primary">Custom</div>
                            <div class="text-[11px] text-text-secondary/70 mt-0.5">Pick a color</div>
                          </div>
                          <input
                            type="color"
                            value={exportBackgroundColor()}
                            disabled={exportBusy()}
                            onInput={(e) => {
                              setExportBackgroundColor(e.currentTarget.value);
                              setExportBackground('custom');
                              setMermaidExportPrefs({ backgroundColor: e.currentTarget.value, background: 'custom' });
                            }}
                            class="w-9 h-9 rounded-xl border border-border bg-transparent p-1 cursor-pointer"
                          />
                        </div>
                      </button>
                    </div>
                  </Show>

                  <Show when={exportFormat() !== 'mmd'}>
                    <details class="mt-6 group">
                      <summary class="cursor-pointer select-none text-xs font-black uppercase tracking-wider text-text-secondary/60 flex items-center justify-between">
                        <span>Advanced</span>
                        <span class="text-[11px] text-text-secondary/40 group-open:hidden">Show</span>
                        <span class="text-[11px] text-text-secondary/40 hidden group-open:inline">Hide</span>
                      </summary>
                      <div class="mt-3 space-y-4">
                        <Show when={exportFormat() === 'png'}>
                          <div>
                            <div class="flex items-center justify-between">
                              <div class="text-sm font-bold text-text-primary">PNG scale</div>
                              <div class="text-xs font-mono text-text-secondary/70">{exportScale()}x</div>
                            </div>
                            <input
                              type="range"
                              min="1"
                              max="4"
                              step="1"
                              value={exportScale()}
                              disabled={exportBusy()}
                              onInput={(e) => {
                                const next = parseInt(e.currentTarget.value, 10) || 2;
                                setExportScale(next);
                                setMermaidExportPrefs({ scale: next });
                              }}
                              class="w-full mt-2"
                            />
                            <div class="mt-1 text-[11px] text-text-secondary/60">Only affects PNG export.</div>
                          </div>
                        </Show>
                        <div>
                          <div class="flex items-center justify-between">
                            <div class="text-sm font-bold text-text-primary">Padding</div>
                            <div class="text-xs font-mono text-text-secondary/70">{exportPadding()}px</div>
                          </div>
                          <input
                            type="range"
                            min="0"
                            max="96"
                            step="4"
                            value={exportPadding()}
                            disabled={exportBusy()}
                            onInput={(e) => {
                              const next = parseInt(e.currentTarget.value, 10) || 0;
                              setExportPadding(next);
                              setMermaidExportPrefs({ padding: next });
                            }}
                            class="w-full mt-2"
                          />
                          <div class="mt-1 text-[11px] text-text-secondary/60">Adds margin around the diagram.</div>
                        </div>
                      </div>
                    </details>
                  </Show>

                  <div class="mt-6">
                    <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">File name</div>
                    <input
                      type="text"
                      value={exportFilename()}
                      disabled={exportBusy()}
                      onInput={(e) => {
                        setExportFilename(e.currentTarget.value);
                        setMermaidExportPrefs({ filename: e.currentTarget.value });
                      }}
                      class="mt-2 w-full px-3 py-2 rounded-xl border border-border bg-surface text-sm font-semibold text-text-primary placeholder:text-text-secondary/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
                      placeholder="diagram"
                    />
                    <div class="mt-1 text-[11px] text-text-secondary/60">Extension is added automatically.</div>
                  </div>
                </div>

                <div class="md:col-span-3 p-5 min-h-0 flex flex-col">
                  <div class="flex items-center justify-between">
                    <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Preview</div>
                    <Show when={exportStatus()}>
                      <div class="text-[11px] font-bold text-primary bg-primary/10 border border-primary/20 px-2 py-1 rounded-full">
                        {exportStatus()}
                      </div>
                    </Show>
                    <div class="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => exportFromContainer('copy')}
                        disabled={exportBusy() || (exportFormat() === 'png' && !canCopyPng())}
                        title={exportFormat() === 'png' && !canCopyPng() ? 'Your browser does not support copying PNG to clipboard.' : ''}
                        class={`px-3 py-2 rounded-xl border border-border transition-colors text-sm font-bold ${
                          exportBusy() || (exportFormat() === 'png' && !canCopyPng())
                            ? 'bg-surface text-text-secondary/40 cursor-not-allowed'
                            : 'bg-surface hover:bg-surface-elevated/70 text-text-primary'
                        }`}
                      >
                        {exportFormat() === 'mmd' ? 'Copy MMD' : exportFormat() === 'svg' ? 'Copy SVG' : 'Copy PNG'}
                      </button>
                      <button
                        ref={(el) => (exportPrimaryBtnRef = el)}
                        type="button"
                        disabled={exportBusy()}
                        onClick={() => exportFromContainer('download')}
                        class={`px-3 py-2 rounded-xl transition-colors text-sm font-black ${
                          exportBusy() ? 'bg-primary/60 text-white cursor-not-allowed' : 'bg-primary text-white hover:brightness-110'
                        }`}
                      >
                        {exportBusy() ? 'Exporting…' : 'Export'}
                      </button>
                    </div>
                  </div>
                  <div class="mt-4 flex-1 min-h-0 rounded-2xl border border-border overflow-hidden">
                    <div class="w-full h-full overflow-auto px-5 pb-5 pt-3" style={exportPreviewStyle()}>
                      <Show when={exportFormat() === 'mmd'} fallback={<div class="w-full flex justify-center items-start" innerHTML={exportPreviewSvg()} />}>
                        <pre class="text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-2xl p-4 overflow-auto whitespace-pre-wrap">{normalizedCode()}</pre>
                      </Show>
                    </div>
                  </div>
                </div>
              </div>

              <div class="h-16 px-6 border-t border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
                <div class="text-[11px] text-text-secondary/60 font-mono truncate">mermaid</div>
                <div class="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsExportOpen(false)}
                    class="px-4 py-2 rounded-xl border border-border bg-surface hover:bg-surface-elevated/70 transition-colors text-sm font-bold text-text-primary"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={exportBusy()}
                    onClick={() => exportFromContainer('download')}
                    class={`px-4 py-2 rounded-xl transition-colors text-sm font-black ${
                      exportBusy() ? 'bg-primary/60 text-white cursor-not-allowed' : 'bg-primary text-white hover:brightness-110'
                    }`}
                  >
                    {exportBusy() ? 'Exporting…' : 'Export'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Show>
    </>
  );
}
