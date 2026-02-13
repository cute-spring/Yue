import { marked } from 'marked';
import hljs from 'highlight.js';
import katex from 'katex';
import { getMermaidThemePreset, MERMAID_THEME_PRESETS, type MermaidThemePreset } from './mermaidTheme';

/**
 * Normalizes mermaid code by removing backticks and language tags.
 */
export function normalizeMermaidCode(code: string): string {
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
  return normalized;
}

/**
 * Returns HTML options for mermaid theme selection.
 */
export function getMermaidThemeOptionsHtml(selected: MermaidThemePreset): string {
  return MERMAID_THEME_PRESETS.map((p) => 
    `<option value="${p.id}" ${p.id === selected ? 'selected' : ''}>${p.label}</option>`
  ).join('');
}

/**
 * Custom math rendering helper using KaTeX.
 * Protects code blocks from being parsed as math.
 */
export function renderMath(text: string): string {
  const codeBlocks: string[] = [];
  
  // 1. Protect code blocks (```...```)
  let processedText = text.replace(/```[\s\S]*?```/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 2. Protect inline code (`...`)
  processedText = processedText.replace(/`[^`\n]+`/g, (match) => {
    codeBlocks.push(match);
    return `__CODE_BLOCK_${codeBlocks.length - 1}__`;
  });

  // 3. Render Math
  // Block math: $$ ... $$ or \[ ... \]
  const blockMathRegex = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]/g;
  processedText = processedText.replace(blockMathRegex, (_, math1, math2) => {
    const math = math1 || math2;
    try {
      return `<div class="math-block my-4 overflow-x-auto">` + 
             katex.renderToString(math, { displayMode: true, throwOnError: false }) + 
             `</div>`;
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Inline math: \( ... \)
  processedText = processedText.replace(/\\\(([\s\S]+?)\\\)/g, (_, math) => {
    try {
      return katex.renderToString(math, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // Inline math: $ ... $ (avoiding common false positives)
  processedText = processedText.replace(/\$([^\s$](?:[^$]*[^\s$])?)\$/g, (_, math) => {
    try {
      return katex.renderToString(math, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="text-red-500">${math}</span>`;
    }
  });

  // 4. Restore code blocks
  processedText = processedText.replace(/__CODE_BLOCK_(\d+)__/g, (_, index) => {
    return codeBlocks[parseInt(index)];
  });

  return processedText;
}

/**
 * Configures and returns a custom marked renderer.
 */
