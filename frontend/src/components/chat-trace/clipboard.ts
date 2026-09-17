export async function copyTraceTextToClipboard(
  text: string,
  clipboard: Pick<Clipboard, 'writeText'> | null =
    typeof navigator !== 'undefined' ? navigator.clipboard : null,
): Promise<boolean> {
  if (!text.trim() || !clipboard?.writeText) return false;

  try {
    await clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
