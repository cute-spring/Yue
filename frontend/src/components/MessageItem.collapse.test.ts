import { describe, expect, it } from 'vitest';
import { shouldCollapseAssistantMessage } from './MessageItem';

describe('MessageItem collapse helpers', () => {
  it('keeps the latest assistant response expanded by default', () => {
    expect(
      shouldCollapseAssistantMessage({
        role: 'assistant',
        isTyping: false,
        isLatestAssistantMessage: true,
      }),
    ).toBe(false);
  });

  it('collapses older assistant messages by default', () => {
    expect(
      shouldCollapseAssistantMessage({
        role: 'assistant',
        isTyping: false,
        isLatestAssistantMessage: false,
      }),
    ).toBe(true);
  });

  it('never collapses user messages', () => {
    expect(
      shouldCollapseAssistantMessage({
        role: 'user',
        isTyping: false,
        isLatestAssistantMessage: false,
      }),
    ).toBe(false);
  });
});
