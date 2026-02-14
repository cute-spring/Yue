import mermaid from 'mermaid';
import hljs from 'highlight.js';
import { getMermaidInitConfig, getMermaidThemePreset } from './mermaidTheme';
import { normalizeMermaidCode, getMermaidThemeOptionsHtml } from './markdown';
import { 
  buildExportSvgString, 
  getMermaidExportTimestamp, 
  sanitizeFilenameBase, 
  downloadBlob, 
  svgStringToPngBlob,
  copyTextToClipboard,
  copyPngBlobToClipboard,
  getMermaidExportPrefs,
  setMermaidExportPrefs,
  canCopyPng
} from './mermaidExport';
import { MermaidThemePreset, setMermaidThemePreset } from './mermaidTheme';
import { getCachedMermaidSvg, setCachedMermaidSvg } from './mermaidCache';

/**
 * Renders a Mermaid chart into a container element.
 * Checks for completion state (data-complete) to avoid rendering partial diagrams during streaming.
 */
export const renderMermaidChart = async (container: Element) => {
  if (container.getAttribute('data-processed') === 'true') return;
  
  const widget = container.closest('.mermaid-widget');
  const isComplete = widget?.getAttribute('data-complete') === 'true';
  
  // If the block is not complete (streaming), don't render yet
  if (!isComplete) return;

  const code = normalizeMermaidCode(decodeURIComponent(container.getAttribute('data-code') || ''));
  if (!code) return;

  try {
    const preset = getMermaidThemePreset();
    
    // Check cache first to avoid redundant rendering
    const cached = getCachedMermaidSvg(code, preset);
    if (cached) {
      container.innerHTML = cached;
      container.setAttribute('data-processed', 'true');
      return;
    }

    (mermaid as any).initialize(getMermaidInitConfig(preset));
    const id = `mermaid-${Math.random().toString(36).slice(2, 11)}`;
    
    // Silent error handling: check if code is valid before rendering
    try {
      await mermaid.parse(code);
    } catch (parseErr) {
      // If parsing fails even when "complete", it's a real syntax error.
      throw parseErr;
    }

    const { svg } = await mermaid.render(id, code);
    
    // Cache the result
    setCachedMermaidSvg(code, preset, svg);

    container.classList.add('opacity-0', 'transition-opacity', 'duration-500');
    container.innerHTML = svg;
    requestAnimationFrame(() => {
      container.classList.remove('opacity-0');
      container.classList.add('opacity-100');
    });
    container.setAttribute('data-processed', 'true');
  } catch (err) {
    console.warn('Mermaid render error (silent):', err);
    container.innerHTML = `
      <div class="text-amber-600 text-xs p-3 border border-amber-200 rounded-xl bg-amber-50/50 font-mono">
        <div class="flex items-center gap-2 mb-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <span class="font-bold">Mermaid Diagram Note</span>
        </div>
        <div class="opacity-80">${err instanceof Error ? err.message.split('\n')[0] : 'Syntax error in diagram'}</div>
        <button type="button" data-mermaid-action="tab-code" class="mt-2 text-amber-700 hover:underline font-bold uppercase tracking-wider text-[9px]">View Code</button>
      </div>
    `;
    container.setAttribute('data-processed', 'true');
  }
};

/**
 * Gets the SVG element from a Mermaid widget.
 */
export const getWidgetMermaidSvg = (widget: HTMLElement) => 
  widget.querySelector('.mermaid-chart svg') as SVGSVGElement | null;

/**
 * Exports a Mermaid diagram from a widget with specified options.
 */
