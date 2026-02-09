import { onMount, createSignal, Show, createEffect } from 'solid-js';
import mermaid from 'mermaid';
import { getMermaidInitConfig, getMermaidThemePreset } from '../utils/mermaidTheme';

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  id?: string;
  maxWidth?: number;
  onRendered?: () => void;
  onError?: (error: string) => void;
}

export default function MermaidDiagram(props: MermaidDiagramProps) {
  const [isRendered, setIsRendered] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);
  const [dimensions, setDimensions] = createSignal({ width: 0, height: 0 });
  const [diagramType, setDiagramType] = createSignal<string>('unknown');
  const diagramId = props.id || `mermaid-${Math.random().toString(36).slice(2, 11)}`;
  let renderSeq = 0;

  const detectDiagramType = (code: string): string => {
    const normalized = code.toLowerCase().trim();
    if (normalized.includes('sequencediagram')) return 'sequence';
    if (normalized.includes('graph')) {
      if (normalized.includes('flowchart')) return 'flowchart';
      if (normalized.includes('classdiagram')) return 'class';
      if (normalized.includes('statediagram')) return 'state';
      if (normalized.includes('entityrelationship')) return 'er';
      return 'graph';
    }
    if (normalized.includes('gantt')) return 'gantt';
    if (normalized.includes('pie')) return 'pie';
    if (normalized.includes('journey')) return 'journey';
    if (normalized.includes('gitgraph')) return 'git';
    return 'unknown';
  };

