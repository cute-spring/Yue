import { onMount } from 'solid-js';
import { disposeYueCharts, handleYueChartChange, handleYueChartClick, renderPendingYueCharts } from '../utils/chartRenderer';

export function useCharts() {
  let renderTimeout: ReturnType<typeof setTimeout> | undefined;

  const debouncedRenderCharts = () => {
    if (renderTimeout) clearTimeout(renderTimeout);
    renderTimeout = setTimeout(() => {
      requestAnimationFrame(() => renderPendingYueCharts());
    }, 100);
  };

  onMount(() => {
    document.addEventListener('click', handleYueChartClick);
    document.addEventListener('change', handleYueChartChange);
    return () => {
      if (renderTimeout) clearTimeout(renderTimeout);
      document.removeEventListener('click', handleYueChartClick);
      document.removeEventListener('change', handleYueChartChange);
      disposeYueCharts();
    };
  });

  return { debouncedRenderCharts };
}
