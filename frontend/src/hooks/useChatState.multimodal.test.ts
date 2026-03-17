import { describe, expect, it } from 'vitest';
import { canSubmitChatRequest } from './useChatState';

describe('useChatState multimodal submit rules', () => {
  it('allows submit when only images are attached', () => {
    expect(canSubmitChatRequest('', 1)).toBe(true);
    expect(canSubmitChatRequest('   ', 2)).toBe(true);
  });

  it('rejects submit when both text and images are empty', () => {
    expect(canSubmitChatRequest('', 0)).toBe(false);
    expect(canSubmitChatRequest('   ', 0)).toBe(false);
  });
});
