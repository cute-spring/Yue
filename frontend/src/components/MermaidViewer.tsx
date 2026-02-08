import { createEffect, createMemo, createSignal, onMount, Show } from 'solid-js';
import hljs from 'highlight.js';
import mermaid from 'mermaid';

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
  const baseId = `mermaid-viewer-${Math.random().toString(36).slice(2, 11)}`;

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

    const padding = 24;
    const nextScale = Math.min((availW - padding) / baseW, (availH - padding) / baseH);
    if (!Number.isFinite(nextScale) || nextScale <= 0) return;
    zoomTo(nextScale);
    setTx(0);
    setTy(0);
  };

  const downloadSvg = (containerId: string) => {
    const element = document.getElementById(containerId);
    const svg = element?.querySelector('svg');
    if (!svg) return;
    const data = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([data], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `diagram-${baseId}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        primaryColor: '#10B981',
        primaryTextColor: '#1f2937',
        primaryBorderColor: '#059669',
        lineColor: '#64748b',
        secondaryColor: '#ecfdf5',
        tertiaryColor: '#f0fdf4',
        fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
        fontSize: '14px',
      },
      flowchart: { curve: 'basis', htmlLabels: true, padding: 15, nodeSpacing: 50, rankSpacing: 80 },
      sequence: { actorMargin: 50, boxMargin: 10, boxTextMargin: 5, noteMargin: 10, messageMargin: 35, mirrorActors: false, bottomMarginAdj: 1 },
      securityLevel: 'loose',
    });
  });

  createEffect(() => {
    props.code;
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
        <button type="button" onClick={() => fitTo(containerId)} class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fit">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 3H3v5" />
            <path d="M16 3h5v5" />
            <path d="M21 16v5h-5" />
            <path d="M3 16v5h5" />
          </svg>
          <span class="text-sm font-semibold">Fit</span>
        </button>
        <button type="button" onClick={() => downloadSvg(containerId)} class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Download">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-semibold">Download</span>
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
                <div class="min-h-[240px] flex justify-center items-start p-6" style={{ transform: `translate(${tx()}px, ${ty()}px) scale(${scale()})`, 'transform-origin': 'top left', cursor: isPanning() ? 'grabbing' : 'grab' }}>
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
                      <div class="min-h-[360px] flex justify-center items-start p-8" style={{ transform: `translate(${tx()}px, ${ty()}px) scale(${scale()})`, 'transform-origin': 'top left', cursor: isPanning() ? 'grabbing' : 'grab' }}>
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
    </>
  );
}
