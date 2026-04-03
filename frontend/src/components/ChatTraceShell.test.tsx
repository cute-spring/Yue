import { describe, expect, test } from 'vitest';

import ChatTraceShell, { CHAT_TRACE_SHELL_TITLE } from './ChatTraceShell';


describe('ChatTraceShell', () => {
  test('exports component function', () => {
    expect(typeof ChatTraceShell).toBe('function');
  });

  test('exports a stable shell title', () => {
    expect(CHAT_TRACE_SHELL_TITLE).toBe('Trace Inspector');
  });
  test('retains a stable component export contract', () => {
    expect(ChatTraceShell.name).toBe('ChatTraceShell');
  });
});
