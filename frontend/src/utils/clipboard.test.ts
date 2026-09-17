import { describe, expect, it, vi } from 'vitest';

import { copyTextToClipboard } from './clipboard';

describe('copyTextToClipboard', () => {
  it('uses the clipboard API when available', async () => {
    const writeText = vi.fn(async () => undefined);

    await expect(
      copyTextToClipboard('convert "Sheet1" to HTML 高仿', {
        writeText,
      } as Pick<Clipboard, 'writeText'>, null),
    ).resolves.toBe(true);

    expect(writeText).toHaveBeenCalledWith('convert "Sheet1" to HTML 高仿');
  });

  it('falls back to document.execCommand when clipboard write fails', async () => {
    const writeText = vi.fn(async () => {
      throw new Error('clipboard blocked');
    });
    const select = vi.fn();
    const setSelectionRange = vi.fn();
    const appendChild = vi.fn();
    const removeChild = vi.fn();
    const execCommand = vi.fn(() => true);
    const textarea = {
      value: '',
      style: {} as Record<string, string>,
      setAttribute: vi.fn(),
      select,
      setSelectionRange,
    };
    const doc = {
      body: {
        appendChild,
        removeChild,
      },
      createElement: vi.fn(() => textarea),
      execCommand,
    } as unknown as Document;

    await expect(
      copyTextToClipboard('historic user message', {
        writeText,
      } as Pick<Clipboard, 'writeText'>, doc),
    ).resolves.toBe(true);

    expect(execCommand).toHaveBeenCalledWith('copy');
    expect(appendChild).toHaveBeenCalledWith(textarea);
    expect(removeChild).toHaveBeenCalledWith(textarea);
    expect(select).toHaveBeenCalled();
    expect(setSelectionRange).toHaveBeenCalledWith(0, 'historic user message'.length);
  });

  it('returns false when text is empty', async () => {
    await expect(copyTextToClipboard('   ', null, null)).resolves.toBe(false);
  });
});
