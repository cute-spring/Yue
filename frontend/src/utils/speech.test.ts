import { describe, expect, it } from 'vitest';
import { getSpeechMessageId, prepareSpeechText, sanitizeSpeechText, splitSpeechSegments } from './speech';

describe('speech utils', () => {
  it('builds stable message id from assistant turn id first', () => {
    expect(getSpeechMessageId({ role: 'assistant', content: 'x', assistant_turn_id: 'turn_1' }, 3)).toBe('turn:turn_1');
  });

  it('sanitizes markdown and code blocks', () => {
    const raw = '# Title\n\n- item\n```ts\nconst x = 1;\n```\n**Hello** [world](https://example.com)';
    expect(sanitizeSpeechText(raw)).toBe('Title item Hello world');
  });

  it('truncates long text with ellipsis', () => {
    const long = 'a'.repeat(1300);
    const out = prepareSpeechText(long, 1200);
    expect(out.length).toBeGreaterThan(1200);
    expect(out.endsWith('...')).toBe(true);
  });

  it('splits mixed Chinese and English into language-aware segments', () => {
    const segments = splitSpeechSegments('这是中文 intro text 再来一段中文 and final English.');
    expect(segments.length).toBeGreaterThan(1);
    expect(segments.some(s => s.langHint === 'zh')).toBe(true);
    expect(segments.some(s => s.langHint === 'en')).toBe(true);
  });
});