export const exportMermaidFromWidget = async (
  widget: HTMLElement,
  opts: { 
    format: 'png' | 'svg' | 'mmd'; 
    background: 'transparent' | 'light' | 'dark' | 'custom'; 
    backgroundColor: string; 
    scale: number; 
    padding: number; 
    filename: string 
  },
) => {
  const encoded = widget.getAttribute('data-code') || '';
  const raw = decodeURIComponent(encoded);
  const normalized = normalizeMermaidCode(raw);
  const ts = getMermaidExportTimestamp();
  const base = sanitizeFilenameBase(opts.filename);

  if (opts.format === 'mmd') {
    const blob = new Blob([normalized], { type: 'text/plain;charset=utf-8' });
    downloadBlob(blob, `${base}-${ts}.mmd`);
    return;
  }

  const chart = widget.querySelector('.mermaid-chart');
  const existingSvg = getWidgetMermaidSvg(widget);
  if (!existingSvg && chart) {
    chart.setAttribute('data-processed', 'false');
    await renderMermaidChart(chart);
  }

  const svgEl = getWidgetMermaidSvg(widget);
  if (!svgEl) return;

  const svgString = buildExportSvgString(svgEl, { 
    padding: opts.padding, 
    background: opts.background, 
    backgroundColor: opts.backgroundColor 
  });

  if (opts.format === 'svg') {
    downloadBlob(new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' }), `${base}-${ts}.svg`);
    return;
  }

  const pngBlob = await svgStringToPngBlob(svgString, opts.scale);
  if (pngBlob) downloadBlob(pngBlob, `${base}-${ts}.png`);
};

/**
 * Copies a Mermaid diagram from a widget to the clipboard.
 */
export const copyMermaidFromWidget = async (
  widget: HTMLElement,
  opts: { 
    format: 'png' | 'svg' | 'mmd'; 
    background: 'transparent' | 'light' | 'dark' | 'custom'; 
    backgroundColor: string; 
    scale: number; 
    padding: number 
  },
) => {
  const encoded = widget.getAttribute('data-code') || '';
  const raw = decodeURIComponent(encoded);
  const normalized = normalizeMermaidCode(raw);

  if (opts.format === 'mmd') {
    await copyTextToClipboard(normalized);
    return;
  }

  const chart = widget.querySelector('.mermaid-chart');
  const existingSvg = getWidgetMermaidSvg(widget);
  if (!existingSvg && chart) {
    chart.setAttribute('data-processed', 'false');
    await renderMermaidChart(chart);
  }
  const svgEl = getWidgetMermaidSvg(widget);
  if (!svgEl) return;

  const svgString = buildExportSvgString(svgEl, { 
    padding: opts.padding, 
    background: opts.background, 
    backgroundColor: opts.backgroundColor 
  });

  if (opts.format === 'svg') {
    await copyTextToClipboard(svgString);
    return;
  }
  const pngBlob = await svgStringToPngBlob(svgString, opts.scale);
  if (!pngBlob) return;
  await copyPngBlobToClipboard(pngBlob);
};

let mermaidOverlayEl: HTMLElement | null = null;
let mermaidExportEl: HTMLElement | null = null;
let activePan: { widget: HTMLElement; startX: number; startY: number; startTx: number; startTy: number } | null = null;

export const getMermaidExportEl = () => mermaidExportEl;
export const getMermaidOverlayEl = () => mermaidOverlayEl;

export const closeMermaidOverlay = () => {
  if (mermaidOverlayEl) {
    mermaidOverlayEl.remove();
    mermaidOverlayEl = null;
    document.body.style.overflow = mermaidExportEl ? 'hidden' : 'auto';
  }
};

export const closeMermaidExportModal = () => {
  const nodes = Array.from(document.querySelectorAll<HTMLElement>('#mermaid-export-modal'));
  nodes.forEach((n) => n.remove());
  mermaidExportEl = null;
  document.body.style.overflow = mermaidOverlayEl ? 'hidden' : 'auto';
};

export const openMermaidExportModal = async (widget: HTMLElement, showToast: (type: 'success' | 'error' | 'info', message: string) => void) => {
  closeMermaidExportModal();
  document.body.style.overflow = 'hidden';

  const encoded = widget.getAttribute('data-code') || '';
  const raw = decodeURIComponent(encoded);
  const normalized = normalizeMermaidCode(raw);

  const prefs = getMermaidExportPrefs();
  const format: 'png' | 'svg' | 'mmd' = prefs.format;
  const background: 'transparent' | 'light' | 'dark' | 'custom' = prefs.background;
  const backgroundColor = prefs.backgroundColor;
  const scale = prefs.scale;
  const padding = prefs.padding;
  const filename = prefs.filename;

  const modal = document.createElement('div');
  modal.id = 'mermaid-export-modal';
  modal.className = 'fixed inset-0 z-[1300]';
  modal.dataset.format = format;
  modal.dataset.background = background;
  modal.dataset.backgroundColor = backgroundColor;
  modal.dataset.scale = String(scale);
  modal.dataset.padding = String(padding);
  modal.dataset.filename = filename;
  modal.dataset.busy = '0';

  const previewChecker = 'background-image: linear-gradient(45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(-45deg, rgba(148,163,184,.18) 25%, transparent 25%), linear-gradient(45deg, transparent 75%, rgba(148,163,184,.18) 75%), linear-gradient(-45deg, transparent 75%, rgba(148,163,184,.18) 75%); background-size: 18px 18px; background-position: 0 0, 0 9px, 9px -9px, -9px 0px;';

  modal.innerHTML = `
    <div class="absolute inset-0 bg-slate-900/25 backdrop-blur-md" data-mermaid-export-close="1"></div>
    <div class="absolute inset-0 flex items-start justify-center px-3 pb-3 pt-3 sm:px-6 sm:pb-6 sm:pt-6">
      <div class="w-[min(1120px,98vw)] h-[min(740px,94vh)] bg-surface border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col" role="dialog" aria-modal="true" aria-labelledby="mermaid-export-title" aria-describedby="mermaid-export-desc" tabindex="-1" data-mermaid-export-dialog="1">
        <div class="h-16 px-6 border-b border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M3 3a1 1 0 011-1h4a1 1 0 010 2H5v12h10V4h-3a1 1 0 110-2h4a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3z" />
                <path d="M9 9a1 1 0 011-1h0a1 1 0 011 1v4.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 111.414-1.414L9 13.586V9z" />
              </svg>
            </div>
            <div>
              <div id="mermaid-export-title" class="text-sm font-extrabold text-text-primary">Export diagram</div>
              <div id="mermaid-export-desc" class="text-xs text-text-secondary/70">PNG / SVG / MMD • Background • Advanced</div>
            </div>
          </div>
          <button type="button" class="p-2 rounded-xl hover:bg-surface-elevated text-text-secondary/70 hover:text-text-primary transition-colors" data-mermaid-export-close="1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <div class="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-5">
          <div class="md:col-span-2 p-5 border-b md:border-b-0 md:border-r border-border overflow-auto">
            <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Export format</div>
            <div class="mt-3 grid grid-cols-3 gap-2">
              <button type="button" data-mermaid-export-format="png" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface-elevated/40 hover:bg-surface-elevated transition-colors text-left">
                <div class="text-sm font-extrabold text-text-primary">PNG</div>
                <div class="text-[11px] text-text-secondary/70 mt-0.5">Raster image</div>
              </button>
              <button type="button" data-mermaid-export-format="svg" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                <div class="text-sm font-extrabold text-text-primary">SVG</div>
                <div class="text-[11px] text-text-secondary/70 mt-0.5">Vector</div>
              </button>
              <button type="button" data-mermaid-export-format="mmd" class="mermaid-export-format px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                <div class="text-sm font-extrabold text-text-primary">MMD</div>
                <div class="text-[11px] text-text-secondary/70 mt-0.5">Mermaid source</div>
              </button>
            </div>

            <div data-mermaid-export-section="background">
              <div class="mt-6 text-xs font-black uppercase tracking-wider text-text-secondary/60">Background</div>
              <div class="mt-3 grid grid-cols-2 gap-2">
                <button type="button" data-mermaid-export-bg="transparent" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface-elevated/40 hover:bg-surface-elevated transition-colors text-left">
                  <div class="text-sm font-extrabold text-text-primary">Transparent</div>
                  <div class="text-[11px] text-text-secondary/70 mt-0.5">Checker preview</div>
                </button>
                <button type="button" data-mermaid-export-bg="light" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                  <div class="text-sm font-extrabold text-text-primary">Light</div>
                  <div class="text-[11px] text-text-secondary/70 mt-0.5">White</div>
                </button>
                <button type="button" data-mermaid-export-bg="dark" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                  <div class="text-sm font-extrabold text-text-primary">Dark</div>
                  <div class="text-[11px] text-text-secondary/70 mt-0.5">Deep navy</div>
                </button>
                <button type="button" data-mermaid-export-bg="custom" class="mermaid-export-bg px-3 py-3 rounded-xl border border-border bg-surface hover:bg-surface-elevated/60 transition-colors text-left">
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="text-sm font-extrabold text-text-primary">Custom</div>
                      <div class="text-[11px] text-text-secondary/70 mt-0.5">Pick a color</div>
                    </div>
                    <input data-mermaid-export-bgcolor="1" type="color" value="${backgroundColor}" class="w-9 h-9 rounded-xl border border-border bg-transparent p-1 cursor-pointer" />
                  </div>
                </button>
              </div>
            </div>

            <details class="mt-6 group">
              <summary class="cursor-pointer select-none text-xs font-black uppercase tracking-wider text-text-secondary/60 flex items-center justify-between">
                <span>Advanced</span>
                <span class="text-[11px] text-text-secondary/40 group-open:hidden">Show</span>
                <span class="text-[11px] text-text-secondary/40 hidden group-open:inline">Hide</span>
              </summary>
              <div class="mt-3 space-y-4">
                <div data-mermaid-export-only="png">
                  <div class="flex items-center justify-between">
                    <div class="text-sm font-bold text-text-primary">PNG scale</div>
                    <div class="text-xs font-mono text-text-secondary/70"><span data-mermaid-export-scale-label="1">${scale}x</span></div>
                  </div>
                  <input data-mermaid-export-scale="1" type="range" min="1" max="4" step="1" value="${scale}" class="w-full mt-2" />
                  <div class="mt-1 text-[11px] text-text-secondary/60">Only affects PNG export.</div>
                </div>
                <div data-mermaid-export-only="svgpng">
                  <div class="flex items-center justify-between">
                    <div class="text-sm font-bold text-text-primary">Padding</div>
                    <div class="text-xs font-mono text-text-secondary/70"><span data-mermaid-export-padding-label="1">${padding}px</span></div>
                  </div>
                  <input data-mermaid-export-padding="1" type="range" min="0" max="96" step="4" value="${padding}" class="w-full mt-2" />
                  <div class="mt-1 text-[11px] text-text-secondary/60">Adds margin around the diagram.</div>
                </div>
                <div>
                  <div class="text-sm font-bold text-text-primary">File name</div>
                  <input data-mermaid-export-filename="1" type="text" value="${filename}" class="mt-2 w-full px-3 py-2 rounded-xl border border-border bg-surface text-sm font-semibold text-text-primary placeholder:text-text-secondary/40 focus:outline-none focus:ring-2 focus:ring-primary/20" placeholder="diagram" />
                  <div class="mt-1 text-[11px] text-text-secondary/60">Extension is added automatically.</div>
                </div>
              </div>
            </details>
          </div>

          <div class="md:col-span-3 p-5 min-h-0 flex flex-col">
            <div class="flex items-center justify-between">
              <div class="text-xs font-black uppercase tracking-wider text-text-secondary/60">Preview</div>
              <div class="flex items-center gap-2">
                <button type="button" data-mermaid-export-copy="1" class="px-3 py-2 rounded-xl border border-border bg-surface hover:bg-surface-elevated/70 transition-colors text-sm font-bold text-text-primary">Copy</button>
                <button type="button" data-mermaid-export-download="1" class="px-3 py-2 rounded-xl bg-primary text-white hover:brightness-110 transition-colors text-sm font-black">Export</button>
              </div>
            </div>
            <div class="mt-4 flex-1 min-h-0 rounded-2xl border border-border overflow-hidden">
              <div data-mermaid-export-preview="1" class="w-full h-full overflow-auto px-5 pb-5 pt-3" style="${previewChecker}"></div>
            </div>
          </div>
        </div>

        <div class="h-16 px-6 border-t border-border flex items-center justify-between bg-surface/80 backdrop-blur-md">
          <div class="text-[11px] text-text-secondary/60 font-mono truncate">mermaid</div>
          <div class="flex items-center gap-2">
            <button type="button" data-mermaid-export-close="1" class="px-4 py-2 rounded-xl border border-border bg-surface hover:bg-surface-elevated/70 transition-colors text-sm font-bold text-text-primary">Cancel</button>
            <button type="button" data-mermaid-export-download="1" class="px-4 py-2 rounded-xl bg-primary text-white hover:brightness-110 transition-colors text-sm font-black">Export</button>
          </div>
        </div>
      </div>
    </div>
  `;

  const updateButtons = () => {
    const fmt = (modal.dataset.format || 'png') as any;
    const busy = modal.dataset.busy === '1';
    modal.querySelectorAll('.mermaid-export-format').forEach((el) => {
      const btn = el as HTMLButtonElement;
      const id = btn.getAttribute('data-mermaid-export-format');
      const active = id === fmt;
      btn.className = `mermaid-export-format px-3 py-3 rounded-xl border transition-colors text-left ${active ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`;
      btn.disabled = busy;
    });
    const bg = modal.dataset.background || 'transparent';
    modal.querySelectorAll('.mermaid-export-bg').forEach((el) => {
      const btn = el as HTMLButtonElement;
      const id = btn.getAttribute('data-mermaid-export-bg');
      const active = id === bg;
      btn.className = `mermaid-export-bg px-3 py-3 rounded-xl border transition-colors text-left ${active ? 'border-primary/40 bg-primary/10' : 'border-border bg-surface hover:bg-surface-elevated/60'}`;
      btn.disabled = busy;
    });

    modal.querySelectorAll('[data-mermaid-export-section="background"]').forEach((el) => {
      (el as HTMLElement).classList.toggle('hidden', fmt === 'mmd');
    });
    modal.querySelectorAll('[data-mermaid-export-only="png"]').forEach((el) => {
      (el as HTMLElement).classList.toggle('hidden', fmt !== 'png');
    });
    modal.querySelectorAll('[data-mermaid-export-only="svgpng"]').forEach((el) => {
      (el as HTMLElement).classList.toggle('hidden', fmt === 'mmd');
    });

    const filenameInput = modal.querySelector('[data-mermaid-export-filename="1"]') as HTMLInputElement | null;
    if (filenameInput) filenameInput.disabled = busy;
    const scaleInput = modal.querySelector('[data-mermaid-export-scale="1"]') as HTMLInputElement | null;
    if (scaleInput) scaleInput.disabled = busy;
    const paddingInput = modal.querySelector('[data-mermaid-export-padding="1"]') as HTMLInputElement | null;
    if (paddingInput) paddingInput.disabled = busy;
    const colorInput = modal.querySelector('[data-mermaid-export-bgcolor="1"]') as HTMLInputElement | null;
    if (colorInput) colorInput.disabled = busy;

    const copyBtn = modal.querySelector('[data-mermaid-export-copy="1"]') as HTMLButtonElement | null;
    if (copyBtn) {
      const isPng = fmt === 'png';
      copyBtn.disabled = busy || (isPng && !canCopyPng());
      copyBtn.className = `px-3 py-2 rounded-xl border border-border transition-colors text-sm font-bold ${copyBtn.disabled ? 'bg-surface text-text-secondary/40 cursor-not-allowed' : 'bg-surface hover:bg-surface-elevated/70 text-text-primary'}`;
      copyBtn.textContent = fmt === 'mmd' ? 'Copy MMD' : fmt === 'svg' ? 'Copy SVG' : 'Copy PNG';
      copyBtn.title = copyBtn.disabled && isPng && !canCopyPng() ? 'Your browser does not support copying PNG to clipboard.' : '';
    }

    modal.querySelectorAll('[data-mermaid-export-download="1"]').forEach((el) => {
      const btn = el as HTMLButtonElement;
      btn.disabled = busy;
      btn.textContent = busy ? 'Exporting…' : 'Export';
    });
  };

  const renderPreview = async () => {
    const preview = modal.querySelector('[data-mermaid-export-preview="1"]') as HTMLElement | null;
    if (!preview) return;
    const fmt = (modal.dataset.format || 'png') as 'png' | 'svg' | 'mmd';
    const bg = (modal.dataset.background || 'transparent') as 'transparent' | 'light' | 'dark' | 'custom';
    const bgColor = modal.dataset.backgroundColor || '#ffffff';
    const pad = parseInt(modal.dataset.padding || '0', 10) || 0;

    preview.innerHTML = '';
    const setPreviewBackground = () => {
      if (bg === 'transparent') {
        preview.setAttribute('style', previewChecker);
        return;
      }
      const fill = bg === 'custom' ? bgColor : bg === 'dark' ? '#0b1220' : '#ffffff';
      preview.setAttribute('style', `background: ${fill};`);
    };
    setPreviewBackground();

    if (fmt === 'mmd') {
      const pre = document.createElement('pre');
      pre.className = 'text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-2xl p-4 overflow-auto whitespace-pre-wrap';
      pre.textContent = normalized;
      preview.appendChild(pre);
      return;
    }

    const chart = widget.querySelector('.mermaid-chart');
    const existingSvg = getWidgetMermaidSvg(widget);
    if (!existingSvg && chart) {
      chart.setAttribute('data-processed', 'false');
      await renderMermaidChart(chart);
    }
    const svgEl = getWidgetMermaidSvg(widget);
    if (!svgEl) return;
    const svgString = buildExportSvgString(svgEl, { padding: pad, background: bg, backgroundColor: bgColor });
    const holder = document.createElement('div');
    holder.className = 'w-full flex justify-center items-start';
    holder.innerHTML = svgString;
    preview.appendChild(holder);
    preview.scrollTop = 0;
  };

  const setBusy = (next: boolean) => {
    modal.dataset.busy = next ? '1' : '0';
    updateButtons();
  };

  const getCurrentOpts = () => {
    return {
      format: (modal.dataset.format || 'png') as 'png' | 'svg' | 'mmd',
      background: (modal.dataset.background || 'transparent') as 'transparent' | 'light' | 'dark' | 'custom',
      backgroundColor: modal.dataset.backgroundColor || '#ffffff',
      scale: parseInt(modal.dataset.scale || '2', 10) || 2,
      padding: parseInt(modal.dataset.padding || '0', 10) || 0,
      filename: modal.dataset.filename || 'diagram',
    };
  };

  const onClick = async (e: MouseEvent) => {
    const t = e.target as HTMLElement | null;
    if (!t) return;
    const closeBtn = t.closest('[data-mermaid-export-close="1"]') as HTMLElement | null;
    if (closeBtn) {
      e.preventDefault();
      e.stopPropagation();
      closeMermaidExportModal();
      return;
    }

    const formatBtn = t.closest('[data-mermaid-export-format]') as HTMLElement | null;
    if (formatBtn) {
      e.preventDefault();
      e.stopPropagation();
      const nextFmt = (formatBtn.getAttribute('data-mermaid-export-format') || 'png') as any;
      modal.dataset.format = nextFmt;
      setMermaidExportPrefs({ format: nextFmt });
      updateButtons();
      await renderPreview();
      return;
    }

    const bgBtn = t.closest('[data-mermaid-export-bg]') as HTMLElement | null;
    if (bgBtn) {
      e.preventDefault();
      e.stopPropagation();
      const nextBg = (bgBtn.getAttribute('data-mermaid-export-bg') || 'transparent') as any;
      modal.dataset.background = nextBg;
      setMermaidExportPrefs({ background: nextBg });
      updateButtons();
      await renderPreview();
      return;
    }

    const copyBtn = t.closest('[data-mermaid-export-copy="1"]') as HTMLElement | null;
    if (copyBtn) {
      e.preventDefault();
      e.stopPropagation();
      if (modal.dataset.busy === '1') return;
      setBusy(true);
      try {
        const opts = getCurrentOpts();
        await copyMermaidFromWidget(widget, opts);
        showToast('success', opts.format === 'mmd' ? 'Copied MMD' : opts.format === 'svg' ? 'Copied SVG' : 'Copied PNG');
      } catch (err) {
        showToast('error', 'Copy failed');
      } finally {
        setBusy(false);
      }
      return;
    }

    const dlBtn = t.closest('[data-mermaid-export-download="1"]') as HTMLElement | null;
    if (dlBtn) {
      e.preventDefault();
      e.stopPropagation();
      if (modal.dataset.busy === '1') return;
      setBusy(true);
      try {
        const opts = getCurrentOpts();
        await exportMermaidFromWidget(widget, opts);
        showToast('success', opts.format === 'mmd' ? 'Exported MMD' : opts.format === 'svg' ? 'Exported SVG' : 'Exported PNG');
      } catch (err) {
        showToast('error', 'Export failed');
      } finally {
        setBusy(false);
      }
      return;
    }
  };

  const onInput = async (e: Event) => {
    const t = e.target as HTMLElement | null;
    if (!t) return;
    if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-bgcolor') === '1') {
      modal.dataset.backgroundColor = t.value || '#ffffff';
      modal.dataset.background = 'custom';
      setMermaidExportPrefs({ backgroundColor: modal.dataset.backgroundColor, background: 'custom' });
      updateButtons();
      await renderPreview();
      return;
    }
    if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-scale') === '1') {
      modal.dataset.scale = t.value;
      const label = modal.querySelector('[data-mermaid-export-scale-label="1"]') as HTMLElement | null;
      if (label) label.textContent = `${t.value}x`;
      setMermaidExportPrefs({ scale: parseInt(t.value, 10) || 2 });
      return;
    }
    if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-padding') === '1') {
      modal.dataset.padding = t.value;
      const label = modal.querySelector('[data-mermaid-export-padding-label="1"]') as HTMLElement | null;
      if (label) label.textContent = `${t.value}px`;
      setMermaidExportPrefs({ padding: parseInt(t.value, 10) || 0 });
      await renderPreview();
      return;
    }
    if (t instanceof HTMLInputElement && t.getAttribute('data-mermaid-export-filename') === '1') {
      modal.dataset.filename = t.value || '';
      setMermaidExportPrefs({ filename: modal.dataset.filename });
      return;
    }
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      closeMermaidExportModal();
      return;
    }
    if (e.key === 'Enter' && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
      const active = document.activeElement as HTMLElement | null;
      if (active && active.tagName === 'TEXTAREA') return;
      const btn = modal.querySelector('[data-mermaid-export-download="1"]') as HTMLButtonElement | null;
      if (btn && !btn.disabled) {
        e.preventDefault();
        btn.click();
      }
      return;
    }
    if (e.key !== 'Tab') return;
    const dialog = modal.querySelector('[data-mermaid-export-dialog="1"]') as HTMLElement | null;
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

  document.body.appendChild(modal);
  mermaidExportEl = modal;
  updateButtons();
  await renderPreview();
  modal.addEventListener('click', onClick);
  modal.addEventListener('input', onInput);
  modal.addEventListener('keydown', onKeyDown);
  const primary = modal.querySelector('[data-mermaid-export-download="1"]') as HTMLButtonElement | null;
  const dialog = modal.querySelector('[data-mermaid-export-dialog="1"]') as HTMLElement | null;
  (primary || dialog)?.focus?.();
};

