import { describe, expect, it, vi } from 'vitest';

import { copyTraceTextToClipboard } from './clipboard';

describe('copyTraceTextToClipboard', () => {
  it('copies the historic user message to the clipboard', async () => {
    const writeText = vi.fn(async () => undefined);

    await expect(
      copyTraceTextToClipboard('Please inspect the last tool chain for this historical run.', {
        writeText,
      } as Pick<Clipboard, 'writeText'>),
    ).resolves.toBe(true);

    expect(writeText).toHaveBeenCalledWith('Please inspect the last tool chain for this historical run.');
  });

  it('returns false when clipboard support is unavailable or text is empty', async () => {
    await expect(copyTraceTextToClipboard('', null)).resolves.toBe(false);
    await expect(copyTraceTextToClipboard('   ', null)).resolves.toBe(false);
  });
});
