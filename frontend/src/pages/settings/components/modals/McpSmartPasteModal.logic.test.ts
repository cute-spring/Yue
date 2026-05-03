import { describe, expect, it } from 'vitest';
import { validateSmartPasteInput, applyTransportChange, findNameConflicts, resolveConfidenceTone, detectSensitiveValues, applyReplacements } from './McpSmartPasteModal.logic';
import type { ParsedMcpConfig } from '../../types';

describe('validateSmartPasteInput', () => {
  it('blocks empty input locally', () => {
    expect(validateSmartPasteInput('   ').kind).toBe('empty');
  });

  it('blocks oversized input', () => {
    expect(validateSmartPasteInput('x'.repeat(8001)).kind).toBe('too_long');
  });

  it('allows valid input', () => {
    const result = validateSmartPasteInput('npx -y @test/pkg');
    expect(result.kind).toBe('ok');
    if (result.kind === 'ok') {
      expect(result.text).toBe('npx -y @test/pkg');
    }
  });
});

describe('applyTransportChange', () => {
  const base: ParsedMcpConfig = {
    name: 'test',
    transport: 'stdio',
    command: 'npx',
    args: ['-y', 'pkg'],
    url: null,
    headers: null,
    env: null,
    enabled: false,
    timeout: 60,
    min_version: null,
    confidence: 0.9,
    hints: [],
    warnings: [],
    missing_fields: [],
  };

  it('clears mutually exclusive fields when transport changes to streamable_http', () => {
    const result = applyTransportChange(base, 'streamable_http');
    expect(result.command).toBeNull();
    expect(result.args).toBeNull();
  });

  it('clears url and headers when switching to stdio', () => {
    const http: ParsedMcpConfig = { ...base, transport: 'streamable_http', command: null, args: null, url: 'https://example.com', headers: { 'X-Test': 'val' } };
    const result = applyTransportChange(http, 'stdio');
    expect(result.url).toBeNull();
    expect(result.headers).toBeNull();
  });
});

describe('findNameConflicts', () => {
  it('finds conflicting names', () => {
    expect(findNameConflicts(['jira', 'fs'], [{ name: 'jira' } as ParsedMcpConfig])).toEqual(['jira']);
  });

  it('returns empty when no conflicts', () => {
    expect(findNameConflicts(['jira'], [{ name: 'fs' } as ParsedMcpConfig])).toEqual([]);
  });
});

describe('resolveConfidenceTone', () => {
  it('marks low-confidence results as high risk below 0.6', () => {
    expect(resolveConfidenceTone(0.4)).toBe('danger');
  });

  it('marks medium confidence as warning', () => {
    expect(resolveConfidenceTone(0.7)).toBe('warning');
  });

  it('marks high confidence as normal', () => {
    expect(resolveConfidenceTone(0.95)).toBe('normal');
  });
});

describe('detectSensitiveValues', () => {
  it('detects sk- style API keys', () => {
    const result = detectSensitiveValues('JIRA_TOKEN=sk-abc123def456');
    expect(result.length).toBe(1);
    expect(result[0].value).toBe('sk-abc123def456');
    expect(result[0].key).toBe('JIRA_TOKEN');
  });

  it('detects Bearer tokens', () => {
    const result = detectSensitiveValues('Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature');
    expect(result.length).toBe(1);
    expect(result[0].placeholder).toBe('${AUTHORIZATION_TOKEN}');
  });

  it('suggests placeholder from surrounding env var name', () => {
    const result = detectSensitiveValues('JIRA_TOKEN=my-real-secret-value');
    expect(result.length).toBe(1);
    expect(result[0].placeholder).toBe('${JIRA_TOKEN_TOKEN}');
  });

  it('returns empty array for clean text', () => {
    const result = detectSensitiveValues('npx -y @company/mcp-server');
    expect(result).toEqual([]);
  });

  it('detects multiple sensitive values', () => {
    const result = detectSensitiveValues(
      'JIRA_TOKEN=sk-abc12345678901234567\nGITHUB_TOKEN=ghp_xyz12345678901234567\ncommand=npx'
    );
    expect(result.length).toBe(2);
  });
});

describe('applyReplacements', () => {
  it('replaces detected values with placeholders', () => {
    const detections = [
      { value: 'sk-abc123', placeholder: '${JIRA_TOKEN}', key: 'JIRA_TOKEN', index: 0 },
    ];
    const result = applyReplacements('JIRA_TOKEN=sk-abc123', detections);
    expect(result).toBe('JIRA_TOKEN=${JIRA_TOKEN}');
  });

  it('preserves non-matching text', () => {
    const detections = [
      { value: 'sk-abc', placeholder: '${TOKEN}', key: 'TOKEN', index: 6 },
    ];
    const result = applyReplacements('command=npx\nTOKEN=sk-abc\nport=8080', detections);
    expect(result).toContain('command=npx');
    expect(result).toContain('port=8080');
    expect(result).toContain('${TOKEN}');
  });
});