export const openMermaidOverlay = async (encoded: string) => {
  closeMermaidOverlay();
  document.body.style.overflow = 'hidden';
  const preset = getMermaidThemePreset();

  const overlay = document.createElement('div');
  overlay.id = 'mermaid-overlay';
  overlay.className = 'fixed inset-0 z-[1200]';
  overlay.innerHTML = `
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" data-mermaid-overlay-close="1"></div>
    <div class="absolute inset-0 p-2 sm:p-4 md:p-6 flex items-center justify-center">
      <div class="w-[98vw] h-[94vh] max-w-none bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col">
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <div class="text-sm font-bold text-gray-800">Mermaid</div>
          <button type="button" class="p-2 rounded-lg hover:bg-gray-50 text-gray-500 hover:text-gray-800" data-mermaid-overlay-close="1">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
        <div class="p-3 sm:p-4 flex-1 min-h-0">
          <div class="mermaid-widget my-0" data-code="${encoded}" data-complete="true" data-scale="1" data-tx="0" data-ty="0" data-tab="diagram">
            <div class="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-xl shadow-sm">
              <div class="flex items-center gap-2">
                <button type="button" data-mermaid-action="tab-diagram" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors bg-gray-100 text-gray-900">Diagram</button>
                <button type="button" data-mermaid-action="tab-code" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors text-gray-500 hover:text-gray-800 hover:bg-gray-50">Code</button>
              </div>
              <div class="flex items-center gap-1.5 text-gray-500">
                <button type="button" data-mermaid-action="zoom-out" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom out">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    <line x1="8" y1="11" x2="14" y2="11" />
                  </svg>
                </button>
                <button type="button" data-mermaid-action="zoom-in" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom in">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    <line x1="11" y1="8" x2="11" y2="14" />
                    <line x1="8" y1="11" x2="14" y2="11" />
                  </svg>
                </button>
                <div class="w-px h-5 bg-gray-200 mx-1"></div>
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-gray-500">Theme</span>
                  <select data-mermaid-theme-select="1" class="text-sm font-semibold text-gray-800 bg-white border border-gray-200 rounded-lg px-2 py-1.5 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20">
                    ${getMermaidThemeOptionsHtml(preset)}
                  </select>
                </div>
                <button type="button" data-mermaid-action="fit" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fit">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M8 3H3v5" />
                    <path d="M16 3h5v5" />
                    <path d="M21 16v5h-5" />
                    <path d="M3 16v5h5" />
                  </svg>
                  <span class="text-sm font-semibold">Fit</span>
                </button>
                <button type="button" data-mermaid-action="download" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Export">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                  <span class="text-sm font-semibold">Export</span>
                </button>
                <button type="button" data-mermaid-action="reset" class="px-2 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Reset zoom">
                  <span class="mermaid-widget-zoom-label text-sm font-semibold">100%</span>
                </button>
              </div>
            </div>
            <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden">
              <div class="mermaid-widget-diagram-panel">
                <div class="mermaid-widget-viewport w-full h-[calc(94vh-220px)] overflow-auto">
                  <div class="mermaid-widget-zoom-area min-h-[360px] flex justify-center items-center p-4 sm:p-6 transition-all duration-300" style="transform: translate(0px, 0px) scale(1); transform-origin: top center;">
                    <div class="mermaid-chart w-full flex justify-center" data-code="${encoded}">
                      <div class="flex flex-col items-center justify-center">
                        <div class="loading-spinner w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mermaid-widget-code-panel hidden p-4">
                <pre class="mermaid-widget-code-pre text-xs leading-relaxed font-mono bg-[#0d1117] text-[#c9d1d9] border border-white/10 rounded-xl p-4 overflow-auto whitespace-pre-wrap"><code class="hljs language-plaintext mermaid-widget-code-code"></code></pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  mermaidOverlayEl = overlay;

  requestAnimationFrame(async () => {
    const chartEl = overlay.querySelector('.mermaid-chart');
    if (chartEl) {
      chartEl.setAttribute('data-processed', 'false');
      await renderMermaidChart(chartEl);
    }
  });
};

export const applyWidgetTransform = (widget: HTMLElement, nextScale: number, nextTx: number, nextTy: number) => {
  const clamped = Math.min(4, Math.max(0.25, nextScale));
  widget.setAttribute('data-scale', String(clamped));
  widget.setAttribute('data-tx', String(nextTx));
  widget.setAttribute('data-ty', String(nextTy));
  const zoomArea = widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
  if (zoomArea) {
    zoomArea.style.transform = `translate(${nextTx}px, ${nextTy}px) scale(${clamped})`;
    zoomArea.style.transformOrigin = 'top center';
    if (!zoomArea.style.cursor) zoomArea.style.cursor = 'grab';
  }
  const label = widget.querySelector('.mermaid-widget-zoom-label') as HTMLElement | null;
  if (label) label.textContent = `${Math.round(clamped * 100)}%`;
};

export const getWidgetScale = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-scale') || '1') || 1;
export const getWidgetTx = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-tx') || '0') || 0;
export const getWidgetTy = (widget: HTMLElement) => parseFloat(widget.getAttribute('data-ty') || '0') || 0;

export const applyWidgetScale = (widget: HTMLElement, nextScale: number) => {
  applyWidgetTransform(widget, nextScale, getWidgetTx(widget), getWidgetTy(widget));
};

export const fitWidget = (widget: HTMLElement) => {
  const viewport = widget.querySelector('.mermaid-widget-viewport') as HTMLElement | null;
  const svg = widget.querySelector('svg') as SVGSVGElement | null;
  if (!viewport || !svg) return;
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
    const current = getWidgetScale(widget);
    const rect = svg.getBoundingClientRect();
    baseW = rect.width / current;
    baseH = rect.height / current;
  }
  if (!baseW || !baseH) return;

  const padding = 56;
  const rawScale = Math.min((availW - padding) / baseW, (availH - padding) / baseH);
  const nextScale = Math.min(rawScale * 0.95, 1.2);
  if (!Number.isFinite(nextScale) || nextScale <= 0) return;
  applyWidgetTransform(widget, nextScale, 0, 0);
  try {
    viewport.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  } catch (e) {
    viewport.scrollTop = 0;
    viewport.scrollLeft = 0;
  }
};

export const setWidgetTab = (widget: HTMLElement, next: 'diagram' | 'code') => {
  widget.setAttribute('data-tab', next);
  const diagramBtn = widget.querySelector('[data-mermaid-action="tab-diagram"]') as HTMLElement | null;
  const codeBtn = widget.querySelector('[data-mermaid-action="tab-code"]') as HTMLElement | null;
  if (diagramBtn) diagramBtn.className = `px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${next === 'diagram' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`;
  if (codeBtn) codeBtn.className = `px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${next === 'code' ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`;
  const diagramPanel = widget.querySelector('.mermaid-widget-diagram-panel') as HTMLElement | null;
  const codePanel = widget.querySelector('.mermaid-widget-code-panel') as HTMLElement | null;
  if (diagramPanel) diagramPanel.classList.toggle('hidden', next !== 'diagram');
  if (codePanel) codePanel.classList.toggle('hidden', next !== 'code');
  if (next === 'code') {
    const codeEl = widget.querySelector('.mermaid-widget-code-code') as HTMLElement | null;
    if (codeEl && !codeEl.innerHTML) {
      const encoded = widget.getAttribute('data-code') || '';
      const raw = decodeURIComponent(encoded);
      const normalized = normalizeMermaidCode(raw);
      codeEl.innerHTML = hljs.highlight(normalized, { language: 'plaintext' }).value;
    }
  }
};

export const handleMermaidClick = (e: MouseEvent, showToast: (type: 'success' | 'error' | 'info', message: string) => void) => {
  const target = e.target as HTMLElement | null;
  if (!target) return;
  const overlayClose = target.closest('[data-mermaid-overlay-close="1"]') as HTMLElement | null;
  if (overlayClose) {
    e.preventDefault();
    e.stopPropagation();
    closeMermaidOverlay();
    return;
  }
  const btn = target.closest('[data-mermaid-action]') as HTMLElement | null;
  if (!btn) return;
  const widget = btn.closest('.mermaid-widget') as HTMLElement | null;
  if (!widget) return;
  const action = btn.getAttribute('data-mermaid-action') || '';

  if (action === 'tab-diagram' || action === 'tab-code' || action === 'zoom-in' || action === 'zoom-out' || action === 'reset' || action === 'fit' || action === 'download' || action === 'fullscreen') {
    e.preventDefault();
    e.stopPropagation();
  } else {
    return;
  }

  const currentScale = getWidgetScale(widget);
  if (action === 'tab-diagram') setWidgetTab(widget, 'diagram');
  if (action === 'tab-code') setWidgetTab(widget, 'code');
  if (action === 'zoom-in') applyWidgetScale(widget, currentScale * 1.2);
  if (action === 'zoom-out') applyWidgetScale(widget, currentScale / 1.2);
  if (action === 'reset') applyWidgetScale(widget, 1);
  if (action === 'fit') fitWidget(widget);
  if (action === 'fullscreen') {
    const encoded = widget.getAttribute('data-code') || '';
    openMermaidOverlay(encoded);
  }
  if (action === 'download') void openMermaidExportModal(widget, showToast);
};

export const handleMermaidWheel = (e: WheelEvent) => {
  if (!e.ctrlKey) return;
  const target = e.target as HTMLElement | null;
  if (!target) return;
  const widget = target.closest('.mermaid-widget') as HTMLElement | null;
  if (!widget) return;
  e.preventDefault();
  const currentScale = getWidgetScale(widget);
  const next = e.deltaY > 0 ? currentScale * 0.9 : currentScale * 1.1;
  applyWidgetTransform(widget, next, getWidgetTx(widget), getWidgetTy(widget));
};

export const handleMermaidPointerDown = (e: PointerEvent) => {
  const target = e.target as HTMLElement | null;
  if (!target) return;
  const viewport = target.closest('.mermaid-widget-viewport') as HTMLElement | null;
  if (!viewport) return;
  const widget = viewport.closest('.mermaid-widget') as HTMLElement | null;
  if (!widget) return;
  if ((widget.getAttribute('data-tab') || 'diagram') !== 'diagram') return;
  if (e.button !== 0) return;
  const zoomArea = widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
  if (zoomArea) zoomArea.style.cursor = 'grabbing';
  activePan = { widget, startX: e.clientX, startY: e.clientY, startTx: getWidgetTx(widget), startTy: getWidgetTy(widget) };
  e.preventDefault();
};

export const handleMermaidPointerMove = (e: PointerEvent) => {
  if (!activePan) return;
  e.preventDefault();
  const { widget, startX, startY, startTx, startTy } = activePan;
  const dx = e.clientX - startX;
  const dy = e.clientY - startY;
  applyWidgetTransform(widget, getWidgetScale(widget), startTx + dx, startTy + dy);
};

export const handleMermaidPointerUp = () => {
  if (!activePan) return;
  const zoomArea = activePan.widget.querySelector('.mermaid-widget-zoom-area') as HTMLElement | null;
  if (zoomArea) zoomArea.style.cursor = 'grab';
  activePan = null;
};

export const handleMermaidChange = (e: Event) => {
  const target = e.target as HTMLElement | null;
  if (!(target instanceof HTMLSelectElement)) return;
  if (target.getAttribute('data-mermaid-theme-select') !== '1') return;

  const next = target.value as MermaidThemePreset;
  setMermaidThemePreset(next);

  document.querySelectorAll('select[data-mermaid-theme-select="1"]').forEach((el) => {
    if (el instanceof HTMLSelectElement) el.value = next;
  });

  document.querySelectorAll('.mermaid-chart').forEach((container) => {
    container.setAttribute('data-processed', 'false');
    renderMermaidChart(container);
  });
};
