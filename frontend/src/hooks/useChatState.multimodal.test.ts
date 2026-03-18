import { describe, expect, it } from 'vitest';
import { canSubmitChatRequest, getVisionStreamFeedback } from './useChatState';

describe('useChatState multimodal submit rules', () => {
  it('allows submit when only images are attached', () => {
    expect(canSubmitChatRequest('', 1)).toBe(true);
    expect(canSubmitChatRequest('   ', 2)).toBe(true);
  });

  it('rejects submit when both text and images are empty', () => {
    expect(canSubmitChatRequest('', 0)).toBe(false);
    expect(canSubmitChatRequest('   ', 0)).toBe(false);
  });

  it('returns fallback warning when backend downgraded vision to text mode', () => {
    const feedback = getVisionStreamFeedback({
      image_count: 2,
      vision_fallback_mode: 'text_only',
      supports_vision: false,
      vision_enabled: false,
    });
    expect(feedback).toEqual({
      level: 'warning',
      message: '当前模型不支持视觉，已自动降级为纯文本回复。建议切换到支持 Vision 的模型。',
    });
  });

  it('returns reject feedback when backend reports unsupported vision model', () => {
    const feedback = getVisionStreamFeedback(
      {
        image_count: 1,
        supports_vision: false,
        vision_enabled: false,
      },
      'MODEL_VISION_UNSUPPORTED',
    );
    expect(feedback).toEqual({
      level: 'error',
      message: '当前模型不支持视觉能力。请切换到带 Vision 标识的模型后重试。',
    });
  });
});
