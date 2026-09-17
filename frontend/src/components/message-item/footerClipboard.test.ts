import { describe, expect, it, vi } from 'vitest';

import { copyAssistantMessageToClipboard } from './footerClipboard';

describe('copyAssistantMessageToClipboard', () => {
  it('copies assistant message content via the shared clipboard utility', async () => {
    const copyText = vi.fn(async () => true);

    await expect(copyAssistantMessageToClipboard('Assistant reply content', copyText)).resolves.toBe(true);

    expect(copyText).toHaveBeenCalledWith('Assistant reply content');
  });

  it('returns false when the content is empty', async () => {
    const copyText = vi.fn(async () => true);

    await expect(copyAssistantMessageToClipboard('   ', copyText)).resolves.toBe(false);
    expect(copyText).not.toHaveBeenCalled();
  });
});
