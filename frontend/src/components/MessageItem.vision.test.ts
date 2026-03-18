import { describe, expect, it } from 'vitest';
import { getVisionBadge, getVisionFeedbackText } from './MessageItem';

describe('MessageItem vision feedback helpers', () => {
  it('returns fallback badge when backend applies text-only fallback', () => {
    expect(
      getVisionBadge({
        vision_fallback_mode: 'text_only',
        image_count: 2,
      }),
    ).toEqual({
      label: 'Vision Fallback',
      className: 'bg-amber-500/5 border-amber-500/20 text-amber-500',
    });
  });

  it('returns off badge when model does not support vision', () => {
    expect(
      getVisionBadge({
        supports_vision: false,
        vision_enabled: false,
      }),
    ).toEqual({
      label: 'Vision Off',
      className: 'bg-rose-500/5 border-rose-500/20 text-rose-500',
    });
  });

  it('returns reject guidance for unsupported vision error code', () => {
    expect(
      getVisionFeedbackText({
        error_code: 'MODEL_VISION_UNSUPPORTED',
      }),
    ).toBe('该模型不支持视觉能力，请切换到带 Vision 标识的模型后重试。');
  });
});
