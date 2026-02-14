import { onMount } from 'solid-js';
import mermaid from 'mermaid';
import { getMermaidInitConfig, getMermaidThemePreset } from '../utils/mermaidTheme';
import { 
  handleMermaidClick, 
  handleMermaidWheel, 
  handleMermaidChange, 
  handleMermaidPointerDown, 
  handleMermaidPointerMove, 
  handleMermaidPointerUp,
  closeMermaidExportModal,
  closeMermaidOverlay,
  renderMermaidChart
} from '../utils/mermaidRenderer';

export function useMermaid(showToast: (type: 'success' | 'error' | 'info', message: string) => void) {
  
  const debouncedRender = () => {
    let renderTimeout: any;
    if (renderTimeout) clearTimeout(renderTimeout);
    renderTimeout = setTimeout(() => {
      requestAnimationFrame(() => {
        const charts = document.querySelectorAll('.mermaid-chart:not([data-processed="true"])');
        charts.forEach(async (container) => {
          const widget = container.closest('.mermaid-widget');
          if (widget?.getAttribute('data-complete') === 'true') {
            await renderMermaidChart(container);
          }
        });
      });
    }, 100);
  };

  onMount(() => {
    const preset = getMermaidThemePreset();
    (mermaid as any).initialize(getMermaidInitConfig(preset));

    const onMermaidClick = (e: MouseEvent) => handleMermaidClick(e, showToast);
    document.addEventListener('click', onMermaidClick);
    document.addEventListener('wheel', handleMermaidWheel, { passive: false });
    document.addEventListener('change', handleMermaidChange);
    document.addEventListener('pointerdown', handleMermaidPointerDown);
    document.addEventListener('pointermove', handleMermaidPointerMove, { passive: false } as any);
    document.addEventListener('pointerup', handleMermaidPointerUp);
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (e.defaultPrevented) return;
        closeMermaidExportModal();
        closeMermaidOverlay();
      }
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('click', onMermaidClick);
      document.removeEventListener('wheel', handleMermaidWheel as any);
      document.removeEventListener('change', handleMermaidChange);
      document.removeEventListener('pointerdown', handleMermaidPointerDown);
      document.removeEventListener('pointermove', handleMermaidPointerMove as any);
      document.removeEventListener('pointerup', handleMermaidPointerUp);
      document.removeEventListener('keydown', handleKeyDown);
      closeMermaidExportModal();
      closeMermaidOverlay();
    };
  });

  return {
    debouncedRender
  };
}
