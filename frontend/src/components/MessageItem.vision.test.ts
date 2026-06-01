import { describe, expect, it } from 'vitest';
import {
  getRenderableUserAttachments,
  getVisionBadge,
  getVisionFeedbackText,
  getWorkspaceGroundingModeLabel,
  getWorkspaceGroundingSummary,
  getWorkspaceSourceModeLabel,
  getWorkspaceToolingWarning,
} from './MessageItem';

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

  it('deduplicates data-url legacy images when uploaded image attachments already exist', () => {
    const result = getRenderableUserAttachments({
      attachments: [
        {
          id: 'att_img_1',
          kind: 'file',
          display_name: 'photo.png',
          mime_type: 'image/png',
          url: '/files/chat/att_img_1.png',
        },
      ],
      images: ['data:image/png;base64,AAA'],
    });

    expect(result).toHaveLength(1);
    expect(result[0].url).toBe('/files/chat/att_img_1.png');
    expect(result[0].source).not.toBe('legacy_images');
  });
});

describe('MessageItem workspace grounding helpers', () => {
  it('labels workspace source and grounding modes', () => {
    expect(getWorkspaceSourceModeLabel('selected')).toBe('Selected sources');
    expect(getWorkspaceGroundingModeLabel('require_sources')).toBe('Citations required');
  });

  it('summarizes answer evidence contract with citations', () => {
    expect(
      getWorkspaceGroundingSummary({
        workspace_grounding: {
          workspace_id: 'ws_1',
          workspace_source_mode: 'selected',
          grounding_mode: 'require_sources',
          eligible_sources: [{ id: 'src_1', display_name: 'Report.pdf' }],
          unavailable_sources: [{ id: 'src_2', display_name: 'Missing.pdf' }],
        },
        citations: [{ path: 'Report.pdf' }, { path: 'Report.pdf' }],
      }),
    ).toBe('Selected sources; Citations required; 1 eligible, 1 unavailable; 2 citations attached');
  });

  it('returns tooling warning when backend marks require-sources turn as tool-incomplete', () => {
    expect(
      getWorkspaceToolingWarning({
        workspace_grounding: {
          grounding_mode: 'require_sources',
          tooling_warning: 'Citation-required mode is active, but no compatible retrieval tools were enabled for this turn.',
        },
      }),
    ).toContain('no compatible retrieval tools');
  });
});
