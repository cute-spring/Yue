import { describe, expect, it } from 'vitest';
import { canSubmitFromInput, extractClipboardImageFiles, getUploadButtonClass, getVisionCapabilityHint, getVoiceInputButtonClass, getVoiceInputProviderLabel, mergeImageAttachments, removeImageAttachmentAt } from './ChatInput';

const makeFile = (name: string, size: number): File => {
  const content = new Array(size).fill('a').join('');
  return new File([content], name, { type: 'image/png' });
};

const makeClipboardItem = (file: File | null, type = 'image/png') => ({
  kind: 'file',
  type,
  getAsFile: () => file,
});

describe('ChatInput multimodal helpers', () => {
  it('allows submit with images only', () => {
    expect(canSubmitFromInput('', 1)).toBe(true);
    expect(canSubmitFromInput('   ', 2)).toBe(true);
  });

  it('merges and caps image attachments with size filtering', () => {
    const existing = [makeFile('a.png', 10)];
    const incoming = [
      makeFile('b.png', 10),
      makeFile('c.png', 12 * 1024 * 1024),
      makeFile('d.png', 10),
    ];
    const result = mergeImageAttachments(existing, incoming, 2, 10 * 1024 * 1024);
    expect(result.files.map((item) => item.name)).toEqual(['a.png', 'b.png']);
    expect(result.oversizedCount).toBe(1);
    expect(result.overflowCount).toBe(1);
  });

  it('uses minimalist style for upload button', () => {
    const idleClass = getUploadButtonClass(0);
    const activeClass = getUploadButtonClass(2);
    expect(idleClass).toContain('text-slate-500');
    expect(idleClass).not.toContain('border');
    expect(activeClass).toContain('bg-primary/20');
    expect(activeClass).toContain('border-primary/30');
  });

  it('extracts pasted image files from clipboard files first', () => {
    const image = makeFile('shot.png', 10);
    const text = new File(['hello'], 'note.txt', { type: 'text/plain' });
    const result = extractClipboardImageFiles({
      files: [text, image],
      items: [makeClipboardItem(null)],
    });
    expect(result.map((item) => item.name)).toEqual(['shot.png']);
  });

  it('falls back to clipboard items when files are unavailable', () => {
    const image = makeFile('pasted.png', 10);
    const result = extractClipboardImageFiles({
      items: [makeClipboardItem(image), makeClipboardItem(null, 'text/plain')],
    });
    expect(result.map((item) => item.name)).toEqual(['pasted.png']);
  });

  it('ignores non-image clipboard payloads', () => {
    const result = extractClipboardImageFiles({
      files: [new File(['hello'], 'note.txt', { type: 'text/plain' })],
      items: [makeClipboardItem(null, 'text/plain')],
    });
    expect(result).toEqual([]);
  });

  it('removes single attachment by index', () => {
    const files = [makeFile('a.png', 10), makeFile('b.png', 10), makeFile('c.png', 10)];
    const result = removeImageAttachmentAt(files, 1);
    expect(result.map((item: File) => item.name)).toEqual(['a.png', 'c.png']);
  });

  it('returns capability hint when model is not vision-enabled', () => {
    expect(getVisionCapabilityHint(true, false, 2)).toBe('当前模型不支持视觉能力，图片请求将被拒绝或降级为纯文本。');
    expect(getVisionCapabilityHint(true, true, 2)).toBe('');
    expect(getVisionCapabilityHint(false, false, 2)).toBe('');
  });

  it('returns voice input button states for idle, recording, processing, and unavailable modes', () => {
    expect(getVoiceInputButtonClass(true, true, false, false)).toContain('text-slate-500');
    expect(getVoiceInputButtonClass(true, true, true, false)).toContain('bg-rose-500');
    expect(getVoiceInputButtonClass(true, true, false, true)).toContain('bg-sky-500');
    expect(getVoiceInputButtonClass(false, true, false, false)).toContain('cursor-not-allowed');
    expect(getVoiceInputButtonClass(true, false, false, false)).toContain('cursor-not-allowed');
  });

  it('returns readable labels for voice input providers', () => {
    expect(getVoiceInputProviderLabel('azure')).toBe('Azure Speech');
    expect(getVoiceInputProviderLabel('browser')).toBe('Browser dictation');
  });
});
