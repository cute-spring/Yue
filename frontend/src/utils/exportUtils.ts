import { toPng } from 'html-to-image';

export const downloadMarkdown = (content: string, filename: string = 'message.md') => {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

export const downloadMessageAsImage = async (
  elementId: string, 
  filename: string = 'message.png'
): Promise<boolean> => {
  try {
    const sourceNode = document.getElementById(elementId);
    if (!sourceNode) throw new Error('Message element not found');
    const sourceRect = sourceNode.getBoundingClientRect();
    const host = sourceNode.parentElement ?? document.body;

    const exportRoot = document.createElement('div');
    exportRoot.dataset.exportRoot = 'true';
    exportRoot.style.position = 'fixed';
    exportRoot.style.left = '0';
    exportRoot.style.top = '0';
    exportRoot.style.zIndex = '-9999';
    exportRoot.style.pointerEvents = 'none';
    exportRoot.style.width = `${Math.max(760, Math.ceil(sourceRect.width))}px`;
    exportRoot.style.padding = '40px';
    exportRoot.style.background = 'linear-gradient(180deg, #f8fbfa 0%, #f0f7f4 100%)';
    exportRoot.style.boxSizing = 'border-box';
    exportRoot.style.borderRadius = '24px';
    exportRoot.style.color = '#0f172a';
    exportRoot.style.overflow = 'hidden';

    const clone = sourceNode.cloneNode(true) as HTMLElement;
    clone.style.maxWidth = '100%';
    clone.style.width = '100%';
    clone.style.margin = '0';
    clone.style.borderRadius = '18px';
    clone.style.boxShadow = '0 16px 40px rgba(0, 0, 0, 0.08)';

    exportRoot.appendChild(clone);
    host.appendChild(exportRoot);

    // Wait for the DOM to update and any styles/fonts to be applied
    await new Promise(resolve => setTimeout(resolve, 100));

    let dataUrl = '';
    try {
      // Sometimes html-to-image needs a warm-up render to load assets
      await toPng(exportRoot, {
        quality: 1,
        pixelRatio: 2,
        backgroundColor: '#f8fbfa',
        filter: (node) => {
          if (!(node instanceof HTMLElement)) return true;
          return !node.classList.contains('export-exclude');
        }
      });
      
      dataUrl = await toPng(exportRoot, {
        quality: 1,
        pixelRatio: 2,
        backgroundColor: '#f8fbfa',
        filter: (node) => {
          if (!(node instanceof HTMLElement)) return true;
          return !node.classList.contains('export-exclude');
        }
      });

      if (!dataUrl || dataUrl === 'data:,') {
        throw new Error('html-to-image returned empty data URL');
      }
    } finally {
      if (exportRoot.parentNode) {
        exportRoot.parentNode.removeChild(exportRoot);
      }
    }

    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    return true;
  } catch (error) {
    console.error('Failed to export image:', error);
    const existing = document.querySelector('div[data-export-root="true"]');
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
    return false;
  }
};
