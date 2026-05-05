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

export type SensitiveDetection = {
  value: string;
  placeholder: string;
  key: string;
  index: number;
};

const SENSITIVE_PATTERNS: { pattern: RegExp; keyFromMatch: (m: RegExpExecArray) => string }[] = [
  {
    pattern: /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*(sk-[a-zA-Z0-9]{20,})/gi,
    keyFromMatch: (m) => m[1] || 'TOKEN',
  },
  {
    pattern: /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*([a-zA-Z0-9_\-]{20,})/gi,
    keyFromMatch: (m) => m[1] || 'TOKEN',
  },
  {
    pattern: /(?:Authorization|X-API-Key|api-key)\s*[=:]\s*(Bearer\s+)?(eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+)/gi,
    keyFromMatch: () => 'AUTHORIZATION',
  },
  {
    pattern: /(?:Authorization|X-API-Key|api-key)\s*[=:]\s*(Bearer\s+)?(sk-[a-zA-Z0-9]{20,})/gi,
    keyFromMatch: () => 'AUTHORIZATION',
  },
];

const PASSWORD_PATTERN = /([A-Z_][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|KEY|API[_\-]?KEY))\s*[=:]\s*([^\s]{8,})/gi;

export const detectSensitiveValues = (text: string): SensitiveDetection[] => {
  const seen = new Set<string>();
  const results: SensitiveDetection[] = [];

  for (const { pattern, keyFromMatch } of SENSITIVE_PATTERNS) {
    pattern.lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text)) !== null) {
      const value = match[2] || match[3] || '';
      if (seen.has(value)) continue;
      seen.add(value);
      const key = keyFromMatch(match);
      results.push({
        value,
        placeholder: `\${${key}_TOKEN}`,
        key,
        index: match.index,
      });
    }
  }

  PASSWORD_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = PASSWORD_PATTERN.exec(text)) !== null) {
    const value = match[2] || '';
    if (
      seen.has(value) ||
      value.startsWith('${') ||
      /^(true|false|yes|no|on|off|\d+)$/i.test(value) ||
      value.includes('://') ||
      (value.includes('@') && value.includes('.'))
    ) {
      continue;
    }
    seen.add(value);
    const key = match[1] || 'SECRET';
    results.push({
      value,
      placeholder: `\${${key.toUpperCase().replace(/-/g, '_')}}`,
      key: key.toUpperCase().replace(/-/g, '_'),
      index: match.index,
    });
  }

  return results.sort((a, b) => a.index - b.index);
};

export const applyReplacements = (
  text: string,
  detections: SensitiveDetection[],
): string => {
  let result = text;
  for (const det of detections) {
    result = result.replace(det.value, det.placeholder);
  }
  return result;
};