const normalizeMermaidCode = (code: string) => {
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
    
    // Auto-fix common syntax errors (Enhanced DeepSeek/Doubao style)
    // 1. Fix broken arrows with spaces
    normalized = normalized.replace(/ - -> /g, ' --> ');
    normalized = normalized.replace(/ = => /g, ' ==> ');
    // 2. Fix common arrow spacing issues
    normalized = normalized.replace(/(\w)\s*-->\s*(\w)/g, '$1 --> $2');
    normalized = normalized.replace(/(\w)\s*-.->\s*(\w)/g, '$1 -.-> $2');
    // 3. Fix participant declarations in sequence diagrams
    normalized = normalized.replace(/participant\s+(\w+)\s+as\s+(\w+)/gi, 'participant $2 as $1');
    // 4. Ensure proper line endings for better parsing
    normalized = normalized.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    return normalized;
  };

  onMount(() => {
    try {
      const preset = getMermaidThemePreset();
      (mermaid as any).initialize(getMermaidInitConfig(preset));
    } catch (err) {
      console.warn('Mermaid initialization warning:', err);
    }
  });

  const renderDiagram = async () => {
    const chart = normalizeMermaidCode(props.chart);
    if (!chart) {
      return;
    }

    try {
      setError(null);
      renderSeq += 1;
      const renderId = `${diagramId}-${renderSeq}`;
      
      // Detect diagram type for optimized rendering
      const detectedType = detectDiagramType(chart);
      setDiagramType(detectedType);
      
      // Configure mermaid based on diagram type (DeepSeek/Doubao style optimization)
      const config = {
        startOnLoad: false,
        theme: 'base' as const,
        themeVariables: {
          primaryColor: '#10B981', // Emerald 500
          primaryTextColor: '#1f2937', // Gray 800
          primaryBorderColor: '#059669',
          lineColor: '#64748b', // Slate 500
          secondaryColor: '#ecfdf5', // Emerald 50
          tertiaryColor: '#f0fdf4', // Emerald 50 lighter
          fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          fontSize: '14px',
          // Type-specific colors
          ...(detectedType === 'sequence' && {
            actorBkg: '#10B981',
            actorBorder: '#059669',
            actorTextColor: '#ffffff',
            actorLineColor: '#64748b',
            signalColor: '#1f2937',
            signalTextColor: '#1f2937',
          }),
          ...(detectedType === 'flowchart' && {
            nodeBkg: '#10B981',
            nodeBorder: '#059669',
            clusterBkg: '#ecfdf5',
            clusterBorder: '#a7f3d0',
          }),
        },
        // Type-specific configurations
        flowchart: {
          curve: 'basis',
          htmlLabels: true,
          padding: 15,
          nodeSpacing: 50,
          rankSpacing: 80,
        },
        sequence: {
          actorMargin: 50,
          boxMargin: 10,
          boxTextMargin: 5,
          noteMargin: 10,
          messageMargin: 35,
          mirrorActors: false,
          bottomMarginAdj: 1,
          activationWidth: 20,
          diagramMarginX: 50,
          diagramMarginY: 10,
        },
        securityLevel: 'loose',
      };
      
      // Re-initialize with type-specific config
      (mermaid as any).initialize(config);
      
      await mermaid.parse(chart);
      const { svg } = await mermaid.render(renderId, chart);
      
      const element = document.getElementById(diagramId + '-container');
      if (element) {
        element.innerHTML = svg;
        
        const parser = new DOMParser();
        const svgDoc = parser.parseFromString(svg, 'image/svg+xml');
        const svgElement = svgDoc.documentElement;
        const width = parseInt(svgElement.getAttribute('width') || '0');
        const height = parseInt(svgElement.getAttribute('height') || '0');
        
        setDimensions({ width, height });
        setIsRendered(true);
        props.onRendered?.();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to render diagram';
      console.error('Mermaid render error:', err);
      setError(errorMsg);
      props.onError?.(errorMsg);
      setIsRendered(false);
    }
  };

  createEffect(() => {
    if (props.chart) {
      renderDiagram();
    }
  });

  return (
    <div class={`relative ${props.className || ''}`}>
      <Show when={error()}>
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-800 dark:text-red-200">
          <div class="font-semibold flex items-center gap-2">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            Diagram Error
          </div>
          <div class="mt-1 opacity-90">{error()}</div>
          <details class="mt-2">
            <summary class="text-xs cursor-pointer opacity-70 hover:opacity-100 transition-opacity">Show diagram code</summary>
            <pre class="mt-1 text-xs overflow-auto bg-red-100 dark:bg-red-900/40 p-2 rounded border border-red-200 dark:border-red-800/50 whitespace-pre-wrap">
              {props.chart}
            </pre>
          </details>
        </div>
      </Show>
      
      <div 
        class={`transition-opacity duration-300 ${isRendered() ? 'opacity-100' : 'opacity-0 absolute inset-0'}`}
      >
        <div 
          id={diagramId + '-container'}
          class="mermaid-output bg-white dark:bg-[#0d1117] rounded-lg border border-gray-200 dark:border-gray-800 p-4 overflow-x-auto flex justify-center"
          style={props.maxWidth ? { 'max-width': `${props.maxWidth}px` } : {}}
        />
        
        <Show when={isRendered() && dimensions().width > 0}>
          <div class="flex justify-between items-center mt-2 px-1">
            <div class="flex items-center gap-2">
              <div class="text-[10px] text-gray-400 font-mono">
                {dimensions().width}×{dimensions().height}px
              </div>
              <Show when={diagramType() !== 'unknown'}>
                <div class="text-[10px] text-emerald-600 font-medium bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded">
                  {diagramType().charAt(0).toUpperCase() + diagramType().slice(1)} Diagram
                </div>
              </Show>
            </div>
            <div class="flex items-center gap-3">
              <button 
                onClick={() => {
                  const chartCode = normalizeMermaidCode(props.chart);
                  const encoded = encodeURIComponent(chartCode).replace(/'/g, '%27');
                  if ((window as any).openArtifact) {
                    (window as any).openArtifact('mermaid', encoded);
                  }
                }}
                class="text-[10px] text-gray-500 hover:text-emerald-600 font-medium transition-colors flex items-center gap-1"
                title="Open in Preview Panel"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd" />
                </svg>
                Preview
              </button>
              <button 
                onClick={() => {
                  const element = document.getElementById(diagramId + '-container');
                  const svg = element?.querySelector('svg');
                  if (svg) {
                    const data = new XMLSerializer().serializeToString(svg);
                    const blob = new Blob([data], { type: 'image/svg+xml' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `diagram-${diagramType()}-${diagramId}.svg`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }
                }}
                class="text-[10px] text-emerald-600 hover:text-emerald-500 font-medium transition-colors flex items-center gap-1"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
                SVG
              </button>
            </div>
          </div>
        </Show>
      </div>

      <Show when={!isRendered() && !error() && props.chart}>
        <div class="flex flex-col items-center justify-center p-8 bg-gray-50/50 dark:bg-gray-800/20 rounded-lg border border-gray-100 dark:border-gray-800">
          <div class="w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
          <span class="text-xs text-gray-500 mt-2">Rendering diagram...</span>
        </div>
      </Show>
    </div>
  );
}
