import type { ParsedMcpConfig } from '../../types';

export type SmartPasteInputValidation =
  | { kind: 'empty' }
  | { kind: 'too_long' }
  | { kind: 'ok'; text: string };

export const validateSmartPasteInput = (rawText: string): SmartPasteInputValidation => {
  const text = rawText.trim();
  if (!text) return { kind: 'empty' };
  if (text.length > 8000) return { kind: 'too_long' };
  return { kind: 'ok', text };
};

export const applyTransportChange = (
  config: ParsedMcpConfig,
  newTransport: 'stdio' | 'streamable_http',
): ParsedMcpConfig => {
  if (newTransport === config.transport) return config;

  if (newTransport === 'stdio') {
    return {
      ...config,
      transport: 'stdio',
      url: null,
      headers: null,
    };
  }

  return {
    ...config,
    transport: 'streamable_http',
    command: null,
    args: null,
  };
};

export const findNameConflicts = (
  existingNames: string[],
  configs: ParsedMcpConfig[],
): string[] => {
  const existing = new Set(existingNames);
  return configs
    .filter((c) => existing.has(c.name))
    .map((c) => c.name);
};

export const resolveConfidenceTone = (confidence: number): 'normal' | 'warning' | 'danger' => {
  if (confidence >= 0.85) return 'normal';
  if (confidence >= 0.6) return 'warning';
  return 'danger';
};
