
// Cache for rendered Mermaid diagrams to avoid flickering during streaming
const svgCache = new Map<string, string>();

/**
 * Gets a cached SVG for a given code and theme.
 */
export const getCachedMermaidSvg = (code: string, theme: string): string | null => {
  return svgCache.get(`${theme}:${code}`) || null;
};

/**
 * Caches an SVG for a given code and theme.
 */
export const setCachedMermaidSvg = (code: string, theme: string, svg: string): void => {
  svgCache.set(`${theme}:${code}`, svg);
};
