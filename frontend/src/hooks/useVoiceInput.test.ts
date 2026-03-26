import { afterEach, describe, expect, it } from 'vitest';
import { composeVoiceInputText, getCommittedVoiceInputText, resolveVoiceInputLanguage } from './useVoiceInput';

const originalNavigator = globalThis.navigator;

afterEach(() => {
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: originalNavigator,
  });
});

describe('composeVoiceInputText', () => {
  it('appends transcript to existing input', () => {
    expect(composeVoiceInputText('Hello', 'world', '', false)).toBe('Hello world');
  });

  it('includes interim transcript when enabled', () => {
    expect(composeVoiceInputText('Hello', 'world', 'again', true)).toBe('Hello world again');
  });

  it('omits interim transcript when disabled', () => {
    expect(composeVoiceInputText('Hello', 'world', 'again', false)).toBe('Hello world');
  });

  it('normalizes whitespace in transcript pieces', () => {
    expect(composeVoiceInputText('Hello ', '  brave   new  ', ' world ', true)).toBe('Hello brave new world');
  });
});

describe('resolveVoiceInputLanguage', () => {
  it('keeps explicit recognition language', () => {
    expect(resolveVoiceInputLanguage('zh-CN', 'en')).toBe('zh-CN');
  });

  it('maps auto to app chinese when app language is zh', () => {
    expect(resolveVoiceInputLanguage('auto', 'zh')).toBe('zh-CN');
  });

  it('maps auto to app english when app language is en', () => {
    expect(resolveVoiceInputLanguage('auto', 'en')).toBe('en-US');
  });

  it('falls back to navigator language when app language is not recognized', () => {
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { language: 'fr-FR' },
    });
    expect(resolveVoiceInputLanguage('auto', 'ja')).toBe('fr-FR');
  });

  it('falls back to english when navigator language is unavailable', () => {
    Object.defineProperty(globalThis, 'navigator', {
      configurable: true,
      value: { language: '' },
    });
    expect(resolveVoiceInputLanguage('auto')).toBe('en-US');
  });
});

describe('getCommittedVoiceInputText', () => {
  it('prefers final transcript when available', () => {
    expect(getCommittedVoiceInputText('hello world', 'hello')).toBe('hello world');
  });

  it('falls back to interim transcript when final transcript is empty', () => {
    expect(getCommittedVoiceInputText('', 'ni hao')).toBe('ni hao');
  });

  it('normalizes whitespace before committing transcript text', () => {
    expect(getCommittedVoiceInputText('  hello   world  ', '')).toBe('hello world');
    expect(getCommittedVoiceInputText('', '  ni   hao  ')).toBe('ni hao');
  });
});