export function createMarkdownRenderer(): any {
  const renderer = new marked.Renderer();

  renderer.code = function({ text, lang }): string {
    const displayLanguage = lang || 'plaintext';
    const highlightLanguage = hljs.getLanguage(displayLanguage) ? displayLanguage : 'plaintext';
    const highlighted = hljs.highlight(text, { language: highlightLanguage }).value;
    
    const isPreviewable = ['html', 'svg', 'xml', 'mermaid'].includes(displayLanguage);
    const encodedContent = encodeURIComponent(text).replace(/'/g, '%27');

    let html = `
      <div class="code-block-container relative group my-6 rounded-xl overflow-hidden border border-border/50 bg-[#0d1117] shadow-xl transition-all duration-300 hover:border-primary/30">
        <div class="flex items-center justify-between px-4 py-2.5 bg-[#161b22]/80 backdrop-blur-sm border-b border-border/10">
          <div class="flex items-center gap-2">
            <div class="flex items-center gap-1.5 mr-2">
              <div class="w-3 h-3 rounded-full bg-[#ff5f56] shadow-inner"></div>
              <div class="w-3 h-3 rounded-full bg-[#ffbd2e] shadow-inner"></div>
              <div class="w-3 h-3 rounded-full bg-[#27c93f] shadow-inner"></div>
            </div>
            <div class="h-4 w-[1px] bg-border/10 mx-1"></div>
            <span class="text-[10px] font-black font-mono text-text-secondary/60 uppercase tracking-[0.2em] ml-1">${displayLanguage}</span>
          </div>
          <div class="flex items-center gap-2">
    `;

    if (isPreviewable) {
      html += `
              <button 
                onclick="window.openArtifact('${displayLanguage}', '${encodedContent}')"
                class="px-2 py-1 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-all flex items-center gap-1.5 border border-primary/20"
                title="Open Preview"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                <span class="text-[9px] font-bold uppercase tracking-wider">Preview</span>
              </button>
      `;
    }

    html += `
            <button 
              onclick="window.copyToClipboard(this)" 
              class="p-1.5 rounded-lg hover:bg-white/5 text-text-secondary/60 hover:text-primary transition-all flex items-center gap-1.5 group/copy"
              title="Copy code"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform group-hover/copy:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              <span class="text-[9px] font-black uppercase tracking-wider">Copy</span>
            </button>
          </div>
        </div>
        <pre class="p-5 overflow-x-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent selection:bg-primary/20"><code class="hljs language-${highlightLanguage} text-[14px] leading-relaxed font-mono block">${highlighted}</code></pre>
      </div>
    `;

    if (lang === 'mermaid') {
      const preset = getMermaidThemePreset();
      
      // Check if the mermaid block is closed
      const raw = (this as any)._currentContent || '';
      const blockCount = ((this as any)._mermaidCount || 0) + 1;
      (this as any)._mermaidCount = blockCount;
      
      let isClosed = true;
      let currentIdx = -1;
      for (let i = 0; i < blockCount; i++) {
        currentIdx = raw.indexOf('```mermaid', currentIdx + 1);
        if (currentIdx === -1) {
          currentIdx = raw.toLowerCase().indexOf('```mermaid', currentIdx + 1);
        }
      }
      
      if (currentIdx !== -1) {
        const afterBlock = raw.substring(currentIdx + 10);
        const closingIdx = afterBlock.indexOf('```');
        isClosed = closingIdx !== -1 && closingIdx >= text.trim().length;
      }

      return `
        <div class="mermaid-widget my-4" data-code="${encodedContent}" data-complete="${isClosed}" data-scale="1" data-tx="0" data-ty="0" data-tab="diagram">
          <div class="flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-xl shadow-sm">
            <div class="flex items-center gap-2">
              <button type="button" data-mermaid-action="tab-diagram" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors ${isClosed ? 'bg-gray-100 text-gray-900' : 'text-gray-400 cursor-not-allowed'}" ${!isClosed ? 'disabled' : ''}>Diagram</button>
              <button type="button" data-mermaid-action="tab-code" class="px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors text-gray-500 hover:text-gray-800 hover:bg-gray-50">Code</button>
            </div>
            <div class="flex items-center gap-1.5 text-gray-500">
              <button type="button" data-mermaid-action="zoom-out" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom out" ${!isClosed ? 'disabled' : ''}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="7" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  <line x1="8" y1="11" x2="14" y2="11" />
                </svg>
              </button>
              <button type="button" data-mermaid-action="zoom-in" class="p-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Zoom in" ${!isClosed ? 'disabled' : ''}>
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
                <select data-mermaid-theme-select="1" class="text-sm font-semibold text-gray-800 bg-white border border-gray-200 rounded-lg px-2 py-1.5 hover:border-gray-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20" ${!isClosed ? 'disabled' : ''}>
                  ${getMermaidThemeOptionsHtml(preset)}
                </select>
              </div>
              <button type="button" data-mermaid-action="fit" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fit" ${!isClosed ? 'disabled' : ''}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 3H3v5" />
                  <path d="M16 3h5v5" />
                  <path d="M21 16v5h-5" />
                  <path d="M3 16v5h5" />
                </svg>
                <span class="text-sm font-semibold">Fit</span>
              </button>
              <button type="button" data-mermaid-action="download" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Export" ${!isClosed ? 'disabled' : ''}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
                <span class="text-sm font-semibold">Export</span>
              </button>
              <button type="button" data-mermaid-action="fullscreen" class="px-3 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800 flex items-center gap-2" title="Fullscreen" ${!isClosed ? 'disabled' : ''}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h5a1 1 0 110 2H6v3a1 1 0 11-2 0V4zm14 0a1 1 0 00-1-1h-5a1 1 0 100 2h3v3a1 1 0 102 0V4zM3 16a1 1 0 001 1h5a1 1 0 100-2H6v-3a1 1 0 10-2 0v4zm14 0a1 1 0 01-1 1h-5a1 1 0 110-2h3v-3a1 1 0 112 0v4z" clip-rule="evenodd" />
                </svg>
                <span class="text-sm font-semibold">Fullscreen</span>
              </button>
              <button type="button" data-mermaid-action="reset" class="px-2 py-2 rounded-lg hover:bg-gray-50 hover:text-gray-800" title="Reset zoom" ${!isClosed ? 'disabled' : ''}>
                <span class="mermaid-widget-zoom-label text-sm font-semibold">100%</span>
              </button>
            </div>
          </div>
          <div class="mt-3 bg-white border border-gray-200 rounded-2xl overflow-hidden">
            <div class="mermaid-widget-diagram-panel">
              <div class="mermaid-widget-viewport w-full overflow-auto">
                <div class="mermaid-widget-zoom-area min-h-[280px] flex justify-center items-center p-6 transition-all duration-300" style="transform: translate(0px, 0px) scale(1); transform-origin: top center;">
                  <div class="mermaid-chart w-full flex justify-center" data-code="${encodedContent}">
                    ${isClosed ? `
                      <div class="flex flex-col items-center justify-center">
                        <div class="loading-spinner w-8 h-8 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin"></div>
                        <div class="text-[10px] mt-3 text-emerald-600/50 font-medium tracking-wider uppercase">Rendering Diagram...</div>
                      </div>
                    ` : `
                      <div class="flex flex-col items-center justify-center text-gray-400">
                        <div class="w-8 h-8 border-2 border-gray-200 border-t-emerald-400 rounded-full animate-spin mb-4"></div>
                        <div class="text-xs font-medium animate-pulse">Generating diagram...</div>
                      </div>
                    `}
                  </div>
                </div>
              </div>
            </div>
            <div class="mermaid-widget-code-panel hidden">
              <pre class="p-6 overflow-x-auto bg-gray-50 text-xs font-mono text-gray-700 leading-relaxed"><code>${text}</code></pre>
            </div>
          </div>
        </div>
      `;
    }

    return html;
  };

  return renderer;
}

/**
 * Main function to render markdown content with math and custom code blocks.
 */
export function renderMarkdown(content: string): string {
  const mathProcessed = renderMath(content);
  const renderer = createMarkdownRenderer();
  
  // Attach state for mermaid block tracking
  (renderer as any)._currentContent = content;
  (renderer as any)._mermaidCount = 0;
  
  return marked(mathProcessed, { renderer }) as string;
}
