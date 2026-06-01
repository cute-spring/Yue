import { Message } from '../types';

const CONTINUE_NOTICE_RE =
  /\n\n> ⚠️ \*\*\[系统提示\]\*\* 由于输出长度限制，内容可能未完全生成。您可以输入 \*\*“继续”\*\* 来获取剩余部分。/g;

export const stripContinuationNotice = (content: string): string =>
  (content || '').replace(CONTINUE_NOTICE_RE, '');

export const getMessageContinuationKey = (msg: Pick<Message, 'assistant_turn_id' | 'id'>): string => {
  if (typeof msg.assistant_turn_id === 'string' && msg.assistant_turn_id.trim()) {
    return msg.assistant_turn_id.trim();
  }
  if (msg.id !== undefined && msg.id !== null) {
    return `message:${String(msg.id)}`;
  }
  return '';
};

const findRootKey = (messages: Message[], msg: Message): string => {
  let current = getMessageContinuationKey(msg);
  let root = msg.continuation_root_id || msg.continuation_of || current;
  const byKey = new Map(messages.map((item) => [getMessageContinuationKey(item), item]));
  const seen = new Set<string>();

  while (root && byKey.has(root) && !seen.has(root)) {
    seen.add(root);
    const parent = byKey.get(root)!;
    const parentKey = getMessageContinuationKey(parent);
    root = parent.continuation_root_id || parent.continuation_of || parentKey || root;
    if (root === parentKey) break;
  }

  return root || current;
};

export const getContinuationChain = (messages: Message[], target: Message): Message[] => {
  const root = findRootKey(messages, target);
  if (!root) return [target];

  return messages.filter((msg) => {
    if (msg.role !== 'assistant') return false;
    const key = getMessageContinuationKey(msg);
    return (
      key === root ||
      msg.continuation_root_id === root ||
      msg.continuation_of === root ||
      findRootKey(messages, msg) === root
    );
  });
};

export const getMergedContinuationContent = (messages: Message[], target: Message): string => {
  const chain = getContinuationChain(messages, target);
  if (chain.length <= 1 && !target.continuation_of && !target.continuation_root_id) {
    return target.content || '';
  }
  return chain.map((msg) => stripContinuationNotice(msg.content || '')).join('');
};

export const hasContinuationSiblings = (messages: Message[], target: Message): boolean =>
  getContinuationChain(messages, target).length > 1;

export const getContinuationTail = (content: string, maxChars = 3000): string =>
  stripContinuationNotice(content || '').slice(-maxChars);

export const inferContinuationContentType = (content: string): string => {
  const matches = [...(content || '').matchAll(/```([a-zA-Z0-9_-]+)?/g)];
  if (matches.length > 0) {
    const lang = matches[matches.length - 1][1]?.trim().toLowerCase();
    if (lang) return lang;
    return 'code';
  }
  const trimmed = (content || '').trimStart().toLowerCase();
  if (trimmed.startsWith('<svg')) return 'svg';
  if (trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html')) return 'html';
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return 'json';
  return 'markdown';
};

export const buildContinuationRequestOverrides = (
  messages: Message[],
  target: Message,
): Record<string, string> => {
  const targetKey = getMessageContinuationKey(target);
  const mergedContent = getMergedContinuationContent(messages, target);
  return {
    continuation_of: targetKey,
    continuation_root_id: findRootKey(messages, target) || targetKey,
    continuation_content_type: target.content_type || inferContinuationContentType(mergedContent),
    continuation_tail: getContinuationTail(mergedContent),
  };
};
