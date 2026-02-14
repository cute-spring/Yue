export type MermaidThemePreset = 'default' | 'forest' | 'dark' | 'neutral';

export const MERMAID_THEME_STORAGE_KEY = 'mermaid_theme';

const PRESETS: Array<{ id: MermaidThemePreset; label: string }> = [
  { id: 'default', label: 'Default' },
  { id: 'forest', label: 'Forest' },
  { id: 'dark', label: 'Dark' },
  { id: 'neutral', label: 'Neutral' },
];

export const MERMAID_THEME_PRESETS = PRESETS;

export const getMermaidThemePreset = (): MermaidThemePreset => {
  try {
    const raw = localStorage.getItem(MERMAID_THEME_STORAGE_KEY);
    const found = PRESETS.find((p) => p.id === raw);
    return found?.id || 'default';
  } catch (e) {
    return 'default';
  }
};

export const setMermaidThemePreset = (preset: MermaidThemePreset) => {
  try {
    localStorage.setItem(MERMAID_THEME_STORAGE_KEY, preset);
  } catch (e) {}
};

export const cycleMermaidThemePreset = (current?: MermaidThemePreset): MermaidThemePreset => {
  const active = current || getMermaidThemePreset();
  const index = Math.max(0, PRESETS.findIndex((p) => p.id === active));
  const next = PRESETS[(index + 1) % PRESETS.length].id;
  setMermaidThemePreset(next);
  return next;
};

export const getMermaidThemeLabel = (preset: MermaidThemePreset) => PRESETS.find((p) => p.id === preset)?.label || 'Theme';

export const detectDiagramType = (code: string): string => {
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

export const getMermaidInitConfig = (preset: MermaidThemePreset) => {
  return {
    startOnLoad: false,
    theme: preset,
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
};
