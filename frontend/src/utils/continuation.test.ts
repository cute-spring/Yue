import { describe, expect, it } from 'vitest';
import {
  buildContinuationRequestOverrides,
  getMergedContinuationContent,
  inferContinuationContentType,
} from './continuation';
import { Message } from '../types';

describe('continuation helpers', () => {
  it('builds request overrides from the merged target response', () => {
    const messages: Message[] = [
      {
        role: 'assistant',
        content: '```svg\n<svg><text>Hello',
        assistant_turn_id: 'turn_root',
        finish_reason: 'length',
      },
    ];

    const overrides = buildContinuationRequestOverrides(messages, messages[0]);

    expect(overrides.continuation_of).toBe('turn_root');
    expect(overrides.continuation_root_id).toBe('turn_root');
    expect(overrides.continuation_content_type).toBe('svg');
    expect(overrides.continuation_tail).toContain('<svg><text>Hello');
  });

  it('merges a continuation chain and strips the generated continue notice', () => {
    const messages: Message[] = [
      {
        role: 'assistant',
        content:
          'First part\n\n> ⚠️ **[系统提示]** 由于输出长度限制，内容可能未完全生成。您可以输入 **“继续”** 来获取剩余部分。',
        assistant_turn_id: 'turn_root',
        finish_reason: 'length',
      },
      {
        role: 'user',
        content: '继续',
      },
      {
        role: 'assistant',
        content: ' second part',
        assistant_turn_id: 'turn_child',
        continuation_of: 'turn_root',
        continuation_root_id: 'turn_root',
      },
    ];

    expect(getMergedContinuationContent(messages, messages[2])).toBe('First part second part');
  });

  it('infers common structured content types', () => {
    expect(inferContinuationContentType('```json\n{"a":')).toBe('json');
    expect(inferContinuationContentType('<svg viewBox="0 0 10 10">')).toBe('svg');
    expect(inferContinuationContentType('regular markdown')).toBe('markdown');
  });
});
