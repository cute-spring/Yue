import { describe, expect, it } from 'vitest';
import { getRenderableUserAttachments, getVisionBadge, getVisionFeedbackText } from './MessageItem';

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

  it('renders history attachments and keeps legacy images compatible', () => {
    const result = getRenderableUserAttachments({
      attachments: [
        { id: 'att_pdf', kind: 'file', display_name: 'report.pdf', mime_type: 'application/pdf', url: '/files/report.pdf' },
      ],
      images: ['/files/legacy.png'],
    });
    expect(result).toHaveLength(2);
    expect(result[0].display_name).toBe('report.pdf');
    expect(result[1].display_name).toBe('legacy.png');
    expect(result[1].mime_type).toBe('image/*');
  });

  it('deduplicates legacy images when attachment with same id/url already exists', () => {
    const result = getRenderableUserAttachments({
      attachments: [
        { id: 'att_img', kind: 'file', display_name: 'screen.png', mime_type: 'image/png', url: '/files/chat/att_img.png' },
        { kind: 'file', display_name: 'report.pdf', mime_type: 'application/pdf', url: '/files/chat/att_pdf.pdf' },
      ],
      images: ['/files/chat/att_img.png', '/files/chat/legacy-only.png'],
    });

    expect(result).toHaveLength(3);
    expect(result.map((item) => item.url)).toEqual([
      '/files/chat/att_img.png',
      '/files/chat/att_pdf.pdf',
      '/files/chat/legacy-only.png',
    ]);
  });

  it('prefers attachment metadata over legacy fallback when same resource appears in both fields', () => {
    const result = getRenderableUserAttachments({
      attachments: [
        {
          kind: 'file',
          id: 'att_1',
          display_name: 'pretty-name.png',
          mime_type: 'image/png',
          url: '/files/chat/dup.png',
        },
      ],
      images: ['/files/chat/dup.png'],
    });

    expect(result).toHaveLength(1);
    expect(result[0].display_name).toBe('pretty-name.png');
    expect(result[0].mime_type).toBe('image/png');
    expect(result[0].source).not.toBe('legacy_images');
  });
});
