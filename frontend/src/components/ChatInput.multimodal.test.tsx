import { describe, expect, it } from 'vitest';
import { canSubmitFromInput, getUploadButtonClass, mergeImageAttachments } from './ChatInput';

const makeFile = (name: string, size: number): File => {
  const content = new Array(size).fill('a').join('');
  return new File([content], name, { type: 'image/png' });
};

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

  it('uses high-contrast style for upload button', () => {
    const idleClass = getUploadButtonClass(0);
    const activeClass = getUploadButtonClass(2);
    expect(idleClass).toContain('border');
    expect(idleClass).toContain('bg-background');
    expect(activeClass).toContain('bg-primary/15');
    expect(activeClass).toContain('border-primary/40');
  });
});
