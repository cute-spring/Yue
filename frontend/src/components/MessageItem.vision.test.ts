import { describe, expect, it } from 'vitest';
import {
  formatSnapshotVisibleText,
  getVisionBadge,
  getVisionFeedbackText,
  sanitizeAssistantDisplayContent,
  structureSnapshotVisibleText,
  stripDuplicateArtifactReferences,
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

  it('removes system action and tool result lines from displayed content', () => {
    const content = [
      '[Action Preflight] `browser-operator.capture` is ready as a platform-tool action.',
      '[Action Flow] `browser-operator.capture` was queued for platform-tool handling.',
      '[Tool Result] `builtin:browser_snapshot` returned:',
      '{"snapshot":{"visible_text":"Example Domain"}}',
      '[Tool Result] `builtin:browser_screenshot` returned:',
      '{"filename":"browser-shot.png","download_url":"/exports/browser-shot.png","artifact":{"kind":"screenshot"}}',
      'Screenshot ready:',
      '![browser-shot.png](/exports/browser-shot.png)',
      '',
      'Example Domain',
      'This domain is for use in illustrative examples in documents.',
    ].join('\n');

    expect(sanitizeAssistantDisplayContent(content)).toBe(
      ['Example Domain', 'This domain is for use in illustrative examples in documents.'].join('\n'),
    );
  });

  it('removes duplicate artifact markdown when the same screenshot is rendered as a content card', () => {
    const content = [
      'Here is the page summary.',
      '![browser-shot.png](/exports/browser-shot.png)',
      '',
      'More explanation below.',
    ].join('\n');

    expect(stripDuplicateArtifactReferences(content, ['/exports/browser-shot.png'])).toBe(
      ['Here is the page summary.', '', 'More explanation below.'].join('\n'),
    );
  });

  it('formats flattened browser snapshot text into readable sections', () => {
    const raw = 'Tools, Thinking models · Ollama Models Docs Pricing Sign in Download Cloud Embedding Vision Tools Thinking Popular Newest nemotron-cascade-2 An open 30B MoE model from NVIDIA. Updated 1 week ago qwen3.5 A multimodal model family. Updated 3 weeks ago';

    expect(formatSnapshotVisibleText(raw, 'Tools, Thinking models · Ollama')).toBe(
      [
        'Models Docs Pricing Sign in Download',
        'Cloud Embedding Vision Tools Thinking',
        'Popular Newest',
        'nemotron-cascade-2 An open 30B MoE model from NVIDIA. Updated 1 week ago',
        'qwen3.5 A multimodal model family. Updated 3 weeks ago',
      ].join('\n\n'),
    );
  });

  it('extracts structure and result items from flattened browser snapshot text', () => {
    const raw = 'Tools, Thinking models · Ollama Models Docs Pricing Sign in Download Cloud Embedding Vision Tools Thinking Popular Newest nemotron-cascade-2 An open 30B MoE model from NVIDIA. Updated 1 week ago qwen3.5 A multimodal model family. Updated 3 weeks ago';

    expect(structureSnapshotVisibleText(raw, 'Tools, Thinking models · Ollama')).toEqual({
      headerLines: ['Models Docs Pricing Sign in Download', 'Cloud Embedding Vision Tools Thinking'],
      scopeLine: '',
      sortLine: 'Popular Newest',
      resultItems: [
        'nemotron-cascade-2 An open 30B MoE model from NVIDIA. Updated 1 week ago',
        'qwen3.5 A multimodal model family. Updated 3 weeks ago',
      ],
      paragraphs: [],
    });
  });
});
