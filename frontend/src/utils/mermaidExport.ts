export type MermaidExportFormat = 'png' | 'svg' | 'mmd';
export type MermaidExportBackground = 'transparent' | 'light' | 'dark' | 'custom';

export const MERMAID_EXPORT_PREFS_STORAGE_KEY = 'mermaid_export_prefs';

export type MermaidExportPrefs = {
  format: MermaidExportFormat;
  background: MermaidExportBackground;
  backgroundColor: string;
  scale: number;
  padding: number;
  filename: string;
};

export const getMermaidExportTimestamp = () => new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');

export const sanitizeFilenameBase = (name: string) => {
  const trimmed = (name || '').trim();
  const safe = trimmed
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, ' ')
    .replace(/\.+$/g, '')
    .trim();
  return safe || 'diagram';
};

export const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

export const buildExportSvgString = (
  svg: SVGSVGElement,
  opts: { padding: number; background: MermaidExportBackground; backgroundColor: string },
) => {
  const padding = Math.max(0, opts.padding || 0);
  const tightBounds = (() => {
    const isOk = (b: DOMRect | null) =>
      Boolean(b && Number.isFinite(b.width) && Number.isFinite(b.height) && b.width > 0 && b.height > 0);
    try {
      if (typeof (svg as any).getBBox === 'function') {
        const b = svg.getBBox();
        if (isOk(b)) return b;
      }
    } catch (e) {}
    try {
      const host = document.createElement('div');
      host.style.position = 'fixed';
      host.style.left = '-10000px';
      host.style.top = '-10000px';
      host.style.width = '0';
      host.style.height = '0';
      host.style.overflow = 'hidden';
      host.style.visibility = 'hidden';
      document.body.appendChild(host);
      try {
        const clone = svg.cloneNode(true) as SVGSVGElement;
        host.appendChild(clone);
        if (typeof (clone as any).getBBox !== 'function') return null;
        const b = clone.getBBox();
        if (isOk(b)) return b;
        return null;
      } finally {
        host.remove();
      }
    } catch (e) {
      return null;
    }
  })();

  const source = svg.cloneNode(true) as SVGSVGElement;
  if (!source.getAttribute('xmlns')) source.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  if (!source.getAttribute('xmlns:xlink')) source.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink');

  const vb = (source as any).viewBox?.baseVal;
  const widthAttr = source.getAttribute('width') || '';
  const heightAttr = source.getAttribute('height') || '';
  const widthFromVb = vb?.width && vb.width > 0 ? vb.width : parseFloat(widthAttr.replace('px', ''));
  const heightFromVb = vb?.height && vb.height > 0 ? vb.height : parseFloat(heightAttr.replace('px', ''));
  const width = tightBounds ? tightBounds.width : widthFromVb || 0;
  const height = tightBounds ? tightBounds.height : heightFromVb || 0;
  const x = tightBounds?.x ?? (vb?.x ?? 0);
  const y = tightBounds?.y ?? (vb?.y ?? 0);
  const strokePad = tightBounds ? 2 : 0;

  const outW = width + (padding + strokePad) * 2;
  const outH = height + (padding + strokePad) * 2;
  const outX = x - padding - strokePad;
  const outY = y - padding - strokePad;

  source.setAttribute('viewBox', `${outX} ${outY} ${outW} ${outH}`);
  source.setAttribute('width', `${Math.max(1, Math.round(outW))}`);
  source.setAttribute('height', `${Math.max(1, Math.round(outH))}`);

  if (opts.background !== 'transparent') {
    const fill = opts.background === 'custom' ? opts.backgroundColor : opts.background === 'dark' ? '#0b1220' : '#ffffff';
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', String(outX));
    rect.setAttribute('y', String(outY));
    rect.setAttribute('width', String(outW));
    rect.setAttribute('height', String(outH));
    rect.setAttribute('fill', fill);
    source.insertBefore(rect, source.firstChild);
  }

  return new XMLSerializer().serializeToString(source);
};

export const svgStringToPngBlob = async (svgString: string, scale: number) => {
  const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  try {
    const img = new Image();
    img.decoding = 'async';
    const loaded = await new Promise<HTMLImageElement | null>((resolve) => {
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = url;
    });
    if (!loaded) return null;

    const s = Math.min(4, Math.max(1, Number.isFinite(scale) ? scale : 2));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round((loaded.naturalWidth || 1) * s));
    canvas.height = Math.max(1, Math.round((loaded.naturalHeight || 1) * s));
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.setTransform(s, 0, 0, s, 0, 0);
    ctx.drawImage(loaded, 0, 0);
    const pngBlob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
    return pngBlob;
  } finally {
    URL.revokeObjectURL(url);
  }
};

export const canCopyPng = () => Boolean((window as any).ClipboardItem);

export const copyTextToClipboard = async (text: string) => {
  await navigator.clipboard.writeText(text);
};

export const copyPngBlobToClipboard = async (pngBlob: Blob) => {
  const ClipboardItemCtor = (window as any).ClipboardItem as any;
  if (!ClipboardItemCtor) return false;
  await navigator.clipboard.write([new ClipboardItemCtor({ 'image/png': pngBlob })]);
  return true;
};

export const getMermaidExportPrefs = (): MermaidExportPrefs => {
  const defaults: MermaidExportPrefs = {
    format: 'png',
    background: 'transparent',
    backgroundColor: '#ffffff',
    scale: 2,
    padding: 32,
    filename: 'diagram',
  };
  try {
    const raw = localStorage.getItem(MERMAID_EXPORT_PREFS_STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw) as Partial<MermaidExportPrefs> | null;
    if (!parsed) return defaults;
    return {
      format: parsed.format || defaults.format,
      background: parsed.background || defaults.background,
      backgroundColor: parsed.backgroundColor || defaults.backgroundColor,
      scale: typeof parsed.scale === 'number' ? parsed.scale : defaults.scale,
      padding: typeof parsed.padding === 'number' ? parsed.padding : defaults.padding,
      filename: typeof parsed.filename === 'string' ? parsed.filename : defaults.filename,
    };
  } catch (e) {
    return defaults;
  }
};

export const setMermaidExportPrefs = (next: Partial<MermaidExportPrefs>) => {
  try {
    const current = getMermaidExportPrefs();
    const merged: MermaidExportPrefs = {
      ...current,
      ...next,
    };
    localStorage.setItem(MERMAID_EXPORT_PREFS_STORAGE_KEY, JSON.stringify(merged));
  } catch (e) {}
};
