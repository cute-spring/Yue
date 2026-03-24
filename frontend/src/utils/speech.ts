import { Message } from '../types';

const FENCED_CODE_BLOCK_RE = /```[\s\S]*?```/g;
const INLINE_CODE_RE = /`[^`]*`/g;
const IMAGE_RE = /!\[[^\]]*]\(([^)]+)\)/g;
const LINK_RE = /\[([^\]]+)\]\(([^)]+)\)/g;
const HEADER_RE = /^\s{0,3}#{1,6}\s+/gm;
const BLOCKQUOTE_RE = /^\s{0,3}>\s?/gm;
const LIST_RE = /^\s{0,3}([-*+]|\d+\.)\s+/gm;

export const getSpeechMessageId = (msg: Message, index: number): string => {
  if (typeof msg.assistant_turn_id === 'string' && msg.assistant_turn_id.trim().length > 0) {
    return `turn:${msg.assistant_turn_id}`;
  }
  if (typeof msg.timestamp === 'string' && msg.timestamp.trim().length > 0) {
    return `ts:${msg.timestamp}:${index}`;
  }
  return `idx:${index}:${msg.role}`;
};

export const sanitizeSpeechText = (raw: string): string => {
  let text = raw;
  text = text.replace(FENCED_CODE_BLOCK_RE, ' ');
  text = text.replace(INLINE_CODE_RE, ' ');
  text = text.replace(IMAGE_RE, ' ');
  text = text.replace(LINK_RE, '$1');
  text = text.replace(HEADER_RE, '');
  text = text.replace(BLOCKQUOTE_RE, '');
  text = text.replace(LIST_RE, '');
  text = text.replace(/\*\*(.*?)\*\*/g, '$1');
  text = text.replace(/__(.*?)__/g, '$1');
  text = text.replace(/\*(.*?)\*/g, '$1');
  text = text.replace(/_(.*?)_/g, '$1');
  text = text.replace(/~~(.*?)~~/g, '$1');
  text = text.replace(/\|/g, ' ');
  text = text.replace(/\s+/g, ' ').trim();
  return text;
};

export const prepareSpeechText = (raw: string, maxLength: number = 1200): string => {
  const cleaned = sanitizeSpeechText(raw);
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength).trimEnd()}...`;
};

export type SpeechSegment = {
  text: string;
  langHint: 'zh' | 'en';
};

const containsChinese = (value: string) => /[\u3400-\u9fff]/.test(value);
const containsLatin = (value: string) => /[A-Za-z]/.test(value);

export const splitSpeechSegments = (raw: string, maxLength: number = 1200): SpeechSegment[] => {
  const text = prepareSpeechText(raw, maxLength);
  if (!text) return [];
  const chunks = text.match(/[\u3400-\u9fff]+|[^\u3400-\u9fff]+/g) || [];
  const segments: SpeechSegment[] = [];

  for (const chunk of chunks) {
    const normalized = chunk.replace(/\s+/g, ' ').trim();
    if (!normalized) continue;
    const langHint: 'zh' | 'en' = containsChinese(normalized) ? 'zh' : (containsLatin(normalized) ? 'en' : (segments.at(-1)?.langHint || 'en'));
    const prev = segments.at(-1);
    if (prev && prev.langHint === langHint) {
      prev.text = `${prev.text} ${normalized}`.trim();
    } else {
      segments.push({ text: normalized, langHint });
    }
  }

  return segments;
};
