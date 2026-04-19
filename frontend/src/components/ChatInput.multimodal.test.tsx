import { describe, expect, it } from 'vitest';
import {
  canSubmitFromInput,
  extractClipboardFiles,
  getAcceptAttributeFromPolicy,
  getAttachmentCompositionHint,
  getModelCapabilityBadge,
  getOversizedWarningMessage,
  getTooManyFilesWarningMessage,
  getUploadButtonClass,
  getVisionCapabilityHint,
  getVoiceInputButtonClass,
  getVoiceInputProviderLabel,
  mergeAttachments,
  removeAttachmentAt,
  resolveUploadPolicy,
  splitAttachmentsByType,
} from './ChatInput';

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
    const result = mergeAttachments(existing, incoming, 2, 10 * 1024 * 1024);
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
    const pdf = new File(['pdf'], 'report.pdf', { type: 'application/pdf' });
    const result = extractClipboardFiles({
      files: [text, image],
      items: [makeClipboardItem(pdf, 'application/pdf')],
    });
    expect(result.map((item) => item.name)).toEqual(['shot.png', 'report.pdf']);
  });

  it('falls back to clipboard items when files are unavailable', () => {
    const image = makeFile('pasted.png', 10);
    const pdf = new File(['pdf'], 'sheet.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const result = extractClipboardFiles({
      items: [makeClipboardItem(image), makeClipboardItem(pdf, pdf.type), makeClipboardItem(null, 'text/plain')],
    });
    expect(result.map((item) => item.name)).toEqual(['pasted.png', 'sheet.xlsx']);
  });

  it('ignores non-file clipboard payloads', () => {
    const result = extractClipboardFiles({
      files: [new File(['hello'], 'note.txt', { type: 'text/plain' })],
      items: [makeClipboardItem(null, 'text/plain')],
    });
    expect(result).toEqual([]);
  });

  it('removes single attachment by index', () => {
    const files = [makeFile('a.png', 10), makeFile('b.png', 10), makeFile('c.png', 10)];
    const result = removeAttachmentAt(files, 1);
    expect(result.map((item: File) => item.name)).toEqual(['a.png', 'c.png']);
  });

  it('splits images and non-image files for submission pipeline', () => {
    const image = makeFile('cover.png', 10);
    const pdf = new File(['pdf'], 'report.pdf', { type: 'application/pdf' });
    const csv = new File(['a,b'], 'table.csv', { type: 'text/csv' });
    const result = splitAttachmentsByType([image, pdf, csv]);
    expect(result.imageFiles.map((item) => item.name)).toEqual(['cover.png']);
    expect(result.nonImageFiles.map((item) => item.name)).toEqual(['report.pdf', 'table.csv']);
  });

  it('returns capability hint only when image attachments are present on a non-vision model', () => {
    expect(getVisionCapabilityHint(true, false, 0)).toBe('');
    expect(getVisionCapabilityHint(true, false, 1)).toBe(
      '当前模型不支持图片理解能力，本次图片不会被分析；PDF/表格附件不受这条提示直接约束。',
    );
    expect(getVisionCapabilityHint(true, true, 1)).toBe('');
    expect(getVisionCapabilityHint(false, false, 2)).toBe('');
  });

  it('summarizes attachment composition for images, documents, and mixed uploads', () => {
    expect(getAttachmentCompositionHint(0, 0)).toBe('');
    expect(getAttachmentCompositionHint(1, 0)).toBe('已选择 1 个附件：1 张图片');
    expect(getAttachmentCompositionHint(0, 2)).toBe('已选择 2 个附件：2 个文档');
    expect(getAttachmentCompositionHint(1, 2)).toBe('已选择 3 个附件：1 张图片，2 个文档');
  });

  it('returns a lightweight model capability badge for the selected model', () => {
    expect(getModelCapabilityBadge(false, false)).toBe('');
    expect(getModelCapabilityBadge(true, true)).toBe('Vision');
    expect(getModelCapabilityBadge(true, false)).toBe('Text Only');
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

  it('resolves backend upload policy with graceful fallback', () => {
    expect(
      resolveUploadPolicy({
        max_files: 6,
        max_file_size_bytes: 8 * 1024 * 1024,
        allowed_mime_types: ['application/pdf', 'image/png'],
        allowed_extensions: ['.pdf', '.png'],
      }),
    ).toMatchObject({
      maxFiles: 6,
      maxFileSizeBytes: 8 * 1024 * 1024,
      allowedMimeTypes: ['application/pdf', 'image/png'],
      allowedExtensions: ['.pdf', '.png'],
    });

    expect(
      resolveUploadPolicy({
        max_files: 0,
        max_file_size_bytes: -1,
        allowed_mime_types: [],
        allowed_extensions: [],
      }),
    ).toMatchObject({
      maxFiles: 10,
      maxFileSizeBytes: 20 * 1024 * 1024,
    });
  });

  it('builds file picker accept list from backend policy', () => {
    expect(getAcceptAttributeFromPolicy(resolveUploadPolicy({
      allowed_mime_types: ['application/pdf', 'image/png'],
      allowed_extensions: ['.pdf', '.png'],
    }))).toBe('.pdf,.png,application/pdf,image/png');
  });

  it('formats warning copy with actual backend limits', () => {
    const policy = resolveUploadPolicy({
      max_files: 6,
      max_file_size_bytes: 8 * 1024 * 1024,
    });
    expect(getTooManyFilesWarningMessage(policy.maxFiles)).toBe('最多选择 6 个附件');
    expect(getOversizedWarningMessage(policy.maxFileSizeBytes)).toBe('部分文件超过 8MB 大小限制，已忽略');
  });
});
