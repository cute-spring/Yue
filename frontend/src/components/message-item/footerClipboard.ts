import { copyTextToClipboard } from '../../utils/clipboard';

export async function copyAssistantMessageToClipboard(
  content: string,
  copyText: (text: string) => Promise<boolean> = copyTextToClipboard,
): Promise<boolean> {
  if (!content.trim()) return false;
  return copyText(content);
}
