type ClipboardLike = Pick<Clipboard, 'writeText'> | null;
type DocumentLike = Pick<Document, 'createElement' | 'execCommand'> & {
  body: Pick<HTMLElement, 'appendChild' | 'removeChild'>;
};

const fallbackCopyWithDocument = (text: string, doc: DocumentLike | null): boolean => {
  if (!doc?.body?.appendChild || !doc.createElement || !doc.execCommand) return false;

  const textarea = doc.createElement('textarea') as HTMLTextAreaElement;
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  textarea.style.pointerEvents = 'none';

  doc.body.appendChild(textarea);
  textarea.select();
  textarea.setSelectionRange(0, text.length);

  try {
    return doc.execCommand('copy');
  } finally {
    doc.body.removeChild(textarea);
  }
};

export async function copyTextToClipboard(
  text: string,
  clipboard: ClipboardLike = typeof navigator !== 'undefined' ? navigator.clipboard : null,
  doc: DocumentLike | null = typeof document !== 'undefined' ? (document as DocumentLike) : null,
): Promise<boolean> {
  if (!text.trim()) return false;

  if (clipboard?.writeText) {
    try {
      await clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to legacy document copy for environments where Clipboard API is blocked.
    }
  }

  return fallbackCopyWithDocument(text, doc);
}
